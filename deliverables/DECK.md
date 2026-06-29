# Project AGL — Challenge 2

Accountant-supervised transaction categorization and reconciliation, wired to a real LLM, running on the seeded data. One section below = one slide. Plain language: a non-AI reader can follow every decision.

---

## Slide 1 — Title

**Project AGL: an accountant can sign off on every entry, and never sees the AI confidently get it wrong.**

- The accountant-side agent reads each bank transaction, decides the bookkeeping account and the invoice/bill it settles, flags anomalies, auto-posts what it is sure of, and defers the rest to a human queue.
- One sentence: **the agent (the LLM) decides, code grounds the facts and guards the post.**
- Live prototype on the seeded data (100 transactions, 10 invoices, 20 bills, a 35-account Dutch SME chart, 5 prior accountant corrections), wired to Claude or Gemini, with a working web console.

---

## Slide 2 — The problem and the bar

- **The goal:** lift one accountant from 30 to 60 customers (and stay on the curve to 100+). The only way to do that is to stop touching the confident bulk by hand and spend attention only on the few that are genuinely uncertain.
- **The constraint that defines the product:** this is a money system. A wrong post flows into VAT and filings. The number that kills trust is **false confidence**: the agent was sure and wrong. Our target: **zero on reconciliation and on any material entry, with a small measured residual on immaterial categorisation** — measured every run, never faked to a flat zero.
- **The job per transaction is two decisions:** which account it belongs to (categorize), and which document it settles (reconcile). They are hard in different ways and can be wrong in different ways.
- **The deal we make:** correct by default, strict is the floor not a dial. We would rather defer an extra transaction to a human than auto-post one we cannot stand behind.

---

## Slide 3 — The one principle: the agent decides, code grounds and guards

This is the tool boundary the whole architecture hangs on.

