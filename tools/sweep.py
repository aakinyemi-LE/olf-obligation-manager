#!/usr/bin/env python3
"""sweep.py — the compliance-sweep engine.

Reads the obligation register, compares each active obligation's diary date
(next_action_date) to 'today', and buckets what needs attention:

    OVERDUE   next_action_date is in the past
    IMMINENT  due within --imminent-days (default 14)
    UPCOMING  due within --horizon-days (default 60)
    WATCH     active + conditional with no diary date (nothing to do yet)

Beyond the horizon is intentionally silent — "surface only when action is
needed." Output is a DRAFT digest for a human to review; this script sends
nothing. --format slack emits Slack mrkdwn ready to paste into a draft.

    python3 tools/sweep.py register/register.sample.json --today 2026-09-16
    python3 tools/sweep.py register/register.sample.json --format slack
    python3 tools/sweep.py register/register.sample.json --format json
"""
import argparse
import json
import sys
from datetime import date, datetime

CATEGORY_LABEL = {
    "renewal": "Renewal", "notice": "Notice / expiry", "termination": "Termination",
    "price_adjustment": "Price adjustment", "reporting": "Reporting duty",
    "insurance": "Insurance", "data_privacy": "Data / privacy", "audit": "Audit",
    "other": "Other",
}


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def classify(ob, today, imminent_days, horizon_days):
    if ob.get("status") != "active":
        return None
    nad = ob.get("next_action_date")
    if not nad:
        return "WATCH" if ob.get("trigger_type") == "conditional" else None
    days = (parse_date(nad) - today).days
    if days < 0:
        return "OVERDUE"
    if days <= imminent_days:
        return "IMMINENT"
    if days <= horizon_days:
        return "UPCOMING"
    return None  # beyond horizon — stay quiet


def days_until(ob, today):
    return (parse_date(ob["next_action_date"]) - today).days


def run(register, today, imminent_days, horizon_days, client=None, require_verified=False):
    buckets = {"OVERDUE": [], "IMMINENT": [], "UPCOMING": [], "WATCH": [], "UNVERIFIED": []}
    for ob in register.get("obligations", []):
        if client and ob.get("client") != client:
            continue
        if require_verified and ob.get("status") == "active" and not ob.get("verified"):
            buckets["UNVERIFIED"].append(ob)
            continue
        b = classify(ob, today, imminent_days, horizon_days)
        if b:
            buckets[b].append(ob)
    for b in ("OVERDUE", "IMMINENT", "UPCOMING"):
        buckets[b].sort(key=lambda o: o["next_action_date"])
    return buckets


def line_text(ob, today):
    nad = ob.get("next_action_date")
    when = ""
    if nad:
        d = days_until(ob, today)
        when = f"{nad} ({'overdue ' + str(-d) + 'd' if d < 0 else 'in ' + str(d) + 'd'})"
    cat = CATEGORY_LABEL.get(ob.get("category"), ob.get("category"))
    return (f"  [{ob['id']}] {ob['client']} — {cat} — {ob.get('contract_title','')} "
            f"{ob.get('clause_ref','')}\n"
            f"      {when}\n"
            f"      {ob.get('action_required','')}")


def render_text(buckets, today, horizon_days):
    out = [f"OBLIGATION SWEEP — as of {today} (horizon {horizon_days}d) — DRAFT, nothing sent", ""]
    counts = {b: len(v) for b, v in buckets.items()}
    unv = f" · {counts['UNVERIFIED']} unverified (held)" if counts.get("UNVERIFIED") else ""
    out.append(f"{counts['OVERDUE']} overdue · {counts['IMMINENT']} imminent · "
               f"{counts['UPCOMING']} upcoming · {counts['WATCH']} on watch{unv}")
    out.append("")
    titles = {"OVERDUE": "OVERDUE — act now", "IMMINENT": "IMMINENT",
              "UPCOMING": "UPCOMING", "WATCH": "WATCH (conditional, no date yet)",
              "UNVERIFIED": "NEEDS VERIFICATION (confirm before diarising / alerting)"}
    any_action = False
    for b in ("OVERDUE", "IMMINENT", "UPCOMING", "WATCH", "UNVERIFIED"):
        if not buckets[b]:
            continue
        if b in ("OVERDUE", "IMMINENT", "UPCOMING"):
            any_action = True
        out.append(f"── {titles[b]} ──")
        for ob in buckets[b]:
            out.append(line_text(ob, today))
        out.append("")
    if not any_action:
        out.append("No action needed inside the horizon. (Watch items only.)")
    return "\n".join(out).rstrip() + "\n"


