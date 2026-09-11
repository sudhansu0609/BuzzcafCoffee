---
title: SOP-08 Monthly close
version: 1.0
last_reviewed: 2026-09-07
owner: Sudhansu
summary: The two-hour monthly routine that keeps GST, books, Amazon and backups honest.
---

# SOP-08 Monthly close (first working week of each month)

| Step | What | Where | Output |
|---|---|---|---|
| 1 | Download Amazon reports: Payments → Date range report; Orders report; FBA inventory report | Seller Central | `vault/07-commerce/amazon/YYYY-MM/` |
| 2 | Export website orders and gateway settlements (Cashfree/Razorpay) | Site admin + gateway dashboard | same folder |
| 3 | Sales register: all B2C sales by state (for GSTR-1 table 7/B2CS). Instant coffee = **5% GST**, HSN 2101 12. Amazon collects TCS 0.5% — reconcile with GSTR-2B | Spreadsheet or CA | sales register |
| 4 | Purchase register: manufacturer invoices, Amazon fee invoices (18% GST, claim ITC), Shiprocket, packaging, gateway fees, software | vault + inbox | purchase register |
| 5 | Send both registers to the CA by the **7th**; GSTR-1 by the 11th, GSTR-3B by the 20th (Ops → Compliance → mark done with ARN) | CA / GST portal | ARNs in compliance log |
| 5a | Drop everything the CA sent this month (filed-return PDFs, challans, acknowledgements, ledgers) into `BuzzcafCoffee/inbox/` and run `python ops/assistant.py sort` (the watcher does it on its own if `run.py --assistant` is up). Clear Ops → Inbox → "needs your eye". `inbox/` must be empty and `python ops/intake.py --unregistered` must print nothing when this step ends | Terminal / Ops → Inbox | rows in Ops → Documents, Finance data, compliance ticks |
| 6 | Bank reconciliation: gateway payouts + Amazon disbursements + supplier payments vs bank statement | Bank | tick-off |
| 7 | Inventory reconciliation: Ops batch `qty_remaining` vs FBA inventory report vs own shelf count (SOP-12) | Ops | adjustments noted |
| 8 | Complaints review: anything open >7 days? any batch pattern? | Ops dashboard | actions |
| 9 | Compliance look-ahead: anything due in the next 60 days? (`python ops/cli.py due --days 60`) | Ops | tasks created |
| 10 | Documents look-ahead: anything expiring in 90 days? (`python ops/cli.py expiring`) | Ops | tasks created |
| 11 | **Backup**: `python ops/backup.py --verify`; copy `ops/backups/latest.zip` to cloud storage (Drive/B2) | Terminal | dated zip |
| 12 | Five-line note in Ops → Decisions or a task: sales, spend, stock cover in weeks, review count/rating, one thing to change | Ops | decision entry |

Quarterly extra: restore-test the backup on a different machine; review each SOP's "last reviewed" date; check the Amazon referral-fee policy still holds (the 0% window can close — the business must work at 7%).
