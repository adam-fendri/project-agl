from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from agl.models import (
    Account,
    Bill,
    Correction,
    GroundTruth,
    Invoice,
    ProvidedMatch,
    Transaction,
)

SEEDS = Path(__file__).resolve().parent.parent / "seeds"
RUNTIME = Path(__file__).resolve().parent.parent / "runtime"

T = TypeVar("T", bound=BaseModel)


def _runtime_dir(override: Path | None) -> Path:
    if override is not None:
        return override
    env = os.getenv("AGL_RUNTIME_DIR")
    return Path(env) if env else RUNTIME


class CorrectionsStore:
    """Writable store for corrections learned at runtime, kept strictly separate from the read-only seed fixtures.

    The committed ``seeds/corrections.json`` holds the five prior accountant corrections and is never
    mutated; everything an accountant teaches the system at runtime is appended here instead.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> list[Correction]:
        if not self._path.exists():
            return []
        records: list[object] = json.loads(self._path.read_text())
        return [Correction.model_validate(record) for record in records]

    def append(self, correction: Correction) -> None:
        self.save([*self.load(), correction])

    def save(self, corrections: list[Correction]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [correction.model_dump(mode="json") for correction in corrections]
        self._path.write_text(json.dumps(payload, indent=2))


class Repository:
    def __init__(self, seeds_dir: Path = SEEDS, runtime_dir: Path | None = None) -> None:
        self._seeds_dir = seeds_dir
        self._runtime_dir = _runtime_dir(runtime_dir)
        self._accounts = self._load(seeds_dir / "accounts.json", Account)
        self._transactions = self._load(seeds_dir / "transactions.json", Transaction)
        self._invoices = self._load(seeds_dir / "invoices.json", Invoice)
        self._bills = self._load(seeds_dir / "bills.json", Bill)
        self._provided = self._load(seeds_dir / "provided_matches.json", ProvidedMatch)
        self._seed_corrections = self._load(seeds_dir / "corrections.json", Correction)
        self._truth = self._load(seeds_dir / "ground_truth.json", GroundTruth)

        self.store = CorrectionsStore(self._runtime_dir / "corrections.json")
        self._runtime_corrections = self.store.load()

        self._invoice_by_id = {i.id: i for i in self._invoices}
        self._bill_by_id = {b.id: b for b in self._bills}
        self._txn_by_id = {t.id: t for t in self._transactions}
        self._provided_by_txn = {p.transaction_id: p for p in self._provided}
        self._truth_by_txn = {g.transaction_id: g for g in self._truth}

    @staticmethod
    def _load(path: Path, model: type[T]) -> list[T]:
        return [model.model_validate(record) for record in json.loads(path.read_text())]

    def reload(self) -> Repository:
        """A fresh Repository over the same seed and runtime locations, re-reading the runtime store."""
        return Repository(self._seeds_dir, self._runtime_dir)

    def accounts(self, customer_id: str) -> list[Account]:
        return [a for a in self._accounts if a.customer_id == customer_id]

    def transactions(self, customer_id: str) -> list[Transaction]:
        return [t for t in self._transactions if t.customer_id == customer_id]

    def transaction(self, transaction_id: str) -> Transaction | None:
        return self._txn_by_id.get(transaction_id)

    def invoices(self, customer_id: str) -> list[Invoice]:
        return [i for i in self._invoices if i.customer_id == customer_id]

    def bills(self, customer_id: str) -> list[Bill]:
        return [b for b in self._bills if b.customer_id == customer_id]

    def document(self, doc_id: str) -> Invoice | Bill | None:
        if doc_id.startswith("INV-"):
            return self._invoice_by_id.get(doc_id)
        return self._bill_by_id.get(doc_id)

    def provided_match(self, transaction_id: str) -> ProvidedMatch | None:
        return self._provided_by_txn.get(transaction_id)

    def corrections(self, customer_id: str) -> list[Correction]:
        merged = [*self._seed_corrections, *self._runtime_corrections]
        return [c for c in merged if c.customer_id == customer_id]

    def ground_truth(self) -> dict[str, GroundTruth]:
        return dict(self._truth_by_txn)