- **The agent (the LLM) decides** the account, the match, the anomaly, and its own confidence. Code never makes the call.
- **Code GROUNDS:** it computes the verifiable facts (the amount versus the document total, the payment direction, which candidate documents are still open as of the transaction's date, whether a correction applies) and hands them to the agent as evidence. The agent decides on facts, not guesses, so its confidence is well founded.
- **Code GUARDS:** a strict backstop. Before anything auto-posts, code checks the agent's decision against hard facts. If a fact contradicts it, code can only **downgrade** it (auto-post becomes review), **never rewrite** the agent's choice.
- Why this split: the brief is explicit that these are the agent's decisions and the agent's confidence, and that code's role is grounding and guarding to prevent hallucinations. Grounding makes the confidence real; the guard holds "never confidently wrong" without code becoming the decider.

---

## Slide 4 — The engine: one transaction, four steps

Every transaction runs the same fixed, auditable path.

1. **Ground (code):** assemble the evidence. The transaction, the chart of accounts, the provided match plus any reconciliation candidates with their computed facts (amount vs total, direction, open/closed as of this date), the relevant corrections, vendor history, and a duplicate note if the same document is claimed twice.
2. **Decide (the agent, one structured-output call):** the agent reads the evidence and returns one typed proposal: vendor, account (plus a one-sentence reason), the matched document id(s) (plus a reason), an anomaly if any, and **two confidences** (one for the account, one for the match).
3. **Guard (code, strict):** check the proposal against hard facts — account exists; the matched amount sums exactly (else partial); no same-amount sibling collision with a disagreeing counterparty; an issued invoice's settlement is not re-booked as revenue; the document is not already claimed by an earlier transaction; direction is right; no vendor→cost-account correction is contradicted; no material missing document is left unflagged; no earlier identical payment fingerprint. Any failure downgrades the route.
4. **Route:** anomaly → anomaly queue; a material missing document → a request to the entrepreneur; **both** confidences high **and** the guard passes → auto-post; everything else → review. A material, VAT-sensitive entry whose counterparty does not corroborate is downgraded even at self-high confidence.

---

## Slide 5 — Categorize vs reconcile (verify-first)

The two halves of the decision are hard for different reasons, so we treat them differently.

- **Categorize (the account):** an easy bulk plus a tail of genuine ambiguities. Examples from the data: a personal-name transfer that is a freelancer cost, not payroll; "GOOGLE *ADS" (marketing) vs "GOOGLE *GSUITE" (software); a hardware purchase that is an asset, not supplies; an owner draw, not salary. The corrections and the agent's reading of the messy bank string carry these.
- **Reconcile (the match) is the structurally hard one.** The matches arrive **already provided at about 96% accuracy** from Neno's infrastructure. So the agent's job is **verify-first**: treat the provided match as a strong but fallible prior, confirm the counterparty and amount both agree, and only when they do not, search the other candidates for the right document (a same-amount collision, two documents cleared by one payment, a short-pay). The prompt names no quota and no error rate — it is told to verify, not to go hunting for a fixed number of failures.
- **Division of labour:** **code does the exact arithmetic** (an LLM cannot be trusted to sum money), the **agent decides which document** the counterparty and reference point to. The agent reasons over numbers code already computed.

---

## Slide 6 — Two confidences and the strict guard (never confidently wrong — the measured target)

- **Two confidences, not one.** A transaction is two decisions with different evidence and different failure modes. One blended number would be either unsafe or lossy. The agent rates the account and the match separately (high / medium / low).
- **Auto-post requires both confidences high and the guard clean** (a material entry that lacks corroboration is downgraded regardless of self-confidence). The card headline shows the weaker of the two, with reasoning that names which part is shaky, so a reviewer's eye lands on the real risk.
- **What the guard actually backstops.** Fact contradictions: account-not-in-chart, amount not summing exactly, a same-amount sibling collision (the failure mode that produced the old confidently-wrong posts), revenue booked on a settled invoice, a document already claimed earlier, wrong direction, an identical-payment fingerprint, and the **vendor→cost-account** correction class. Conventions that hinge on judgement (asset vs supplies, owner-draw) and match re-points are **not** guard-enforced — they are held by the confidence gate plus the eval, and that boundary is stated honestly, not papered over.
- **Never confidently wrong is measured, not asserted.** The eval counts auto-posted-and-wrong per run, split by task. **Reconciliation and material entries: zero, every run.** Categorisation false-confidence is **1–3 (mean 2) across three runs, all immaterial (≤€210)** — and inspecting them, they are ground-truth-weakness or judgment-calls, not clear model errors. Held by grounding + the guard + calibration + the human, and reported every run rather than claimed.
- **Settlement is given, not derived.** Documents carry their own paid/unpaid status. A duplicate is a document claimed by two transactions in the provided matches plus that status, surfaced to the agent, who decides the later one is the duplicate. No runtime ledger to drift.

---

## Slide 7 — The learning loop (one correction moves the next N)

The accountant corrects on the card, in plain language. No coding.

- **The fix is a dropdown:** pick the right account, or re-point the match. The system builds the correction by joining the **vendor the agent already identified** (a canonical key, never the raw IBAN) with the accountant's pick.
- **Corrections are written to a runtime store, not the seed.** The committed fixtures stay read-only; a money system does not mutate its own data as runtime state. From then on the relevant corrections are pulled into the agent's evidence, and the agent applies them by reasoning.
- **It moves the next ones immediately.** The system re-runs the pending same-vendor transactions so they flip on the spot ("N similar re-run"), instead of only fixing the one in front of the accountant. Proven two ways: a unit test (`test_lift_report_measures_correction_gain_on_eligible_rows`) asserts the same-vendor siblings move, and the eval's cold→warm lift measures it end-to-end at **+0.50** on the eligible rows.
- **The guard backstops the cost-account class.** If retrieval ever drops a vendor→cost-account correction, the guard still enforces it, so that known fix is never silently lost. (Asset/owner-draw conventions and match re-points are not in that class — they defer to review rather than auto-post.)
- **It stays small at scale.** General accounting lessons live in the prompt always (few of them); vendor-specific corrections are filtered by vendor so the prompt does not bloat as corrections grow.

---

## Slide 8 — The accountant console (the live prototype)

What the supervising accountant actually sees and clicks — a working, no-build static web app served by the same FastAPI app, talking only to the API.

- **A review queue ranked by where attention is worth most:** likely-wrong times costly (probability of error × euro value × VAT-sensitivity). Anomalies are pinned to the top. Not lowest-confidence-only, not biggest-euro-only.
- **An auto-posted tab** with reasoning visible to spot-check, not touched one by one. That untouched bulk is the capacity gain.
- **Every item is a card:** the agent's choice, its one-line reasoning, the sources (the verified signals code computed and the documents read), and the two confidences.
- **Three actions:** **accept** (post it), **correct** (the dropdown fix that triggers the learning loop and reports "N similar re-run"), **explain** (a deterministic, code-built narration of the decision — not a second LLM call; a real follow-up model call is a small next step, not claimed today). Anomaly cards add the **next action**: request the bill, flag the duplicate.
- **A trace drawer** on every card: the grounded context, the exact prompt, the raw model proposal, and the guard verdict.
- API-first: the engine sits behind a clean REST API (`POST /run`, `GET /queue`, `GET /posted`, `GET /transaction/{id}`, `POST /transaction/{id}/accept`, `POST /transaction/{id}/correct`, `POST /transaction/{id}/explain`, `GET /metrics`, `GET /trace/{id}`), so the UI is a swappable client.

---

## Slide 9 — The eval numbers (what is produced, and how)

Run the engine over all 100, compare to the held-out ground truth, report real numbers. The harness (`scripts/run_eval.py`) runs the batch twice — corrections suppressed (cold), then applied (warm) — and writes a self-describing `eval_artifact.json` (agent, model id, date, denominator).

- **Real-LLM run, three times** (Claude Sonnet 4.6, all 100, k=3 for the non-determinism): categorisation **0.93–0.96**, reconciliation **25/25 (1.000 every run)**, routing **~84% auto / ~13 review / 1 anomaly / 2–3 request**, **false-confidence 1–3 (mean 2), all immaterial (≤€210)**. Inspecting those few: a Spotify subscription where the agent's account is arguably more correct than the label, a KvK fee that is a genuine judgment call, and a staff lunch the chart has no proper account for — **none a clear model error.** The reconciliation side, which has hard facts to guard, is a stable zero.
- **Per-outcome gates** (precision/recall against ground truth) are scored for auto-post, review, anomaly, and request-document — so over-deferral and missed anomalies are both visible, not just headline accuracy.
- **The numbers above are k=3** because the LLM is non-deterministic — a single run is a point estimate, and false-confidence swung 1–3 across the three runs. The harness stamps each run's `eval_artifact.json` with agent, model id, date, and denominator, and we report the range, not one lucky draw.
- **Deferral quality on the labelled set:** ground truth is **81 auto / 16 review / 1 anomaly** (the duplicate) / **2 request-document** (the two material missing-document cases). The eval scores whether the engine catches that 1 anomaly with no false positives (it does, every run) and routes the 2 requests correctly — not "two anomalies."
- **The honest caveat:** synthetic data (Studio Vondel B.V., Q1 2026) and our own labels, so the eval proves the **mechanism** — reconciliation held exact, the small categorisation residual immaterial and inspected — not a production-calibrated accuracy rate. On real, messier data day one defers more; the auto-set grows as the system learns.

---

## Slide 10 — Tooling: the five choices, each defended

- **Model:** a strong frontier model (Claude Sonnet 4.6, or Gemini 2.5 Pro behind the same interface) for the single interpretation call. **Defence:** the precision bar is high (errors hit VAT and filings), so capability beats per-call cost; cost is softened because rule-covered transactions need less of the model, and the eval tests whether a cheaper model (Flash) holds the accuracy before we downgrade.
- **Orchestration:** our own deterministic pipeline, with pydantic-ai wrapping the one structured-output call. **No agent framework.** **Defence:** the per-transaction flow is fixed (one LLM step), not an open-ended agentic loop, so a framework's flexibility is unused; ours stays auditable, simple, and one call per transaction. Tool-calling is reserved for the entrepreneur side, where it is genuinely needed.
- **Retrieval and context:** the relevant corrections pulled into the agent's evidence (general always, vendor-filtered), with the cost-account guard behind that class. **Defence:** the agent decides with the convention in front of it, and a missed retrieval of a vendor→cost-account fix still cannot cause a wrong post because the guard enforces it.
- **Evals:** the harness above, scoring categorization, reconciliation, false confidence (k=3 for the non-determinism), per-outcome gates, and the cold-vs-corrected lift. **Defence:** false confidence is the number that kills trust, so we measure it per run as a range, not a claim; the lift is the concrete proof that learning works.
- **Observability:** two layers. A **JSON `/trace/{id}` endpoint** reconstructs the full per-transaction record (grounded context, exact prompt, raw model output, guard verdict, confidence signals, final decision) — deterministic, rendered in the console's clickable trace drawer; and **Logfire is wired** (env-gated to a project-only token, content scrubbed) — it auto-instruments the LLM call (model, tokens, latency, retries), wraps the `claude -p` path, and spans the pipeline. **Defence:** the trace record is the debug + audit surface; Logfire is the queryable backend, off by default so no credentials leak. **Production plan:** dashboards and alerting on false-confidence regressions and drift.

---

## Slide 11 — Capacity: minutes saved per customer per month

A **model** with stated inputs (replace with telemetry), not a measured production result. The auto-rate is the one input we measure on the data; the per-task minutes are assumptions.

- **Inputs:** baseline manual handling `B = 2.0 min/txn` (read the line, pick the account, find and verify the document, post); spot-check an auto-posted card `s = 0.2 min`; review a deferred entry with the agent's pre-work already done `R = 1.5 min`; volume `V = 100 txns/customer/month`; auto-rate `a` (measured: **~0.84**, k=3 on the warm run).
- **Two levers:**
  - **Auto-post lever** saves `B − s = 1.8 min` per auto-posted entry → `1.8 × 0.84 × 100 ≈ 151 min/month`.
  - **Queue pre-work + ranking lever** saves `B − R = 0.5 min` per deferred entry → `0.5 × 0.16 × 100 ≈ 8 min/month`, plus the unpriced quality of sending scarce attention to the costly/uncertain first.
- **Worked figure:** ≈ **159 minutes (~2.6 hours) saved per customer per month**; baseline 200 min/customer drops to ~41, about **4.8×** on this step.
- **Which step cuts most:** the **auto-post step delivers ~95% of the minutes** (151 of 159) — it is the throughput lever and the engine of 30→60. The **queue-ranking step delivers the small remainder in raw time but is the trust lever** — it spends scarce attention where a mistake is both likely and costly, which is how false-confidence stays low. Learning grows `a` over time, pushing the curve toward 100+.
- **Caveat:** `B`, `s`, `R`, `V` are assumptions pending real telemetry; only `a` is measured (and on real data day-one `a` is lower, rising as corrections accumulate). The durable claims are the formula and "auto-rate dominates minutes, ranking holds trust."

---

## Slide 12 — Outcomes, assumptions, timelines

**The outcomes we claim and how we hold them.**

- **Capacity 30 to 60:** the accountant only touches the uncertain few and the anomalies; the confident bulk auto-posts; the queue ranking sends attention where a mistake is both likely and costly (Slide 11).
- **False confidence held low:** zero on reconciliation and material entries; a small, measured, immaterial residual on categorisation (1–3 of 100, k=3) — held by grounding + the guard + calibration + the human, measured every run.
- **Learning:** one correction moves the next same-vendor ones, re-run live; the mechanism is unit-tested, and the cold→warm lift measures it at **+0.50** on the eligible rows.

**Stated assumptions.**

- **Model capability:** a strong LLM can interpret messy bank strings well enough to be the primary categorizer, gated by grounding and the guard.
- **Data quality:** real bank data is messy and inconsistent, so the system is built to verify, not to trust inputs (the provided matches are ~96% accurate but fallible — which is exactly why the agent verifies every one rather than trusting it).
- **The accountant's role:** supervise the uncertain, correct the misses, sign off. The agent is the worker; the accountant is the final supervision layer.
- **Latency vs accuracy vs trust:** the accountant side is batch, so we trade latency for accuracy and trust. Speed lives on the entrepreneur side (the coffee-cooling conversation).

**Timelines and resources (prototype to production).**

- **Now (prototype, built):** engine, guard, learning loop, eval with the cold/warm harness (k=3), FastAPI console API, the static web console, the JSON trace endpoint, **Logfire instrumentation (env-gated)**, on the seeded data, wired to a real LLM.
- **Next (hardening):** real Postgres ingestion, scale the correction store with retrieval, calibrate confidence on real data, **Logfire dashboards + alerting** on false-confidence/drift, multi-tenant + audit log, the eval as a CI release gate.
- **Resources:** a small team (one or two backend/AI engineers plus a frontend engineer), an accountant in the loop for labeling and validation, and the eval as the release gate that protects the zero-false-confidence bar as scale grows.
