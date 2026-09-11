"""Buzzcaf Ops obeys the shared port law (GUARDIAN_PLAN.md section 11).

Nothing is hardcoded past the preferred default, a busy port is stepped over
rather than taken, /health says who is on the port, and the ledger entry appears
on start and is gone again after a clean stop.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
from pathlib import Path

import pytest

OPS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPS_ROOT))

from tests.test_ops import client  # noqa: F401,E402  (the shared throwaway-data fixture)

import buzzcaf_ports  # noqa: E402
from app.main import APP_ID, PREFERRED_PORT, bound_port, identity, set_bound_port  # noqa: E402

CANONICAL = OPS_ROOT.parent.parent / "dexter" / "backend" / "buzzcaf_ports.py"


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "ports.json"
    monkeypatch.setenv("BUZZCAF_PORTS_FILE", str(path))
    return path


@pytest.fixture
def occupied():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    try:
        yield sock.getsockname()[1]
    finally:
        sock.close()


def test_health_says_who_and_where_we_are(client):
    body = client.get("/health").json()
    assert body["app"] == APP_ID == "buzzcafcoffee"
    assert body["status"] == "ok"
    assert body["port"] == bound_port()
    assert body["pid"] == os.getpid()


def test_the_api_health_route_keeps_its_callers_and_gains_identity(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True and body["app"] == APP_ID
    assert "db" in body and "vault" in body


def test_health_reports_the_port_we_actually_bound(client):
    before = bound_port()
    try:
        set_bound_port(before + 5)
        assert client.get("/health").json()["port"] == before + 5
    finally:
        set_bound_port(before)


@pytest.mark.skipif(not CANONICAL.exists(), reason="Dexter checkout not beside this one")
def test_the_port_helper_is_a_byte_identical_copy():
    copy = OPS_ROOT / "buzzcaf_ports.py"
    assert hashlib.sha256(copy.read_bytes()).hexdigest() == hashlib.sha256(CANONICAL.read_bytes()).hexdigest()


def test_a_busy_port_is_stepped_over_never_taken(occupied):
    chosen = buzzcaf_ports.pick_port(occupied)
    assert occupied < chosen <= occupied + buzzcaf_ports.SPAN
    spare = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(OSError):
            spare.bind(("127.0.0.1", occupied))
            spare.listen(1)
    finally:
        spare.close()


def test_publish_then_withdraw_leaves_the_ledger_clean(ledger):
    import run

    buzzcaf_ports.publish(APP_ID, PREFERRED_PORT, f"http://127.0.0.1:{PREFERRED_PORT}/health")
    entry = json.loads(ledger.read_text(encoding="utf-8"))[APP_ID]
    assert entry["port"] == PREFERRED_PORT and entry["pid"] == os.getpid()
    run._withdraw()
    assert APP_ID not in json.loads(ledger.read_text(encoding="utf-8"))


def test_the_preferred_port_is_the_only_literal_and_comes_from_the_environment(monkeypatch):
    import importlib

    import app.main as ops_main

    monkeypatch.setenv("BUZZCAFCOFFEE_PORT", "8321")
    try:
        assert importlib.reload(ops_main).PREFERRED_PORT == 8321
    finally:
        monkeypatch.undo()
        importlib.reload(ops_main)

    # And nothing else in ops/ writes a port down.
    offenders = []
    for path in OPS_ROOT.rglob("*.py"):
        if {"__pycache__", "tests", "backups", "data"} & set(path.parts):
            continue
        if path.name in {"buzzcaf_ports.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if "getenv" in line or line.strip().startswith("#"):
                continue
            for token in ("8010", ":800", ":30"):
                if token in line and "port" in line.lower():
                    offenders.append(f"{path.name}: {line.strip()}")
    assert not offenders, offenders


def test_identity_is_the_shape_every_app_answers():
    body = identity()
    assert set(body) >= {"app", "status", "port", "pid"}
    assert body["status"] == "ok"
