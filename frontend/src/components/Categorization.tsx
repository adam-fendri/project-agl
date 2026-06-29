import { useAppData } from "../data/store";
import type { Decision } from "../api/types";
import { RUBRIEK_LABEL, vatLabel } from "../lib/labels";
import { ConfidencePill } from "./ui/Pill";

export function Categorization({ decision }: { decision: Decision }) {
  const { accountByNumber } = useAppData();
  const account = accountByNumber[decision.account];
  const nameLine = account
    ? account.name_nl && account.name_nl !== account.name_en
      ? `${account.name_en} (${account.name_nl})`
      : account.name_en
    : "Not yet in the chart of accounts";

  return (
    <section className="cardsection">
      <div className="cardsection__head">
        <h3>Categorisation</h3>
        <ConfidencePill label="Account" confidence={decision.account_confidence} />
      </div>

      <div className="account">
        <span className="account__number">{decision.account}</span>
        <div className="account__body">
          <span className="account__name">{nameLine}</span>
          {account && <span className="account__rubriek">{RUBRIEK_LABEL[account.rubriek]}</span>}
        </div>
      </div>

      <p className="reasoning">{decision.account_reasoning}</p>

      <div className="metarow">
        <div className="kv">
          <span className="kv__k">VAT treatment</span>
          <span className="kv__v">{vatLabel(decision.vat_treatment)}</span>
        </div>
      </div>

      {decision.account_unlisted && (
        <div className="notice notice--warning">
          No existing account fits this spend. Use <strong>Add account</strong> below to create one and
          teach it to similar transactions.
        </div>
      )}
    </section>
  );
}
