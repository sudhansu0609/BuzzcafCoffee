"""Single source of truth for every filesystem location used by Buzzcaf Ops.

Mirrors the BuzzcafAI convention (core/paths.py): everything derives from this
file's position, and an environment override is honoured only when the target
directory already exists.

    OPS_ROOT      ops/
    DATA_DIR      ops/data              (override: BUZZCAF_OPS_DATA)
    DB_PATH       ops/data/ops.db
    UPLOAD_DIR    vault/                (override: BUZZCAF_OPS_VAULT)
    INBOX_DIR     inbox/                (override: BUZZCAF_OPS_INBOX)
    ENV_FILE      ops/.env
    SOP_DIR       ops/sops
    TEMPLATE_DIR  ops/app/templates
    STATIC_DIR    ops/app/static
"""
from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
OPS_ROOT = APP_DIR.parent
PROJECT_ROOT = OPS_ROOT.parent  # BuzzcafCoffee/


def _override(env: str, default: Path) -> Path:
    value = os.environ.get(env)
    if value:
        candidate = Path(value).expanduser().resolve()
        if candidate.is_dir():
            return candidate
    return default


DATA_DIR = _override("BUZZCAF_OPS_DATA", OPS_ROOT / "data")
VAULT_DIR = _override("BUZZCAF_OPS_VAULT", PROJECT_ROOT / "vault")
INBOX_DIR = _override("BUZZCAF_OPS_INBOX", PROJECT_ROOT / "inbox")   # drop zone: anything here gets sorted into the vault
ENV_FILE = OPS_ROOT / ".env"                                          # mail + API credentials, gitignored
SOP_DIR = OPS_ROOT / "sops"
TEMPLATE_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
BACKUP_DIR = OPS_ROOT / "backups"


def db_path() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "ops.db"


def ensure_dirs() -> None:
    for d in (DATA_DIR, VAULT_DIR, SOP_DIR, BACKUP_DIR, INBOX_DIR):
        d.mkdir(parents=True, exist_ok=True)
