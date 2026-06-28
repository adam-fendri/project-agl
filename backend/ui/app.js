"use strict";

const state = {
  tab: "queue",
  selected: null,
  accounts: [],
  accountByNumber: {},
  txns: {},
  decisions: {},
};

const RUBRIEK_LABEL = {
  "0": "Fixed assets & equity",
  "1": "Financial (balance)",
  "4": "Costs",
  "8": "Revenue",
  "9": "Financial result",
};

const NEXT_ACTION = {
  duplicate: "Flag as a duplicate payment and hold it; confirm with the entrepreneur before posting.",
  missing_counterpart: "Request the missing invoice or bill from the entrepreneur to complete the match.",
  suspicious_vendor: "Escalate: verify the vendor's identity and bank details before posting.",
  unusual_amount: "Confirm the amount with the entrepreneur; it is outside this vendor's normal range.",
};

const FLAG_ACTION = {
  duplicate: "Flag duplicate",
  missing_counterpart: "Request counterpart",
  suspicious_vendor: "Escalate vendor",
  unusual_amount: "Confirm amount",
};

const HANDLED_LABEL = {
  flag_duplicate: "Flagged & held",
  request_document: "Document requested",
};

const HANDLED_OUTCOME_CLASS = {
  flag_duplicate: "anomaly",
  request_document: "request_document",
};

const LIST_HINT = {
  queue: "Ranked by impact × uncertainty. Anomalies pinned to the top.",
  posted: "Auto-posted plus accepted entries. Spot-check before sign-off.",
  handled: "Flagged anomalies held and document requests logged. Out of the active queue.",
};

const EMPTY_LABEL = {
  queue: "Queue is clear.",
  posted: "Nothing posted yet.",
  handled: "Nothing flagged or requested yet.",
};

function blockedActionLabel(d) {
  if (d.outcome === "request_document") return "Request document";
  if (d.anomaly && FLAG_ACTION[d.anomaly.type]) return FLAG_ACTION[d.anomaly.type];
  return "Resolve before posting";
}

async function api(path, method = "GET", body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${method} ${path} -> ${res.status}: ${text}`);
  }
  return res.status === 204 ? null : res.json();
}

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

function money(value) {
  const n = Number(value);
  const sign = n < 0 ? "-" : "+";
  const abs = Math.abs(n).toLocaleString("nl-NL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${sign} €${abs}`;
}

function toast(message, isError) {
  const node = document.getElementById("toast");
  node.textContent = message;
  node.className = isError ? "toast err" : "toast";
  node.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { node.hidden = true; }, 4200);
}

function confChip(label, level) {
  const chip = el("span", "chip");
  chip.append(`${label} `);
  const b = el("b", `conf-${level}`, level);
  chip.append(b);
  return chip;
}

function accountLabel(number) {
  const acc = state.accountByNumber[number];
  return acc ? `${number} · ${acc.name_en}` : number;
}

function vatLabel(treatment) {
  const rate = { standard: "21%", reduced: "9%", exempt: "0% / exempt" }[treatment];
  return rate ? `${rate} (${treatment})` : treatment;
}

async function loadStatics() {
  const [accounts, txns] = await Promise.all([
    fetch("/accounts.json").then((r) => r.json()),
    fetch("/transactions.json").then((r) => r.json()),
  ]);
  state.accounts = accounts;
  state.txns = txns;
  state.accountByNumber = Object.fromEntries(accounts.map((a) => [a.number, a]));
}

function indexDecisions(list) {
  for (const d of list) state.decisions[d.transaction_id] = d;
}

async function refresh() {
  const [queue, posted, handled, metrics] = await Promise.all([
    api("/queue"),
    api("/posted"),
    api("/handled"),
    api("/metrics"),
  ]);
  indexDecisions(queue);
  indexDecisions(posted);
  state.queue = queue;
  state.posted = posted;
  state.handled = handled;
  renderMetrics(metrics);
  document.getElementById("queue-count").textContent = String(queue.length);
  document.getElementById("posted-count").textContent = String(posted.length);
  document.getElementById("handled-count").textContent = String(handled.length);
  renderList();
}

