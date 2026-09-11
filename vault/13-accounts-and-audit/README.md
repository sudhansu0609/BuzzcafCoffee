# 13-accounts-and-audit — everything the CA produces

This is the one home for anything a Chartered Accountant, Company Secretary or auditor sends about Buzzcaf Private Limited: financial statements, audit reports, income-tax returns, GST returns, TDS returns, ROC filings, ledgers, bank statements and their working papers.

Rule: **if the CA sent it, it lives here** — one folder per financial year, one Ops → Documents row per file. Not in email, not in WhatsApp, not on the desktop.

## Folders

| Folder | What goes in |
|---|---|
| `inbox/` | (legacy) — the real drop zone is now `BuzzcafCoffee/inbox/`, which auto-files into the folders below. Anything left here is filed by hand with `python ops/intake.py`. |
| `FY2022-23/` | Financial year 1 Apr 2022 – 31 Mar 2023 (first year; company incorporated 23 Mar 2022, so FY2021-22 had 8 days and is usually clubbed into this one — confirm with CA) |
| `FY2023-24/` | Dormant year |
| `FY2024-25/` | Dormant year |
| `FY2025-26/` | Dormant year |
| `FY2026-27/` | Restart year (current) |

Add `FY2027-28/` etc. as years come. Never overwrite a file; a revised version gets a new file with a later date, and the old one stays.

## Naming

`<kind>-fy<yyyy-yy>-<detail>-<YYYY-MM-DD>.pdf`, lowercase, hyphens. The date is the date on the document (signing / filing / statement end), not the date you saved it.

| Kind (prefix) | Example | Ops document type |
|---|---|---|
| `financial-statements` | `financial-statements-fy2024-25-signed-2025-09-20.pdf` | financial-statements |
| `audit-report` | `audit-report-fy2024-25-2025-09-20.pdf` | audit-report |
| `directors-report` | `directors-report-fy2024-25-2025-09-20.pdf` | board-minutes |
| `notice-agm` / `minutes-agm` | `minutes-agm-fy2024-25-2025-09-29.pdf` | board-minutes |
| `itr` | `itr-fy2024-25-ay2025-26-ack-2025-10-25.pdf` | itr |
| `form-26as` / `ais` | `form-26as-fy2024-25-2025-10-01.pdf` | form-26as |
| `aoc-4`, `mgt-7a`, `adt-1`, `dir-3-kyc` | `aoc-4-fy2024-25-srn-A12345678-2025-10-28.pdf` | roc-filing |
| `gstr-1`, `gstr-3b`, `gstr-9` | `gstr-3b-fy2026-27-2026-09-2026-10-18.pdf` (period, then filing date) | gst-return |
| `tds-24q`, `tds-26q` | `tds-26q-fy2026-27-q2-2026-10-30.pdf` | tds-return |
| `ledger` / `trial-balance` | `trial-balance-fy2024-25-2025-09-15.xlsx` | ledger |
| `bank-statement` | `bank-statement-fy2024-25-hdfc-50200069779258-2025-03-31.pdf` | bank-statement |
| `ca-report` (anything else: compliance status report, engagement letter, fee invoice, opinion) | `ca-report-fy2024-25-compliance-status-2026-09-10.pdf` | ca-report |

## Filing a report

**Easiest: drop it in `BuzzcafCoffee/inbox/` and run `python ops/assistant.py sort`** (or leave `python ops/run.py --assistant` running). The assistant reads the file, decides kind and year, names it as below, files it here, registers it in Ops, extracts the numbers and ticks the compliance calendar. See `docs/11-ASSISTANT.md`.

### By hand (two ways)

**A. Command line (preferred, one line per file):**
```bash
python ops/intake.py vault/13-accounts-and-audit/inbox/report.pdf --kind audit-report --fy 2024-25 --date 2025-09-20
python ops/intake.py "C:/Users/singh/Downloads/AOC-4 ack.pdf" --kind aoc-4 --fy 2024-25 --date 2025-10-28 --number A12345678
python ops/intake.py --unregistered        # anything in the vault that has no Ops row yet
```
It renames per the convention, moves the file into the right `FYxxxx-xx/` folder, and creates the Ops → Documents row (type, number, dates, tags `accounts, fy2024-25`).

**B. Ops UI:** Documents → New → upload; set folder to `13-accounts-and-audit/FY2024-25`; type as per the table; tags `accounts, fy2024-25`.

## What to ask the CA for, per financial year (the full set)

Tick these off in Ops → Compliance → mark done, with the SRN / ARN / acknowledgement number in the note.

1. Signed **financial statements** (balance sheet, P&L, notes) with UDIN.
2. **Auditor's report** (statutory audit is mandatory for every company, even dormant) and **ADT-1** appointment acknowledgement.
3. **Directors' report** and **AGM notice + minutes** (AGM by 30 Sep).
4. **AOC-4** and **MGT-7A** filing acknowledgements with SRN and challan.
5. **DIR-3 KYC** acknowledgements for both directors (by 30 Sep).
6. **ITR-6** acknowledgement (ITR-V) and the computation of income.
7. **Form 26AS / AIS** for the year.
8. **GSTR-1 and GSTR-3B** filed copies for every period, plus **GSTR-9** if applicable, and the GST portal's filing-status table.
9. **TDS returns** (24Q/26Q) if any TDS was deducted, else a note saying "nil, not applicable".
10. **Professional tax** (PTRC/PTEC) returns if applicable.
11. **Ledger / trial balance** export (Tally or Excel) so the books are not locked inside the CA's software.
12. A one-page **compliance status report**: what was filed, what is pending, penalties accrued, and what they need from us.

For the dormant years FY2023-24 and FY2024-25 the first thing to obtain is item 12 — it tells us which of items 1–10 exist at all. Ask also whether **Form MSC-1 (dormant status)** was ever filed; if not, all annual filings were still due.

Empty on 2026-09-09. Register every file added here in Buzzcaf Ops → Documents.
