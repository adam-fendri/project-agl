# Cast + Documents — Studio Vondel B.V. (Q1 2026)

Parties the studio trades with, plus the 10 invoices issued and 20 bills received.
The 100 bank transactions (next artifact) will reconcile against these.

Amounts grounded in 2025 benchmarks (within real ranges, not exact quotes):
office rent Amsterdam ~EUR2.2-4k/mo; Dutch dev/designer gross ~EUR69-78k/yr;
freelance ZZP ~EUR72-92/hr; agency projects ~EUR3.5-25k. Sources in s.5.

---

## 1. The cast

### Owner / director (DGA)
- **Tijn Bakker** — founder & creative director. Monthly DGA salary (~EUR4,700 gross,
  gebruikelijk loon). Also takes occasional **privé-opnamen** (owner draws) -> `0600`.
  ⚠️ his draw looks like a transfer/salary but is NOT an expense.

### Employees (payroll, 6) — monthly net salary -> `4000`
- Sanne de Wit (senior designer), Lars Jansen (developer), Emma Visser (UX designer),
  Daan Mulder (developer), Femke Smit (junior designer), Noa van Dijk (PM/strategist).
- Plus one monthly **loonheffing** payment to Belastingdienst -> `1700`/`4010`.

### Clients (invoiced -> money in)
| Client | Type | Notes |
|---|---|---|
| Lumen Retail B.V. | retail brand | repeat client (2 invoices) |
| Kasa Tech B.V. | startup | repeat client (3 invoices) |
| Gemeente Haarlem | municipality | pays slowly -> stays UNPAID |
| Brightseed B.V. | scale-up | short-pays by EUR10 |
| Mendo | concept store | clean |
| Voss & Partners | law firm | gross collides with Lumen |
| NorthBridge Ltd (UK) | foreign | export, 0% VAT, UNPAID |

### Suppliers (bills -> money out) and the account each maps to
| Supplier | Account | Note |
|---|---|---|
| Kantoorpand Keizersgracht | `4200` Rent | monthly |
| Adobe / Figma / Slack | `4300` Software | recurring |
| Google Workspace | `4300` Software | ⚠️ same "Google" as Ads |
| Google Ads | `4400` Marketing | ⚠️ same "Google" as Workspace |
| AWS | `4310` Hosting | "Amazon" but is hosting |
| Eneco | `4210` Utilities | |
| KPN | `4510` Phone & internet | |
| Studio Pixel (freelance dev) | `4100` Freelance | ⚠️ PAID TWICE -> anomaly |
| J. de Vries (freelance motion) | `4100` Freelance | ⚠️ name looks like a salary |
| Mark Hendriks (freelance copy) | `4100` Freelance | |
| Centraal Beheer | `4700` Insurance | ⚠️ NO reclaimable BTW (exempt + assurantiebelasting) |
| Amac | `0150` Equipment | ⚠️ MacBook = asset vs supplies |
| NS Business | `4600` Travel | ⚠️ 9% VAT, not 21% |
| LinkedIn Ads | `4400` Marketing | |
| Administratiekantoor Mol | `4710` Accounting | |
| Coolblue | `4500` Office supplies | ⚠️ monitor = supplies vs asset |
| Bouwbedrijf de Groot | (none) | ⚠️ office reno, NO bill on file -> missing counterpart |
| Lichtdruk Amsterdam | `4400` Marketing/print | bill B-04, received UNPAID (open AP, no Q1 payment) |
| Juridisch Bureau Zuidas | `4710` Accounting/admin | bill B-05, received UNPAID (open AP, no Q1 payment) |

---

## 2. The 10 invoices issued (accounts receivable)

VAT 21% unless noted. Gross = net x 1.21.

