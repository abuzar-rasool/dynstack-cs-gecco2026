"""
Scenario CLI: writes a `Settings` protobuf to disk for the C# server.

    python -m scenarios --list
    python -m scenarios --name default --out /tmp/dynstack.buf
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scenarios.presets import PRESETS


def main() -> int:
    p = argparse.ArgumentParser(prog="scenarios")
    p.add_argument("--list", action="store_true", help="list known preset names")
    p.add_argument("--name", help="preset name (see --list)")
    p.add_argument("--out",  help="output path for the serialised .buf file")
    args = p.parse_args()

    if args.list:
        for name in PRESETS:
            print(name)
        return 0

    if not args.name or not args.out:
        p.error("--name and --out are required (unless --list)")

    factory = PRESETS.get(args.name.lower())
    if factory is None:
        print(f"unknown preset: {args.name!r}. Known: {', '.join(PRESETS)}", file=sys.stderr)
        return 2

    payload = factory().SerializeToString()
    Path(args.out).write_bytes(payload)
    print(f"wrote {len(payload)} bytes -> {args.out} (preset={args.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