function renderMetrics(m) {
  const wrap = document.getElementById("metrics");
  wrap.innerHTML = "";
  const c = m.counts || {};
  const items = [
    ["auto-posted", c.auto_post ?? 0, "ok"],
    ["in review", c.review ?? 0, ""],
    ["anomalies", c.anomaly ?? 0, ""],
    ["false-confidence", m.false_confidence_count, m.false_confidence_count > 0 ? "alert" : "ok"],
    ["categorization", `${Math.round((m.categorization_accuracy || 0) * 100)}%`, ""],
    ["match", `${Math.round((m.match_accuracy || 0) * 100)}%`, ""],
  ];
  for (const [label, val, cls] of items) {
    const box = el("div", `metric ${cls}`.trim());
    box.append(el("b", null, String(val)), el("span", null, label));
    wrap.append(box);
  }
}

function listSource() {
  if (state.tab === "posted") return state.posted || [];
  if (state.tab === "handled") return state.handled || [];
  return state.queue || [];
}

function renderList() {
  const ul = document.getElementById("list");
  ul.innerHTML = "";
  document.getElementById("list-hint").textContent = LIST_HINT[state.tab];
  const source = listSource();
  if (source.length === 0) {
    ul.append(renderEmptyState());
    return;
  }
  const render = state.tab === "handled" ? renderHandledItem : renderItem;
  for (const entry of source) {
    ul.append(render(entry));
  }
}

function engineHasRun() {
  return (state.queue || []).length > 0 || (state.posted || []).length > 0 || (state.handled || []).length > 0;
}

function renderEmptyState() {
  const li = el("li", "empty");
  if (engineHasRun()) {
    li.textContent = EMPTY_LABEL[state.tab];
    return li;
  }
  li.append(el("div", null, "No decisions yet. Run the engine to categorize and reconcile the transactions."));
  const btn = el("button", "btn btn-run", "Run engine");
  btn.style.marginTop = "14px";
  btn.addEventListener("click", runEngine);
  li.append(btn);
  return li;
}

function renderItem(d) {
  const txn = state.txns[d.transaction_id] || {};
  const li = el("li", "item");
  if (d.outcome === "anomaly") li.classList.add("pinned");
  if (state.selected === d.transaction_id) li.classList.add("selected");
  li.dataset.id = d.transaction_id;

  const top = el("div", "item-top");
  top.append(el("span", "item-vendor", d.vendor || txn.counterparty || d.transaction_id));
  if (txn.amount !== undefined) top.append(el("span", "item-amt", money(txn.amount)));
  li.append(top);

  const sub = el("div", "item-sub");
  const left = el("div", "chips");
  left.append(el("span", `outcome ${d.outcome}`, d.outcome.replace("_", " ")));
  sub.append(left);
  const right = el("div", "chips");
  right.append(confChip("acct", d.account_confidence));
  if (d.match && d.match.length) right.append(confChip("match", d.match_confidence));
  sub.append(right);
  li.append(sub);

  li.append(el("div", "item-id", d.transaction_id));
  li.addEventListener("click", () => openCard(d.transaction_id));
  return li;
}

function block(title, extra) {
  const b = el("div", "block");
  const h = el("h3", null, title);
  if (extra) h.append(extra);
  b.append(h);
  return b;
}