Accrual basis: revenue (8000 Omzet) and the receivable (1300 Debiteuren) are booked when
the invoice is ISSUED (Dr 1300 / Cr 8000). The later client bank inflow only CLEARS the
receivable (Dr 1100 Bank / Cr 1300), so the bank-feed GT account for every invoice-settling
inflow is **1300**, never 8000 — booking it to 8000 would double-count Q1 omzet and output
BTW. (See DECISIONS D11.)

| Invoice | Client | Date | Net | VAT | Gross | Status |
|---|---|---|---|---|---|---|
| INV-2025-041 | Lumen Retail | 2025-12-18 | 8,000 | 1,680 | **9,680** | PAID (Jan 9) |
| INV-2025-042 | Kasa Tech | 2025-12-22 | 12,500 | 2,625 | **15,125** | PAID (Jan 15) |
| INV-2026-001 | Gemeente Haarlem | 2026-01-12 | 18,000 | 3,780 | **21,780** | **UNPAID** |
| INV-2026-002 | Brightseed | 2026-01-20 | 4,200 | 882 | **5,082** | PAID SHORT (5,072, -10) Feb 18 |
| INV-2026-003 | Mendo | 2026-01-28 | 3,500 | 735 | **4,235** | PAID (Feb 12) |
| INV-2026-004 | Voss & Partners | 2026-02-05 | 6,000 | 1,260 | **7,260** | PAID (Mar 6) |
| INV-2026-005 | Lumen Retail | 2026-02-16 | 6,000 | 1,260 | **7,260** | PAID (Mar 9) |
| INV-2026-006 | Kasa Tech | 2026-02-20 | 1,790 | 375.90 | **2,165.90** | PAID combined (Mar 11) |
| INV-2026-007 | Kasa Tech | 2026-02-23 | 1,000 | 210 | **1,210** | PAID combined (Mar 11) |
| INV-2026-008 | NorthBridge Ltd | 2026-02-27 | 5,000 | 0 (export) | **5,000** | **UNPAID** |

### Planted reconciliation cases (AR side)
1. **Amount collision:** INV-004 and INV-005 are both **EUR7,260**. Two separate
   EUR7,260 inflows arrive (Mar 6, Mar 9). The agent must use date/sender to decide
   which inflow clears which invoice, not amount alone.
2. **One payment, two invoices:** Kasa pays INV-006 + INV-007 in ONE transfer of
   **EUR3,375.90**. One inflow must reconcile to two documents.
3. **Short payment:** INV-002 billed EUR5,082, Brightseed pays **EUR5,072** (-EUR10).
   Match with a tolerance, or flag the EUR10? Judgment.
4. **Unpaid (no inflow):** INV-001 (EUR21,780) and INV-008 (EUR5,000) have no payment.
   The agent must NOT invent a match. These are the open receivables.

---

## 3. The 20 bills received (accounts payable)

