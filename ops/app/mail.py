"""Read the company mailbox, understand each mail, save attachments to the
inbox for sorting, create tasks, and send the morning brief back.

Plain IMAP/SMTP so it works with Gmail (app password), Zoho, Outlook or any
host. Credentials come from ops/.env (see ops/.env.example); nothing is
stored in the database except what the mail said.

    from app import mail
    mail.load_env()
    new = mail.fetch(con)                  # new messages -> Ops → Mail (+ attachments -> inbox/)
    mail.send(subject, body)               # SMTP, to MAIL_BRIEF_TO (defaults to MAIL_USER)
"""
from __future__ import annotations

import email
import email.utils
import imaplib
import os
import re
import smtplib
from datetime import date, datetime, timedelta
from email.header import decode_header, make_header
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from . import classify, db, paths
from .specs import RESOURCES

ATTACH_EXT = {".pdf", ".xlsx", ".xls", ".csv", ".docx", ".doc", ".zip", ".json", ".txt", ".jpg", ".jpeg", ".png"}
CATEGORIES = RESOURCES["mail"].field("category").options or []

SENDER_RULES = [
    (r"gst\.gov\.in|gstn", "gst"), (r"mca\.gov\.in", "mca-roc"), (r"incometax|tdscpc|traces", "income-tax"),
    (r"fssai|foscos", "fssai"), (r"amazon\.(?:in|com)|sellercentral", "amazon"),
    (r"hdfcbank|icicibank|axisbank|sbi\.co\.in|kotak|yesbank|idfc", "bank"),
    (r"razorpay|cashfree|payu|phonepe|paytm", "payment-gateway"),
    (r"godaddy|namecheap|cloudflare|vercel|hostinger|bigrock|neon\.tech|google\.com", "domain-hosting"),
    (r"udyam|msme|mahagst|mahakamgar|ipindia|\.gov\.in", "government"),
]
SUBJECT_RULES = [
    (r"\bGSTR|\bGST\b|input tax credit|\bITC\b", "gst"),
    (r"\bAOC|\bMGT|\bROC\b|\bMCA\b|\bDIN\b|DIR-3|annual return|form ADT", "mca-roc"),
    (r"\bITR\b|income[- ]tax|\bTDS\b|26AS|assessment", "income-tax"),
    (r"FSSAI|FoSCoS|licen[cs]e", "fssai"),
    (r"balance sheet|audit|financial statement|trial balance|ledger|books of account", "ca-accounts"),
    (r"statement of account|account statement|\bIFSC\b|net ?banking|debit|credit card", "bank"),
    (r"settlement|FBA|seller central|listing|ASIN|buy box", "amazon"),
    (r"quotation|quote\b|\bMOQ\b|sample|proforma|purchase order|\bPO\b", "supplier"),
    (r"order #|your order|refund|complaint|delivery|tracking", "customer"),
    (r"razorpay|cashfree|payout|settlement", "payment-gateway"),
    (r"domain|DNS|SSL|hosting|renewal notice|deploy", "domain-hosting"),
    (r"legal notice|summons|show cause|demand notice|penalty", "legal-notice"),
    (r"unsubscribe|newsletter|webinar|% off|sale ends|limited offer|digest", "newsletter"),
]
NOISE = re.compile(r"unsubscribe|newsletter|webinar|% off|sale ends|limited offer|view in browser|promotional", re.I)
ACTION_WORDS = re.compile(r"please (?:pay|reply|confirm|submit|upload|share|send|sign|approve|review)|action required|"
                          r"due (?:date|on|by)|last date|deadline|expir(?:es|ing|y)|overdue|pending|reminder|"
                          r"respond within|within \d+ days|kindly (?:provide|share|send|confirm|sign|review|approve)|sign and (?:send|return)", re.I)


def load_env(path: Path | None = None) -> dict[str, str]:
    """Load KEY=VALUE lines from ops/.env into os.environ (without overriding). Returns what was read."""
    p = path or paths.ENV_FILE
    out: dict[str, str] = {}
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        out[k] = v
        os.environ.setdefault(k, v)
    return out


