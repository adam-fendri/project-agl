# Neno AI Engineer Case Challenge — Challenge 2 (CANONICAL BRIEF)

> Source of truth. Refer here, do not paraphrase from memory. Personal job challenge for Neno
> (a fintech SaaS), NOT VoxAI work.

## Challenge 2: Accountant-supervised categorization and reconciliation
This is the surface where every decision matters: confidence thresholds, learning from corrections, audit, handoff.

### Inputs the agent has access to
Production data lives in Postgres on GCP. For this challenge, assume an API exposes the following as JSON
(model the data for your demo):
- 100 bank transactions (EUR, mixed: invoices paid, expenses, payroll, ambiguous)
- 10 invoices issued by this customer with metadata (some paid, some unpaid)
- 20 bills this customer received (some were already paid by the customer)
- Transaction <-> invoice and transaction <-> bill matches are **provided by Neno's infrastructure at ~96% accuracy**.
- A chart of accounts for a typical Dutch SME (2-50 FTE)
- 5 prior accountant corrections on this customer, e.g. chart of accounts attribution, transaction-to-invoice match.

### Decisions the accountant-side agent must make
- Which account in the Chart of Accounts a transaction belongs to, and whether it matches an open invoice
- Whether a transaction is anomalous e.g. potential fraud, miscategorized, missing counterpart
- When confidence is low enough that the accountant must review before the entry is posted
- If the matching invoice/bill/transaction is not in the system, should it be requested from the entrepreneur and when?

### What the supervising accountant sees
- A queue ordered by where their attention adds the most value, with each suggestion showing the agent's
  choice, reasoning, sources, and confidence
- The ability to accept, correct, or ask the agent to explain

### Outcomes you should design for
- Accountant capacity: 30 -> 60 customers per accountant (stay on the curve to 100+). Tell us, in minutes
  saved per customer per month, how your system gets there and which workflow steps deliver the largest cuts.
- Correctness vs false-confidence rate, e.g. agent was sure and wrong. This is the number that kills trust.
  Name your target and how you hold it.
- How quickly the system learns from a correction (one accountant edit should move the next 10 similar
  transactions, not just the one)
- For the entrepreneur conversation: does the entrepreneur walk away with the right answer, and the right next step?

### Demo (Challenge 2)
- 90%+ of transactions that the agent is confident in categorizing, with reasoning visible.
- A few the agent is uncertain on, surfaced for review with the right context.
- One transaction flagged as anomalous, and what the accountant clicks next.
- Build a live prototype against the mocked data: a Claude project or simple web app. The design decisions,
  user interactions and agentic workflow should be visible and defensible.

## Deliverables
- A live prototype, wired end-to-end to a real LLM: Google's Gemini or Anthropic's Claude family.
- Architecture diagram (one page: agent topology, tool boundary, where the human sits, where context comes from)
- Either a video demo (7 min max), or a concise presentation (<15 slides). Screen-share and walk us through it.

## Tooling (defend, one sentence each)
- Model choice: which frontier model(s) for which step, and why.
- Agent framework / orchestration: direct calls or a framework of your choice, trade-offs.
- Retrieval & context: how you engineer what agents work with.
- Evals: how you'd measure the accuracy of the agent's response, false-confidence, blocked responses.
- Observability: how do you enable yourself to debug your agentic flows.
(We care more about the reasoning than the names.)

## Evaluation Criteria
- Strategic Thinking: act vs defer (and defend it); the precision bar for financial workflows
  (reconciliation, VAT, audit); the latency/accuracy/trust trade-off; assumptions about model capability,
  data quality, and the accountant's role, and why.
- Technical Depth: agent interaction patterns, context engineering, RAG, evaluation, observability.
- Prioritization: focus on the end users (accountant + entrepreneur) over what is interesting as a technical problem.
- Execution: practical, shippable, and safe enough for real customer financial data.
- Communication: clear, concise, structured; a non-AI engineer on the team can follow your design decisions.

## Bonus Points
- Delivering both challenges
- Running a real eval on the seeded data and reporting numbers
- Adding a trace/observability view: tool call, prompt, confidence, with a clickable example

## Time / Submission
- ~6 hours expected.
- Live prototype wired to a real LLM (Gemini/Anthropic) on the mocked data; one-page architecture diagram;
  video walkthrough (7 min max) OR slide deck (PDF, <15 slides).

## Guiding Question
If you joined Neno tomorrow, how would you design Project AGL so that an accountant can sign off on every
entry it produces, an entrepreneur gets an answer before their coffee cools, and neither of them ever sees
the AI confidently get it wrong? And what timelines and resources do you need to make this real?
