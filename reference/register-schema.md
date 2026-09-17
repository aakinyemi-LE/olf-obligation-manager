# Obligation register — schema (prototype store)

The register is the **single durable store** the whole plugin reads and writes.
For the prototype it is a plain JSON file (`register/register.json`, seeded from
`register/register.sample.json`). The schema is deliberately store-agnostic so it
can be lifted into Notion / Ontra Insight later without changing the skills — the
field names below map 1:1 onto columns in whatever store replaces the file.

Treat the register as the source of truth. Extraction **appends/updates** rows;
the sweep **reads** rows and computes what needs action; the dashboard **renders**
rows. Nothing in this plugin sends anything — the Slack digest is a draft.

## File shape

```json
{
  "schema_version": "0.1.0",
  "generated": "2026-09-16",
  "obligations": [ { …obligation… } ]
}
```

## Obligation record

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable key, `OBL-NNNN`. Never reused. |
| `client` | string | The OLF client the obligation is tracked for. |
| `counterparty` | string | The other party to the contract. |
| `contract_title` | string | Human name of the executed contract. |
| `contract_ref` | string | Internal/file reference, if any. |
| `source_document` | string | Path/URL to the executed document (evidence). |
| `category` | enum | One of the taxonomy categories — see `obligation-taxonomy.md`: `renewal`, `notice`, `termination`, `price_adjustment`, `reporting`, `insurance`, `data_privacy`, `audit`, `other`. |
| `clause_ref` | string | Where in the contract it lives, e.g. `§11.2`. |
| `summary` | string | One-sentence, plain-lawyer description of the provision. |
| `action_required` | string | The concrete step and its consequence if missed. |
| `obligation_owner` | enum | Who must act: `client`, `counterparty`, `mutual`. |
| `responsible_lawyer` | string | OLF lawyer accountable for the diary entry. |
| `trigger_type` | enum | `recurring`, `one_time`, `conditional`. |
| `effective_date` | date | When the contract/obligation started (`YYYY-MM-DD`). |
| `term_end_date` | date\|null | Current term end, if dated. |
| `notice_window_days` | int\|null | Days of advance notice the provision requires. |
| `recurrence` | enum | `annual`, `quarterly`, `monthly`, `none`. |
| `next_action_date` | date\|null | **The diary date.** Usually `term_end_date − notice_window_days`, or the next recurring due date. This is what the sweep keys on. |
| `status` | enum | `active`, `snoozed`, `completed`, `waived`. |
| `confidence` | enum | Extraction confidence: `high`, `medium`, `low`. Low → lawyer must verify. |
| `last_reviewed` | date | When a human last confirmed this row. |
| `notes` | string | Free text. |
| `clause_text` | string | **Verbatim** quote of the operative clause — the citation a lawyer checks against. Empty until captured. |
| `verified` | bool | A human has confirmed this row. **Alerts (calendar, Slack, client invites) fire only from verified rows.** |
| `verified_by` | string\|null | Who verified it. |
| `verified_at` | date\|null | When. |
| `responsible_lawyer_email` | string | Owner of the diary entry — the internal calendar invitee. |
| `client_contact_email` | string | Client-side contact, used only for an approved client invite. |
| `invite_to_client` | bool | Opt-in: may a client deadline invite be *drafted* for this row. Default false. |
| `invite_status` | enum | `none`, `pending_approval`, `approved`, `sent`. Client invites never leave `pending_approval` without explicit approval. |
| `calendar_event_id` | string\|null | Id of the synced internal calendar event — makes sync **idempotent** (re-runs update, never duplicate). |
| `calendar_synced_at` | date\|null | When the event was last synced. |

## Rules the validator enforces (`tools/check_register.py`)

1. `id` is present, unique, and matches `OBL-\d{4}`.
2. `category`, `obligation_owner`, `trigger_type`, `recurrence`, `status`,
   `confidence` are within their enums.
3. All date fields that are present parse as `YYYY-MM-DD`.
4. If `notice_window_days` and `term_end_date` are both set and
   `next_action_date` is set, it should equal `term_end_date − notice_window_days`
   (warning, not error — a lawyer may override the diary date deliberately).
5. Every `active` row has a `next_action_date` (else it can never surface).

The guard is a gate, exactly like the review-bot's `check_review_state.py`.
