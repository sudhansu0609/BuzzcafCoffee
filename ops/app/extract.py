"""Pull numbers out of a classified document so the finance dashboard has data.

    facts = extract_facts(kind, text, fy, period)   # -> list of {metric, value, period, confidence, notes}

Rule-based, Indian-format aware (1,23,456.00, (negatives), "Rs. in lakhs").
Every fact carries a confidence; the dashboard shows the number and the
Finance data page lets a human correct it. Optional LLM extraction in llm.py
fills what these rules miss.
"""
from __future__ import annotations

import csv
import io
import re

NUM = r"\(?-?\s*(?:₹|Rs\.?|INR)?\s*\d[\d,]*(?:\.\d+)?\s*\)?"


def parse_amount(s: str) -> float | None:
    s = s.strip()
    neg = s.startswith("(") and s.endswith(")") or s.startswith("-")
    s = re.sub(r"[^\d.]", "", s)
    if not s or s == ".":
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def scale_of(text: str) -> tuple[float, str]:
    head = text[:6000]
    if re.search(r"(?:₹|Rs\.?|INR|amount)s?\s*(?:in|\()\s*(?:lakhs?|lacs?)", head, re.I):
        return 1e5, "stated in lakhs"
    if re.search(r"(?:₹|Rs\.?|INR|amount)s?\s*(?:in|\()\s*(?:crores?)", head, re.I):
        return 1e7, "stated in crores"
    if re.search(r"(?:₹|Rs\.?|INR|amount)s?\s*(?:in|\()\s*(?:thousands?|'000)", head, re.I):
        return 1e3, "stated in thousands"
    if re.search(r"(?:₹|Rs\.?|INR|amount)s?\s*(?:in|\()\s*hundreds?", head, re.I):
        return 1e2, "stated in hundreds"
    return 1.0, ""


def _first_amount_after(label_pat: str, text: str, nth: int = 1) -> float | None:
    """Value of the nth number on the same line as (and after) the label."""
    v = _scan(label_pat, text, nth)
    if v is None and text.startswith("[ocr]"):
        from .classify import despace, despace_pat
        v = _scan(despace_pat(label_pat), despace(text), nth)
    return v


def _scan(label_pat: str, text: str, nth: int) -> float | None:
    for m in re.finditer(label_pat, text, re.I):
        line_end = text.find("\n", m.end())
        seg = text[m.end(): line_end if line_end != -1 else m.end() + 200]
        nums = [parse_amount(x) for x in re.findall(NUM, seg)]
        nums = [n for n in nums if n is not None]
        # skip note-reference numbers like "3" or "2.1" that precede the amounts
        nums = [n for n in nums if abs(n) >= 100 or n == 0] or nums
        if len(nums) >= nth:
            return nums[nth - 1]
    return None


FIN_LABELS = [
    ("revenue", r"revenue\s+from\s+operations", 0.85),
    ("other_income", r"other\s+income", 0.7),
    ("total_income", r"total\s+income", 0.8),
    ("total_expenses", r"total\s+expenses", 0.85),
    ("pbt", r"profit\s*/?\s*\(?loss\)?\s+before\s+(?:exceptional\s+items\s+and\s+)?tax", 0.8),
    ("pat", r"profit\s*/?\s*\(?loss\)?\s+(?:for\s+the\s+(?:year|period)|after\s+tax)", 0.8),
    ("total_assets", r"total\s+assets", 0.85),
    ("equity", r"(?:total\s+equity|shareholders?'?\s*funds?)", 0.75),
    ("total_liabilities", r"total\s+(?:equity\s+and\s+)?liabilities", 0.6),
    ("cash", r"cash\s+and\s+cash\s+equivalents", 0.75),
    ("share_capital", r"(?:equity\s+)?share\s+capital", 0.6),
    ("borrowings", r"borrowings", 0.5),
]

GST_LABELS = [
    ("gst_taxable_value", r"\(a\)\s*outward\s+taxable\s+supplies\s*\(other\s+than", 1, 0.8),
    ("gst_igst", r"\(a\)\s*outward\s+taxable\s+supplies\s*\(other\s+than", 2, 0.7),
    ("gst_cgst", r"\(a\)\s*outward\s+taxable\s+supplies\s*\(other\s+than", 3, 0.7),
    ("gst_sgst", r"\(a\)\s*outward\s+taxable\s+supplies\s*\(other\s+than", 4, 0.7),
    ("gst_itc", r"\(?c\)?\s*net\s+ITC\s+available", 1, 0.7),
]

