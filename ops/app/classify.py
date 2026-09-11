"""Read a dropped file and decide what it is.

    text  = extract_text(path)          # PDF / XLSX / CSV / DOCX / TXT / MD / JSON (images: '' — no OCR)
    guess = classify(path, text)        # -> Guess(kind, fy, date, number, folder, title, confidence, reasons)

Pure rules, no network. Every kind maps to an intake.KINDS entry so the same
filing path is used whether a human or the sorter files the document. The
optional LLM pass (llm.py) only runs when the rules are unsure.
"""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from . import ocr

TEXT_LIMIT = 60_000
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
PDF_PAGES = 12

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


# ----------------------------------------------------------------- text ----
def extract_text(path: Path) -> str:
    """Best-effort plain text from a file. Never raises; returns '' when unreadable."""
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            text, pages = _pdf_text_and_pages(path)
            if ocr.looks_scanned(text, pages) and ocr.available():
                scanned = ocr.pdf_text(path)
                if len(scanned.strip()) > len(text.strip()):
                    return ("[ocr]\n" + scanned)[:TEXT_LIMIT]
            return text
        if ext in IMAGE_EXT:
            t = ocr.image_text(path) if ocr.available() else ""
            return ("[ocr]\n" + t)[:TEXT_LIMIT] if t.strip() else ""
        if ext in (".xlsx", ".xlsm"):
            return _xlsx_text(path)
        if ext in (".csv", ".tsv"):
            return path.read_text(encoding="utf-8-sig", errors="replace")[:TEXT_LIMIT]
        if ext == ".docx":
            return _docx_text(path)
        if ext in (".txt", ".md", ".json", ".html", ".htm", ".eml"):
            t = path.read_text(encoding="utf-8", errors="replace")
            if ext in (".html", ".htm"):
                t = re.sub(r"<[^>]+>", " ", t)
            return t[:TEXT_LIMIT]
    except Exception:  # noqa: BLE001 - a bad file must not stop the sorter
        return ""
    return ""


def _pdf_text(path: Path) -> str:
    return _pdf_text_and_pages(path)[0]


def _pdf_text_and_pages(path: Path) -> tuple[str, int]:
    from pypdf import PdfReader
    r = PdfReader(str(path))
    if r.is_encrypted:
        try:
            r.decrypt("")
        except Exception:  # noqa: BLE001
            return "", 0
    out: list[str] = []
    n = 0
    for i, page in enumerate(r.pages):
        if i >= PDF_PAGES:
            break
        n += 1
        try:
            out.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 - a broken page must not kill the whole file
            out.append("")
        if sum(len(x) for x in out) > TEXT_LIMIT:
            break
    return "\n".join(out)[:TEXT_LIMIT], n


def _xlsx_text(path: Path) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    out: list[str] = []
    for ws in wb.worksheets[:5]:
        out.append(f"## sheet {ws.title}")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None and str(c).strip()]
            if cells:
                out.append(" | ".join(cells))
            if sum(len(x) for x in out) > TEXT_LIMIT:
                break
    return "\n".join(out)[:TEXT_LIMIT]


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(str(path)) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)[:TEXT_LIMIT]


# -------------------------------------------------------------- helpers ----
def is_ocr(text: str) -> bool:
    return text.startswith("[ocr]")


def despace(text: str) -> str:
    """OCR often glues or splits words: 'FormGSTR-3B', 'Latefee'. Drop whitespace between letters
    (numbers keep their separators so amounts stay parseable)."""
    return re.sub(r"(?<=[A-Za-z(),.:;'/-])\s+(?=[A-Za-z(])", "", text)


# a word boundary that also accepts a lower->UPPER case change, so "FormGSTR-3B" still yields "GSTR"
# but "NDA" inside "STANDARDS" does not match
_OCR_BOUNDARY = r"(?:(?<![A-Za-z0-9])|(?![A-Za-z0-9])|(?-i:(?<=[a-z])(?=[A-Z])))"


def despace_pat(pat: str) -> str:
    """Pattern variant for despaced text: whitespace optional, word boundaries case-change aware."""
    return re.sub(r"\\s\+", r"\\s*", pat).replace(r"\b", _OCR_BOUNDARY)


