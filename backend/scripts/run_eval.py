from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

from agl.agent import ClaudeCliAgent, LlmAgent
from agl.eval import EvalReport, LiftHarness, lift_report
from agl.models import AgentProtocol, Decision, GroundTruth
from agl.repository import Repository

_DEFAULT_CUSTOMER = "studio-vondel"
_DEFAULT_OUT = Path(__file__).resolve().parent.parent / "eval_artifact.json"

REPRESENTATIVE = [
    "T001", "T003", "T005", "T006", "T007", "T008", "T009", "T010", "T011", "T012",
    "T013", "T016", "T017", "T019", "T020", "T021", "T026", "T029", "T033", "T036",
    "T038", "T039", "T043", "T045", "T046", "T047", "T049", "T050", "T062", "T068",
    "T072", "T074", "T075", "T076", "T079", "T086", "T096",
]


def _build_agent(name: str, model: str | None) -> AgentProtocol:
    if name == "llm":
        return LlmAgent(model)
    return ClaudeCliAgent(model)


def _subset_ids(spec: str, limit: int | None, repo: Repository, customer: str) -> set[str] | None:
    ordered = [t.id for t in sorted(repo.transactions(customer), key=lambda t: (t.booked_on, t.id))]
    if spec == "all":
        chosen = ordered
    elif spec == "representative":
        chosen = [tid for tid in REPRESENTATIVE if tid in set(ordered)]
    else:
        wanted = {tid.strip() for tid in spec.split(",") if tid.strip()}
        chosen = [tid for tid in ordered if tid in wanted]
    if limit is not None:
        chosen = chosen[:limit]
    return None if spec == "all" and limit is None else set(chosen)


def probe_model_id(model_arg: str) -> str | None:
    """Resolve the concrete model id the Claude CLI uses for ``model_arg`` via one probe call."""
    try:
        completed = subprocess.run(
            ["claude", "-p", "Reply with the single character: x", "--output-format", "json", "--model", model_arg],
            capture_output=True,
            text=True,
            cwd="/tmp",
            timeout=120,
        )
        usage = json.loads(completed.stdout).get("modelUsage", {})
        ids = list(usage.keys())
        return ids[0] if ids else None
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return None


def _eligible_rows(
    cold: list[Decision],
    warm: list[Decision],
    truth: dict[str, GroundTruth],
    eligible_ids: list[str],
) -> list[dict[str, object]]:
    cold_by = {d.transaction_id: d for d in cold}
    warm_by = {d.transaction_id: d for d in warm}
    rows: list[dict[str, object]] = []
    for tid in eligible_ids:
        c = cold_by.get(tid)
        w = warm_by.get(tid)
        g = truth.get(tid)
        if c is None or w is None or g is None:
            continue
        warm_correct = w.account == g.account and set(w.match) == set(g.match)
        cold_correct = c.account == g.account and set(c.match) == set(g.match)
        rows.append(
            {
                "transaction_id": tid,
                "cold_account": c.account,
                "warm_account": w.account,
                "gt_account": g.account,
                "cold_match": c.match,
                "warm_match": w.match,
                "gt_match": g.match,
                "cold_correct": cold_correct,
                "warm_correct": warm_correct,
                "became_correct": warm_correct and not cold_correct,
            }
        )
    return rows


def _summary(report: EvalReport) -> str:
    gate_lines = [
        f"  {name:>16}: precision {gate.precision:.2f} recall {gate.recall:.2f} "
        f"(predicted {gate.predicted}, expected {gate.expected})"
        for name, gate in report.gates.items()
    ]
    lift = "n/a" if report.lift is None else f"{report.lift:+.2f}"
    cold = "n/a" if report.cold_accuracy is None else f"{report.cold_accuracy:.2f}"
    warm = "n/a" if report.corrected_accuracy is None else f"{report.corrected_accuracy:.2f}"
    return "\n".join(
        [
            f"categorization_accuracy : {report.categorization_accuracy:.3f}",
            f"match_accuracy          : {report.match_accuracy:.3f}",
            f"false_confidence_count  : {report.false_confidence_count}",
            f"routing                 : {report.counts}",
            "gates:",
            *gate_lines,
            f"lift (eligible n={report.eligible_count}): cold {cold} -> warm {warm} = {lift}",
            f"eligible_ids            : {report.eligible_ids}",
        ]
    )


async def run(args: argparse.Namespace) -> EvalReport:
    repo = Repository()
    agent = _build_agent(args.agent, args.model)
    subset = _subset_ids(args.subset, args.limit, repo, args.customer)

    harness = LiftHarness(
        repo, agent, args.customer, concurrency=args.concurrency, retries=args.retries
    )
    cold_result, warm_result = await harness.cold_and_warm(subset)

    report = lift_report(cold_result.decisions, warm_result.decisions, repo)
    truth = repo.ground_truth()

    model_id = probe_model_id(args.model or "sonnet") if args.agent == "claude" else (args.model or None)

    artifact: dict[str, object] = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "as_of_date": args.date,
            "agent": args.agent,
            "model_arg": args.model or ("sonnet" if args.agent == "claude" else None),
            "model_id": model_id,
            "customer_id": args.customer,
            "subset": args.subset if args.limit is None else f"{args.subset}[:{args.limit}]",
            "concurrency": args.concurrency,
            "retries": args.retries,
            "warm_decided": len(warm_result.decisions),
            "warm_failed": warm_result.failed,
            "cold_decided": len(cold_result.decisions),
            "cold_failed": cold_result.failed,
        },
        "report": report.model_dump(mode="json"),
        "eligible_rows": _eligible_rows(
            cold_result.decisions, warm_result.decisions, truth, report.eligible_ids
        ),
    }

    out = Path(args.out)
    out.write_text(json.dumps(artifact, indent=2))
    print(_summary(report))
    print(f"\nwrote artifact -> {out}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AGL cold-vs-warm lift eval and write the artifact.")
    parser.add_argument("--agent", choices=["claude", "llm"], default="claude")
    parser.add_argument("--model", default=None)
    parser.add_argument("--customer", default=_DEFAULT_CUSTOMER)
    parser.add_argument("--subset", default="representative", help="'all', 'representative', or comma-separated ids")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--out", default=str(_DEFAULT_OUT))
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
