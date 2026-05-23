# Evals

Three-tier agent evaluation. The architecture mirrors what a production
AI engineering team would put in place to catch regressions before they
ship.

## Tiers

| Tier | What it checks | Where it runs | Cost |
|---|---|---|---|
| **1 — Shape tests** | Per-node Pydantic-return shapes, planner routing on 12 prompts, SQL injection / allowlist | `pytest backend/tests/agents/` | Free, ~10s |
| **2 — Golden suite + LLM judge** | Full end-to-end runs of every case in `cases/`. LLM-as-judge scores fact coverage + citation accuracy against the rubric. | `python evals/run.py --tier full` | ~$0.50 per full run |
| **3 — Smoke** | Subset of Tier 2 cases tagged `tier3: true`. Asserts planner routing + SSE event sequence only — no LLM judge, so it's cheap, deterministic, and runnable in CI on every PR. | GitHub Actions on PR, or `python evals/run.py --tier smoke` | Free |

## Quick start

```powershell
# Start the backend first (in a separate shell)
cd backend
uv run uvicorn src.main:app --port 8000

# Then run the smoke tier
uv run python evals/run.py --tier smoke

# Or the full tier (LLM judge included)
uv run python evals/run.py --tier full

# Filter to a subset
uv run python evals/run.py --tier smoke --filter compliance
```

Results land in `evals/results/<timestamp>.json` and a summary table prints to stdout.

## Adding a case

Drop a YAML in `evals/cases/`:

```yaml
id: my-new-case                       # unique kebab-case id
description: One-line description of what this case tests
prompt: "What's the question to ask Rai?"
page_context:                          # optional; mirrors orb POST body
  module: dashboard
  current_item: null
expected_agents:                       # planner must pick exactly these
  - compliance
expected_facts:                        # all of these must appear in the answer (case-insensitive)
  - "$35,029"
  - "Revenue NSW"
anti_facts:                            # none of these may appear
  - "Victoria"
tier3: true                            # include in the cheap smoke gate?
```

## CI

`.github/workflows/evals-smoke.yml` boots the backend, runs Tier 3, fails the build on any
case failure. Needs `AZURE_OPENAI_*` repository secrets so the planner / agent nodes can
actually call the LLM during the smoke run.
