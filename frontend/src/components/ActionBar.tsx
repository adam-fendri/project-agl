import { useState } from "react";
import { useAppData } from "../data/store";
import type { Decision } from "../api/types";
import { ANOMALY_ACTION } from "../lib/labels";
import { AccountPicker } from "./AccountPicker";
import { MatchPicker } from "./MatchPicker";
import { AddAccountForm } from "./AddAccountForm";
import { Spinner } from "./ui/Spinner";
import { Check } from "./ui/icons";

type Panel = "none" | "account" | "match" | "add";

function flagLabel(decision: Decision): string {
  if (decision.anomaly) {
    return ANOMALY_ACTION[decision.anomaly.type];
  }
  if (decision.outcome === "anomaly") {
    return "Confirm duplicate";
  }
  return "Request the missing document";
}

function flagExplain(decision: Decision): string {
  if (decision.outcome === "request_document") {
    return "Logs a document request to the entrepreneur and moves this entry to Handled.";
  }
  return "Holds this out of the ledger as a likely duplicate and moves it to Handled.";
}

export function ActionBar({ decision }: { decision: Decision }) {
  const { accept, handle, correct, assignAccount, isPosted, isHandled } = useAppData();
  const id = decision.transaction_id;
  const [panel, setPanel] = useState<Panel>("none");
  const [busy, setBusy] = useState(false);

  const posted = isPosted(id);
  const handledFlag = isHandled(id);
  const postable = decision.outcome === "auto_post" || decision.outcome === "review";
  const flag = decision.outcome === "anomaly" || decision.outcome === "request_document";

  async function run(action: () => Promise<unknown>, closePanel = true) {
    setBusy(true);
    try {
      await action();
      if (closePanel) {
        setPanel("none");
      }
    } finally {
      setBusy(false);
    }
  }

  function toggle(target: Panel) {
    setPanel((current) => (current === target ? "none" : target));
  }

  return (
    <section className="actions">
      <div className="actions__row">
        {postable && (
          <button
            type="button"
            className="btn btn--primary btn--lg"
            disabled={posted || busy}
            onClick={() => run(() => accept(id), false)}
          >
            {posted ? (
              <>
                <Check size={16} /> Posted to ledger
              </>
            ) : (
              <>
                {busy && <Spinner size={15} />}
                Accept &amp; post
              </>
            )}
          </button>
        )}

        {flag && (
          <button
            type="button"
            className={`btn btn--lg ${decision.outcome === "anomaly" ? "btn--danger" : "btn--info"}`}
            disabled={handledFlag || busy}
            onClick={() => run(() => handle(id), false)}
          >
            {handledFlag ? (
              <>
                <Check size={16} /> Handled
              </>
            ) : (
              <>
                {busy && <Spinner size={15} />}
                {flagLabel(decision)}
              </>
            )}
          </button>
        )}

        <button
          type="button"
          className={`btn btn--ghost${panel === "account" ? " is-open" : ""}`}
          disabled={busy}
          onClick={() => toggle("account")}
        >
          Correct account
        </button>
        <button
          type="button"
          className={`btn btn--ghost${panel === "match" ? " is-open" : ""}`}
          disabled={busy}
          onClick={() => toggle("match")}
        >
          Re-point match
        </button>
        {decision.account_unlisted && (
          <button
            type="button"
            className={`btn btn--ghost${panel === "add" ? " is-open" : ""}`}
            disabled={busy}
            onClick={() => toggle("add")}
          >
            Add account
          </button>
        )}
      </div>

      {flag && !handledFlag && <p className="actions__explain">{flagExplain(decision)}</p>}

      {panel === "account" && (
        <AccountPicker
          current={decision.account}
          busy={busy}
          onCancel={() => setPanel("none")}
          onSubmit={(number) => run(() => correct(id, { corrected_account: number }))}
        />
      )}
      {panel === "match" && (
        <MatchPicker
          current={decision.match}
          busy={busy}
          onCancel={() => setPanel("none")}
          onSubmit={(ids) => run(() => correct(id, { corrected_match: ids }))}
        />
      )}
      {panel === "add" && (
        <AddAccountForm
          suggestedNumber={decision.account}
          busy={busy}
          onCancel={() => setPanel("none")}
          onSubmit={(body) => run(() => assignAccount(id, body))}
        />
      )}
    </section>
  );
}
