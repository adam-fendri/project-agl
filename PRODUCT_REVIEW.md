# PRODUCT REVIEW — Neno Challenge 2 (Agentic General Ledger)

Lead-reviewer consolidation of eleven dimension reviews, re-verified against the live code and the committed `backend/eval_artifact.json` on 2026-06-28. Deterministic checks only (no `claude -p` eval was launched).

---

## 1. VERDICT

This is a **proof-of-concept with senior-grade design instincts, not a shippable SaaS** — and right now it is not safe to submit as one. The deterministic core is clean (strict-typed, `Decimal` money, frozen Pydantic, downgrade-only guard, an honest cold-vs-warm lift harness) and the routine bulk of categorization is genuinely good (0.91 cat / 0.99 match on the committed run), but every production gate a fintech reviewer blocks on is absent: no database (the posted ledger lives in a RAM set), no auth, no audit trail, single-tenant id collisions, and the default/benchmarked agent is a `claude -p` subprocess that cannot run as a service. It is **multiple weeks-to-months of focused work** from a real product: roughly two weeks to fix the correctness/trust defects, a month-plus to build the persistence/auth/audit/observability backbone, plus the required PDF/video that does not yet exist.

**The single biggest risk to a senior interview** is not any one bug — it is that the deliverables stake the central trust claim ("false-confidence held at 0, test-gated by `test_mock_run_holds_false_confidence_at_zero`") on a test, a `MockAgent`, and a repro command that **do not exist**, while the committed artifact shipped beside them reports **false_confidence = 1**. In a money system, naming a fabricated safety gate as the guarantee for "the number that kills trust" reads as exactly the confidently-wrong failure the brief warns against, and is disqualifying until reconciled. The good news: the gap is an honesty-pass and ~2 focused fixes wide, not an architecture rewrite — the *shape* of the answer (agent decides, code grounds + guards, guard may only downgrade, two independent confidences, batch-accountant vs interactive-entrepreneur) is right.

---

## 2. THE PRODUCTION GAP (what makes this a demo, not a product)

Each item is the kind of thing a senior infra/security reviewer flags before reading a line of model logic.

