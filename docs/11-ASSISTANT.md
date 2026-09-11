# The Assistant — drop folder, auto-filing, finance dashboard, mail reader, morning brief

Built 9 Sep 2026. Lives inside Buzzcaf Ops (`ops/`). Nothing leaves the machine unless you configure a mailbox or an Anthropic key.

## 1. What it does, in one picture

```
 you / your CA / the mailbox
          │  any file (PDF, Excel, CSV, Word, photo)
          ▼
   BuzzcafCoffee/inbox/          ← the only place you ever need to drop things
          │  python ops/assistant.py sort   (or Ops → Inbox → "Sort now", or the watcher)
          ▼
   read text → classify (kind, FY, month, date, SRN/ARN/UDIN) → rename → move
          │
          ├── vault/13-accounts-and-audit/FY2024-25/audit-report-fy2024-25-2025-09-20.pdf
          ├── Ops → Documents (type, number, dates, SHA-256, "why" in notes)
          ├── Ops → Finance data (revenue, PAT, GST taxable value, ITC, bank balances …)
          ├── Ops → Compliance: AOC-4 / GSTR-3B / ITR / DIR-3 KYC … marked done with the date on the document
          └── Ops → Finance dashboard: filing matrix per FY, KPIs, GST by month, bank
```

Unsure files (confidence < 0.6, or a financial document whose year it cannot find) go to `vault/12-uploads/needs-review/` as a *pending* Document and are listed on the Inbox page. Duplicates (same SHA-256 as an existing document) move to `inbox/duplicates/`. Nothing is deleted or overwritten, ever.

## 2. Run it

| How | Command | When |
|---|---|---|
| One pass | `python ops/assistant.py sort` | you just dropped files |
| Preview | `python ops/assistant.py sort --dry-run` | you want to see what it would do |
| Mail + files + brief | `python ops/assistant.py run` | any time |
| Always on | `python ops/run.py --assistant` | the Ops web app with the watcher inside (every 10 min; brief e-mailed at `BRIEF_HOUR`) |
| Only the watcher | `python ops/assistant.py watch --every 600` | headless |
| In the browser | Ops → Inbox → "Sort now" / "Mail + sort"; Ops → Morning brief → "E-mail it to me" | |

`--no-llm` forces the rule-based path; `--json` gives machine output. Every action is also on the JSON API: `POST /api/inbox/sort`, `POST /api/assistant/cycle`, `GET /api/finance`, `GET /api/brief` — BuzzcafAI / Dexter can call them.

## 3. Connecting your mailbox ("read my mail and update me")

1. Copy `ops/.env.example` to `ops/.env` (gitignored).
2. Gmail / Google Workspace: Google Account → Security → 2-Step Verification → **App passwords** → create one for "Buzzcaf Ops"; put it in `MAIL_PASSWORD`. Zoho/Outlook: their IMAP host + app password.
3. `MAIL_USER=sudhansu@buzzcaf.com` (or whichever box receives CA / GST / MCA / Amazon mail). Optional: `MAIL_CA_ADDRESSES=` your CA's address so their mail is filed as *ca-accounts*; `MAIL_WATCH_SENDERS=` to restrict which senders are read at all.
4. `python ops/assistant.py test-mail` → should print `ok: imap.gmail.com as … has N messages`.
5. `python ops/assistant.py mail` reads the last 14 days (`MAIL_SINCE_DAYS`), never marks anything read, never deletes.

What happens to each mail:
- It is stored in **Ops → Mail** with category (gst, mca-roc, income-tax, fssai, bank, amazon, supplier, customer, ca-accounts, …), importance (urgent / high / normal / low / ignore), a summary, the action needed, any deadline and amount it mentions.
- PDF/Excel/CSV/Word/image attachments are saved to `inbox/` (prefixed with the mail date) and sorted like anything else; the mail row links to the resulting documents.
- Urgent/high mails with an action create a **Task** (priority, due date, area) linked back to the mail.
- Newsletters and promotions are marked *ignore* and never reach the brief.
- The **morning brief** (Ops → Morning brief, `/api/brief`, and e-mailed to `MAIL_BRIEF_TO` once a day at `BRIEF_HOUR`) lists: overdue filings, expiring documents, mail that needs you, what was filed overnight, what needs your eye, tasks due.

## 4. Understanding: rules first, Claude when available

