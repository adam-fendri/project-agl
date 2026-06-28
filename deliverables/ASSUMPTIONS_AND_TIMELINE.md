# Project AGL — Stated Assumptions, the Guiding Question, Timelines and Resources

> The accountant-supervised categorization and reconciliation agent for Neno. This document states the
> assumptions the design rests on (model capability, data quality, the accountant's role), answers the
> guiding question (sign off every entry, answer before the coffee cools, never confidently wrong), and
> sets out the prototype to production roadmap with what to harden, who to hire, and a rough timeline.
> Companion docs: `PLAN.md` (the engine), `DECISIONS.md` (the why behind every choice).

---

## Part A — Stated Assumptions

Three assumptions carry the design. Each is stated with the why, and with what the design does so that the
assumption being imperfect never turns into a confidently wrong post.

### A1. Model capability

**Assumption.** A strong frontier model (Claude Sonnet 4.6, or Gemini 2.5 Pro behind the same interface)
can read a messy Dutch bank line (`GOOGLE *ADS 8729`, `SEPA OVERBOEKING J. DE VRIES FACT 2026-014`, an
iDEAL BEA string) and reliably infer the vendor, the nature of the spend, and which document a payment
settles, given the chart of accounts and the candidate documents in front of it. This is genuine
natural-language interpretation of inconsistent strings, which is the one part of the task a rules engine
cannot do well, so the model is the **primary categorizer and matcher**, not a tie-breaker.

**Why.** The brief assigns the decisions to the agent ("the AGENT's decisions, the AGENT's confidence") and
the hard tail is linguistic: Google Workspace versus Google Ads, freelancer versus salary, asset versus
office supplies, owner draw versus expense. Those are disambiguated by reading the string and the customer's
conventions, which is exactly what a capable LLM does and a regex does not.

**What the design does about its limits.** A model is fluent but not arithmetic, and it can be fluently
wrong. So the design never trusts it for two things: **sums** and **never-confidently-wrong**.

- The model never does the money arithmetic. `reconcile.py` computes amount versus document total,
  direction, short-pay gap, and combination sums; the agent only decides *which* document the counterparty
  and reference point to. An LLM cannot be trusted with a Decimal sum, so it is never asked for one.
- The model rates its **own** confidence, but that confidence is **grounded** (it reads computed facts, not
  guesses) and **required to be corroborated** before anything auto-posts. The strict guard (`guard.py`) is
  the backstop for the rare "sure and wrong": it can only **downgrade** an auto-post to review, never rewrite
  the agent's choice.
- The model is swappable behind one interface (`AgentProtocol.decide`). The eval (`eval.py`) is how we
  *measure* capability rather than assume it: it tests whether a cheaper model (Gemini Flash) holds the
  accuracy before we ever downgrade in production. Capability is validated, not asserted.

### A2. Data quality

**Assumption.** Real bank data is messy and partially trustworthy, and the design must assume that as the
*normal* case, not the exception.

- Bank descriptions are inconsistent, truncated, and noisy (the same vendor appears under several strings).
- The transaction to document matches arrive from Neno's infrastructure at **~96% accuracy across the
  feed** (and ~85% precision on the positive matches alone), so a meaningful share are wrong, incomplete, or
  missing. The provided match is a strong hint, not ground truth.
- Documents (10 invoices, 20 bills here) carry their own paid/unpaid status as **given metadata**, and some
  expenses simply have no document in the system yet.

**Why.** This is the source of the precision bar. A misclassified or wrongly reconciled transaction flows
downstream into the VAT return and the filings, so a system that assumes clean inputs would auto-post the
wrong matches with full confidence, which is precisely the failure that kills trust.

**What the design does about it.**

- **Verify first, do not re-search blindly.** Because the matches are already ~96% right, the agent's job is
  to *confirm* the provided match (counterparty/reference agrees, amount lines up) and, only when it does not,
  search the other candidates for the right document. This spends the agent's attention where the data is
  actually broken (the collision, the combination, the short-pay).
- **Settlement is given, not derived.** The duplicate is a document **claimed by two transactions** in the
  provided matches plus the paid status, surfaced to the agent as a duplicate note; there is no runtime
  ledger inventing state the data did not give us.
- **Fail closed at the boundary.** Inputs are validated into strict Pydantic models (`extra="forbid"`,
  `Decimal` money). A malformed payload is rejected loudly rather than best-efforted into a wrong post. In
  production this is where ingestion hardening lives (Part C).
- **Honest day-one posture.** On messier real data the cold confidence is lower than on the curated set, so
  the system **defers more on day one** and the auto-set grows as corrections accumulate. That is the safe
  direction to be wrong in.

### A3. The accountant's role

**Assumption.** The accountant is the **final supervision layer and the source of truth for conventions**,
not a data-entry clerk and not a rubber stamp. The agent does the bulk; the accountant's scarce attention is
spent on the uncertain few and the anomalies, and on **correcting**, which is how the system learns.

**Why.** The capacity goal (30 to 60 customers per accountant, on the curve to 100+) is only credible if the
confident bulk auto-posts untouched and the accountant touches the tail. The brief is explicit that the
accountant "accepts, corrects, or asks the agent to explain", and that one correction should move the next
ten similar transactions. So the accountant's highest-value act is not clicking accept, it is **teaching**.

**What the design does about it.**

- **The queue is ranked by where attention is worth most** (likely-wrong times costly: euro value times
  VAT-sensitivity times uncertainty, with anomalies pinned), so limited attention lands on the entries where
  a mistake is both probable and expensive (`api.py` `_rank_key`).
- **Correcting is a dropdown, not coding.** The accountant picks the right account or re-points the match;
  the system builds the correction by joining the **vendor the agent already identified** (a canonical key,
  never the raw IBAN) with the accountant's pick, writes it to a **runtime store** (the committed seeds stay
  read-only), and **re-runs the pending same-vendor ones** immediately ("N similar re-run"), with the
  cost-account guard guaranteeing that class of fix is never silently dropped.