def search(pat: str, text: str, flags: int = re.I):
    """re.search that also tries the space-free variant when the text came from OCR."""
    m = re.search(pat, text, flags)
    if m or not is_ocr(text):
        return m
    return re.search(despace_pat(pat), despace(text), flags)


def find_fy(text: str, filename: str = "") -> str | None:
    """Return '2024-25' style FY from text/filename, or None."""
    hay = filename + "\n" + text
    if is_ocr(text):
        hay = hay + "\n" + despace(text)
    # explicit FY / financial year
    m = re.search(r"(?:F\.?Y\.?|financial\s+year|fiscal\s+year)\s*:?\s*(20\d\d)\s*[-–/]\s*(20)?(\d\d)\b", hay, re.I)
    if m:
        return _fy(int(m.group(1)))
    # assessment year -> previous FY
    m = re.search(r"(?:A\.?Y\.?|assessment\s+year)\s*:?\s*(20\d\d)\s*[-–/]\s*(20)?(\d\d)\b", hay, re.I)
    if m:
        return _fy(int(m.group(1)) - 1)
    # year ended 31 March 2025
    m = re.search(r"(?:year|period)\s+end(?:ed|ing)\s+(?:on\s+)?(?:31(?:st)?\s*(?:march|mar)\.?,?\s*|31[./-]03[./-])(20\d\d)", hay, re.I)
    if m:
        return _fy(int(m.group(1)) - 1)
    m = re.search(r"as\s+(?:at|on)\s+(?:31(?:st)?\s*(?:march|mar)\.?,?\s*|31[./-]03[./-])(20\d\d)", hay, re.I)
    if m:
        return _fy(int(m.group(1)) - 1)
    # bare 2024-25 in filename or near top of text
    m = re.search(r"\b(20\d\d)\s*[-–]\s*(\d\d)\b", filename) or re.search(r"\b(20\d\d)\s*[-–]\s*(\d\d)\b", text[:3000])
    if m and int(m.group(2)) == (int(m.group(1)) + 1) % 100:
        return _fy(int(m.group(1)))
    # GST period: "Period 09/2026" or "Tax period September 2026"
    p = find_period(text)
    if p:
        y, mo = int(p[:4]), int(p[5:7])
        return _fy(y if mo >= 4 else y - 1)
    return None


def _fy(start_year: int) -> str:
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def find_period(text: str) -> str | None:
    """Month period 'YYYY-MM' for GST/TDS/bank documents."""
    if is_ocr(text):
        text = text + "\n" + despace(text)
    m = re.search(r"(?:tax\s*)?period\s*:?\s*(0?[1-9]|1[0-2])\s*[/-]\s*(20\d\d)", text, re.I)
    if m:
        return f"{m.group(2)}-{int(m.group(1)):02d}"
    m = re.search(r"(?:tax\s+)?period\s*:?\s*([A-Za-z]{3,9})\s*,?\s*(20\d\d)", text, re.I)
    if m and m.group(1)[:3].lower() in MONTHS:
        return f"{m.group(2)}-{MONTHS[m.group(1)[:3].lower()]:02d}"
    m = re.search(r"(?:month|for\s+the\s+month\s+of)\s*:?\s*([A-Za-z]{3,9})\s*,?\s*(20\d\d)", text, re.I)
    if m and m.group(1)[:3].lower() in MONTHS:
        return f"{m.group(2)}-{MONTHS[m.group(1)[:3].lower()]:02d}"
    return None


