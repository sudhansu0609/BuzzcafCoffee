"""The assistant cycle: read mail → sort the inbox → write the brief.

    from app import assistant
    report = assistant.run_cycle(con)                 # one pass; returns what happened
    text   = assistant.brief(con)                     # today's brief as plain text
    assistant.send_brief(con)                         # e-mail it to MAIL_BRIEF_TO

Every step is optional and independent: no mailbox configured → mail is
skipped; no LLM → rule-based summaries; nothing in the inbox → nothing filed.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from . import db, mail, services, sorter


def run_cycle(con, *, use_llm: bool | None = None, fetch_mail: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {"at": db.now(), "mail": [], "mail_error": "", "sorted": [], "brief": ""}
    if fetch_mail and mail.configured():
        try:
            out["mail"] = mail.fetch(con, use_llm=use_llm)
        except Exception as e:  # noqa: BLE001 - keep going; the inbox can still be sorted
            out["mail_error"] = f"{type(e).__name__}: {e}"
    res = sorter.sort_inbox(con, use_llm=use_llm)
    out["sorted"] = [r.as_dict() for r in res]
    mail.link_documents(con, out["sorted"])
    db.meta_set(con, "assistant_last_cycle", json.dumps(
        {k: v for k, v in out.items() if k != "brief"}, ensure_ascii=False, default=str))
    return out


def last_cycle(con) -> dict[str, Any] | None:
    raw = db.meta_get(con, "assistant_last_cycle")
    return json.loads(raw) if raw else None


def context(con, today: date | None = None) -> dict[str, Any]:
    """Everything the brief is written from (also served at /api/brief)."""
    today = today or date.today()
    d = services.dashboard(con, today)
    since = (today - timedelta(days=1)).isoformat()
    new_mail = db.list_rows(con, "mail", where="status = 'new' AND importance IN ('urgent','high','normal')", limit=25)
    recent_mail = db.list_rows(con, "mail", where="received >= ? AND importance != 'ignore'", params=[since], limit=40)
    review = sorter.needs_review(con)
    lr = sorter.last_run(con) or {}
    filed = [r for r in lr.get("results", []) if r.get("action") == "filed"]
    return {
        "today": today.isoformat(),
        "overdue": [{"name": x["name"], "due": x["next_due"], "authority": x.get("authority")} for x in d["overdue"]],
        "due_soon": [{"name": x["name"], "due": x["next_due"]} for x in d["soon"]],
        "expired_documents": [{"title": x["title"], "expired": x.get("expiry_date")} for x in d["expired"]],
        "expiring_documents": [{"title": x["title"], "expiry": x.get("expiry_date"), "days": x.get("days_left")} for x in d["d30"]],
        "tasks_due": [{"title": t["title"], "priority": t["priority"], "due": t.get("due_date")} for t in d["tasks_due"]],
        "new_mail": [{"from": m["sender"], "subject": m["subject"], "category": m["category"], "importance": m["importance"],
                      "summary": m.get("summary"), "action": m.get("action_needed"), "due": m.get("due_date")} for m in new_mail],
        "mail_last_24h": len(recent_mail),
        "filed_last_run": [{"file": r["file"], "kind": r["kind"], "dest": r["dest"], "facts": r.get("facts", 0),
                            "compliance": r.get("compliance")} for r in filed],
        "needs_review": [{"title": x["title"], "id": x["id"]} for x in review],
        "open_complaints": len(d["open_complaints"]),
        "inbox_pending": [p.name for p in sorter.pending_files()],
    }


def brief(con, *, use_llm: bool | None = None, today: date | None = None) -> str:
    from . import llm
    ctx = context(con, today)
    want = llm.enabled() if use_llm is None else use_llm
    if want:
        text = llm.write_brief(ctx)
        if text:
            return text
    return plain_brief(ctx)


def plain_brief(c: dict[str, Any]) -> str:
    lines = [f"Buzzcaf brief for {c['today']}", ""]
    if c["overdue"]:
        lines.append(f"{len(c['overdue'])} statutory items are overdue: " + "; ".join(f"{x['name']} (was due {x['due']})" for x in c["overdue"][:6]) + ".")
    if c["expired_documents"]:
        lines.append("Expired documents: " + "; ".join(x["title"] for x in c["expired_documents"][:5]) + ".")
    if c["due_soon"]:
        lines.append("Due in the next 30 days: " + "; ".join(f"{x['name']} on {x['due']}" for x in c["due_soon"][:6]) + ".")
    if c["expiring_documents"]:
        lines.append("Expiring within 30 days: " + "; ".join(f"{x['title']} ({x['days']} d)" for x in c["expiring_documents"]) + ".")
    lines.append("")
    if c["new_mail"]:
        lines.append(f"Mail needing attention ({len(c['new_mail'])}):")
        for m in c["new_mail"][:12]:
            extra = f" Deadline {m['due']}." if m.get("due") else ""
            act = f" → {m['action']}" if m.get("action") else ""
            lines.append(f"- [{m['importance']}] {m['subject']} — from {m['from']}. {m.get('summary') or ''}{extra}{act}")
    else:
        lines.append("No new mail needs attention." if c["mail_last_24h"] == 0 else f"{c['mail_last_24h']} mails in the last day, none need action.")
    lines.append("")
    if c["filed_last_run"]:
        lines.append(f"Filed automatically ({len(c['filed_last_run'])}):")
        for r in c["filed_last_run"][:12]:
            bits = [f"{r['file']} → {r['dest']} ({r['kind']})"]
            if r.get("facts"):
                bits.append(f"{r['facts']} numbers extracted")
            if r.get("compliance"):
                bits.append(r["compliance"])
            lines.append("- " + "; ".join(bits))
    if c["needs_review"]:
        lines.append(f"Needs your eye ({len(c['needs_review'])}): " + "; ".join(x["title"] for x in c["needs_review"][:8]) + ".")
    if c["inbox_pending"]:
        lines.append("Still in the inbox (not yet settled or unreadable): " + ", ".join(c["inbox_pending"][:8]) + ".")
    lines.append("")
    if c["tasks_due"]:
        lines.append("Tasks due: " + "; ".join(f"{t['title']} ({t['priority']}, {t.get('due') or 'no date'})" for t in c["tasks_due"][:8]) + ".")
    if c["open_complaints"]:
        lines.append(f"Open complaints: {c['open_complaints']}.")
    return "\n".join(lines).strip() + "\n"


def send_brief(con, *, use_llm: bool | None = None) -> bool:
    text = brief(con, use_llm=use_llm)
    ok = mail.send(f"Buzzcaf brief — {date.today().isoformat()}", text)
    if ok:
        db.meta_set(con, "brief_last_sent", db.now())
    return ok
