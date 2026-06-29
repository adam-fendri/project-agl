import { useState } from "react";
import type { AssignAccountRequest, Rubriek } from "../api/types";
import { RUBRIEK_LABEL, RUBRIEK_ORDER } from "../lib/labels";
import { Spinner } from "./ui/Spinner";

export function AddAccountForm({
  suggestedNumber,
  busy,
  onSubmit,
  onCancel,
}: {
  suggestedNumber: string;
  busy: boolean;
  onSubmit: (body: AssignAccountRequest) => void;
  onCancel: () => void;
}) {
  const [number, setNumber] = useState(suggestedNumber);
  const [nameEn, setNameEn] = useState("");
  const [nameNl, setNameNl] = useState("");
  const [rubriek, setRubriek] = useState<Rubriek>("4");

  const valid = number.trim().length > 0 && nameEn.trim().length > 0;

  return (
    <div className="panel">
      <div className="panel__title">Add a new account and assign it</div>
      <p className="panel__hint">
        This grows the chart of accounts and teaches the assignment to similar transactions.
      </p>

      <div className="formgrid">
        <label className="field">
          <span className="field__label">Account number</span>
          <input
            className="input"
            value={number}
            onChange={(event) => setNumber(event.target.value)}
            placeholder="e.g. 4310"
          />
        </label>
        <label className="field">
          <span className="field__label">Rubriek</span>
          <select
            className="input"
            value={rubriek}
            onChange={(event) => setRubriek(event.target.value as Rubriek)}
          >
            {RUBRIEK_ORDER.map((code) => (
              <option key={code} value={code}>
                {code} — {RUBRIEK_LABEL[code]}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field__label">Name (English)</span>
          <input
            className="input"
            value={nameEn}
            onChange={(event) => setNameEn(event.target.value)}
            placeholder="e.g. Design tools"
          />
        </label>
        <label className="field">
          <span className="field__label">Name (Dutch)</span>
          <input
            className="input"
            value={nameNl}
            onChange={(event) => setNameNl(event.target.value)}
            placeholder="optional — defaults to English"
          />
        </label>
      </div>

      <div className="panel__foot">
        <button type="button" className="btn btn--ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button
          type="button"
          className="btn btn--primary"
          disabled={!valid || busy}
          onClick={() =>
            onSubmit({
              number: number.trim(),
              name_en: nameEn.trim(),
              name_nl: (nameNl.trim() || nameEn.trim()),
              rubriek,
            })
          }
        >
          {busy && <Spinner size={14} />}
          Create &amp; assign
        </button>
      </div>
    </div>
  );
}