- **The auto-posted set stays signable in bulk**, with reasoning and verified sources visible to spot-check,
  so the accountant can sign off on the confident set without touching each one. That untouched bulk is the
  capacity gain.
- **The entrepreneur is a second user, not this agent's responsibility.** The accountant supervises; the
  entrepreneur conversation (request a missing bill, answer "what is my VAT this quarter") is a separate,
  interactive surface (Challenge 1) that shares this engine but runs a tool-calling pattern, not single-pass.

---

## Part B — Answer to the Guiding Question

> *If you joined Neno tomorrow, how would you design Project AGL so that an accountant can sign off on every
> entry it produces, an entrepreneur gets an answer before their coffee cools, and neither of them ever sees
> the AI confidently get it wrong?*

Three promises. Each is held by a concrete mechanism already in the prototype, not by hope.

### B1. The accountant can sign off on every entry

Sign-off requires that every entry be **auditable**: the accountant must see *what* was decided, *why*, and
*on what verified facts*, and must be able to override without friction.

- **Grounding before deciding.** Code assembles the evidence (the transaction, the chart of accounts, the
  provided match and candidates with their computed facts, the relevant corrections, vendor history) so the
  decision rests on facts, not vibes. That evidence is the audit record.
- **Every card carries the agent's reasoning plus code's verified facts as sources** (`Decision.sources`,
  `confidence_signals`): which account, why, which document it settles, whether the amount sums exactly,
  whether the provided match was confirmed or overridden, whether a correction applied. The accountant signs
  off on a fact-backed claim, not an opinion.
- **One click to accept, one dropdown to correct, one button to explain** (a deterministic, code-built
  narration of the decision over the card's own fields — not a second LLM call; a real follow-up model call
  is a small, deliberate next step we have not built yet). Override is always available and always cheap.
- **A full per-transaction trace** reconstructed on demand by the JSON `/trace/{id}` endpoint (context,
  prompt, raw model output, guard verdict, confidence signals, final decision) and rendered in the console's
  trace drawer. Every entry is reconstructable end to end, which is what "sign off" means for a money system
  under audit. (Streaming the same payload to Logfire as one span per transaction is the production
  observability step — planned, not built.)

### B2. The entrepreneur gets an answer before the coffee cools

The coffee-cooling promise is a **latency** promise, and it lives on the **entrepreneur** surface, so the
design splits the two surfaces deliberately by their dominant constraint.

- **The accountant surface is batch.** Reconciliation runs over the customer's transactions ahead of the
  accountant opening the queue, so here I deliberately **trade latency for accuracy and trust**: one
  structured-output call per transaction, temperature 0, runnable concurrently across the batch. Nobody is
  waiting on a single call, so correctness wins.
- **The entrepreneur surface is interactive and bounded.** The entrepreneur asks a question or is asked for a
  missing bill; that is a tool-calling conversation (Challenge 1) over the *same* grounded engine, where the
  latency budget is a few seconds of bounded tool rounds, not an open-ended agent loop. The right next step
  (request this specific bill, here is your unpaid total) is produced directly, with the engine's verified
  facts behind it so the answer is fast **and** correct.
- **The split is the point.** Choosing single-pass for the accountant (cheap, deterministic, auditable) and
  tool-calling for the entrepreneur (flexible, interactive) is the right interaction pattern per job, which
  is exactly the latency/accuracy/trust trade-off the brief asks us to defend.

### B3. Neither ever sees the AI confidently get it wrong

False-confidence ("sure and wrong, auto-posted") is the number that kills trust. **Target: zero on the
evaluated set.** It is held by four layers, not one.

