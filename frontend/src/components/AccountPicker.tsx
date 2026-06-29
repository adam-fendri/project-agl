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
  onSubmit: (number: string) => void;
  onCancel: () => void;
}) {
  const { accounts } = useAppData();
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState(current);

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

      <div className="panel__foot">
        <button type="button" className="btn btn--ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => onSubmit(picked)}
          disabled={busy || picked === current}
        >
          {busy && <Spinner size={14} />}
          Save &amp; re-run
        </button>
      </div>
    </div>
  );
}
