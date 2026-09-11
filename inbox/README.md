# inbox — drop anything here

This is the drop zone for the whole company. Put any file in this folder — a PDF from the CA, a GST return, a bank statement, an Amazon report, a lab report, a supplier quote, a photo of a licence — and the assistant will:

1. read it (PDF, Excel, CSV, Word, text; scanned PDFs and photos are read with OCR),
2. work out what it is and which financial year / month it belongs to,
3. rename it to the house convention and move it to the right vault folder,
4. register it in Buzzcaf Ops → Documents (with SHA-256 so duplicates are caught),
5. pull the numbers out of it into Ops → Finance data (revenue, profit, GST, bank balances…),
6. tick off the statutory filing it proves (AOC-4, GSTR-3B, ITR…) in Ops → Compliance,
7. show it on the Finance dashboard.

Anything it is not sure about goes to `vault/12-uploads/needs-review/` with a pending row, listed under "needs review" on the Inbox page — nothing is ever deleted or overwritten. Duplicates move to `inbox/duplicates/`.

## Run it

```bash
python ops/assistant.py sort            # sort what is here now
python ops/assistant.py sort --dry-run  # only tell me what would happen
python ops/assistant.py run             # read mail + sort inbox + print the brief
python ops/assistant.py watch           # keep doing that every 10 minutes (and e-mail the brief at BRIEF_HOUR)
python ops/run.py --assistant           # the Ops web app with the watcher inside it
```

Or open Ops → Inbox (http://127.0.0.1:8010/inbox) and press "Sort now".

Mail attachments the assistant pulls from the company mailbox land here too (prefixed with the mail date) and go through the same path.
