# Project AGL — Challenge 2 Design

> Accountant-supervised transaction **categorization + reconciliation** for Neno.
> The whole point: an accountant signs off on every entry, and **neither the accountant nor
> the entrepreneur ever sees the AI confidently get it wrong.**

This document is anchored to the case brief and reports **real measured numbers** from the
prototype. Anything not yet built is labelled **Roadmap**. Numbers come from three runs whose
provenance is stated inline so they are never conflated (see [Section 4](#4-the-two-tasks-measured-honestly)).

---

## 1. Goal, problem, the agent's two tasks

**Goal.** An accountant supervising a book of clients can only scale if they stop touching the
routine majority and spend their attention on the few entries that actually need a human. The
agent reads each bank transaction and **auto-posts what it is genuinely sure of** while
**deferring the rest** to a review queue. The accountant signs off; the trust contract is that a
posted entry is right.

**The core problem is not accuracy — it is calibration.** The dangerous failure is not "the agent
was wrong"; it is "the agent was wrong **and sure**," because that is the entry that gets
auto-posted without a human ever looking. So the central capability is the agent **knowing when it
is right versus guessing**, and routing on that self-knowledge: rate a routine entry HIGH and post
it; rate a genuinely ambiguous entry MEDIUM/LOW and send it to a human *before* posting. Deferring
an ambiguous entry is the **correct** outcome, not a failure.

**Per bank transaction the agent makes two independent decisions and rates calibrated confidence on
each:**

1. **Categorize** — the one chart-of-accounts number the transaction belongs to. This drives VAT
   and the financial statements, so it must be right. The bulk is routine (subscriptions, payroll,
   rent, taxes, recognisable supplier costs map straight from the description); the tail is genuine
   ambiguity (asset-vs-supplies near the capitalisation line, business-cost-vs-owner-draw,
   payroll-vs-contractor, two adjacent cost categories) where judgement and prior corrections carry
   it.
2. **Reconcile** — whether, and which, open invoice or bill this transaction settles. Matches arrive
   **provided at ~96%** from Neno's infra, so the agent's job is **verify-first**: confirm the
   provided match, catch the ~4% that is wrong, and only search from scratch for the genuinely
   wrong/incomplete/missing ones (a same-amount collision, a one-payment-clears-two combination, a
   short-pay). **Reconciliation is the harder task** — the bank line is a messy string, two
   documents can share an amount, and the arithmetic must be exact.

They are **two decisions, not one** — different evidence, different ways to be wrong — so the agent
emits **two confidences**, and an entry auto-posts only when **both** are HIGH. The card headline is
the **weaker** of the two with reasoning that names which part is shaky.

**Also required by the brief, and built:** flag **anomalies** (duplicate / missing counterpart /
suspicious vendor / unusual amount); when material evidence is missing, **request the document**
from the entrepreneur rather than guess; route everything uncertain to **human review before
posting**.

**The number that kills trust is false-confidence** — auto-posted *and* wrong. Target: **zero**,
measured **per task** so we know which decision is the weak link.

---

## 2. Architecture: the agent decides, code grounds and guards

One principle runs through everything:

```
            ┌──────────────────────── per transaction ────────────────────────┐
            │                                                                  │
  seeds ──► GROUND (code) ──► DECIDE (agent, ONE call) ──► GUARD (code) ──► ROUTE (code)
            facts in            account + match +           downgrade-only       auto-post |
            evidence out        anomaly + 2 confidences     hard-fact backstop   review | anomaly |
            (no guesses)        (the agent decides)         (never rewrites)     request-document
```

- **The agent (the LLM) decides** — the account, the match, the anomaly, and **its own
  confidence** on each. One temperature-0 structured-output call per transaction
  (`agl/agent.py`, `Proposal` in `agl/models.py`). No agent loop, no tool-calling: the
  per-transaction flow is fixed, not agentic.
- **Code grounds** — `build_evidence` (`agl/grounding.py`) assembles the agent's evidence: the
  transaction, the chart of accounts, the provided match plus reconciliation candidates with their
  **computed facts** (amount vs document total, direction, paid/unpaid status), any document ids the
  remittance literally quotes, the relevant corrections (general always, vendor-specific filtered),
  and vendor history. Code does the **exact arithmetic** an LLM cannot be trusted with; the agent
  reads facts, not raw rows.
- **Code guards** — before any auto-post, `run_guard` (`agl/guard.py`) checks the proposal against
  hard facts: the account exists; the matched amount **sums exactly** (else partial); direction is
  right; a quoted document reference is honoured; a same-amount sibling whose counterparty disagrees
  isn't silently picked (collision); an issued invoice settlement isn't re-booked as revenue; the
  document isn't already claimed by an earlier transaction (duplicate); no prior correction is
  contradicted; no material missing document is unflagged; no earlier same-amount/same-vendor payment
  looks like a double-pay. **Any failure downgrades to review — it never rewrites the agent's
  choice.** The guard can only make the system *more* cautious, never silently "fix" a decision and
  post it.
- **The accountant console** (`agl/api.py` + `ui/`) — a **review queue ranked by where attention is
  worth most** (euro amount × VAT-sensitivity × uncertainty, anomalies pinned to the top), the
  **auto-posted set** sitting with reasoning visible for spot-checking (the untouched bulk is the
  capacity gain), and a **decision card** per entry: the agent's choice, its reasoning, the verified
  sources, the two confidences. Actions: **accept** (post), **correct** (a dropdown — pick the right
  account or re-point the match, no coding), **explain** (a deterministic code-built narration),
  and on anomaly cards a **next action** (flag the duplicate / request the bill).
- **The learning loop** — the accountant corrects a card; the system keys the correction on the
  vendor *the agent already identified* (`apply_correction`, `agl/learning.py`), persists it to a
  **runtime store kept strictly separate from the read-only seeds** (`agl/repository.py`), pulls it
  into future evidence, and **re-runs the pending same-vendor siblings** so they flip immediately
  ("N similar updated"). One correction moves the whole cohort; the guard backstops any miss.

---

## 3. How false-confidence is held to zero

Two decisions, so two mechanisms — one per task, each measured separately.

**Categorization: calibrated agent confidence (prompt-engineered).** Confidence is the *agent's*,
but the prompt is engineered so HIGH means "the evidence settles a single answer," not "I have an
answer." The system prompt (`agl/agent.py`) follows Anthropic's prompt-engineering guidance for
Sonnet 4.6:

- **Dialed-back emphatic language.** No "be confident" / "rate HIGH" pressure. Instead: *"HIGH is
  earned by the evidence, not assumed."*
- **Explicit permission to defer.** *"Sending an ambiguous entry on for review is the correct
  result, not a failure"*; *"MEDIUM or LOW is the correct, expected result."* Deferral is framed as
  success, removing the model's bias to resolve every case.
- **Evidence-before-confidence.** *"Name the evidence that fixes each rating; if you cannot name
  evidence that rules the alternatives out, it is not HIGH,"* plus a closing self-check. The model
  must justify HIGH against the alternatives before it may claim it.
- **Diverse examples** spanning HIGH/MEDIUM/LOW across *both* tasks, so the model sees ambiguity
  rated MEDIUM as often as it sees a clean case rated HIGH.

**Reconciliation: the hard-fact guard.** Matches are arithmetic, and arithmetic is verifiable, so
confidence here rests on code, not vibes. `validate_match` (`agl/reconcile.py`) recomputes the sum
and direction; the guard refuses to auto-post a match that doesn't sum exactly, points the wrong
direction, contradicts a quoted reference, or sits on an unresolved same-amount collision. This is
why reconciliation false-confidence is the easier zero to hold.

### Plan evolution (documented honestly)

The original plan (`PLAN.md`, `DECISIONS.md`) specified **code-computed confidence plus
self-consistency** (sample the categorization N times, treat agreement as confidence). On reading
the actual prompt before building that, we found the miscalibration was **authored into the prompt
itself**: an emphatic, rate-HIGH instruction that overtriggers Sonnet 4.6 into rating almost
everything HIGH. The evidence was unambiguous — the **baseline run auto-posted 94/100 with 0
reviews and 5 false-confidence** (Section 4). A model told to be confident will be confident.

So we fixed it **prompt-first** — the four changes above — which is the cheaper, more honest fix:
the defect was in the instruction, so it belongs in the instruction, not behind a code wrapper that
papers over a prompt that still says the wrong thing. **Self-consistency remains documented as a
real-data backstop** (Roadmap, Section 6): on production data where prompt calibration alone proves
insufficient, an N-sample categorization vote is the next lever. We did not build it because the
prompt fix moved the number it was meant to move.

---

## 4. The two tasks, measured honestly

Three runs, distinct provenance, never conflated:

| Run | What | Scope | Source |
|-----|------|-------|--------|
| **A — Baseline** | before the calibration fix (emphatic prompt) | full 100 | task-provided |
| **B — After fix** | the calibrated prompt | targeted **29-transaction** hard-case subset, **one non-deterministic run** | task-provided |
| **C — Lift artifact** | learning lift, separate full run | full 100, `claude-sonnet-4-6`, 2026-06-28 | `eval_artifact.json` |

Metrics are split by task on purpose: **categorization accuracy over all rows**, **reconciliation
accuracy over document-settling rows only** (25 of the 100 ground-truth entries settle a document;
scoring "empty == empty" on the other 75 would flatter the number), and **false-confidence per
task**.

### A → B: the calibration fix

| Metric | A: Baseline (full-100) | B: After fix (29-subset, 1 run) |
|---|---|---|
| Categorization accuracy | **0.94** | **0.793** (23/29) |
| Reconciliation accuracy (docs-only) | — | **1.00** |
| **False-confidence — total** | **5** | **2** |
| &nbsp;&nbsp;· categorization | 5 | 2 (`T081` 4730 vs GT 4900; `T082` 4410 vs GT 4500) |
| &nbsp;&nbsp;· reconciliation | 0 | **0** |
| Reviews (deferred to human) | **0** | **7** (`T010,T030,T036,T037,T046,T048,T075`) |
| Routing | 94 auto / 0 review / 3 anomaly / 3 request | 16 auto / 7 review / 4 anomaly / 2 request |

**Read this correctly.** The 0.94 → 0.793 is **not a regression**. B runs a deliberately
hard-case-enriched 29-transaction subset, and the calibration now pulls the genuinely ambiguous
cases out into review instead of auto-posting them — that is the design working. The clear routine
cases still flow straight through (`T001/T003/T006/T007/T008/T009/T019` auto-post). The signal that
matters:

- **Reviews went 0 → 7.** Before, nothing was ever deferred — the system had no notion of "I'm not
  sure." Now genuinely ambiguous cases reach a human first.
- **False-confidence dropped 5 → 2**, and the two residuals are **categorization-only, near-miss
  account picks** (4730 vs 4900; 4410 vs 4500 — adjacent cost accounts), not reconciliation errors
  and not wild misclassifications.
- **Reconciliation false-confidence held at 0** on both runs — the hard-fact guard does its job.

**Honest caveats.** Target is zero false-confidence; on the hard subset we are at **2, not 0** — the
adjacent-cost-account confusions are the open edge. This is **one non-deterministic subset run**;
the calibration figure needs N-run stability before it is a rate rather than a reading. And the
**anomaly gate over-fires**: **4 predicted vs 1 expected** on B (the run's own verdict flags
duplicate false-positives), so the missing-counterpart / duplicate routing is too eager and is the
next thing to tighten.

### C: the learning lift (mechanism proof)

From `eval_artifact.json` (full-100, `claude-sonnet-4-6`, 2026-06-28), on the **9 rows a correction
actually moved**:

- fully-correct (account **and** match) **cold 0.33 → warm 0.56 = +0.22**;
- full-100 categorization **cold 0.89 → warm 0.91**;
- **5 rows flipped to correct** (`T016,T043,T075,T079,T084`), **3 regressed** (`T026,T037,T093`),
  1 stayed wrong (`T049`) — a **net +2/9**.

This is an **honest, not clean, win**: the loop demonstrably moves siblings in the right direction,
and it occasionally over-generalises — which is exactly why the **guard backstops every correction**
and why the cohort re-run is shown to the accountant rather than applied silently. The lift proves
the **mechanism**; on synthetic data with our own labels it is not a production-calibrated rate.

---

## 5. Tooling rationale (one line each)

- **Model** — Claude **Sonnet 4.6** for the agent (configured `anthropic:claude-sonnet-4-6`, or the
  local `claude -p` CLI), **Gemini 2.5 Pro fallback** (`google:gemini-2.5-pro`), selected by
  environment; a frontier model because the failure mode is judgement under ambiguity, and the eval
  is the place to later test whether a cheaper model holds the accuracy.
- **Orchestration** — our own **deterministic per-transaction pipeline** (`ground → decide → guard →
  route`) with **one pydantic-ai structured-output call** per transaction; **no agent framework**,
  because the flow is fixed, not an agentic loop, and a framework would add ceremony and
  non-determinism for nothing.
- **Retrieval / context** — **direct grounding from the customer's own data** (chart of accounts,
  open documents, corrections, vendor history) assembled into the prompt; **no vector RAG** — at one
  SMB's scale the relevant set is small and exactly selectable by id/vendor, so exact selection beats
  approximate similarity and removes a moving part (general corrections always included,
  vendor-specific ones filtered by vendor).
- **Evals** — `agl/eval.py`: per-task accuracy (categorization all-rows, reconciliation docs-only),
  **per-task false-confidence** gated at zero, per-outcome routing precision/recall, and a
  **cold-vs-warm learning lift** harness, all written to a model-id-and-date-stamped artifact by
  `scripts/run_eval.py`.
- **Observability** — a deterministic **per-transaction trace** (`GET /trace/{id}`) reconstructs the
  full record — grounded context, exact prompt, raw model proposal, guard verdict, confidence
  signals, decision — rendered in the console's trace drawer and read by the eval from the same
  structure.

---

## 6. Roadmap (what it takes to make this real)

The prototype proves the architecture and holds reconciliation false-confidence at zero on the set.
The brief's guiding question — *what would it take to run this for real?* — breaks into four tracks.
Timelines and resources below are estimates for a small team (1–2 engineers) and are explicitly not
measured.

**1. Production backbone (~4–6 weeks).** Replace JSON seeds + the runtime corrections file with
**Postgres** (transactions, documents, corrections, decisions, the posted ledger); add **auth** and
a tamper-evident **audit log** (every auto-post, correction, and override, who and when — non-
negotiable for a money system); expose the agent path as a **versioned API** for Neno's pipeline to
call per transaction; and turn the threaded-but-single-tenant `customer_id` into real
**multi-tenancy** with per-tenant isolation. **Wire Logfire** — the dependency is already declared
in `pyproject.toml` but unwired; production observability is one span per transaction carrying the
trace payload the prototype already builds.

**2. Real-data calibration hardening (~3–4 weeks).** Stabilise the calibration over **N runs** (the
current B figure is one non-deterministic subset run); **build the documented self-consistency
backstop** (N-sample categorization vote) for the cases prompt calibration alone does not settle;
**fix the anomaly over-fire** (4 predicted vs 1 expected) — tighten the missing-counterpart /
duplicate gates and de-duplicate the false positives; and drive the two residual adjacent-cost-
account false-confidences toward zero. Move **materiality from a hardcoded €1000 threshold**
(`engine.py`) to **per-customer config**, alongside the duplicate-window and amount-tolerance
heuristics.

**3. The VAT dimension (~2–3 weeks).** The chart already carries `rubriek` (4 = costs, 8 = revenue)
and documents carry `vat`, so the categorization decision **already determines** the VAT treatment;
what is not built is the **VAT-return / box mapping and reconciliation** on top of the posted
account. This is the natural next deliverable once accounts post reliably, and the place where a
wrong category becomes a wrong tax filing — so it inherits the same false-confidence discipline.

**4. Separate the eval harness from the runtime (~1 week).** Today ground truth and the eval live
alongside the service. In production the **eval harness is a CI/offline gate** (run on every prompt
or model change, fail the build if per-task false-confidence rises), not code shipped in the request
path. Likewise the deterministic `explain` narration is a first step; a **real LLM follow-up call**
for accountant Q&A on a decision is the planned upgrade.

---

### Appendix: built vs roadmap at a glance

**Built** — per-transaction `ground → decide → guard → route` pipeline; calibrated single
structured-output call (Sonnet 4.6 / CLI / Gemini fallback); downgrade-only hard-fact guard
(collision, duplicate, revenue-on-settled, correction-conflict, reference, direction, sum,
missing-doc, fingerprint double-pay); attention-ranked review queue; accept / correct / explain /
trace; learning loop with cohort re-run and read-only-seed isolation; FastAPI console + no-build UI;
per-task eval harness with cold-vs-warm lift and a stamped artifact.

**Roadmap** — Postgres + auth + audit log + multi-tenancy + API agent path; Logfire wiring;
N-run-stable calibration + self-consistency backstop; anomaly-gate fix; materiality/heuristics from
config; the VAT return/box dimension; eval-harness/runtime separation; real LLM follow-up explain.
