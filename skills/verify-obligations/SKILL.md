---
name: verify-obligations
description: Walk a lawyer through confirming extracted obligations against the contract before they drive any alert. Trigger on "verify these obligations", "confirm the extracted terms", "review the register for verification", "which obligations need verifying", "sign off these obligations", or as the verification step of obligation management. Sets verified/verified_by/verified_at and captures the verbatim clause. Alerts fire only from verified rows.
---

# Verify obligations before they drive alerts

Extraction is a first pass. A diary date a lawyer has not confirmed must never
reach a calendar, a Slack digest, or a client. This is the human-in-the-loop gate.

**Read first:** `${CLAUDE_PLUGIN_ROOT}/reference/register-schema.md` (the
verification fields).

## Flow

1. **List what needs verifying:** the active rows where `verified` is false. Run
   `python3 ${CLAUDE_PLUGIN_ROOT}/tools/sweep.py register/register.json --today <date> --require-verified`
   — the `NEEDS VERIFICATION` section is exactly this set.
2. **For each, show the lawyer the grounds:** the summary, the computed diary date
   and how it was derived (term end − notice window), and the **verbatim clause**
   (`clause_text`). If `clause_text` is empty, capture it now from the source
   document — a verified row must carry its citation (the guard warns otherwise).
3. **On the lawyer's confirmation**, set `verified: true`, `verified_by` to the
   lawyer, `verified_at` to today. If they correct a date/owner/category, apply the
   correction first, then verify. If they reject the row, mark `status: waived`
   with a note, don't delete it.
4. **Persist** and run `python3 ${CLAUDE_PLUGIN_ROOT}/tools/check_register.py register/register.json`.

## Why it matters

- The calendar sync (`calendar-sync`) and client reports (`report.py`) are
  **verified-only**. Verifying a row is what makes it actionable downstream.
- Keep verification honest: do not bulk-verify without actually checking the
  clause. The point of the gate is that a human read the words.