Everything runs on rules with no network. If `ANTHROPIC_API_KEY` is set (in `ops/.env` or the environment), the assistant additionally asks Claude (`claude-opus-5`, structured JSON output, server-side refusal fallbacks enabled) to:
- classify a document the rules were unsure about (confidence < 0.75),
- pull the numbers out of a financial statement / ITR / GSTR-3B / bank statement when the rules found fewer than three,
- read each non-noise mail and write the summary / action / deadline,
- write the morning brief in prose.

Set `BUZZCAF_ASSISTANT_LLM=0` to switch that off even with a key. Facts extracted by Claude are marked `method = llm`; anything you type by hand (`manual`) always wins on the dashboard.

## 4a. Reading scanned PDFs and photos (OCR)

Text PDFs are read through their text layer. When a PDF has no text layer (a scan from the CA, a photo-to-PDF from a phone) or a file is an image (JPG/PNG/TIFF), the assistant renders the pages and runs OCR (`ops/app/ocr.py`):

- Engine: **RapidOCR** (`pip install rapidocr-onnxruntime pypdfium2`, pure pip, offline, no external binary). If a Tesseract binary is on PATH and `pytesseract` is installed it is used as a fallback.
- Pages are rendered at 144 dpi, up to `BUZZCAF_OCR_PAGES` (default 8) pages per file; a phone photo is downscaled to 2400 px. About 1–3 s per page on CPU.
- Results are cached in `ops/data/ocr-cache/<sha256>.txt`, so a file is only OCR'd once.
- OCR text is marked `[ocr]`; the classifier and the fact extractor then match tolerantly (OCR often glues words: `FormGSTR-3B`, `Latefee`), and the Inbox run shows *read by OCR (rapidocr)* in the "why" column.
- Licence-style documents get their **expiry** picked up (`Valid upto 23/06/2024`) and written to the Document row, so the renewal reminders work for scans too.
- Ops → Vault → *read* (and *read* next to any document's file) shows exactly what the assistant could read out of a file — use it when a scan was filed wrongly.
- Set `BUZZCAF_OCR=0` to switch OCR off. A blank or unreadable image is still parked in needs-review.

## 5. The finance dashboard (Ops → Finance)

- **Filing matrix**: one row per FY from 2022-23, columns Financials · Audit · AOC-4 · MGT-7A · DIR-3 KYC · ITR · GSTR-3B (n/12) · GSTR-1 (n/12) · Bank statements (n/12). ✓ means a document of that kind is in the vault for that year; click it. A blank cell means *not in the vault*, not necessarily *never filed* — get the file from the CA and drop it in.
- **KPIs per FY**: revenue, total income, expenses, PBT, PAT, total assets, equity, cash, ITR figures, GST turnover / ITC / late fees — each with confidence, method and a link to the source document.
- **Across the years**: bars for revenue, expenses, PAT, cash, GST turnover.
- **GST by month** and **Bank** tables from GSTR-3B and statements.
- Every number is a row in **Ops → Finance data**; edit or add rows there (set method = manual).

## 6. Where the code is

| File | Role |
|---|---|
| `inbox/` | the drop zone (README inside) |
| `ops/app/classify.py` | text extraction (pypdf / openpyxl / docx / csv, OCR fallback) + rule classifier (kind, FY, period, date, expiry, numbers) |
| `ops/app/ocr.py` | scanned PDFs and photos → text (pypdfium2 render + RapidOCR, cached by SHA-256) |
| `ops/app/extract.py` | numbers out of text → facts (Indian number format, lakhs/crores scaling) |
| `ops/app/sorter.py` | the pipeline: hash → classify → file via `intake.py` → facts → compliance → log |
| `ops/app/mail.py` | IMAP reader, rule-based understanding, attachments → inbox, tasks, SMTP send |
| `ops/app/llm.py` | optional Claude calls (documents, facts, mail, brief) |
| `ops/app/assistant.py` | the cycle and the brief |
| `ops/app/finance.py` | dashboard data |
| `ops/assistant.py` | CLI; `ops/run.py --assistant` runs it as a thread |
| `ops/tests/test_assistant.py`, `test_ocr.py` | synthetic text PDFs, rendered 'scans' and photos through the whole pipeline, mail rules, pages |

## 7. Limits you should know

- OCR is good on clean scans and phone photos of printed documents; handwriting, very skewed photos and low-light shots may come out garbled — check Ops → Vault → *read* and fix the record by hand.
- Fact extraction is pattern-based; exotic CA layouts may yield fewer numbers. The Documents page shows what was extracted; correct it in Finance data.
- Mail is read over IMAP with an app password; OAuth is not implemented. Keep `ops/.env` out of git (it is).
- Compliance auto-marking uses the date on the document; if the CA sends an old filing after a newer one was already marked, it is not regressed.
