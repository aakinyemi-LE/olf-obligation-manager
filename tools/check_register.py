#!/usr/bin/env python3
"""check_register.py — regression guard for the obligation register.

Validates one or more register JSON files against the schema in
reference/register-schema.md. Errors fail the build (exit 1); soft
inconsistencies print as warnings. Mirrors the review-bot's
check_review_state.py so a release is one deterministic gate.

    python3 tools/check_register.py register/register.sample.json
"""
import json
import re
import sys
from datetime import date, datetime

ID_RE = re.compile(r"^OBL-\d{4}$")

ENUMS = {
    "category": {"renewal", "notice", "termination", "price_adjustment",
                 "reporting", "insurance", "data_privacy", "audit", "other"},
    "obligation_owner": {"client", "counterparty", "mutual"},
    "trigger_type": {"recurring", "one_time", "conditional"},
    "recurrence": {"annual", "quarterly", "monthly", "none"},
    "status": {"active", "snoozed", "completed", "waived"},
    "confidence": {"high", "medium", "low"},
    "invite_status": {"none", "pending_approval", "approved", "sent"},
}
REQUIRED = ["id", "client", "counterparty", "contract_title", "category",
            "summary", "action_required", "obligation_owner", "trigger_type",
            "recurrence", "status", "confidence"]
DATE_FIELDS = ["effective_date", "term_end_date", "next_action_date", "last_reviewed",
               "verified_at", "calendar_synced_at"]


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def check_file(path):
    errors, warnings = [], []
    try:
        data = json.load(open(path))
    except Exception as e:  # noqa: BLE001
        return [f"{path}: not valid JSON — {e}"], []

    obs = data.get("obligations")
    if not isinstance(obs, list):
        return [f"{path}: top-level 'obligations' must be a list"], []

    seen = set()
    for i, ob in enumerate(obs):
        tag = ob.get("id", f"index {i}")
        for field in REQUIRED:
            if not ob.get(field):
                errors.append(f"{path}: {tag}: missing required field '{field}'")
        oid = ob.get("id", "")
        if oid and not ID_RE.match(oid):
            errors.append(f"{path}: {tag}: id must match OBL-NNNN")
        if oid in seen:
            errors.append(f"{path}: duplicate id '{oid}'")
        seen.add(oid)
        for field, allowed in ENUMS.items():
            val = ob.get(field)
            if val is not None and val not in allowed:
                errors.append(f"{path}: {tag}: {field}='{val}' not in {sorted(allowed)}")
        parsed = {}
        for field in DATE_FIELDS:
            val = ob.get(field)
            if val in (None, ""):
                continue
            try:
                parsed[field] = parse_date(val)
            except ValueError:
                errors.append(f"{path}: {tag}: {field}='{val}' is not YYYY-MM-DD")
        # active rows must be diarised, else they can never surface
        if ob.get("status") == "active" and not ob.get("next_action_date"):
            if ob.get("trigger_type") != "conditional":
                errors.append(f"{path}: {tag}: active row has no next_action_date")
            else:
                warnings.append(f"{path}: {tag}: conditional row has no diary date "
                                "(will sit on the watch list until triggered)")
        # a verified row should carry its verbatim citation
        if ob.get("verified") and not ob.get("clause_text"):
            warnings.append(f"{path}: {tag}: verified but has no clause_text citation")
        # a client invite must never be marked sent without approval in the data
        if ob.get("invite_status") == "sent" and not ob.get("verified"):
            errors.append(f"{path}: {tag}: invite marked sent on an unverified row")
        # diary-date consistency (warning only — a lawyer may override)
        if {"term_end_date", "next_action_date"} <= parsed.keys() and ob.get("notice_window_days"):
            expected = parsed["term_end_date"].toordinal() - ob["notice_window_days"]
            if parsed["next_action_date"].toordinal() != expected:
                warnings.append(f"{path}: {tag}: next_action_date is not "
                                "term_end_date − notice_window_days (override?)")
    return errors, warnings


def main(argv):
    if not argv:
        print("usage: check_register.py <register.json> [more.json ...]")
        return 2
    all_errors, all_warnings = [], []
    for path in argv:
        e, w = check_file(path)
        all_errors += e
        all_warnings += w
    for w in all_warnings:
        print("WARN:", w)
    for e in all_errors:
        print("FAIL:", e)
    if all_errors:
        print(f"\n{len(all_errors)} error(s).")
        return 1
    print(f"OK — {len(argv)} file(s) valid"
          + (f", {len(all_warnings)} warning(s)" if all_warnings else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
