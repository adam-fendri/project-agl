import { useState } from "react";
import { useAppData } from "../data/store";
import type { Decision, DocumentView } from "../api/types";
import { formatDate, formatEuro } from "../lib/format";
import { ConfidencePill, Pill } from "./ui/Pill";
import { DocumentDetail } from "./DocumentDetail";
import { Eye, FileText, Receipt } from "./ui/icons";

const MATCH_STATUS_LABEL: Record<Decision["match_status"], string> = {
  full: "Full settlement",
  partial: "Partial settlement",
  none: "No settlement",
};

function DocumentCard({
  document,
  onOpen,
}: {
  document: DocumentView;
  onOpen: () => void;
}) {
  const isInvoice = document.kind === "invoice";
  return (
    <button type="button" className="doccard doccard--clickable" onClick={onOpen}>
      <span className="doccard__icon">
        {isInvoice ? <FileText size={18} /> : <Receipt size={18} />}
      </span>
      <div className="doccard__body">
        <div className="doccard__top">
          <span className={`chip chip--${isInvoice ? "invoice" : "bill"}`}>
            {isInvoice ? "Invoice" : "Bill"}
          </span>
          <span className="doccard__id mono">{document.id}</span>
          <Pill tone={document.status === "paid" ? "success" : "warning"} soft>
            {document.status === "paid" ? "Settled" : "Open"}
          </Pill>
        </div>
        <div className="doccard__party">{document.party}</div>
        <div className="doccard__meta">
          <span className="doccard__amount">{formatEuro(document.gross)}</span>
          <span>{formatDate(document.date)}</span>
        </div>
      </div>
      <span className="doccard__read">
        <Eye size={15} /> Read
      </span>
    </button>
  );
}

export function Reconciliation({ decision }: { decision: Decision }) {
  const { documentById } = useAppData();
  const [detail, setDetail] = useState<DocumentView | null>(null);
  const hasMatch = decision.match.length > 0;

  return (
    <section className="cardsection">
      <div className="cardsection__head">
        <h3>Reconciliation</h3>
        {hasMatch && <ConfidencePill label="Match" confidence={decision.match_confidence} />}
      </div>

      {hasMatch ? (
        <>
          <div className="docs">
            {decision.match.map((id) => {
              const document = documentById[id];
              return document ? (
                <DocumentCard key={id} document={document} onOpen={() => setDetail(document)} />
              ) : (
                <div key={id} className="doccard doccard--missing">
                  <span className="doccard__id mono">{id}</span>
                  <span className="doccard__note">Document not found in the ledger</span>
                </div>
              );
            })}
          </div>
          {decision.match_reasoning && <p className="reasoning">{decision.match_reasoning}</p>}
          <div className="metarow">
            <Pill tone={decision.match_status === "full" ? "success" : "warning"} soft>
              {MATCH_STATUS_LABEL[decision.match_status]}
            </Pill>
          </div>
        </>
      ) : (
        <div className="nomatch">
          <p className="nomatch__title">No open document settles this.</p>
          <p className="nomatch__sub">
            {decision.match_reasoning ||
              "This payment does not correspond to any invoice or bill in the ledger."}
          </p>
        </div>
      )}

      {detail && <DocumentDetail document={detail} onClose={() => setDetail(null)} />}
    </section>
  );
}
