import { useAppData } from "../data/store";
import type { DocumentView } from "../api/types";
import { formatDate, formatEuro } from "../lib/format";
import { Modal } from "./ui/Modal";
import { Pill } from "./ui/Pill";
import { FileText, Receipt } from "./ui/icons";

export function DocumentDetail({
  document,
  selected,
  onToggleSelect,
  onClose,
}: {
  document: DocumentView;
  selected?: boolean;
  onToggleSelect?: () => void;
  onClose: () => void;
}) {
  const { accountByNumber } = useAppData();
  const isInvoice = document.kind === "invoice";
  const account = document.account ? accountByNumber[document.account] : undefined;
  const accountLabel = document.account
    ? account
      ? account.name_nl && account.name_nl !== account.name_en
        ? `${document.account} — ${account.name_en} (${account.name_nl})`
        : `${document.account} — ${account.name_en}`
      : document.account
    : null;

  const footer = onToggleSelect ? (
    <>
      <button type="button" className="btn btn--ghost" onClick={onClose}>
        Close
      </button>
      <button
        type="button"
        className={selected ? "btn btn--ghost" : "btn btn--primary"}
        onClick={onToggleSelect}
      >
        {selected ? "Remove from match" : "Select as the match"}
      </button>
    </>
  ) : (
    <button type="button" className="btn btn--ghost" onClick={onClose}>
      Close
    </button>
  );

  return (
    <Modal title="Document detail" width={540} onClose={onClose} footer={footer}>
      <div className="docdetail">
        <div className="docdetail__head">
          <span className="docdetail__icon">
            {isInvoice ? <FileText size={20} /> : <Receipt size={20} />}
          </span>
          <div className="docdetail__title">
            <div className="docdetail__top">
              <span className={`chip chip--${isInvoice ? "invoice" : "bill"}`}>
                {isInvoice ? "Invoice" : "Bill"}
              </span>
              <span className="mono docdetail__id">{document.id}</span>
              <Pill tone={document.status === "paid" ? "success" : "warning"} soft>
                {document.status === "paid" ? "Settled" : "Open"}
              </Pill>
            </div>
            <div className="docdetail__party">{document.party}</div>
          </div>
        </div>

        <div className="docdetail__rows">
          <div className="kv">
            <span className="kv__k">{isInvoice ? "Client" : "Supplier"}</span>
            <span className="kv__v">{document.party}</span>
          </div>
          <div className="kv">
            <span className="kv__k">Date</span>
            <span className="kv__v">{formatDate(document.date)}</span>
          </div>
          <div className="kv">
            <span className="kv__k">Status</span>
            <span className="kv__v">
              {document.status === "paid" ? "Paid / settled" : "Unpaid / open"}
            </span>
          </div>
          {accountLabel && (
            <div className="kv">
              <span className="kv__k">Default account</span>
              <span className="kv__v">{accountLabel}</span>
            </div>
          )}
        </div>

        <div className="breakdown">
          <div className="breakdown__row">
            <span>Net</span>
            <span className="breakdown__amt">{formatEuro(document.net)}</span>
          </div>
          <div className="breakdown__row">
            <span>VAT</span>
            <span className="breakdown__amt">{formatEuro(document.vat)}</span>
          </div>
          <div className="breakdown__row breakdown__row--total">
            <span>Gross</span>
            <span className="breakdown__amt">{formatEuro(document.gross)}</span>
          </div>
        </div>
      </div>
    </Modal>
  );
}
