from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel

from agl.models import (
    Account,
    Bill,
    Correction,
    Customer,
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


class RuntimeStore(Generic[T]):
    """Append-only JSON store for records the accountant teaches at runtime, kept strictly separate from the read-only seed fixtures.

    The committed ``seeds/*.json`` fixtures are never mutated; everything learned at runtime — the
    corrections, and the accounts the accountant adds to grow the chart — is appended to its own file
    under ``runtime_dir`` instead.
    """

    def __init__(self, path: Path, model: type[T]) -> None:
        self._path = path
        self._model = model

    def load(self) -> list[T]:
        if not self._path.exists():
            return []
        records: list[object] = json.loads(self._path.read_text())
        return [self._model.model_validate(record) for record in records]

    def append(self, record: T) -> None:
        self.save([*self.load(), record])

    def save(self, records: list[T]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [record.model_dump(mode="json") for record in records]
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
        self._customers = self._load(seeds_dir / "customers.json", Customer)

        self.store: RuntimeStore[Correction] = RuntimeStore(
            self._runtime_dir / "corrections.json", Correction
        )
        self._runtime_corrections = self.store.load()
        self.accounts_store: RuntimeStore[Account] = RuntimeStore(
            self._runtime_dir / "accounts.json", Account
        )
        self._runtime_accounts = self.accounts_store.load()

        self._invoice_by_id = {i.id: i for i in self._invoices}
        self._bill_by_id = {b.id: b for b in self._bills}
        self._txn_by_id = {t.id: t for t in self._transactions}
        self._provided_by_txn = {p.transaction_id: p for p in self._provided}
        self._truth_by_txn = {g.transaction_id: g for g in self._truth}
        self._customer_by_id = {c.id: c for c in self._customers}

    @staticmethod
    def _load(path: Path, model: type[T]) -> list[T]:
        return [model.model_validate(record) for record in json.loads(path.read_text())]

    def reload(self) -> Repository:
        """A fresh Repository over the same seed and runtime locations, re-reading the runtime store."""
        return Repository(self._seeds_dir, self._runtime_dir)

    @property
    def runtime_dir(self) -> Path:
        return self._runtime_dir

    def accounts(self, customer_id: str) -> list[Account]:
        chart = [*self._accounts, *self._runtime_accounts]
        return [a for a in chart if a.customer_id == customer_id]

    def add_account(self, account: Account) -> Repository:
        """Append a new account to the runtime chart and return a reloaded Repository; the seed chart is never mutated.

        Rejects a number already present in the customer's chart, so the chart only ever grows with genuinely new accounts.
        """
        if account.number in {a.number for a in self.accounts(account.customer_id)}:
            raise ValueError(f"account {account.number!r} already in the chart")
        self.accounts_store.append(account)
        return self.reload()

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

    def customer(self, customer_id: str) -> Customer | None:
        return self._customer_by_id.get(customer_id)

    def customers(self) -> list[Customer]:
        return list(self._customers)
