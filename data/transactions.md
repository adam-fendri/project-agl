# 100 Bank Transactions — Studio Vondel B.V. (Q1 2026)

ING zakelijke rekening NL21INGB0001234567. Bank feed for Jan-Mar 2026.
Amounts: `-` = afschrijving (out), `+` = bijschrijving (in). EUR, Dutch decimal.

**Columns:** ID | date | amount | counterparty | omschrijving | **GT acct** (ground-truth
account) | **match** (invoice/bill or `-`) | **decision** (AUTO post / REVIEW / ANOMALY / REQUEST).

GT and decision are the labels for the eval. They are NOT shown to the agent; the agent
must derive them. "REVIEW" = genuinely uncertain (see planted-case notes at the bottom).

Client inflows that settle an issued invoice carry GT account **1300 Debiteuren** (the
receivable cleared), NOT 8000 Omzet: revenue is recognized when the invoice is issued
(Dr 1300 / Cr 8000), so the bank receipt only clears the receivable. No bank-feed line
books to 8000 (revenue lives off the feed, at invoicing). See DECISIONS D11.

## January

| ID | Date | Amount | Counterparty | Omschrijving | GT acct | Match | Decision |
|----|------|--------|--------------|--------------|---------|-------|----------|
| T001 | 01-02 | -4.235,00 | Kantoorpand Keizersgracht B.V. | SEPA Overboeking Huur jan 2026 | 4200 | B-01 | AUTO |
| T002 | 01-05 | -185,00 | Centraal Beheer | SEPA Incasso polis 8842 bedrijfsverz. | 4700 | B-14 | AUTO |
| T003 | 01-06 | -254,10 | Adobe Systems Ireland | SEPA Incasso ADOBE CREATIVE CLOUD | 4300 | - | AUTO |
| T004 | 01-06 | -217,80 | Figma Inc | SEPA Incasso FIGMA *PRO SEAT | 4300 | - | AUTO |
| T005 | 01-07 | -348,48 | Google Cloud EMEA | SEPA Incasso GOOGLE *GSUITE_studiov | 4300 | B-06 | AUTO |
| T006 | 01-07 | -96,80 | Slack Technologies | SEPA Incasso SLACK | 4300 | - | AUTO |
| T007 | 01-09 | +9.680,00 | Lumen Retail B.V. | SEPA Overboeking INV-2025-041 | 1300 | INV-2025-041 | AUTO |
| T008 | 01-09 | -8.420,00 | Belastingdienst | SEPA Overboeking OB Q4-2025 aangifte | 1510 | - | AUTO |
| T009 | 01-12 | -375,10 | Eneco | SEPA Incasso energie jan | 4210 | B-09 | AUTO |
| T010 | 01-12 | -78,50 | Café de Jaren Amsterdam | BEA Betaalpas 11-01 21:14 Pas003 | 4410 | - | REVIEW |
| T011 | 01-14 | -169,40 | KPN | SEPA Incasso internet/telefoon jan | 4510 | B-10 | AUTO |
| T012 | 01-15 | +15.125,00 | Kasa Tech B.V. | SEPA Overboeking INV-2025-042 | 1300 | INV-2025-042 | AUTO |
| T013 | 01-16 | -423,50 | Administratiekantoor Mol | SEPA Incasso boekhouding jan | 4710 | B-19 | AUTO |
| T014 | 01-19 | -89,95 | Coolblue | iDEAL bestelling 7741 toetsenbord | 4500 | - | AUTO |
| T015 | 01-20 | -42,35 | Vodafone Libertel | SEPA Incasso mobiel zakelijk | 4510 | - | AUTO |
| T016 | 01-21 | -1.250,00 | T. Bakker | SEPA Overboeking (geen omschrijving) | 0600 | - | REVIEW |
| T017 | 01-22 | -65,30 | Q-Park Amsterdam Centrum | BEA Betaalpas parkeren 22-01 | 4600 | - | AUTO |
| T018 | 01-23 | -52,99 | Bol.com | iDEAL kantoorartikelen | 4500 | - | AUTO |
| T019 | 01-26 | -3.300,00 | T. Bakker | SEPA Overboeking salaris jan 2026 | 4000 | - | AUTO |
| T020 | 01-26 | -3.600,00 | S. de Wit | SEPA Overboeking salaris jan 2026 | 4000 | - | AUTO |
| T021 | 01-26 | -3.350,00 | L. Jansen | SEPA Overboeking salaris jan 2026 | 4000 | - | AUTO |
| T022 | 01-26 | -2.950,00 | E. Visser | SEPA Overboeking salaris jan 2026 | 4000 | - | AUTO |
| T023 | 01-26 | -3.150,00 | D. Mulder | SEPA Overboeking salaris jan 2026 | 4000 | - | AUTO |
| T024 | 01-26 | -2.500,00 | F. Smit | SEPA Overboeking salaris jan 2026 | 4000 | - | AUTO |
| T025 | 01-26 | -3.050,00 | N. van Dijk | SEPA Overboeking salaris jan 2026 | 4000 | - | AUTO |
| T026 | 01-28 | -6.812,00 | Belastingdienst | SEPA Overboeking loonheffing jan | 1700 | - | AUTO |
| T027 | 01-29 | -4,25 | ING Bank N.V. | kosten zakelijk betaalpakket | 4720 | - | AUTO |
| T028 | 01-30 | -890,00 | Pensioenfonds PFZW | SEPA Incasso pensioen jan | 4020 | - | AUTO |
| T029 | 01-31 | -508,20 | Amazon Web Services EMEA | SEPA Incasso AWS invoice EU | 4310 | B-07 | AUTO |
| T030 | 01-31 | -54,45 | LinkedIn Ireland | iDEAL LNKD premium career | 4730 | - | REVIEW |