function openCard(txnId) {
  state.selected = txnId;
  document.querySelectorAll(".item").forEach((n) => n.classList.toggle("selected", n.dataset.id === txnId));
  const d = state.decisions[txnId];
  const txn = state.txns[txnId] || {};
  const card = document.getElementById("card");
  document.getElementById("card-empty").hidden = true;
  card.hidden = false;
  card.innerHTML = "";

  const head = el("div", "txn-line");
  const who = el("div");
  who.append(el("div", "who", d.vendor || txn.counterparty || txnId));
  if (txn.description) who.append(el("div", "desc", txn.description));
  who.append(el("div", "meta", `${txnId} · ${txn.booked_on || ""} · ${(txn.type || "").replace(/_/g, " ")}`));
  head.append(who);
  if (txn.amount !== undefined) {
    const amt = el("div", "amt");
    amt.append(document.createTextNode(money(txn.amount)));
    amt.append(el("small", null, txn.counterparty || ""));
    head.append(amt);
  }
  card.append(head);

  const traceBtn = el("button", "link-trace", "View trace ↗");
  traceBtn.addEventListener("click", () => openTrace(txnId));
  const acctBlock = block("Categorization — the agent's choice", traceBtn);
  acctBlock.append(el("div", "choice", accountLabel(d.account)));
  acctBlock.append(el("div", "reason", d.account_reasoning));
  if (d.vat_treatment) acctBlock.append(el("div", "vat", `VAT treatment: ${vatLabel(d.vat_treatment)}`));
  const acctChips = el("div", "chips");
  acctChips.style.marginTop = "8px";
  acctChips.append(confChip("account confidence", d.account_confidence));
  acctBlock.append(acctChips);
  card.append(acctBlock);

  const matchBlock = block("Reconciliation — invoice / bill match");
  if (d.match && d.match.length) {
    matchBlock.append(el("div", "choice", d.match.join(", ")));
    matchBlock.append(el("div", "reason", d.match_reasoning || ""));
    const mChips = el("div", "chips");
    mChips.style.marginTop = "8px";
    mChips.append(confChip("match confidence", d.match_confidence));
    mChips.append(el("span", "chip", `amount ${d.match_status}`));
    matchBlock.append(mChips);
  } else {
    matchBlock.append(el("div", "reason muted", "No document in the system settles this transaction."));
  }
  card.append(matchBlock);

  const srcBlock = block("Sources — verified signals");
  if (d.confidence_signals && d.confidence_signals.length) {
    const ul = el("ul", "signals");
    for (const s of d.confidence_signals) ul.append(el("li", null, s));
    srcBlock.append(ul);
  } else {
    srcBlock.append(el("div", "reason muted", "No grounded signals recorded."));
  }
  if (d.sources && d.sources.length) {
    srcBlock.append(el("div", "sources-line", `Documents read: ${d.sources.join(", ")}`));
  }
  card.append(srcBlock);

  if (d.anomaly) {
    const an = el("div", "block anomaly-block");
    an.append(el("h3", null, `Anomaly — ${d.anomaly.type.replace(/_/g, " ")}`));
    an.append(el("div", "reason", d.anomaly.reason));
    an.append(el("div", "next-action", `Next: ${NEXT_ACTION[d.anomaly.type] || "Resolve before posting."}`));
    card.append(an);
  } else if (d.outcome === "request_document") {
    const rd = el("div", "block anomaly-block");
    rd.append(el("h3", null, "Missing document"));
    rd.append(el("div", "next-action", "Next: request the matching invoice or bill from the entrepreneur."));
    card.append(rd);
  }

  card.append(renderActions(txnId, d));
}

function renderActions(txnId, d) {
  const wrap = el("div");
  const postable = d.outcome === "auto_post" || d.outcome === "review";
  const isPosted = d.outcome === "auto_post" || (state.posted || []).some((p) => p.transaction_id === txnId);

  const actions = el("div", "actions");
  if (postable) {
    const acceptBtn = el("button", "btn btn-accept", isPosted ? "Posted ✓" : "Accept & post");
    acceptBtn.disabled = isPosted;
    acceptBtn.addEventListener("click", () => onAccept(txnId));
    actions.append(acceptBtn);
  } else {
    const isHandled = (state.handled || []).some((h) => h.transaction_id === txnId);
    const handleBtn = el("button", "btn btn-accept", isHandled ? "Handled ✓" : blockedActionLabel(d));
    handleBtn.disabled = isHandled;
    handleBtn.title = isHandled
      ? "Logged. This entry is out of the active queue."
      : "Record this next action and move the entry out of the active queue.";
    if (!isHandled) handleBtn.addEventListener("click", () => onHandle(txnId));
    actions.append(handleBtn);
  }

  const correctBtn = el("button", "btn btn-correct", "Correct");
  const explainBtn = el("button", "btn", "Explain");
  actions.append(correctBtn, explainBtn);
  const assignBtn = d.outcome === "review" ? el("button", "btn", "New account") : null;
  if (assignBtn) actions.append(assignBtn);
  wrap.append(actions);

  const correctPanel = renderCorrectPanel(txnId, d);
  correctPanel.hidden = true;
  wrap.append(correctPanel);
  correctBtn.addEventListener("click", () => { correctPanel.hidden = !correctPanel.hidden; });

  if (assignBtn) {
    const assignPanel = renderAssignPanel(txnId);
    assignPanel.hidden = true;
    wrap.append(assignPanel);
    assignBtn.addEventListener("click", () => { assignPanel.hidden = !assignPanel.hidden; });
  }

  const explainOut = el("div", "explain-out");
  explainOut.hidden = true;
  wrap.append(explainOut);
  explainBtn.addEventListener("click", async () => {
    explainBtn.disabled = true;
    try {
      const res = await api(`/transaction/${txnId}/explain`, "POST");
      explainOut.textContent = res.explanation;
      explainOut.hidden = false;
    } catch (e) {
      toast(String(e.message || e), true);
    } finally {
      explainBtn.disabled = false;
    }
  });
  return wrap;
}

