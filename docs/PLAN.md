# Project AGL — Build Plan

Grounded in the brief (the PDF) and verified Dutch conventions (RGS / Belastingdienst).
Prompt-first for agent behaviour; code only for hard facts. The standard (ground truth +
chart) is grounded before anything is measured against it; the capabilities the edge cases
demand are built next; measured per task; deliverables last.

## Phase 1 — Ground the standard (until it is right, every number lies)
- 1.1 Correct contested GT labels against verified conventions, per case, each sourced.
  Genuine judgment calls (two-plus defensible accounts) -> REVIEW, never an account rewrite.
  Clear errors -> the convention.
- 1.2 Missing-account cases stay as the test for "no listed account fits -> the agent must
  defer", not patched by silently adding accounts.
- 1.3 A small taxonomised edge-case set, one clean case per scenario, so the eval tests
  capabilities rather than a flat pile.

## Phase 2 — The capabilities the edge cases demand (prompt-first)
- 2.1 No-fit -> defer. The agent recognises no listed account genuinely fits -> rates LOW +
  signals it -> review. (prompt + one output field + routing)
- 2.2 Anomaly agent-vs-code split. Remove duplicate-detection from the prompt (the agent
  cannot see other transactions); code owns duplicates; the agent flags only
  single-transaction signals. (prompt) Fixes the over-fire.
- 2.3 Private-vs-business. A private/owner spend from the BV is a rekening-courant item, not
  a cost -> flag/defer. (prompt)

## Phase 3 — The precision bar + the learning loop
- 3.1 VAT dimension. The output carries the VAT treatment (rate + deductibility); the brief's
  precision bar is reconciliation, VAT, audit. Mixed costs carry the deductibility limit.
  (schema + prompt + eval) — largest piece.
- 3.2 New-account learning. When a no-fit case is reviewed and the accountant assigns or
  creates an account, the system learns it and propagates to the cohort.
  (console + learning + chart)

## Phase 4 — Measure honestly, then ship
- 4.1 Re-measure per task on the grounded GT, k/N for the non-deterministic parts.
- 4.2 Separate the eval harness from the runtime.
- 4.3 Deliverables (deck, one-page diagram, tooling rationale) — last.

## Sequence
Core-first: Phase 1 -> 2.1 -> 2.2 -> 3.1 (VAT) -> 2.3 / 3.2 -> Phase 4.