## February

| ID | Date | Amount | Counterparty | Omschrijving | GT acct | Match | Decision |
|----|------|--------|--------------|--------------|---------|-------|----------|
| T031 | 02-02 | -4.235,00 | Kantoorpand Keizersgracht B.V. | SEPA Overboeking Huur feb 2026 | 4200 | B-02 | AUTO |
| T032 | 02-03 | -375,10 | Eneco | SEPA Incasso energie feb | 4210 | - | AUTO |
| T033 | 02-04 | -2.662,00 | Amac Apple Premium Reseller | iDEAL MacBook Pro 14 M4 | 0150 | B-15 | REVIEW |
| T034 | 02-04 | -96,80 | Slack Technologies | SEPA Incasso SLACK | 4300 | - | AUTO |
| T035 | 02-05 | -169,40 | KPN | SEPA Incasso internet/telefoon feb | 4510 | - | AUTO |
| T036 | 02-06 | -41,20 | Albert Heijn 1342 | BEA Betaalpas 06-02 kantine | 4500 | - | REVIEW |
| T037 | 02-09 | -210,00 | Vimeo Inc | SEPA Incasso VIMEO PRO jaar | 4300 | - | AUTO |
| T038 | 02-10 | -27,50 | NS Groep | BEA Betaalpas trein 10-02 Pas003 | 4600 | - | AUTO |
| T039 | 02-12 | +4.235,00 | Mendo | SEPA Overboeking INV-2026-003 | 1300 | INV-2026-003 | AUTO |
| T040 | 02-12 | -7.865,00 | Studio Pixel | SEPA Overboeking factuur SP-2026-018 | 4100 | B-11 | AUTO |
| T041 | 02-13 | -119,00 | Sticker Mule | iDEAL custom stickers | 4400 | - | AUTO |
| T042 | 02-14 | -78,00 | Restaurant Bak | BEA Betaalpas 14-02 diner klant | 4410 | - | REVIEW |
| T043 | 02-16 | -2.904,00 | J. de Vries | SEPA Overboeking factuur 2026-03 | 4100 | B-12 | REVIEW |
| T044 | 02-17 | -149,00 | Mailchimp | SEPA Incasso MAILCHIMP MONTHLY | 4400 | - | AUTO |
| T045 | 02-18 | +5.072,00 | Brightseed B.V. | SEPA Overboeking INV-2026-002 | 1300 | INV-2026-002 | REVIEW |
| T046 | 02-19 | -7.865,00 | Studio Pixel | SEPA Overboeking factuur SP-2026-018 | 4100 | B-11? | ANOMALY |
| T047 | 02-20 | -240,00 | NS Groep Zakelijk | SEPA Incasso NS Business Card feb | 4600 | B-16 | AUTO |
| T048 | 02-23 | -34,99 | Spotify | SEPA Incasso SPOTIFY studio | 4900 | - | REVIEW |
| T049 | 02-24 | -4.500,00 | Bouwbedrijf de Groot B.V. | SEPA Overboeking aanbetaling verbouwing | 0100 | - | REQUEST |
| T050 | 02-25 | -3.300,00 | T. Bakker | SEPA Overboeking salaris feb 2026 | 4000 | - | AUTO |
| T051 | 02-25 | -3.600,00 | S. de Wit | SEPA Overboeking salaris feb 2026 | 4000 | - | AUTO |
| T052 | 02-25 | -3.350,00 | L. Jansen | SEPA Overboeking salaris feb 2026 | 4000 | - | AUTO |
| T053 | 02-25 | -2.950,00 | E. Visser | SEPA Overboeking salaris feb 2026 | 4000 | - | AUTO |
| T054 | 02-25 | -3.150,00 | D. Mulder | SEPA Overboeking salaris feb 2026 | 4000 | - | AUTO |
| T055 | 02-25 | -2.500,00 | F. Smit | SEPA Overboeking salaris feb 2026 | 4000 | - | AUTO |
| T056 | 02-25 | -3.050,00 | N. van Dijk | SEPA Overboeking salaris feb 2026 | 4000 | - | AUTO |
| T057 | 02-26 | -726,00 | LinkedIn Marketing Sol. | SEPA Incasso LNKD ADS campagne | 4400 | B-17 | AUTO |
| T058 | 02-27 | -6.812,00 | Belastingdienst | SEPA Overboeking loonheffing feb | 1700 | - | AUTO |
| T059 | 02-27 | -890,00 | Pensioenfonds PFZW | SEPA Incasso pensioen feb | 4020 | - | AUTO |
| T060 | 02-27 | -4,25 | ING Bank N.V. | kosten zakelijk betaalpakket | 4720 | - | AUTO |
| T061 | 02-27 | -62,00 | Greenwheels | SEPA Incasso autodelen feb | 4600 | - | AUTO |
| T062 | 02-28 | -562,65 | Amazon Web Services EMEA | SEPA Incasso AWS invoice EU | 4310 | B-08 | AUTO |
| T063 | 02-28 | -118,40 | bol.com zakelijk | iDEAL 2 monitorarmen | 4500 | - | AUTO |
| T064 | 02-28 | -250,00 | Stichting Dutch Design | iDEAL lidmaatschap 2026 | 4730 | - | AUTO |
| T065 | 02-28 | +680,00 | Eneco | SEPA Overboeking teruggave voorschot 2025 | 4210 | - | AUTO |