def find_dates(text: str) -> list[date]:
    out: list[date] = []
    for m in re.finditer(r"(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](20\d\d)(?!\d)", text):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            out.append(date(y, mo, d))
        except ValueError:
            pass
    for m in re.finditer(r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?\s*(?:day\s*of\s*)?([A-Za-z]{3,9})\.?,?\s*(20\d\d)(?!\d)", text):
        mo = MONTHS.get(m.group(2)[:3].lower())
        if mo:
            try:
                out.append(date(int(m.group(3)), mo, int(m.group(1))))
            except ValueError:
                pass
    for m in re.finditer(r"\b(20\d\d)-(\d\d)-(\d\d)\b", text):
        try:
            out.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            pass
    return out


def best_date(text: str, filename: str = "") -> date | None:
    """The most plausible 'date on the document': the latest date not in the future."""
    today = date.today()
    ds = [d for d in find_dates(filename + "\n" + text) if date(2015, 1, 1) <= d <= today]
    return max(ds) if ds else None


NUMBER_PATTERNS = [
    ("udin", r"UDIN\s*:?\s*([0-9A-Z]{18})(?![0-9A-Z])"),
    ("srn", r"SRN\s*:?\s*([A-Z]\d{8})(?!\d)"),
    ("arn", r"ARN\s*:?\s*(A[A-Z0-9]{14})"),
    ("ack", r"(?:Acknowledg(?:e)?ment\s*(?:Number|No\.?)|Ack\.?\s*No\.?)\s*:?\s*(\d{15})(?!\d)"),
    ("gstin", r"(?<![A-Z0-9])(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d])(?![A-Z0-9])"),
    ("fssai", r"(?<!\d)(1\d{13})(?!\d)"),
    ("cin", r"(?<![A-Z0-9])([UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})(?![A-Z0-9])"),
    ("account", r"(?:A/?c\.?\s*(?:No\.?|Number)|Account\s*(?:No\.?|Number))\s*:?\s*(\d{9,18})(?!\d)"),
]

EXPIRY_PAT = (r"(?:valid\s*(?:up\s*to|till|until|through|upto)|validity\s*(?:up\s*to|till|until|ends?)?|expir(?:y|es|ing)\s*(?:date|on)?|"
              r"date\s*of\s*expiry|renew(?:al)?\s*(?:by|before|due))\s*:?\s*"
              r"(\d{1,2}[/.-]\d{1,2}[/.-]20\d\d|\d{1,2}(?:st|nd|rd|th)?\s*[A-Za-z]{3,9}\.?,?\s*20\d\d|20\d\d-\d\d-\d\d)")


def find_expiry(text: str) -> date | None:
    m = search(EXPIRY_PAT, text)
    if not m:
        return None
    ds = find_dates(m.group(1))
    return ds[0] if ds else None


def find_number(text: str, prefer: tuple[str, ...] = ()) -> str | None:
    found: dict[str, str] = {}
    for name, pat in NUMBER_PATTERNS:
        m = search(pat, text, 0) or search(pat, text.upper(), 0)
        if m:
            found[name] = m.group(1).upper()
    for p in prefer:
        if p in found:
            return found[p]
    for name in ("udin", "srn", "arn", "ack"):
        if name in found:
            return found[name]
    return None


# ------------------------------------------------------------- classify ----
@dataclass
class Guess:
    kind: str = "other"
    folder: str | None = None      # None -> intake decides from kind + fy
    fy: str | None = None
    period: str | None = None
    when: str | None = None        # YYYY-MM-DD
    expiry: str | None = None      # YYYY-MM-DD, licences / agreements
    number: str | None = None
    title: str | None = None
    detail: str | None = None
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)
    text_chars: int = 0

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


