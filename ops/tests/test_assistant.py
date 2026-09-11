"""Inbox sorter, classifier, fact extraction, mail understanding, assistant pages.

Uses the same throwaway data dir as test_ops (BUZZCAF_OPS_DATA) plus a temp
vault and inbox per test via monkeypatching app.paths.
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
if "app.paths" not in sys.modules:
    os.environ.setdefault("BUZZCAF_OPS_DATA", tempfile.mkdtemp(prefix="buzzcaf-ops-test-"))
os.environ["BUZZCAF_ASSISTANT_LLM"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from app import assistant, classify, db, extract, finance, mail, paths, sorter  # noqa: E402
from app.main import create_app  # noqa: E402


# ------------------------------------------------------------- helpers ----
def make_pdf(path: Path, lines: list[str]) -> Path:
    """A minimal one-page PDF with Helvetica text that pypdf can read back."""
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = "BT /F1 11 Tf 40 800 Td 14 TL " + " ".join(f"({esc(l)}) Tj T*" for l in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content.encode('latin-1'))} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = "%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out.encode("latin-1")))
        out += f"{i} 0 obj\n{o}\nendobj\n"
    xref = len(out.encode("latin-1"))
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    path.write_bytes(out.encode("latin-1"))
    return path


AUDIT_LINES = [
    "BUZZCAF PRIVATE LIMITED",
    "INDEPENDENT AUDITOR'S REPORT",
    "To the Members of Buzzcaf Private Limited",
    "Report on the audit of the financial statements for the year ended 31st March 2025",
    "In our opinion the financial statements give a true and fair view",
    "Statement of Profit and Loss (Amount in Rs.)",
    "Revenue from operations 12,50,000",
    "Other income 5,000",
    "Total income 12,55,000",
    "Total expenses 14,00,000",
    "Profit/(Loss) before tax (1,45,000)",
    "Profit/(Loss) for the year (1,45,000)",
    "Balance Sheet as at 31st March 2025",
    "Total assets 3,20,000",
    "Cash and cash equivalents 42,000",
    "UDIN: 25123456BKABCD1234",
    "Place: Pune Date: 20/09/2025",
]

GSTR3B_LINES = [
    "Form GSTR-3B",
    "GSTIN 27AAKCB6111C1Z3 Legal name BUZZCAF PRIVATE LIMITED",
    "Tax period 08/2026 Financial year 2026-27",
    "3.1 Details of Outward Supplies and inward supplies liable to reverse charge",
    "(a) Outward taxable supplies (other than zero rated, nil rated and exempted) 1,00,000.00 0.00 2,500.00 2,500.00 0.00",
    "4. Eligible ITC",
    "(C) Net ITC Available (A) - (B) 1,800.00 0.00 900.00 900.00",
    "Late fee 0.00",
    "ARN AA270826123456Z Date of filing 05/09/2026",
]


@pytest.fixture()
def env(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    inbox = tmp_path / "inbox"
    vault.mkdir()
    inbox.mkdir()
    monkeypatch.setattr(paths, "VAULT_DIR", vault)
    monkeypatch.setattr(paths, "INBOX_DIR", inbox)
    monkeypatch.setattr(sorter, "SETTLE_SECONDS", 0)
    con = db.connect()
    db.init_schema(con)
    con.execute("DELETE FROM documents")
    con.execute("DELETE FROM facts")
    con.execute("DELETE FROM mail")
    con.execute("DELETE FROM compliance")
    con.execute("DELETE FROM compliance_log")
    con.commit()
    db.insert(con, "compliance", {"name": "GSTR-3B (summary + payment)", "frequency": "monthly",
                                  "rule": '{"type":"monthly","day":20}', "status": "active"})
    yield con, vault, inbox
    con.close()


# ------------------------------------------------------------ classify ----
def test_classify_audit_report(tmp_path):
    p = make_pdf(tmp_path / "Audit Report Final.pdf", AUDIT_LINES)
    text = classify.extract_text(p)
    assert "AUDITOR" in text.upper()
    g = classify.classify(p, text)
    assert g.kind == "audit-report"
    assert g.fy == "2024-25"
    assert g.when == "2025-09-20"
    assert g.number == "25123456BKABCD1234"
    assert g.confidence >= sorter.THRESHOLD


def test_classify_gstr3b_and_period(tmp_path):
    p = make_pdf(tmp_path / "gstr3b.pdf", GSTR3B_LINES)
    text = classify.extract_text(p)
    g = classify.classify(p, text)
    assert g.kind == "gstr-3b"
    assert g.period == "2026-08"
    assert g.fy == "2026-27"
    assert g.number == "AA270826123456Z"
    assert g.detail == "2026-08"


def test_classify_unknown_and_image(tmp_path):
    p = tmp_path / "IMG_1234.jpg"
    p.write_bytes(b"\xff\xd8\xff not really")
    g = classify.classify(p, "")
    assert g.kind == "photo" and g.confidence < sorter.THRESHOLD
    q = tmp_path / "notes.txt"
    q.write_text("hello there, nothing here")
    g2 = classify.classify(q, q.read_text())
    assert g2.confidence < sorter.THRESHOLD


def test_find_fy_variants():
    assert classify.find_fy("Assessment Year 2025-26") == "2024-25"
    assert classify.find_fy("for the year ended 31 March, 2024") == "2022-23" or classify.find_fy("for the year ended 31 March, 2024") == "2023-24"
    assert classify.find_fy("FY 2023-2024") == "2023-24"
    assert classify.find_fy("", "financials-2024-25-signed.pdf") == "2024-25"


def test_find_dates_legal_style():
    ds = classify.find_dates("entered into on this 3rd day of July 2022 at Pune; renewed 1st April, 2023")
    assert date(2022, 7, 3) in ds and date(2023, 4, 1) in ds


# ------------------------------------------------------------- extract ----
def test_extract_financial_facts(tmp_path):
    text = classify.extract_text(make_pdf(tmp_path / "a.pdf", AUDIT_LINES))
    facts = {f["metric"]: f["value"] for f in extract.extract_facts("audit-report", text, "2024-25")}
    assert facts["revenue"] == 1250000
    assert facts["total_expenses"] == 1400000
    assert facts["pbt"] == -145000
    assert facts["pat"] == -145000
    assert facts["total_assets"] == 320000
    assert facts["cash"] == 42000


def test_extract_gst_facts(tmp_path):
    text = classify.extract_text(make_pdf(tmp_path / "g.pdf", GSTR3B_LINES))
    facts = {f["metric"]: f for f in extract.extract_facts("gstr-3b", text, "2026-27", "2026-08")}
    assert facts["gst_taxable_value"]["value"] == 100000
    assert facts["gst_cgst"]["value"] == 2500 and facts["gst_sgst"]["value"] == 2500
    assert facts["gst_itc"]["value"] == 1800
    assert facts["gst_taxable_value"]["period"] == "2026-08"


def test_scale_in_lakhs():
    text = "Balance sheet (Rs. in lakhs)\nRevenue from operations 12.50\n"
    facts = {f["metric"]: f["value"] for f in extract.extract_facts("financial-statements", text, "2024-25")}
    assert facts["revenue"] == 1250000


# -------------------------------------------------------------- sorter ----
def test_sorter_files_registers_extracts_and_marks_compliance(env):
    con, vault, inbox = env
    make_pdf(inbox / "Audit Report FINAL.pdf", AUDIT_LINES)
    make_pdf(inbox / "GSTR3B Aug.pdf", GSTR3B_LINES)
    (inbox / "README.md").write_text("ignore me")
    (inbox / "random photo.jpg").write_bytes(b"\xff\xd8\xff")

    res = {r.file: r for r in sorter.sort_inbox(con)}
    assert res["Audit Report FINAL.pdf"].action == "filed"
    assert res["Audit Report FINAL.pdf"].dest == "13-accounts-and-audit/FY2024-25/audit-report-fy2024-25-2025-09-20.pdf"
    assert (vault / res["Audit Report FINAL.pdf"].dest).exists()
    assert res["Audit Report FINAL.pdf"].facts >= 5
    doc = db.get(con, "documents", res["Audit Report FINAL.pdf"].doc_id)
    assert doc["doc_type"] == "audit-report" and doc["sha256"] and doc["source"] == "inbox-auto"
    assert "fy2024-25" in doc["tags"]

    g = res["GSTR3B Aug.pdf"]
    assert g.action == "filed" and g.dest.endswith("gstr-3b-fy2026-27-2026-08-2026-09-05.pdf")
    assert "GSTR-3B" in g.compliance and "marked done" in g.compliance
    ob = db.find_one(con, "compliance", "name = ?", ["GSTR-3B (summary + payment)"])
    assert ob["last_done"] == "2026-09-05"

    ph = res["random photo.jpg"]
    assert ph.action == "review" and ph.dest.startswith("12-uploads/needs-review/")
    assert db.get(con, "documents", ph.doc_id)["status"] == "pending"
    assert "README.md" not in res
    assert sorter.pending_files() == []
    assert sorter.last_run(con)["results"]

    # finance overview sees it
    f = finance.overview(con)
    assert f["kpis"]["2024-25"]["revenue"]["value"] == 1250000
    assert f["gst_months"][0]["period"] == "2026-08" and f["gst_months"][0]["tax"] == 5000
    row = next(r for r in f["matrix"] if r["fy"] == "2024-25")
    assert row["cells"]["audit-report"]["state"] == "done"
    row26 = next(r for r in f["matrix"] if r["fy"] == "2026-27")
    assert row26["cells"]["gstr-3b"]["state"] == "partial" and row26["cells"]["gstr-3b"]["months"] == 1
    assert len(sorter.needs_review(con)) == 1


def test_sorter_duplicate_and_dry_run(env):
    con, vault, inbox = env
    make_pdf(inbox / "audit.pdf", AUDIT_LINES)
    dry = sorter.sort_inbox(con, dry_run=True)
    assert dry[0].action == "would-file" and (inbox / "audit.pdf").exists()
    sorter.sort_inbox(con)
    make_pdf(inbox / "audit copy.pdf", AUDIT_LINES)
    res = sorter.sort_inbox(con)
    assert res[0].action == "duplicate"
    assert (inbox / "duplicates" / "audit copy.pdf").exists()
    assert db.count(con, "documents") == 1


def test_manual_fact_wins(env):
    con, vault, inbox = env
    make_pdf(inbox / "audit.pdf", AUDIT_LINES)
    r = sorter.sort_inbox(con)[0]
    db.insert(con, "facts", {"fy": "2024-25", "period": "FY", "metric": "revenue", "value": 999, "method": "manual", "source_id": r.doc_id})
    assert finance.facts_by_fy(con)["2024-25"]["revenue"]["value"] == 999


# ---------------------------------------------------------------- mail ----
def test_mail_understand_rules():
    u = mail.understand("GST Portal <noreply@gst.gov.in>", "Reminder: GSTR-3B for Aug 2026 due on 20/09/2026",
                        "Dear taxpayer, please file GSTR-3B before the due date 20/09/2026 to avoid late fee of Rs. 50 per day.", [])
    assert u["category"] == "gst" and u["importance"] in ("high", "urgent")
    assert u["due_date"] == "2026-09-20" and u["amount"] == 50 and u["create_task"]
    n = mail.understand("Deals <promo@shop.example>", "50% off this weekend only", "Unsubscribe here. View in browser.", [])
    assert n["importance"] == "ignore" and n["category"] == "newsletter"
    c = mail.understand("Rahul CA <rahul@caoffice.in>", "Audited financials FY 2024-25 attached", "Please find attached the signed balance sheet. Kindly sign and send back.", ["fin.pdf"])
    assert c["category"] == "ca-accounts" and c["create_task"]


def test_mail_record_creates_task(env):
    con, *_ = env
    u = mail.understand("MCA <noreply@mca.gov.in>", "DIR-3 KYC due 30/09/2026", "Action required: file DIR-3 KYC by 30/09/2026 else DIN deactivated with penalty.", [])
    rid = mail.record(con, {"message_id": "<x@y>", "uid": "1", "received": "2026-09-08", "sender": "MCA", "subject": "DIR-3 KYC due", "attachments": "", "body_excerpt": ""}, u, "rules")
    m = db.get(con, "mail", rid)
    assert m["importance"] == "urgent" and m["task_id"]
    t = db.get(con, "tasks", m["task_id"])
    assert t["priority"] == "urgent" and t["link"] == f"mail/{rid}" and t["area"] == "compliance"


def test_load_env_and_configured(tmp_path, monkeypatch):
    envf = tmp_path / ".env"
    envf.write_text("MAIL_USER=a@b.c\nMAIL_PASSWORD='secret'\n# comment\n")
    monkeypatch.delenv("MAIL_USER", raising=False)
    monkeypatch.delenv("MAIL_PASSWORD", raising=False)
    monkeypatch.setattr(paths, "ENV_FILE", envf)
    assert mail.load_env()["MAIL_PASSWORD"] == "secret"
    assert mail.configured()


# --------------------------------------------------------------- brief ----
def test_brief_and_cycle_without_mail(env, monkeypatch):
    con, vault, inbox = env
    monkeypatch.delenv("MAIL_USER", raising=False)
    monkeypatch.delenv("MAIL_PASSWORD", raising=False)
    monkeypatch.setattr(paths, "ENV_FILE", vault / "nope.env")
    make_pdf(inbox / "audit.pdf", AUDIT_LINES)
    out = assistant.run_cycle(con)
    assert out["mail"] == [] and out["sorted"][0]["action"] == "filed"
    text = assistant.brief(con)
    assert "Filed automatically" in text and "audit.pdf" in text
    assert assistant.last_cycle(con)["sorted"]


# --------------------------------------------------------------- pages ----
@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


@pytest.mark.parametrize("url", ["/inbox", "/finance", "/brief", "/facts", "/mail", "/api/finance", "/api/brief", "/api/inbox"])
def test_assistant_pages(client, url):
    r = client.get(url)
    assert r.status_code == 200, url


def test_inbox_upload_and_sort_via_http(client, env):
    con, vault, inbox = env
    pdf = make_pdf(vault / "tmp.pdf", GSTR3B_LINES).read_bytes()
    r = client.post("/inbox/upload", files=[("files", ("GSTR3B.pdf", pdf, "application/pdf"))], follow_redirects=False)
    assert r.status_code == 303 and (inbox / "GSTR3B.pdf").exists()
    res = client.post("/api/inbox/sort").json()
    assert res[0]["action"] == "filed" and res[0]["kind"] == "gstr-3b"