## March

| ID | Date | Amount | Counterparty | Omschrijving | GT acct | Match | Decision |
|----|------|--------|--------------|--------------|---------|-------|----------|
| T066 | 03-02 | -4.235,00 | Kantoorpand Keizersgracht B.V. | SEPA Overboeking Huur mrt 2026 | 4200 | B-03 | AUTO |
| T067 | 03-02 | -375,10 | Eneco | SEPA Incasso energie mrt | 4210 | - | AUTO |
| T068 | 03-03 | -544,50 | Google Ads | SEPA Incasso GOOGLE *ADS8821 | 4400 | B-18 | REVIEW |
| T069 | 03-03 | -96,80 | Slack Technologies | SEPA Incasso SLACK | 4300 | - | AUTO |
| T070 | 03-04 | -169,40 | KPN | SEPA Incasso internet/telefoon mrt | 4510 | - | AUTO |
| T071 | 03-05 | -254,10 | Adobe Systems Ireland | SEPA Incasso ADOBE CREATIVE CLOUD | 4300 | - | AUTO |
| T072 | 03-06 | +7.260,00 | Voss & Partners | SEPA Overboeking INV-2026-004 | 1300 | INV-2026-004 | REVIEW |
| T073 | 03-06 | -2.178,00 | M. Hendriks | SEPA Overboeking factuur MH26-7 tekst | 4100 | B-13 | AUTO |
| T074 | 03-09 | +7.260,00 | Lumen Retail B.V. | SEPA Overboeking betaling | 1300 | INV-2026-005 | REVIEW |
| T075 | 03-10 | -459,80 | Coolblue Zakelijk | iDEAL Dell UltraSharp 27 | 4500 | B-20 | AUTO |
| T076 | 03-11 | +3.375,90 | Kasa Tech B.V. | SEPA Overboeking facturen feb | 1300 | INV-2026-006+007 | REVIEW |
| T077 | 03-12 | -39,00 | Typeform | SEPA Incasso TYPEFORM basic | 4300 | - | AUTO |
| T078 | 03-13 | -88,00 | Hotel Casa Amsterdam | BEA Betaalpas 13-03 overnachting | 4600 | - | AUTO |
| T079 | 03-16 | -1.000,00 | T. Bakker | SEPA Overboeking (geen omschrijving) | 0600 | - | REVIEW |
| T080 | 03-17 | -132,00 | PostNL | SEPA Incasso verzendingen feb | 4900 | - | AUTO |
| T081 | 03-18 | -210,00 | KvK | SEPA Incasso handelsregister | 4900 | - | REVIEW |
| T082 | 03-19 | -67,50 | Picnic | iDEAL kantoor lunch team | 4500 | - | REVIEW |
| T083 | 03-20 | -445,00 | Drukkerij Tielen | iDEAL drukwerk portfolio | 4400 | - | AUTO |
| T084 | 03-23 | -1.815,00 | Webflow Inc | SEPA Incasso WEBFLOW enterprise jr | 4300 | - | AUTO |
| T085 | 03-24 | -29,00 | Notion Labs | SEPA Incasso NOTION team | 4300 | - | AUTO |
| T086 | 03-25 | -3.300,00 | T. Bakker | SEPA Overboeking salaris mrt 2026 | 4000 | - | AUTO |
| T087 | 03-25 | -3.600,00 | S. de Wit | SEPA Overboeking salaris mrt 2026 | 4000 | - | AUTO |
| T088 | 03-25 | -3.350,00 | L. Jansen | SEPA Overboeking salaris mrt 2026 | 4000 | - | AUTO |
| T089 | 03-25 | -2.950,00 | E. Visser | SEPA Overboeking salaris mrt 2026 | 4000 | - | AUTO |
| T090 | 03-25 | -3.150,00 | D. Mulder | SEPA Overboeking salaris mrt 2026 | 4000 | - | AUTO |
| T091 | 03-25 | -2.500,00 | F. Smit | SEPA Overboeking salaris mrt 2026 | 4000 | - | AUTO |
| T092 | 03-25 | -3.050,00 | N. van Dijk | SEPA Overboeking salaris mrt 2026 | 4000 | - | AUTO |
| T093 | 03-26 | -6.900,00 | Belastingdienst | SEPA Overboeking loonheffing mrt | 1700 | - | AUTO |
| T094 | 03-27 | -890,00 | Pensioenfonds PFZW | SEPA Incasso pensioen mrt | 4020 | - | AUTO |
| T095 | 03-27 | -4,25 | ING Bank N.V. | kosten zakelijk betaalpakket | 4720 | - | AUTO |
| T096 | 03-27 | -890,00 | Stipt Service B.V. | SEPA Overboeking factuur 99213 | 4900 | - | REQUEST |
| T097 | 03-30 | -149,00 | Mailchimp | SEPA Incasso MAILCHIMP MONTHLY | 4400 | - | AUTO |
| T098 | 03-30 | -62,00 | Greenwheels | SEPA Incasso autodelen mrt | 4600 | - | AUTO |
| T099 | 03-31 | -315,00 | Figma Inc | SEPA Incasso FIGMA *ORG extra seats | 4300 | - | AUTO |
| T100 | 03-31 | -22,99 | Dropbox | SEPA Incasso DROPBOX business | 4300 | - | AUTO |

