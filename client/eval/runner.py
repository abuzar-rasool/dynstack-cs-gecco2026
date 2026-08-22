"""
Each run gets its own port pair, its own .buf file, and its own subprocess
tree, so many can execute in parallel. We only parse three KPIs out of the
client's stdout: enough for the lexicographic competition objective. Any
parse miss or timeout collapses into a sentinel `delivery_errors = -1` so
the caller can report `ERR` without crashing the whole matrix.

Ctrl-C tears down every spawned subprocess via the `_processes` registry,
which is also wiped when the matrix finishes.
"""
from __future__ import annotations

import os
import re
import signal
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from itertools import count
from pathlib import Path
from threading import Lock

from scenarios import settings_pb2
from scenarios.presets import PRESETS


CLIENT_DIR  = Path(__file__).resolve().parent.parent
SRC_DIR     = CLIENT_DIR.parent
RUNNER_DLL  = Path(os.environ.get(
    "DYNSTACK_RUNNER_DLL",
    str(SRC_DIR / "server/simulation/DynStack.SimulationRunner/bin/Debug/net10.0/DynStack.SimulationRunner.dll"),
))
VENV_PYTHON = SRC_DIR / ".venv/bin/python"
SIM_ID      = "658f9b28-6686-40d2-8800-611bd8466215"
SCRATCH_DIR = Path("/tmp/dynstack-eval")

_ERRORS_RE  = re.compile(r"Delivery Errors\s*:\s*(-?\d+)")
_BLOCKS_RE  = re.compile(r"Handled Blocks\s*:\s*(-?\d+)")
_PARKING_RE = re.compile(r"Max Parking Duration\s*:\s*([\d.]+)s")


@dataclass
class RunResult:
    scenario: str
    seed: int | None
    delivery_errors: int
    handled_blocks: int
    max_parking_duration: float

    @property
    def parse_failed(self) -> bool:
        return self.delivery_errors < 0


def _failed(scenario: str, seed: int | None) -> RunResult:
    return RunResult(scenario, seed, -1, -1, float("inf"))


def _parse_kpis(stdout: str, scenario: str, seed: int) -> RunResult:
    e = _ERRORS_RE.search(stdout)
    b = _BLOCKS_RE.search(stdout)
    p = _PARKING_RE.search(stdout)
    if not (e and b and p):
        return _failed(scenario, seed)
    return RunResult(scenario, seed, int(e.group(1)), int(b.group(1)), float(p.group(1)))


_port_counter = count(9000, 10)
_port_lock = Lock()


def _reset_port_counter() -> None:
    global _port_counter
    with _port_lock:
        _port_counter = count(9000, 10)


def _alloc_port_pair() -> tuple[int, int]:
    with _port_lock:
        for _ in range(1000):
            base = next(_port_counter)
            if _port_free(base) and _port_free(base + 1):
                return base, base + 1
        raise RuntimeError("could not find a free port pair in 1000 tries")


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _wait_for_port(port: int, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.1)
    return False


_processes: set[subprocess.Popen] = set()
_processes_lock = Lock()


def kill_all() -> None:
    """Terminate every still-running subprocess. Called on Ctrl-C and exit."""
    with _processes_lock:
        procs = list(_processes)
    for p in procs:
        try:
            p.terminate()
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 3.0
    for p in procs:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            p.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            try:
                p.kill()
            except ProcessLookupError:
                pass


def _write_buf(scenario: str, path: Path, seed: int | None) -> int:
    """Serialise the preset (with optional seed override) and return the
    effective seed actually used."""
    if scenario not in PRESETS:
        raise KeyError(f"unknown scenario: {scenario!r}")
    settings: settings_pb2.Settings = PRESETS[scenario]()
    if seed is not None:
        settings.Seed = seed
    path.write_bytes(settings.SerializeToString())
    return settings.Seed


