"""Buzzcaf Ops test suite.  Run:  cd ops && python -m pytest tests -q

Uses a throwaway data directory (BUZZCAF_OPS_DATA) so the real ops.db is never touched.
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

import pytest

OPS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPS_ROOT))

_tmp = os.environ.get("BUZZCAF_OPS_DATA") or tempfile.mkdtemp(prefix="buzzcaf-ops-test-")
os.environ["BUZZCAF_OPS_DATA"] = _tmp  # must exist before app.paths is imported (shared with test_assistant)

from fastapi.testclient import TestClient  # noqa: E402

from app import db, services  # noqa: E402
from app.main import create_app  # noqa: E402
from app.specs import NAV_ORDER, RESOURCES  # noqa: E402


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def con():
    c = db.connect()
    db.init_schema(c)
    try:
        yield c
    finally:
        c.close()


def test_uses_temp_data_dir():
    from app import paths
    assert str(paths.DATA_DIR) == str(Path(_tmp).resolve()) or paths.DATA_DIR.samefile(_tmp)


def test_health_and_dashboard(client):
    assert client.get("/api/health").status_code == 200
    r = client.get("/")
    assert r.status_code == 200
    assert "Dashboard" in r.text
    j = client.get("/api/dashboard").json()
    assert {"expired", "overdue", "soon", "tasks_due"} <= set(j)


@pytest.mark.parametrize("key", NAV_ORDER)
def test_every_module_lists(client, key):
    assert key in RESOURCES
    assert client.get(f"/{key}").status_code == 200
    assert client.get(f"/{key}/new").status_code == 200
    assert client.get(f"/api/{key}").status_code == 200


def test_sops_and_vault_pages(client):
    r = client.get("/sops")
    assert r.status_code == 200
    sops = client.get("/api/sops").json()
    assert len(sops) >= 12
    first = sops[0]["slug"]
    assert client.get(f"/sops/{first}").status_code == 200
    assert client.get("/vault").status_code == 200
    assert client.get("/vault/file/../../ops/run.py").status_code in (400, 404, 422)


def test_document_roundtrip_via_api(client):
    payload = {
        "title": "Test FSSAI licence", "doc_type": "fssai_licence", "number": "TEST123",
        "authority": "FoSCoS", "issue_date": "2026-01-01", "expiry_date": "2026-10-01", "status": "valid",
    }
    r = client.post("/api/documents", json=payload)
    assert r.status_code == 201, r.text
    row_id = r.json()["id"]
    got = client.get(f"/api/documents/{row_id}").json()
    assert got["number"] == "TEST123"
    r = client.patch(f"/api/documents/{row_id}", json={"number": "TEST456"})
    assert r.status_code == 200
    assert client.get(f"/api/documents/{row_id}").json()["number"] == "TEST456"
    assert client.get(f"/documents/{row_id}").status_code == 200
    assert client.get(f"/documents/{row_id}/edit").status_code == 200
    assert client.delete(f"/api/documents/{row_id}").status_code in (200, 204)
    assert client.get(f"/api/documents/{row_id}").status_code == 404


def test_html_form_create(client):
    r = client.post("/tasks/new", data={"title": "Form task", "status": "todo", "priority": "high"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    rows = client.get("/api/tasks", params={"q": "Form task"}).json()
    assert any(t["title"] == "Form task" for t in rows)


def test_document_expiry_buckets(con):
    today = date(2026, 9, 7)
    for title, exp in [("exp", "2026-09-01"), ("d30", "2026-09-20"), ("d60", "2026-10-30"), ("d90", "2026-11-30"), ("far", "2027-06-01")]:
        db.insert(con, "documents", {"title": title, "doc_type": "other", "expiry_date": exp, "status": "valid"})
    b = services.document_expiry(con, today)
    titles = lambda rows: {r["title"] for r in rows}  # noqa: E731
    assert "exp" in titles(b.expired)
    assert "d30" in titles(b.d30)
    assert "d60" in titles(b.d60)
    assert "d90" in titles(b.d90)
    assert "far" not in titles(b.expired + b.d30 + b.d60 + b.d90)
    n = services.auto_expire_documents(con, today)
    assert n >= 1
    row = db.find_one(con, "documents", "title = ?", ["exp"])
    assert row["status"] == "expired"


def test_compliance_next_due_rules():
    today = date(2026, 9, 7)
    # monthly on the 11th, never marked done -> reported overdue at the last occurrence
    assert services.next_due({"type": "monthly", "day": 11}, today) == date(2026, 8, 11)
    # monthly on the 11th, August done -> 11 Sep 2026
    assert services.next_due({"type": "monthly", "day": 11}, today, last_done=date(2026, 8, 11)) == date(2026, 9, 11)
    # monthly on the 20th, already done for this period -> next month
    assert services.next_due({"type": "monthly", "day": 20}, today, last_done=date(2026, 9, 20)) == date(2026, 10, 20)
    # yearly 31 May -> next year
    assert services.next_due({"type": "annual", "dates": [[5, 31]]}, today, last_done=date(2026, 6, 1)) == date(2027, 5, 31)
    # yearly 30 Sep -> this year
    assert services.next_due({"type": "annual", "dates": [[9, 30]]}, today, last_done=date(2025, 9, 30)) == date(2026, 9, 30)


def test_mark_done_advances_next_due(con):
    rid = db.insert(con, "compliance", {"name": "GSTR-3B test", "rule": '{"type":"monthly","day":20}', "status": "active"})
    services.refresh_compliance(con, date(2026, 9, 7))
    assert db.get(con, "compliance", rid)["next_due"] == "2026-08-20"  # never done -> overdue August
    services.mark_done(con, rid, date(2026, 9, 18), note="filed")
    assert db.get(con, "compliance", rid)["last_done"] == "2026-09-18"
    assert db.get(con, "compliance", rid)["next_due"] in ("2026-09-20", "2026-10-20")
    log = services.compliance_log(con, rid)
    assert log and log[0]["note"] == "filed"


def test_complaint_pattern_flag(con):
    for i in range(3):
        db.insert(con, "complaints", {"summary": f"clumping {i}", "batch_no": "B-TEST-001", "issue": "clumping", "channel": "amazon", "resolved": 0})
    db.insert(con, "complaints", {"summary": "one-off", "batch_no": "B-TEST-002", "issue": "delivery", "channel": "site", "resolved": 0})
    patterns = services.complaint_patterns(con, threshold=3)
    batches = {p["batch_no"] for p in patterns}
    assert "B-TEST-001" in batches
    assert "B-TEST-002" not in batches


def test_batch_health_flags_missing_checks(con):
    ok = db.insert(con, "batches", {"batch_no": "B-OK", "qc_result": "pass", **{c: 1 for c in services.CHECKS}})
    bad = db.insert(con, "batches", {"batch_no": "B-BAD", "qc_result": "pending", "chk_paperwork": 1})
    flagged = {b["id"] for b in services.batch_health(con)}
    assert bad in flagged and ok not in flagged


def test_intake_files_and_registers(con, tmp_path, monkeypatch):
    import intake
    from app import paths

    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setattr(paths, "VAULT_DIR", vault)
    src = tmp_path / "Audit Report FINAL.pdf"
    src.write_bytes(b"%PDF-1.4 test")

    dest, doc_id = intake.file_document(src, "audit-report", fy=intake.norm_fy("FY2024-25"),
                                        when="2025-09-20", number="UDIN123", con=con)
    assert dest == vault / "13-accounts-and-audit" / "FY2024-25" / "audit-report-fy2024-25-2025-09-20.pdf"
    assert dest.exists() and not src.exists()
    row = db.get(con, "documents", doc_id)
    assert row["doc_type"] == "audit-report"
    assert row["file_path"] == "13-accounts-and-audit/FY2024-25/audit-report-fy2024-25-2025-09-20.pdf"
    assert row["number"] == "UDIN123" and row["issue_date"] == "2025-09-20"
    assert "fy2024-25" in row["tags"] and "accounts" in row["tags"]
    assert row["title"].endswith("FY2024-25")

    # second file with the same name is not overwritten
    src2 = tmp_path / "again.pdf"
    src2.write_bytes(b"x")
    dest2, _ = intake.file_document(src2, "audit-report", fy="2024-25", when="2025-09-20", con=con)
    assert dest2.name == "audit-report-fy2024-25-2025-09-20-1.pdf"

    # unregistered listing sees a stray file but not the registered ones or READMEs
    (vault / "13-accounts-and-audit" / "inbox").mkdir()
    (vault / "13-accounts-and-audit" / "inbox" / "README.md").write_text("x")
    (vault / "13-accounts-and-audit" / "inbox" / "stray.pdf").write_bytes(b"x")
    assert intake.unregistered(con) == ["13-accounts-and-audit/inbox/stray.pdf"]


def test_intake_fy_validation():
    import intake
    assert intake.norm_fy("2024-25") == "2024-25"
    assert intake.norm_fy("fy2024-2025") == "2024-25"
    with pytest.raises(SystemExit):
        intake.norm_fy("2024-26")