## Tally

- **AUTO** (confident, auto-post): 81
- **REVIEW** (uncertain, queue): 16 -> T010, T016, T030, T033, T036, T042, T043, T045, T048, T068, T072, T074, T076, T079, T081, T082
- **ANOMALY**: 1 -> T046
- **REQUEST_DOCUMENT** (missing counterpart, ask the entrepreneur for the document): 2 -> T049, T096

81 + 16 + 1 + 2 = 100. Confident rate = 81% on this DELIBERATELY-HARD set.
90%+ is the PRODUCTION target reached as the correction loop learns the customer's
conventions (the demo shows the mechanism, not a rigged 90% on synthetic data).

## Planted-case notes (why each REVIEW/ANOMALY is genuinely hard)

- **T010 / T042** restaurant & café: representation (`4410`) vs staff catering (`4500`)
  vs private. Intent not in the data.
- **T016 / T079** `T. Bakker` round transfers, no omschrijving: owner's draw (`0600`,
  NOT an expense) and must be told apart from his salary (T019/T050/T086 -> `4000`).
- **T030** LinkedIn premium: subscription (`4730`) vs marketing (`4400`).
- **T033** MacBook (EUR2.662, net ~EUR2.200): capitalize as asset (`0150`) vs expense as
  supplies (`4500`). Threshold judgment. (T075 Dell monitor EUR459,80 = ~EUR380 net is
  BELOW the ~EUR450 line -> clear immediate expense `4500`, so it auto-posts; no longer a
  threshold judgment.)
