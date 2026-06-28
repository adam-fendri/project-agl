# Neno AI Engineer Case Challenge — Working Scratchpad

> Living document for a multi-session project. We are still in the
> UNDERSTANDING + DECISION phase. No build decisions are locked yet.
> Source brief: `~/Downloads/Adam - Neno - AI Engineer Case Challenge.pdf`

---

## 0. Status / where we are

- Phase: understanding the challenge and making design decisions.
- Nothing built yet. Biggest open decisions are listed in section 9.

### DECISION (Adam, locked): build a REAL PRODUCT, go the extra mile
- This assignment is high-stakes / career-changing for Adam. Target = a genuinely
  working, polished product, NOT a minimal demo/prototype. Deliberately exceed the
  brief's ~6h expectation; the 3 bonus points all reward going further.
- "Extra mile" must show in the CORE first (real LLM proposals, real persistence,
  a learning loop that actually changes the next run, real eval numbers), THEN the UI.
  A polished app on a faked core scores worse than the reverse.
- Assistant note-to-self: STOP downscoping / "keep it simple" framing. Raise ambition.
  Stay honest about what's genuinely hard (s.11) without deflating it.

### Challenge 2 product = an interactive SaaS web app (CONFIRMED from brief)
The accountant opens a web portal, sees the agent's work (proposed account + match,
reasoning, sources, confidence per txn), and interacts: accept / correct / ask-to-explain.
Main surface = a RANKED REVIEW QUEUE (not a free-form chatbot; the chat is Ch.1).
Brief: "queue ordered by where their attention adds the most value... accept, correct,
or ask the agent to explain"; "user interactions ... visible and defensible".

### Target feature set ("AGL cockpit" / accountant review console)
ENGINE (all real): LLM structured proposals; deterministic tool layer; confidence +
act/defer policy; correction store that PERSISTS and changes later runs; eval harness.
SURFACES:
1. Review queue ranked by attention-value (impact x uncertainty).
2. Transaction card: raw txn, proposed account, proposed match, confidence, reasoning,
   CLICKABLE sources (the actual invoice/bill/correction used). Accept / Correct / Explain.
3. Auto-posted view (confident entries, reasoning visible, spot-checkable).
4. Anomaly surface w/ next action (request doc / escalate / dismiss).
5. Ask-the-agent (per-txn conversational explain) = the interactive sliver.
6. VISIBLE LEARNING: on a correction, show "fixes N similar pending" and RE-RUN live.
   (makes "one correction moves the next 10" something evaluators WATCH.) Highest-impact demo.
7. Trace/observability view (clickable: tool calls, prompt, evidence, confidence). [bonus]
8. Metrics header: %auto, %defer, false-confidence on labeled set, minutes saved. [bonus]

### BUILD SEQUENCE (Adam's directive): required product FIRST, then extra mile
PRINCIPLE: long-run thinking = SOUND FOUNDATIONS, not building future features early.
Phase 1 ships MINIMUM features on architecture that won't be ripped out later.

PHASE 1 = the working product the brief explicitly asks for:
- one customer; agent categorizes + reconciles + flags EVERY txn w/ confidence+reasoning+sources
- auto-post confident set; queue the rest ranked by attention-value
- accountant console: queue + cards (choice/reasoning/sources/confidence) + accept/correct/explain
- a correction PERSISTS and updates similar pending txns (learning requirement, real)
- the ONE anomaly w/ a clear next action
- wired end-to-end to a real LLM
(this IS the SaaS web app, scoped to required features; nothing here is extra mile)

PHASE 2 = extra mile (only after Phase 1 works):
- eval harness + live metrics dashboard (real numbers) [bonus]
- trace/observability VIEW [bonus] (trace DATA is captured in Phase 1; only the view is P2)
- Challenge 1 entrepreneur chat on the SAME engine [bonus]
- multi-customer portfolio queue, polish, more data

LONG-RUN FOUNDATIONAL DECISIONS (made now; architecture not features):
1. Typed MULTI-TENANT domain model; every record carries customer_id; shapes MIRROR the
   eventual Postgres schema (prod = "Postgres on GCP"). Demo=1 customer, no migration to scale.
