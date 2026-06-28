# Chart of Accounts — Studio Vondel B.V.

Customer: **Studio Vondel B.V.**, an 8-person web & branding studio in Amsterdam.
Period modelled: **Q1 2026 (Jan-Mar)**. Charges 21% VAT, files BTW quarterly.

## Grounding (honest provenance)

- **Numbering** = Studio Vondel's own 4-digit numbering. RGS explicitly allows a
  business to keep its own numbering (verified: referentiegrootboekschema.nl).
- **RGS column** = each account is mapped to its real RGS **group** reference code,
  verified from the live RGS scheme (boekhoudplaza RGS MKB decimal schema + B/W groups).
- **Grounding level = RGS group (level 3), not the 5-digit leaf code.** The full RGS
  is 1194 lines; mapping every account to an exact leaf code was deliberately skipped
  as out-of-proportion for an input artifact. Group-level mapping is defensible:
  every account rolls up to a real RGS group.
- 4 balance items (debiteuren, crediteuren, BTW x2, loonheffingen) show the RGS group
  by NAME; exact leaf code marked `~` = to confirm if needed. Not fabricated.
- ⚠️ = deliberate "trap" account: it exists so a specific hard categorization case has
  a real competing answer (see notes). Without these, the agent's uncertainty is fake.

## Rubriek 0 — Vaste activa & eigen vermogen (fixed assets & equity)

| Nr | Account (NL) | English | RGS group | Notes |
|----|------|---------|-----------|-------|
| 0100 | Inventaris | Equipment & furniture | `BMva` | asset |
| 0150 | Computers & hardware | Computers & hardware | `BMva` | ⚠️ asset vs office supplies (4500) |
| 0200 | Afschrijving inventaris | Accumulated depreciation | `BMva` | balance contra |
| 0500 | Eigen vermogen | Owner's equity | `BEiv` | |
| 0600 | Privé-opnamen | Owner's drawings | `BEiv` | ⚠️ owner takes money; NOT an expense |

## Rubriek 1 — Financieel (bank, receivables, payables, VAT)

| Nr | Account (NL) | English | RGS group | Notes |
|----|------|---------|-----------|-------|
| 1100 | Bank — ING zakelijk | Business bank account | `BLimBanRba` | the bank feed (verified leaf) |
| 1300 | Debiteuren | Accounts receivable | `BVor` ~ | money clients owe |
| 1600 | Crediteuren | Accounts payable | `BSch` ~ | money owed to suppliers |
| 1500 | Te vorderen BTW | Input VAT (reclaimable) | `BVor` ~ | |
| 1510 | Af te dragen BTW | Output VAT (payable) | `BSch` ~ | |
| 1700 | Loonheffingen te betalen | Payroll tax payable | `BSch` ~ | |

## Rubriek 4 — Kosten (costs; most categorization happens here)

| Nr | Account (NL) | English | RGS group | Notes |
|----|------|---------|-----------|-------|
| 4000 | Brutolonen | Gross wages & salaries | `WPer` | ⚠️ vs freelancers (4100) |
| 4010 | Sociale lasten | Employer social security | `WPer` | |
| 4020 | Pensioenlasten | Pension contributions | `WPer` | |
| 4100 | Inhuur freelancers | Freelance / subcontractor | `WPer` | ⚠️ vs wages (4000) vs owner draw (0600) |
| 4200 | Huur kantoor | Office rent | `WBed` | |
| 4210 | Servicekosten & nuts | Service charges & utilities | `WBed` | |
| 4300 | Software & licenties | Software & licenses | `WBed` | ⚠️ vs marketing (4400), vs IT (4310) |
| 4310 | Hosting & IT | Hosting & IT infrastructure | `WBed` | |
| 4400 | Marketing & advertenties | Marketing & advertising | `WVkf` | ⚠️ Google Ads vs Google Workspace (4300) |
| 4410 | Representatiekosten | Representation / client entertainment | `WVkf` | ⚠️ vs staff lunch, vs private (0600) |
| 4500 | Kantoorbenodigdheden | Office supplies | `WBed` | ⚠️ vs hardware asset (0150) |
| 4510 | Telefoon & internet | Phone & internet | `WBed` | |
| 4600 | Reiskosten | Travel costs | `WBed` | ⚠️ vs representation (4410) |
| 4700 | Verzekeringen | Insurance | `WBed` | |
| 4710 | Administratie- & accountantskosten | Accounting & admin fees | `WAkf` | |
| 4720 | Bankkosten | Bank charges | `WBed` | small fees; (RGS: WBed/WFbe) |
| 4730 | Abonnementen & contributies | Subscriptions & memberships | `WBed` | |
| 4800 | Afschrijvingskosten | Depreciation expense | `WAfs` | the P&L side of 0200 |
| 4900 | Overige kosten | Miscellaneous / other costs | `WBed` | ⚠️ the catch-all to resist overusing |

## Rubriek 8 — Omzet (revenue)

| Nr | Account (NL) | English | RGS group | Notes |
|----|------|---------|-----------|-------|
| 8000 | Omzet ontwerp & development | Design & dev service revenue | `WOmz` | client payments land here |
| 8010 | Omzet consultancy | Consultancy revenue | `WOmz` | |
| 8100 | Overige opbrengsten | Other income | `WOvb` | |

## Rubriek 9 — Financieel resultaat

| Nr | Account (NL) | English | RGS group | Notes |
|----|------|---------|-----------|-------|
| 9000 | Rentebaten & -lasten | Interest income / expense | `WFbe` | |
| 9100 | Koersverschillen | FX differences | `WFbe` | for a foreign-currency payment |

## Note

This chart is canonical but may gain or lose an account as we design the 100
transactions (if a transaction needs an account not here, or an account ends up unused).
~33 accounts is realistic for an 8-FTE Dutch agency.