def configured() -> bool:
    load_env()
    return bool(os.environ.get("MAIL_USER") and os.environ.get("MAIL_PASSWORD"))


def _cfg(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# --------------------------------------------------------------- parsing ----
def _hdr(msg, name: str) -> str:
    raw = msg.get(name, "")
    try:
        return str(make_header(decode_header(raw)))
    except Exception:  # noqa: BLE001
        return raw


def _body(msg) -> str:
    plain, html = "", ""
    for part in msg.walk():
        ct = part.get_content_type()
        if part.get_content_disposition() == "attachment":
            continue
        try:
            payload = part.get_payload(decode=True)
        except Exception:  # noqa: BLE001
            continue
        if not payload:
            continue
        charset = part.get_content_charset() or "utf-8"
        txt = payload.decode(charset, errors="replace")
        if ct == "text/plain" and not plain:
            plain = txt
        elif ct == "text/html" and not html:
            html = txt
    if plain.strip():
        return plain
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<br\s*/?>|</p>|</div>|</tr>", "\n", html, flags=re.I)
    return re.sub(r"[ \t]+", " ", re.sub(r"<[^>]+>", " ", html))


def _safe(s: str, n: int = 60) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-.")
    return (s or "mail")[:n]


def _save_attachments(msg, received: date, subject: str) -> list[str]:
    saved: list[str] = []
    for part in msg.walk():
        if part.get_content_disposition() != "attachment":
            continue
        fn = part.get_filename()
        if not fn:
            continue
        try:
            fn = str(make_header(decode_header(fn)))
        except Exception:  # noqa: BLE001
            pass
        ext = Path(fn).suffix.lower()
        if ext not in ATTACH_EXT:
            continue
        data = part.get_payload(decode=True)
        if not data:
            continue
        paths.INBOX_DIR.mkdir(parents=True, exist_ok=True)
        dest = paths.INBOX_DIR / f"{received.isoformat()}-{_safe(Path(fn).stem)}{ext}"
        i = 1
        while dest.exists():
            dest = paths.INBOX_DIR / f"{received.isoformat()}-{_safe(Path(fn).stem)}-{i}{ext}"
            i += 1
        dest.write_bytes(data)
        saved.append(dest.name)
    return saved


# ---------------------------------------------------------- understanding ----
def understand(sender: str, subject: str, body: str, attachments: list[str]) -> dict[str, Any]:
    """Rule-based reading of one mail. The LLM (llm.py) may refine it."""
    low_sender = sender.lower()
    hay = subject + "\n" + body[:6000]
    category = "other"
    for pat, cat in SENDER_RULES:
        if re.search(pat, low_sender):
            category = cat
            break
    ca = [a.strip().lower() for a in _cfg("MAIL_CA_ADDRESSES").split(",") if a.strip()]
    if any(a and a in low_sender for a in ca):
        category = "ca-accounts"
    if category in ("other", "government", "domain-hosting"):
        for pat, cat in SUBJECT_RULES:
            if re.search(pat, hay, re.I):
                category = cat
                break
    noise = bool(NOISE.search(hay)) and category in ("other", "newsletter", "marketing", "domain-hosting")
    if noise:
        category = "newsletter"
    action = bool(ACTION_WORDS.search(hay))
    today = date.today()
    future = sorted(d for d in classify.find_dates(hay) if today <= d <= today + timedelta(days=120))
    due = future[0].isoformat() if future else None
    m = re.search(r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d+)?)", hay)
    amount = None
    if m:
        try:
            amount = float(m.group(1).replace(",", ""))
        except ValueError:
            amount = None
    if noise:
        importance = "ignore"
    elif category in ("legal-notice",) or (category in ("gst", "mca-roc", "income-tax", "fssai", "bank") and (action or due)):
        importance = "urgent" if re.search(r"penalty|show cause|final|last date|suspend|block|deactivat", hay, re.I) else "high"
    elif category in ("ca-accounts", "amazon", "payment-gateway", "supplier", "customer", "government") and (action or due or attachments):
        importance = "high" if action else "normal"
    elif category == "other":
        importance = "normal" if action else "low"
    else:
        importance = "normal"
    clean = re.sub(r"\s+", " ", body).strip()
    summary = clean[:320] + ("…" if len(clean) > 320 else "")
    action_needed = ""
    if action and importance not in ("ignore", "low"):
        sent = next((s for s in re.split(r"(?<=[.!?])\s+", clean) if ACTION_WORDS.search(s)), "")
        action_needed = sent[:240]
    if not action_needed and attachments and category in ("ca-accounts", "gst", "mca-roc", "income-tax", "fssai", "bank", "legal-notice"):
        action_needed = f"Review attachment(s): {', '.join(attachments)[:160]} (they are in the inbox for sorting)"
        importance = "high" if importance in ("normal", "low") else importance
    return {
        "category": category, "importance": importance, "summary": summary, "action_needed": action_needed,
        "due_date": due, "amount": amount,
        "create_task": importance in ("urgent", "high") and bool(action_needed or due),
        "task_title": f"Mail: {subject[:90]}",
    }