2. Data access behind a REPOSITORY INTERFACE (JSON now -> Postgres/GCP later = a swap).
3. ENGINE separated from UI, reusable by BOTH front doors. Standalone typed core; FastAPI
   exposes it; React consumes it. Entrepreneur chat (P2) reuses same engine+tools. ("one engine")
4. Confidence + act/defer POLICY isolated as its own swappable layer (will be tuned/replaced).
5. Correction store = real persistence behind an interface (grows: retrieval->rules->priors->cross-cust).
6. Every decision emits a STRUCTURED TRACE record from day one (debug + bonus view + prod obs
   all read the same data; the bonus becomes near-free).
7. LLM behind a thin PROVIDER INTERFACE (Claude/Gemini swappable).
8. Production-credible STACK (not a demo toy you'd rip out).

### STACK (recommended; pending Adam confirm) — justified for the LONG RUN
- Backend: Python + FastAPI + Pydantic (typed boundaries map to Postgres later; matches `demo`).
- Frontend: React + Vite (real product UI; matches `terminal-vite`).
- LLM: Claude (Sonnet 4.x) for engine + explain; Gemini equally allowed by brief. Behind interface.
- Rejected: Streamlit/Gradio (demo toy, dead-end, violates long-run rule).
- OPEN: Adam to confirm stack + provider before any code. Plan-before-code applies.

---

## 1. What the challenge actually is

Neno builds full-stack AI financial services for European SMEs (accounting,
banking, payments, AI agents in one platform). Commercially live 6 months,
onboarding ~1 customer/day.

We build **Project AGL (Agentic General Ledger)**: the agentic layer between
Neno's data and two humans:

- **Entrepreneur** — the business owner. Wants fast answers + actions. Read-mostly.
- **Accountant** — supervises the back office. Write path. Every entry flows into
  VAT returns and tax filings, so errors cost real money and legal exposure.

Constraints from the brief: accurate enough for a VAT return, fast enough for a
conversation, explainable enough that an accountant can sign off.

### Pick ONE of two challenges, build end-to-end
- **Challenge 1 — Entrepreneur conversation:** multi-turn Q&A grounded in real
  data ("What's my VAT this quarter?", "What are my unpaid invoices?").
- **Challenge 2 — Accountant-supervised categorization + reconciliation:**
  confidence thresholds, learning from corrections, audit, handoff.

The brief itself says: "one product with two front doors."

### Seeded/mocked data (we model it as JSON)
- 100 bank transactions (EUR; invoices paid, expenses, payroll, ambiguous)
- 10 invoices issued by the customer (some paid, some unpaid) = accounts receivable
- 20 bills the customer received (some already paid) = accounts payable
- Txn<->invoice / txn<->bill matches provided by Neno infra at **~96% accuracy**
- Chart of accounts for a typical Dutch SME (2-50 FTE)
- 5 prior accountant corrections (CoA attribution, txn-to-invoice match)

### Deliverables
- Live prototype wired to a real LLM (Gemini or Claude)
- One-page architecture diagram (agent topology, tool boundary, where the human
  sits, where context comes from)
- 7-min video OR <15-slide deck
- Stack rationale (model choice, orchestration, retrieval/context, evals,
  observability) — one sentence each
- Time budget: ~6 hours

### Bonus points
- Deliver both challenges
- Run a real eval on seeded data and report numbers
- Add a clickable trace/observability view (tool call, prompt, confidence)

### Guiding question (the rubric in one sentence)
Design AGL so the accountant can sign off on every entry, the entrepreneur gets
an answer before the coffee cools, and neither ever sees the AI confidently get
it wrong. Plus: what timelines and resources to make it real.

### Evaluated on
Strategic thinking (act vs. defer + defend it, precision bar, latency/accuracy/
trust trade-off, stated assumptions); technical depth; prioritization (users over
what's technically interesting); execution (shippable + safe); communication
(a non-AI engineer can follow it). "We care more about the reasoning than names."

---

## 2. Domain knowledge (accounting) — enough to not say something dumb

> SCOPE CORRECTION: VAT is NOT the centerpiece. The brief mentions VAT once, as a
> sample entrepreneur question. The earlier deductibility deep-dive (private use,
> representation, exempt/pro-rata) was OUT OF SCOPE and is removed. The Challenge 2
> core the brief names is: pick CoA account, verify invoice/bill match, flag
> anomalies, set confidence/when to defer, request missing docs.

### Core vocabulary
- **General Ledger (GL):** master record; every transaction becomes a journal entry.
- **Chart of Accounts (CoA):** structured list of accounts to file things into.
- **Categorization:** assign each bank transaction to the right CoA account.
- **Reconciliation / matching:** link a bank transaction to its source document.
- **Invoice (issued by customer):** money owed TO them = accounts receivable / sales.
- **Bill (received by customer):** money THEY owe a supplier = accounts payable / purchases.
- Inflows reconcile to **invoices**; outflows reconcile to **bills**.

### Why precision matters (use the brief's OWN words, not invented nuance)
The brief: *"a misclassified transaction propagates through VAT returns, financial
statements, and tax filings."* That one line justifies the whole precision bar.
No deductibility/representation/private-use needed.

### VAT facts (VERIFIED, only if we keep a `compute_vat` demo feature)
- Rates: **21%** standard, **9%** reduced, **0%/exempt**. Filed **quarterly** for
  most SMEs (monthly/annual exist). Source: Belastingdienst + business.gov.nl.
- VAT owed = Output VAT (on sales) - Input VAT (on purchases).
- For THIS challenge: VAT = a downstream aggregation over categorized txns, answering
  one example entrepreneur question. Keep it minimal; do not model deductibility.

### Reconciliation checks (where the bad 4% of matches hide)
A provided match is a hypothesis to VALIDATE, not a fact to trust:
- **Amount (gross, VAT-inclusive):** exact match = strong; off materially = flag.
- **Direction:** inflow->invoice, outflow->bill. Wrong direction = category error.
- **Date sanity:** payment date on/after document date. Earlier = suspicious.
- **Duplicate detection:** two outflows, same amount/vendor/week = possible double pay.
- **Missing counterpart:** outflow with no bill = request it, or flag off-books.

### Worked slice (demo backbone) — exercises the required beats
| Txn | Categorize | Reconcile | Agent decision |
|---|---|---|---|
| Inflow EUR6,050 | Sales revenue | Matches invoice exactly | ACT (confident auto-post) |
| Outflow EUR121 "CloudCo" | Software/IT | Matches bill exactly | ACT (confident auto-post) |
| Outflow EUR3,200 "Salaris" | Wages | No document expected | ACT (confident, known pattern) |
| Outflow EUR145 ambiguous payee | two plausible accounts | no doc | DEFER (uncertain) |
| Outflow EUR40,000 unknown payee | unclear | No matching bill | ANOMALY -> review + request doc |
| Inflow EUR1,200 "matched" to EUR1,210 invoice | -- | amount off | BAD MATCH (the 4%) -> defer |

---

## 3. The "one engine, two front doors" framing (the senior read)

Don't build two apps. Build ONE engine; the two challenges are two views of a
single **act vs. defer** decision.

### What is literally SHARED (the engine)
1. **Tool layer** over the GL (query txns, get invoice/bill, validate match,
   search corrections, aggregate).
2. **Grounding discipline** (never assert what a tool didn't return).
3. **Decision core** (confidence scoring + the act vs. defer call). NOTE: this is a
   simple LLM-proposes / code-decides loop, not grand "architecture" (see s.5/s.11).
4. **Correction store** (accountant edits silently improve entrepreneur answers).
5. **Data model + eval harness.**

### REFINEMENT: the two sides use DIFFERENT safety mechanisms (not just defer-target)
Earlier "only the defer-target differs" was too clean. The brief sets OPPOSITE postures:
- **Entrepreneur (Ch.1):** safety = GROUNDING + ABSTENTION. Failure mode = hallucination.
  Brief: "human handoffs as a last resort; rely on grounding and tool design." Defers RARELY.
- **Accountant (Ch.2):** safety = CONFIDENCE-GATED DEFERRAL. Failure mode = false-confidence
  (auto-posting a wrong entry). Brief: "when confidence is low enough the accountant must
  review before the entry is posted." Defers READILY.
Shared engine, opposite default postures, different primary safety mechanism.

### What DIFFERS: only the "defer" target + who's in the loop
| | Entrepreneur (Ch.1) | Accountant (Ch.2) |
|---|---|---|
| In the loop | entrepreneur, live in chat | accountant, in a review queue |
| "Act" = | grounded answer + next step | auto-post the journal entry |
| "Defer" = | **defer to honesty** ("I'm not sure, N txns under review, could move by EURx") | **defer to the queue** ("not confident enough to post") |
| Cost of wrong | acts on a soft answer | wrong entry hits VAT return / tax filing |

Same line (act when confident AND stakes bounded; defer otherwise), two sides.

---

## 4. Agent architecture: the two front doors ARE different shapes

Adam's instinct (they're architecturally different) is correct. The sharpest
axis of difference is NOT "real-time vs not" (that's a symptom) but
**who controls the flow**:

- **Entrepreneur side = an AGENT.** Open-ended questions, can't pre-script the
  tool sequence, so the **LLM drives control flow** (chooses tools, when to stop,
  when to answer). Latency-bound, reactive/pull, multi-turn.
- **Accountant side = a WORKFLOW with an LLM step inside.** Same operation 100x,
  must be auditable + calibrated, so **code drives the flow** (gather evidence ->
  propose -> score -> route) and the LLM is boxed into one node. Throughput-bound,
  proactive/push, batch.

Maps to Anthropic's agents (LLM directs its process) vs workflows (predefined
code paths with LLM steps). High-stakes side should be a workflow precisely
because auditability + low false-confidence are easier when the model can't wander.

Nuance (each has a bit of the other):
- Accountant workflow has an interactive sub-mode: "explain this" / "correct it".
- Entrepreneur agent can spawn async work: "I've flagged those to your accountant".

---

## 5. Technical reality: what's CODE vs PROMPT vs DATA

Central idea: **in a high-stakes financial system the LLM decides as LITTLE as
possible.** The LLM appears in only two narrow spots; everything else is
deterministic code + data.

1. **Tool layer = CODE** (typed functions) + a JSON schema so the LLM can call it.
   Arithmetic lives in code so the model never does math in its head.
2. **Grounding discipline = WIRING (+ small prompt + validator).** The real
   enforcement: don't put raw data in the prompt; the only path to a fact is a
   tool call, so it can't fabricate.
3. **Decision core = CODE fed by a structured LLM output.** NOT a prompt.
   - Fuzzy part (LLM + prompt): emits a STRUCTURED proposal
     `{account, match, reasoning, signals}` — that's the prompt's only job.
   - Decision part (pure code): `confidence = score(signals...)`; then
     `if confidence >= THRESHOLD and value < CAP: ACT else DEFER`.
   - Threshold + confidence live in CODE because: auditable, unit-testable, stable
     (no prompt drift), and structural-signal confidence beats model self-report.
   - Same shape as drive-thru ActionDispatcher: LLM proposes, CODE disposes.
4. **Correction store = a DATABASE**, consumed two ways: retrieval (inject similar
   past corrections into the prompt as few-shot) + deterministic override (confirmed
   vendor->account rule short-circuits the LLM).
5. **Data model + eval harness = CODE.** Typed schemas (Pydantic/TS). Eval = script
   that runs the agent over labeled txns and computes metrics (no LLM in scoring).

### One transaction through the accountant workflow
| Step | What it is | LLM? |
|---|---|---|
| 1. Gather evidence (candidate accounts, provided match, similar corrections) | CODE (tools) | No |
| 2. Propose `{account, match, reasoning}` | LLM + PROMPT | **Yes** |
| 3. Score confidence from structural signals | CODE | No |
| 4. Decide act vs. defer (confidence threshold + euro-value cap) | CODE (policy) | No |
| 5. Write proposal + decision + trace to queue/ledger | CODE + DATA | No |
LLM = 1 step of 5.

---

## 6. Act vs. defer + confidence calibration (the spine)

- **Confidence comes from evidence, not from asking the model.** Self-reported
  "95% sure" is poorly calibrated and produces the false-confidence the brief hunts.
- **Raise confidence:** exact gross amount match; vendor seen before -> one account;
  a prior correction covers it; provided match passes all checks.
- **Lower confidence:** ambiguous description; new vendor; matches no document;
  multiple plausible accounts.
- **Defer triggers on low confidence OR high stakes** (euro value).
  A confident categorization on a EUR40,000 txn STILL defers. It's
  confidence x consequence, not confidence alone.
- Policy tiers: Act (auto-post) / Defer to queue / Block-and-request (missing doc) /
  Flag (anomaly to top of queue).

### False-confidence rate (the trust-killer metric) — brief calls it "the number that kills trust"
- Definition: of entries the agent AUTO-POSTED, fraction the accountant later corrects.
- Target: must NAME one and defend it. PLACEHOLDER ONLY: the "<1%" figure I floated
  earlier was invented; the real target depends on the accountant's own manual error
  rate + what Neno deems acceptable. Do NOT ship a number we can't ground.
- Hold it via: require corroborating evidence for high confidence; cap auto-post by
  euro value; sampling audit of auto-posted; learning loop pulls recurring errors down;
  bias to abstention when uncertain.

### THE CENTRAL TENSION (the strongest point in the submission)
Three asks pull against each other: 90%+ auto-categorized, false-confidence ~0,
and 30->60 capacity. Push auto-rate up -> false-confidence rises; push false-confidence
down -> defer more -> auto-rate and capacity drop.
HONEST RESOLUTION: the confident set is NOT constant. Day one, auto-post only the
structurally verifiable (exact match + known vendor + a prior correction covers it);
defer the rest. As corrections accumulate, the confident set GROWS toward 90%+ WITHOUT
raising the error rate. This directly answers "how fast does it learn" and is credible.
A naive "90% auto + 0% error on day one" is not.

### Queue ordering — brief's words: "where attention adds the most value"
= expected value of review = P(agent wrong) x cost of being wrong. NOT confidence-sorted.
High-value txn with borderline confidence floats up; near-certain or tiny ones sink.

### Capacity math (they ask for minutes saved) — MODEL, not measured numbers
- Shape: manual ~M min/txn x ~100 txns; with X% auto + (1-X)% reviewed @ ~R min each.
- The earlier "~8x / ~200->25 min" used INVENTED M and R. Present as a MODEL with
  stated inputs ("plug in real numbers"), not a measured result. Do not claim 8x.
- Biggest cuts: auto-posting the confident set; corrections stopping recurring errors.

---

## 7. Learning from corrections (one edit moves the next 10)

Requirement: a correction must change FUTURE behavior, not patch one row.
Layered mechanisms:
1. **Correction memory (retrieval/few-shot):** store `(features, corrected value,
   note)`; retrieve k most similar per new txn, inject as examples. Generalizes
   immediately, no retraining.
2. **Promoted rules (deterministic override):** unambiguous, CONFIRMED pattern
   (seen twice / "always do this") -> hard override scoped to that vendor+customer.
   Guard against over-generalizing a one-off.
3. **Per-customer priors:** vendor->account distribution updated by each correction,
   feeds the confidence model.
One **correction store** serves all three. Bonus: each correction is also a labeled
eval example (growing golden set).

---

## 8. Recommendation + system shape (PROPOSAL, not locked)

### Which challenge — HONEST TRADEOFF, not a slam dunk
Lean: **Challenge 2 as the one we build and defend.** It's where the scored substance
is (capacity, false-confidence, learning are all accountant-side) and it maps to
confidence-gating / human-in-the-loop / learn-from-corrections.
BUT: "deliver both" is a BONUS, not core. In 6h, two thin things score worse than one
strong one. So DO NOT plan for both. Build Ch.2 well; add a Ch.1 conversation ONLY if
Ch.2 is genuinely done and the same tools make it nearly free.
Counter-consideration: Ch.1 is easier to finish + demo well + fits a "Claude project"
(upload data + system prompt + chat). If time/finish-risk dominates, Ch.1 is the safer
pick. Decide deliberately.

### System shape (one-page diagram, in words) — it's SIMPLE, that's correct
NB: this is "LLM proposes / code decides + tools + a store", not grand architecture.
The brief WANTS it simple ("simple web app", "reasoning not names").
- Two front doors: Entrepreneur chat (fast model) / Accountant review queue.
- AGENTS: conversation agent (Ch.1) + categorization/reconciliation agent (Ch.2),
  both emit structured output `{account, match, confidence, reasoning, sources,
  anomaly_flag}`.
- POLICY LAYER (deterministic code): act / defer / block-and-request. Act-vs-defer
  lives HERE, not in the model.
- TOOL LAYER (grounding boundary): query_transactions, get_invoice/bill,
  validate_match, compute_vat, lookup_coa, search_corrections. Pure typed functions.
- DATA: mocked JSON now; Postgres on GCP in prod.
- CORRECTION STORE: retrieval memory + rules + priors; feeds back into the agents.
- EVAL HARNESS: run over 100 txns; report accuracy, false-confidence, %auto/%defer,
  queue precision (bonus: real numbers).
- TRACE VIEW: per-txn tool calls, prompt, evidence, confidence, decision; clickable
  example (bonus: observability).

### Stack rationale (one sentence each)
- **Model:** strong reasoning model (Claude Sonnet/Opus 4.x or Gemini Pro) on the
  accuracy-critical write path; fast model (Claude Haiku / Gemini Flash) on the
  latency-critical chat path.
- **Orchestration:** direct API calls + structured outputs + a thin deterministic
  policy layer, not a heavy framework, because act-vs-defer must be auditable code.
- **Retrieval/context:** per txn, assemble candidate accounts + the provided match +
  top-k similar corrections; nothing more (tight, grounded).
- **Evals:** run over the 100 txns; score accuracy + false-confidence against
  corrections + a hand-labeled golden set; report %auto vs %deferred + queue precision.
- **Observability:** per-txn trace (tool calls, prompt, evidence, confidence,
  decision) with one clickable worked example.

---

## 9. OPEN DECISIONS / TODO (still to settle)

- [ ] LOCK the challenge choice (lean Ch.2; Ch.1 only as bonus if Ch.2 done — see s.8).
- [ ] Confirm LLM provider (Claude vs Gemini) and exact models per path.
- [ ] Design the seeded JSON data so the demo hits every beat: confident set, a few
      uncertain, one anomaly, one of the ~4 bad matches. (HARD + load-bearing, see s.11)
- [x] Customer LOCKED = Studio Vondel B.V. (8-FTE Amsterdam web/branding studio, Q1 2026).
- [x] Chart of accounts DONE + RGS-grounded -> `data/chart_of_accounts.md` (~33 accounts,
      mapped to verified RGS GROUP codes; own 4-digit numbering; leaf codes not fabricated).
- [x] Cast + 10 invoices + 20 bills DONE -> `data/cast_and_documents.md` (grounded amounts;
      planted categorization traps, reconciliation traps, 2 anomalies). 
- [x] 100 transactions DONE -> `data/transactions.md` (grounded Dutch SEPA/iDEAL/BEA lines,
      ground-truth account+match+decision labels baked in). Split = 84 AUTO / 14 REVIEW / 2 ANOMALY.
      DECISION (Adam): KEEP 84/14/2. Cold baseline; corrections lift it to 92 (see below).
- [x] 96% provided matches DONE -> `data/matches.md` (4 wrong, one per failure mode:
      duplicate / counterparty-swap / short-pay / incomplete-split; ~24 correct).
- [x] 5 prior corrections DONE -> `data/corrections.md` (each = a RULE; applying all 5 lifts
      cold 84% -> 92% confident = the measurable "learning moves the next N" demo).
- [x] **DATA DESIGN PHASE COMPLETE.** 5 artifacts in `data/`: chart_of_accounts, cast_and_documents,
      transactions, matches, corrections. All grounded + internally consistent + GT labels inline.
- NEXT (per agreement): BEFORE any app code -> write the full Challenge-2 BUILD PLAN for approval.
- [ ] Decide tech stack for the prototype (web app? Python backend? UI?).
- [ ] Define the exact confidence signals + the act/defer thresholds + value cap.
- [ ] Define the false-confidence target number and how the eval measures it.
- [ ] Decide how the trace/observability view is rendered.
- [ ] Decide deliverable format: 7-min video vs <15-slide deck (or both).
- [ ] Draft the one-page architecture diagram.
- [ ] Timelines + resources answer (for the guiding question).

---

## 10. Glossary (quick reference)

- **AGL:** Agentic General Ledger (the product we design).
- **GL:** General Ledger (master record of all entries).
- **CoA:** Chart of Accounts (the categories).
- **AR / invoice:** accounts receivable; money owed to the customer.
- **AP / bill:** accounts payable; money the customer owes.
- **BTW:** Dutch VAT (21% / 9% / 0%, filed quarterly).
- **Reconciliation:** matching a bank txn to its invoice/bill.
- **False-confidence rate:** of auto-posted entries, fraction later corrected.
- **Act vs. defer:** auto-handle vs route to a human.
- **Agent vs workflow:** LLM-driven control flow vs code-driven flow with an LLM step.

---

## 11. DIFFICULTY MAP (calibrated — not "all hard", not "all easy")

The orchestration is simple ON PURPOSE; the problem underneath is hard in SPECIFIC
places. "Simple deliverable form" != "easy problem". Spend the 6h on the HARD column,
do not gold-plate the EASY one.

### Genuinely EASY (plumbing — don't over-build)
- Wiring an LLM call to Claude/Gemini.
- Tool functions over 100 JSON rows (filter / aggregate / lookup).
- Getting the LLM to propose an account for a txn.
- Validating the OBVIOUS bad matches (amount mismatch, wrong direction, bad date).
- A list/queue UI.

### MEDIUM
- Queue ranking (concept simple; tuning to surface the right items is not).
- General composable tools the LLM must combine for "any GL question" (Ch.1).
- A trace view that's actually useful, not a JSON dump.

### Genuinely HARD (the crux — more code does NOT fix these)
- **Calibrated confidence we can defend.** Brief calls false-confidence "the number
  that kills trust." LLM self-confidence is miscalibrated; can't tune calibration on
  100 self-authored rows. Hardest single thing.
- **Act/defer threshold under asymmetric cost** (wrong auto-post >> extra defer).
  Judgment, not code.
- **Catching the subtle 4% bad matches** (right amount, wrong invoice) — NOT catchable
  by simple checks; relies on the defer mechanism routing borderline matches to a human.
- **Learning loop that generalizes without over-generalizing** (a one-off must not
  flip already-correct cases).
- **Honest eval on a tiny self-authored set** — can show MECHANISM, not statistical
  PROOF; reporting numbers without overclaiming is itself hard.
- **Domain correctness for a newcomer** — one wrong accounting claim and a real
  accountant stops trusting the whole thing. Real risk since the domain is new to Adam.

### The meta
Moderately-to-genuinely hard challenge; hardness concentrated in JUDGMENT, DATA DESIGN,
DOMAIN CORRECTNESS, HONEST EVAL — not the plumbing. Part of the test is identifying
WHERE the hardness is and not wasting time on the easy parts.

---

## 12. CORRECTIONS LOG (assistant self-audit — what was wrong earlier)
- VAT deductibility was OUT OF SCOPE; over-inflated. Removed. Use the brief's
  propagation line instead.
- "Architecture" was overused for a simple LLM+tools+guards system. Downgraded.
- Invented numbers ("<1% false-confidence", "~8x capacity") had no basis. Marked as
  placeholders / model-only; do not ship as measured.
- "One engine, only defer-target differs" was too clean. Refined: different safety
  mechanisms (grounding/abstention vs confidence-gated deferral).
- Swung to "everything is easy" once; corrected with the calibrated difficulty map (s.11).
- Rule going forward: never assume; verify with official sources (have web access).
