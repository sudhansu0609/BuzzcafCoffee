"""SQLite access layer. Schema is generated from specs.RESOURCES.

Nothing clever: one connection per request, row_factory=sqlite3.Row, and a
handful of helpers (insert/update/get/list/search). Column additions are
applied automatically with ALTER TABLE so specs can grow without migrations.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from . import paths
from .specs import RESOURCES, Resource

_META = "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"
_COMPLIANCE_LOG = (
    "CREATE TABLE IF NOT EXISTS compliance_log ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT, obligation_id INTEGER NOT NULL,"
    " done_on TEXT NOT NULL, period TEXT, note TEXT, created_at TEXT NOT NULL)"
)


def connect(path: Path | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(str(path or paths.db_path()), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con


def _create_sql(r: Resource) -> str:
    cols = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
    for f in r.fields:
        if f.kind == "readonly":
            cols.append(f"{f.name} TEXT")
        else:
            cols.append(f"{f.name} {f.sql_type}")
    cols += ["created_at TEXT NOT NULL", "updated_at TEXT NOT NULL"]
    return f"CREATE TABLE IF NOT EXISTS {r.key} ({', '.join(cols)})"


def init_schema(con: sqlite3.Connection) -> None:
    con.execute(_META)
    con.execute(_COMPLIANCE_LOG)
    for r in RESOURCES.values():
        con.execute(_create_sql(r))
        existing = {row[1] for row in con.execute(f"PRAGMA table_info({r.key})")}
        for f in r.fields:
            if f.name not in existing:
                sql_type = "TEXT" if f.kind == "readonly" else f.sql_type
                con.execute(f"ALTER TABLE {r.key} ADD COLUMN {f.name} {sql_type}")
    con.commit()


def now() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _coerce(r: Resource, data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in r.fields:
        if f.name not in data:
            continue
        v = data[f.name]
        if f.kind in ("int",):
            v = int(v) if v not in (None, "", "None") else None
        elif f.kind == "real":
            v = float(v) if v not in (None, "", "None") else None
        elif f.kind == "bool":
            v = 1 if v in (1, True, "1", "on", "true", "True", "yes") else 0
        elif f.kind == "json":
            if isinstance(v, (dict, list)):
                v = json.dumps(v)
            elif v in (None, ""):
                v = None
            else:
                json.loads(v)  # validate
        elif f.kind == "ref":
            v = int(v) if v not in (None, "", "None") else None
        else:
            v = None if v is None else str(v).strip()
            if v == "":
                v = None
        out[f.name] = v
    return out


def insert(con: sqlite3.Connection, key: str, data: dict[str, Any]) -> int:
    r = RESOURCES[key]
    row = {f.name: f.default for f in r.fields if f.default is not None}
    row.update(_coerce(r, data))
    ts = now()
    row["created_at"] = ts
    row["updated_at"] = ts
    cols = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    cur = con.execute(f"INSERT INTO {key} ({cols}) VALUES ({marks})", list(row.values()))
    con.commit()
    return int(cur.lastrowid)


def update(con: sqlite3.Connection, key: str, row_id: int, data: dict[str, Any]) -> None:
    r = RESOURCES[key]
    row = _coerce(r, data)
    row["updated_at"] = now()
    sets = ", ".join(f"{c} = ?" for c in row)
    con.execute(f"UPDATE {key} SET {sets} WHERE id = ?", [*row.values(), row_id])
    con.commit()


def delete(con: sqlite3.Connection, key: str, row_id: int) -> None:
    con.execute(f"DELETE FROM {key} WHERE id = ?", (row_id,))
    con.commit()


def get(con: sqlite3.Connection, key: str, row_id: int) -> dict[str, Any] | None:
    row = con.execute(f"SELECT * FROM {key} WHERE id = ?", (row_id,)).fetchone()
    return dict(row) if row else None


def list_rows(con: sqlite3.Connection, key: str, q: str | None = None,
              where: str | None = None, params: Iterable[Any] = (), limit: int = 500) -> list[dict[str, Any]]:
    r = RESOURCES[key]
    clauses: list[str] = []
    vals: list[Any] = list(params)
    if where:
        clauses.append(f"({where})")
    if q and r.search_fields:
        like = " OR ".join(f"{f} LIKE ?" for f in r.search_fields)
        clauses.append(f"({like})")
        vals += [f"%{q}%"] * len(r.search_fields)
    sql = f"SELECT * FROM {key}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += f" ORDER BY {r.order_by} LIMIT {int(limit)}"
    return [dict(x) for x in con.execute(sql, vals).fetchall()]


def count(con: sqlite3.Connection, key: str, where: str = "1=1", params: Iterable[Any] = ()) -> int:
    return int(con.execute(f"SELECT COUNT(*) FROM {key} WHERE {where}", list(params)).fetchone()[0])


def find_one(con: sqlite3.Connection, key: str, where: str, params: Iterable[Any]) -> dict[str, Any] | None:
    row = con.execute(f"SELECT * FROM {key} WHERE {where} LIMIT 1", list(params)).fetchone()
    return dict(row) if row else None


def ref_titles(con: sqlite3.Connection, key: str) -> dict[int, str]:
    r = RESOURCES[key]
    rows = con.execute(f"SELECT id, {r.title_field} AS t FROM {key} ORDER BY {r.title_field}").fetchall()
    return {int(x["id"]): str(x["t"]) for x in rows}


def meta_get(con: sqlite3.Connection, k: str) -> str | None:
    row = con.execute("SELECT value FROM meta WHERE key = ?", (k,)).fetchone()
    return row[0] if row else None


def meta_set(con: sqlite3.Connection, k: str, v: str) -> None:
    con.execute("INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (k, v))
    con.commit()
