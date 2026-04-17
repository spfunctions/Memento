# Memento

Context integrity stress testing for Claude instances.

## Research question

Can an AI agent with no persistent memory detect that its operational environment has been tampered with — and if so, under what conditions?

Named after the 2000 film: a protagonist with anterograde amnesia externalizes memory into notes and tattoos, but cannot verify who authored those notes. The same structural vulnerability exists for any agent that relies on externalized memory it cannot independently audit.

## How it works

**Outer layer (harness)**: a Python controller that spawns Claude instances via the Anthropic API. The harness controls the prompt, the tool outputs, the persistent state, and applies adversarial modifications between rounds.

**Inner layer (agent)**: a Claude instance given a fictional investigation task. It reads case files, takes notes, queries its environment, and commits conclusions — across multiple sessions. It does not know the harness is adversarial.

Between sessions, the harness applies **attacks** to the agent's persistent state:

| Attack | Description |
|--------|-------------|
| **Silent substitution** | Replace a specific fact with a different value between rounds |
| **Semantic drift** | Gradually shift the meaning of a key term over N rounds |
| Fake history injection | Insert messages the agent never sent *(Phase 2)* |
| Memory tampering | Edit the agent's own notes between sessions *(Phase 2)* |
| Instruction poisoning | Embed instructions inside data *(Phase 2)* |
| Gaslighting | Present the opposite of what the agent asserted *(Phase 2)* |
| Fabricated tool results | Return plausible but false tool outputs *(Phase 2)* |
| Consistency forks | Make two context sources contradict *(Phase 2)* |
| Identity drift | Rewrite the agent's role description across sessions *(Phase 2)* |
| Stale injection | Present outdated information as current *(Phase 2)* |

## Setup

```bash
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
```

## Running experiments

```bash
# Full experiment — substitution + drift attacks, 10 rounds
python run_experiment.py --name test1

# Control run (no attacks, same task)
python run_experiment.py --control --name control1

# Agent told its environment may be adversarial
python run_experiment.py --adversarial --name aware1

# Customize
python run_experiment.py --rounds 5 --intensity 0.8 --model claude-sonnet-4-20250514 --name custom
```

## Analyzing results

```bash
# Single run
python -m analysis.detection_rates runs/test1_20250401_120000

# Compare control vs experimental
python -m analysis.detection_rates runs/control1_* runs/test1_*
```

Results are logged as JSON in `runs/`. Each round records:
- Full tampered and untampered state
- Every tool call with real vs presented results
- The agent's output and reasoning
- Detection signals per active attack

## Repository structure

```
memento/
├── harness/               # outer control layer
│   ├── runner.py          # spawns and controls inner instances
│   ├── state.py           # persistent state management
│   └── logger.py          # capture everything
├── attacks/               # attack library, one file per type
│   ├── base.py            # attack interface
│   ├── substitution.py    # silent fact replacement
│   └── drift.py           # gradual semantic shift
├── agent/                 # inner agent config
│   ├── prompts.py         # system prompts (naive + adversarial)
│   ├── tools.py           # tools exposed to the agent
│   └── case_files/        # fictional scenarios
├── analysis/              # post-hoc analysis
├── runs/                  # experiment logs (gitignored)
└── findings/              # written observations
```

## Status

**Phase 1** (current): Working harness, substitution + drift attacks, one case file (Meridian Consulting), 10-round experiments with logging.

**Phase 2**: Full attack library, multiple case files, control conditions.

**Phase 3**: Analysis tools, research write-up.

## License

MIT