# (kind, folder-or-None, [(regex, weight, applies_to)], number preference)
# applies_to: "t" text, "f" filename, "tf" both
RULES: list[tuple[str, str | None, list[tuple[str, float, str]], tuple[str, ...]]] = [
    ("gstr-3b", None, [(r"\bGSTR\s*-?\s*3B\b", 3, "tf"), (r"eligible\s+ITC", 1, "t"), (r"outward\s+taxable\s+supplies", 1, "t")], ("arn",)),
    ("gstr-1", None, [(r"\bGSTR\s*-?\s*1\b(?!\d)", 3, "tf"), (r"B2C\s*\(?(?:small|large|others)", 1, "t"), (r"details\s+of\s+outward\s+supplies", 1, "t")], ("arn",)),
    ("gstr-9", None, [(r"\bGSTR\s*-?\s*9\b", 3, "tf"), (r"annual\s+return", 1, "t")], ("arn",)),
    ("aoc-4", None, [(r"\bAOC\s*-?\s*4\b", 3, "tf"), (r"form\s+for\s+filing\s+financial\s+statement", 2, "t")], ("srn",)),
    ("mgt-7a", None, [(r"\bMGT\s*-?\s*7A?\b", 3, "tf"), (r"abridged\s+annual\s+return", 2, "t"), (r"annual\s+return.*small\s+compan", 1, "t")], ("srn",)),
    ("adt-1", None, [(r"\bADT\s*-?\s*1\b", 3, "tf"), (r"appointment\s+of\s+auditor", 2, "t")], ("srn",)),
    ("dir-3-kyc", None, [(r"\bDIR\s*-?\s*3\s*-?\s*KYC\b", 3, "tf"), (r"\bDIN\b.*\bKYC\b", 1, "t")], ("srn",)),
    ("msc-1", None, [(r"\bMSC\s*-?\s*1\b", 3, "tf"), (r"dormant\s+status", 2, "t")], ("srn",)),
    ("itr", None, [(r"\bITR\s*-?\s*V\b", 3, "tf"), (r"\bITR\s*-?\s*6\b", 3, "tf"), (r"INDIAN\s+INCOME\s+TAX\s+RETURN", 3, "t"), (r"e-?filing\s+acknowledg", 2, "t"), (r"assessment\s+year", 1, "t")], ("ack",)),
    ("form-26as", None, [(r"\bForm\s*26\s*AS\b", 3, "tf"), (r"annual\s+information\s+statement", 3, "t"), (r"\bAIS\b", 1, "f"), (r"tax\s+credit\s+statement", 1, "t")], ()),
    ("tds-26q", None, [(r"\bForm\s*26\s*Q\b", 3, "tf"), (r"\b26Q\b", 2, "f")], ()),
    ("tds-24q", None, [(r"\bForm\s*24\s*Q\b", 3, "tf"), (r"\b24Q\b", 2, "f")], ()),
    ("audit-report", None, [(r"independent\s+auditor'?s?\s+report", 4, "t"), (r"auditor'?s?\s+report", 2, "tf"), (r"true\s+and\s+fair\s+view", 1, "t"), (r"\bCARO\b", 1, "t"), (r"\bUDIN\b", 1, "t")], ("udin",)),
    ("financial-statements", None, [(r"balance\s+sheet", 2, "tf"), (r"statement\s+of\s+profit\s+and\s+loss", 3, "t"), (r"profit\s+(?:and|&)\s+loss", 1, "tf"), (r"notes\s+(?:forming\s+part|to\s+(?:the\s+)?(?:financial|accounts))", 1, "t"), (r"financial\s+statements?", 2, "tf"), (r"\bfinancials?\b", 1, "f")], ("udin",)),
    ("directors-report", None, [(r"director'?s'?\s+report", 3, "tf"), (r"board'?s\s+report", 3, "tf")], ()),
    ("minutes-agm", None, [(r"minutes\s+of\s+(?:the\s+)?(?:annual\s+general\s+meeting|AGM)", 4, "tf"), (r"\bAGM\b.*minutes", 2, "tf")], ()),
    ("notice-agm", None, [(r"notice\s+(?:is\s+hereby\s+given|of\s+(?:the\s+)?(?:annual\s+general\s+meeting|AGM))", 4, "t"), (r"\bAGM\s+notice\b", 3, "tf")], ()),
    ("board-resolution", None, [(r"board\s+resolution", 3, "tf"), (r"resolved\s+that", 2, "t"), (r"certified\s+true\s+copy", 1, "t")], ()),
    ("trial-balance", None, [(r"trial\s+balance", 4, "tf")], ()),
    ("ledger", None, [(r"\bledger\b", 3, "tf"), (r"day\s*book", 2, "tf"), (r"\bgeneral\s+ledger\b", 2, "tf")], ()),
    ("bank-statement", None, [(r"statement\s+of\s+account", 3, "t"), (r"bank\s+statement", 3, "tf"), (r"opening\s+balance", 1, "t"), (r"closing\s+balance", 1, "t"), (r"\bIFSC\b", 1, "t"), (r"withdrawal|deposit", 1, "t")], ("account",)),
    ("pt-return", None, [(r"profession(?:al)?\s+tax", 3, "tf"), (r"\bPTRC\b|\bPTEC\b", 3, "tf")], ()),
    ("engagement-letter", None, [(r"engagement\s+letter", 4, "tf"), (r"terms\s+of\s+(?:our\s+)?engagement", 2, "t")], ()),
    ("fee-invoice", None, [(r"professional\s+fees?", 2, "t"), (r"chartered\s+accountants?", 1, "t"), (r"\binvoice\b", 1, "tf")], ()),
    ("ca-report", None, [(r"compliance\s+status", 3, "tf"), (r"chartered\s+accountant", 1, "t"), (r"\bCA\s+report\b", 2, "f")], ()),
    # non-accounts categories
    ("fssai-licence", "03-fssai", [(r"\bFSSAI\b", 2, "tf"), (r"food\s+safety\s+and\s+standards", 2, "t"), (r"licen[cs]e\s+(?:no|number)", 1, "t"), (r"\bFoSCoS\b", 1, "t"), (r"kind\s+of\s+business", 1, "t")], ("fssai",)),
    ("gst-certificate", "02-tax", [(r"registration\s+certificate", 2, "t"), (r"\bREG\s*-?\s*06\b", 3, "t"), (r"goods\s+and\s+services\s+tax", 1, "t"), (r"\bGSTIN\b", 1, "t")], ("gstin",)),
    ("incorporation", "01-company", [(r"certificate\s+of\s+incorporation", 4, "t"), (r"corporate\s+identity\s+number", 1, "t"), (r"\bSPICe\b", 2, "t")], ("cin",)),
    ("coa", "09-batches-coa", [(r"certificate\s+of\s+analysis", 4, "tf"), (r"\bCOA\b", 3, "tf"), (r"batch\s+(?:no|number)", 1, "t"), (r"moisture", 1, "t")], ()),
    ("lab-report", "10-lab-reports", [(r"test\s+report", 3, "tf"), (r"\bNABL\b", 2, "t"), (r"nutritional?\s+(?:analysis|information|value)", 2, "t"), (r"microbi", 1, "t"), (r"\blab(?:oratory)?\b", 1, "tf")], ()),
    ("supplier-licence", "08-suppliers", [(r"manufacturer", 1, "t"), (r"quotation|quote\b", 2, "tf"), (r"proforma", 2, "tf"), (r"\bMOQ\b", 2, "t"), (r"price\s+per\s+kg", 2, "t")], ("fssai",)),
    ("amazon-report", "07-commerce", [(r"settlement-id|settlement\s+id", 3, "t"), (r"amazon", 2, "tf"), (r"order-id|order\s+id", 1, "t"), (r"\bFBA\b", 1, "tf"), (r"seller\s+central", 1, "t"), (r"fulfil?ment", 1, "t")], ()),
    ("agreement", "11-agreements", [(r"\bagreement\b", 3, "tf"), (r"\bcontract\b", 2, "tf"), (r"witnesseth|party\s+of\s+the\s+first\s+part", 2, "t"), (r"\bNDA\b", 2, "tf"), (r"terms\s+and\s+conditions", 1, "t")], ()),
    ("invoice", None, [(r"tax\s+invoice", 3, "tf"), (r"\binvoice\b", 2, "tf"), (r"\bHSN\b", 1, "t"), (r"\bbill\b", 1, "f")], ("gstin",)),
    ("label-artwork", "06-brand", [(r"artwork", 3, "f"), (r"label", 2, "f"), (r"\bbest\s+before\b", 2, "t"), (r"net\s+(?:qty|quantity|wt)", 2, "t")], ()),
]