def render_slack(buckets, today, horizon_days):
    emoji = {"OVERDUE": ":red_circle:", "IMMINENT": ":large_orange_circle:",
             "UPCOMING": ":large_yellow_circle:", "WATCH": ":white_circle:"}
    titles = {"OVERDUE": "Overdue — act now", "IMMINENT": "Imminent",
              "UPCOMING": "Upcoming", "WATCH": "Watch (conditional)"}
    counts = {b: len(v) for b, v in buckets.items()}
    lines = [f"*Obligation sweep — {today}*  _(draft; nothing sent)_",
             f"{counts['OVERDUE']} overdue · {counts['IMMINENT']} imminent · "
             f"{counts['UPCOMING']} upcoming · {counts['WATCH']} on watch"]
    for b in ("OVERDUE", "IMMINENT", "UPCOMING", "WATCH"):
        if not buckets[b]:
            continue
        lines.append(f"\n{emoji[b]} *{titles[b]}*")
        for ob in buckets[b]:
            nad = ob.get("next_action_date")
            when = ""
            if nad:
                d = days_until(ob, today)
                when = f" — *{nad}* ({'overdue ' + str(-d) + 'd' if d < 0 else 'in ' + str(d) + 'd'})"
            cat = CATEGORY_LABEL.get(ob.get("category"), ob.get("category"))
            lines.append(f"• [{ob['id']}] *{ob['client']}* · {cat} · "
                         f"{ob.get('contract_title','')} {ob.get('clause_ref','')}{when}")
            lines.append(f"    {ob.get('action_required','')}")
    if not any(buckets[b] for b in ("OVERDUE", "IMMINENT", "UPCOMING")):
        lines.append("\n:white_check_mark: No action needed inside the horizon.")
    return "\n".join(lines)


def render_post(buckets, today, horizon_days, channel_label=None):
    """Standard-markdown digest shaped for the Slack connector
    (mcp slack_send_message takes **bold**, not Slack's native *bold*)."""
    emoji = {"OVERDUE": "\U0001F534", "IMMINENT": "\U0001F7E0",
             "UPCOMING": "\U0001F7E1", "WATCH": "⚪"}
    titles = {"OVERDUE": "Overdue — act now", "IMMINENT": "Imminent",
              "UPCOMING": "Upcoming", "WATCH": "Watch (conditional)"}
    counts = {b: len(v) for b, v in buckets.items()}
    where = f" — posted to {channel_label}" if channel_label else ""
    lines = [f"**Obligation due-dates — {today}**{where}",
             f"{counts['OVERDUE']} overdue · {counts['IMMINENT']} imminent · "
             f"{counts['UPCOMING']} upcoming · {counts['WATCH']} on watch"]
    for b in ("OVERDUE", "IMMINENT", "UPCOMING", "WATCH"):
        if not buckets[b]:
            continue
        lines.append(f"\n{emoji[b]} **{titles[b]}**")
        for ob in buckets[b]:
            nad = ob.get("next_action_date")
            when = ""
            if nad:
                d = days_until(ob, today)
                when = f" — **{nad}** ({'overdue ' + str(-d) + 'd' if d < 0 else 'in ' + str(d) + 'd'})"
            cat = CATEGORY_LABEL.get(ob.get("category"), ob.get("category"))
            lines.append(f"- **[{ob['id']}] {ob['client']}** · {cat} · "
                         f"{ob.get('contract_title','')} {ob.get('clause_ref','')}{when}")
            lines.append(f"    {ob.get('action_required','')} _(owner: {ob.get('obligation_owner','?')})_")
    if not any(buckets[b] for b in ("OVERDUE", "IMMINENT", "UPCOMING")):
        lines.append("\n✅ No obligations need action inside the horizon.")
    lines.append("\n_Automated internal reminder from the OLF obligation register. "
                 "Confirm each diary date against the contract before relying on it._")
    return "\n".join(lines)


def main(argv):
    ap = argparse.ArgumentParser(description="Obligation compliance sweep.")
    ap.add_argument("register")
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--imminent-days", type=int, default=14)
    ap.add_argument("--horizon-days", type=int, default=60)
    ap.add_argument("--client", default=None, help="limit to one client")
    ap.add_argument("--channel", default=None, help="channel label for the post header")
    ap.add_argument("--quiet-when-empty", action="store_true",
                    help="print nothing (exit 0) when no OVERDUE/IMMINENT/UPCOMING items")
    ap.add_argument("--require-verified", action="store_true",
                    help="hold unverified rows out of the action buckets and list them separately")
    ap.add_argument("--format", choices=["text", "slack", "post", "json"], default="text")
    args = ap.parse_args(argv)

    register = json.load(open(args.register))
    today = parse_date(args.today)
    buckets = run(register, today, args.imminent_days, args.horizon_days,
                  args.client, args.require_verified)

    has_action = any(buckets[b] for b in ("OVERDUE", "IMMINENT", "UPCOMING"))
    if args.quiet_when_empty and not has_action:
        return 0  # silent — nothing to post

    if args.format == "json":
        payload = {"as_of": args.today, "horizon_days": args.horizon_days,
                   "has_action": has_action,
                   "counts": {b: len(v) for b, v in buckets.items()},
                   "buckets": buckets}
        print(json.dumps(payload, indent=2))
    elif args.format == "slack":
        print(render_slack(buckets, today, args.horizon_days))
    elif args.format == "post":
        print(render_post(buckets, today, args.horizon_days, args.channel))
    else:
        print(render_text(buckets, today, args.horizon_days))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
