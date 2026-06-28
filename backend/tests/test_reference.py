from __future__ import annotations

import pytest

from agl.grounding import referenced_documents
from agl.guard import run_guard
from agl.models import Confidence, Outcome, Proposal, Transaction
from agl.repository import Repository

CUSTOMER = "studio-vondel"


@pytest.fixture(scope="module")
def repo() -> Repository:
    return Repository()


@pytest.fixture(scope="module")
def by_id(repo: Repository) -> dict[str, Transaction]:
    return {t.id: t for t in repo.transactions(CUSTOMER)}


@pytest.fixture(scope="module")
def known_ids(repo: Repository) -> set[str]:
    return {i.id for i in repo.invoices(CUSTOMER)} | {b.id for b in repo.bills(CUSTOMER)}


def _proposal(vendor: str, account: str, match: list[str]) -> Proposal:
    return Proposal(
        vendor=vendor,
        account=account,
        account_reasoning="test",
        account_confidence=Confidence.HIGH,
        match=match,
        match_reasoning="test" if match else None,
        match_confidence=Confidence.HIGH,
    )


def _txn_provided(repo: Repository, by_id: dict[str, Transaction], document_id: str) -> Transaction:
    for txn in by_id.values():
        provided = repo.provided_match(txn.id)
        if provided is not None and provided.document_id == document_id:
            return txn
    raise AssertionError(f"no transaction has provided match {document_id}")


def test_referenced_documents_parses_our_invoice_id(
    by_id: dict[str, Transaction], known_ids: set[str]
) -> None:
    assert referenced_documents(by_id["T072"], known_ids) == ["INV-2026-004"]


def test_referenced_documents_ignores_iban_only_remittance(
    by_id: dict[str, Transaction], known_ids: set[str]
) -> None:
    assert referenced_documents(by_id["T046"], known_ids) == []


def test_wrong_reference_match_is_flagged_and_not_auto(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal("Lumen Retail", "1300", ["INV-2026-005"])

    verdict = run_guard(proposal, by_id["T072"], repo, {})

    assert "reference_mismatch" in verdict.failed_checks
    assert verdict.passed is False
    assert verdict.forced_outcome is Outcome.REVIEW


def test_confirming_reference_clears_ambiguity(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal("Voss & Partners", "1300", ["INV-2026-004"])

    verdict = run_guard(proposal, by_id["T072"], repo, {})

    assert "reference_mismatch" not in verdict.failed_checks
    assert "amount_ambiguous" not in verdict.failed_checks


def test_same_amount_rent_without_reference_still_passes_fuzzy(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    txn = _txn_provided(repo, by_id, "B-01")
    proposal = _proposal("Kantoorpand", "4200", ["B-01"])

    verdict = run_guard(proposal, txn, repo, {})

    assert "reference_mismatch" not in verdict.failed_checks
    assert "amount_ambiguous" not in verdict.failed_checks