| # | Gap | Evidence | Fix | Rough effort |
|---|-----|----------|-----|--------------|
| P1 | **No durable storage — the posted ledger is an in-memory `set`.** A restart or every `/run` wipes all auto-posted + accountant-accepted entries; "posted" is an accounting act, so this is silent financial-data loss. | `api.py:154-156` (`_decisions`/`_posted` in process memory), `api.py:166` (`_posted.clear()` on every run); no postgres/sqlite/orm anywhere | Postgres on GCP (the stated prod DB): tenant-scoped tables for decisions + an append-only postings ledger; fail-closed FK constraints at the boundary | 1–2 wks |
| P2 | **No authentication or authorization on any endpoint.** `/run`, `/posted`, `/transaction/{id}/accept`, `/correct`, `/trace/{id}` (full prompt + financial context) are wide open — anyone on the port reads every transaction, posts ledger entries, and rewrites the learning store. | `api.py:256-318`; grep for `Depends`/`Authorization`/`HTTPBearer` in `agl/` → **empty** | Auth middleware (OIDC/session) + per-route authz; bind accountant identity to every mutation | 3–5 days |
| P3 | **No immutable audit trail of who accepted/corrected/posted.** `accept()` is a bare `self._posted.add(...)` — no actor, timestamp, or before→after. `Correction` has `created_at` but no actor. A ledger must be append-only and attributable. | `api.py:185-188`; `models.py:125-136` (no actor field) | Append-only audit table; actor+timestamp+before/after on every accept/correct/post; immutable storage | 3–5 days |
| P4 | **The default + benchmarked agent is a `claude -p` subprocess, not the shippable client.** Selected by default when no API key is set; the committed numbers were produced by it (`"agent":"claude"`). It spawns a process per transaction at `cwd="/tmp"`, passes financial PII as argv, has **no timeout** on `communicate()` (a hung `claude` hangs the request forever), no rate/cost control, and needs an interactive Claude subscription on the host — uncontainerizable. So the headline metrics validate a path that won't run in prod. | `api.py:60-66` (default `ClaudeCliAgent()`); `agent.py:134-156`; `eval_artifact.json` metadata `"agent":"claude"` | Make API-backed `LlmAgent` the only prod path; quarantine `ClaudeCliAgent` behind a dev flag; never put PII in argv; per-call timeout + backoff; re-run the eval through the API client | 2–4 days + re-eval |
| P5 | **Single-tenant by-id indexes leak across customers.** Repository indexes are keyed on bare id (`T001`, `INV-2026-001`); ids are per-customer sequential, so a second tenant guarantees a key collision and silent overwrite. `customer_id` is on every model but no accessor scopes by it. | `repository.py:73-77, 93-112`; `build_seeds.py:28` hardcodes one customer; `_console` global at `api.py:257` | Composite `(customer_id, id)` keys + tenant resolved from auth context per request; per-tenant repository/chart/model | 3–5 days (mechanical, schema instinct already correct) |
| P6 | **No observability despite the brief naming it.** `logfire>=2.6` is declared but never imported/configured; the `/trace` endpoint *recomputes* the decision on demand rather than replaying a recorded one, so it can diverge from what actually posted (esp. after a `correct()` mutates repo state). | `pyproject.toml:11` vs grep `import logfire` → empty; `api.py:226-241` rebuilds evidence + re-runs guard | Wire `logfire.configure()` + instrument FastAPI/pydantic-ai; persist the real prompt/raw output/verdict at decision time and render those verbatim | 2–4 days |
| P7 | **Corrections store is non-atomic and not concurrency-safe.** `save()` is a full-file `write_text` (no temp+rename, no fsync, no lock) — a crash mid-write corrupts the entire learned-knowledge file; the per-process `asyncio.Lock` doesn't protect against `>1` uvicorn worker, and ids are `f"L{len+1}"` so concurrent corrections mint the same id. | `repository.py:49-55`; `learning.py:107` | Atomic temp+`os.replace` (interim) → DB rows with a sequence/UUID id; row-level append, not whole-file rewrite | 1–2 days interim, folds into P1 |
| P8 | **Not a git repo; no CI; test/type tooling undeclared.** `neno-challenge/` has no `.git`; `pytest`/`pyright` are absent from `pyproject.toml` and the venv, so `uv run pytest`/`pyright` fail out of the box (every reviewer had to inject `--with pytest`). The "shippable" bar has no version control and no build that runs the 42 tests. | `git rev-parse` → "not a git repository"; `pyproject.toml` has `[project]`+`[tool.pyright]` only, no dev group | `git init`; add a `dependency-groups`/dev extra with pytest+pyright; a CI job that runs both with thresholds | 1 day |
| P9 | **The required submission artifact does not exist.** The brief mandates a <15-slide PDF *or* a ≤7-min video screen-share. `deliverables/` holds only three `.md` files; no `*.pdf/*.mp4/*.mov/*.pptx` anywhere; the architecture "diagram" is a Mermaid code block. You cannot submit per the brief as-is. | `deliverables/` listing; repo-wide `find` for slide/video formats → empty | Export `DECK.md` → <15-slide PDF, render Mermaid → one-page image, record the 7-min walkthrough | 0.5–1 day |
| P10 | **Console metrics + trace are demo artifacts that can't exist in prod.** The metrics bar scores categorization %, match %, and `false_confidence` against `ground_truth.json` — in prod the accountant *is* the label, so the endpoint 500s without a GT seed. The eval oracle is co-located with the live fixtures and loaded by the runtime `Repository`. | `api.py:302-308`, `app.js:104-120`; `repository.py:68,77,114-115` loads `ground_truth.json` | Live bar shows throughput/auto-rate/review-rate/correction-rate; accuracy/FC stay in the offline eval surface; move GT to a `tests/`-only fixture never built by the runtime repo | 1–2 days |
| P11 | **Product run path is sequential, single-flight, no isolation.** `run_batch` is a plain `for … await` loop under a process-wide `asyncio.Lock`; one raised LLM error 500s the whole `/run` with no partial results. The retry/bounded-concurrency/failure-isolation logic exists only in the offline `LiftHarness`, not the engine the API calls — so the product path is *more* fragile than the eval path, contradicting the deck's "runnable concurrently" latency defense. | `engine.py:45-52`; `api.py:162-167`; vs `eval.py:249-274` | Move the harness pattern into the engine (bounded concurrency + per-txn capture-and-continue); make `/run` a job/queue with progress (SSE), not a blocking request | 2–3 days |

