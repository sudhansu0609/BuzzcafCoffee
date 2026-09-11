"""Zip the Ops database + the vault into ops/backups/buzzcaf-ops-YYYYMMDD-HHMM.zip
and refresh ops/backups/latest.zip. Run monthly (SOP-08) or before anything risky.

    python ops/backup.py            # create backup
    python ops/backup.py --verify   # also re-open the zipped DB and count rows
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import paths  # noqa: E402


def make_backup() -> Path:
    paths.ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out = paths.BACKUP_DIR / f"buzzcaf-ops-{stamp}.zip"
    dbp = paths.db_path()
    with tempfile.TemporaryDirectory() as td:
        snap = Path(td) / "ops.db"
        src = sqlite3.connect(str(dbp))
        dst = sqlite3.connect(str(snap))
        src.backup(dst)
        dst.close(); src.close()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(snap, "data/ops.db")
            for p in paths.VAULT_DIR.rglob("*"):
                if p.is_file():
                    z.write(p, "vault/" + str(p.relative_to(paths.VAULT_DIR)).replace("\\", "/"))
            for p in paths.SOP_DIR.glob("*.md"):
                z.write(p, "sops/" + p.name)
    shutil.copy2(out, paths.BACKUP_DIR / "latest.zip")
    return out


def verify(zip_path: Path) -> int:
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(zip_path) as z:
            z.extract("data/ops.db", td)
        con = sqlite3.connect(str(Path(td) / "data" / "ops.db"))
        n = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        con.close()
        return int(n)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    p = make_backup()
    print("backup:", p, f"({p.stat().st_size // 1024} KB)")
    if a.verify:
        print("verified: documents rows =", verify(p))
