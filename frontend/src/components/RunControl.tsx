import { useState } from "react";
import { useAppData } from "../data/store";
import { useElapsedSeconds } from "../lib/hooks";
import { Modal } from "./ui/Modal";
import { Spinner } from "./ui/Spinner";
import { Play, Sparkles } from "./ui/icons";

export function RunControl() {
  const { running, runEngine, engineHasRun, txnById } = useAppData();
  const [confirming, setConfirming] = useState(false);
  const total = Object.keys(txnById).length;

  async function confirmRun() {
    setConfirming(false);
    await runEngine();
  }

  return (
    <>
      <button
        type="button"
        className="btn btn--primary"
        onClick={() => setConfirming(true)}
        disabled={running}
      >
        {running ? <Spinner size={15} /> : <Play size={15} />}
        {running ? "Running…" : engineHasRun ? "Re-run engine" : "Run engine"}
      </button>

      {confirming && (
        <Modal
          title="Run the engine"
          width={460}
          onClose={() => setConfirming(false)}
          footer={
            <>
              <button type="button" className="btn btn--ghost" onClick={() => setConfirming(false)}>
                Cancel
              </button>
              <button type="button" className="btn btn--primary" onClick={confirmRun}>
                <Sparkles size={15} />
                Run engine
              </button>
            </>
          }
        >
          <p className="modal__lead">
            This categorises and reconciles all {total || 100} transactions for{" "}
            <strong>Studio Vondel B.V.</strong>
          </p>
          <p className="modal__note">
            It makes around 100 model calls and can take a few minutes. Anything already posted is kept.
          </p>
        </Modal>
      )}
    </>
  );
}

export function RunProgress() {
  const { running } = useAppData();
  const seconds = useElapsedSeconds(running);
  if (!running) {
    return null;
  }
  return (
    <div className="runprogress" role="status" aria-live="polite">
      <div className="runprogress__bar">
        <span className="runprogress__fill" />
      </div>
      <div className="runprogress__text">
        <Spinner size={15} />
        <span>
          Categorising and reconciling transactions… grounding facts and running the guard ({seconds}s)
        </span>
      </div>
    </div>
  );
}
