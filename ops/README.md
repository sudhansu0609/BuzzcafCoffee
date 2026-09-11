# Buzzcaf Ops — company records, compliance and protocols

A local, single-user system that holds everything Buzzcaf Private Limited must keep: documents with expiry dates, the statutory compliance calendar, suppliers, batches and QC, retention samples, complaints, lab tests, contacts, tasks, a decisions log and the twelve SOPs. FastAPI + SQLite + server-rendered HTML; no build step; JSON API under `/api/*` for BuzzcafAI / Dexter.

## Run
```bash
pip install -r ops/requirements.txt      # fastapi, uvicorn, jinja2, python-multipart, pydantic, markdown, pytest, httpx + pypdf, openpyxl, pypdfium2, rapidocr-onnxruntime (OCR)
python ops/seed.py                       # idempotent: 55 documents from the vault, 18 obligations, 6 suppliers, 16 contacts, 20 tasks, 8 decisions
python ops/run.py                        # prints `READY port=N` and opens there (--port, --host, --reload)
                                         # the port is a preference: BUZZCAFCOFFEE_PORT, else 8010, and it
                                         # steps forward if that one is busy (GUARDIAN_PLAN.md section 11)
python ops/run.py --assistant            # same, plus the assistant watcher: reads mail, sorts inbox/, e-mails the brief
```
Or `python -m ops` from `BuzzcafCoffee/`. API docs at `/api/docs`.

CLI (for cron / Dexter):
```bash
python ops/cli.py expiring --days 60     # documents expired / expiring
python ops/cli.py due                    # compliance due in 30 days + overdue
python ops/backup.py [--verify]          # ops/backups/buzzcaf-ops-YYYYMMDD-HHMM.zip (db + vault) and latest.zip
python ops/intake.py <file> --kind audit-report --fy 2024-25 --date 2025-09-20   # file a CA report into the vault + register it
python ops/intake.py --unregistered      # vault files that have no Documents row
python ops/assistant.py sort [--dry-run] # auto-file everything in inbox/ (classify -> vault -> Documents -> Finance data -> Compliance)
python ops/assistant.py run              # read mail + sort inbox + print the brief;  watch = keep doing it;  brief --send = e-mail it
```
Tests: `cd ops && python -m pytest tests -q` (uses a temp data dir; never touches `ops/data/ops.db`).

## Modules
| URL | What | Special logic |
|---|---|---|
| `/` | Dashboard: expired / 30 / 60 / 90-day documents, overdue and upcoming obligations, tasks due, open complaints, batch health, complaint patterns | Runs auto-expiry + next-due refresh on every load |
| `/inbox` | Drop-zone status, upload, "Sort now", last run, needs-review | Sorter: `app/sorter.py` (classify → intake → facts → compliance) |
| `/finance` | Finance dashboard: filing matrix per FY, KPIs, GST by month, bank, year-over-year bars | Built from `/facts` + document tags; `app/finance.py` |
| `/brief` | Morning brief (overdue, mail needing you, filed overnight, needs review); "E-mail it to me" | `app/assistant.py`; sent daily at BRIEF_HOUR by the watcher |
| `/facts` | Finance data: one row per metric per period, linked to its source document; manual beats auto | `app/extract.py` fills it; edit freely |
| `/mail` | Mail the assistant read: category, importance, summary, action, deadline, attachments → documents, task | `app/mail.py` (IMAP, app password in `ops/.env`) |
| `/documents` | Every company paper: type, number, authority, issue/expiry, status, vault file, restricted flag, renewal lead days | File upload into `vault/`; "open file" served read-only |
| `/compliance` | Obligations with a JSON rule (`monthly` day N, `yearly` month/day, `quarterly`, `once`, every-N-`years`) → `next_due`; "mark done" writes a log and advances the date | Seeded with GST, ROC, FSSAI, ITR, PT, TDS, domains, backups |
| `/suppliers` | Manufacturer register: FSSAI no + FoSCoS-verified flag, MOQ, lead time, quotes, samples, audit visit | Seeded with the six from the restart plan |
| `/batches` | Batch no, product, supplier, dates, qty, COA file, the six SOP-03 receiving checks, QC result, destination | Dashboard flags batches with missing checks or fail/quarantine |
| `/retention_samples` | Two per batch, location, discard-after | |
| `/complaints` | Channel, batch, issue, severity, action, resolved | ≥3 complaints on one batch = pattern flag |
| `/lab_tests` | Lab, batch, test type, result file, pass/fail, valid-until | |
| `/contacts` | CA, CS, bank, FoSCoS 1800112100, Amazon, gateways, registrar, printer, courier | PLACEHOLDER where unknown |
| `/tasks`, `/decisions` | Todo/doing/done with due dates; decisions with rationale | Seeded with the week-one actions |
| `/sops` | SOP-01 … SOP-12 rendered from `ops/sops/*.md` (front-matter: version, last_reviewed, owner) | Edit the markdown; no DB |
| `/vault` | Browser for the `vault/` folder; *read* shows what the assistant can read out of any file (text layer or OCR) | Read-only |

## Vault layout (`../vault/`)
`01-company` (incorporation, MOA/AOA, SPICe+, INC-20A, challans, ePAN, bank statement) · `02-tax` (GST) · `03-fssai` · `04-licences` (Shop Act, rent/leave-licence, address proofs) · `05-directors-kyc` (**restricted**: Aadhaar/PAN) · `06-brand` (logos, product photos) · `07-commerce` (note only: secrets are not stored here) · `08-suppliers` · `09-batches-coa` · `10-lab-reports` · `11-agreements` · `12-uploads` (files dropped in from the Ops UI without a folder) · `13-accounts-and-audit` (**everything the CA sends**: financial statements, audit, ITR, GST/TDS returns, ROC filings, ledgers, bank statements — one folder per FY, `inbox/` drop zone) · `99-archive`. `vault/INDEX.md` and `vault/index.json` list every file with the numbers and dates extracted from it.

## Mount inside BuzzcafAI (optional)
```python
# BuzzcafAI backend/app/main.py
import sys; sys.path.insert(0, r"B:/youtubeProjects/Buzzcaf_Media/BuzzcafCoffee/ops")
from app.main import create_app as create_ops_app
app.mount("/ops", create_ops_app(root_path="/ops"))
```
Paths derive from `ops/app/paths.py` (env overrides `BUZZCAF_OPS_DATA`, `BUZZCAF_OPS_VAULT`, honoured only if the directory exists — same guard as BuzzcafAI). Dexter can call `GET /ops/api/dashboard` for the morning brief.

## Data model
Declared once in `ops/app/specs.py` (a `Resource` = table + ordered `Field`s + list columns). Adding a field there adds the column automatically (`ALTER TABLE` on boot), the form input, the list column and the API field. Kinds: text, textarea, date, int, real, bool, select, file, ref, json, readonly.

## Backups and security
This system holds identity documents. Keep `BuzzcafCoffee/` on an encrypted drive; run `backup.py` monthly (SOP-08) and copy the zip to an encrypted cloud folder; test a restore quarterly (open `latest.zip`, copy `ops.db` back). Never expose the Ops port beyond localhost (`--host` defaults to 127.0.0.1).
