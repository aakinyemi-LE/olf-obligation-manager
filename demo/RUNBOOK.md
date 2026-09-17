# Demo runbook — OLF Post-Signature Obligation Manager

**~5 minutes. Everything below is pre-built and verified; the "wow" is the
folder → register → what's-due-now → Slack flow.**

Fixed demo date: **2026-09-16**. All numbers below assume that `--today`.

## Setup (once, before you present)

- Open a Cowork session with the `olf-obligation-manager` plugin.
- The demo data is ready:
  - `demo/contracts/` — **10 synthetic executed contracts** (3 clients).
  - `demo/register.json` — the matching **14-obligation** register (your safety net).
  - `assets/dashboard-template.html` — the console, pre-populated.
- If you want the live Slack post at the end, confirm `plugin:legal:slack` is
  connected in claude.ai connector settings. If it isn't, use the fallback (below)
  — do not try to authorise on stage.

## The script

**1. The pitch (10 sec).** "After we review and sign a contract, the obligations
don't stop — renewals, notice deadlines, insurance, reporting. This keeps them
diarised and tells the team what needs action, per client."

**2. Point it at the folder.** Say:
> "Track the obligations in the contracts in `demo/contracts/`."

It reads all 10 signed contracts and extracts the obligations into the register.
Chat returns a count line and a by-category list. *(If you'd rather not run live
extraction, skip straight to step 3 — the register is already built.)*

**3. Show the console.** Open `assets/dashboard-template.html`. Talk to:
- the four tiles — **2 overdue · 3 imminent · 6 upcoming · 2 on watch**;
- the **client filter** (All / Ashton / Northwind / Pembroke) — click a client,
  tiles and rows refilter;
- a couple of rows: the **overdue** Quill expiry and Meridian insurance COI, the
  **imminent** Pembroke termination window;
- the **Your call** control on any row — Done / Escalate / Snooze / Waive + a note.
  Mark one **Escalate**, add a note, hit **Copy updates to chat**, and paste it
  back to show the register updating.

**4. What needs action now.** Say:
> "Run the obligation sweep for today."

It buckets overdue / imminent / upcoming / watch in chat.

**5. Send it to the team.** Say:
> "Post the obligations digest to our Slack channel."

- **If Slack is connected:** it resolves the channel and posts the digest; share
  the message link. Note it stays **silent on weeks with nothing due**.
- **Fallback (Slack not connected):** it shows the exact post text and says the
  connector needs authorising. Read the digest off-screen — the story ("this is
  what lands in the channel, automatically, only when action is needed") is intact.

**6. Close.** "Today the register is a file and contracts come from a folder.
Same schema drops into Notion or Ontra Insight, and the folder becomes a DocuSign
/ Box / Egnyte feed — no change to the logic."

## Pre-flight checks (run these to be sure)

```bash
python3 tools/check_register.py demo/register.json
python3 tools/sweep.py demo/register.json --today 2026-09-16
python3 tools/sweep.py demo/register.json --today 2026-09-16 --format post --channel "#olf-obligations"
```

Expected: guard OK (2 watch-list warnings — the two conditional, no-date rows),
and sweep counts **2 overdue · 3 imminent · 6 upcoming · 2 on watch**, matching
the console tiles exactly.

## If something goes wrong

- **Live extraction is slow/odd:** the register is already correct — go to the
  console and sweep. Don't re-run extraction on stage.
- **Slack errors:** use the fallback text. Never authorise connectors live.
- **Dates look wrong:** you forgot `--today 2026-09-16`; the data is anchored to
  that date.
