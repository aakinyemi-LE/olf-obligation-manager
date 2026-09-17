#!/usr/bin/env python3
"""report.py — a per-client obligations report (the QBR / client-facing deliverable).

Turns the register into a clean per-client summary the OLF lawyer can share with a
repeat client: what we are tracking for you, and what is coming up. Client-facing
output is VERIFIED-ONLY by default — never show a client an unverified row.

  python3 tools/report.py demo/register.json --client "Northwind Therapeutics, Inc." --today 2026-09-16
  python3 tools/report.py demo/register.json --all --today 2026-09-16 > report.md
"""
import argparse
import json
import sys
from datetime import date, datetime

CAT = {"renewal": "Renewal", "notice": "Notice / expiry", "termination": "Termination",
       "price_adjustment": "Price adjustment", "reporting": "Reporting", "insurance": "Insurance",
       "data_privacy": "Data / privacy", "audit": "Audit", "other": "Other"}


def d(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def client_report(rows, client, today, include_unverified):
    rows = [o for o in rows if o["client"] == client and o.get("status") == "active"]
    shown = [o for o in rows if include_unverified or o.get("verified")]
    held = [o for o in rows if not o.get("verified")]
    dated = sorted([o for o in shown if o.get("next_action_date")],
                   key=lambda o: o["next_action_date"])
    watch = [o for o in shown if not o.get("next_action_date")]

    out = [f"# Obligations report — {client}",
           f"_As of {today.isoformat()} · prepared by OLF · advisory, confirm each date against the contract_",
           "",
           f"We are actively tracking **{len(shown)} obligations** across your agreements. "
           f"{len(dated)} have a scheduled action date; {len(watch)} are event-driven.",
           "",
           "## Upcoming actions",
           "",
           "| Date | Days | Obligation | Contract | Clause | Who acts |",
           "|---|---|---|---|---|---|"]
    for o in dated:
        days = (d(o["next_action_date"]) - today).days
        when = f"overdue {-days}d" if days < 0 else f"{days}d"
        out.append(f"| {o['next_action_date']} | {when} | {CAT.get(o['category'],o['category'])} "
                   f"| {o.get('contract_title','')} | {o.get('clause_ref','')} | {o.get('obligation_owner','')} |")
    if not dated:
        out.append("| — | — | _no scheduled actions_ | | | |")
    if watch:
        out.append("")
        out.append("## Event-driven (no fixed date)")
        for o in watch:
            out.append(f"- **{CAT.get(o['category'],o['category'])}** — {o.get('summary','')} "
                       f"({o.get('contract_title','')} {o.get('clause_ref','')})")
    if held and not include_unverified:
        out.append("")
        out.append(f"> _Internal note: {len(held)} further obligation(s) for this client are pending "
                   "lawyer verification and are excluded from this client-facing report._")
    return "\n".join(out) + "\n"


def main(argv):
    ap = argparse.ArgumentParser(description="Per-client obligations report.")
    ap.add_argument("register")
    ap.add_argument("--client", default=None)
    ap.add_argument("--all", action="store_true", help="one section per client")
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--include-unverified", action="store_true",
                    help="INTERNAL use only — include rows not yet verified")
    args = ap.parse_args(argv)

    data = json.load(open(args.register))
    today = datetime.strptime(args.today, "%Y-%m-%d").date()
    rows = data.get("obligations", [])

    if args.all:
        clients = sorted({o["client"] for o in rows})
        print("\n\n---\n\n".join(
            client_report(rows, c, today, args.include_unverified) for c in clients))
    elif args.client:
        print(client_report(rows, args.client, today, args.include_unverified))
    else:
        print("specify --client \"<name>\" or --all")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
