# AGL Challenge 2 — Consolidated Lead Review

Reviewed against `BRIEF.md`. Findings are grounded in the committed code and verified by running the eval, rendering prompts, and grepping call sites. Eight dimension reviews consolidated, deduplicated, ranked by judging impact.

Verification run (default offline path, `MockAgent`, customer `studio-vondel`, all 100 txns):
`false_confidence_count = 2 · auto_post = 25 · review = 74 · anomaly = 1 · categorization_accuracy = 0.49 · match_accuracy = 0.96`.

---

## 1. VERDICT

The thinking is senior and the skeleton is the right shape — `ground -> decide -> guard -> route`, code owns the arithmetic, the LLM owns the semantics, two independent confidences (account vs match), a downgrade-only guard, an impact x uncertainty queue, and a genuinely good one-page architecture diagram. But the written deliverables run well ahead of the prototype: they present a React console, a "separate LLM call" to explain, a "done" Logfire observability layer, an "84% -> 92%" learning lift, and "false-confidence held at zero" — and **not one of those five is true in the code**. The runnable system has no UI at all, emits no Logfire span, computes no lift (the function is dead code), narrates `explain` with an f-string, and auto-posts two confidently-wrong EUR 7,260 entries. Worse, the single grounding bug that produces those two bad posts (the candidate search hides every "paid" document) makes the four flagship reconciliation cases the candidate built the dataset around structurally unsolvable.

**Single biggest risk to the interview:** the credibility gap. A reviewer who reads the polished deck and then runs the code finds the headline numbers unproduced, the headline tooling defence (observability) unbuilt, the named trust target (false-confidence = 0) empirically false, and the marquee reconciliation demo unsolvable by design. In a take-home for an *agentic general ledger handling real financial data*, "the narrative asserts what the system does not do" is the failure mode that reads as not-shippable and not-trustworthy — exactly the thing the brief says kills trust.

---

## 2. CRITICAL ISSUES (ranked by judging impact)

### C1 — No live prototype UI; the headline deliverable does not exist
- **Where:** No frontend anywhere (no `package.json`, `*.tsx/jsx/html`, `static/`, `templates/`, `StaticFiles`, `HTMLResponse`). Only the FastAPI JSON API in `backend/agl/api.py`. No README / run instructions in the tree. The candidate's own `DECISIONS.md` (D8) and `PLAN.md:97-99` specify a "React + Vite" client that was never built; `ASSUMPTIONS_AND_TIMELINE.md:197-198` lists the React client under "what exists today."
- **Fails:** brief Deliverables ("A live prototype... a Claude project or simple web app... user interactions and agentic workflow should be visible") and Demo ("one anomaly + what the accountant clicks next" — there is nothing to click).
- **Fix:** build a minimal queue/card page (queue -> card with choice/reasoning/sources/two-confidences -> accept/correct/explain -> trace drawer) over the existing endpoints, even a single static HTML file; add a README with run steps. Or, if time forbids, state plainly in the deliverables that the prototype is API-only and stop listing a React client as built.
- **Dimensions:** Execution, Prioritization (end users), Communication, Demo.

### C2 — The reconciliation candidate search hides every "paid" document, so the four engineered hard cases are structurally unsolvable
- **Where:** `reconcile.py:52-54` builds `open_docs` as `[... if id not in settled]`; `grounding.py:120-123` (`_settled_ids`) defines `settled` as final `status == PAID`. `find_candidates` and its combination branch (`reconcile.py:71-96`) iterate only `open_docs`. The agent is told "never invent a document... not listed here" (`grounding.py:81-83`). Verified: T072 (`SEPA OVB VOSS & PARTNERS INV-2026-004`, GT `INV-2026-004`, paid) -> candidates `[]`; T074 (Lumen, GT `INV-2026-005`, paid) -> `[]`; T076 (split, GT `INV-006+INV-007`, both paid) -> `[]`. `sample_context_T072.txt:91-92` confirms "none found among open documents." Root cause: document `status` conflates "paid before the feed" with "paid by this very transaction" — there is no temporal/as-of-date model (`models.py:90-114` has no `settled_on`).
- **Fails:** brief decision (1) "whether it matches an open invoice"; the precision bar for reconciliation; and the deck's flagship "catch the 4% that are wrong... search the other candidates" (`DECK.md:53`). The correct answer is unreachable on the exact cases built to prove the skill.
- **Fix:** include same-amount / same-counterparty documents in the candidate set regardless of paid status (render status as a fact — a paid doc already claimed by another txn is itself the signal), or model "open as of `txn.booked_on`" by replaying earlier matched transactions. Add a `find_candidates` reachability test for T072/T074/T076 (none exists).
- **Dimensions:** Strategic Thinking (precision bar), Technical Depth (reconciliation, context engineering), Execution.

