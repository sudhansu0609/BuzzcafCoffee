"""OCR for scanned PDFs and photos, so the sorter can read them like any other file.

    from app import ocr
    ocr.available()              # True when an engine is importable
    ocr.pdf_text(path)           # render pages (pypdfium2) -> recognise text (RapidOCR)
    ocr.image_text(path)         # photo / screenshot -> text

Engine order: RapidOCR (pip `rapidocr-onnxruntime`, no external binary, works
offline) then pytesseract if a Tesseract binary is on PATH. Both are optional:
without either, scanned files are parked for a human as before.

Results are cached next to the DB (ops/data/ocr-cache/<sha256>.txt) so a file
is only OCR'd once.
"""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path

from . import paths

RENDER_SCALE = 2.0          # 72 dpi * 2 = 144 dpi: enough for print, fast on CPU
MAX_PAGES = int(os.environ.get("BUZZCAF_OCR_PAGES", "8"))
MIN_TEXT_PER_PAGE = 40      # a "text" PDF with fewer chars per page than this is treated as scanned
_engine = None
_engine_name = ""


def _load_engine():
    global _engine, _engine_name
    if _engine is not None:
        return _engine
    if os.environ.get("BUZZCAF_OCR", "1") == "0":
        _engine, _engine_name = False, ""
        return False
    try:
        from rapidocr_onnxruntime import RapidOCR
        _engine, _engine_name = RapidOCR(), "rapidocr"
        return _engine
    except Exception:  # noqa: BLE001 - fall through to tesseract
        pass
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        _engine, _engine_name = pytesseract, "tesseract"
        return _engine
    except Exception:  # noqa: BLE001
        _engine, _engine_name = False, ""
        return False


def available() -> bool:
    return bool(_load_engine())


def engine_name() -> str:
    _load_engine()
    return _engine_name


# ---------------------------------------------------------------- cache ----
def _cache_dir() -> Path:
    d = paths.DATA_DIR / "ocr-cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _cached(path: Path) -> tuple[Path, str | None]:
    cp = _cache_dir() / f"{_digest(path)}.txt"
    if cp.exists():
        return cp, cp.read_text(encoding="utf-8", errors="replace")
    return cp, None


# -------------------------------------------------------------- engines ----
def _recognise(pil_image) -> str:
    """Text from one PIL image, reading order top-to-bottom, left-to-right."""
    eng = _load_engine()
    if not eng:
        return ""
    if _engine_name == "rapidocr":
        import numpy as np
        result, _ = eng(np.array(pil_image.convert("RGB")))
        if not result:
            return ""
        # each item: [box(4 points), text, score]; group into lines by the box's vertical centre
        items = []
        for box, text, score in result:
            ys = [p[1] for p in box]
            xs = [p[0] for p in box]
            items.append(((min(ys) + max(ys)) / 2, min(xs), max(ys) - min(ys), text, float(score)))
        items.sort(key=lambda t: (t[0], t[1]))
        lines: list[list] = []
        for it in items:
            if it[4] < 0.3:
                continue
            if lines and abs(lines[-1][0][0] - it[0]) < max(8, it[2] * 0.6):
                lines[-1].append(it)
            else:
                lines.append([it])
        return "\n".join(" ".join(t[3] for t in sorted(line, key=lambda t: t[1])) for line in lines)
    # tesseract
    return eng.image_to_string(pil_image) or ""


def image_text(path: Path) -> str:
    if not available():
        return ""
    cp, hit = _cached(path)
    if hit is not None:
        return hit
    from PIL import Image, ImageOps
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if max(im.size) > 2400:                       # phone photos: shrink, OCR is happier and faster
            im.thumbnail((2400, 2400))
        text = _recognise(im)
    cp.write_text(text, encoding="utf-8")
    return text


def pdf_text(path: Path, max_pages: int = MAX_PAGES) -> str:
    if not available():
        return ""
    cp, hit = _cached(path)
    if hit is not None:
        return hit
    import pypdfium2 as pdfium
    out: list[str] = []
    pdf = pdfium.PdfDocument(str(path))
    try:
        for i in range(min(len(pdf), max_pages)):
            page = pdf[i]
            bitmap = page.render(scale=RENDER_SCALE)
            out.append(_recognise(bitmap.to_pil()))
            page.close()
    finally:
        pdf.close()
    text = "\n".join(out)
    cp.write_text(text, encoding="utf-8")
    return text


def looks_scanned(text: str, pages: int) -> bool:
    """True when a PDF's text layer is missing or nearly empty."""
    return len(text.strip()) < MIN_TEXT_PER_PAGE * max(1, pages)
