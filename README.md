# Project AGL — Agentic General Ledger (Challenge 2)

An accountant-supervised agent that categorizes and reconciles bank transactions for a Dutch SME,
auto-posts what it is sure of, and defers the rest to a ranked human queue. Built for the Neno case
challenge.

**One principle: the agent (the LLM) decides; code only grounds the facts and guards the post.** Per
transaction the agent picks the chart-of-accounts account, decides which open invoice or bill it
settles (verifying the provided ~96% match rather than trusting it), flags anomalies, and rates two
independent confidences (one for the account, one for the match). Code computes the verifiable facts
(amount vs document total, payment direction, which documents are still open) and runs a strict,
downgrade-only guard before anything auto-posts. A confident wrong post is the costly outcome, so the
whole design serves one goal: never be confidently wrong.

## Results

From the committed `backend/eval_artifact.json` (a real Claude run over all 100 transactions; the
deck reports the k=3 range, since the model is non-deterministic).

| Metric | Value |
|--------|-------|
| Auto-post rate | ~84% — the confident bulk that drives the 30→60 capacity gain |
| Reconciliation accuracy (document-settling rows) | 25/25 — zero false matches |
| Categorisation accuracy | 0.93–0.96 |
| False-confidence (auto-posted-and-wrong) | 0 on reconciliation and material entries; 1–3 immaterial on categorisation |
| Anomaly detection | 1 of 1 caught, 0 false positives |
| Learning lift (cold→warm, eligible rows) | about +0.5 |

The false-confidence residual is inspected, not hidden: the few cases are a ground-truth-weak label,
a judgment-call account, and a chart gap — none a clear model error. The data is synthetic (Studio
Vondel B.V., Q1 2026), so this proves the mechanism, not a production-calibrated accuracy rate.

## Run

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), and the `claude` CLI signed in (the
default agent runs on the Claude subscription, no API key needed).

```bash
cd backend
uv sync                                      # create .venv and install dependencies

# the accountant console (the live prototype)
.venv/bin/uvicorn agl.api:app --port 8137
# open http://127.0.0.1:8137/ and click "Run engine" (it confirms first — it is ~100 LLM calls)

# the eval: cold-vs-warm lift over all 100, (re)writes backend/eval_artifact.json
.venv/bin/python scripts/run_eval.py --agent claude --subset all
```

To drive a hosted model instead of the local CLI, set `AGL_AGENT=llm` and an API key
(`ANTHROPIC_API_KEY` for Claude, or Gemini — see `agl/api.py` `_select_agent`).

## Repository

| Path | What |
|------|------|
| `backend/agl/` | the engine: `engine` (ground → decide → guard → route), `guard`, `agent`, `grounding`, `reconcile`, `learning`, `eval`, `api`, `observability` |
| `backend/ui/` | the no-build static accountant console, served by the same FastAPI app |
| `backend/seeds/` | the dataset: 100 transactions, 10 invoices, 20 bills, a 35-account chart, 5 prior corrections, and ground truth |
| `backend/scripts/run_eval.py` | the eval harness (writes a self-describing artifact) |
| `backend/tests/` | the test suite |
| `backend/eval_artifact.json` | the committed eval result (the numbers above) |
| `data/*.md` | human-readable documentation of the dataset |
| `deliverables/` | **DECK.md** (the deck), **ARCHITECTURE.md** (one-page diagram), **ASSUMPTIONS_AND_TIMELINE.md** |
| `DECISIONS.md` | the design-decision log (why each choice was made) |
| `BRIEF.md` | the original challenge brief |

## Observability

Every decision has a deterministic `GET /trace/{id}` record — the grounded context, the exact prompt,
the raw model proposal, and the guard verdict — rendered in the console's trace drawer. Logfire is
also wired (env-gated to a project-only token via `AGL_LOGFIRE_TOKEN`, off by default, content
scrubbed): it instruments the LLM call and spans the pipeline.
