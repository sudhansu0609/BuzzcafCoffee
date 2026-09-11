---
title: SOP-09 Document control and renewals
version: 1.0
last_reviewed: 2026-09-07
owner: Sudhansu
summary: One place for every paper, a naming rule, and a renewal lead time so nothing expires unnoticed again.
---

# SOP-09 Document control and renewals

The FSSAI licence expired on 23 June 2024 and nobody noticed for two years. This SOP exists so that cannot happen to any document again.

## 1. One home: the vault

`BuzzcafCoffee/vault/` is the single filing cabinet. Folder = category (`01-company` … `11-agreements`, `12-uploads` for things dropped in from the Ops UI, `13-accounts-and-audit/FY<yyyy-yy>/` for everything the CA, CS or auditor produces). Nothing important lives only in email, WhatsApp or a phone gallery.

Fastest way to file anything: drop it in `BuzzcafCoffee/inbox/` and run `python ops/assistant.py sort` — the assistant classifies, renames, files and registers it (docs/11-ASSISTANT.md). By hand: `python ops/intake.py <file> --kind <kind> --fy <yyyy-yy> --date <YYYY-MM-DD> [--number <SRN/ARN>]`. It renames per the rule below, moves the file into the right folder and creates the Ops → Documents row in one step. `python ops/intake.py --unregistered` lists any vault file that still has no row.

Naming: `<what>-<number-or-party>-<YYYY-MM-DD>.pdf`, lowercase, hyphens. Examples: `fssai-state-licence-11522079000056.pdf`, `coa-BZH2609-2026-11-03.pdf`, `dayum-quote-2026-09-20.pdf`.

## 2. Register everything with a date

Every file that has a number, a validity, or a legal weight gets a row in Ops → Documents with: type, number, authority, issue date, **expiry date** (blank only if it truly never expires), renewal lead days, status, vault path.

Default lead times:

| Document | Lead | Why |
|---|---|---|
| FSSAI licence | 180 days | Renewal window opens 180 days before expiry; late = penalty and possible fresh application |
| Rent / leave-and-licence | 60 days | Registered office proof for ROC, bank, FSSAI |
| Domain | 60 days | Losing the domain loses email and the shop |
| Trademark | 365 days | 10-year term; renewal with surcharge window |
| Supplier FSSAI licence | 90 days | We may not contract with an unlicensed manufacturer |
| Lab reports (nutrition) | 60 days | Retest on recipe change or annually |
| Insurance (if taken) | 45 days | |

## 3. The weekly glance

Open the Ops dashboard once a week (or run `python ops/cli.py summary`). Anything in **expired** or **≤30 days** becomes a Task with an owner and a due date that day.

## 4. Restricted documents

`05-directors-kyc/` holds Aadhaar/PAN of the directors. They are shared only when a regulator, bank or registrar requires them, and never uploaded to a third-party tool without need. Masked Aadhaar (VID / last four digits) wherever accepted.

## 5. Versions

When a document is renewed, keep the old file, add the new one, and update the registry row's issue/expiry dates and path. The old row's notes get "superseded by …". Never overwrite.

## 6. Who

Sudhansu owns the registry. Himansu is the second reader for anything legal before it is signed. The CA receives the compliance calendar export each quarter.
