#!/usr/bin/env python3
"""rollforward.py — advance a recurring obligation to its next occurrence.

When a recurring obligation is marked done, it should not close — it should roll
forward to the next due date so nothing falls through. This computes (and, with
--write, applies) that advance.

  annual    -> +1 year      quarterly -> +3 months     monthly -> +1 month

By default it is a DRY RUN and prints what would change; pass --write to apply it
to the register file (then re-run tools/check_register.py).

  python3 tools/rollforward.py demo/register.json --id OBL-0006 --today 2026-10-16
  python3 tools/rollforward.py demo/register.json --id OBL-0006 --write
"""
import argparse
import json
import sys
from datetime import date, datetime

STEP_MONTHS = {"annual": 12, "quarterly": 3, "monthly": 1}


def add_months(d, months):
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    # clamp day to end of target month
    import calendar
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def next_occurrence(current, recurrence):
    step = STEP_MONTHS.get(recurrence)
    if not step:
        return None
    return add_months(current, step)


def roll(ob, today):
    """Return (new_next_action_date, message) or (None, reason)."""
    if ob.get("recurrence") not in STEP_MONTHS:
        return None, f"{ob['id']}: not recurring ({ob.get('recurrence')}) — mark completed instead"
    cur = ob.get("next_action_date")
    if not cur:
        return None, f"{ob['id']}: no current next_action_date to advance"
    d = datetime.strptime(cur, "%Y-%m-%d").date()
    nxt = next_occurrence(d, ob["recurrence"])
    # if the recurrence lands on/before today, keep stepping until it is in the future
    while nxt and nxt <= today:
        nxt = next_occurrence(nxt, ob["recurrence"])
    return nxt.isoformat(), f"{ob['id']}: {cur} -> {nxt.isoformat()} ({ob['recurrence']})"


def main(argv):
    ap = argparse.ArgumentParser(description="Roll a recurring obligation to its next occurrence.")
    ap.add_argument("register")
    ap.add_argument("--id", required=True, help="obligation id to roll forward")
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--write", action="store_true", help="apply the change to the register file")
    args = ap.parse_args(argv)

    data = json.load(open(args.register))
    today = datetime.strptime(args.today, "%Y-%m-%d").date()
    ob = next((o for o in data["obligations"] if o["id"] == args.id), None)
    if not ob:
        print(f"no such obligation: {args.id}")
        return 1

    new_date, msg = roll(ob, today)
    print(msg)
    if new_date is None:
        return 1
    if args.write:
        ob["next_action_date"] = new_date
        ob["status"] = "active"
        ob["last_reviewed"] = args.today
        ob["calendar_synced_at"] = None  # force a re-sync of the moved event
        json.dump(data, open(args.register, "w"), indent=2, ensure_ascii=False)
        open(args.register, "a").write("\n")
        print(f"written to {args.register} (re-run the guard and re-sync the calendar)")
    else:
        print("dry run — pass --write to apply")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
