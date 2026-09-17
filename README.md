# OLF Post-Signature Obligation & Renewal Manager

A Cowork plugin for an OLF lawyer to manage **executed** contracts: it extracts
the living obligations — notice periods, renewals, termination rights, price
adjustments, reporting duties, insurance requirements, data obligations, audit
rights — into a durable register, computes each provision's diary date, and runs
a compliance sweep that surfaces only what needs action. It is the downstream
complement to `olf-elcc-review-bot` (which does the pre-signature first pass).

**Obligation-first.** The one thing that sends is the **internal** due-dates
digest to the OLF team's own Slack channel (on request, or auto once a schedule is
enabled). Everything outbound to a client or counterparty stays draft-only and
needs per-message approval.

## What it does

1. **Extract** (`skills/extract-obligations`) — reads a signed contract and writes
   diarised rows to the register (`reference/register-schema.md`), one provision
   per row, across nine categories (`reference/obligation-taxonomy.md`).
2. **Sweep** (`skills/obligation-sweep`) — `tools/sweep.py` compares each active
   obligation's diary date to today and buckets: **overdue / imminent / upcoming /
   watch**. Silent when nothing is due.
3. **Surface** — an HTML dashboard console (`assets/dashboard-template.html`) for
   triage, and a due-dates digest **posted to the internal OLF team Slack channel**
   (`config/notify.json`) via the Slack connector. The console's "Your call" marks
   round-trip back into the register.

`skills/manage` orchestrates the three.

## The register (prototype store)

The register is a JSON file for now — `register/register.sample.json` is the seed
and shape. The schema is store-agnostic on purpose: the same fields become columns
in Notion or Ontra Insight later without touching the skills.

## Try it

```bash
python3 tools/check_register.py register/register.sample.json                       # validate
python3 tools/sweep.py register/register.sample.json --today 2026-09-16              # text sweep
python3 tools/sweep.py register/register.sample.json --format post --channel "#olf-obligations"  # Slack post text
open assets/dashboard-template.html                                                 # console
```

To post: the `obligation-sweep` skill runs the sweep with `--format post
--quiet-when-empty`, resolves the channel via `slack_search_channels`, and calls
`slack_send_message`. The Slack connector must be authorised first.

## Guardrails

- **Internal digest may post; outbound stays draft-only.** Posting the due-dates
  digest to the internal OLF channel is authorised; emails/invites/messages to
  clients or counterparties are drafted for per-message approval. Slack must be
  authorised before anything posts.
- **Silent when quiet.** `--quiet-when-empty` means no post on weeks with nothing
  due, so the channel is signal, not noise.
- **Traceable.** Every row keeps its clause reference and source document;
  ungrounded dates are `confidence: low`, never guessed.
- **Advisory.** The lawyer confirms every diary date before relying on it.

## Release

`tools/release.sh <version>` bumps both manifests and runs the guard over
`tests/fixtures/*.register.json`. GitHub is the source of truth; the Cowork
marketplace copy is derived.
