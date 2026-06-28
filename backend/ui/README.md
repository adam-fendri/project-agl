# Project AGL — Accountant Console (live prototype)

A minimal, no-build accountant console for the Challenge 2 categorization &
reconciliation agent. A single static page (`index.html` + `app.js` + `style.css`)
served by the existing FastAPI app over the endpoints already in `agl/api.py`.

## What it shows

- **Review queue** (left) — the deferred decisions ranked by impact × uncertainty,
  with anomalies pinned to the top. Each row shows vendor, euro amount, outcome,
  and the two independent confidences (account + match).
- **Decision card** (centre) — opens on click: the transaction line, the agent's
  **categorization** (account + reasoning + account-confidence), the
  **reconciliation** match (document ids + reasoning + match-confidence + amount
  status), the **sources** (the grounded/guard confidence signals and documents
  read), and, when present, the **anomaly** with the accountant's next action
  (request the bill / flag the duplicate). Actions: **Accept & post**,
  **Correct** (account dropdown grouped by rubriek, or re-point the match — shows
  "N similar transactions re-run"), **Explain** (on-demand narration).
- **Auto-posted** (tab) — the auto-posted ledger plus anything accepted,
  spot-checkable without re-running.
- **Trace drawer** (right) — `View trace ↗` on any card: the grounded context,
  the exact prompt sent to the model, the raw model proposal, and the guard
  verification.
- **Metrics bar** (top) — auto-posted / in-review / anomaly counts,
  false-confidence count, and categorization / match accuracy from `/metrics`.

## Run

From `backend/`:

```bash
# the default agent is the real Claude CLI (your Claude subscription, no API key)
.venv/bin/uvicorn agl.api:app --port 8137
```

Then open <http://127.0.0.1:8137/>. The page runs the engine on load (`POST /run`),
populates the queue, and is immediately demo-able. Use the **Run engine** button to
re-run.

To drive it against a hosted model instead of the local CLI, set an API key and
`AGL_AGENT=llm` (Claude via `ANTHROPIC_API_KEY`, or Gemini; see `agl/api.py:_select_agent`):

```bash
AGL_AGENT=llm AGL_MODEL=... ANTHROPIC_API_KEY=... .venv/bin/uvicorn agl.api:app --port 8137
```

## How it talks to the backend

The page is a thin client over the live API — no business logic lives in the UI:

| UI action            | Endpoint |
|----------------------|----------|
| load / Run engine    | `POST /run` |
| queue                | `GET /queue` |
| auto-posted          | `GET /posted` |
| metrics bar          | `GET /metrics` |
| Accept & post        | `POST /transaction/{id}/accept` |
| Correct              | `POST /transaction/{id}/correct` |
| Explain              | `POST /transaction/{id}/explain` |
| View trace           | `GET /trace/{id}` |

The agent's decisions are always read from the server. `accounts.json` and
`transactions.json` in this directory are static display snapshots of the
committed seed (the chart of accounts for the correction dropdown, and the
transaction lines for the queue/card header); they carry no decision logic.