1. **Two confidences, not one.** A transaction is two decisions (the account and the match) with different
   evidence and different ways to be wrong. The agent rates each independently. A single number would be
   either unsafe or lossy.
2. **Auto-post requires BOTH high AND corroboration.** High is allowed only when the evidence corroborates
   it (for the account, the description or a correction makes it unambiguous; for the match, the
   counterparty/reference **and** the amount both agree). A material, VAT-sensitive entry whose counterparty
   does not corroborate is downgraded to review even at self-high confidence.
3. **The strict guard backstops every auto-post.** Before anything posts, code checks the decision against
   hard facts: account exists, amount sums exactly, no same-amount sibling collision with a disagreeing
   counterparty, revenue not booked on a settled invoice, document not already claimed by an earlier
   transaction, direction correct, no vendor→cost-account correction contradicted, no material missing
   document unflagged, no identical-payment fingerprint. Any failure **downgrades**. The guard catches
   fact-contradictions and the cost-account correction class; conventions that hinge on judgement
   (asset/owner-draw) and match re-points are held by the confidence gate plus the eval, and that line is
   stated rather than overclaimed. The guard can only downgrade, never rewrite, so the agent stays the
   decider and the floor stays strict.
4. **The eval measures it.** `eval.py` counts auto-posted-and-wrong against held-out ground truth and reports
   it as a first-class number, alongside accuracy and the learning lift. On the offline deterministic run it
   is **0**, and a regression test (`test_mock_run_holds_false_confidence_at_zero`) fails the build if it ever
   rises; on the real-LLM run the same number is measured. We hold the target by *measuring and gating* it,
   not by claiming it.

**Honest caveat.** The data is synthetic (Studio Vondel B.V., an 8-FTE Amsterdam studio, Q1 2026) and the
labels are ours, so the eval proves the **mechanism** and that false-confidence is held at zero on this set.
It does not prove a production-calibrated rate. That calibration is the first thing production hardening
buys (Part C).

### B4. And so the capacity story holds

Capacity 30 to 60 follows from the above, not from a separate trick. The confident bulk auto-posts untouched
(the labelled split is 84 auto / 13 review / 1 anomaly / 2 request-document), the queue ranking sends the
accountant's attention to the few uncertain and costly entries, and one correction flips the next same-vendor
ones immediately (proven offline: a Figma correction moves its two pending siblings from wrong to fully
correct, lift +1.0 on those rows; the cold→warm accuracy lift on real data is what the harness measures).
**Minutes saved** come from the auto-rate (entries never touched) plus the ranking (attention not wasted on
the safe bulk): on a worked model — baseline 2.0 min/txn, spot-check 0.2 min, review 1.5 min, 100
txns/customer/month, 84% auto — the auto-post step saves ~151 min/customer/month and the queue step ~8 min,
about **2.6 hours saved per customer per month**, of which the auto-post step is ~95% (the throughput lever)
and the ranking step is the trust lever that holds false-confidence at zero (DECK Slide 11; `B`, `R`, `V` are
assumptions, the 84% auto-rate is the measured input). The auto-rate grows as the correction memory grows,
which is how the curve continues toward 100+.

---

## Part C — Timelines and Resources

What it takes to make this real, from the working prototype to production on live customer financial data.

### C0. What exists today (the prototype)

A live, end-to-end prototype on the seeded Studio Vondel data, wired to a real LLM (Claude Sonnet 4.6 or
Gemini 2.5 Pro, swappable), all in `backend/`:

- the single-pass engine (ground, decide, guard, route) over 100 transactions, 10 invoices, 20 bills;
- the strict downgrade-only guard (account/amount/direction, same-amount collision, revenue-on-settled,
  duplicate claim, fingerprint duplicate, cost-account correction) and the two-confidence routing with the
  material × VAT corroboration gate;
- the learning loop (correct, persist to a runtime store with seeds read-only, re-run the pending
  same-vendor siblings);
- the FastAPI console API (run, queue, posted, accept, correct, explain, metrics, trace);
- a **no-build static web console** (`backend/ui/`, vanilla HTML/JS served by the same FastAPI app) — the
  review queue, the auto-posted tab, the decision card with accept/correct/explain, and the trace drawer;
- the eval harness reporting accuracy, false-confidence (0 offline, test-gated), per-outcome gates, routing
  counts, and the cold-versus-corrected lift, via a runnable CLI that writes a self-describing
  `eval_artifact.json` (agent, model id, date, denominator);
- a JSON `/trace/{id}` endpoint that reconstructs the full per-transaction record on demand (the prototype's
  debug surface and the clickable trace view).

