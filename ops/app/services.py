"""Module-specific logic: compliance next-due, document expiry buckets,
complaint patterns, batch health, SOP loading, dashboard aggregation."""
from __future__ import annotations

import json
import re
import sqlite3
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from . import db, paths

# ---------------------------------------------------------------- dates -----

def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _clamp(y: int, m: int, d: int) -> date:
    return date(y, m, min(d, monthrange(y, m)[1]))


def next_due(rule: dict[str, Any] | str | None, after: date, last_done: date | None = None) -> date | None:
    """Compute the next due date for a compliance rule.

    The result is the first occurrence strictly after ``last_done`` (if any)
    and not before ``after`` (normally today) — except that overdue items are
    reported as overdue: if the last occurrence before ``after`` was never
    marked done, that past date is returned.
    """
    if not rule:
        return None
    if isinstance(rule, str):
        try:
            rule = json.loads(rule)
        except json.JSONDecodeError:
            return None
    t = rule.get("type")
    floor = after
    if last_done and last_done >= after:
        floor = last_done + timedelta(days=1)

    if t == "once":
        d = parse_date(rule.get("date"))
        if d is None:
            return None
        if last_done and last_done >= d:
            return None
        return d
    if t == "relative":
        anchor = parse_date(rule.get("anchor"))
        if anchor is None:
            return None
        d = anchor + timedelta(days=int(rule.get("days", 0)))
        if last_done and last_done >= d:
            return None
        return d
    if t == "monthly":
        day = int(rule.get("day", 1))
        # candidate this month, previous month (for overdue), next months
        y, m = floor.year, floor.month
        prev = _clamp(y - (1 if m == 1 else 0), 12 if m == 1 else m - 1, day)
        if prev < after and (last_done is None or last_done < prev):
            return prev
        for _ in range(3):
            cand = _clamp(y, m, day)
            if cand >= floor:
                return cand
            m += 1
            if m > 12:
                m, y = 1, y + 1
        return None
    if t in ("annual", "quarterly", "multi"):
        dates = rule.get("dates") or []
        occ: list[date] = []
        for y in (floor.year - 1, floor.year, floor.year + 1):
            for md in dates:
                occ.append(_clamp(y, int(md[0]), int(md[1])))
        occ.sort()
        past = [d for d in occ if d < after]
        if past:
            last_occ = past[-1]
            if last_done is None or last_done < last_occ:
                # never done for the last period -> overdue
                if (after - last_occ).days <= int(rule.get("grace_days", 400)):
                    return last_occ
        for d in occ:
            if d >= floor:
                return d
        return None
    if t == "yearly_from":
        # every N years from an anchor date (trademark renewals)
        anchor = parse_date(rule.get("anchor"))
        n = int(rule.get("years", 10))
        if anchor is None:
            return None
        d = anchor
        while d < floor:
            d = _clamp(d.year + n, d.month, d.day)
        return d
    return None


def refresh_compliance(con: sqlite3.Connection, today: date | None = None) -> None:
    today = today or date.today()
    for row in db.list_rows(con, "compliance"):
        nd = next_due(row.get("rule"), today, parse_date(row.get("last_done")))
        val = nd.isoformat() if nd else None
        if val != row.get("next_due"):
            con.execute("UPDATE compliance SET next_due = ? WHERE id = ?", (val, row["id"]))
    con.commit()


def mark_done(con: sqlite3.Connection, obligation_id: int, done_on: date, note: str = "", period: str = "") -> None:
    con.execute(
        "INSERT INTO compliance_log (obligation_id, done_on, period, note, created_at) VALUES (?,?,?,?,?)",
        (obligation_id, done_on.isoformat(), period, note, db.now()),
    )
    con.execute("UPDATE compliance SET last_done = ?, updated_at = ? WHERE id = ?",
                (done_on.isoformat(), db.now(), obligation_id))
    con.commit()
    refresh_compliance(con)


def compliance_log(con: sqlite3.Connection, obligation_id: int) -> list[dict[str, Any]]:
    rows = con.execute("SELECT * FROM compliance_log WHERE obligation_id = ? ORDER BY done_on DESC", (obligation_id,))
    return [dict(r) for r in rows.fetchall()]


# ------------------------------------------------------------ documents -----

@dataclass
class ExpiryBuckets:
    expired: list[dict[str, Any]]
    d30: list[dict[str, Any]]
    d60: list[dict[str, Any]]
    d90: list[dict[str, Any]]


