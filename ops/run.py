r"""Run Buzzcaf Ops standalone:  python ops/run.py  [--port N] [--host H]

The port is a wish, never a fact (GUARDIAN_PLAN.md section 11). `--port` and
`BUZZCAFCOFFEE_PORT` say what we would *like*; if something already holds it we
step forward to the next free port rather than evicting whoever is there. Once
/health answers as us we publish where we landed into the shared ledger
(`%LOCALAPPDATA%\Buzzcaf\ports.json`), print `READY port=N` for whatever
launched us, and take the entry out again on the way down.
"""
from __future__ import annotations
import argparse, atexit, json, sys, threading, time, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import uvicorn
import buzzcaf_ports  # byte-identical copy of dexter/backend/buzzcaf_ports.py; never edit here
from app.main import APP_ID, PREFERRED_PORT, create_app, set_bound_port


def _announce_when_ready(host: str, port: int, timeout: float = 40.0) -> None:
    """Publish to the ledger only once we really answer on the port we took."""
    probe_host = "127.0.0.1" if host in ("0.0.0.0", "") else host
    url = f"http://{probe_host}:{port}/health"

    def _wait() -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=1.5) as res:
                    if json.loads(res.read().decode("utf-8") or "{}").get("app") == APP_ID:
                        buzzcaf_ports.publish(APP_ID, port, url)
                        print(f"READY port={port}", flush=True)
                        return
            except Exception:
                pass
            time.sleep(0.25)

    threading.Thread(target=_wait, name="ops-ports-publish", daemon=True).start()
    atexit.register(_withdraw)


def _withdraw() -> None:
    try:
        buzzcaf_ports.withdraw(APP_ID)
    except Exception:  # a ledger problem must never stop a shutdown
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=None,
                    help="preferred port (default: BUZZCAFCOFFEE_PORT, else the app's own)")
    ap.add_argument("--reload", action="store_true")
    ap.add_argument("--assistant", action="store_true", help="also run the assistant watcher (mail + inbox sorting + daily brief)")
    ap.add_argument("--every", type=int, default=600, help="assistant pass interval in seconds")
    a = ap.parse_args()
    if a.assistant:
        import threading as _threading
        from app import db, mail
        from assistant import watch
        mail.load_env()
        con = db.connect()
        db.init_schema(con)
        _threading.Thread(target=watch, kwargs={"con": con, "every": a.every}, daemon=True, name="buzzcaf-assistant").start()

    preferred = a.port if a.port is not None else PREFERRED_PORT
    bind_host = "127.0.0.1" if a.host in ("0.0.0.0", "") else a.host
    port = buzzcaf_ports.pick_port(preferred, host=bind_host)
    if port != preferred:
        print(f"[ops] port {preferred} is held by another process; using {port} instead", flush=True)
    set_bound_port(port)
    _announce_when_ready(a.host, port)
    try:
        if a.reload:
            # --reload re-imports the app in a child process, so the port has to
            # travel by environment for that child's /health to tell the truth.
            import os
            os.environ["BUZZCAFCOFFEE_PORT"] = str(port)
            uvicorn.run("app.main:create_app", factory=True, host=a.host, port=port, reload=True)
        else:
            uvicorn.run(create_app(), host=a.host, port=port)
    finally:
        _withdraw()


if __name__ == "__main__":
    main()