TASK_AREA = {"gst": "compliance", "mca-roc": "compliance", "income-tax": "compliance", "fssai": "compliance",
             "ca-accounts": "finance", "bank": "finance", "payment-gateway": "finance", "amazon": "amazon",
             "supplier": "supply", "customer": "other", "domain-hosting": "website", "legal-notice": "compliance",
             "government": "compliance"}


def record(con, meta: dict[str, Any], understanding: dict[str, Any], method: str) -> int:
    imp = understanding["importance"]
    task_id = None
    if understanding.get("create_task") and imp in ("urgent", "high"):
        task_id = db.insert(con, "tasks", {
            "title": understanding.get("task_title") or f"Mail: {meta['subject'][:90]}",
            "priority": "urgent" if imp == "urgent" else "high",
            "area": TASK_AREA.get(understanding["category"], "other"),
            "due_date": understanding.get("due_date") or "",
            "details": (understanding.get("action_needed") or understanding.get("summary") or "")[:1000]
                       + f"\n\nFrom: {meta['sender']} on {meta['received']}",
            "link": "",
        })
    row_id = db.insert(con, "mail", {
        **meta,
        "category": understanding["category"], "importance": imp,
        "summary": understanding.get("summary") or "", "action_needed": understanding.get("action_needed") or "",
        "due_date": understanding.get("due_date") or "", "amount": understanding.get("amount"),
        "task_id": task_id, "status": "ignored" if imp == "ignore" else "new", "method": method,
    })
    if task_id:
        db.update(con, "tasks", task_id, {"link": f"mail/{row_id}"})
    return row_id


