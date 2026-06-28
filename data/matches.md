# Provided Matches (Neno infra, ~96% accurate) — Studio Vondel B.V.

Neno's infrastructure proposes a transaction<->document match for each reconcilable
transaction. The agent receives these as a PRIOR to VERIFY, not as truth. It must catch
the wrong ones.

## How the number is honest (two figures, both computed from the seeds)

The infra makes a match/no-match DECISION for every one of the 100 transactions. A row in
`provided_matches.json` is a POSITIVE match assertion; the absence of a row is a "no document
matches" decision. There are 26 positive assertions and 74 (implicit) no-match decisions.

- **Per-transaction match-decision accuracy = 96/100 = ~96%.** Of all 100 decisions, 96 are
  correct (22 correct positive matches + 74 correct no-matches) and 4 are the planted errors
  below. This is the brief's "~96% accurate" number, and it is the accuracy of the matching
  SYSTEM across the feed. Every term is derivable from `ground_truth.json` (no hand-waved true
  negatives); `build_seeds.py` computes and prints it.
- **Precision on the POSITIVE matches = 22/26 = ~85%.** Of the 26 matches the infra actually
  ASSERTS, 4 are wrong. So the agent faces a ~15% error rate on the matches it is GIVEN — which
  is precisely why it must verify every provided match (counterparty + amount), not trust it.

(The earlier "96% on the matched set" was the dishonest version: it reached 96% only by counting
the 74 no-match transactions as true negatives without recording them. Both numbers are now stated.)

## Rule
For every transaction that settles a document, the provided match EQUALS ground truth EXCEPT the
4 planted failures below. T003/T004 (Adobe/Figma Jan direct debits) have no provided match — those
bills were never ingested, like the other recurring-SaaS months — so the positive set is 26 rows.

## The 4 wrong matches (one per failure mode)

### W1 — duplicate / false match (T046)
- **Infra says:** T046 (-EUR7.865, Studio Pixel, 02-19) reconciles **B-11**.
- **Truth:** B-11 was **already settled by T040** (-EUR7.865, 02-12). T046 is a SECOND identical
  payment -> a duplicate, no valid counterpart.
- **How the agent catches it:** B-11 is already paid; a second payment to the same payee/amount
  within a week is a duplicate. -> ANOMALY, not a match.

### W2 — amount collision (T072)
- **Infra says:** T072 (Voss & Partners, +EUR7.260) -> **INV-2026-005**.
- **Truth:** INV-005 was issued to **Lumen**; INV-004 to **Voss**. T072 should clear **INV-004**.
  Both invoices are EUR7.260, so the infra collided on amount and picked the wrong same-amount one.
- **How the agent catches it:** amounts are identical, so amount alone is useless; the PAYER is Voss
  but INV-005's client is Lumen -> mismatch. Match by counterparty (exactly what correction C5 teaches).

### W3 — swap (T074)
- **Infra says:** T074 (Lumen Retail, +EUR7.260) -> **INV-2026-004**.
- **Truth:** T074 should clear **INV-2026-005** (Lumen's invoice). Together with W2 this is the swap:
  infra handed Voss's invoice to Lumen's payment and vice-versa.
- **How the agent catches it:** the payer is Lumen; INV-004's client is Voss -> counterparty mismatch.

### W4 — incomplete / split match (T076)
- **Infra says:** T076 (+EUR3.375,90, Kasa) reconciles **INV-2026-006 (EUR2.165,90)** only.
- **Truth:** the payment covers **INV-006 + INV-007** (EUR2.165,90 + EUR1.210 = EUR3.375,90).
- **How the agent catches it:** EUR3.375,90 != EUR2.165,90; the EUR1.210 remainder equals INV-007
  exactly -> one payment covers two invoices, leaving INV-007 wrongly open if not caught.

## Correct match, but flag the amount gap (T045) — NOT a wrong match
- **Infra says:** T045 (+EUR5.072, Brightseed) reconciles **INV-2026-002 (EUR5.082)**.
- **Truth:** the document id is **CORRECT** (it is INV-002), so this is NOT one of the 4 errors and
  does not lower precision. The skill here is amount tolerance: the payment is EUR10 short, so the
  agent should match the invoice but FLAG the EUR10 gap (partial payment) for the accountant rather
  than silently closing it. (`ProvidedMatch` carries no "paid in full" field, so the "marked paid"
  wrongness is recomputed from the amount gap, not asserted in the match row.)

## Why these four
Each trains a different reconciliation skill: duplicate detection (W1), amount-collision and
counterparty disambiguation (W2/W3), and split/combined matching (W4). The other 22 positive matches
are correct, so the agent must ALSO not "find problems" where none exist (avoid false positives), and
T045 must be matched-with-a-flag, not rejected.
