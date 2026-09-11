"""Buzzcaf assistant — the virtual employee. Reads the mailbox, sorts the
inbox drop folder into the vault, extracts the numbers, keeps the compliance
calendar honest and writes the morning brief.

    python ops/assistant.py sort [--dry-run]        sort inbox/ into the vault + Ops
    python ops/assistant.py mail                    read new mail into Ops → Mail (attachments -> inbox/)
    python ops/assistant.py run                     mail + sort + print brief
    python ops/assistant.py brief [--send]          print (or e-mail) the brief
    python ops/assistant.py watch [--every 600]     run forever; brief e-mailed once a day at BRIEF_HOUR
    python ops/assistant.py test-mail               check IMAP login
    add --no-llm to force the rule-based path, --json for machine output
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import assistant, db, mail, paths, sorter  # noqa: E402


def _print_results(results) -> None:
    if not results:
        print("inbox empty — nothing to sort")
        return
    for r in results:
        r = r if isinstance(r, dict) else r.as_dict()
        line = f"{r['action']:12} {r['file']}"
        if r.get("kind"):
            line += f"  → {r['kind']} ({r['confidence']:.2f})"
        if r.get("dest"):
            line += f"  → vault/{r['dest']}"
        if r.get("doc_id"):
            line += f"  documents/{r['doc_id']}"
        if r.get("facts"):
            line += f"  +{r['facts']} facts"
        if r.get("compliance"):
            line += f"  [{r['compliance']}]"
        if r.get("note"):
            line += f"  ({r['note']})"
        print(line)


def main() -> None:
    for stream in (sys.stdout, sys.stderr):      # Windows consoles default to cp1252
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="buzzcaf-assistant", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true")
    common.add_argument("--no-llm", action="store_true", help="rules only, even if an API key exists")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sort", parents=[common]); s.add_argument("--dry-run", action="store_true")
    sub.add_parser("mail", parents=[common])
    sub.add_parser("run", parents=[common])
    b = sub.add_parser("brief", parents=[common]); b.add_argument("--send", action="store_true")
    w = sub.add_parser("watch", parents=[common]); w.add_argument("--every", type=int, default=600, help="seconds between passes")
    sub.add_parser("test-mail", parents=[common])
    a = ap.parse_args()
    use_llm = False if a.no_llm else None
    mail.load_env()
    con = db.connect()
    db.init_schema(con)

    if a.cmd == "sort":
        res = sorter.sort_inbox(con, dry_run=a.dry_run, use_llm=use_llm)
        print(json.dumps([r.as_dict() for r in res], indent=1, ensure_ascii=False)) if a.json else _print_results(res)
    elif a.cmd == "mail":
        if not mail.configured():
            sys.exit("mailbox not configured: copy ops/.env.example to ops/.env and fill MAIL_USER / MAIL_PASSWORD")
        rows = mail.fetch(con, use_llm=use_llm)
        if a.json:
            print(json.dumps(rows, indent=1, ensure_ascii=False, default=str))
        else:
            print(f"{len(rows)} new mail(s)")
            for m in rows:
                print(f"  [{m['importance']:6}] {m['category']:14} {m['received']}  {m['subject'][:70]}  <{m['sender'][:40]}>")
    elif a.cmd == "run":
        out = assistant.run_cycle(con, use_llm=use_llm)
        if a.json:
            out["brief"] = assistant.brief(con, use_llm=use_llm)
            print(json.dumps(out, indent=1, ensure_ascii=False, default=str))
        else:
            if out["mail_error"]:
                print("mail:", out["mail_error"])
            elif mail.configured():
                print(f"mail: {len(out['mail'])} new")
            else:
                print("mail: not configured (ops/.env)")
            _print_results(out["sorted"])
            print()
            print(assistant.brief(con, use_llm=use_llm))
    elif a.cmd == "brief":
        if a.send:
            ok = assistant.send_brief(con, use_llm=use_llm)
            print("sent" if ok else "not sent: mailbox not configured")
        else:
            print(assistant.brief(con, use_llm=use_llm))
    elif a.cmd == "test-mail":
        print(mail.test_connection())
    elif a.cmd == "watch":
        watch(con, every=a.every, use_llm=use_llm)


def watch(con, *, every: int = 600, use_llm: bool | None = None, stop=None) -> None:
    """Loop forever: cycle every `every` seconds; e-mail the brief once per day at BRIEF_HOUR."""
    import os
    brief_hour = int(os.environ.get("BRIEF_HOUR", "8"))
    print(f"assistant watching {paths.INBOX_DIR} every {every}s; brief at {brief_hour:02d}:00 "
          f"({'mail on' if mail.configured() else 'mail off'})")
    while True:
        if stop is not None and stop.is_set():
            return
        try:
            out = assistant.run_cycle(con, use_llm=use_llm)
            acted = [r for r in out["sorted"] if r["action"] not in ("skipped",)]
            if out["mail"] or acted or out["mail_error"]:
                print(f"[{datetime.now():%H:%M}] mail +{len(out['mail'])}"
                      + (f" ({out['mail_error']})" if out["mail_error"] else "") + f", sorted {len(acted)}")
                _print_results(acted)
            last_sent = db.meta_get(con, "brief_last_sent") or ""
            now = datetime.now()
            if now.hour >= brief_hour and not last_sent.startswith(date.today().isoformat()) and mail.configured():
                if assistant.send_brief(con, use_llm=use_llm):
                    print(f"[{now:%H:%M}] brief sent")
        except Exception as e:  # noqa: BLE001 - the watcher must survive a bad pass
            print(f"[{datetime.now():%H:%M}] pass failed: {type(e).__name__}: {e}")
        for _ in range(every):
            if stop is not None and stop.is_set():
                return
            time.sleep(1)


if __name__ == "__main__":
    main()