def run_one(
    strategy: str,
    scenario: str,
    *,
    seed: int | None = None,
    params: dict[str, str] | None = None,
    server_timeout: float = 120.0,
    client_timeout: float = 120.0,
) -> RunResult:
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"{strategy}__{scenario}__{uuid.uuid4().hex}"
    buf_path = SCRATCH_DIR / f"{tag}.buf"
    effective_seed = _write_buf(scenario, buf_path, seed)

    async_port, sync_port = _alloc_port_pair()

    server = subprocess.Popen(
        [
            "dotnet", "exec", str(RUNNER_DLL),
            "--sim", "CS",
            "--settings", str(buf_path),
            "--url", f"tcp://127.0.0.1:{async_port}",
            "--id", SIM_ID,
            "--syncurl", f"tcp://127.0.0.1:{sync_port}",
        ],
        cwd=SRC_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    with _processes_lock:
        _processes.add(server)

    try:
        if not _wait_for_port(sync_port, timeout=server_timeout):
            return _failed(scenario, effective_seed)
        client_env = os.environ.copy()
        client_env["DYNSTACK_QUIET"] = "1"
        client_cmd = [
            str(VENV_PYTHON), "-u", "main.py",
            f"tcp://127.0.0.1:{sync_port}", SIM_ID,
            "--strategy", strategy,
        ]
        for key, value in (params or {}).items():
            client_cmd += ["-p", f"{key}={value}"]
        client = subprocess.run(
            client_cmd,
            cwd=CLIENT_DIR,
            capture_output=True,
            text=True,
            timeout=client_timeout,
            env=client_env,
        )
        return _parse_kpis(client.stdout, scenario, effective_seed)
    except subprocess.TimeoutExpired:
        return _failed(scenario, effective_seed)
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=2)
        with _processes_lock:
            _processes.discard(server)
        buf_path.unlink(missing_ok=True)


def run_paired(
    strategies: list[str],
    scenarios: list[str],
    seeds_by_scenario: dict[str, list[int | None]],
    *,
    workers: int = 8,
    progress: Callable[[str, str, RunResult], None] | None = None,
) -> dict[str, dict[str, list[RunResult]]]:
    """Run every strategy on every scenario across a *shared* seed list.

    `seeds_by_scenario[scenario]` is the list of seeds run for that
    scenario, used identically for every strategy: that's what makes the
    comparison paired (common random numbers), so shared per-instance
    variance cancels when you difference two strategies. Returns one
    `RunResult` per seed, in the seed-list order, so the caller can
    aggregate (mean ± std) and pair across strategies by index.
    """
    jobs = [
        (s, sc, i, seed)
        for s in strategies
        for sc in scenarios
        for i, seed in enumerate(seeds_by_scenario[sc])
    ]
    results: dict[str, dict[str, list[RunResult]]] = {
        s: {sc: [None] * len(seeds_by_scenario[sc]) for sc in scenarios}
        for s in strategies
    }

    _reset_port_counter()

    prev_int = prev_term = None
    try:
        prev_int  = signal.signal(signal.SIGINT,  lambda *_: (kill_all(), sys.exit(130)))
        prev_term = signal.signal(signal.SIGTERM, lambda *_: (kill_all(), sys.exit(143)))
    except ValueError:
        pass

    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    run_one, strategy, scenario, seed=seed,
                ): (strategy, scenario, idx)
                for strategy, scenario, idx, seed in jobs
            }
            for fut in as_completed(futures):
                strategy, scenario, idx = futures[fut]
                try:
                    result = fut.result()
                except Exception:
                    result = _failed(scenario, None)
                results[strategy][scenario][idx] = result
                if progress:
                    progress(strategy, scenario, result)
    finally:
        if prev_int  is not None: signal.signal(signal.SIGINT,  prev_int)
        if prev_term is not None: signal.signal(signal.SIGTERM, prev_term)
        kill_all()

    return {s: dict(sorted(runs.items())) for s, runs in results.items()}


def ensure_runner_built() -> None:
    if RUNNER_DLL.exists():
        return
    proc = subprocess.run(
        ["dotnet", "build", "--nologo"],
        cwd=SRC_DIR / "server/simulation",
    )
    if proc.returncode != 0 or not RUNNER_DLL.exists():
        raise RuntimeError("dotnet build failed; cannot run eval")
