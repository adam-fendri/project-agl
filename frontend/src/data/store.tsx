import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api, ApiError } from "../api/client";
import type {
  Account,
  AssignAccountRequest,
  CorrectRequest,
  CorrectResponse,
  Customer,
  Decision,
  DocumentView,
  EvalReport,
  HandledRecord,
  Transaction,
} from "../api/types";

export type ToastTone = "info" | "success" | "danger";

export interface Toast {
  id: number;
  message: string;
  tone: ToastTone;
}

interface AppData {
  customer: Customer | null;
  accounts: Account[];
  accountByNumber: Record<string, Account>;
  documents: DocumentView[];
  documentById: Record<string, DocumentView>;
  openDocuments: DocumentView[];
  txnById: Record<string, Transaction>;
  queue: Decision[];
  posted: Decision[];
  handled: HandledRecord[];
  metrics: EvalReport | null;
  engineHasRun: boolean;
  bootLoading: boolean;
  bootError: string | null;
  running: boolean;
  selectedId: string | null;
  selected: Decision | null;
  selectLoading: boolean;
  openDecision: (id: string) => void;
  closeDecision: () => void;
  runEngine: () => Promise<void>;
  accept: (id: string) => Promise<void>;
  handle: (id: string) => Promise<void>;
  correct: (id: string, body: CorrectRequest) => Promise<CorrectResponse | null>;
  assignAccount: (id: string, body: AssignAccountRequest) => Promise<void>;
  toasts: Toast[];
  notify: (message: string, tone?: ToastTone) => void;
  dismissToast: (id: number) => void;
  isPosted: (id: string) => boolean;
  isHandled: (id: string) => boolean;
}

const AppDataContext = createContext<AppData | null>(null);

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong.";
}

