# Output contract — what the plugin hands back

Same house style as the review-bot: **cards at the top**, then a succinct chat
summary. **Draft-only — nothing sends.** Three surfaces:

## 1. Chat packet (always)

After any extraction or sweep, chat opens with a **count line**, then the detail.

- **Extraction reply:** `N obligations captured · M need a lawyer's eye`
  (the second count = rows with `confidence: low`). Then a short list grouped by
  category, each: `[OBL-id] category — summary` + the diary date + `action_required`.
  End with the low-confidence rows called out for verification. Do **not** dump
  the full JSON in chat — it goes to the register and the dashboard.
- **Sweep reply:** `X overdue · Y imminent · Z upcoming · W on watch`, then the
  bucketed list (the `sweep.py` text render is the canonical shape). Only surface
  buckets that have items; if nothing needs action inside the horizon, say so in
  one line rather than printing empty sections.

Keep it lean: no em-dashes, plain lawyer voice, no "Claude-speak". The chat is a
scan surface, not a data dump.

## 2. HTML dashboard console (card at top)

`assets/dashboard-template.html`, populated by replacing the JSON in
`<script id="register-data">`. A scan-first view of the register:

- **Header strip:** four tiles — Overdue · Imminent · Upcoming · On watch.
- **Timeline table:** one row per obligation, sorted by `next_action_date`,
  colour-coded by urgency (red overdue, amber imminent, yellow upcoming, grey
  watch, green done). Columns: diary date · client · category · contract · clause
  · action · owner · status.
- **Per-row "Your call" control** (mirrors the review-bot decisions layer):
  Done / Snooze / Waive + optional note, persisted per-viewer in `localStorage`
  keyed by obligation id. A **Copy updates to chat** button emits a plain-text
  `Register updates` block the lawyer pastes back so the plugin applies the
  status deltas to the register (re-diarises, marks done, etc.) rather than
  re-extracting.
- Every `clause_ref` links to the source clause when `source_document` sections
  are supplied, exactly as the review-bot console does.

## 3. Slack digest (internal team channel)

The sweep's `--format post` output (standard markdown, shaped for the Slack
connector) is **posted to the internal OLF team channel** named in
`config/notify.json`. This is an authorised internal reminder — on request now,
and auto-posting once a schedule is enabled (`skills/obligation-sweep/SKILL.md`).
The sweep stays **silent when nothing needs action** (`--quiet-when-empty`), so
the channel only lights up when there is something to do. A live post needs
`plugin:legal:slack` authorised; if it isn't, the plugin hands over the text to
paste. `--format slack` (native mrkdwn) remains available for manual paste.
Anything outbound to a client or counterparty is a different surface and stays
draft-only.

## 4. Internal calendar (Google) + client invites

`tools/calendar_plan.py` computes an idempotent sync plan; `skills/calendar-sync`
executes it via the Google Calendar connector. **Internal** events (on the shared
"OLF Obligations" calendar) may be created/updated without a per-event click;
duplicates are prevented by writing `calendar_event_id` back to the row. **Client
deadline invites are draft-only** and need per-item approval (and only fire from a
verified row). Provider is Google today; Teams/Outlook awaits a Microsoft Graph
connector.

## 5. Per-client report

`tools/report.py --client "<name>"` (or `--all`) emits a client-facing markdown
report of what OLF is tracking and what is coming up — the QBR deliverable. It is
**verified-only**: unverified rows are excluded and noted as an internal aside.

## Verification gate (applies to 3, 4, 5)

A row drives a Slack line, a calendar event, or a client report **only when
`verified` is true**. Extraction yields candidates; `skills/verify-obligations`
turns them into actionable rows once a lawyer confirms them against the verbatim
`clause_text`. The sweep's `--require-verified` surfaces the unverified queue
without alerting on it.

## Shared object

The register (`reference/register-schema.md`) is the single state object that all
three surfaces read from. Extraction writes it; the dashboard and digest render
it; the "your call" / "register updates" round-trip mutates it. There is no other
hidden state.
