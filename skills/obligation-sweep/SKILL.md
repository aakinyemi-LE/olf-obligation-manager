---
name: obligation-sweep
description: Run a compliance sweep over the obligation register and draft a Slack digest of what needs action. Trigger on "run the obligation sweep", "what needs action this week", "what renewals/notices are coming up", "which deadlines are approaching", "draft the Slack digest", "compliance check", or as the sweep step of obligation management. Surfaces overdue/imminent/upcoming/watch items only; silent when nothing is due. Draft-only — nothing posts.
---

# Sweep the register for what needs action

Compare every active obligation's diary date to today and surface only what needs
attention. The point is signal, not noise.

**Read first:** `${CLAUDE_PLUGIN_ROOT}/reference/output-contract.md` (packet shape).

## Run the sweep

The engine is deterministic — use it, don't eyeball dates:

```
python3 ${CLAUDE_PLUGIN_ROOT}/tools/sweep.py register/register.json --today <YYYY-MM-DD>
```

Flags: `--horizon-days` (default 60), `--imminent-days` (default 14),
`--client "<name>"` to scope to one client, `--format slack|text|json`. Default
`--today` is the system date; pass it explicitly when the lawyer asks about a
specific date.

Buckets: **OVERDUE** (past due) · **IMMINENT** (≤14d) · **UPCOMING** (≤horizon) ·
**WATCH** (active + conditional, no diary date yet). Beyond the horizon is silent.

## Output

1. **Chat:** the text render's count line
   (`X overdue · Y imminent · Z upcoming · W on watch`) then the bucketed detail.
   Only show buckets with items. If nothing needs action inside the horizon, say
   that in one line and stop.
2. **Slack digest:** posted to the team channel — see below.

## Post the due-dates digest to Slack (on demand)

Recipients are **one internal OLF team channel** (`config/notify.json` →
`slack.channel_name`). Posting the digest there is an authorised **internal**
reminder — this step may send. (Outbound to a client or counterparty is *not* this
step and stays draft-only.)

Steps:
1. Read `${CLAUDE_PLUGIN_ROOT}/config/notify.json` for `channel_name`,
   `channel_id`, `post_when_empty`, and the windows.
2. Build the message deterministically:
   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/tools/sweep.py register/register.json \
     --today <YYYY-MM-DD> --channel "#<channel_name>" --format post \
     --imminent-days <n> --horizon-days <n> [--quiet-when-empty]
   ```
   Pass `--quiet-when-empty` unless `post_when_empty` is true. If the command
   prints nothing, tell the lawyer nothing is due and **do not post**.
3. Resolve the channel id if `channel_id` is blank: call
   `slack_search_channels` with the channel name, confirm the match, and use its
   id (offer to save it back into `config/notify.json`).
4. **Post:** call `slack_send_message` with that `channel_id` and the `--format
   post` output as `message` (the connector takes standard markdown, which that
   format emits). Return the message link to the lawyer.
5. If the Slack connector is **not authorised** (`plugin:legal:slack`), do not
   attempt the call — say it needs connecting in claude.ai connector settings and
   hand over the post text so the lawyer can paste it. Never ask for tokens.

The lawyer's decision at setup was **auto-post** once a schedule exists; until
then this runs **on request** ("post the obligations digest"). Either way, the
sweep stays silent when nothing is due, so the channel only lights up on action.

## Turn it into a recurring post (when the lawyer asks)

The lawyer chose on-demand for now. When they want it automatic, create a
scheduled task (do not create it unprompted):

- Use `create_scheduled_task` with a weekly cron (e.g. `30 8 * * 1` — Mon 08:30
  local) and a **self-contained** prompt that: opens this plugin, runs the sweep
  with `--quiet-when-empty --format post`, and if there is output, posts it to the
  configured channel via `slack_send_message`; if the sweep is silent, does
  nothing. The prompt must name the register path, the channel, and the windows,
  because each run starts fresh with no memory of this session.
- Because `auto_post` is true and the target is the internal channel, the
  scheduled run posts without a further click. Quiet weeks produce no message.

## Applying updates

When the lawyer pastes back a `Register updates` block from the dashboard (Done /
Escalate / Snooze / Waive / new date), apply the deltas to the register rows,
re-run the guard, then re-run the sweep so the counts reflect the new state.
- **Done** → `status: completed`; a recurring row instead rolls forward to its
  next occurrence rather than closing.
- **Escalate** → keep `status: active`, prepend `[ESCALATED] ` to `notes` with the
  lawyer's note, and surface it at the top of the next chat summary. Escalation is
  an internal flag for senior/deal-team attention; it does not itself send anything
  outbound.
- **Snooze** → set a later `next_action_date` (ask for the new date if the note
  doesn't give one).
- **Waive** → `status: waived`.