ITR_LABELS = [
    ("itr_gross_total_income", r"gross\s+total\s+income", 0.8),
    ("itr_total_income", r"\btotal\s+income\b", 0.75),
    ("itr_tax_payable", r"(?:net\s+)?tax\s+payable", 0.7),
    ("itr_taxes_paid", r"taxes\s+paid", 0.7),
    ("itr_refund", r"refund(?:able)?", 0.5),
    ("itr_business_loss", r"current\s+year\s+(?:business\s+)?loss", 0.6),
]

BANK_LABELS = [
    ("bank_opening", r"opening\s+balance", 0.8),
    ("bank_closing", r"closing\s+balance", 0.8),
    ("bank_credits", r"(?:total\s+)?credits?\s*(?:amount|total)?", 0.5),
    ("bank_debits", r"(?:total\s+)?debits?\s*(?:amount|total)?", 0.5),
]


def extract_facts(kind: str, text: str, fy: str | None, period: str | None = None) -> list[dict]:
    if not text:
        return []
    out: list[dict] = []
    mult, note = scale_of(text)

    def add(metric: str, value: float | None, conf: float, per: str | None = None, extra: str = ""):
        if value is None:
            return
        out.append({"metric": metric, "value": round(value * mult, 2), "period": per or ("FY" if fy else ""),
                    "confidence": conf, "notes": " ".join(x for x in (note, extra) if x).strip()})

    if kind in ("financial-statements", "audit-report", "directors-report"):
        for metric, pat, conf in FIN_LABELS:
            add(metric, _first_amount_after(pat, text), conf)
    elif kind == "gstr-3b":
        for metric, pat, nth, conf in GST_LABELS:
            add(metric, _first_amount_after(pat, text, nth), conf, period)
        paid = _first_amount_after(r"tax\s+paid\s+in\s+cash|paid\s+through\s+cash", text)
        add("gst_tax_paid_cash", paid, 0.5, period)
        late = _first_amount_after(r"late\s+fee", text)
        add("gst_late_fee", late, 0.5, period)
    elif kind == "gstr-1":
        add("gst_taxable_value", _first_amount_after(r"total\s+taxable\s+value", text), 0.6, period)
    elif kind == "itr":
        for metric, pat, conf in ITR_LABELS:
            add(metric, _first_amount_after(pat, text), conf)
    elif kind == "bank-statement":
        for metric, pat, conf in BANK_LABELS:
            add(metric, _first_amount_after(pat, text), conf, period)
    elif kind == "trial-balance":
        add("tb_total", _first_amount_after(r"(?:grand\s+)?total", text), 0.4)
    elif kind == "amazon-report":
        out += amazon_csv_facts(text, period)
    return out


def amazon_csv_facts(text: str, period: str | None) -> list[dict]:
    """Amazon 'Payments → Date range report' / settlement CSV: sales total + order count."""
    try:
        rows = list(csv.DictReader(io.StringIO(text)))
    except csv.Error:
        return []
    if not rows:
        return []
    cols = {c.lower().strip(): c for c in rows[0].keys() if c}
    total_col = cols.get("total") or cols.get("amount")
    type_col = cols.get("type") or cols.get("amount-type") or cols.get("transaction-type")
    if not total_col:
        return []
    sales = 0.0
    orders = 0
    for r in rows:
        v = parse_amount(r.get(total_col) or "")
        if v is None:
            continue
        t = (r.get(type_col) or "").lower() if type_col else ""
        if not t or "order" in t or "principal" in t:
            sales += v
            orders += 1
    if not orders:
        return []
    return [
        {"metric": "amazon_sales", "value": round(sales, 2), "period": period or "", "confidence": 0.6, "notes": f"sum of '{total_col}' over {orders} order rows"},
        {"metric": "amazon_orders", "value": orders, "period": period or "", "confidence": 0.6, "notes": "rows with an order type"},
    ]
