"""Buzzcaf Ops CLI — for cron jobs, Dexter, or a quick terminal check.

    python ops/cli.py expiring --days 60     documents expiring/expired
    python ops/cli.py due [--days 30]        compliance obligations due/overdue
    python ops/cli.py tasks                  open tasks
    python ops/cli.py complaints             open complaints + batch patterns
    python ops/cli.py summary                everything, short
    add --json to any command for machine output
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import db, services  # noqa: E402


def table(rows: list[dict], cols: list[str]) -> str:
    if not rows:
        return "  (none)"
    widths = {c: max(len(c), *(len(str(r.get(c) or "")) for r in rows)) for c in cols}
    line = "  " + "  ".join(c.upper().ljust(widths[c]) for c in cols)
    out = [line, "  " + "-" * (len(line) - 2)]
    for r in rows:
        out.append("  " + "  ".join(str(r.get(c) or "").ljust(widths[c]) for c in cols))
    return "\n".join(out)


def cmd_expiring(con, days: int) -> list[dict]:
    today = date.today()
    services.auto_expire_documents(con, today)
    b = services.document_expiry(con, today)
    rows = [dict(x, bucket="EXPIRED") for x in b.expired]
    for x in b.d30 + b.d60 + b.d90:
        if x["days_left"] <= days:
            rows.append(dict(x, bucket=f"{x['days_left']}d"))
    return [{"id": r["id"], "bucket": r["bucket"], "title": r["title"], "number": r.get("number"), "expiry": r.get("expiry_date")} for r in rows]


def cmd_due(con, days: int) -> list[dict]:
    today = date.today()
    services.refresh_compliance(con, today)
    horizon = (today + timedelta(days=days)).isoformat()
    rows = db.list_rows(con, "compliance", where="status='active' AND next_due IS NOT NULL AND next_due <= ?", params=[horizon])
    return [{"id": r["id"], "state": "OVERDUE" if r["next_due"] < today.isoformat() else "due",
             "next_due": r["next_due"], "name": r["name"], "authority": r.get("authority"), "cost": r.get("cost_estimate")} for r in rows]


def cmd_tasks(con) -> list[dict]:
    rows = db.list_rows(con, "tasks", where="status IN ('todo','doing')")
    return [{"id": r["id"], "priority": r["priority"], "due": r.get("due_date"), "status": r["status"], "title": r["title"]} for r in rows]


def cmd_complaints(con) -> dict:
    rows = db.list_rows(con, "complaints", where="resolved = 0")
    return {"open": [{"id": r["id"], "date": r["date"], "batch": r.get("batch_no"), "issue": r["issue"], "summary": r["summary"]} for r in rows],
            "patterns": services.complaint_patterns(con)}


def main() -> None:
    ap = argparse.ArgumentParser(prog="buzzcaf-ops")
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("expiring"); e.add_argument("--days", type=int, default=90)
    d = sub.add_parser("due"); d.add_argument("--days", type=int, default=30)
    sub.add_parser("tasks"); sub.add_parser("complaints"); sub.add_parser("summary")
    a = ap.parse_args()
    con = db.connect()
    db.init_schema(con)
    if a.cmd == "expiring":
        rows = cmd_expiring(con, a.days)
        print(json.dumps(rows, indent=1) if a.json else f"Documents expired / expiring within {a.days} days:\n" + table(rows, ["bucket", "title", "number", "expiry"]))
    elif a.cmd == "due":
        rows = cmd_due(con, a.days)
        print(json.dumps(rows, indent=1) if a.json else f"Compliance due within {a.days} days:\n" + table(rows, ["state", "next_due", "name", "authority", "cost"]))
    elif a.cmd == "tasks":
        rows = cmd_tasks(con)
        print(json.dumps(rows, indent=1) if a.json else "Open tasks:\n" + table(rows, ["priority", "due", "status", "title"]))
    elif a.cmd == "complaints":
        res = cmd_complaints(con)
        print(json.dumps(res, indent=1) if a.json else "Open complaints:\n" + table(res["open"], ["date", "batch", "issue", "summary"]) + "\nPatterns (>=3 on one batch):\n" + table(res["patterns"], ["batch_no", "n", "issues"]))
    else:
        res = {"expiring": cmd_expiring(con, 90), "due": cmd_due(con, 30), "tasks": cmd_tasks(con), "complaints": cmd_complaints(con)}
        if a.json:
            print(json.dumps(res, indent=1))
        else:
            print(f"BUZZCAF OPS SUMMARY — {date.today()}")
            print("\nDocuments (expired / ≤90d):\n" + table(res["expiring"], ["bucket", "title", "expiry"]))
            print("\nCompliance (≤30d):\n" + table(res["due"], ["state", "next_due", "name"]))
            print("\nOpen tasks:\n" + table(res["tasks"][:12], ["priority", "due", "title"]))
            print("\nOpen complaints:\n" + table(res["complaints"]["open"], ["date", "batch", "issue", "summary"]))
    con.close()


if __name__ == "__main__":
    main()