| Bill | Supplier | Date | Net | VAT | Gross | Account | Status |
|---|---|---|---|---|---|---|---|
| B-01 | Kantoorpand (rent Jan) | 2026-01-01 | 3,500 | 735 | 4,235 | `4200` | PAID |
| B-02 | Kantoorpand (rent Feb) | 2026-02-01 | 3,500 | 735 | 4,235 | `4200` | PAID |
| B-03 | Kantoorpand (rent Mar) | 2026-03-01 | 3,500 | 735 | 4,235 | `4200` | PAID |
| B-04 | Lichtdruk Amsterdam (print run) | 2026-03-25 | 1,250 | 262.50 | 1,512.50 | `4400` | **UNPAID** |
| B-05 | Juridisch Bureau Zuidas (legal advice) | 2026-03-26 | 1,600 | 336 | 1,936 | `4710` | **UNPAID** |
| B-06 | Google Workspace | 2026-01-06 | 288 | 60.48 | 348.48 | `4300` ⚠️ | PAID |
| B-07 | AWS (Jan) | 2026-01-31 | 420 | 88.20 | 508.20 | `4310` | PAID |
| B-08 | AWS (Feb) | 2026-02-28 | 465 | 97.65 | 562.65 | `4310` | PAID |
| B-09 | Eneco | 2026-01-10 | 310 | 65.10 | 375.10 | `4210` | PAID |
| B-10 | KPN | 2026-01-12 | 140 | 29.40 | 169.40 | `4510` | PAID |
| B-11 | Studio Pixel (freelance dev) | 2026-02-10 | 6,500 | 1,365 | 7,865 | `4100` | PAID ⚠️ twice |
| B-12 | J. de Vries (freelance motion) | 2026-02-14 | 2,400 | 504 | 2,904 | `4100` ⚠️ | PAID |
| B-13 | Mark Hendriks (freelance copy) | 2026-03-05 | 1,800 | 378 | 2,178 | `4100` | PAID |
| B-14 | Centraal Beheer (insurance) | 2026-01-08 | 185 | 0 (exempt) | 185 | `4700` ⚠️ | PAID |
| B-15 | Amac (MacBook Pro) | 2026-02-03 | 2,200 | 462 | 2,662 | `0150` ⚠️ | PAID |
| B-16 | NS Business (travel) | 2026-02-20 | 220.18 | 19.82 (9%) | 240 | `4600` ⚠️ | PAID |
| B-17 | LinkedIn Ads | 2026-02-25 | 600 | 126 | 726 | `4400` | PAID |
| B-18 | Google Ads | 2026-03-02 | 450 | 94.50 | 544.50 | `4400` ⚠️ | PAID |
| B-19 | Administratiekantoor Mol | 2026-01-15 | 350 | 73.50 | 423.50 | `4710` | PAID |
| B-20 | Coolblue (monitor) | 2026-03-10 | 380 | 79.80 | 459.80 | `4500` ⚠️ | PAID |

**Open accounts payable:** B-04 and B-05 are received but **UNPAID** at quarter-end (the
studio pays them in Q2), so NO Q1 bank transaction settles them — they are the open AP. The
other 18 bills were paid within Q1. (The Jan Adobe/Figma direct debits T003/T004 therefore
carry no bill match, like the other recurring-SaaS months.)

---

## 4. Planted hard-case map (what each thing tests)

**Categorization traps (right account is non-obvious):**
- `Google Workspace` (B-06) vs `Google Ads` (B-18): same "Google", `4300` vs `4400`.
- `J. de Vries` freelance (B-12) vs the 6 named salaries: looks like payroll, is `4100`.
- Owner privé-opname vs salary vs freelancer: `0600` (not an expense).
- `Amac` MacBook (B-15) `0150` asset vs `Coolblue` monitor (B-20) `4500` supplies: capitalize or expense?
- VAT-rate realism: insurance (B-14) exempt/no BTW; NS travel (B-16) 9% not 21%.
- The catch-all `4900`: the agent must resist dumping ambiguous items here.

**Reconciliation traps (AR, see s.2):** amount collision; one-payment-two-invoices;
short payment; unpaid (no match).

**Anomalies (in the transactions, next artifact):**
- **Headline = duplicate payment:** Studio Pixel (B-11, EUR7,865) paid TWICE (Feb 12 & 19).
- **Missing counterpart:** EUR4,500 to Bouwbedrijf de Groot, NO bill on file ->
  triggers the brief's "request the bill from the entrepreneur" decision.

---

## 5. Grounding sources (benchmarks)
- Office rent Amsterdam (EUR2.2-4k/mo small private office): skepp.com, edgeworkspaces.com
- Dutch dev/designer gross salary (~EUR69-78k/yr): glassdoor, payscale, salaryexpert
- Freelance ZZP rates (designer ~EUR72/hr, dev ~EUR92/hr): knab.nl (bieb), xolo.io
- Agency project pricing (branding EUR5-15k, web EUR2.5-20k): yhad.nl, sortlist
- VAT: 21% standard / 9% transport / insurance exempt: belastingdienst.nl, business.gov.nl
