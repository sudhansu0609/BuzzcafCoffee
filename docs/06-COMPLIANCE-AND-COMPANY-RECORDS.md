# Compliance and Company Records

All records live in **Buzzcaf Ops** (`ops/`, run locally) with the files in `vault/`. This document is the plain-English map of what exists, what is broken, and what must happen when.

## 1. What the company holds today (from `vault/`)
| Document | Number | Status (7 Sep 2026) | Action |
|---|---|---|---|
| Certificate of Incorporation | CIN U15400PN2022PTC209619, 23 Mar 2022 | Valid | None |
| MOA / AOA / SPICe+ / INC-9 / AGILE-PRO / INC-20A (commencement, filed Oct 2022) | – | Filed | Keep |
| Company PAN / TAN | PAN AAKCB6111C (from GSTIN); TAN on certificate | Valid | Note TAN in Ops |
| GST registration | 27AAKCB6111C1Z3, regular, from 19 May 2022; amended cert 6 Jul 2023 | Valid — **check filing status**: if no GSTR-3B has been filed for months, late fees accrue; nil returns are still mandatory | CA to check GST portal today |
| FSSAI State licence | 11522079000056, Repacker – General Manufacturing, cat 14.1.5 coffee, issued 24 Jun 2022 | **EXPIRED** (validity ended 23 Jun 2024 per restart plan; original showed 23 Jun 2023) | Renew/re-apply on FoSCoS; KOB → **Relabeller** + **Retailer**; premises address correct; ask if both KOBs fit one licence; expect late fee ₹100/day only applies to renewals within window — a two-year lapse likely means a **fresh application** |
| FSSAI annual return (Form D1) | Due 31 May each year for the previous FY | Probably not filed for FY23-24, 24-25 | File/regularise with the renewal |
| Shop & Establishment (Maharashtra) | 2231000316356174 (4 Apr 2022) | Valid (check validity period on certificate; Maharashtra intimation is typically 10 years) | Confirm in Ops |
| Trademark (Class 30) | PLACEHOLDER — certificate not in vault | Stated registered in restart plan | Locate certificate, add to vault; needed for Brand Registry |
| Udyam (MSME) | Not found | Missing | Register (free, instant) — halves TM fees, GS1 subsidy |
| ROC annual filings (AOC-4, MGT-7A), auditor (ADT-1), DIR-3 KYC for both directors | – | **Unknown — verify on MCA portal** | CA/CS to check; penalties compound daily |
| Income tax return (company) | – | Unknown | CA |
| Rent agreement (registered office) | In vault | Check expiry | Ops |
| Bank current account | PLACEHOLDER | Unknown | Confirm active, net-banking access |
| Amazon Seller Central | Active per plan | Check account health | Sudhansu |
| Razorpay account | Active (key from 2022) | **Secret in plaintext** | Rotate today |

## 2. The compliance calendar (seeded in Ops → Compliance)
| Obligation | Frequency | Due | Owner |
|---|---|---|---|
| GSTR-1 | Monthly (or quarterly under QRMP if turnover < ₹5 Cr — recommended) | 11th (13th QRMP) | CA |
| GSTR-3B | Monthly / quarterly | 20th (22nd QRMP) | CA |
| GSTR-9 annual | Yearly (only if turnover > ₹2 Cr) | 31 Dec | CA |
| TDS returns | Quarterly, if any TDS deducted | 31 Jul/Oct/Jan/May | CA |
| Professional tax (Maharashtra PTRC/PTEC) | Monthly/annual | Varies | CA |
| AGM | Yearly | By 30 Sep | Directors |
| AOC-4 (financials) | Yearly | 30 days after AGM | CA/CS |
| MGT-7A (annual return, small company) | Yearly | 60 days after AGM | CA/CS |
| DIR-3 KYC (each director) | Yearly | 30 Sep | Directors |
| ITR-6 company | Yearly | 31 Oct (audit case) | CA |
| FSSAI annual return Form D1 | Yearly | 31 May | Sudhansu |
| FSSAI licence renewal | Before expiry (window opens 180 days before) | per licence | Sudhansu |
| Product lab testing | Every 6 months per FSSAI for licensed FBOs (deemed manufacturer) | Ops → Tests | Sudhansu |
| Trademark renewal | Every 10 years | per certificate | – |
| Domain renewals | Yearly | registrar | Sudhansu |
| Shop Act renewal | Per certificate validity | – | – |
| Backups restore test | Monthly | 1st | Sudhansu |

