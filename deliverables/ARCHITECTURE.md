# Project AGL — Architecture (one page)

Accountant-supervised categorization + reconciliation for Neno. One principle: **the agent (LLM)
decides; code only grounds and guards.** Every transaction runs one fixed pass — ground → decide →
guard → route — and the strict guard is the floor that holds "never confidently wrong."

```mermaid
flowchart TB
    REPO[("Repository — context in<br/>100 txns · 10 invoices · 20 bills<br/>chart of accounts · provided matches (~96%)")]
    MEM[("Runtime corrections store<br/>accountant conventions, keyed by<br/>canonical vendor — seeds stay read-only")]

    subgraph ENGINE["Engine · single pass per transaction"]
      direction TB
      subgraph G["CODE grounds &nbsp;(deterministic facts)"]
        GROUND["Ground · build_evidence<br/>computes: amount vs gross · direction<br/>open-as-of-booked_on candidates<br/>relevant corrections · vendor history<br/>duplicate-collision note"]
      end
      subgraph A["AGENT decides &nbsp;(one structured LLM call)"]
        DECIDE["Decide · agent.decide<br/>pydantic-ai · temp 0 · Claude Sonnet 4.6 / Gemini 2.5 Pro<br/>Proposal: vendor · account +reason +confidence<br/>match[] +reason +confidence · anomaly?"]
      end
      subgraph V["CODE guards + routes &nbsp;(strict backstop)"]
        GUARD["Guard · run_guard<br/>account in chart? · sums exactly? · direction ok?<br/>same-amount sibling collision? · revenue on settled invoice?<br/>already claimed earlier? · cost-account correction conflict?<br/>missing doc flagged? · fingerprint duplicate?<br/><b>may only DOWNGRADE, never rewrite</b>"]
        ROUTE{"Route · outcome<br/>material × VAT × uncorroborated → review"}
      end
      GROUND --> DECIDE --> GUARD --> ROUTE
    end

    REPO --> GROUND
    MEM --> GROUND

    ROUTE -->|both confidences HIGH<br/>guard passed| AUTO["Auto-posted set<br/>reasoning visible · spot-check only"]
    ROUTE -->|low confidence OR<br/>guard downgraded| QUEUE
    ROUTE -->|anomaly| QUEUE
    ROUTE -->|material doc missing| REQ["Request from entrepreneur"]

    subgraph HUMAN["Accountant console (static web app over the API) · where the human sits"]
      QUEUE["Review queue<br/>ranked: impact × uncertainty<br/>anomalies pinned to top"]
      CARD["Card · choice · reasoning · sources · two confidences<br/>accept &nbsp;·&nbsp; correct &nbsp;·&nbsp; explain (deterministic narration)"]
      QUEUE --> CARD
    end
    AUTO -. spot-check .-> CARD

    CARD -->|correct → apply_correction| MEM
    MEM -->|pending_reruns · re-run same-vendor siblings| GROUND

    DECIDE -. rebuilt on demand .-> OBS["JSON /trace (deterministic) · Logfire (env-gated, project token) · eval<br/>accuracy · false-confidence 1–3 (k=3, all immaterial) · cold→warm lift"]
    GUARD -. .-> OBS
```

**Topology (single-pass).** Each transaction flows `ground → decide → guard → route` exactly once
(`engine.run_batch`, run as a two-pass batch — decide all, resolve `settled_by`, then finalize, so a duplicate is the later claimant regardless of order). No agentic loop: the per-transaction flow is fixed, so we orchestrate it
ourselves and reserve tool-calling for the entrepreneur side. The agent makes one temperature-0
structured-output call (`agent.decide`, via pydantic-ai) and returns a typed `Proposal` carrying
**two** confidences — one for the account, one for the match — because a transaction is two decisions
with different ways to be wrong. The live prototype runs this engine behind a FastAPI JSON API, with a
no-build static **accountant console** (`backend/ui/`, served by the same app) as the client.

**Tool boundary (LLM decides | code grounds + guards).** The three engine bands are the boundary.
**Code grounds** (`grounding.build_evidence`): it computes every verifiable fact — amount vs document
gross, direction, the reconciliation candidates that are still *open as of the transaction's booked
date* (an earlier exact match closes its document, except when a same-amount sibling makes the earlier
match itself suspect), the relevant corrections, vendor history, duplicate collisions — so the agent
decides on facts, not guesses (an LLM is never trusted with arithmetic). **The agent decides** the
account, the match, the anomaly, and its own confidence. **Code guards** (`guard.run_guard`, strict):
before any auto-post it checks the decision against hard facts — account in chart, amount sums exactly,
no same-amount sibling collision with a disagreeing counterparty, an issued invoice's settlement not
re-booked as revenue, the document not already claimed by an earlier transaction, direction correct, no
vendor→cost-account correction contradicted, no material missing document unflagged, no fingerprint of
an earlier identical payment — and may only **downgrade** auto → review/anomaly/request. It never
rewrites the agent's choice. `engine._route` then auto-posts only when both confidences are HIGH **and**
the guard passes **and** the post is corroborated (a material, VAT-sensitive entry whose counterparty
does not corroborate is downgraded to review regardless of self-confidence); everything else defers.

**Where the human sits.** The accountant owns the **review queue** (`Console.queue`), ranked by where
attention is worth most — impact × uncertainty (euro value × VAT-sensitivity × P(wrong)), anomalies
pinned. The confident bulk sits in the **auto-posted set** (`/posted`), reasoning visible,
spot-checkable rather than touched one by one — that untouched bulk is the 30→60 capacity gain. Each
item is a **card**: choice, reasoning, the verified signals as sources, the two confidences, with
**accept / correct / explain**. *Explain is deterministic narration* — a code-built sentence over the
card's own fields (`Console.explain` → `_narrate`), not a second LLM call. A real follow-up model call
is a small, deliberate next step, not something the prototype claims today.

**Where context comes from.** Two sources, both injected into the agent's evidence at ground time: the
**Repository** (transactions, invoices, bills, chart of accounts, the ~96% provided matches) and the
**runtime corrections store** (accountant conventions, keyed by a canonical vendor that is never the raw
IBAN). The committed `seeds/` are read-only; learned corrections are written to a separate runtime store
(`apply_correction`), so a money system never mutates its own fixtures. A `correct` builds a correction
from the vendor the agent already identified, writes it to that store, and **re-runs the pending
same-vendor transactions** (`learning.pending_reruns`) so one edit moves the next ones — closing the
loop back into grounding, with the strict guard backstopping the vendor→cost-account class on any
retrieval miss. Observability has two layers. The **JSON `/trace/{id}` endpoint** reconstructs the full
per-transaction record on demand (grounded context, exact prompt, raw `Proposal`, guard verdict,
confidence signals, final decision) — deterministic, so it never drifts; the console's trace drawer
renders it. And **Logfire is wired** (env-gated to this project's own token, content scrubbed): it
auto-instruments the agent's LLM call (model, tokens, latency, retries), wraps the `claude -p` path in a
span, and spans the pipeline (`run_batch` / `decide` / `finalize`, carrying outcome, guard verdict, and
the two confidences) — off by default, exporting only when a project token is set. The eval reads the
same decision structure to report per-task accuracy, **false-confidence (measured at 1–3 across three
runs on the grounded set — all immaterial; never claimed to be 0)**, and the cold→warm learning lift.