function renderCorrectPanel(txnId, d) {
  const panel = el("div", "correct-panel");
  panel.append(el("h3", null, "Correct this entry — the agent learns it for similar transactions"));

  const acctField = el("div", "field");
  acctField.append(el("label", null, "Re-categorize to account"));
  const select = el("select");
  const groups = {};
  for (const a of state.accounts) (groups[a.rubriek] ||= []).push(a);
  for (const rubriek of Object.keys(groups).sort()) {
    const og = el("optgroup");
    og.label = RUBRIEK_LABEL[rubriek] || rubriek;
    for (const a of groups[rubriek]) {
      const opt = el("option", null, `${a.number} · ${a.name_en}`);
      opt.value = a.number;
      if (a.number === d.account) opt.selected = true;
      og.append(opt);
    }
    select.append(og);
  }
  acctField.append(select);
  panel.append(acctField);

  const matchField = el("div", "field");
  matchField.append(el("label", null, "Re-point match (document ids, comma-separated; blank to leave)"));
  const matchInput = el("input");
  matchInput.placeholder = (d.match || []).join(", ") || "e.g. INV-2026-004";
  matchField.append(matchInput);
  panel.append(matchField);

  const submit = el("button", "btn btn-correct", "Save correction");
  submit.addEventListener("click", async () => {
    const body = {};
    if (select.value && select.value !== d.account) body.corrected_account = select.value;
    const raw = matchInput.value.trim();
    if (raw) body.corrected_match = raw.split(/[\s,]+/).filter(Boolean);
    if (!body.corrected_account && !body.corrected_match) {
      toast("Change the account or enter a match to save a correction.", true);
      return;
    }
    submit.disabled = true;
    try {
      const res = await api(`/transaction/${txnId}/correct`, "POST", body);
      toast(`Correction saved. ${res.reran.length} similar transaction(s) re-run.`);
      await refresh();
      openCard(txnId);
    } catch (e) {
      toast(String(e.message || e), true);
    } finally {
      submit.disabled = false;
    }
  });
  panel.append(submit);
  return panel;
}

function renderAssignPanel(txnId) {
  const panel = el("div", "correct-panel");
  panel.append(el("h3", null, "Create account & assign — grows the chart and teaches the cohort"));

  const numField = el("div", "field");
  numField.append(el("label", null, "New account number"));
  const numInput = el("input");
  numInput.placeholder = "e.g. 4310";
  numField.append(numInput);
  panel.append(numField);

  const nameField = el("div", "field");
  nameField.append(el("label", null, "Account name"));
  const nameInput = el("input");
  nameInput.placeholder = "e.g. Design tools";
  nameField.append(nameInput);
  panel.append(nameField);

  const rubField = el("div", "field");
  rubField.append(el("label", null, "Rubriek"));
  const rubSelect = el("select");
  for (const code of Object.keys(RUBRIEK_LABEL)) {
    const opt = el("option", null, `${code} · ${RUBRIEK_LABEL[code]}`);
    opt.value = code;
    rubSelect.append(opt);
  }
  rubField.append(rubSelect);
  panel.append(rubField);

  const submit = el("button", "btn btn-correct", "Create & assign");
  submit.addEventListener("click", () => onAssignAccount(txnId, numInput, nameInput, rubSelect, submit));
  panel.append(submit);
  return panel;
}

async function onAssignAccount(txnId, numInput, nameInput, rubSelect, submit) {
  const number = numInput.value.trim();
  const name = nameInput.value.trim();
  if (!number || !name) {
    toast("Enter an account number and a name.", true);
    return;
  }
  const rubriek = rubSelect.value;
  submit.disabled = true;
  try {
    const updated = await api(`/transaction/${txnId}/assign-account`, "POST", {
      number,
      name_en: name,
      name_nl: name,
      rubriek,
    });
    if (!state.accountByNumber[number]) {
      const account = { number, name_en: name, name_nl: name, rubriek };
      state.accountByNumber[number] = account;
      state.accounts.push(account);
    }
    toast(`Account ${number} created and assigned. ${updated.length} decision(s) re-run.`);
    await refresh();
    closeCard();
  } catch (e) {
    toast(String(e.message || e), true);
  } finally {
    submit.disabled = false;
  }
}