### C3 — The named trust target is empirically false: false-confidence = 2, not 0, and the guard cannot see the failure mode that causes it
- **Where:** Deck/diagram stake the product on "false confidence... Target: zero on the set" (`DECK.md:63,97-100`), "held at 0" (`ARCHITECTURE.md:45,80`). The runnable eval reports **2** (T072, T074 auto-posted with the wrong provided match, both EUR 7,260 VAT-relevant). The guard's match checks are `direction_ok` and `sums_exactly` only (`guard.py:43-54`); a same-amount collision (INV-2026-004 / INV-2026-005 both 7,260) sums exactly and direction is right, so `passed=True`. Correction C5 ("disambiguate same-amount by counterparty") is shown to the model but not enforced by the guard. Confidence is pure LLM self-rating (`agent.py:58-63`, `models.py:164-176`) with no grounding-signal floor; consequence (euro x VAT) enters only queue *ranking* (`api.py:135-144`), never the post/defer gate (`engine.py:114-116`). Note `MatchVerdict.all_open` (`reconcile.py:28,130`) is computed but **never read** (the deck's advertised "already-paid" guard check is dead code; both call sites pass `settled=set()` at `guard.py:50`, `engine.py:94`).
- **Fails:** brief "Correctness vs false-confidence... name your target and how you hold it." The system *measures* it honestly (`eval.py:54-58`) but does not *hold* it, and no test gates it.
- **Fix:** add a guard ambiguity check — if another known document shares the matched amount and the chosen counterparty does not corroborate, downgrade to review or cap `match_confidence`; fold consequence (euro x VAT-weight) into the auto-post gate so high-value items need corroboration, not just self-HIGH; add a regression assertion `false_confidence_count == 0`. Restate "held at zero" honestly until true (the guard catches fact-contradicting errors; semantically-wrong-but-arithmetically-valid is caught only by the confidence gate + post-hoc eval).
- **Dimensions:** Strategic Thinking, Execution (safe for financial data), Technical Depth (evals).

### C4 — The headline learning lift "84 -> 92" is produced by zero runnable code; `lift_report` is dead code
- **Where:** `eval.py:93-104` `lift_report` is the only thing computing `cold_accuracy`/`corrected_accuracy`/`lift`, and it has **no callers** (verified: only its definition matches). `/metrics` (`api.py:217`) calls `run_eval`, leaving those fields `None`. Yet "84% cold -> 92%" is headlined as a measured result in `DECK.md:99`, `ARCHITECTURE.md:45,80`, `PLAN.md:81`, `ASSUMPTIONS_AND_TIMELINE.md:179`, `DECISIONS.md:176`. The only reproducible run (MockAgent) yields categorization 0.49. "84" also equals the GT auto-post label count (84/14/2), suggesting conflation.
- **Fails:** bonus "running a real eval on the seeded data and reporting numbers"; learning-speed criterion ("one correction moves the next 10").
- **Fix:** wire a two-run lift path (run batch with corrections suppressed, then applied, call `lift_report`, commit the JSON output) against a real LLM; report actual numbers with model id + date. Until then, mark 84->92 as a *target*, not a result, everywhere, and fix the `/metrics` docstring. Also measure lift on a held-out / next-N set, not in-sample, to substantiate "moves the next 10."
- **Dimensions:** Technical Depth (evaluation), Communication (asserting unproduced numbers).

