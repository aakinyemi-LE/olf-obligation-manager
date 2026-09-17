#!/usr/bin/env python3
"""eval_extraction.py — score a fresh extraction against a ground-truth answer key.

This is the accuracy gate for a legal tool: a MISSED obligation (in the key, not
in the extraction) is the dangerous error, so recall is reported prominently, and
--min-recall / --min-precision can fail a build.

Obligations are matched across the two files on (contract_ref, clause_ref) — the
stable identity of a provision, independent of OBL ids. Among matched pairs it
scores category, owner, and diary-date agreement.

  python3 tools/eval_extraction.py --key demo/answer-key.json --candidate out.json
  python3 tools/eval_extraction.py --key demo/answer-key.json --candidate out.json --min-recall 0.9
"""
import argparse
import json
import sys


def load(path):
    return json.load(open(path)).get("obligations", [])


def key_of(o):
    return (str(o.get("contract_ref") or o.get("contract_title") or "").strip().lower(),
            str(o.get("clause_ref") or "").strip().lower())


def index(rows):
    idx = {}
    for o in rows:
        idx.setdefault(key_of(o), []).append(o)
    return idx


def main(argv):
    ap = argparse.ArgumentParser(description="Score an extraction against an answer key.")
    ap.add_argument("--key", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--min-recall", type=float, default=None)
    ap.add_argument("--min-precision", type=float, default=None)
    args = ap.parse_args(argv)

    key = load(args.key)
    cand = load(args.candidate)
    kidx, cidx = index(key), index(cand)

    matched_keys = [k for k in kidx if k in cidx]
    missed = [k for k in kidx if k not in cidx]        # in key, not extracted — DANGER
    extra = [k for k in cidx if k not in kidx]          # extracted, not in key — noise

    n_key = len(key) or 1
    n_cand = len(cand) or 1
    recall = len(matched_keys) / n_key
    precision = len(matched_keys) / n_cand

    cat_ok = own_ok = date_ok = 0
    field_misses = []
    for k in matched_keys:
        ko, co = kidx[k][0], cidx[k][0]
        c = ko.get("category") == co.get("category")
        o = ko.get("obligation_owner") == co.get("obligation_owner")
        d = ko.get("next_action_date") == co.get("next_action_date")
        cat_ok += c; own_ok += o; date_ok += d
        if not (c and o and d):
            field_misses.append((k, {"category": (ko.get("category"), co.get("category")) if not c else None,
                                     "owner": (ko.get("obligation_owner"), co.get("obligation_owner")) if not o else None,
                                     "date": (ko.get("next_action_date"), co.get("next_action_date")) if not d else None}))
    m = len(matched_keys) or 1

    print("EXTRACTION EVAL")
    print(f"  key={len(key)}  candidate={len(cand)}  matched={len(matched_keys)}")
    print(f"  recall     {recall:5.1%}   (missed {len(missed)} — obligations the extractor did not find)")
    print(f"  precision  {precision:5.1%}   (extra {len(extra)} — rows with no match in the key)")
    print(f"  among matched:  category {cat_ok/m:5.1%}   owner {own_ok/m:5.1%}   diary-date {date_ok/m:5.1%}")
    if missed:
        print("  MISSED (in key, not extracted):")
        for k in missed:
            print(f"    - {k[0]} {k[1]}")
    if extra:
        print("  EXTRA (extracted, not in key):")
        for k in extra:
            print(f"    - {k[0]} {k[1]}")
    if field_misses:
        print("  FIELD MISMATCHES (matched rows with wrong fields):")
        for k, diff in field_misses:
            parts = [f"{f} {v[0]}!={v[1]}" for f, v in diff.items() if v]
            print(f"    - {k[0]} {k[1]}: " + "; ".join(parts))

    fail = False
    if args.min_recall is not None and recall < args.min_recall:
        print(f"FAIL: recall {recall:.1%} < required {args.min_recall:.0%}"); fail = True
    if args.min_precision is not None and precision < args.min_precision:
        print(f"FAIL: precision {precision:.1%} < required {args.min_precision:.0%}"); fail = True
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
