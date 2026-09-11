"""The inbox sorter: everything dropped in `inbox/` gets read, classified,
renamed, filed in the vault, registered in Ops → Documents, mined for numbers
(→ Finance data) and, when it proves a statutory filing, ticked off in the
compliance calendar.

    from app import sorter
    results = sorter.sort_inbox(con)            # one pass
    sorter.sort_inbox(con, dry_run=True)        # only say what would happen

Unsure files (confidence below THRESHOLD) still leave the inbox: they go to
vault/12-uploads/needs-review/ with a pending Documents row so nothing is lost
and the dashboard shows them under "needs review".
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from . import classify, db, extract, paths, services

THRESHOLD = 0.6
LLM_THRESHOLD = 0.75          # rules below this -> ask the LLM if available
SKIP_NAMES = {"readme.md", "desktop.ini", "thumbs.db", ".ds_store"}
SETTLE_SECONDS = 3            # a file still being written is left for the next pass

# document kind -> compliance obligation name (seed.py) it proves
PROVES = {
    "gstr-1": "GSTR-1 (outward supplies)",
    "gstr-3b": "GSTR-3B (summary + payment)",
    "gstr-9": "GSTR-9 annual return",
    "aoc-4": "AOC-4 (financial statements)",
    "mgt-7a": "MGT-7A (annual return, small company)",
    "dir-3-kyc": "DIR-3 KYC (both directors)",
    "adt-1": "ADT-1 (auditor appointment)",
    "itr": "Company income-tax return",
    "minutes-agm": "Annual General Meeting",
    "tds-26q": "TDS returns (24Q/26Q) — if TDS deducted",
    "tds-24q": "TDS returns (24Q/26Q) — if TDS deducted",
    "pt-return": "Professional Tax (PTEC) annual payment",
}


@dataclass
class Result:
    file: str
    action: str = ""            # filed | review | duplicate | skipped | error | would-file | would-review
    kind: str = ""
    dest: str = ""
    doc_id: int | None = None
    confidence: float = 0.0
    fy: str | None = None
    facts: int = 0
    compliance: str = ""
    note: str = ""
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def _intake():
    """intake.py lives one level up (ops/); import lazily to avoid a cycle."""
    ops_root = str(paths.OPS_ROOT)
    if ops_root not in sys.path:
        sys.path.insert(0, ops_root)
    import intake  # noqa: WPS433
    return intake


def pending_files(inbox: Path | None = None) -> list[Path]:
    inbox = inbox or paths.INBOX_DIR
    if not inbox.exists():
        return []
    out = []
    for p in sorted(inbox.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(inbox).as_posix()
        if rel.startswith(("needs-review/", "duplicates/", "_")) or p.name.lower() in SKIP_NAMES:
            continue
        if p.name.startswith((".", "~$")) or p.suffix.lower() in (".part", ".crdownload", ".tmp"):
            continue
        out.append(p)
    return out


def _settled(p: Path) -> bool:
    try:
        return time.time() - p.stat().st_mtime >= SETTLE_SECONDS
    except OSError:
        return False


def _existing_by_hash(con, digest: str) -> dict | None:
    return db.find_one(con, "documents", "sha256 = ?", [digest])


def _prove_compliance(con, kind: str, when: str, doc_id: int, fy: str | None) -> str:
    name = PROVES.get(kind)
    if not name:
        return ""
    ob = db.find_one(con, "compliance", "name = ?", [name])
    if not ob:
        return ""
    done_on = services.parse_date(when) or date.today()
    last = services.parse_date(ob.get("last_done"))
    if last and last >= done_on:
        return f"{name}: already marked done on {last.isoformat()}"
    services.mark_done(con, int(ob["id"]), done_on, note=f"auto: documents/{doc_id}", period=fy or "")
    return f"{name}: marked done {done_on.isoformat()}"


def _store_facts(con, doc_id: int, fy: str | None, facts: list[dict], method: str) -> int:
    n = 0
    for f in facts:
        if fy is None and not f.get("period"):
            continue
        # replace an earlier auto fact for the same key from the same source
        con.execute("DELETE FROM facts WHERE source_id = ? AND metric = ? AND period = ? AND method != 'manual'",
                    (doc_id, f["metric"], f.get("period") or ""))
        db.insert(con, "facts", {
            "fy": fy or "", "period": f.get("period") or "", "metric": f["metric"], "value": f["value"],
            "unit": "INR" if not f["metric"].endswith("_orders") else "count", "source_id": doc_id,
            "confidence": f.get("confidence", 0.5), "method": method, "notes": f.get("notes", ""),
        })
        n += 1
    return n


def sort_one(con, path: Path, *, dry_run: bool = False, use_llm: bool | None = None) -> Result:
    intake = _intake()
    from . import llm
    res = Result(file=path.name)
    try:
        digest = classify.sha256_of(path)
        dup = _existing_by_hash(con, digest)
        if dup:
            res.action, res.doc_id, res.note = "duplicate", int(dup["id"]), f"same content as documents/{dup['id']} ({dup['file_path']})"
            if not dry_run:
                dest_dir = paths.INBOX_DIR / "duplicates"
                dest_dir.mkdir(parents=True, exist_ok=True)
                path.replace(intake.unique(dest_dir / path.name))
            return res

        text = classify.extract_text(path)
        g = classify.classify(path, text)
        method = "auto"
        want_llm = llm.enabled() if use_llm is None else use_llm
        if want_llm and g.confidence < LLM_THRESHOLD:
            kinds = sorted(set(intake.KINDS) | set(classify.KIND_ALIASES))
            ans = llm.classify_document(path.name, text, kinds)
            if ans and ans.get("kind") in kinds:
                g.kind = ans["kind"]
                g.fy = ans.get("fy") or g.fy
                g.period = ans.get("period") or g.period
                g.when = ans.get("date") or g.when
                g.number = ans.get("number") or g.number
                g.expiry = ans.get("expiry") or g.expiry
                g.title = ans.get("title") or g.title
                g.confidence = max(g.confidence, float(ans.get("confidence") or 0))
                g.folder = dict((k, f) for k, f, _, _ in classify.RULES).get(g.kind)
                g.reasons.append("llm: " + (ans.get("why") or "")[:160])
                method = "llm"
        res.kind, res.confidence, res.fy, res.reasons = g.kind, g.confidence, g.fy, g.reasons
        when = g.when or date.today().isoformat()

        # resolve classify-only kinds to intake kinds + doc types
        kind = g.kind
        title = g.title
        doc_type_override = classify.DOC_TYPE_OVERRIDES.get(kind)
        if kind in classify.KIND_ALIASES:
            kind, default_title = classify.KIND_ALIASES[g.kind]
            title = title or default_title
        folder = g.folder
        if g.kind == "amazon-report":
            folder = f"07-commerce/amazon/{(g.period or when[:7])}"
        if g.kind == "invoice" and g.fy:
            folder = f"{intake.ACCOUNTS_FOLDER}/FY{g.fy}/invoices"
        unsure = g.confidence < THRESHOLD or (kind in classify.ACCOUNTS_KINDS and not g.fy and folder is None)
        if unsure:
            folder = "12-uploads/needs-review"
            res.action = "would-review" if dry_run else "review"
        else:
            res.action = "would-file" if dry_run else "filed"
        if dry_run:
            res.dest = f"{folder or intake.ACCOUNTS_FOLDER + '/FY' + (g.fy or '?')}/"
            return res

        dest, doc_id = intake.file_document(
            path, kind if not unsure else (kind if kind in intake.KINDS else "other"),
            fy=g.fy, when=when, detail=g.detail, folder=folder, title=title, number=g.number, expiry=g.expiry,
            notes=(f"Auto-sorted from inbox on {date.today().isoformat()} · confidence {g.confidence:.2f} · "
                   f"{'; '.join(g.reasons)[:400]}"), con=con)
        upd: dict[str, Any] = {"sha256": digest, "source": "inbox-auto" if method == "auto" else "inbox-llm"}
        if doc_type_override and not unsure:
            upd["doc_type"] = doc_type_override
        if unsure:
            upd["status"] = "pending"
            upd["tags"] = f"needs-review, {g.kind}" + (f", fy{g.fy}" if g.fy else "")
        db.update(con, "documents", doc_id, upd)
        res.doc_id, res.dest = doc_id, str(dest.relative_to(paths.VAULT_DIR)).replace("\\", "/")

        if not unsure:
            facts = extract.extract_facts(g.kind, text, g.fy, g.period)
            fmethod = "auto"
            if want_llm and g.kind in ("financial-statements", "audit-report", "itr", "gstr-3b", "bank-statement") and len(facts) < 3:
                more = llm.extract_facts(g.kind, text, g.fy)
                if more:
                    facts, fmethod = more, "llm"
            res.facts = _store_facts(con, doc_id, g.fy, facts, fmethod)
            res.compliance = _prove_compliance(con, g.kind, when, doc_id, g.fy)
        return res
    except Exception as e:  # noqa: BLE001 - one bad file must not stop the run
        res.action, res.note = "error", f"{type(e).__name__}: {e}"
        return res


def sort_inbox(con, *, dry_run: bool = False, use_llm: bool | None = None, inbox: Path | None = None) -> list[Result]:
    results: list[Result] = []
    for p in pending_files(inbox):
        waited = 0
        while not _settled(p) and waited < 6:      # a file just dropped: give the copy a moment to finish
            time.sleep(1)
            waited += 1
        if not _settled(p):
            results.append(Result(file=p.name, action="skipped", note="still being written; next pass"))
            continue
        results.append(sort_one(con, p, dry_run=dry_run, use_llm=use_llm))
    if results and not dry_run:
        db.meta_set(con, "inbox_last_run", json.dumps({
            "at": db.now(), "results": [r.as_dict() for r in results]}, ensure_ascii=False))
    return results


def last_run(con) -> dict[str, Any] | None:
    raw = db.meta_get(con, "inbox_last_run")
    return json.loads(raw) if raw else None


def needs_review(con) -> list[dict]:
    return db.list_rows(con, "documents", where="tags LIKE '%needs-review%' AND status = 'pending'", limit=100)