---

## 3. CRITICAL correctness issues (deduped, ranked by interview impact)

These are the trust/precision defects a senior reviewer running the repo would flag. Ranked by how much each damages a money-system hiring decision.

**C1 — The named trust mechanism is fabricated, and the deck's headline numbers are contradicted by the artifact shipped beside them.**
The deck/architecture/assumptions stake "false-confidence held at 0" on `test_mock_run_holds_false_confidence_at_zero` and an offline `MockAgent` reproducible via `python -m scripts.run_eval --agent mock`. Verified: **no such test, no `MockAgent`, no false-confidence assertion anywhere**, and `run_eval` only accepts `--agent {claude,llm}` so the cited command errors. The committed `eval_artifact.json` reports `false_confidence_count = 1`, `anomaly` 5 vs 1 expected (4 false positives), `request_document` 33 vs 2 (precision 0.06) — directly contradicting the deck's "1 anomaly, no false positives… false-confidence 0." A reviewer who runs `pytest` (42 green, none about FC), then the documented repro (error), then opens the artifact (FC=1), watches the safety narrative collapse.
- *Files:* `DECK.md:63,97,100`, `ASSUMPTIONS_AND_TIMELINE.md:176`, `ARCHITECTURE.md:45,93`; vs `eval.py` (no FC test), `agent.py:97,134` (only `LlmAgent`/`ClaudeCliAgent`), `run_eval.py:166`; `eval_artifact.json` report.
- *Fix:* Either add a real `assert false_confidence_*==0` gate per task and make it pass, or restate the target honestly with the measured **1** disclosed; delete every dead test/command/`MockAgent` reference; rewrite all numeric claims from the artifact and **showcase** the genuinely strong 0.91/0.99 the deck currently omits.

**C2 — False-confidence is one blended number, is not held at 0, and the lone deterministic guard structurally cannot catch the mode that caused it.**
`eval.py:104-108` counts `AUTO_POST and not _fully_correct`, where `_fully_correct` (`:62`) = account AND match — so the brief's two distinct tasks (categorization→VAT/tax vs reconciliation→settled document, different precision bars and blast radii) are conflated into one counter, and you cannot tell whether the 1 leaked FC mis-stated VAT or mis-settled a document. Worse, every guard check (`guard.py:44-74`) is structural/arithmetic — none can tell `4310` is wrong when `4300` is right (both valid chart entries), which is exactly the confusable-neighbor oscillation the artifact shows. A HIGH/HIGH wrong-account proposal passes the guard and auto-posts.
- *Fix:* emit `false_confidence_categorization` (auto & account-wrong) and `false_confidence_reconciliation` (auto & match-wrong) separately and gate each at 0; auto-post precision cannot rest on a structural guard — add calibrated confidence, a second independent categorization vote, or rule-coverage gating of which accounts may auto-post.

