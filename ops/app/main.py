"""Buzzcaf Ops — FastAPI application factory.

    from app.main import create_app
    app = create_app()                 # standalone
    studio.mount("/ops", create_app(root_path="/ops"))   # inside BuzzcafAI

Every route reads/writes SQLite through db.py; HTML is Jinja2; the JSON API
mirrors the HTML pages under /api/<resource>.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

import markdown
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import assistant, db, finance, mail, paths, services, sorter
from .specs import NAV_ORDER, RESOURCES, Resource

APP_VERSION = "1.1.0"

#: This app's name in the shared port ledger and in every health body
#: (GUARDIAN_PLAN.md section 11 rule 4).
APP_ID = "buzzcafcoffee"
#: A wish, not a fact: run.py may have had to step past it. Whoever binds calls
#: set_bound_port() with the port it really got.
PREFERRED_PORT = int(os.getenv("BUZZCAFCOFFEE_PORT", "8010"))
_bound_port = PREFERRED_PORT


def set_bound_port(port: int) -> None:
    global _bound_port
    _bound_port = int(port)


def bound_port() -> int:
    return _bound_port


def identity() -> dict:
    """Who is on this port, and which process. The one shape every app answers."""
    return {"app": APP_ID, "status": "ok", "port": _bound_port, "pid": os.getpid(), "version": APP_VERSION}


def _safe_name(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.")
    return name or "file"


def create_app(root_path: str = "") -> FastAPI:
    paths.ensure_dirs()
    with db.connect() as con:
        db.init_schema(con)

    app = FastAPI(title="Buzzcaf Ops", version=APP_VERSION, root_path=root_path, docs_url="/api/docs", redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(paths.STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(paths.TEMPLATE_DIR))
    templates.env.add_extension("jinja2.ext.loopcontrols")
    templates.env.globals.update(
        resources=RESOURCES, nav_order=NAV_ORDER, app_version=APP_VERSION,
        root=root_path, today=lambda: date.today().isoformat(),
    )
    templates.env.filters["md"] = lambda s: markdown.markdown(s or "", extensions=["tables", "fenced_code", "toc"])
    templates.env.filters["jsonpretty"] = lambda s: json.dumps(json.loads(s), indent=1) if s else ""

    def get_con():
        con = db.connect()
        try:
            yield con
        finally:
            con.close()

    def resource(key: str) -> Resource:
        r = RESOURCES.get(key)
        if not r:
            raise HTTPException(404, f"unknown resource {key}")
        return r

    def render(name: str, request: Request, **ctx: Any) -> HTMLResponse:
        return templates.TemplateResponse(request, name, ctx)

    def ref_maps(con: sqlite3.Connection, r: Resource) -> dict[str, dict[int, str]]:
        return {f.name: db.ref_titles(con, f.ref) for f in r.fields if f.kind == "ref" and f.ref}

    async def form_to_data(request: Request, r: Resource) -> dict[str, Any]:
        form = await request.form()
        data: dict[str, Any] = {}
        for f in r.fields:
            if f.kind == "readonly":
                continue
            if f.kind == "file":
                upload = form.get(f.name + "__upload")
                if isinstance(upload, UploadFile) and upload.filename:
                    folder = (form.get(f.name + "__folder") or "12-uploads").strip("/\\")
                    dest_dir = paths.VAULT_DIR / folder
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest = dest_dir / _safe_name(upload.filename)
                    i = 1
                    while dest.exists():
                        dest = dest_dir / f"{dest.stem}-{i}{dest.suffix}"
                        i += 1
                    dest.write_bytes(await upload.read())
                    data[f.name] = str(dest.relative_to(paths.VAULT_DIR)).replace("\\", "/")
                    continue
                data[f.name] = form.get(f.name, "")
                continue
            if f.kind == "bool":
                data[f.name] = 1 if form.get(f.name) else 0
            else:
                data[f.name] = form.get(f.name, "")
        return data

    # ------------------------------------------------------------ dashboard
    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, con: sqlite3.Connection = Depends(get_con)):
        return render("dashboard.html", request, d=services.dashboard(con), active="home")

    @app.get("/api/dashboard")
    def api_dashboard(con: sqlite3.Connection = Depends(get_con)):
        d = services.dashboard(con)
        d["today"] = d["today"].isoformat()
        return d

    @app.get("/health")
    def health_identity():
        # The plain route every other app in the ecosystem scans for. It says who
        # we are and nothing about the records behind us.
        return identity()

    @app.get("/api/health")
    def health():
        # Kept for the existing callers (BuzzcafAI / Dexter read db + vault from
        # here), now carrying the same identity fields.
        return {**identity(), "ok": True, "db": str(paths.db_path()), "vault": str(paths.VAULT_DIR)}

    # ------------------------------------------------------------------ SOPs
    @app.get("/sops", response_class=HTMLResponse)
    def sops(request: Request):
        return render("sops.html", request, sops=services.load_sops(), active="sops")

    @app.get("/sops/{slug}", response_class=HTMLResponse)
    def sop(request: Request, slug: str):
        s = services.get_sop(slug)
        if not s:
            raise HTTPException(404)
        return render("sop.html", request, sop=s, active="sops")

    @app.get("/api/sops")
    def api_sops():
        return [{k: v for k, v in s.items() if k != "body"} for s in services.load_sops()]

    # ------------------------------------------------------------- vault files
    @app.get("/vault", response_class=HTMLResponse)
    def vault(request: Request):
        files = []
        for p in sorted(paths.VAULT_DIR.rglob("*")):
            if p.is_file():
                rel = str(p.relative_to(paths.VAULT_DIR)).replace("\\", "/")
                files.append({"path": rel, "size": p.stat().st_size, "restricted": rel.startswith("05-")})
        return render("vault.html", request, files=files, active="vault", vault_dir=str(paths.VAULT_DIR))

    @app.get("/vault/file/{rel:path}")
    def vault_file(rel: str):
        target = (paths.VAULT_DIR / rel).resolve()
        if paths.VAULT_DIR.resolve() not in target.parents or not target.is_file():
            raise HTTPException(404)
        mt, _ = mimetypes.guess_type(str(target))
        return FileResponse(str(target), media_type=mt or "application/octet-stream", filename=target.name,
                            content_disposition_type="inline")

    # ------------------------------------------------ assistant: inbox / finance / brief
    @app.get("/inbox", response_class=HTMLResponse)
    def inbox_page(request: Request, con: sqlite3.Connection = Depends(get_con)):
        pending = [{"name": p.name, "size": p.stat().st_size, "rel": p.relative_to(paths.INBOX_DIR).as_posix()}
                   for p in sorter.pending_files()]
        return render("inbox.html", request, active="inbox", pending=pending, last=sorter.last_run(con),
                      review=sorter.needs_review(con), inbox_dir=str(paths.INBOX_DIR),
                      cycle=assistant.last_cycle(con), mail_on=mail.configured(),
                      llm_on=__import__("app.llm", fromlist=["enabled"]).enabled(),
                      ocr_on=__import__("app.ocr", fromlist=["available"]).available(),
                      ocr_engine=__import__("app.ocr", fromlist=["engine_name"]).engine_name())

    @app.post("/inbox/sort")
    def inbox_sort(dry_run: str = Form(""), con: sqlite3.Connection = Depends(get_con)):
        sorter.sort_inbox(con, dry_run=bool(dry_run))
        return RedirectResponse(f"{root_path}/inbox", status_code=303)

    @app.post("/inbox/upload")
    async def inbox_upload(files: list[UploadFile] = File(...)):
        paths.INBOX_DIR.mkdir(parents=True, exist_ok=True)
        for up in files:
            if not up.filename:
                continue
            dest = paths.INBOX_DIR / _safe_name(up.filename)
            i = 1
            while dest.exists():
                dest = paths.INBOX_DIR / f"{dest.stem}-{i}{dest.suffix}"
                i += 1
            dest.write_bytes(await up.read())
        return RedirectResponse(f"{root_path}/inbox", status_code=303)

    @app.post("/inbox/cycle")
    def inbox_cycle(con: sqlite3.Connection = Depends(get_con)):
        assistant.run_cycle(con)
        return RedirectResponse(f"{root_path}/inbox", status_code=303)

    @app.post("/api/inbox/sort")
    def api_inbox_sort(dry_run: bool = False, con: sqlite3.Connection = Depends(get_con)):
        return [r.as_dict() for r in sorter.sort_inbox(con, dry_run=dry_run)]

    @app.get("/api/inbox")
    def api_inbox(con: sqlite3.Connection = Depends(get_con)):
        return {"pending": [p.name for p in sorter.pending_files()], "last_run": sorter.last_run(con),
                "needs_review": sorter.needs_review(con)}

    @app.get("/finance", response_class=HTMLResponse)
    def finance_page(request: Request, con: sqlite3.Connection = Depends(get_con)):
        return render("finance.html", request, active="finance", f=finance.overview(con))

    @app.get("/api/finance")
    def api_finance(con: sqlite3.Connection = Depends(get_con)):
        return finance.overview(con)

    @app.get("/brief", response_class=HTMLResponse)
    def brief_page(request: Request, con: sqlite3.Connection = Depends(get_con)):
        return render("brief.html", request, active="brief", text=assistant.brief(con), ctx=assistant.context(con),
                      mail_on=mail.configured(), last_sent=db.meta_get(con, "brief_last_sent"))

    @app.post("/brief/send")
    def brief_send(con: sqlite3.Connection = Depends(get_con)):
        assistant.send_brief(con)
        return RedirectResponse(f"{root_path}/brief", status_code=303)

    @app.get("/api/brief")
    def api_brief(con: sqlite3.Connection = Depends(get_con)):
        return {"brief": assistant.brief(con), "context": assistant.context(con)}

    @app.post("/api/assistant/cycle")
    def api_cycle(con: sqlite3.Connection = Depends(get_con)):
        return assistant.run_cycle(con)

    @app.post("/mail/fetch")
    def mail_fetch(con: sqlite3.Connection = Depends(get_con)):
        if mail.configured():
            try:
                mail.fetch(con)
            except Exception as e:  # noqa: BLE001
                return HTMLResponse(f"<p>mail fetch failed: {e}</p><a href='{root_path}/mail'>back</a>", status_code=502)
        return RedirectResponse(f"{root_path}/mail", status_code=303)

    @app.post("/mail/{row_id}/status")
    def mail_status(row_id: int, status: str = Form(...), con: sqlite3.Connection = Depends(get_con)):
        db.update(con, "mail", row_id, {"status": status})
        return RedirectResponse(f"{root_path}/mail/{row_id}", status_code=303)

    @app.get("/vault/text/{rel:path}", response_class=HTMLResponse)
    def vault_text(rel: str, request: Request):
        """What the assistant can read out of a vault file (text layer or OCR)."""
        from . import classify, ocr
        target = (paths.VAULT_DIR / rel).resolve()
        if paths.VAULT_DIR.resolve() not in target.parents or not target.is_file():
            raise HTTPException(404)
        text = classify.extract_text(target)
        return render("text.html", request, active="vault", rel=rel, text=text, ocr=text.startswith("[ocr]"),
                      engine=ocr.engine_name(), ocr_available=ocr.available())

    # ---------------------------------------------------- compliance actions
    @app.post("/compliance/{row_id}/done")
    def compliance_done(row_id: int, done_on: str = Form(...), note: str = Form(""), period: str = Form(""),
                        con: sqlite3.Connection = Depends(get_con)):
        d = services.parse_date(done_on) or date.today()
        services.mark_done(con, row_id, d, note, period)
        return RedirectResponse(f"{root_path}/compliance/{row_id}", status_code=303)

    @app.post("/api/compliance/{row_id}/done")
    def api_compliance_done(row_id: int, payload: dict[str, Any], con: sqlite3.Connection = Depends(get_con)):
        d = services.parse_date(payload.get("done_on")) or date.today()
        services.mark_done(con, row_id, d, payload.get("note", ""), payload.get("period", ""))
        return db.get(con, "compliance", row_id)

    # ---------------------------------------------------------- generic HTML
    @app.get("/api/{key}")
    def api_list(key: str, q: str | None = None, con: sqlite3.Connection = Depends(get_con)):
        resource(key)
        if key == "compliance":
            services.refresh_compliance(con)
        return db.list_rows(con, key, q=q)

    @app.post("/api/{key}", status_code=201)
    def api_create(key: str, payload: dict[str, Any], con: sqlite3.Connection = Depends(get_con)):
        resource(key)
        try:
            row_id = db.insert(con, key, payload)
        except (ValueError, json.JSONDecodeError) as e:
            raise HTTPException(422, str(e))
        if key == "compliance":
            services.refresh_compliance(con)
        return db.get(con, key, row_id)

    @app.get("/api/{key}/{row_id}")
    def api_get(key: str, row_id: int, con: sqlite3.Connection = Depends(get_con)):
        resource(key)
        row = db.get(con, key, row_id)
        if not row:
            raise HTTPException(404)
        return row

    @app.put("/api/{key}/{row_id}")
    @app.patch("/api/{key}/{row_id}")
    def api_update(key: str, row_id: int, payload: dict[str, Any], con: sqlite3.Connection = Depends(get_con)):
        resource(key)
        if not db.get(con, key, row_id):
            raise HTTPException(404)
        db.update(con, key, row_id, payload)
        if key == "compliance":
            services.refresh_compliance(con)
        return db.get(con, key, row_id)

    @app.delete("/api/{key}/{row_id}")
    def api_delete(key: str, row_id: int, con: sqlite3.Connection = Depends(get_con)):
        resource(key)
        db.delete(con, key, row_id)
        return JSONResponse({"deleted": row_id})

    @app.get("/{key}", response_class=HTMLResponse)
    def list_page(key: str, request: Request, q: str | None = None, status: str | None = None,
                  con: sqlite3.Connection = Depends(get_con)):
        r = resource(key)
        if key == "compliance":
            services.refresh_compliance(con)
        if key == "documents":
            services.auto_expire_documents(con)
        where, params = None, []
        if status and any(f.name == "status" for f in r.fields):
            where, params = "status = ?", [status]
        rows = db.list_rows(con, key, q=q, where=where, params=params)
        refs = ref_maps(con, r)
        return render("list.html", request, r=r, rows=rows, q=q or "", status=status or "", refs=refs, active=key,
                      today=date.today().isoformat())

    @app.get("/{key}/new", response_class=HTMLResponse)
    def new_page(key: str, request: Request, con: sqlite3.Connection = Depends(get_con)):
        r = resource(key)
        row = {f.name: f.default for f in r.fields}
        for k, v in request.query_params.items():
            if k in row:
                row[k] = v
        return render("form.html", request, r=r, row=row, refs=ref_maps(con, r), active=key, mode="new")

    @app.post("/{key}/new")
    async def create(key: str, request: Request, con: sqlite3.Connection = Depends(get_con)):
        r = resource(key)
        data = await form_to_data(request, r)
        row_id = db.insert(con, key, data)
        if key == "compliance":
            services.refresh_compliance(con)
        return RedirectResponse(f"{root_path}/{key}/{row_id}", status_code=303)

    @app.get("/{key}/{row_id}", response_class=HTMLResponse)
    def detail_page(key: str, row_id: int, request: Request, con: sqlite3.Connection = Depends(get_con)):
        r = resource(key)
        row = db.get(con, key, row_id)
        if not row:
            raise HTTPException(404)
        extra: dict[str, Any] = {}
        if key == "compliance":
            extra["log"] = services.compliance_log(con, row_id)
        if key == "batches":
            extra["samples"] = db.list_rows(con, "retention_samples", where="batch_id = ?", params=[row_id])
            extra["complaints"] = db.list_rows(con, "complaints", where="batch_no = ?", params=[row.get("batch_no")])
            extra["tests"] = db.list_rows(con, "lab_tests", where="batch_id = ?", params=[row_id])
        if key == "suppliers":
            extra["batches"] = db.list_rows(con, "batches", where="supplier_id = ?", params=[row_id])
        if key == "documents":
            extra["facts"] = db.list_rows(con, "facts", where="source_id = ?", params=[row_id])
        if key == "mail":
            extra["mail_actions"] = True
        return render("detail.html", request, r=r, row=row, refs=ref_maps(con, r), active=key, **extra)

    @app.get("/{key}/{row_id}/edit", response_class=HTMLResponse)
    def edit_page(key: str, row_id: int, request: Request, con: sqlite3.Connection = Depends(get_con)):
        r = resource(key)
        row = db.get(con, key, row_id)
        if not row:
            raise HTTPException(404)
        return render("form.html", request, r=r, row=row, refs=ref_maps(con, r), active=key, mode="edit")

    @app.post("/{key}/{row_id}/edit")
    async def save(key: str, row_id: int, request: Request, con: sqlite3.Connection = Depends(get_con)):
        r = resource(key)
        if not db.get(con, key, row_id):
            raise HTTPException(404)
        data = await form_to_data(request, r)
        db.update(con, key, row_id, data)
        if key == "compliance":
            services.refresh_compliance(con)
        return RedirectResponse(f"{root_path}/{key}/{row_id}", status_code=303)

    @app.post("/{key}/{row_id}/delete")
    def remove(key: str, row_id: int, con: sqlite3.Connection = Depends(get_con)):
        resource(key)
        db.delete(con, key, row_id)
        return RedirectResponse(f"{root_path}/{key}", status_code=303)

    # ------------------------------------------------------------ JSON API
    return app