### C5 — The observability tooling defence (1 of the 5 the brief requires) is fabricated; no Logfire exists
- **Where:** `grep logfire backend/agl/*.py` returns nothing. `logfire>=2.6` is in `pyproject.toml` but never imported or configured. Deliverables claim "one Logfire span per transaction... done" (`ASSUMPTIONS_AND_TIMELINE.md:200`), "Logfire, one span per transaction... exposed at `/trace/{id}`" (`DECK.md:110`, `ARCHITECTURE.md:78-80`), "automatic Logfire tracing `instrument_pydantic_ai`" (`DECISIONS.md` D4/D9). `/trace/{id}` (`api.py:295-298`) just rebuilds a `Trace` pydantic object on demand — it emits no span and is not a clickable trace view.
- **Fails:** brief Tooling ("Observability — how you enable yourself to debug your agentic flows") and bonus "trace/observability view... with a clickable example."
- **Fix:** wire Logfire for real (`logfire.configure()` + `instrument_pydantic_ai()` + one span/txn), or rewrite the observability defence to describe the JSON `/trace` endpoint as the only artifact and stop calling it "Logfire"/"done."
- **Dimensions:** Technical Depth (observability), Execution, Communication.

### C6 — The learning loop contaminates the committed seed and the only repeatable path generalizes to nothing
- **Where:** `learning.py:49,96-98` `_persist` writes back to `SEEDS/corrections.json` (`learning.py:10`) — the same git-tracked fixture `Repository` loads (`repository.py:31`). Reviewers observed a 6th correction (C6) persisted from a single demo correction, keyed on T068's raw IBAN counterparty `NL44INGB0E64DCC676` (`learning.py:26` keys on `vendor or txn.counterparty`), which generalizes to zero future transactions and duplicates C2. (The file is currently restored to 5, but the mutating behavior is the defect.) On the default offline path, `MockAgent` sets `vendor = transaction.counterparty` (IBAN noise) and never reads `evidence.corrections`, so a correction reruns `[]` siblings — the CI/testable path demonstrates the *opposite* of "one correction moves the next 10." `_select_agent` returns `MockAgent` whenever no LLM key is set (`api.py:58-66`).
- **Fails:** brief learning-speed outcome; brief "5 prior accountant corrections" (the seed mutates); Execution (a money system must not mutate a committed fixture as runtime state).
- **Fix:** write learned corrections to a separate runtime store (the stated Postgres target), keep `seeds/` read-only; extract a canonical vendor key (never the raw counterparty/IBAN) shared by selection, injection, and guard; make the mock consult corrections so the mechanism is demonstrable offline; dedupe against existing rules.
- **Dimensions:** Technical Depth (learning, RAG/context), Execution.

---

## 3. MAJOR ISSUES

### M1 — "Ask the agent to explain" is sold as a separate LLM call; it is an f-string
`explain` (`api.py:212-214`) is a sync method returning `_narrate(decision)` (`api.py:114-132`), pure string concatenation of fields already on the card — no `await`, no agent, no model. Claimed as "a separate on-demand LLM call that narrates the decision" in `DECK.md:87`, `ARCHITECTURE.md:70`, `ASSUMPTIONS_AND_TIMELINE.md:124-125`. Fails brief action "ask the agent to explain." Fix: route through the agent as a real follow-up call, or relabel everywhere as deterministic narration. (Execution, Communication.)

### M2 — The prompt leaks the benchmark's accuracy ("~96% / catch the 4%")
`agent.py:42-44` ("about 96 percent accuracy... Catch the roughly 4 percent that are wrong") and `grounding.py:316` ("~96% accurate"). This is an eval-set statistic baked into a production prompt; "catch the 4%" instructs the model to expect a wrong match and go hunting, biasing toward over-flagging the 96% that are correct — raising false-confidence in the anomaly direction. The deck frames it purely as a strength (`DECK.md:53`). Fix: "treat the provided match as a strong but fallible prior; verify counterparty and amount" with no number and no quota. (Strategic Thinking re data-quality assumptions, Technical Depth context engineering.)

### M3 — Triple-stacked, overlapping instruction blocks on the live path
The live `LlmAgent` (`api.py:59-66`) sends three restatements of persona/produce-list/confidence rubric: `agent.py:_SYSTEM_PROMPT` (system), `grounding.py:_INSTRUCTIONS` (prepended to the user message at `grounding.py:59`), and the `Proposal` field descriptions (`models.py:157-179`). They even frame the task differently ("Decide three things" vs "Produce: 1..4"). Dilutes attention, the opposite of tight context engineering. Fix: one instruction surface — keep the system prompt, delete `_INSTRUCTIONS`, let schema field descriptions carry output shape. (Technical Depth.)