**C3 — The duplicate guard reads the PROVIDED matches, not the agent's resolved ones, so it manufactures a false fraud alarm on the correctly-fixed swap.**
`engine.py:55-58` builds `claimed_by` from `repo.provided_match`; `guard.py:65` consumes it. When the agent correctly un-swaps T074→INV-2026-005 (the brief's planted swap), the stale provided map still lists T072 as an earlier claimant → `duplicate:INV-2026-005` → forced **ANOMALY** (GT = review). A correct, exact-amount reconciliation is turned into the most severe outcome — the precise "AI confidently wrong" that kills trust, and almost certainly one of the artifact's 4 anomaly false-positives. It is also blind to agent-*created* duplicates (74/100 txns never enter the map).
- *Fix:* build `claimed_by` from the agent's **resolved** settlements (two-pass / post-decision collision map); require prior-and-resolved to agree before flagging.

**C4 — Reconciliation precision rests on fuzzy party-token overlap, not the invoice reference sitting in the data.**
`guard.py:58` `_amount_ambiguous` → `counterparty_agrees` → ≥4-char token overlap (`grounding.py:87-96`). Five transactions carry the matched doc id literally in the SEPA remittance (e.g. T072 `INV-2026-004`, T045 `INV-2026-002`) — reconciliation is string equality for them — yet neither grounding nor guard extracts it; a same-amount wrong match passes purely because a shared token appears, and an IBAN-only counterparty yields zero overlap and false-fails. Documents carry no counterparty IBAN (`models.py:90-114`), so a true cross-check is impossible. This is the "precision bar for reconciliation/VAT/audit" approximated by a heuristic.
- *Fix:* parse the structured ref (`INV-\d{4}-\d{3}`/`B-\d{2}`/"factuur <id>") in grounding; in the guard, when a ref is present, hard-fail any disagreeing match and hard-confirm an agreeing one; add counterparty IBAN to the document model.

**C5 — A committed junk correction poisons the live system and contaminates the headline learning number.**
`backend/runtime/corrections.json` is committed (no `.gitignore` excludes it) and contains `L1: BELASTINGDIENST → 4300` — the Dutch **tax authority** pinned to **Software & licenses**, learned from T008 with an empty note at 05:17, before the 08:51 eval. Every `Repository()` loads it. The artifact shows the consequence: T026 and T093 both regress **cold 1700 (correct) → warm 4300 (wrong)** — exactly L1's account — and of 9 moved rows, 5 improved but **3 regressed correct→wrong** (T026, T037, T093). That is "moves 9, breaks 3," not "one correction moves the next 10." Root causes: `learning.apply_correction` writes a vendor→account rule with zero rubriek-sanity validation (`learning.py:79-117`), the prompt says to follow corrections unconditionally (`agent.py:27-28`), and the guard *enforces* the bad rule (`guard.py:188-201`).
- *Fix:* gitignore `runtime/` and ship it empty; reject a learned account whose rubriek contradicts the transaction's nature; scope the vendor key with a remittance discriminator (loonheffing vs omzetbelasting); add a rubriek-sanity rule to guard + prompt; re-run the full 100 clean.

**C6 — Routing simultaneously over-defers and over-fires; the capacity thesis breaks.**
Auto-post recall **0.536** (45/84 correct-and-auto), `request_document` 33 predicted vs 2 (precision 0.06 → the entrepreneur gets pinged on a third of all transactions), anomaly 5 vs 1. Confidence is a 3-way LLM self-rating (`models.py:48-51`) gated by `engine.py:126-137` (both HIGH → auto) — uncalibrated, categorical, no numeric threshold, so you cannot trade over-deferral against false-confidence; both ride the same coarse self-rating. The `missing_document` guard is a pure pass-through of the LLM's anomaly that the one-directional guard can only escalate, never temper (`guard.py:68-94`).
- *Fix:* calibrate confidence (P(correct|band)/ECE); make `missing_document` a real fact (material one-off outflow AND no candidate doc of matching amount/direction) and let the guard suppress an unsupported request; report the achieved correct-auto rate, not the GT ceiling.

**C7 — No VAT dimension — categorization cannot produce the BTW-aangifte the brief names as the outcome.**
The prompt asserts categorization "drives VAT," but `Proposal` emits a single `account` string (`models.py:156-179`) with no VAT rate (21/9/0%), base, deductibility flag, or reverse-charge/KOR handling, and `Transaction` carries gross only. Non-deductible horeca and partly-deductible representation are unmodeled. A single COA number is structurally insufficient for the named precision bar.
- *Fix:* add VAT rate/base/deductibility to the output schema and a per-account VAT-treatment table; surface a draft BTW box mapping.

**C8 — The committed artifact is stale relative to the current prompt; the headline numbers don't describe HEAD.**
The full-100 *was* run today (`generated_at` 08:51 UTC = 10:51 CEST, matching mtime) — so "the re-eval was not run" is too strong — **but** `agent.py` (mtime 11:59) and `grounding.py` (11:33) were edited ~1h *after* the eval, including the "no document is normal" change meant to cut the request-document over-firing. So the 0.91/0.99/53/33 numbers reflect the *previous* prompt, not the one that ships. With no git history there's no way to reconcile which prompt produced them.
- *Fix:* re-run full-100 on the current prompt; stamp a prompt-hash + model-id into the artifact and refuse to score if they don't match the agent under test.

**C9 — The accountant console destroys human work and re-bills 100 LLM calls on every page load.**
`app.js:431` `boot()` calls `/run`, and `Console.run` replaces `_decisions` and calls `_posted.clear()` (`api.py:166`) — a browser refresh fires 100 fresh agent calls and throws away every accept/correct. This is the opposite of human-in-the-loop, and combined with P4 (no timeout, no isolation) makes the interactive surface unsafe. One-click "Accept & post" is also enabled on `anomaly`/`request_document` items (`app.js:262-264`).
- *Fix:* load reads persisted state; `/run` becomes an explicit, rare, append-only action that never clears posted; block post on flagged outcomes pending resolution.

---

## 4. MAJOR + MINOR (deduped)

**MAJOR**
- **Match accuracy 0.99 is inflated by a 75%-trivial denominator.** 75/100 GT rows have `match=[]` (correct by emitting nothing); real skill lives on the 25 doc-bearing rows, and provided matches spoon-feed 23 of them. The eval never isolates reconciliation-only accuracy or a false-match rate. (`eval.py:58-103`, `build_seeds.py:242-252`.) Report positives-only + override-slice + no-doc precision/recall.
- **Learning can only teach the trivial vendor→account shape.** `CorrectRequest` exposes only `corrected_account`/`corrected_match`; `apply_correction` hardcodes `note=""`; the conditional/threshold/product-split shapes (C2/C3/C4/C5 seeds) exist only as hand-authored seed notes and cannot be created through the product. Re-runs auto-generalize by fuzzy-token intersection — the exact method `DECISIONS.md` D6 claims to have ruled out — with no accountant-confirm step. (`api.py:45-47`, `learning.py:114,130`.)
- **Capacity headline (~2.6 h/customer/mo, "84% auto") uses the GT ceiling, not the measured 0.53 auto-rate.** Plugging the real 0.53 into the candidate's own formula yields ~119 min, not 159 — and the 53 contains the one confidently-wrong post. (`DECK.md:117-124`; `eval_artifact.json` counts.) The candidate's own `REVIEW.md:39` already flagged the conflation; it survived into the deck.
- **Learning-lift metric is N=1 with no noise-floor control.** Cold and warm are two separate temp=0 batches; eligibility is "any row that changed," not correction-siblings, so sampling noise (T037 4300→4310 on a no-correction vendor) is counted as a correction effect. (`eval.py:139-185`.) Scope to siblings, hold out the applied correction, run N≥5, report a warm-vs-warm control.
- **Combination matching is exact-pair-to-fixture; candidate tolerance is a wide 2% band.** No 3+ split, no sum tolerance, no party constraint (it even concatenates across different parties); the band injects spurious near-amount distractors. (`reconcile.py:30-31,69-95`.) Bounded subset-sum over one counterparty's open set with a small fixed tolerance.
- **No write-boundary validation (fail-open).** `corrected_account`/`corrected_match` are persisted with no check that the account exists in the chart or the doc ids exist — a typo writes a garbage correction that feeds the whole vendor class. (`learning.py:79-117`.) Validate at the boundary, reject 422.
- **Zero tests on the human-in-the-loop surface.** No `TestClient`; the 42 tests cover guard/eval/learning/reconcile/agent only — queue ranking, accept, correct-rerun, posted, and every route are untested.
- **Asset/supplies and freelancer-vs-salary rules are uncomputable or unscaled.** C3 keys on **net** ≥ €450 but the agent sees gross only (`grounding.py:354-367`); the freelancer rule lives only inside C1's note bound to one vendor name. Promote to brand-agnostic structural rules; render net from the matched document.

**MINOR**
- `temperature=0.0` applied unconditionally (`agent.py:106`) — 400s on current Opus/Fable, breaking the advertised model-swappability.
- Model-choice defense is unmeasured — no Sonnet-vs-Haiku/Flash comparison committed despite the brief's "which model for which step"; no difficulty-tiered routing.
- No prompt caching / Batch API; the prompt even renders the volatile transaction *before* the static chart, so the byte-identical chart can never form a cacheable prefix (`grounding.py:54-72`).
- Latency budget is qualitative only — `eval_artifact.json` records concurrency/retries but zero timing; no p50/p95.
- `_fingerprint_duplicate`'s "share vendor" gate tokenizes SEPA boilerplate (`sepa`/`2026`), effectively a no-op at volume (`grounding.py:99-101`).
- Settlement model is a `unpaid|paid` boolean reconstructed at runtime, not a ledger with `settled_on`/partial amounts; won't survive reversals/refunds/FX (`models.py:31-33`).
- Chart gaps for real Dutch SMEs (no leasehold-improvements, no IB/VPB liability, no suspense/Kruisposten); 4900 used as an uncertainty sink.
- Accessibility gaps (non-focusable queue rows, no `aria-live` toast, no focus trap on the trace drawer); free-text match re-pointing with no id validation.
- Card display amounts come from a static `ui/transactions.json` snapshot not written by `build_seeds`, so it can silently drift from the scored seeds (`app.js:75-82`).
- Conflicting corrections deadlock a vendor: `apply_correction` dedupes only on the exact tuple, `vendor_cost_account` returns the *older* rule, and the guard flags both — re-correcting makes it worse (`learning.py:98-104`, `guard.py:188-201`).
- Dead/duplicated machinery: four divergent vendor-match implementations; `Rule`/`RuleScope` never constructed; `L{len+1}` ids collide after deletion.

---

## 5. GENUINE STRENGTHS (keep and showcase)

- **The architecture is the right shape and well-argued.** Agent decides → code grounds → guard verifies → route, with the guard able only to **downgrade** via `forced_outcome`, never rewrite the agent's choice (`engine.py:106-114`, `models.py:214-221`), and this contract is genuinely unit-tested (16 guard cases). The single-pass-no-framework rationale (`DECISIONS.md:120-160`) is senior reasoning, not hand-waving.
- **Two independent confidences (account vs match) drive routing and the decision card** — a thoughtful, decision-shaped design that honors the brief's two-task split, rendered as distinct chips in the UI.
- **Verify-first reconciliation is real:** provided match is surfaced as a prior, candidates are independently recomputed with gap/direction/counterparty facts, the "open as of `booked_on`" model correctly keeps a fixable swap reachable, and money is exact `Decimal` end-to-end with correct direction handling and a deterministic short-pay → PARTIAL → review path.
- **Per-outcome precision *and* recall gates make the failures visible** rather than hiding them behind headline accuracy — it is this honest instrumentation that surfaces the 0.06 request precision. The cold-vs-warm `LiftHarness` with `corrections_suppressed` temp-copy is the correct way to isolate learning effect and it captures regressions, not just gains.
- **Read-only seeds vs a writable runtime store** (`repository.py:33-55`) — the correct instinct that a money system never mutates its own fixtures; `customer_id` is already on every model and filter, making the multi-tenant retrofit mechanical.
- **Strong typed boundary:** Pydantic v2, `frozen=True, extra="forbid"` everywhere; production code passes `pyright --strict` clean; 42 deterministic tests pass in ~0.5s.
- **The fixture is a genuinely strong *evaluation* artifact:** RGS-grounded chart with deliberate trap accounts (0150 vs 4500, 4300/4310/4400, 4000/4100/0600), md5-hardened messy bank lines, accrual-correct receivable modeling, planted traps asserted in `verify()`.
- **The strategic deliverables are senior in craft:** the one-page architecture diagram meets all four required elements; the five tooling defenses reason rather than name-drop; the guiding question is answered in full with a phased roadmap, named hires (incl. a domain accountant), and the batch-accountant vs interactive-entrepreneur latency split; assumptions A1–A3 disclose the ~85% real match precision rather than hiding behind "~96%." `DECISIONS.md` D12 honestly retracted earlier overclaims — the honesty pass simply stopped one eval-run too early.
- **Safe UI rendering:** all model/vendor/reasoning text goes through `textContent`/`el()` — no `innerHTML` of model output, no XSS. Thin client, logic on the server, no build step — legible for a non-AI engineer.

---

## 6. ROADMAP TO SHIP

Ordered. Each phase has an exit criterion. "Buildable now" = no decision needed; "needs Adam" = a scope/resourcing call.

### Phase 0 — Honesty pass + submission artifact (≈1 day, buildable now) — *do before any interview*
1. Delete `runtime/corrections.json` (and gitignore `runtime/`). [C5]
2. Reconcile every number in DECK/ASSUMPTIONS/ARCHITECTURE to `eval_artifact.json`: state FC=1, auto 0.53, request 33/0.06, anomaly 5/1; **showcase** 0.91/0.99; strike all references to the non-existent `MockAgent`/`test_mock_run_holds_false_confidence_at_zero`/`--agent mock`. [C1]
3. `git init` + first commit; add pytest+pyright dev group so the suite runs as committed. [P8]
4. Export `DECK.md` → <15-slide PDF, render the Mermaid diagram, record the 7-min screen-share. [P9]
- **Exit:** no claim in the repo is contradicted by the repo's own evidence; the brief's required artifact exists.

### Phase 1 — Correctness / trust (≈1–2 wks, buildable now)
5. Duplicate guard off the **resolved** match (two-pass collision map). [C3]
6. Reference-based reconciliation: parse the remittance doc id; hard-confirm/hard-fail on it; add counterparty IBAN to the doc model. [C4]
7. Split false-confidence per task and gate each at 0; re-run full-100 on the **current** prompt and stamp prompt-hash + model-id into the artifact. [C2, C8]
8. Rubriek-sanity validation on learned corrections (write-time + guard + prompt); scope the vendor key with a remittance discriminator. [C5]
9. Calibrate routing (confidence→P(correct), ECE); make `missing_document` a real fact and let the guard temper it; tighten reconciliation tolerance. [C6, MAJOR]
10. Write-boundary validation (account ∈ chart, match ⊆ docs → 422). [MAJOR]
- **Exit:** per-task FC = 0 on a fresh full-100; request_document and anomaly precision recover; no learning regression; the swap reconciles without a false anomaly.

### Phase 2 — Product backbone (≈1 month+, *needs Adam* on stack/sequencing)
11. Postgres on GCP: tenant-scoped tables, an append-only postings ledger + immutable audit log (actor/when/before→after), atomic correction writes. [P1, P3, P7]
12. Auth (OIDC/session) + per-route authz; tenant resolved from identity per request; drop the module-global console. [P2, P5]
13. Make `LlmAgent` (API client) the only prod path; per-call timeout + backoff + cost control; re-eval through it; quarantine `ClaudeCliAgent`. [P4]
14. Move the run to a job/queue with bounded concurrency + per-txn isolation + progress (SSE); load reads persisted state; `/run` append-only, never clears posted. [P11, C9]
15. Wire Logfire; record the real prompt/output/verdict at decision time and make `/trace` replay it verbatim; live console metrics = throughput/auto-rate/review-rate/correction-rate; move GT to tests-only. [P6, P10]
16. Add the VAT dimension to the output schema + a per-account treatment table + draft BTW mapping. [C7] — *needs Adam:* how far to take VAT for the take-home vs the prod plan.
17. Structured corrections (predicate + rationale) + accountant-confirmed generalization scope + a next-N held-out learning eval + amend-posted path. [MAJOR learning]
- **Exit:** a second tenant cannot see tenant one's data; a restart loses nothing; every post is attributable and replayable; the eval gates the build in CI.

### Phase 3 — Scale & polish (post-MVP, *needs Adam*)
18. DB-indexed retrieval (kill the O(T²) full-scans), pagination, top-k correction retrieval; per-tenant editable RGS-versioned charts; difficulty-tiered model routing with a committed cost/accuracy comparison; prompt caching + Batch API; accessibility; deploy surface (Dockerfile/CI/health checks/rate limits).

**Bottom line:** Phase 0 is non-negotiable before showing this to anyone — it is what stands between "senior hire" and "fabricated a safety gate." Phases 0–1 (~2–3 wks) get to a *credible, correct* prototype; Phase 2 (~1 month+) is what the word "SaaS" in the brief actually requires.
