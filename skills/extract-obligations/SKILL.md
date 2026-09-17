---
name: extract-obligations
description: Extract post-signature obligations from an executed contract into the register. Trigger on "track the obligations in this", "add this signed contract to the register", "extract the renewals and deadlines", "what are my ongoing duties under this", "capture the obligations", or as the extraction step of obligation management. Reads an executed EL, MSA, DPA, services agreement, or similar and produces diarised register rows. Draft-only.
---

# Extract obligations from an executed contract

Turn one signed contract into a set of diarised register rows. Precision over
recall theatre: capture every future-facing duty, but never fabricate a date.

**Read first:** `${CLAUDE_PLUGIN_ROOT}/reference/obligation-taxonomy.md` (the nine
categories + discipline) and `${CLAUDE_PLUGIN_ROOT}/reference/register-schema.md`
(the row shape).

## Inputs

- The **executed** contract (`.docx` / `.pdf` / pasted text) — the lawyer uploads
  it. Confirm it is signed; obligation tracking is for live contracts.
- Optional: client / counterparty identity if the document is ambiguous.
- Optional: the existing register, so new rows get fresh `OBL-NNNN` ids that don't
  collide.

## Method

1. **Identify the contract header facts** once: client, counterparty,
   contract_title, contract_ref, effective_date, term structure. These populate
   the shared fields on every row from this document.
2. **Walk the contract for obligation-bearing provisions** and classify each into
   one taxonomy category. Look hardest at: term & renewal clause, termination,
   fees/escalators, reporting/deliverables, insurance, data return/deletion,
   audit rights, and any notice requirements. One provision → one row.
3. **For each row, compute the diary date.** Prefer
   `next_action_date = term_end_date − notice_window_days`. Convert stated notice
   periods (months → days) explicitly. If no date can be grounded, set
   `next_action_date: null` and `trigger_type: conditional` (it lands on WATCH).
4. **Set owner and confidence honestly.** `obligation_owner` = who must act.
   `confidence: low` for anything a human must verify — say why in `notes`.
5. **Assign ids** `OBL-NNNN`, continuing from the highest existing id.
6. **Append to the register file**, then run
   `python3 ${CLAUDE_PLUGIN_ROOT}/tools/check_register.py register/register.json`.
   Fix any FAIL before presenting.

## Output

Per the output contract: chat opens with
`N obligations captured · M need a lawyer's eye`, then a short by-category list
(id · summary · diary date · action), then the low-confidence rows called out for
verification. Refresh the dashboard console card. Do not paste the raw JSON into
chat — it lives in the register and the console.
