# Decision Log — Project AGL (Neno AI Engineer Challenge, Challenge 2)

Built step by step with Adam. Each decision records the WHY (positives + the negative we accept),
so every choice is defensible. Keep the assignment goal and time in view: a real, defensible,
shippable prototype, not over-engineering.

## Goal (kept in view)
Challenge 2: the accountant-supervised categorization + reconciliation agent, wired to a real LLM,
on the seeded data. Deliverables = working prototype + one-page architecture diagram + deck/video +
tooling rationale + timelines. Judged on strategic thinking, technical depth, prioritization
(users over tech), execution (shippable/safe), communication. Don't over-build; serve the assignment.

---

## D1 — Build Challenge 2 (the agent)
The accountant-supervised categorization + reconciliation agent. The agent IS the product; the
accountant is the FINAL supervision layer.
WHY: it's where "every decision matters" and maps onto the rubric (act-vs-defer, precision bar,
false-confidence, learning).

## D2 — Architecture: the AGENT decides; code GROUNDS + GUARDS
The AGENT (LLM) makes the decisions the brief assigns it: which account, whether/what it matches, whether
it is anomalous, and how confident it is (post vs defer). CODE never decides; it does two things:
GROUND (compute the verifiable facts -- amount vs gross, direction, already-settled, is there a correction
for this vendor -- and hand them to the agent as evidence, so it decides on facts not guesses) and
GUARD (a STRICT backstop: never let a decision a hard fact contradicts auto-post; it can only DOWNGRADE
auto->review, never silently rewrite the agent's call). Learning: corrections become memory the agent
decides with, plus an exact-rule guard so a known fix always applies.
WHY: the brief is explicit that these are "the AGENT's decisions / the AGENT's confidence" and that code's
role is "grounding and tool design to prevent hallucinations". Grounding makes the agent's confidence
well-founded; the strict guard holds "never confidently wrong" (the number that kills trust) WITHOUT code
becoming the decider. This is a money system: strict is the floor, not a dial.
NEGATIVE WE ACCEPT: on real messy data the system defers more on day 1; honest, and the auto-set grows via learning.

## D3 — Model: a strong frontier model, eval-validated
Use a strong model (Claude Sonnet or Gemini Pro) for the interpretation; the eval tests whether a
cheaper model (e.g. Gemini Flash) holds the accuracy for production.
WHY: the LLM is primary and the precision bar is high (errors hit VAT/filings), so capability beats
per-call cost; cost is softened because rule-covered txns skip the LLM; and we measure with the eval
rather than guess.
NEGATIVE WE ACCEPT: a strong model costs more per call; mitigated by rule-skip + eval-driven downgrade.

## D4 — Orchestration: our own pipeline (no framework); the LLM call uses pydantic-ai
PIPELINE = our own deterministic code, NO orchestration framework (LangGraph/CrewAI), because the flow
is FIXED (one LLM step per txn), not an agentic loop -> auditable + simple (PDF: practical, users over tech).
THE LLM CALL = pydantic-ai (a LIGHT structured-output wrapper, NOT an orchestration framework): typed
Pydantic output + retries (ModelRetry) + automatic Logfire tracing (instrument_pydantic_ai) +
provider-swappability (Claude/Gemini).
WHY pydantic-ai for the call: exactly our needs (typed output, retries, Logfire, swappable), light, and
familiar from Adam's stack -> faster build. The orchestration stays OURS; pydantic-ai only wraps the call.

## D5 — Context engineering: corrections in the AGENT's EVIDENCE; code guards the exact rule
STATIC config (chart of accounts, client settings) -> stored per client, LOADED into the prompt.
CORRECTIONS -> SURFACED TO THE AGENT as evidence (the relevant ones in the prompt) so the AGENT applies the
customer's convention itself and DECIDES with it. They are ALSO kept in an indexed store (keyed by normalized
vendor / pattern) so CODE can GUARD: if the agent's account contradicts an exact rule for that vendor, code
downgrades to review (the "always-apply" safety) -> a known fix is never silently missed.
  - Demo scale (5 corrections): all relevant corrections fit in the prompt; the agent decides with them.
  - Production scale: retrieve the relevant corrections into the prompt (the store is the index); the guard
    still enforces exact rules. Retrieval is a SCALE step EXPLAINED IN THE DECK, not built for 5.