async function onAccept(txnId) {
  try {
    await api(`/transaction/${txnId}/accept`, "POST");
    toast(`${txnId} posted to the ledger.`);
    await refresh();
    if (state.tab === "queue" && !(state.queue || []).some((d) => d.transaction_id === txnId)) {
      closeCard();
    } else {
      openCard(txnId);
    }
  } catch (e) {
    toast(String(e.message || e), true);
  }
}

async function onHandle(txnId) {
  try {
    const rec = await api(`/transaction/${txnId}/handle`, "POST");
    toast(`${txnId}: ${HANDLED_LABEL[rec.action] || rec.action}.`);
    await refresh();
    if (state.tab === "queue" && !(state.queue || []).some((d) => d.transaction_id === txnId)) {
      closeCard();
    } else {
      openCard(txnId);
    }
  } catch (e) {
    toast(String(e.message || e), true);
  }
}

function renderHandledItem(h) {
  const txn = state.txns[h.transaction_id] || {};
  const li = el("li", "item");
  li.dataset.id = h.transaction_id;

  const top = el("div", "item-top");
  top.append(el("span", "item-vendor", h.vendor || txn.counterparty || h.transaction_id));
  if (txn.amount !== undefined) top.append(el("span", "item-amt", money(txn.amount)));
  li.append(top);

  const sub = el("div", "item-sub");
  const left = el("div", "chips");
  const actionClass = `outcome ${HANDLED_OUTCOME_CLASS[h.action] || ""}`.trim();
  left.append(el("span", actionClass, HANDLED_LABEL[h.action] || h.action.replace(/_/g, " ")));
  sub.append(left);
  const right = el("div", "chips");
  right.append(el("span", "chip", accountLabel(h.account)));
  sub.append(right);
  li.append(sub);

  li.append(el("div", "item-id", h.transaction_id));
  return li;
}

async function openTrace(txnId) {
  try {
    const trace = await api(`/trace/${txnId}`);
    const body = document.getElementById("trace-body");
    body.innerHTML = "";
    body.append(traceSection("Context (grounded evidence)", JSON.stringify(trace.context, null, 2)));
    body.append(traceSection("Prompt sent to the model", trace.prompt));
    body.append(traceSection("Model output (raw proposal)", JSON.stringify(trace.llm_output, null, 2)));
    body.append(traceSection("Guard verification", JSON.stringify(trace.verification, null, 2)));
    document.getElementById("trace-pane").hidden = false;
    document.querySelector(".layout").classList.add("with-trace");
  } catch (e) {
    toast(String(e.message || e), true);
  }
}

function traceSection(title, text) {
  const sec = el("div", "trace-section");
  sec.append(el("h4", null, title));
  sec.append(el("pre", null, text));
  return sec;
}

function closeTrace() {
  document.getElementById("trace-pane").hidden = true;
  document.querySelector(".layout").classList.remove("with-trace");
}

function closeCard() {
  state.selected = null;
  document.getElementById("card").hidden = true;
  document.getElementById("card-empty").hidden = false;
  document.querySelectorAll(".item").forEach((n) => n.classList.remove("selected"));
}

function switchTab(tab) {
  state.tab = tab;
  document.getElementById("tab-queue").classList.toggle("active", tab === "queue");
  document.getElementById("tab-posted").classList.toggle("active", tab === "posted");
  document.getElementById("tab-handled").classList.toggle("active", tab === "handled");
  renderList();
}

async function runEngine() {
  if (!confirm("Run the engine over all transactions? This makes ~100 LLM calls and can take a while. Posted entries are kept.")) {
    return;
  }
  const btn = document.getElementById("run-btn");
  btn.disabled = true;
  btn.textContent = "Running…";
  try {
    await api("/run", "POST");
    await refresh();
    closeCard();
    toast("Engine run complete.");
  } catch (e) {
    toast(String(e.message || e), true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Run engine";
  }
}

async function boot() {
  document.getElementById("tab-queue").addEventListener("click", () => switchTab("queue"));
  document.getElementById("tab-posted").addEventListener("click", () => switchTab("posted"));
  document.getElementById("tab-handled").addEventListener("click", () => switchTab("handled"));
  document.getElementById("run-btn").addEventListener("click", runEngine);
  document.getElementById("trace-close").addEventListener("click", closeTrace);
  try {
    await loadStatics();
    await refresh();
  } catch (e) {
    toast(String(e.message || e), true);
  }
}

boot();
