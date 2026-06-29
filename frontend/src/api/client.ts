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
  Trace,
  Transaction,
} from "./types";

const BASE = import.meta.env.DEV ? "/api" : "";

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  method: "GET" | "POST",
  body?: unknown,
): Promise<T> {
  const init: RequestInit = { method, headers: {} };
  if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  const response = await fetch(`${BASE}${path}`, init);
  if (!response.ok) {
    throw new ApiError(response.status, await detail(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function detail(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") {
      return data.detail;
    }
    return `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

export const api = {
  customer: () => request<Customer>("/customer", "GET"),
  accounts: () => request<Account[]>("/accounts", "GET"),
  documents: () => request<DocumentView[]>("/documents", "GET"),
  transactions: () => request<Transaction[]>("/transactions", "GET"),
  queue: () => request<Decision[]>("/queue", "GET"),
  posted: () => request<Decision[]>("/posted", "GET"),
  handled: () => request<HandledRecord[]>("/handled", "GET"),
  metrics: () => request<EvalReport>("/metrics", "GET"),
  run: () => request<Decision[]>("/run", "POST"),
  decision: (id: string) => request<Decision>(`/transaction/${id}`, "GET"),
  trace: (id: string) => request<Trace>(`/trace/${id}`, "GET"),
  accept: (id: string) => request<Decision>(`/transaction/${id}/accept`, "POST"),
  handle: (id: string) =>
    request<HandledRecord>(`/transaction/${id}/handle`, "POST"),
  correct: (id: string, body: CorrectRequest) =>
    request<CorrectResponse>(`/transaction/${id}/correct`, "POST", body),
  assignAccount: (id: string, body: AssignAccountRequest) =>
    request<Decision[]>(`/transaction/${id}/assign-account`, "POST", body),
};
