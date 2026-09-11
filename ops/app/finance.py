"""Finance dashboard data: what the filed documents say, per financial year.

    finance.overview(con) -> {
        "years": ["2022-23", ...],
        "matrix": [{"fy": ..., "cells": {"financial-statements": {...}, ...}}],   # filing status per FY
        "kpis": {"2024-25": {"revenue": {...}, "pat": {...}, ...}},                # latest fact per metric
        "gst_months": [{"period": "2026-09", "taxable": .., "tax": .., "itc": ..}],
        "bank": [...], "series": {...}, "needs_review": [...], "docs_by_fy": {...}
    }
"""
from __future__ import annotations

from datetime import date
from typing import Any

from . import db

FILINGS = [
    ("financial-statements", "Financial statements"),
    ("audit-report", "Audit report"),
    ("aoc-4", "AOC-4"),
    ("mgt-7a", "MGT-7A"),
    ("dir-3-kyc", "DIR-3 KYC"),
    ("itr", "ITR"),
    ("gstr-3b", "GSTR-3B"),
    ("gstr-1", "GSTR-1"),
    ("bank-statement", "Bank statements"),
]
MONTHLY = {"gstr-3b", "gstr-1", "bank-statement"}
KPI_METRICS = ["revenue", "total_income", "total_expenses", "pbt", "pat", "total_assets", "equity", "cash",
               "itr_total_income", "itr_tax_payable", "gst_taxable_value", "gst_itc", "gst_late_fee"]
KPI_LABELS = {
    "revenue": "Revenue from operations", "total_income": "Total income", "total_expenses": "Total expenses",
    "pbt": "Profit / loss before tax", "pat": "Profit / loss after tax", "total_assets": "Total assets",
    "equity": "Equity", "cash": "Cash at year end", "itr_total_income": "ITR total income",
    "itr_tax_payable": "ITR tax payable", "gst_taxable_value": "GST taxable turnover (sum of months)",
    "gst_itc": "GST input credit (sum of months)", "gst_late_fee": "GST late fees (sum of months)",
}
SUMMED = {"gst_taxable_value", "gst_itc", "gst_late_fee", "gst_tax_paid_cash", "amazon_sales", "amazon_orders"}


def current_fy(today: date | None = None) -> str:
    t = today or date.today()
    y = t.year if t.month >= 4 else t.year - 1
    return f"{y}-{(y + 1) % 100:02d}"


def years(con, first: str = "2022-23") -> list[str]:
    ys = {first, current_fy()}
    for r in con.execute("SELECT DISTINCT fy FROM facts WHERE fy != ''"):
        ys.add(r[0])
    for r in con.execute("SELECT tags FROM documents WHERE tags LIKE '%fy20%'"):
        for t in (r[0] or "").split(","):
            t = t.strip().lower()
            if t.startswith("fy20") and len(t) == 9:
                ys.add(t[2:])
    start = int(first[:4])
    end = int(current_fy()[:4])
    return [f"{y}-{(y + 1) % 100:02d}" for y in range(start, end + 1)] + sorted(y for y in ys if not (start <= int(y[:4]) <= end))


def _docs_with_kind(con) -> list[dict]:
    rows = db.list_rows(con, "documents", where="tags LIKE '%fy20%' OR file_path LIKE '13-accounts-and-audit/%'", limit=2000)
    out = []
    for r in rows:
        tags = [t.strip().lower() for t in (r.get("tags") or "").split(",")]
        fy = next((t[2:] for t in tags if t.startswith("fy20") and len(t) == 9), None)
        kind = next((t for t in tags if t in {k for k, _ in FILINGS} or t in ("trial-balance", "ledger", "form-26as", "adt-1", "minutes-agm", "ca-report", "invoice", "fee-invoice", "pt-return", "tds-26q", "tds-24q")), None)
        if not kind:
            # fall back on doc_type
            kind = {"financial-statements": "financial-statements", "audit-report": "audit-report", "itr": "itr",
                    "bank-statement": "bank-statement"}.get(r.get("doc_type") or "")
        out.append({**r, "fy": fy, "kind": kind})
    return out


