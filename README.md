# Evolutionary Dispatching for Dynamic Crane Scheduling

Code for my master's thesis "Exploration of Evolutionary Approaches for
Dispatching Heuristics in Dynamic Crane Scheduling under Uncertainty"
(M.Sc. High Integrity Systems, Frankfurt UAS) and for my entry to the
[DynStack](https://dynstack.adaptop.at/) GECCO 2026 Crane Scheduling
competition, which placed 2nd with 186 handled blocks and no delivery
errors.

Two gantry cranes share a girder rail. A discrete-event simulator streams
the world state over ZMQ once per simulated second and the solver answers
with a schedule assigning pending block moves to the cranes. Scoring is
lexicographic: delivery errors first (they must be zero), then handled
blocks, then maximum parking duration.

## The two methods

Both use the same base: a fixed rule skeleton derived from Pham et al.'s
GECCO 2024 winner, split into seven decision hooks, plus a tracker that
rejects any proposal violating the simulator contract. Three hooks are
worth learning: placement (2), sequencing (4), routing (5). Only their
scoring functions are learned, over the same 20 features.

**SCA-GPHH** evolves one GP tree per hook with epsilon-lexicase selection,
in five stages: A dispatch core, B placement, C joint, D denoised joint,
E denoised joint through the shipped overlays. Champion:
`sca_gphh_stage_e`.

**CMA-ES** keeps the skeleton and features but replaces the trees with a
flat 20-weight vector. Champion: `cmaes_champion`.

Two structural overlays sit in the framework, not in either policy:
proactive dig-out of buried blocks, and a head-of-line reorder fix. They
are worth about a third of the total gain and work on any custom-move
strategy (on the Pham baseline alone they add 33 blocks on `default`).

Held-out results, 3 scenarios and 10 paired seeds, handled blocks, no
delivery errors anywhere:

| Policy | Held-out mean |
|---|---:|
| `nearest_crane` | 98.2 |
| `pham_rule_based` | 136.6 |
| `sca_gphh_stage_e` | 173.9 |
| `cmaes_champion` | 175.3 |

The gap between the two champions sits inside the simulation noise band,
so the tree representation does not beat a well-tuned linear combination
of the same features here. It is far more readable though: the champion
uses 6 of the 20 features and its sequencing rule is just
`pd_dist - is_upstream`.

## Quick start

Needs [uv](https://docs.astral.sh/uv/) (Python 3.13+) and the .NET SDK.

```bash
uv sync
make build
make eval STRATEGIES="sca_gphh_stage_e cmaes_champion"
```

`make eval` runs the paired benchmark (the same seed list for every
strategy, 15 scenarios by 10 seeds) and writes `client/eval/results/` and
`client/eval/summary.md`. Plain `make` opens a picker. To watch a run
live: `make server SCENARIO=busy` in one terminal, `make client` in
another.

## Layout

```
client/
  main.py            strategy registry and CLI
  core/              the ZMQ receive-plan-reply loop
  framework/         hook pipeline, constraint tracker, the two overlays
  scenarios/         12 training and 3 held-out presets
  strategies/        baselines, sca_gphh/ (stages + champions), cmaes/
  eval/              paired multi-seed benchmark
  training/          train_gp.py, train_cmaes.py, and their pieces
server/              forked DynStack simulator (see below)
```

Strategies are named after the training stage they came from, so
`sca_gphh_stage_a` through `sca_gphh_stage_e`. The `gp_stage_*` and
`cmaes_weights` entries are the runtime bases the trainers drive; they run
standalone but are skipped by the benchmark unless named explicitly.

## Reproducing the thesis numbers

Any single data point needs four things: the server, the client with a
champion genome (pinned in source, there are no model files), a scenario
preset and a seed. One evaluation takes about 5 seconds.

```bash
cd client

# the ladder behind the staircase and the appendix tables, ~25 min on 8 cores
uv run python -m eval

# GP training, one stage at a time, promote each champion before the next
uv run python -m training.train_gp --stage A     # then B, C, D, E

# CMA-ES training
uv run python -m training.train_cmaes
```

Strategy behaviour is set through constructor parameters, passed with
repeated `-p key=value` flags (for example `-p digout=False`). Each
strategy's `__init__` lists what it accepts.

`DYNSTACK_GP_SMOKE=1` (or `DYNSTACK_CMAES_SMOKE=1`) gives a two-minute
plumbing run of any stage. `DYNSTACK_GP_WORKERS` matches the fan-out to
your cores. The full GP pipeline is around 154,000 simulations, the CMA-ES
run 144,000.

Each training run writes a folder under `client/training/data/runs/` with
its configuration, per-generation convergence, the Hall of Fame, and the
confirmation pass that selects the champion. The runs that produced the
shipped champions are checked in, one folder per stage plus one for
CMA-ES.

Two things cannot be reproduced here. The competition placement itself:
that scenario is undisclosed and was evaluated once on the organisers'
server, so the three `comp_scenario_*` presets are my reconstruction of
competition-like conditions and serve as the held-out set. And the Pham
baseline is re-implemented from the paper, since the original code is not
available.

## Simulation server

`server/` is a fork of
[dynstack/dynstack](https://github.com/dynstack/dynstack) (upstream commit
`87345f6`). Only the `simulation/` tree is vendored; upstream's starter
kits, publications and the settings for the other two tracks are left out.
All changes sit in the synchronous code path of the crane-scheduling
simulation, so the asynchronous path used by the competition is untouched
and the client behaves the same against an unmodified upstream server:

1. Synchronous virtual-time mode ported to the crane-scheduling track,
   which upstream only implements for hot storage. A one-hour simulation
   finishes in about 5 seconds. The 200 ms activation delay is kept, so
   scheduling semantics do not change.
2. An end-of-run frame in synchronous mode, so a client no longer waits
   out a receive timeout to notice a run finished.
3. Faster first contact: the first world frame is resent every 200 ms
   until the client answers, instead of once every 5 seconds.

The last two roughly double throughput, which is what made the multi-seed
training affordable. Scenarios are not defined in the server; they live in
`client/scenarios/presets.py` and are passed in as a serialised settings
message.

Build it with `cd server/simulation && dotnet build`, or just `make build`.

## License

Client code: GPL-3.0, see `LICENSE`. The `server/` directory keeps its
upstream MIT license.