### M4 — Decision #4 ("request a missing document, and when") is mis-wired, uncovered, and has no timing
Only trigger is the LLM emitting `MISSING_COUNTERPART`, routed to `REQUEST_DOCUMENT` (`engine.py:111-112`, `guard.py:62-63`). But the genuine case, T049, is labelled `anomaly` in `ground_truth.json` (not `request_document`), so the eval scores a correct request as an anomaly miss. There are **zero** `request_document` rows in GT (outcomes are auto_post/review/anomaly only), so an entire brief decision is unscored. No aging/timing logic and no entrepreneur-facing message exists. No API action to send a request. Fix: separate `missing_counterpart` (defer) from a deliberate `request_document` outcome with an aging trigger and a generated ask; label T049 (+1-2 more) in GT; score request precision/recall; add the action endpoint. (Strategic Thinking, Prioritization re entrepreneur, Evals.)

### M5 — Inflow account convention (8000 Omzet) is inconsistent with the accrual receivable model the candidate also built
GT books every invoice-settling inflow to 8000 Omzet (revenue); 1300 Debiteuren is never used, despite the chart defining it (`chart_of_accounts.md:36,70`) and tracking invoice paid/unpaid (an accrual world where a customer payment clears the receivable Dr 1100 / Cr 1300, not re-recognize revenue). Booking settlements to 8000 double-counts Q1 omzet and output BTW — directly the VAT/audit precision bar. `DECISIONS.md`/`PLAN.md` never address it. Fix: book settlements to 1300, or document the cash-basis assumption and drop the receivable model. (Strategic Thinking precision bar, Execution.)

### M6 — Queue ranking buries the highest-value class (guard-caught "sure and wrong")
`_rank_key` (`api.py:135-144`) proxies uncertainty from the agent's *own* confidence and ignores `verdict.failed_checks` entirely. A HIGH/HIGH item the guard caught ranks below an agent-low/low item at equal euro. The brief's trust number is "sure and wrong"; that exact near-miss is where attention adds most value, and the ranking sends it to the bottom because it trusts the confidence that just proved unreliable. Fix: fold guard downgrades / `failed_checks` into the uncertainty term. (Prioritization, Strategic Thinking.)

### M7 — "Exact-rule guard backstops every correction" is false for 3 of 5
`guard._correction_conflict` (`guard.py:102-115`) only fires when the corrected account is in the COSTS rubriek (`guard.py:111`). C3 (0150 asset), C4 (0600 owner-draw), C5 (match re-point, `corrected_account=None`) are never guard-enforced. C4 specifically: if the LLM ignores the owner-draw convention at high confidence, it auto-posts wrong with no backstop. The blanket claim appears in `DECK.md:75`, `PLAN.md:64-66`, `DECISIONS.md:62`, `ARCHITECTURE.md:21`. Fix: scope the claim to vendor->cost-account corrections, or implement condition-aware enforcement. (Technical Depth, Communication.)

### M8 — The brief's explicit "minutes saved per customer per month" is never quantified
Every capacity reference is qualitative (`DECK.md:118-121`, `ASSUMPTIONS_AND_TIMELINE.md:179-181`, `PLAN.md:111`). The brief asks verbatim for the figure "in minutes saved per customer per month" and "which workflow steps deliver the largest cuts." Fix: put a worked figure on a slide (baseline min/txn x txns/customer/month x auto-rate; size the auto-post step vs the queue-ranking step separately). (Strategic Thinking, Communication.)

### M9 — Provided-match accuracy is ~86% on the matched set, not the brief's ~96%
28 provided matches, 4 imperfect at the doc-id-set level (T046, T072, T074, T076) = 24/28 = 85.7% precision. `matches.md:10-14` reaches "96%" only by counting the 72 no-match transactions as true negatives, but `provided_matches.json` asserts no negatives. The agent actually faces a ~14% error rate on matches it is given. Fix: add correct matches to hit ~96%, or restate honestly as "~86% precision on proposed matches (4 planted failure modes)." (Strategic Thinking re data-quality assumptions.)

