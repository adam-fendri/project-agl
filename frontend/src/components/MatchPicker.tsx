import { useState } from "react";
import { useAppData } from "../data/store";
import type { DocumentView } from "../api/types";
import { formatDate, formatEuro } from "../lib/format";
import { DocumentDetail } from "./DocumentDetail";
import { Eye, FileText, Receipt } from "./ui/icons";
import { Spinner } from "./ui/Spinner";

export function MatchPicker({
  current,
  busy,
  onSubmit,
  onCancel,
}: {
  current: string[];
  busy: boolean;
  onSubmit: (ids: string[]) => void;
  onCancel: () => void;
}) {
  const { openDocuments } = useAppData();
  const openIds = new Set(openDocuments.map((document) => document.id));
  const [selected, setSelected] = useState<string[]>(current.filter((id) => openIds.has(id)));
  const [none, setNone] = useState(false);
  const [detail, setDetail] = useState<DocumentView | null>(null);

  function toggle(id: string) {
    setNone(false);
    setSelected((value) =>
      value.includes(id) ? value.filter((entry) => entry !== id) : [...value, id],
    );
  }

  function chooseNone() {
    setNone(true);
    setSelected([]);
  }

  const canSubmit = !busy && (none || selected.length > 0);

  return (
    <div className="panel">
      <div className="panel__title">Re-point the match to the open documents</div>
      <p className="panel__hint">
        Read a document in full before you select it. One payment can clear more than one document.
      </p>

      <div className="optionlist">
        {openDocuments.length === 0 && (
          <div className="optionlist__empty">No open documents to match.</div>
        )}
        {openDocuments.map((document) => {
          const isInvoice = document.kind === "invoice";
          const checked = selected.includes(document.id);
          return (
            <div key={document.id} className={`pickdoc${checked ? " is-checked" : ""}`}>
              <input
                type="checkbox"
                checked={checked}
                onChange={() => toggle(document.id)}
                aria-label={`Select ${document.id}`}
              />
              <button type="button" className="pickdoc__main" onClick={() => toggle(document.id)}>
                <span className="pickdoc__icon">
                  {isInvoice ? <FileText size={16} /> : <Receipt size={16} />}
                </span>
                <span className="pickdoc__body">
                  <span className="pickdoc__top">
                    <span className={`chip chip--${isInvoice ? "invoice" : "bill"}`}>
                      {isInvoice ? "Invoice" : "Bill"}
                    </span>
                    <span className="mono">{document.id}</span>
                  </span>
                  <span className="pickdoc__party">{document.party}</span>
                </span>
                <span className="pickdoc__meta">
                  <span className="pickdoc__amount">{formatEuro(document.gross)}</span>
                  <span>{formatDate(document.date)}</span>
                </span>
              </button>
              <button
                type="button"
                className="pickdoc__read"
                onClick={() => setDetail(document)}
                aria-label={`Read ${document.id}`}
              >
                <Eye size={15} /> Read
              </button>
            </div>
          );
        })}

        <button
          type="button"
          className={`pickdoc pickdoc--none${none ? " is-checked" : ""}`}
          onClick={chooseNone}
        >
          <span className="pickdoc__radio" aria-hidden="true" />
          <span className="pickdoc__body">
            <span className="pickdoc__party">No document settles this</span>
            <span className="pickdoc__sub">Clear the match entirely</span>
          </span>
        </button>
      </div>

      <div className="panel__foot">
        <button type="button" className="btn btn--ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => onSubmit(none ? [] : selected)}
          disabled={!canSubmit}
        >
          {busy && <Spinner size={14} />}
          Save &amp; re-run
        </button>
      </div>

      {detail && (
        <DocumentDetail
          document={detail}
          selected={selected.includes(detail.id)}
          onToggleSelect={() => {
            toggle(detail.id);
            setDetail(null);
          }}
          onClose={() => setDetail(null)}
        />
      )}
    </div>
  );
}
