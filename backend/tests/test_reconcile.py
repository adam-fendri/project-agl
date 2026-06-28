from __future__ import annotations

import pytest

from agl.grounding import build_evidence
from agl.models import Transaction
from agl.reconcile import find_candidates
from agl.repository import Repository

CUSTOMER = "studio-vondel"


@pytest.fixture(scope="module")
def repo() -> Repository:
    return Repository()


@pytest.fixture(scope="module")
def by_id(repo: Repository) -> dict[str, Transaction]:
    return {t.id: t for t in repo.transactions(CUSTOMER)}


def _candidate_document_sets(repo: Repository, txn: Transaction) -> set[frozenset[str]]:
    candidates = find_candidates(txn, repo.invoices(CUSTOMER), repo.bills(CUSTOMER))
    return {frozenset(c.document_ids) for c in candidates}


def _evidence_document_sets(repo: Repository, txn: Transaction) -> set[frozenset[str]]:
    evidence = build_evidence(txn, repo, CUSTOMER)
    return {frozenset(c.candidate.document_ids) for c in evidence.candidates}


def test_paid_collision_invoice_is_a_reachable_candidate(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    sets = _candidate_document_sets(repo, by_id["T072"])

    assert frozenset({"INV-2026-004"}) in sets
    assert frozenset({"INV-2026-005"}) in sets


def test_paid_documents_are_not_filtered_from_candidates(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    invoice = repo.document("INV-2026-004")
    assert invoice is not None and invoice.status.value == "paid"

    sets = _candidate_document_sets(repo, by_id["T074"])

    assert frozenset({"INV-2026-005"}) in sets


def test_split_payment_combination_is_reachable(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    sets = _candidate_document_sets(repo, by_id["T076"])

    assert frozenset({"INV-2026-006", "INV-2026-007"}) in sets


def test_grounding_surfaces_swapped_collision_invoice_for_t072(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    sets = _evidence_document_sets(repo, by_id["T072"])

    assert frozenset({"INV-2026-004"}) in sets


def test_grounding_surfaces_swapped_collision_invoice_for_t074(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    sets = _evidence_document_sets(repo, by_id["T074"])

    assert frozenset({"INV-2026-005"}) in sets


def test_grounding_surfaces_split_combination_for_t076(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    sets = _evidence_document_sets(repo, by_id["T076"])

    assert frozenset({"INV-2026-006", "INV-2026-007"}) in sets


def test_credibly_settled_recurring_bill_is_not_offered_to_later_payment(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    sets = _evidence_document_sets(repo, by_id["T070"])

    assert frozenset({"B-10"}) not in sets