# folder for kinds that live in the accounts tree is decided by intake (needs fy)
ACCOUNTS_KINDS = {
    "gstr-3b", "gstr-1", "gstr-9", "aoc-4", "mgt-7a", "adt-1", "dir-3-kyc", "msc-1", "itr", "form-26as",
    "tds-26q", "tds-24q", "audit-report", "financial-statements", "directors-report", "minutes-agm", "notice-agm",
    "board-resolution", "trial-balance", "ledger", "bank-statement", "pt-return", "engagement-letter",
    "fee-invoice", "ca-report", "invoice",
}

# kinds classify may emit that intake does not know: map to (intake kind, title)
KIND_ALIASES = {
    "gst-certificate": ("other", "GST registration certificate"),
    "incorporation": ("other", "Certificate of incorporation"),
    "fssai-licence": ("other", "FSSAI licence / FoSCoS document"),
    "supplier-licence": ("other", "Supplier document"),
    "amazon-report": ("other", "Amazon report"),
    "agreement": ("other", "Agreement"),
    "label-artwork": ("other", "Label artwork"),
}
DOC_TYPE_OVERRIDES = {
    "gst-certificate": "gst", "incorporation": "incorporation", "fssai-licence": "fssai-licence",
    "supplier-licence": "supplier-licence", "amazon-report": "other", "agreement": "supplier-agreement",
    "label-artwork": "label-artwork",
}



