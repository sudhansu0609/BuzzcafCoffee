"""File a document into the vault and register it in Buzzcaf Ops in one step.

Built for the CA's output (accounts, audit, ITR, GST, ROC), but works for any
vault folder.

    python ops/intake.py <file> --kind audit-report --fy 2024-25 --date 2025-09-20
    python ops/intake.py <file> --kind aoc-4 --fy 2024-25 --date 2025-10-28 --number A12345678
    python ops/intake.py <file> --kind coa --folder 09-batches-coa --title "COA BZH2609" --date 2026-11-03
    python ops/intake.py --unregistered            # vault files with no Ops -> Documents row
    python ops/intake.py --kinds                   # list known kinds

The file is renamed to <kind>-fy<yyyy-yy>[-<detail>]-<date><ext>, moved (or
copied with --copy) into vault/13-accounts-and-audit/FY<yyyy-yy>/ unless
--folder is given, and a Documents row is created with the matching type,
number, issue date and tags. Nothing is ever overwritten: a name clash gets
a -1, -2 suffix.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import db, paths  # noqa: E402

ACCOUNTS_FOLDER = "13-accounts-and-audit"

# kind -> (Ops doc_type, default title, authority)
KINDS: dict[str, tuple[str, str, str]] = {
    "financial-statements": ("financial-statements", "Financial statements (BS, P&L, notes)", "Auditor / CA"),
    "audit-report": ("audit-report", "Statutory auditor's report", "Auditor"),
    "directors-report": ("board-minutes", "Directors' report", "Board"),
    "notice-agm": ("board-minutes", "AGM notice", "Board"),
    "minutes-agm": ("board-minutes", "AGM minutes", "Board"),
    "board-resolution": ("board-resolution", "Board resolution", "Board"),
    "itr": ("itr", "Income tax return ITR-6 acknowledgement", "Income Tax Dept"),
    "form-26as": ("form-26as", "Form 26AS", "Income Tax Dept"),
    "ais": ("form-26as", "Annual Information Statement", "Income Tax Dept"),
    "aoc-4": ("roc-filing", "AOC-4 financial statements filing", "MCA / ROC Pune"),
    "mgt-7a": ("roc-filing", "MGT-7A annual return", "MCA / ROC Pune"),
    "adt-1": ("roc-filing", "ADT-1 auditor appointment", "MCA / ROC Pune"),
    "dir-3-kyc": ("roc-filing", "DIR-3 KYC", "MCA"),
    "msc-1": ("roc-filing", "MSC-1 dormant status application", "MCA / ROC Pune"),
    "roc-filing": ("roc-filing", "ROC filing", "MCA / ROC Pune"),
    "gstr-1": ("gst-return", "GSTR-1", "GST portal"),
    "gstr-3b": ("gst-return", "GSTR-3B", "GST portal"),
    "gstr-9": ("gst-return", "GSTR-9 annual return", "GST portal"),
    "gst-return": ("gst-return", "GST return", "GST portal"),
    "tds-24q": ("tds-return", "TDS return 24Q", "TRACES"),
    "tds-26q": ("tds-return", "TDS return 26Q", "TRACES"),
    "tds-return": ("tds-return", "TDS return", "TRACES"),
    "pt-return": ("ca-report", "Professional tax return", "Maharashtra PT"),
    "ledger": ("ledger", "Ledger export", "CA"),
    "trial-balance": ("ledger", "Trial balance", "CA"),
    "bank-statement": ("bank-statement", "Bank statement", "Bank"),
    "ca-report": ("ca-report", "CA report", "CA"),
    "engagement-letter": ("ca-report", "CA engagement letter", "CA"),
    "fee-invoice": ("invoice", "CA fee invoice", "CA"),
    "coa": ("coa", "Certificate of analysis", "Supplier"),
    "lab-report": ("lab-report", "Lab report", "Lab"),
    "invoice": ("invoice", "Invoice", ""),
    "other": ("other", "Document", ""),
}

SKIP_NAMES = {"readme.md", "index.md", "index.json", "secrets-not-stored-here.md"}
SKIP_PREFIXES = ("99-archive/", "06-brand/")


def norm_fy(fy: str | None) -> str | None:
    """'2024-25' | 'FY2024-25' | '2024-2025' -> '2024-25'."""
    if not fy:
        return None
    f = fy.strip().upper().replace("/", "-")
    if f.startswith("FY"):
        f = f[2:]
    m = re.match(r"^(20\d\d)-(?:20)?(\d\d)$", f)
    if not m:
        raise SystemExit(f"--fy must look like 2024-25 (got {fy!r})")
    y1, y2 = int(m.group(1)), int(m.group(2))
    if y2 != (y1 + 1) % 100:
        raise SystemExit(f"--fy {fy!r}: second year must follow the first (e.g. 2024-25)")
    return f"{y1}-{y2:02d}"


def slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)


def target_name(kind: str, fy: str | None, detail: str | None, when: str, ext: str) -> str:
    parts = [kind]
    if fy:
        parts.append(f"fy{fy}")
    if detail:
        parts.append(slug(detail))
    parts.append(when)
    return "-".join(parts) + ext.lower()


def unique(dest: Path) -> Path:
    i = 1
    out = dest
    while out.exists():
        out = dest.with_name(f"{dest.stem}-{i}{dest.suffix}")
        i += 1
    return out


def file_document(src: Path, kind: str, *, fy: str | None, when: str, detail: str | None = None,
                  folder: str | None = None, title: str | None = None, number: str | None = None,
                  expiry: str | None = None, notes: str | None = None, copy: bool = False,
                  con=None) -> tuple[Path, int]:
    """Move/copy `src` into the vault under the naming rule and insert a Documents row.

    Returns (destination path, document id)."""
    if kind not in KINDS:
        raise SystemExit(f"unknown kind {kind!r}; run --kinds")
    if not src.is_file():
        raise SystemExit(f"not a file: {src}")
    date.fromisoformat(when)  # validate
    if expiry:
        date.fromisoformat(expiry)
    doc_type, default_title, authority = KINDS[kind]
    if folder is None:
        if fy is None:
            raise SystemExit("--fy is required unless --folder is given")
        folder = f"{ACCOUNTS_FOLDER}/FY{fy}"
    folder = folder.strip("/\\").replace("\\", "/")
    dest_dir = paths.VAULT_DIR / folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = unique(dest_dir / target_name(kind, fy, detail, when, src.suffix))
    if copy:
        shutil.copy2(str(src), str(dest))
    else:
        shutil.move(str(src), str(dest))
    rel = str(dest.relative_to(paths.VAULT_DIR)).replace("\\", "/")

    t = title or default_title
    if fy and f"FY{fy}" not in t:
        t = f"{t} FY{fy}"
    if detail and detail not in t:
        t = f"{t} ({detail})"
    tags = ["accounts" if folder.startswith(ACCOUNTS_FOLDER) else folder.split("/")[0], kind]
    if fy:
        tags.append(f"fy{fy}")
    own = con is None
    con = con or db.connect()
    if own:
        db.init_schema(con)
    row_id = db.insert(con, "documents", {
        "title": t, "doc_type": doc_type, "number": number or "", "authority": authority,
        "issue_date": when, "expiry_date": expiry or "", "renewal_lead_days": 90 if expiry else 0,
        "status": "valid", "file_path": rel, "tags": ", ".join(tags),
        "notes": notes or f"Filed via ops/intake.py on {date.today().isoformat()} from {src.name}.",
    })
    if own:
        con.close()
    return dest, row_id


def unregistered(con) -> list[str]:
    """Vault files (outside brand/archive) that no Documents row points at."""
    known = {r[0] for r in con.execute("SELECT file_path FROM documents WHERE file_path IS NOT NULL")}
    out: list[str] = []
    for p in sorted(paths.VAULT_DIR.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(paths.VAULT_DIR)).replace("\\", "/")
        if rel.startswith(SKIP_PREFIXES) or p.name.lower() in SKIP_NAMES:
            continue
        if rel not in known:
            out.append(rel)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(prog="buzzcaf-intake", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="file to bring into the vault")
    ap.add_argument("--kind", choices=sorted(KINDS), help="what the document is")
    ap.add_argument("--fy", help="financial year, e.g. 2024-25")
    ap.add_argument("--date", help="date on the document, YYYY-MM-DD (default today)")
    ap.add_argument("--detail", help="short qualifier for the filename, e.g. 'signed', 'q2', 'srn-A123'")
    ap.add_argument("--folder", help="vault folder to use instead of 13-accounts-and-audit/FY<fy>")
    ap.add_argument("--title")
    ap.add_argument("--number", help="SRN / ARN / acknowledgement number")
    ap.add_argument("--expiry", help="YYYY-MM-DD, only if the document expires")
    ap.add_argument("--notes")
    ap.add_argument("--copy", action="store_true", help="copy instead of move the source file")
    ap.add_argument("--unregistered", action="store_true", help="list vault files with no Documents row")
    ap.add_argument("--kinds", action="store_true", help="list known kinds")
    a = ap.parse_args()

    if a.kinds:
        for k, (dt, title, _) in KINDS.items():
            print(f"  {k:22} -> {dt:22} {title}")
        return
    if a.unregistered:
        con = db.connect()
        db.init_schema(con)
        rows = unregistered(con)
        print("\n".join(rows) if rows else "Every vault file has a Documents row.")
        return
    if not a.file or not a.kind:
        ap.error("need <file> and --kind (or --unregistered / --kinds)")
    dest, row_id = file_document(
        Path(a.file), a.kind, fy=norm_fy(a.fy), when=a.date or date.today().isoformat(), detail=a.detail,
        folder=a.folder, title=a.title, number=a.number, expiry=a.expiry, notes=a.notes, copy=a.copy)
    rel = str(dest.relative_to(paths.VAULT_DIR)).replace("\\", "/")
    print(f"filed  vault/{rel}")
    # Where Ops actually is, not where it usually is: it may have stepped forward
    # off its preferred port (GUARDIAN_PLAN.md section 11 rule 5).
    import buzzcaf_ports
    from app.main import APP_ID, PREFERRED_PORT

    base = buzzcaf_ports.discover(APP_ID, PREFERRED_PORT)
    where = f"  ({base}/documents/{row_id})" if base else ""
    print(f"ops    documents/{row_id}{where}")


if __name__ == "__main__":
    main()
