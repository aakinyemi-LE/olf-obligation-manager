# Obligation taxonomy — what to extract from an executed contract

Post-signature review is **obligation-first**: the job is to find every provision
that creates a *future action, deadline, or standing duty*, and turn it into a
diarised register row. Ignore provisions that are purely historical or fully
discharged at signing. When in doubt, capture it with `confidence: low` and flag
for the lawyer — a missed evergreen renewal is far costlier than a redundant row.

Each captured provision maps to one `category`. The nine categories:

| Category | What it catches | The diary date (`next_action_date`) |
|---|---|---|
| `renewal` | Auto-renewal / evergreen terms; renewal options. | Term end − notice window (the last day to stop the roll-over). |
| `notice` | Fixed-term expiry with **no** auto-renewal; any standalone notice requirement. | Enough lead time before expiry to act (use the stated notice period, else a sensible default). |
| `termination` | Termination for convenience/cause; tail-fee or survival windows triggered by termination. | The notice date if a wind-down is contemplated; otherwise a WATCH row. |
| `price_adjustment` | Fee escalators, CPI/index uplifts, most-favoured-pricing, rebate true-ups. | When the counterparty's price-change notice is expected, or the annual review point. |
| `reporting` | Recurring deliverables: attestations, certifications, financial statements, KPI/SLA reports. | The next recurring due date. |
| `insurance` | Minimum cover levels; certificate-of-insurance (COI) delivery; additional-insured status. | The annual COI-refresh date. |
| `data_privacy` | Data return/deletion on termination, breach-notice windows, sub-processor consent, audit rights over data. | Event-driven (often WATCH) unless there is a periodic duty. |
| `audit` | Audit / inspection rights and the notice needed to exercise them; records-retention duties. | The window open/close date, or WATCH. |
| `other` | Anything obligation-bearing that doesn't fit above (e.g. exclusivity review points, MFN, change-of-control notices). | As applicable. |

## Extraction discipline

- **One provision → one row.** A clause that both auto-renews *and* escalates
  price is two rows (`renewal` + `price_adjustment`), cross-referenced in `notes`.
- **Owner matters.** Set `obligation_owner` to who must *act* (`client`,
  `counterparty`, `mutual`). A counterparty duty (e.g. supplier's COI) still gets
  a row — OLF's job is to *check* it was met.
- **Compute the diary date, don't guess it.** Prefer
  `term_end_date − notice_window_days`. If the contract states the notice period
  as months, convert. If no date can be grounded, leave `next_action_date` null
  and set `trigger_type: conditional` so it lands on the WATCH list.
- **Quote the clause reference** (`clause_ref`) and keep the `source_document`
  pointer — the register row is only trustworthy if it is traceable to the
  executed text.
- **Confidence.** `high` = date and mechanics explicit; `medium` = mechanics
  clear but a date must be inferred; `low` = ambiguous, needs the lawyer's eye.