export function AppDataProvider({ children }: { children: ReactNode }) {
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [documents, setDocuments] = useState<DocumentView[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [queue, setQueue] = useState<Decision[]>([]);
  const [posted, setPosted] = useState<Decision[]>([]);
  const [handled, setHandled] = useState<HandledRecord[]>([]);
  const [metrics, setMetrics] = useState<EvalReport | null>(null);

  const [bootLoading, setBootLoading] = useState(true);
  const [bootError, setBootError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Decision | null>(null);
  const [selectLoading, setSelectLoading] = useState(false);

  const [toasts, setToasts] = useState<Toast[]>([]);
  const toastSeq = useRef(0);

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const notify = useCallback(
    (message: string, tone: ToastTone = "info") => {
      const id = (toastSeq.current += 1);
      setToasts((current) => [...current, { id, message, tone }]);
      window.setTimeout(() => dismissToast(id), 4600);
    },
    [dismissToast],
  );

  const refresh = useCallback(async () => {
    const [nextAccounts, nextDocuments, nextQueue, nextPosted, nextHandled, nextMetrics] =
      await Promise.all([
        api.accounts(),
        api.documents(),
        api.queue(),
        api.posted(),
        api.handled(),
        api.metrics(),
      ]);
    setAccounts(nextAccounts);
    setDocuments(nextDocuments);
    setQueue(nextQueue);
    setPosted(nextPosted);
    setHandled(nextHandled);
    setMetrics(nextMetrics);
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [nextCustomer, nextTransactions] = await Promise.all([
          api.customer(),
          api.transactions(),
        ]);
        if (!active) {
          return;
        }
        setCustomer(nextCustomer);
        setTransactions(nextTransactions);
        await refresh();
      } catch (error) {
        if (active) {
          setBootError(errorMessage(error));
        }
      } finally {
        if (active) {
          setBootLoading(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [refresh]);

  const fetchSelected = useCallback(async (id: string) => {
    try {
      const decision = await api.decision(id);
      setSelected(decision);
    } catch {
      setSelected(null);
    }
  }, []);

  const openDecision = useCallback(
    (id: string) => {
      setSelectedId(id);
      setSelectLoading(true);
      api
        .decision(id)
        .then((decision) => setSelected(decision))
        .catch(() => setSelected(null))
        .finally(() => setSelectLoading(false));
    },
    [],
  );

  const closeDecision = useCallback(() => {
    setSelectedId(null);
    setSelected(null);
  }, []);

  const runEngine = useCallback(async () => {
    setRunning(true);
    try {
      await api.run();
      await refresh();
      closeDecision();
      notify("Engine run complete. The queue is ready.", "success");
    } catch (error) {
      notify(errorMessage(error), "danger");
    } finally {
      setRunning(false);
    }
  }, [refresh, closeDecision, notify]);

  const accept = useCallback(
    async (id: string) => {
      try {
        await api.accept(id);
        await refresh();
        await fetchSelected(id);
        notify(`${id} posted to the ledger.`, "success");
      } catch (error) {
        notify(errorMessage(error), "danger");
      }
    },
    [refresh, fetchSelected, notify],
  );

  const handle = useCallback(
    async (id: string) => {
      try {
        const record = await api.handle(id);
        await refresh();
        await fetchSelected(id);
        const verb =
          record.action === "request_document" ? "Document requested" : "Flagged and held";
        notify(`${id}: ${verb}.`, "success");
      } catch (error) {
        notify(errorMessage(error), "danger");
      }
    },
    [refresh, fetchSelected, notify],
  );

  const correct = useCallback(
    async (id: string, body: CorrectRequest) => {
      try {
        const response = await api.correct(id, body);
        await refresh();
        await fetchSelected(id);
        const reran = response.reran.length;
        const suffix = reran === 1 ? "1 similar transaction re-run" : `${reran} similar transactions re-run`;
        notify(`Correction saved. ${suffix}.`, "success");
        return response;
      } catch (error) {
        notify(errorMessage(error), "danger");
        return null;
      }
    },
    [refresh, fetchSelected, notify],
  );

  const assignAccount = useCallback(
    async (id: string, body: AssignAccountRequest) => {
      try {
        const updated = await api.assignAccount(id, body);
        await refresh();
        await fetchSelected(id);
        const count = updated.length;
        const suffix = count === 1 ? "1 decision re-run" : `${count} decisions re-run`;
        notify(`Account ${body.number} assigned. ${suffix}.`, "success");
      } catch (error) {
        notify(errorMessage(error), "danger");
      }
    },
    [refresh, fetchSelected, notify],
  );

  const accountByNumber = useMemo(
    () => Object.fromEntries(accounts.map((account) => [account.number, account])),
    [accounts],
  );
  const documentById = useMemo(
    () => Object.fromEntries(documents.map((document) => [document.id, document])),
    [documents],
  );
  const openDocuments = useMemo(
    () => documents.filter((document) => document.status === "unpaid"),
    [documents],
  );
  const txnById = useMemo(
    () => Object.fromEntries(transactions.map((txn) => [txn.id, txn])),
    [transactions],
  );

  const postedIds = useMemo(
    () => new Set(posted.map((decision) => decision.transaction_id)),
    [posted],
  );
  const handledIds = useMemo(
    () => new Set(handled.map((record) => record.transaction_id)),
    [handled],
  );

  const isPosted = useCallback((id: string) => postedIds.has(id), [postedIds]);
  const isHandled = useCallback((id: string) => handledIds.has(id), [handledIds]);

  const engineHasRun =
    (metrics?.counts.total ?? 0) > 0 ||
    queue.length > 0 ||
    posted.length > 0 ||
    handled.length > 0;

  const value: AppData = {
    customer,
    accounts,
    accountByNumber,
    documents,
    documentById,
    openDocuments,
    txnById,
    queue,
    posted,
    handled,
    metrics,
    engineHasRun,
    bootLoading,
    bootError,
    running,
    selectedId,
    selected,
    selectLoading,
    openDecision,
    closeDecision,
    runEngine,
    accept,
    handle,
    correct,
    assignAccount,
    toasts,
    notify,
    dismissToast,
    isPosted,
    isHandled,
  };

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>;
}

export function useAppData(): AppData {
  const context = useContext(AppDataContext);
  if (!context) {
    throw new Error("useAppData must be used within AppDataProvider");
  }
  return context;
}