WHY: the brief says the AGENT decides, so corrections must inform the agent's DECISION (in evidence), not be
applied by code behind it. The exact-rule GUARD is how "one correction moves the next 10" / "a known fix
always applies" holds WITHOUT making code the decider. Wrong categories with no corroboration DEFER (never
silently auto-post). (Supersedes the earlier "rules never enter the prompt / code overrides" wording.)
NEGATIVE WE ACCEPT: a truly novel vendor isn't covered -> the agent decides from its base interpretation, and
it becomes a correction (agent memory + guard rule) once the accountant fixes it.

## D6 — Generalization of corrections (one correction -> the next 10 "similar")
RULED OUT: (A) auto-generalize one correction across vendors by fuzzy similarity -> unreliable +
over-generalization (one fix wrongly blanket-changes unrelated txns -> violates the precision bar).
USE, layered:
- (B) the LLM generalizes by REASONING for NOVEL vendors (free; categorizes a new freelancer from the
  string without needing the correction).
- (C) GENERAL accounting lessons live in the PROMPT (systematic, all-clients; e.g. "individual +
  invoice = freelancer cost, not salary").
- (D) ACCOUNTANT-CONFIRMED PATTERN rules for client-specific generalization: system proposes "apply to
  all X?", accountant confirms -> a pattern rule. Safe (human sign-off), visible (demo beat).
WHY: generalize as far as is SAFE, no further; never over-generalize silently (a wrong generalization
flows into VAT/filings). Layers = vendor rule (D5, exact) + LLM base (novel) + prompt (general) +
accountant-confirmed pattern (client-specific).

## D7 — Accountant console (UI)
PDF-specified pieces: a REVIEW QUEUE (the uncertain + anomalies); each item a CARD showing choice +
reasoning + sources + confidence, with ACCEPT / CORRECT / ASK-TO-EXPLAIN; a separate AUTO-POSTED view
(the confident ~90%, reasoning visible, spot-checkable); anomaly cards show a NEXT ACTION (request doc /
escalate / dismiss); a TRACE view (bonus, near-free since we already capture the trace). Live learning:
on CORRECT, show "N similar updated" + re-run those.
DECISION -- queue RANKING by IMPACT x UNCERTAINTY (P(wrong) x cost: euro value, VAT-sensitivity),
anomalies pinned to top. (Not lowest-confidence-only; not euro-value-only.)
WHY: the literal reading of "where their attention adds the most value"; sends limited accountant
attention where a mistake is both likely AND costly -> makes the 30->60 capacity claim credible.

## D8 — Stack: Python/FastAPI API-first + decoupled React client
Backend: Python + FastAPI, API-FIRST (the engine behind a clean REST API; frontend-agnostic).
Frontend: React + Vite, a DECOUPLED CLIENT of that API (swappable; can start simpler and swap up).
LLM: the strong model (D3) via direct structured-output calls (D4), behind a thin provider interface.
WHY: the API boundary insulates the valuable engine from the frontend -> swapping the frontend = UI
rebuild only, ZERO backend change; matches "full product" and keeps the frontend choice reversible.
RULE: the frontend NEVER reaches into the engine in-process; every frontend calls the API.
REALITY (post-build): the prototype shipped a NO-BUILD STATIC console (vanilla HTML/JS in `backend/ui/`,
served by the same FastAPI app), NOT React + Vite. The API-first boundary held, so React remains a
production option; the deliverables describe what was actually built (a static web console), not React (see D12).

## D9 — Observability (debug the agentic flow): Logfire
TOOL: Logfire (+ OpenTelemetry). Configure once at import; per transaction emit ONE span carrying the
full record (assembled context, prompt, raw LLM output, code verification results, confidence signals,
final decision) as attributes (pattern reused from Adam's VoxAI stack: their "turn.record" on the span).
WHY: the PDF's observability bullet is "how you DEBUG your agentic flows" -> the per-txn span IS the
debug tool; AND the Logfire UI is a clickable per-transaction trace viewer -> that's the BONUS trace
view ~free (point the deck at a real Logfire trace). One artifact, both jobs. (Reuse, not anchor:
the DESIGN was decided on the challenge's merits; Logfire is just the right, familiar tool to build it.)
REALITY (post-build): Logfire is NOT wired in the prototype (the dependency is declared but never imported
or configured). The prototype's observability is the JSON `/trace/{id}` endpoint that reconstructs the full
record on demand (rendered in the console's trace drawer). Logfire — one span/txn with that same payload —
is the production observability step, stated as roadmap, not claimed as built (see D12).

## D10 — Agent interaction pattern: SINGLE-PASS (the AGENT decides once on grounded evidence; code grounds + guards). Concretizes D4.
The real distinction between the candidates = does the LLM RE-ENGAGE with computed results (a loop) or not?

THREE shapes, with positives + negatives:
- (A) FRAMEWORK TOOL-CALLING — the LLM runs a loop, decides which tools to call, sees results, continues.
  + maximally flexible; least orchestration code; right for open-ended tasks.
  - LLM owns control flow -> non-deterministic, hard to audit/test/reproduce; many round-trips/txn (cost+latency x100);
    tool-call error surface; the flexibility is UNUSED on a fixed pipeline.
- (VOX) MANUAL TOOL-CALLING (code-orchestrated LOOP) — code calls the LLM (decide) -> runs the engine -> feeds the
  computed state BACK to the LLM (Vox's render / "say" 2nd call, core.py "Two-call model") -> final output. Vox is
  NOT single-pass; it LOOPS, we just orchestrate it ourselves.
  + code controls the loop (more deterministic than A); the FINAL output reflects computed state (essential when it
    must be LLM-rendered, e.g. natural speech); proven at scale.
  - still 2+ LLM calls/txn (cost/latency x100); extra complexity for a benefit we don't need (our output is a
    STRUCTURED decision, not prose); the 2nd call does NOT improve CORRECTNESS (the agent already decides from grounded facts; code grounds + guards).
- (B, CHOSEN) SINGLE-PASS — code GROUNDS the agent with computed facts -> ONE structured-output LLM call where the
  AGENT decides -> code GUARDS (strict backstop); the LLM does not RE-ENGAGE with computed results (no loop).
  + deterministic + auditable end-to-end (code grounds every fact + guards every route -> meets precision + sign-off
    bar); cheapest + simplest (1 call/txn); the agent's judgment can NEVER auto-post past the guard (serves "never
    confidently wrong"); structured output ~100% schema-reliable.
  - the agent decides in one shot, so its evidence must be well-grounded up front (code's job); the card reasoning is
    the agent's, with code's verified facts shown as sources; the "explain" call covers richer narration; demands
    thorough grounding + guard code (required by the precision bar anyway).

PATTERN (B), per transaction:
1. GROUND (code): assemble the agent's evidence = transaction + CoA (config) + candidate documents (provided match +
   reconciliation candidates) WITH computed facts (amount vs gross, direction, already-settled, combination sums) +
   the relevant corrections + vendor history.
2. DECIDE (ONE LLM call = the AGENT, structured output via pydantic-ai, NO tools/toolset, temp 0): grounded in those
   facts, the agent decides account, match, anomaly, AND its confidence.
   Proposal{vendor, account, account_reasoning, match[], match_reasoning, anomaly?, confidence?}.
3. GUARD (code, STRICT backstop, NOT the decider): never let a decision a hard fact contradicts auto-post
   (amount!=gross, doc already settled, account not in CoA, exact-rule conflict, material missing-doc unflagged);
   it can only DOWNGRADE auto->review, never rewrite. Then route auto/review/anomaly/request-doc; show computed facts as sources.
ON-DEMAND: the accountant's "explain" was DESIGNED as a separate LLM call (does not reintroduce the per-txn
loop). IN THE PROTOTYPE it ships as a DETERMINISTIC, code-built narration of the decision (`Console.explain`
-> `_narrate`), not an LLM call; the real follow-up call is the planned next step (see D12).

WHY B fits Ch2 (DERIVED FROM THE TASK, not the Vox precedent or preference):
- FIXED per-txn flow -> no LLM orchestration needed (A's flexibility unused).
- PREDICTABLE/structured inputs -> code pre-computes all evidence -> no fetch loop (A not needed).
- PRECISION BAR + AUDIT (sign-off, never-confidently-wrong) -> grounding + the guard must be deterministic code (the
  agent decides on real facts; the strict guard catches any fact-contradiction) -> single-pass; agent judgment never auto-posts past the guard.
- BATCH at scale (30->100+ customers) -> minimize calls (1/txn); loops double cost for no correctness gain.
- Output is a STRUCTURED decision -> the agent decides it in one shot from grounded facts -> no LLM render loop (Vox's
  reason to loop does NOT apply). Hard cases: the agent SEES the bill is already settled -> decides duplicate; SEES the
  sum-search candidates -> matches both invoices; SEES the amount gap -> flags short-pay; SEES the payer -> matches the
  right invoice. Code grounds + guards; none needs a 2nd LLM turn.

CHALLENGE-1 CONTRAST (right pattern per job = the "agent interaction patterns" the rubric grades): the entrepreneur
conversation IS a genuine tool-calling task (open-ended -> the LLM must decide what data to pull). So TOOL-CALLING
for Ch1 (bonus), SINGLE-PASS for Ch2.

SOURCES: Anthropic "Building Effective Agents" (use the simplest thing); structured-outputs-vs-function-calling
(MachineLearningMastery, agenta); ANNA production categorization (ZenML); Vox assistants core.py (verified: it is a
2-call decide->render LOOP, NOT single-pass).

## Coverage check vs the full brief (validation)
COVERED by D1-D9 + build sequence: live prototype+LLM; model/orchestration/retrieval/evals/observability
tooling; act-vs-defer (D2); precision bar; prioritization (users over tech); execution (safe/auditable);
bonuses: eval-with-numbers (step 8) + trace view (D7/D9).
DELIVERABLE CONTENT TO WRITE (not new system decisions, go in the deck/diagram):
- STATED ASSUMPTIONS: model capability (LLM interprets messy strings -> primary categorizer, verified+gated);
  data quality (real bank data is messy/inconsistent); accountant role (supervise uncertain, correct, sign-off).
- LATENCY/ACCURACY/TRUST: accountant side is BATCH -> trade latency for accuracy+trust (coffee-cooling = entrepreneur side).
- TIMELINES & RESOURCES (guiding question): prototype -> production roadmap (harden ingestion, real Postgres,
  scale the rule store, hires, rough timeline).
DATA NOTE: hardening descriptions can lower the cold confident rate -> tune data so corrections + recurring
  vendors still land the 90%+ beat. The "cold ~84 -> ~92" figure is an ILLUSTRATIVE DESIGN TARGET, never a
  produced result: the lift MECHANISM is proven offline (a Figma correction moves its 2 siblings, +1.0 on
  those rows), and the cold->warm accuracy figure is harness-measured per run (model id + date in
  `eval_artifact.json`); do not state 84->92 as a measured number anywhere (see D12).
TIME/PRIORITY: ESSENTIAL first = engine + eval + functional console + deliverables. OPTIONAL upside =
  Challenge 1 entrepreneur chat (3rd bonus, same engine) + heavy UI polish.

## D11 — Data-layer corrections from the lead review (M5 / M9 / M4 + minors)
Honesty is the cardinal rule of this submission: every seed number must be computable from the
data and true. `build_seeds.py` now asserts each invariant below and prints the distributions.

- **M5 — inflow accounting is ACCRUAL.** A bank inflow that settles an issued invoice books to
  **1300 Debiteuren** (it clears the receivable), NOT 8000 Omzet. Revenue and the receivable are
  recognized when the invoice is ISSUED (Dr 1300 / Cr 8000), off the bank feed; the cash receipt
  only clears the receivable (Dr 1100 Bank / Cr 1300). Booking settlements to 8000 would
  double-count Q1 omzet AND output BTW — a direct hit to the VAT/audit precision bar. The 7
  invoice-settling inflows (T007/T012/T039/T045/T072/T074/T076) are GT account 1300; ZERO
  bank-feed lines book to 8000 (8000 is only ever touched at invoicing, which is not in the feed).
- **M9 — provided-match accuracy is stated honestly, two numbers.** The brief's "~96%" is the
  per-transaction match/no-match accuracy across ALL 100 transactions: 96 correct decisions, 4
  planted errors. On the POSITIVE-match subset alone, precision is ~85% (4 wrong of 26) — disclosed
  openly, because that ~15% error on the matches the agent is GIVEN is exactly why the agent must
  VERIFY every provided match, not trust it. Both numbers are computed from the seeds (no
  hand-waved "count the 72 no-matches as true negatives"). Exactly 4 planted failures are kept:
  collision T072, swap T074, split T076, duplicate T046. T045 (short-pay) is a CORRECT doc-id match
  (its planted skill is amount-tolerance flagging, not a wrong document).
  NEGATIVE WE ACCEPT: literal ~96% precision on the positive subset is impossible with only ~28
  reconcilable transactions and 4 planted failures (it would need ~100 positive rows), so the honest
  dual-number framing is used instead of inflating the denominator.
- **M4 — REQUEST_DOCUMENT is a scored outcome, distinct from MISSING_COUNTERPART.** A low-stakes
  missing counterpart defers to REVIEW; a MATERIAL missing document triggers a deliberate
  REQUEST_DOCUMENT (ask the entrepreneur). T049 (EUR4,500 builder, no bill) and T096 (cites
  invoice 99213, no bill) are labelled `request_document`; the lone anomaly is now T046 (the
  duplicate). Outcomes: 84 auto / 13 review / 1 anomaly / 2 request_document.
- **Minors.** Bills B-04/B-05 are repurposed to two **UNPAID** open payables (18 paid / 2 open AP),
  so "some were already paid" is true and the studio has realistic accounts payable; their former
  Adobe/Figma Jan direct debits (T003/T004) now carry no bill match, like the other recurring-SaaS
  months. Counterparty truncation artifacts ("KASA TECH .", "BRIGHTSEED .") are fixed in
  `_abbrev` (trailing separators stripped after suffix removal and truncation).

CROSS-FILE IMPLICATIONS (not changed here, flagged for the owners): `agent.py` MockAgent still books
inflows to 8000 (`_REVENUE_ACCOUNT`); it now disagrees with GT 1300 on the 7 inflows, but it rates
inflows LOW confidence so they route to review, NOT auto-post — so this lowers only the naive mock's
categorization accuracy (a realistic baseline error the real LLM must beat), it does NOT create
false-confidence. `eval.py` counts `request_document` routing but does not yet score its
precision/recall — an eval enhancement outside this data-layer change.

## CORRECTNESS PRINCIPLE + open items (after the agent-decides realignment of D2/D5/D10)
PRINCIPLE: this is a MONEY system -> CORRECT by default; STRICT is the floor, not a dial. Zero-tolerance:
confident-wrong auto-post, double-pay, silent short-close, wrong VAT, a known correction not applying.
Simplicity must EARN its place by not weakening correctness (proper != complicated). "Demo" = limited SCOPE,
never limited correctness.
AGREED: GUARD = strict. SHORT-PAY = always flag, never a silent close. MISSING-DOC = the agent judges WHETHER
to request (material) vs flag, but a missing document on a real expense is NEVER silently dropped (the floor).
OPEN (resolve when we finalize grounding + guard; NOT yet built):
- Proposal/Decision CONFIDENCE field -- the agent's confidence output shape (the agent decides confidence).
- SETTLEMENT — RESOLVED: documents carry paid/unpaid status (GIVEN metadata, restored; I'd wrongly removed it).
  The DUPLICATE = a document claimed by 2 transactions in the provided matches (a collision: B-11 <- T040 AND T046)
  plus the paid status, surfaced to the agent, who decides the later one is the duplicate. NO runtime ledger
  (over-engineered; the brief gives the status, and the collision is in the provided matches).
- HARDENING calibration -- UNVERIFIED until the eval runs (whether the AUTO cases stayed auto-able).
UI: React is NOT fixed (D8) -- a lighter UI on the same API is fine; the proper/scalable part is the engine.

## D12 — Reality-sync (post-build honesty pass, from the lead review C5/M1/M7 + the honesty mandate)
Honesty is the cardinal rule of this submission: nothing in any deliverable may claim something the code
does not do. This decision reconciles every place an earlier decision ran ahead of the build, and is the
source of truth the deliverables (DECK, ARCHITECTURE, ASSUMPTIONS_AND_TIMELINE) were rewritten against.

- **UI EXISTS, and it is a static web console, not React.** `backend/ui/` (index.html + app.js + style.css)
  is a no-build vanilla-JS accountant console served by the FastAPI app (`StaticFiles` mount): review queue,
  auto-posted tab, decision card (accept/correct/explain), trace drawer, metrics bar. Deliverables describe
  this; they no longer list a "React client" as built (corrects D8 / the old C0).
- **`explain` is deterministic narration, not an LLM call.** `Console.explain` -> `_narrate` builds a
  sentence over the card's own fields; it is sync, with no model call. Relabelled everywhere as deterministic
  narration; a real follow-up LLM call is named as the next step (corrects D7/D10, review M1).
- **No Logfire is wired.** The prototype's observability is the JSON `/trace/{id}` endpoint (reconstructed on
  demand, rendered in the trace drawer, read by the eval). Logfire is described as the production plan, never
  as "done" (corrects D4/D9, review C5).
- **False-confidence is HELD at 0 and gated by a test.** The guard gained a same-amount-collision check, a
  revenue-on-settled-invoice check, and a fingerprint-duplicate check; the router downgrades material x
  VAT-sensitive x uncorroborated posts. Offline run = 0; `test_mock_run_holds_false_confidence_at_zero` fails
  the build if it rises. On the real-LLM run the same number is measured (review C3).
- **"Every correction is backstopped" scoped to the cost-account class.** The guard enforces vendor->cost
  (rubriek 4) corrections; asset/owner-draw conventions and match re-points defer via the confidence gate +
  eval, not the guard. Deliverables state this boundary (corrects review M7).
- **No fixed eval result is asserted.** Reproducible offline baseline (MockAgent, all 100, 2026-06-28):
  false-confidence 0; routing 18 auto / 81 review / 1 anomaly; categorization 40% (naive baseline the real
  LLM must beat); match 90% (circular — the mock copies the provided match). The real-LLM run
  (`scripts/run_eval.py --agent claude`) writes a self-describing `eval_artifact.json` (agent, model id,
  date, denominator); its categorization/match/lift figures are targets the harness measures, cited only
  once the committed artifact carries them — never asserted as produced numbers in prose (review C4).
- **GT outcome split is 84 auto / 13 review / 1 anomaly / 2 request-document** (not "84/14/2", not "two
  anomalies"): the single anomaly is the duplicate, the two requests are the material missing-document cases.
- **Minutes saved is a MODEL with stated inputs** (DECK Slide 11), not a measured result: the auto-rate is
  the measured input (84% on this set), the per-task minutes are assumptions; the auto-post step dominates
  the minutes, the queue-ranking step holds false-confidence at zero (answers review M8).