def classify(path: Path, text: str) -> Guess:
    name = path.name
    stem = re.sub(r"[_\-.]+", " ", path.stem)
    g = Guess(text_chars=len(text))
    scores: dict[str, float] = {}
    hits: dict[str, list[str]] = {}
    for kind, folder, pats, _pref in RULES:
        s = 0.0
        for pat, w, where in pats:
            if "t" in where and text and search(pat, text):
                s += w
                hits.setdefault(kind, []).append(f"text:{pat}")
            if "f" in where and re.search(pat, stem, re.I):
                s += w * 1.5
                hits.setdefault(kind, []).append(f"name:{pat}")
        if s:
            scores[kind] = s
    if path.suffix.lower() in IMAGE_EXT and not scores:
        g.kind, g.folder, g.confidence = "photo", "12-uploads/needs-review", 0.2
        g.reasons.append("image with no readable text" + ("" if ocr.available() else " (no OCR engine installed)") + "; needs a human")
        return g
    if text.startswith("[ocr]"):
        g.reasons.append(f"read by OCR ({ocr.engine_name()})")
    if not scores:
        g.reasons.append("no rule matched" + ("" if text else " (no readable text)"))
        g.kind, g.confidence = "other", 0.1
    else:
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        kind, top = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else 0.0
        g.kind = kind
        g.confidence = min(0.98, 0.35 + 0.12 * top - 0.06 * second)
        g.reasons += hits[kind][:4]
        # an audit report usually carries the financial statements too: same folder, no penalty
        family = {"audit-report", "financial-statements", "directors-report"}
        if second and top - second < 1 and not ({kind, ranked[1][0]} <= family):
            g.reasons.append(f"close call with {ranked[1][0]}")
            g.confidence = min(g.confidence, 0.55)
        g.folder = dict((k, f) for k, f, _, _ in RULES).get(kind)
    g.fy = find_fy(text, name)
    g.period = find_period(text)
    exp = find_expiry(text)
    g.expiry = exp.isoformat() if exp else None
    d = best_date(text, name)
    if d and exp and d == exp:
        others = [x for x in find_dates(name + "\n" + text) if date(2015, 1, 1) <= x <= date.today() and x != exp]
        d = max(others) if others else None
    g.when = d.isoformat() if d else None
    pref = dict((k, p) for k, _, _, p in RULES).get(g.kind, ())
    g.number = find_number(text, pref)
    if g.kind in ACCOUNTS_KINDS and not g.fy:
        g.confidence -= 0.15
        g.reasons.append("financial year not found")
    if g.period and g.kind in ("gstr-3b", "gstr-1", "tds-26q", "tds-24q", "bank-statement"):
        g.detail = g.period
    if not g.when:
        g.reasons.append("no date found; using today")
    g.confidence = round(max(0.0, min(1.0, g.confidence)), 2)
    return g


def sha256_of(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def as_json(g: Guess) -> str:
    return json.dumps(g.as_dict(), ensure_ascii=False)
