---
name: calendar-sync
description: Sync verified obligation deadlines to an internal shared calendar, and draft client deadline invites for approval. Trigger on "sync the deadlines to the calendar", "put these on the calendar", "calendar the obligations", "add the renewals to my calendar", "send the client a calendar invite for this deadline", or as the calendaring step of obligation management. Internal events may be created/updated; client invites are draft-only and need approval. Fires only from VERIFIED rows.
---

# Sync obligation deadlines to the calendar

Put each verified obligation's diary date on a shared **internal** calendar so it
reaches the lawyer where they already work, and — only on approval — draft a
deadline invite to the client. **Provider today is Google Calendar** (the wired
connector). Teams/Outlook would need a Microsoft Graph connector; until then,
`config/notify.json` → `calendar.provider` stays `google`.

**Read first:** `${CLAUDE_PLUGIN_ROOT}/reference/register-schema.md` (the calendar
fields) and `${CLAUDE_PLUGIN_ROOT}/reference/output-contract.md`.

## The trust gate

Only **verified** active rows with a diary date are eligible. `calendar_plan.py`
enforces this and skips the rest — never override it. An unverified row never
reaches a calendar and never reaches a client.

## Internal sync (may create/update without a further click)

1. Compute the plan deterministically:
   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/tools/calendar_plan.py register/register.json \
     --today <YYYY-MM-DD> --config ${CLAUDE_PLUGIN_ROOT}/config/notify.json --format json
   ```
2. Resolve the target calendar: if `calendar.internal_calendar_id` is blank, call
   `list_calendars`, find (or offer to create) the "OLF Obligations" calendar, and
   offer to save its id back to `config/notify.json`.
3. Execute the plan **idempotently**:
   - `create` → `create_event` (all-day on `start_date`, with the title,
     description, `attendees`, and reminders from the plan). Capture the returned
     event id and **write it back** to that row's `calendar_event_id` +
     `calendar_synced_at` — this is what stops duplicates next run.
   - `update` → `update_event` on the stored `calendar_event_id`.
   - `delete` → `delete_event` (a row that was completed/waived).
4. Re-run the guard after writing ids back.

Because the target is an internal calendar, this may run without a per-event
click (the lawyer authorised it once). Quiet runs (nothing verified/eligible)
create nothing.

## Client invites (DRAFT ONLY — approval required)

The plan lists `client_invites` separately. Each is a **draft**:
- Present it to the lawyer with the client, date, and text.
- **Do not create or send** a client-facing invite unless the row's
  `invite_status` is `approved` AND the lawyer confirms now. Sending a client an
  invite is outbound and per-item — treat it like sending an email. Ideally it
  also carries partner sign-off (a business call, not an automation default).
- On approval, create the event with the client contact as attendee and let the
  invite go; then set `invite_status: sent`. Otherwise leave it
  `pending_approval` and move on.

## If the connector is not authorised

If Google Calendar is not connected, do not attempt writes. Show the plan
(`--format text`) so the lawyer sees exactly what would be created, and say the
calendar connector needs authorising in claude.ai connector settings. Never ask
for tokens.