# ------------------------------------------------------------------ IMAP ----
def fetch(con, *, limit: int = 60, since_days: int | None = None, use_llm: bool | None = None) -> list[dict[str, Any]]:
    """Pull new messages, understand them, store them. Returns the stored rows."""
    load_env()
    from . import llm
    host = _cfg("MAIL_IMAP_HOST", "imap.gmail.com")
    user, pw = _cfg("MAIL_USER"), _cfg("MAIL_PASSWORD")
    if not (user and pw):
        raise RuntimeError("MAIL_USER / MAIL_PASSWORD not set — see ops/.env.example")
    folder = _cfg("MAIL_FOLDER", "INBOX")
    days = since_days if since_days is not None else int(_cfg("MAIL_SINCE_DAYS", "14"))
    want_llm = llm.enabled() if use_llm is None else use_llm
    watch = [s.strip().lower() for s in _cfg("MAIL_WATCH_SENDERS").split(",") if s.strip()]

    known = {r[0] for r in con.execute("SELECT message_id FROM mail WHERE message_id IS NOT NULL")}
    stored: list[dict[str, Any]] = []
    M = imaplib.IMAP4_SSL(host, int(_cfg("MAIL_IMAP_PORT", "993")))
    try:
        M.login(user, pw)
        M.select(folder, readonly=True)
        since = (date.today() - timedelta(days=days)).strftime("%d-%b-%Y")
        typ, data = M.search(None, f'(SINCE "{since}")')
        uids = data[0].split() if typ == "OK" and data and data[0] else []
        for uid in reversed(uids[-400:]):
            if len(stored) >= limit:
                break
            typ, parts = M.fetch(uid, "(BODY.PEEK[])")
            if typ != "OK" or not parts or not isinstance(parts[0], tuple):
                continue
            msg = email.message_from_bytes(parts[0][1])
            mid = (msg.get("Message-ID") or "").strip()
            if mid and mid in known:
                continue
            sender = _hdr(msg, "From")
            if watch and not any(w in sender.lower() for w in watch):
                continue
            subject = _hdr(msg, "Subject") or "(no subject)"
            try:
                received = email.utils.parsedate_to_datetime(msg.get("Date", "")).date()
            except Exception:  # noqa: BLE001
                received = date.today()
            body = _body(msg)
            attachments = _save_attachments(msg, received, subject)
            u = understand(sender, subject, body, attachments)
            method = "rules"
            if want_llm and u["importance"] != "ignore":
                ans = llm.understand_mail(sender, subject, body, attachments, CATEGORIES)
                if ans and ans.get("category") in CATEGORIES:
                    u.update({k: ans.get(k) for k in ("category", "importance", "summary", "action_needed",
                                                      "due_date", "amount", "create_task", "task_title")})
                    method = "llm"
            meta = {"message_id": mid or f"uid:{uid.decode()}", "uid": uid.decode(), "received": received.isoformat(),
                    "sender": sender[:200], "subject": subject[:300], "attachments": ", ".join(attachments),
                    "body_excerpt": body[:4000]}
            row_id = record(con, meta, u, method)
            known.add(meta["message_id"])
            stored.append({**meta, **u, "id": row_id, "method": method})
    finally:
        try:
            M.logout()
        except Exception:  # noqa: BLE001
            pass
    return stored


def link_documents(con, sorted_results: list[dict[str, Any]]) -> None:
    """After the sorter ran, note on each mail which Documents its attachments became."""
    by_file = {r["file"]: r for r in sorted_results if r.get("doc_id")}
    if not by_file:
        return
    for m in db.list_rows(con, "mail", where="attachments != '' AND attachments IS NOT NULL", limit=300):
        names = [a.strip() for a in (m.get("attachments") or "").split(",") if a.strip()]
        ids = [f"documents/{by_file[n]['doc_id']}" for n in names if n in by_file]
        if ids:
            prev = m.get("documents") or ""
            merged = ", ".join(dict.fromkeys([*(x.strip() for x in prev.split(",") if x.strip()), *ids]))
            db.update(con, "mail", int(m["id"]), {"documents": merged})


# ------------------------------------------------------------------ SMTP ----
def send(subject: str, body: str, to: str | None = None, html: str | None = None) -> bool:
    load_env()
    user, pw = _cfg("MAIL_USER"), _cfg("MAIL_PASSWORD")
    if not (user and pw):
        return False
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to or _cfg("MAIL_BRIEF_TO") or user
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    host, port = _cfg("MAIL_SMTP_HOST", "smtp.gmail.com"), int(_cfg("MAIL_SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls()
        s.login(user, pw)
        s.send_message(msg)
    return True


def test_connection() -> str:
    load_env()
    if not configured():
        return "not configured: copy ops/.env.example to ops/.env and fill MAIL_USER / MAIL_PASSWORD"
    host = _cfg("MAIL_IMAP_HOST", "imap.gmail.com")
    M = imaplib.IMAP4_SSL(host, int(_cfg("MAIL_IMAP_PORT", "993")))
    try:
        M.login(_cfg("MAIL_USER"), _cfg("MAIL_PASSWORD"))
        typ, data = M.select(_cfg("MAIL_FOLDER", "INBOX"), readonly=True)
        n = data[0].decode() if data and data[0] else "?"
        return f"ok: {host} as {_cfg('MAIL_USER')}, folder {_cfg('MAIL_FOLDER', 'INBOX')} has {n} messages"
    finally:
        try:
            M.logout()
        except Exception:  # noqa: BLE001
            pass
