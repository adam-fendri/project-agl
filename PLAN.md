# Project AGL — Challenge 2 Plan

> Accountant-supervised transaction categorization + reconciliation, for Neno (a fintech SaaS).
> The agreed design, end to end, readable in one pass. Source brief: `BRIEF.md`.
> Decision log + full rationale: `DECISIONS.md`. (Personal job challenge, NOT VoxAI work.)

## 1. What we're building
A live prototype of the accountant-side agent. It reads each bank transaction, decides which
chart-of-accounts account it belongs to and which invoice/bill it settles, flags anomalies, and
**auto-posts what it is sure of** while **deferring the rest** to a human queue ordered by where the
accountant's attention is worth most. It **learns** from the accountant's corrections. Wired to a real
LLM (Claude or Gemini), running on the seeded data.

## 2. The one principle everything follows
- **The agent (the LLM) decides** — the account, the match, the anomaly, and its own confidence.
- **Code grounds and guards** — it computes the verifiable facts and hands them to the agent (ground),
  and it refuses to auto-post anything a hard fact contradicts (guard). Code never makes the decision.
- This is a **money system**: correct by default, strict is the floor, never confidently wrong.
  Simplicity is welcome only where it costs no correctness.

## 3. The engine — what happens to one transaction
Four steps per transaction:
1. **Ground (code):** assemble the agent's evidence — the transaction, the chart of accounts, the
   provided match + any reconciliation candidates with their computed facts (amount vs the document
   total, direction, the document's paid/unpaid status), the relevant corrections, vendor history.
2. **Decide (the agent, ONE structured-output LLM call):** the agent reads the evidence and outputs the
   vendor, the account (+ reasoning), the matched document(s) (+ reasoning), an anomaly if any, and
   **two confidences** — one for the categorization, one for the reconciliation.
3. **Guard (code, strict):** before auto-posting, check the decision against hard facts — the account
   exists; the matched amount sums exactly (else flag partial); the document isn't already paid by
   another transaction (else duplicate); direction is right; no prior correction is contradicted; no
   material missing document is unflagged. Any failure → **downgrade to review** (never rewrite the
   agent's choice).
4. **Route:** anomaly → anomaly queue; material missing doc → request from the entrepreneur; **both**
   confidences high AND the guard passes → auto-post; otherwise → review.

**Categorize vs reconcile.** Categorize (the account) is the easier bulk plus a tail of hard
ambiguities (Google Workspace vs Ads, freelancer-vs-salary, asset-vs-supplies, owner-draw) where the
corrections and the agent's judgment carry it. Reconcile (the match) is the structurally hard one: the
matches come **provided at ~96%**, so the agent's job is **verify-first** — check the provided match,
catch the ~4% wrong, and only search from scratch for the wrong/incomplete/missing ones (the collision,
the combination, the short-pay). Code does the exact arithmetic (an LLM can't be trusted with sums); the
agent decides which document, using the counterparty/reference it reads from the messy string.

**Confidence (two, not one).** A transaction is two decisions with different evidence and different ways
to be wrong, so one number would be unsafe or lossy. It auto-posts only if **both** are high and
corroborated; the card headline = the weaker one with the reasoning naming which part is shaky;
false-confidence is measured **per job** so we know which is the weak link.

**Never confidently wrong.** The confidence is the agent's, but **grounded** in real facts and
**required to be corroborated** by code's verified signals; the strict guard catches the rare "sure and
wrong"; the eval measures it. Target: **zero** false-confidence on the set.

**Settlement is given, not derived.** Documents carry their paid/unpaid status (given metadata). The
duplicate is a document **claimed by two transactions** in the provided matches, plus the paid status —
surfaced to the agent, who decides the later one is the duplicate. No runtime ledger.

**The learning loop (one correction → the next similar ones).** The accountant **corrects** a transaction
on the card (a dropdown: pick the right account, or re-point the match — no coding). The system **builds
the correction** by joining the vendor *the agent already identified* with the accountant's pick, and
**confirms the scope** in plain language ("apply to all this vendor?"). A correction is a *convention* —
a vendor mapping, a condition, a threshold, or a matching rule. It is **saved to memory**; from then on
the relevant ones are pulled into the agent's evidence and the agent applies them by reasoning; the
system **re-runs the pending similar ones** so they flip immediately ("N similar updated"); the guard
backstops any miss. **Prompt stays small at scale:** general conventions stay in the prompt always (few),
vendor-specific ones are filtered by vendor, and the exact guard guarantees a correction is never
silently dropped.

## 4. The accountant console
- A **review queue** ranked by where attention is worth most (likely-wrong × costly; anomalies pinned).
- The **auto-posted set** sitting with reasoning visible to spot-check, not touched one by one — that
  untouched bulk is the capacity gain.
- Each item is a **card**: the agent's choice, its reasoning, the sources (the verified facts), the two
  confidences. Actions: **accept** (post), **correct** (the dropdown fix → triggers learning), **explain**
  (a deterministic, code-built narration of the decision — NOT a second LLM call; a real follow-up call is
  the planned next step). Anomaly cards add the **next action** (request the bill, flag the duplicate).

## 5. The eval (real numbers)
Run the engine over the 100, compare to the **held-out ground truth**, report: categorization accuracy,
reconciliation accuracy, **false-confidence** (auto-posted-and-wrong, target 0), deferral quality (caught
the 1 labelled anomaly — the duplicate — and the 2 material missing-document requests, no false
positives), per-outcome gates, and the **cold-vs-corrected lift** as the learning proof. The lift
*mechanism* is proven offline (a Figma correction moves its 2 siblings, +1.0 on those rows); the
cold→warm accuracy figure is harness-measured per run and stamped with the model id + date in
`eval_artifact.json` — no fixed "84 → 92" is asserted as a produced result. Honest caveat: synthetic data
+ our labels, so it proves the **mechanism** + that false-confidence is held at zero, not a
production-calibrated rate.

## 6. Stack & tooling (defensible, one line each)
- **Model:** a strong frontier model (Claude or Gemini) for the agent; the eval tests whether a cheaper
  one holds the accuracy.
- **Orchestration:** our own deterministic pipeline + pydantic-ai for the single structured-output call —
  single-pass, no agent framework, because the per-transaction flow is fixed, not an agentic loop
  (tool-calling is reserved for the entrepreneur side).
- **Retrieval & context:** the relevant corrections pulled into the prompt (general always, vendor
  filtered), with an exact guard so a missed retrieval can't cause a wrong post.
- **Evals:** the harness above — accuracy, false-confidence, the lift.
- **Observability:** in the prototype, a JSON `/trace/{id}` endpoint reconstructs the full per-transaction
  record (context, prompt, raw output, guard verdict, confidence, decision); the console's trace drawer
  renders it and the eval reads the same structure. Logfire — one span per transaction with that payload —
  is the production observability step (the dependency is declared), NOT wired in the prototype.

## 7. Backend / frontend
Python + FastAPI, **API-first** (the engine behind a clean API); a **decoupled web UI** that is just a
client of the API, so the UI choice is reversible. The prototype ships a no-build static console (vanilla
HTML/JS served by the same app); React is one production option, not what was built.

## 8. Deliverables
- The **live prototype** on the seeded data, wired to a real LLM.
- A **one-page architecture diagram**: agent topology, the **tool boundary** (LLM-decides | code-grounds-
  and-guards), where the **human sits** (the queue), where **context comes from** (the repository + memory).
- A **deck (<15 slides) or 7-min video**.
- The **stated assumptions** (model capability, data quality, the accountant's role) and the
  **timelines + resources** answer to the guiding question.

## 9. The outcomes story (what we claim, and how we hold it)
- **Capacity 30 → 60:** the accountant only touches the uncertain few + the anomalies; the confident bulk
  auto-posts. Minutes saved come from the auto-rate + the queue ranking sending attention where it counts.
- **False-confidence ~0:** held by grounding + the strict guard, measured by the eval.
- **Learning:** one correction moves the next same-vendor ones (re-run), shown live; the mechanism is
  proven offline (+1.0 on the Figma siblings) and the cold→warm accuracy lift is harness-measured, not a
  fixed asserted figure.

## 10. Build order (once this plan is signed off)
1. Domain model + repository + seeds (DONE).
2. Grounding (assemble evidence + the reconcile candidate search) — partly DONE.
3. The agent call (the prompt + the structured Proposal, wired to a real LLM).
4. The guard + routing + the settlement/duplicate check.
5. The learning loop (correction → memory → re-run).
6. The FastAPI API.
7. The eval harness + the numbers.
8. The console UI.
9. The deliverables (diagram, deck, assumptions, timelines).
