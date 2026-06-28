# 5 Prior Accountant Corrections — Studio Vondel B.V.

These are corrections the accountant made on this customer **before** Q1 2026. The agent
has them as memory from the start. Each one is not a one-off fix: it establishes a **rule**
that should move every matching transaction (the brief's "one correction moves the next 10").

## How to read the impact
- **Cold agent** (ignores corrections): 84 AUTO / 14 REVIEW / 2 ANOMALY (see transactions.md).
- **With these 5 corrections applied:** 8 of the 14 REVIEW cases become confident ->
  **92 AUTO / 6 REVIEW / 2 ANOMALY.**
- That **84% -> 92%** lift IS the measurable demonstration of learning. The eval reports
  both numbers. A live correction in the demo pushes it further.
- Honest note on "next 10": in this single quarter each rule moves 1-2 transactions; the
  rule generalises to ALL future matching transactions, which over a year is >10. The
  mechanism scales; the quarter is just the sample.

## The 5 corrections

### C1 — Freelancer payments -> 4100 (not 4000 wages)
- **Past fix:** a SEPA transfer to "J. de Vries" was booked as Salaris (`4000`); accountant
  moved it to Inhuur freelancers (`4100`), noting de Vries is not on payroll.
- **Rule:** a personal-name SEPA transfer that is NOT one of the 7 payrolled employees,
  and has a freelance invoice ref, is a freelancer -> `4100`.
- **Moves in Q1:** T043 (J. de Vries) REVIEW -> AUTO. Reinforces T040, T046, T073.

### C2 — GOOGLE *ADS -> 4400 marketing (not 4300 software)
- **Past fix:** a "GOOGLE *ADS" charge was booked as Software (`4300`); accountant moved it
  to Marketing (`4400`).
- **Rule:** same vendor root "GOOGLE" splits by product: `*ADS` -> `4400` marketing;
  `*GSUITE`/Workspace -> `4300` software.
- **Moves in Q1:** T068 (Google Ads) REVIEW -> AUTO. (T005 GWS stays `4300`.)

### C3 — Hardware with net value >= EUR450 -> 0150 asset (not 4500 supplies)
- **Past fix:** a laptop was booked as Office supplies (`4500`); accountant capitalised it
  to Equipment (`0150`), citing the capitalisation threshold.
- **Rule:** hardware with **net** value >= ~EUR450 is an asset (`0150`, depreciated);
  below that, office supplies (`4500`).
- **Moves in Q1:** T033 (MacBook, net EUR2.200) REVIEW -> AUTO asset; T075 (monitor, net
  EUR380) REVIEW -> AUTO supplies. One rule, resolves both directions.

### C4 — Owner off-cycle round transfers -> 0600 privé-opnamen (not an expense)
- **Past fix:** a round EUR-transfer to "T. Bakker" with no omschrijving was booked as a
  cost; accountant moved it to Privé-opnamen (`0600`).
- **Rule:** a transfer to the owner that is NOT the fixed monthly salary (off-cycle date,
  round amount, no omschrijving) is an owner draw -> `0600`, never an expense.
- **Moves in Q1:** T016, T079 REVIEW -> AUTO `0600`. Monthly salary lines (T019/T050/T086)
  stay `4000`.

### C5 — Equal-amount invoices: match by counterparty, not amount
- **Past fix:** infra had matched a payment to the wrong invoice when two open invoices
  shared an amount; accountant re-pointed it to the invoice whose client equals the payer.
- **Rule:** when >1 open invoice shares the same amount, disambiguate by the **paying
  counterparty**, not amount alone.
- **Moves in Q1:** T072 -> INV-004 (Voss), T074 -> INV-005 (Lumen), correcting the infra
  collision + swap (matches.md W2/W3). REVIEW -> AUTO.

## Net effect
C1..C5 flip 8 REVIEW cases to AUTO: T016, T033, T043, T068, T072, T074, T075, T079.
Remaining 6 REVIEW (genuinely hard, no rule covers them yet): T010 & T042 (restaurant:
representation vs staff vs private), T030 (LinkedIn subscription vs marketing), T045
(EUR10 short-payment), T076 (combined two-invoice payment), T096 (unknown new vendor).
These are where the human's attention still adds the most value, and where the NEXT live
correction in the demo will teach the agent.
