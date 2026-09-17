#!/usr/bin/env python3
"""calendar_plan.py — compute an idempotent calendar-sync PLAN from the register.

This does NOT touch any calendar. It reads the register and emits a deterministic
plan of actions; the `calendar-sync` skill executes that plan through the Google
Calendar connector (create_event / update_event / delete_event). Keeping the plan
in Python makes the sync testable and predictable, and keeps the side-effecting
writes in the skill where approval and connector-auth live.

Rules (the trust gate matters here):
  * Only VERIFIED, active rows with a diary date get an INTERNAL event.
  * calendar_event_id present  -> UPDATE that event (idempotent; never duplicate).
  * calendar_event_id absent    -> CREATE a new event.
  * status completed/waived + event id present -> DELETE the stale event.
  * Client invites are separate and DRAFT-ONLY: emitted as draft_client_invite
    with send=false unless invite_status == "approved". Never send from here.

    python3 tools/calendar_plan.py demo/register.json --today 2026-09-16
    python3 tools/calendar_plan.py demo/register.json --format json
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta

CATEGORY_LABEL = {
    "renewal": "Renewal", "notice": "Notice / expiry", "termination": "Termination",
    "price_adjustment": "Price adjustment", "reporting": "Reporting duty",
    "insurance": "Insurance", "data_privacy": "Data / privacy", "audit": "Audit",
    "other": "Other",
}


def short_client(c):
    for suf in (", Inc.", " Inc.", ", L.P.", " L.P.", " LLC", " LLP", " Ltd."):
        if c.endswith(suf):
            return c[: -len(suf)]
    return c


def event_title(o):
    return (f"{short_client(o['client'])} · {CATEGORY_LABEL.get(o['category'], o['category'])}"
            f" · {o.get('contract_title','')} ({o['id']})")


def event_description(o):
    lines = [o.get("action_required", "")]
    if o.get("clause_ref") or o.get("clause_text"):
        lines.append("")
        lines.append(f"Clause {o.get('clause_ref','')}: {o.get('clause_text','') or '(citation not captured)'}")
    lines.append("")
    lines.append(f"Owner: {o.get('obligation_owner','?')} · Counterparty: {o.get('counterparty','')}")
    if o.get("source_document"):
        lines.append(f"Source: {o['source_document']}")
    lines.append(f"Tracked by the OLF obligation register ({o['id']}). "
                 "Confirm against the contract before relying on this date.")
    return "\n".join(lines)


def build_plan(register, today, cfg):
    cal_id = cfg.get("internal_calendar_id") or cfg.get("internal_calendar_name") or "OLF Obligations"
    reminders = cfg.get("reminder_days_before", [7, 1])
    allow_invites = cfg.get("allow_client_invites", True)
    plan = {"calendar": cal_id, "reminder_days_before": reminders,
            "internal": [], "client_invites": [], "skipped": []}

    for o in register.get("obligations", []):
        active = o.get("status") == "active"
        nad = o.get("next_action_date")
        has_evt = bool(o.get("calendar_event_id"))

        # tidy up stale events for closed rows
        if not active and has_evt:
            plan["internal"].append({"action": "delete", "id": o["id"],
                                     "event_id": o["calendar_event_id"]})
            continue

        if not active:
            continue
        if not o.get("verified"):
            plan["skipped"].append({"id": o["id"], "reason": "unverified"})
            continue
        if not nad:
            plan["skipped"].append({"id": o["id"], "reason": "no diary date (watch)"})
            continue

        ev = {
            "action": "update" if has_evt else "create",
            "id": o["id"],
            "event_id": o.get("calendar_event_id"),
            "calendar": cal_id,
            "title": event_title(o),
            "start_date": nad,          # all-day
            "end_date": nad,
            "all_day": True,
            "description": event_description(o),
            "attendees": [o["responsible_lawyer_email"]] if o.get("responsible_lawyer_email") else [],
            "reminders_minutes": [d * 24 * 60 for d in reminders],
        }
        plan["internal"].append(ev)

        # client invite — DRAFT ONLY
        if o.get("invite_to_client") and allow_invites:
            approved = o.get("invite_status") == "approved"
            plan["client_invites"].append({
                "action": "draft_client_invite",
                "id": o["id"],
                "send": approved,               # never true unless explicitly approved in the data
                "invite_status": o.get("invite_status", "none"),
                "to": o.get("client_contact_email", ""),
                "calendar": cal_id,
                "title": event_title(o) + " — client reminder",
                "start_date": nad,
                "all_day": True,
                "description": ("Reminder of an upcoming deadline under your agreement.\n\n"
                                + o.get("action_required", "")),
            })
    return plan


def render_text(plan):
    creates = [e for e in plan["internal"] if e["action"] == "create"]
    updates = [e for e in plan["internal"] if e["action"] == "update"]
    deletes = [e for e in plan["internal"] if e["action"] == "delete"]
    out = ["CALENDAR SYNC PLAN — internal calendar: " + str(plan["calendar"]),
           "This plan is executed by the calendar-sync skill; nothing is written here.",
           "",
           f"{len(creates)} create · {len(updates)} update · {len(deletes)} delete "
           f"· {len(plan['client_invites'])} client-invite draft(s) · {len(plan['skipped'])} skipped",
           ""]
    if creates:
        out.append("── CREATE (new internal events) ──")
        for e in creates:
            out.append(f"  [{e['id']}] {e['start_date']}  {e['title']}")
        out.append("")
    if updates:
        out.append("── UPDATE (existing events) ──")
        for e in updates:
            out.append(f"  [{e['id']}] {e['start_date']}  {e['title']}")
        out.append("")
    if deletes:
        out.append("── DELETE (closed rows) ──")
        for e in deletes:
            out.append(f"  [{e['id']}] event {e['event_id']}")
        out.append("")
    if plan["client_invites"]:
        out.append("── CLIENT INVITES (DRAFT — approval required, none sent) ──")
        for e in plan["client_invites"]:
            flag = "APPROVED→ready" if e["send"] else "needs approval"
            out.append(f"  [{e['id']}] to {e['to'] or '(no contact)'} — {flag}")
        out.append("")
    if plan["skipped"]:
        out.append("── SKIPPED (not eligible for calendar) ──")
        for s in plan["skipped"]:
            out.append(f"  [{s['id']}] {s['reason']}")
    return "\n".join(out).rstrip() + "\n"


def main(argv):
    ap = argparse.ArgumentParser(description="Compute an idempotent calendar sync plan (no writes).")
    ap.add_argument("register")
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--config", default=None, help="path to notify.json (for the calendar block)")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args(argv)

    register = json.load(open(args.register))
    cfg = {}
    if args.config:
        cfg = json.load(open(args.config)).get("calendar", {})
    today = datetime.strptime(args.today, "%Y-%m-%d").date()
    plan = build_plan(register, today, cfg)

    if args.format == "json":
        print(json.dumps(plan, indent=2, ensure_ascii=False))
    else:
        print(render_text(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