## 3. Being a Relabeller (deemed manufacturer) — what it obliges
- Contract only with an FSSAI-licensed manufacturer whose licence covers category 14.1.5 (coffee); hold a copy; verify the number on FoSCoS yourself.
- Label carries both: "Manufactured by <maker, address, FSSAI no>" and "Marketed by Buzzcaf Private Limited, <licensed address>, FSSAI 11522079000056".
- Maintain traceability: batch number on every unit → Ops → Batches (supplier, COA, dates, where stock went).
- Recall plan: Ops → Complaints flags 3+ complaints on a batch; SOP-05 describes the recall trail (retention samples, FBA removal order, customer notice).
- Product testing: keep lab reports (nutrition per 100 g, microbial, moisture) in Ops → Tests.
- Annual return Form D1.
- Schedule 4 hygiene: an audit visit to the manufacturer with a checklist (SOP-01 has it).

## 4. Label / listing legal checklist (also enforced as SOP-04)
Name of food; ingredients descending by weight incl. flavouring type (natural / nature-identical / artificial); nutritional info per 100 g from a lab; green veg symbol; allergens; FSSAI logo + both licence numbers; net quantity; MRP incl. all taxes; consumer care phone + email; batch; manufacture date and best before DD/MM/YYYY; storage instructions; country of origin; 3 mm minimum for Schedule II text. Since Oct 2023 the **product page** (site and Amazon) must show manufacturer/marketer name + address, generic name, net quantity, MRP, consumer care and country of origin — the website renders this block on every product page.

## 5. Records that must exist from the first batch
Batch log, COA per batch, receiving checklist, retention samples (2 per batch, kept past best-before), complaints against batch, lab reports, supplier licence copies, purchase invoices, sales reports (Amazon + site), GST returns, board minutes/resolutions (at least the AGM), bank statements. All have a home in Ops.

## 6. Professional help to line up this week
- A **CA** for GST + ITR + ROC (₹1,500–3,000/month for this size). Ask them first to pull the GST filing status and MCA compliance status — this is the one unknown that could carry real penalties.
- Optional: a **food licensing consultant** for the FoSCoS re-application (₹2,000–5,000) if FoSCoS support cannot answer the two-KOB question.

## 7. Where the CA's output lives (single source of truth)

Everything a Chartered Accountant, Company Secretary or auditor produces goes to **`vault/13-accounts-and-audit/FY<yyyy-yy>/`** and gets a row in **Ops → Documents** (types: financial-statements, audit-report, itr, roc-filing, gst-return, tds-return, form-26as, ledger, bank-statement, board-minutes, ca-report). The folder README carries the naming rule and the full per-year checklist of what to ask the CA for.

How a report gets in (automatic, since 9 Sep 2026):
1. Drop the file into `BuzzcafCoffee/inbox/` (or let the mail reader pull it from the CA's e-mail).
2. `python ops/assistant.py sort` (or Ops → Inbox → Sort now, or the always-on watcher). It classifies, renames, files, registers, extracts the numbers and marks the matching obligation done with the date on the document.
3. Anything it was unsure about is on Ops → Inbox under "needs your eye": fix the type/year, set status valid.

Manual path (still works): `python ops/intake.py <file> --kind <kind> --fy <yyyy-yy> --date <date> [--number <SRN/ARN/UDIN>]`, then Ops → Compliance → mark done. See `docs/11-ASSISTANT.md`.

Financial years so far: FY2022-23 (first, incorporated 23 Mar 2022), FY2023-24, FY2024-25, FY2025-26 (dormant), FY2026-27 (restart). The first document to obtain for the dormant years is the CA's one-page compliance status report; it tells us which filings exist and which penalties have accrued.
