import { useState } from "react";
import { useAppData } from "../data/store";
import type { Account } from "../api/types";
import { RUBRIEK_LABEL, RUBRIEK_ORDER, vatLabel } from "../lib/labels";
import { Search } from "./ui/icons";
import { Spinner } from "./ui/Spinner";

function matches(account: Account, query: string): boolean {
  if (query.trim().length === 0) {
    return true;
  }
  const haystack = `${account.number} ${account.name_en} ${account.name_nl}`.toLowerCase();
  return query
    .toLowerCase()
    .split(/\s+/)
    .every((term) => haystack.includes(term));
}

export function AccountPicker({
  current,
  busy,
  onSubmit,
  onCancel,
}: {
  current: string;
  busy: boolean;
  onSubmit: (number: string, note: string) => void;
  onCancel: () => void;
}) {
  const { accounts } = useAppData();
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState(current);
  const [note, setNote] = useState("");

  const groups = RUBRIEK_ORDER.map((rubriek) => ({
    rubriek,
    items: accounts.filter((account) => account.rubriek === rubriek && matches(account, query)),
  })).filter((group) => group.items.length > 0);

  return (
    <div className="panel">
      <div className="panel__title">Re-categorise to a different account</div>
      <div className="searchbox">
        <Search size={15} className="searchbox__icon" />
        <input
          className="searchbox__input"
          placeholder="Search by number or name…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          autoFocus
        />
      </div>

      <div className="optionlist">
        {groups.length === 0 && <div className="optionlist__empty">No matching accounts.</div>}
        {groups.map((group) => (
          <div key={group.rubriek} className="optiongroup">
            <div className="optiongroup__label">{RUBRIEK_LABEL[group.rubriek]}</div>
            {group.items.map((account) => (
              <button
                key={account.number}
                type="button"
                className={`option${picked === account.number ? " is-picked" : ""}`}
                onClick={() => setPicked(account.number)}
              >
                <span className="option__main">
                  <span className="option__num mono">{account.number}</span>
                  <span className="option__name">
                    {account.name_en}
                    {account.name_nl && account.name_nl !== account.name_en && (
                      <span className="option__nl"> · {account.name_nl}</span>
                    )}
                  </span>
                </span>
                <span className="option__vat">{vatLabel(account.vat_treatment)}</span>
              </button>
            ))}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 14 }}>
        <label style={{ display: "block", fontSize: 12.5, color: "#6b7280", marginBottom: 6 }}>
          Why? (optional) — saved with the rule and shown to the agent on this vendor's future lines
        </label>
        <input
          type="text"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="e.g. recurring software subscription, always Software"
          style={{
            width: "100%",
            padding: "8px 11px",
            border: "1px solid #d7d2c4",
            borderRadius: 6,
            fontSize: 14,
            boxSizing: "border-box",
          }}
        />
      </div>

      <div className="panel__foot">
        <button type="button" className="btn btn--ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => onSubmit(picked, note)}
          disabled={busy || picked === current}
        >
          {busy && <Spinner size={14} />}
          Save &amp; re-run
        </button>
      </div>
    </div>
  );
}
