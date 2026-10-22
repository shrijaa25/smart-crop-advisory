"""Preserve the supplied chilli schedule PDF text page-by-page for review.

PDF extraction deliberately does not convert free text into active advice.
Every page is retained as an inactive, needs_review agricultural source record.
"""
from pathlib import Path

from sqlalchemy import select
from pypdf import PdfReader
import fitz

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models import AgriculturalSourceRecord, KnowledgeSource

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_FILE = PROJECT_ROOT / "data" / "raw" / "Chilli-Crop-Schedule-English .pdf"
SOURCE_NAME = PDF_FILE.name


def extract_fertilizer_rows(page_number: int) -> list[dict[str, str | int | None]]:
    """Read exact text cells from the fertilizer table using page coordinates.

    Bounds follow the visible source table columns. Results remain raw review
    records; they are never converted into active application rules.
    """
    with fitz.open(str(PDF_FILE)) as document:
        page = document[page_number - 1]
        words = sorted(page.get_text("words"), key=lambda word: (word[1], word[0]))
    bands: list[list[tuple]] = []
    for word in words:
        if word[1] < 138 or word[1] > 414:
            continue
        if not bands or word[1] - min(item[1] for item in bands[-1]) > 2.5:
            bands.append([word])
        else:
            bands[-1].append(word)

    ranges = [
        (138, 174, "Basal dose"),
        (174, 212, "3 to 30 days"),
        (212, 269, "31 to 60 days"),
        (269, 325, "61 to 90 days"),
        (325, 381, "91 to 120 days"),
        (381, 414, "121 to 180"),
    ]
    rows = []
    for band in bands:
        band.sort(key=lambda word: word[0])
        cells = [[], [], []]
        for word in band:
            x, token = word[0], word[4]
            if 130 <= x < 240:
                cells[0].append(token)
            elif 240 <= x < 325:
                cells[1].append(token)
            elif 325 <= x < 445:
                cells[2].append(token)
        fertilizer, daily_dose, quantity = (" ".join(cell).strip() for cell in cells)
        y = band[0][1]
        age_range = next(label for low, high, label in ranges if low <= y < high)
        if fertilizer and (daily_dose or quantity) and not fertilizer.lower().startswith("fertilizers"):
            rows.append({
                "source_page": page_number,
                "source_age_range_text": age_range,
                "fertilizer_text": fertilizer,
                "dose_per_day_per_acre_text": daily_dose,
                "quantity_per_acre_text": quantity or None,
            })
    return rows


def import_pdf() -> tuple[int, int]:
    if not PDF_FILE.exists():
        raise FileNotFoundError(PDF_FILE)
    reader = PdfReader(str(PDF_FILE))
    init_db()
    inserted = 0
    with SessionLocal() as db:
        source = db.scalar(select(KnowledgeSource).where(KnowledgeSource.file_name == SOURCE_NAME))
        if source is None:
            source = KnowledgeSource(
                title="Chilli Crop Schedule English",
                file_name=SOURCE_NAME,
                notes="Page text extracted verbatim for expert transcription and review. No schedule values are activated automatically.",
                verification_status="needs_review",
            )
            db.add(source)
            db.flush()
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                text = "[No extractable text; page may require OCR.]"
            existing = db.scalar(select(AgriculturalSourceRecord).where(
                AgriculturalSourceRecord.source_id == source.id,
                AgriculturalSourceRecord.sheet_name == "PDF page",
                AgriculturalSourceRecord.source_row == page_num,
            ))
            raw_data = {
                "page_text": text,
                "fertilizer_schedule_rows": extract_fertilizer_rows(page_num),
                "spraying_schedule_text": text,
                "extraction": "pypdf text plus coordinate-based fertilizer cells; verify every cell against the source image",
                "review_flags": [
                    "All extracted rows need agricultural review before rule creation.",
                    "Spray product mixtures, dose associations, product labels, weather restrictions, and pre-harvest intervals require verification.",
                    "The source provides no machine-verified treatment safety or label details.",
                ],
            }
            if existing is not None:
                # Refresh extracted source text without changing any curator's
                # review status or activation decision.
                existing.raw_data = raw_data
                continue
            db.add(AgriculturalSourceRecord(
                source_id=source.id,
                sheet_name="PDF page",
                source_row=page_num,
                crop_name="chilli",
                raw_data=raw_data,
                verification_status="needs_review",
                is_active=False,
            ))
            inserted += 1
        db.commit()
        return source.id, inserted


if __name__ == "__main__":
    source_id, inserted = import_pdf()
    print(f"Source ID: {source_id}; pages added: {inserted}; status: needs_review, inactive")