def document_expiry(con: sqlite3.Connection, today: date | None = None) -> ExpiryBuckets:
    today = today or date.today()
    b = ExpiryBuckets([], [], [], [])
    for d in db.list_rows(con, "documents", where="status != 'na'"):
        exp = parse_date(d.get("expiry_date"))
        if exp is None:
            if d.get("status") == "expired":
                b.expired.append(d)
            continue
        days = (exp - today).days
        d["days_left"] = days
        if days < 0 or d.get("status") == "expired":
            b.expired.append(d)
        elif days <= 30:
            b.d30.append(d)
        elif days <= 60:
            b.d60.append(d)
        elif days <= 90:
            b.d90.append(d)
    return b


def auto_expire_documents(con: sqlite3.Connection, today: date | None = None) -> int:
    today = today or date.today()
    n = 0
    for d in db.list_rows(con, "documents", where="status = 'valid' AND expiry_date IS NOT NULL"):
        exp = parse_date(d.get("expiry_date"))
        if exp and exp < today:
            con.execute("UPDATE documents SET status = 'expired' WHERE id = ?", (d["id"],))
            n += 1
    con.commit()
    return n


# ----------------------------------------------------------- complaints -----

def complaint_patterns(con: sqlite3.Connection, threshold: int = 3) -> list[dict[str, Any]]:
    rows = con.execute(
        "SELECT batch_no, COUNT(*) AS n, SUM(CASE WHEN resolved=1 THEN 0 ELSE 1 END) AS open_n, "
        "GROUP_CONCAT(DISTINCT issue) AS issues FROM complaints "
        "WHERE batch_no IS NOT NULL AND batch_no != '' AND lower(batch_no) != 'unknown' AND issue != 'praise' "
        "GROUP BY batch_no HAVING n >= ? ORDER BY n DESC", (threshold,)
    ).fetchall()
    return [dict(r) for r in rows]


# -------------------------------------------------------------- batches -----

CHECKS = ["chk_paperwork", "chk_sensory", "chk_label", "chk_fill_seal", "chk_retention", "chk_logged"]


def batch_health(con: sqlite3.Connection) -> list[dict[str, Any]]:
    out = []
    for b in db.list_rows(con, "batches"):
        missing = [c for c in CHECKS if not b.get(c)]
        if b.get("qc_result") in ("fail", "quarantine") or (missing and b.get("qc_result") != "pass"):
            b["missing_checks"] = len(missing)
            out.append(b)
    return out


# ------------------------------------------------------------------ SOPs -----

_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def load_sops() -> list[dict[str, Any]]:
    sops = []
    for p in sorted(paths.SOP_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        meta: dict[str, str] = {}
        m = _FM.match(text)
        body = text
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')
            body = text[m.end():]
        title = meta.get("title") or next((l[2:] for l in body.splitlines() if l.startswith("# ")), p.stem)
        sops.append({"slug": p.stem, "title": title, "version": meta.get("version", "1.0"),
                     "last_reviewed": meta.get("last_reviewed", ""), "owner": meta.get("owner", ""),
                     "summary": meta.get("summary", ""), "body": body, "path": str(p)})
    return sops


def get_sop(slug: str) -> dict[str, Any] | None:
    for s in load_sops():
        if s["slug"] == slug:
            return s
    return None


# ------------------------------------------------------------ dashboard -----

def dashboard(con: sqlite3.Connection, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    auto_expire_documents(con, today)
    refresh_compliance(con, today)
    exp = document_expiry(con, today)
    comp = db.list_rows(con, "compliance", where="status = 'active' AND next_due IS NOT NULL")
    overdue = [c for c in comp if parse_date(c["next_due"]) and parse_date(c["next_due"]) < today]
    soon = [c for c in comp if parse_date(c["next_due"]) and today <= parse_date(c["next_due"]) <= today + timedelta(days=30)]
    tasks_due = db.list_rows(con, "tasks", where="status IN ('todo','doing') AND (due_date IS NULL OR due_date <= ?)",
                             params=[(today + timedelta(days=14)).isoformat()], limit=15)
    open_complaints = db.list_rows(con, "complaints", where="resolved = 0", limit=10)
    return {
        "today": today,
        "expired": exp.expired, "d30": exp.d30, "d60": exp.d60, "d90": exp.d90,
        "overdue": overdue, "soon": soon,
        "tasks_due": tasks_due,
        "open_complaints": open_complaints,
        "patterns": complaint_patterns(con),
        "batch_issues": batch_health(con),
        "counts": {k: db.count(con, k) for k in ("documents", "suppliers", "batches", "complaints", "tasks", "contacts")},
        "sops": len(load_sops()),
    }
