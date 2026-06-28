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
  const [queue, posted, metrics] = await Promise.all([
    api("/queue"),
    api("/posted"),
    api("/metrics"),
  ]);
  indexDecisions(queue);
  indexDecisions(posted);
  state.queue = queue;
  state.posted = posted;
  renderMetrics(metrics);
  document.getElementById("queue-count").textContent = String(queue.length);
  document.getElementById("posted-count").textContent = String(posted.length);
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
  return state.tab === "queue" ? state.queue || [] : state.posted || [];
}

function renderList() {
  const ul = document.getElementById("list");
  ul.innerHTML = "";
  const hint = document.getElementById("list-hint");
  hint.textContent = state.tab === "queue"
    ? "Ranked by impact × uncertainty. Anomalies pinned to the top."
    : "Auto-posted plus accepted entries. Spot-check before sign-off.";
  const source = listSource();
  if (source.length === 0) {
    ul.append(el("li", "empty", state.tab === "queue" ? "Queue is clear." : "Nothing posted yet."));
    return;
  }
  for (const d of source) {
    ul.append(renderItem(d));
  }
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
  const isPosted = d.outcome === "auto_post" || (state.posted || []).some((p) => p.transaction_id === txnId);

  const actions = el("div", "actions");
  const acceptBtn = el("button", "btn btn-accept", isPosted ? "Posted ✓" : "Accept & post");
  acceptBtn.disabled = isPosted;
  acceptBtn.addEventListener("click", () => onAccept(txnId));

  const correctBtn = el("button", "btn btn-correct", "Correct");
  const explainBtn = el("button", "btn", "Explain");
  actions.append(acceptBtn, correctBtn, explainBtn);
  wrap.append(actions);

  const correctPanel = renderCorrectPanel(txnId, d);
  correctPanel.hidden = true;
  wrap.append(correctPanel);
  correctBtn.addEventListener("click", () => { correctPanel.hidden = !correctPanel.hidden; });

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
  renderList();
}

async function runEngine() {
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
  document.getElementById("run-btn").addEventListener("click", runEngine);
  document.getElementById("trace-close").addEventListener("click", closeTrace);
  try {
    await loadStatics();
    await api("/run", "POST");
    await refresh();
  } catch (e) {
    toast(String(e.message || e), true);
  }
}

boot();
