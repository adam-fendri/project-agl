import { useAppData } from "../data/store";
import { formatDate } from "../lib/format";
import { ConfidencePill } from "./ui/Pill";
import { Money } from "./ui/Money";
import { Check } from "./ui/icons";
import type { Decision } from "../api/types";

export function QueueRow({ decision }: { decision: Decision }) {
  const { txnById, accountByNumber, openDecision, selectedId, isPosted } = useAppData();
  const id = decision.transaction_id;
  const txn = txnById[id];
  const account = accountByNumber[decision.account];
  const accountName = account ? account.name_en : "Account to add";
  const selected = selectedId === id;
  const posted = isPosted(id);

  return (
    <button
      type="button"
      className={`qrow${selected ? " is-selected" : ""}`}
      onClick={() => openDecision(id)}
    >
      <div className="qrow__top">
        <span className="qrow__party">{decision.vendor || txn?.counterparty || id}</span>
        {txn && <Money value={txn.amount} size="sm" />}
      </div>
      <div className="qrow__account">
        <span className="qrow__num">{decision.account}</span>
        <span className="qrow__name">{accountName}</span>
      </div>
      <div className="qrow__bottom">
        <div className="qrow__pills">
          <ConfidencePill label="Account" confidence={decision.account_confidence} />
          {decision.match.length > 0 && (
            <ConfidencePill label="Match" confidence={decision.match_confidence} />
          )}
        </div>
        <span className="qrow__date">{txn ? formatDate(txn.booked_on) : ""}</span>
      </div>
      {posted && (
        <span className="qrow__posted">
          <Check size={12} /> Posted
        </span>
      )}
    </button>
  );
}

export function HandledRow({
  transactionId,
  vendor,
  account,
  action,
}: {
  transactionId: string;
  vendor: string;
  account: string;
  action: string;
}) {
  const { txnById, accountByNumber, openDecision, selectedId } = useAppData();
  const txn = txnById[transactionId];
  const accountMeta = accountByNumber[account];
  const accountName = accountMeta ? accountMeta.name_en : account;
  const selected = selectedId === transactionId;
  const label = action === "request_document" ? "Document requested" : "Flagged & held";
  const tone = action === "request_document" ? "info" : "danger";

  return (
    <button
      type="button"
      className={`qrow${selected ? " is-selected" : ""}`}
      onClick={() => openDecision(transactionId)}
    >
      <div className="qrow__top">
        <span className="qrow__party">{vendor || txn?.counterparty || transactionId}</span>
        {txn && <Money value={txn.amount} size="sm" />}
      </div>
      <div className="qrow__account">
        <span className="qrow__num">{account}</span>
        <span className="qrow__name">{accountName}</span>
      </div>
      <div className="qrow__bottom">
        <span className={`pill pill--${tone} pill--soft`}>{label}</span>
        <span className="qrow__date">{txn ? formatDate(txn.booked_on) : ""}</span>
      </div>
    </button>
  );
}
