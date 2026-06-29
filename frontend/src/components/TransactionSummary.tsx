import type { Decision, Transaction } from "../api/types";
import { formatDate } from "../lib/format";
import { TXN_TYPE_LABEL } from "../lib/labels";
import {
  cleanPurpose,
  extractCounterpartyName,
  extractReference,
  looksLikeIban,
  titleCase,
} from "../lib/parse";
import { Money } from "./ui/Money";

function resolveParty(decision: Decision, txn: Transaction | undefined): string {
  if (decision.vendor && decision.vendor.trim().length > 0) {
    return decision.vendor;
  }
  if (txn) {
    if (!looksLikeIban(txn.counterparty)) {
      return titleCase(txn.counterparty);
    }
    const named = extractCounterpartyName(txn.description);
    if (named) {
      return named;
    }
  }
  return "Unidentified party";
}

export function TransactionSummary({
  decision,
  txn,
}: {
  decision: Decision;
  txn: Transaction | undefined;
}) {
  const party = resolveParty(decision, txn);
  const reference = txn ? extractReference(txn.description) : null;
  const purpose = txn ? cleanPurpose(txn.description) : null;

  return (
    <div className="txnsummary">
      <div className="txnsummary__lead">
        <div className="txnsummary__who">
          <h2 className="txnsummary__party">{party}</h2>
          <div className="txnsummary__meta">
            <span className="mono">{decision.transaction_id}</span>
            {txn && <span>{formatDate(txn.booked_on)}</span>}
            {txn && <span className="chip chip--type">{TXN_TYPE_LABEL[txn.type]}</span>}
          </div>
        </div>
        {txn && (
          <div className="txnsummary__amount">
            <Money value={txn.amount} size="lg" />
            <span className={`flow flow--${Number(txn.amount) < 0 ? "out" : "in"}`}>
              {Number(txn.amount) < 0 ? "Money out" : "Money in"}
            </span>
          </div>
        )}
      </div>

      <div className="txnsummary__details">
        {purpose && (
          <div className="kv">
            <span className="kv__k">Purpose</span>
            <span className="kv__v">{purpose}</span>
          </div>
        )}
        {reference && (
          <div className="kv">
            <span className="kv__k">{reference.label}</span>
            <span className="kv__v mono">{reference.value}</span>
          </div>
        )}
      </div>

      {txn && (
        <details className="rawline">
          <summary>Raw bank line</summary>
          <div className="rawline__body">
            <div className="kv">
              <span className="kv__k">Counterparty</span>
              <span className="kv__v mono">{txn.counterparty}</span>
            </div>
            <div className="kv">
              <span className="kv__k">Remittance</span>
              <span className="kv__v mono">{txn.description}</span>
            </div>
          </div>
        </details>
      )}
    </div>
  );
}