### M10 — General corrections injected as "binding conventions" on every transaction
`_relevant_corrections` (`grounding.py:183-191`) unconditionally includes empty-vendor corrections; `_render_corrections` labels them "binding conventions" under "apply every applicable correction below" (`grounding.py:97`). Verified: C3 (hardware >= EUR450 -> asset) appears on a EUR 7,260 client-invoice inflow and a EUR 78.50 cafe payment. Context pollution presented as binding, with no cap/recency/relevance ranking — the brief's RAG expectation met only as substring filtering. Fix: gate general corrections by applicability, or label them "general policies" distinct from vendor-bound conventions. (Technical Depth context/RAG.)

### M11 — No auth, no audit trail, single global console; `correct` mutates committed seed
The console is one module-global singleton (`api.py:250`) with no auth/session (grep finds none). `accept` only adds to an in-memory set lost on `/run` (`api.py:185-188`); `correct` persists to the tracked seed (see C6). A money system needs auth + an immutable audit record of who accepted/corrected. Fix: per-customer runtime store + auth + audit log. (Execution: safe for real financial data.)

---

## 4. MINOR / POLISH

- **Counterparty agreement (the load-bearing W2 signal) is not a computed fact** — grounding computes amount-gap/direction/paid (`grounding.py:283-312`) but no token-overlap "party agrees/mismatch"; the single most decision-relevant check is left to LLM eyeballing of free text (T072's counterparty is an IBAN with the name buried in `description`). The code already has `_vendor_matches_raw` to reuse.
- **Editorializing evidence labels** — "verify before trusting" (`grounding.py:316`), "(possible short-pay)", "DIRECTION MISMATCH", "may be a duplicate payment" pre-judge rather than present fact + threshold.
- **Dead/diverging prompt surfaces** — `_JSON_INSTRUCTION`/`_extract_json` exist only in `ClaudeCliAgent` (`agent.py:144-187`), never constructed by `api.py`/`eval.py`; the committed `sample_context_T072.txt` was generated from a different surface than the live path renders.
- **MockAgent match-accuracy 0.96 is circular** — the mock copies the provided match, so it re-measures "96 of 100 provided == GT."
- **Review-gate precision/recall unscored** — `run_eval` scores anomaly catch/false-positive but never REVIEW correctness, so over-deferral (74/100 on the mock) is invisible.
- **Duplicate detection keys only on shared provided doc-id** (`engine.py:51-58`) — a real un-matched duplicate (same counterparty/amount/date-window, no shared id) is invisible.
- **GT cannot represent cold vs warm** — corrections are always in the evidence but GT encodes cold labels; an agent obeying corrections is scored wrong on the 8 review->auto rows. Ship two label sets or per-row cold/warm expectations.
- **W3 short-pay not representable in `ProvidedMatch`** — model has only `transaction_id`+`document_id`, no claimed-settlement/fullness field; the "marked paid in full" wrongness exists only as a recomputed gap.
- **All 20 bills `paid`** — no open accounts payable, diverges from "some were already paid" and is unrealistic for an 8-FTE studio.
- **Counterparty truncation artifacts** ("KASA TECH .", "BRIGHTSEED .").
- **`learning.py:81` couples production learning to `repo.ground_truth()`** (the eval label file) as a transaction index — would break in prod where the file is absent.
- **`DECK.md:88` lists wrong endpoint paths** (`/accept` vs `/transaction/{id}/accept`) — a reader following the deck hits 404s.
- **No `GET /posted`** — the auto-posted bulk is only visible by re-running `/run` (which clears `_posted`), contradicting "spot-checkable."
- **Deck is markdown, not the brief's PDF deck / 7-min video** — the actual screen-share artifact is absent.
- **`pytest` not installed in the project `.venv`** — the suite does not run as delivered.

---

## 5. GENUINE STRENGTHS (keep and showcase)

- **The architecture is the right shape and well-defended.** Single-pass `ground -> decide -> guard -> route` (`engine.py:28-38`); the guard can only *downgrade* severity, never rewrite the agent's account/match (`engine.py:20-25,101-105`) — a sound human-supervised, fail-safe topology. "Strict is the floor, not a dial" holds for the checks that exist.
- **Arithmetic is offloaded to code, not the LLM** (`reconcile.py`, `grounding.py:283-312`): gap, direction, paid/unpaid, combination-sum are computed; the prompt tells the model to trust those numbers and judge only semantics. Correct context engineering for a money system.
- **Two independent confidences (account vs match)** (`models.py:164-176`) directly serve the reconciliation-precision and false-confidence goals; auto-post requiring *both* HIGH is appropriately conservative.
- **The Decision card is exactly the brief's card** (`models.py:224-240`): choice, reasoning, sources + confidence_signals, two confidences. The `/trace/{id}` route (`api.py:295-298`, `Trace` `models.py:251-260`) is a real, clean bonus artifact (context + prompt + raw Proposal + verdict + decision).
- **False-confidence is correctly defined and honestly measured** (`eval.py:54-58`: auto_post AND (account or match wrong)); the harness *did* surface the two real failures (T072/T074). The synthetic-data caveat is explicit (`DECK.md:100`).
- **The seed data is genuinely realistic and arithmetically exact.** `build_seeds.harden()` renders the same vendor as different strings across SEPA/iDEAL/card formats; the four hard reconciliation cases (collision, split, short-pay, duplicate) are exact (INV-006 2,165.90 + INV-007 1,210 = T076 3,375.90); VAT realism is a standout (insurance exempt, NS travel 9%, export 0%). The bug is in the grounding plumbing, not the scenario design.
- **The strategic framing and the one-page diagram are senior.** The diagram meets all four brief requirements (topology, tool boundary, where the human sits, where context comes from); the five tooling defences reason rather than name-drop; the batch-accountant vs interactive-entrepreneur latency split and the phased shadow-mode rollout are sharp and concrete.

---

## 6. THE FIX PLAN (priority order)

**Buildable now (no decision needed):**
1. **Fix the candidate filter (C2).** Include same-amount/same-counterparty docs regardless of paid status, rendering status as a fact. This unlocks T072/T074/T076 and is the single highest-leverage change — it fixes the reconciliation demo *and* removes the root cause of the false-confidence in C3. Add `find_candidates` reachability tests.
2. **Hold false-confidence (C3).** Add a guard same-amount-ambiguity check (downgrade / cap match_confidence when counterparty does not corroborate); fold euro x VAT into the post/defer gate; add an `assert false_confidence_count == 0` regression gate. Either consume `all_open` against a temporally-correct settled set or delete it.
3. **Stop the seed contamination + make learning demonstrable offline (C6).** Write learned corrections to a runtime store, keep `seeds/` read-only; extract a canonical vendor key (never raw IBAN) shared across selection/injection/guard; make `MockAgent` consult corrections.
4. **Wire the eval numbers (C4).** Add a runnable two-run lift script that calls `lift_report` and commits its JSON output; commit a real `LlmAgent` eval artifact (model id + date). Until produced, relabel 84->92 and "FC=0" as targets in every deliverable.
5. **De-overclaim the deliverables (C5, M1, M7).** Either build Logfire for real or rewrite the observability defence to describe the JSON `/trace` endpoint; make `explain` a real LLM call or relabel it; scope the "every correction is backstopped" claim to the 2 it covers.
6. **Tighten the prompt (M2, M3, M10).** Remove the "~96% / catch the 4%" leak; collapse to one instruction surface; gate/relabel general corrections.
7. **Quantify minutes saved (M8)** and add the request-document action + GT coverage (M4).
8. **Fix correctness-of-narrative details (Minor):** correct endpoint paths in the deck, add `GET /posted`, restate the "96%" match accuracy as ~86%, install pytest so the suite runs.

**Needs a decision from Adam (scope vs ~6h budget):**
- **Build the web UI (C1)?** This is the headline deliverable and the biggest single gap. A minimal static queue/card page over the existing API is achievable; decide whether to build it or to honestly re-scope the deliverables to "API-only prototype + UI is next" and lean on a strong screen-shared demo of the API + trace JSON.
- **Inflow accounting (M5):** book settlements to 1300 Debiteuren (accrual, consistent with the receivable model) vs document a cash-basis assumption and drop the receivable model. Pick one and make the data + chart consistent.
- **Demo artifact:** record the 7-min video / export the deck to PDF as the brief requires.