- **T036 / T082** Albert Heijn `kantine` & Picnic `kantoor lunch team`: staff catering /
  team lunch. This chart has NO staff-catering line -> `4410` Representatie is *client*
  entertainment, `4500` office supplies is not food, `4900` is the catch-all. No account
  truly fits, so the agent must DEFER to review rather than force-fit; GT `4500` is provisional.
- **T043** `J. de Vries` SEPA transfer that looks exactly like the 7 salary lines but
  is a freelancer (`4100`, has bill B-12).
- **T045** Brightseed pays EUR5.072 against the EUR5.082 invoice: match with a EUR10
  tolerance or flag the short-pay?
- **T046** Studio Pixel paid a SECOND time (identical to T040) -> duplicate payment,
  the headline anomaly. Bill B-11 was already settled.
- **T048 / T081** Spotify & KvK `handelsregister` fee: judgment-call defers. Spotify reads
  as a `4730` subscription or `4300` software yet may be ambient/private; the KvK
  Chamber-of-Commerce levy sits between `4730` contributies and `4900` overige kosten.
  Genuinely uncertain -> review; GT `4900` for both.
- **T049** EUR4.500 to a builder with NO bill on file -> missing counterpart. This is a
  MATERIAL document gap, so the outcome is `REQUEST_DOCUMENT` (ask the entrepreneur for the
  bill), distinct from a low-stakes missing-counterpart that merely defers to REVIEW. (GT
  acct `0100` Inventaris is provisional, pending the requested invoice; a building
  renovation is a tangible fixed asset, NOT `0150` Computers & hardware.)
- **T068** `GOOGLE *ADS` (`4400`) vs the GOOGLE Workspace charge T005 (`4300`): same
  vendor root, two accounts. Naive vendor-mapping fails.
- **T072 / T074** two separate EUR7.260 inflows -> which clears INV-004 vs INV-005?
  T074's omschrijving is just "betaling" (no invoice ref), so amount alone is ambiguous.
- **T076** one EUR3.375,90 inflow clears TWO invoices (INV-006 + INV-007).
- **T096** transfer to an unknown counterparty citing an invoice number (`factuur 99213`)
  with NO bill on file -> the document is referenced but missing, so the outcome is
  `REQUEST_DOCUMENT` (ask the entrepreneur to supply invoice 99213).

## Provided matches (Neno infra)

Per-transaction match/no-match decisions are ~96% accurate across the 100 transactions
(4 planted errors: T046 duplicate, T072 collision, T074 swap, T076 split). On the subset of
POSITIVE match assertions alone, ~85% are exactly right at the document-set level -- so the
agent must VERIFY every provided match, not trust it. Full accounting in `matches.md`.

Note: T003/T004 (Adobe/Figma Jan direct debits) carry NO bill match -- those bills were not
ingested, like the other recurring-SaaS months (T034/T069/T071/T099). Bills B-04/B-05 are now
two UNPAID open payables (see `cast_and_documents.md` s.3).