def matrix(con, ys: list[str]) -> list[dict[str, Any]]:
    docs = _docs_with_kind(con)
    rows = []
    for fy in ys:
        cells: dict[str, Any] = {}
        for kind, label in FILINGS:
            mine = [d for d in docs if d["fy"] == fy and d["kind"] == kind]
            if kind in MONTHLY:
                periods = set()
                for d in mine:
                    fp = d.get("file_path") or ""
                    import re
                    m = re.search(r"(20\d\d-\d\d)-20\d\d-\d\d-\d\d", fp)
                    if m:
                        periods.add(m.group(1))
                cells[kind] = {"label": label, "count": len(mine), "months": len(periods) if periods else len(mine),
                               "state": "done" if len(periods or mine) >= 12 else ("partial" if mine else "missing"),
                               "ids": [d["id"] for d in mine][:12]}
            else:
                cells[kind] = {"label": label, "count": len(mine), "state": "done" if mine else "missing",
                               "ids": [d["id"] for d in mine][:5], "number": (mine[0].get("number") if mine else "")}
        rows.append({"fy": fy, "cells": cells, "docs": len([d for d in docs if d["fy"] == fy])})
    return rows


def facts_by_fy(con) -> dict[str, dict[str, Any]]:
    """Latest manual/best fact per metric per FY (summing monthly metrics)."""
    out: dict[str, dict[str, Any]] = {}
    rows = db.list_rows(con, "facts", limit=5000)
    for r in rows:
        fy, metric = r.get("fy") or "", r.get("metric") or ""
        if not fy or not metric:
            continue
        slot = out.setdefault(fy, {})
        if metric in SUMMED:
            cur = slot.setdefault(metric, {"value": 0.0, "n": 0, "confidence": 1.0, "sources": set(), "method": r["method"]})
            cur["value"] += float(r["value"] or 0)
            cur["n"] += 1
            cur["confidence"] = min(cur["confidence"], float(r.get("confidence") or 0))
            if r.get("source_id"):
                cur["sources"].add(int(r["source_id"]))
        else:
            prev = slot.get(metric)
            better = prev is None or (r["method"] == "manual" and prev["method"] != "manual") or \
                (prev["method"] != "manual" and float(r.get("confidence") or 0) > prev["confidence"])
            if better:
                slot[metric] = {"value": float(r["value"] or 0), "n": 1, "confidence": float(r.get("confidence") or 0),
                                "sources": {int(r["source_id"])} if r.get("source_id") else set(), "method": r["method"]}
    for fy in out.values():
        for m in fy.values():
            m["sources"] = sorted(m["sources"])
    return out


def gst_months(con) -> list[dict[str, Any]]:
    rows = db.list_rows(con, "facts", where="metric LIKE 'gst_%' AND period LIKE '20__-__'", limit=2000)
    by: dict[str, dict[str, Any]] = {}
    for r in rows:
        p = by.setdefault(r["period"], {"period": r["period"], "fy": r["fy"], "taxable": None, "tax": 0.0, "itc": None, "late_fee": None, "source_id": r.get("source_id")})
        m, v = r["metric"], float(r["value"] or 0)
        if m == "gst_taxable_value":
            p["taxable"] = v
        elif m in ("gst_igst", "gst_cgst", "gst_sgst"):
            p["tax"] += v
        elif m == "gst_itc":
            p["itc"] = v
        elif m == "gst_late_fee":
            p["late_fee"] = v
    return sorted(by.values(), key=lambda x: x["period"])


def bank_months(con) -> list[dict[str, Any]]:
    rows = db.list_rows(con, "facts", where="metric IN ('bank_opening','bank_closing','bank_credits','bank_debits')", limit=2000)
    by: dict[str, dict[str, Any]] = {}
    for r in rows:
        key = r.get("period") or r.get("fy") or ""
        p = by.setdefault(key, {"period": key, "fy": r["fy"], "opening": None, "closing": None, "credits": None, "debits": None, "source_id": r.get("source_id")})
        p[{"bank_opening": "opening", "bank_closing": "closing", "bank_credits": "credits", "bank_debits": "debits"}[r["metric"]]] = float(r["value"] or 0)
    return sorted(by.values(), key=lambda x: x["period"])


def overview(con) -> dict[str, Any]:
    ys = years(con)
    kp = facts_by_fy(con)
    series = {}
    for metric in ("revenue", "total_expenses", "pat", "cash", "gst_taxable_value"):
        pts = [{"fy": fy, "value": kp.get(fy, {}).get(metric, {}).get("value")} for fy in ys]
        if any(p["value"] is not None for p in pts):
            series[metric] = pts
    review = db.list_rows(con, "documents", where="tags LIKE '%needs-review%' AND status = 'pending'", limit=50)
    docs_by_fy = {}
    for row in matrix(con, ys):
        docs_by_fy[row["fy"]] = row["docs"]
    return {
        "years": ys, "current_fy": current_fy(), "matrix": matrix(con, ys), "kpis": kp,
        "kpi_metrics": KPI_METRICS, "kpi_labels": KPI_LABELS, "series": series,
        "gst_months": gst_months(con), "bank": bank_months(con), "needs_review": review, "docs_by_fy": docs_by_fy,
        "facts_total": db.count(con, "facts"),
    }
