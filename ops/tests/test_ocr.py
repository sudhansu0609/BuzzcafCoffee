"""OCR path: scanned (image-only) PDFs and photos are read, classified and mined like text PDFs.

Skipped when no OCR engine is installed (pip install rapidocr-onnxruntime pypdfium2).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

OPS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPS_ROOT))
if "app.paths" not in sys.modules:
    os.environ.setdefault("BUZZCAF_OPS_DATA", tempfile.mkdtemp(prefix="buzzcaf-ops-test-"))
os.environ["BUZZCAF_ASSISTANT_LLM"] = "0"

from app import classify, extract, ocr, paths, sorter, db  # noqa: E402

pytestmark = pytest.mark.skipif(not ocr.available(), reason="no OCR engine installed")

GSTR3B = [
    "Form GSTR-3B",
    "GSTIN 27AAKCB6111C1Z3   Legal name BUZZCAF PRIVATE LIMITED",
    "Tax period 08/2026   Financial year 2026-27",
    "3.1 Details of Outward Supplies and inward supplies liable to reverse charge",
    "(a) Outward taxable supplies (other than zero rated, nil rated and exempted)  1,00,000.00  0.00  2,500.00  2,500.00",
    "4. Eligible ITC",
    "Late fee 0.00",
    "ARN AA270826123456Z   Date of filing 05/09/2026",
]
LICENCE = [
    "FOOD SAFETY AND STANDARDS AUTHORITY OF INDIA",
    "Licence No 11522079000056",
    "Kind of Business: Repacker",
    "Valid upto 23/06/2024",
    "BUZZCAF PRIVATE LIMITED, Pune",
]


def page_image(lines, w=1654, h=2339):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("arial.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    y = 120
    for line in lines:
        d.text((100, y), line, fill="black", font=font)
        y += 60
    return im


def test_engine_reports_name():
    assert ocr.engine_name() in ("rapidocr", "tesseract")


def test_scanned_pdf_is_read_and_classified(tmp_path):
    scan = tmp_path / "scan.pdf"
    page_image(GSTR3B).save(scan, "PDF", resolution=200)
    text = classify.extract_text(scan)
    assert text.startswith("[ocr]") and "GSTR" in text.replace(" ", "").upper()
    g = classify.classify(scan, text)
    assert g.kind == "gstr-3b"
    assert g.period == "2026-08" and g.fy == "2026-27"
    assert g.number == "AA270826123456Z"
    assert g.when == "2026-09-05"
    assert any("OCR" in r for r in g.reasons)
    facts = {f["metric"]: f["value"] for f in extract.extract_facts(g.kind, text, g.fy, g.period)}
    assert facts["gst_taxable_value"] == 100000
    # second read hits the cache (no re-render)
    assert classify.extract_text(scan) == text


def test_photo_of_licence(tmp_path):
    photo = tmp_path / "IMG_20260909_120000.jpg"
    page_image(LICENCE, 1200, 800).save(photo, "JPEG", quality=85)
    text = classify.extract_text(photo)
    g = classify.classify(photo, text)
    assert g.kind == "fssai-licence"
    assert g.number == "11522079000056"
    assert g.expiry == "2024-06-23"
    assert g.confidence >= sorter.THRESHOLD


def test_blank_image_still_parked(tmp_path):
    from PIL import Image
    blank = tmp_path / "blank.png"
    Image.new("RGB", (400, 300), "white").save(blank)
    text = classify.extract_text(blank)
    g = classify.classify(blank, text)
    assert g.kind == "photo" and g.confidence < sorter.THRESHOLD


def test_sorter_files_scanned_licence_with_expiry(tmp_path, monkeypatch):
    vault, inbox = tmp_path / "vault", tmp_path / "inbox"
    vault.mkdir(); inbox.mkdir()
    monkeypatch.setattr(paths, "VAULT_DIR", vault)
    monkeypatch.setattr(paths, "INBOX_DIR", inbox)
    monkeypatch.setattr(sorter, "SETTLE_SECONDS", 0)
    con = db.connect(); db.init_schema(con)
    con.execute("DELETE FROM documents"); con.commit()
    page_image(LICENCE, 1200, 800).save(inbox / "licence photo.jpg", "JPEG", quality=85)
    r = sorter.sort_inbox(con)[0]
    assert r.action == "filed" and r.dest.startswith("03-fssai/")
    doc = db.get(con, "documents", r.doc_id)
    assert doc["expiry_date"] == "2024-06-23" and doc["doc_type"] == "fssai-licence" and doc["number"] == "11522079000056"
    con.close()


def test_read_view(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    vault = tmp_path / "vault"; vault.mkdir()
    monkeypatch.setattr(paths, "VAULT_DIR", vault)
    page_image(LICENCE, 1200, 800).save(vault / "x.jpg", "JPEG")
    with TestClient(create_app()) as c:
        r = c.get("/vault/text/x.jpg")
        assert r.status_code == 200 and "OCR" in r.text
        assert c.get("/vault/text/../secret").status_code in (404, 400, 422)