This is the demo. It proves the mechanism. Everything below turns the mechanism into a product on real data.
(Logfire spans, multi-tenant auth + audit log, and a real follow-up "explain" LLM call are explicitly *not*
in the prototype — they are in the hardening list below.)

### C1. What to harden for production

| Area | Today (prototype) | Production hardening |
|------|-------------------|----------------------|
| **Ingestion** | JSON seeds loaded by `repository.py` | Real bank/PSD2 feeds, OCR'd documents, and the live ~96% provided-match source, validated at the boundary into the strict models, fail-closed on malformed input. |
| **Persistence** | In-memory repository over JSON; corrections in a runtime store | The real Postgres on GCP behind the same repository interface; the engine does not change, only the adapter. |
| **Correction / rule store** | All 5 corrections fit in the prompt | At scale (hundreds of vendors per customer), retrieve the relevant corrections (general always, vendor-filtered) so the prompt stays small; the cost-account guard still enforces that class. |
| **Confidence calibration** | Zero false-confidence on the synthetic set | Calibrate thresholds on a real labeled golden set; the cold rate will be lower than synthetic, so tune the high/medium/low bands until false-confidence holds at zero on real data before any auto-post is enabled. |
| **Security and audit** | Single-customer demo, no auth | Per-customer isolation (multi-tenant), auth/session, secrets management, PII handling, and an immutable audit log of every post, correction, and who signed off. GDPR posture; SOC 2 track. |
| **Explain** | Deterministic narration of the decision | A real follow-up LLM call for richer, conversational explanation, over the same trace. |
| **Observability and SLOs** | JSON `/trace/{id}` endpoint | Wire **Logfire** (the dependency is declared) for one span per transaction with the trace payload; alerting on false-confidence regressions, drift, and auto-rate drops; dashboards per accountant and per customer. |
| **Eval as a gate** | A script we run | A golden-set regression gate in CI that blocks any deploy (prompt, model, or code) that lowers accuracy or raises false-confidence. The eval becomes the safety mechanism, not a one-off. |
| **Rollout safety** | Engine auto-posts in the demo | Ship in **shadow mode** first: the agent proposes, the accountant signs everything, we measure the would-be auto-rate and false-confidence on live data with zero auto-posting, and only turn on auto-post for the high-confidence band once the number holds at zero. |

### C2. Resources (the hires)

A small, senior team is enough to take this to production. The engine is the valuable, already-built part.

- **AI / ML engineer** (owns the engine): prompts, the eval and golden set, model selection and the
  Sonnet-to-cheaper downgrade, calibration. This is the role I would fill.
- **Backend engineer**: ingestion adapters, the real Postgres, multi-tenant isolation, auth, API and audit
  hardening, Logfire wiring, the CI eval gate.
- **Frontend engineer**: productionize the accountant console (the prototype is a static page — harden it
  into the real client: queue, cards, correct/explain, trace) and later the entrepreneur surface.
- **A domain expert (Dutch bookkeeper / accountant) in the loop**, part-time but essential: builds and signs
  the labeled golden set, defines the accounting conventions and VAT-sensitivity weights, validates outputs.
  Without this role the eval has no trustworthy ground truth.
- **Later, as we scale past a handful of customers**: a part-time data/ML-ops engineer for the golden-set
  pipeline, drift monitoring, and the observability dashboards.

### C3. Rough timeline

A pragmatic path. Each phase ends on a gate that is a **measured number**, not a date.

- **Phase 0 — done (the prototype).** Engine, guard, learning loop, eval, console (API + static web app),
  JSON trace endpoint, wired to a real LLM on seeded data.
- **Phase 1 — pilot in shadow mode (roughly month 1 to 2).** Swap seeds for the live Postgres and ingestion
  adapters; build the labeled golden set with the accountant; wire Logfire and basic dashboards; run on 1 to
  3 real customers in shadow (propose-only, accountant signs everything). **Gate:** false-confidence at zero
  and a credible auto-rate on the golden set.
- **Phase 2 — auto-post on, hardened (roughly month 3 to 4).** Enable auto-post for the high-confidence band;
  ship retrieval for the correction store; multi-tenant, auth, audit log, security posture, the CI eval gate.
  **Gate:** false-confidence holds at zero on live data; the 30-to-60 capacity claim is visible in
  minutes-saved telemetry.
- **Phase 3 — scale and the entrepreneur surface (roughly month 5 to 9).** Roll out across the accountant
  base toward the 60-and-beyond curve; run the eval-driven model downgrade to control cost; add the
  entrepreneur conversation (Challenge 1) on the same engine; continuous calibration and drift monitoring.
  **Gate:** the capacity curve holds at scale with false-confidence still measured at zero.

The throughline is the same as the engine's: ship the strict, auditable, measurable thing, prove the number
that kills trust is held at zero, and let the auto-set grow as the system learns. Strict is the floor, never
a dial.
