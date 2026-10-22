import json
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models import AgriculturalSourceRecord, KnowledgeSource


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXCEL_FILE = PROJECT_ROOT / "data" / "raw" / "Cleaned_Crop_Pesticide_Guide.xlsx"

SOURCE_TITLE = "Cleaned Crop Pesticide Guide"
SOURCE_FILE = "Cleaned_Crop_Pesticide_Guide.xlsx"

SHEETS = {
    "Prevention Measures": "Prevention measures",
    "Pesticide - Diseases": "Disease pesticide information",
    "Pesticide - Pests": "Pest pesticide information",
}


def clean_value(value):
    """Convert Excel cell values to JSON-safe Python values."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def get_or_create_source(db):
    source = db.scalar(
        select(KnowledgeSource).where(
            KnowledgeSource.title == SOURCE_TITLE,
            KnowledgeSource.file_name == SOURCE_FILE,
        )
    )
    if source is None:
        source = KnowledgeSource(
            title=SOURCE_TITLE,
            file_name=SOURCE_FILE,
            notes=(
                "Imported from the user-provided Excel workbook. Original sheet "
                "names, column names, and row values are preserved. All records "
                "require expert review."
            ),
            verification_status="needs_review",
        )
        db.add(source)
        db.flush()
    return source


def main():
    if not EXCEL_FILE.exists():
        raise FileNotFoundError(
            f"Excel file not found: {EXCEL_FILE}\n"
            "Copy the workbook into data/raw/ and use the expected filename."
        )

    init_db()
    inserted = 0
    skipped = 0

    with pd.ExcelFile(EXCEL_FILE, engine="openpyxl") as workbook:
        missing_sheets = set(SHEETS) - set(workbook.sheet_names)
        if missing_sheets:
            raise ValueError(
                f"Required sheets missing from workbook: {sorted(missing_sheets)}"
            )

        with SessionLocal() as db:
            try:
                source = get_or_create_source(db)

                for sheet_name in SHEETS:
                    dataframe = pd.read_excel(workbook, sheet_name=sheet_name)
                    dataframe.columns = [str(column).strip() for column in dataframe.columns]

                    for index, row in dataframe.iterrows():
                        raw_data = {
                            str(column): clean_value(value)
                            for column, value in row.items()
                        }
                        # Excel row 1 contains column headings.
                        excel_row = int(index) + 2

                        if all(value is None for value in raw_data.values()):
                            continue

                        existing = db.scalar(
                            select(AgriculturalSourceRecord.id).where(
                                AgriculturalSourceRecord.source_id == source.id,
                                AgriculturalSourceRecord.sheet_name == sheet_name,
                                AgriculturalSourceRecord.source_row == excel_row,
                            )
                        )
                        if existing is not None:
                            skipped += 1
                            continue

                        crop = raw_data.get("Crop")
                        problem = (
                            raw_data.get("Disease")
                            or raw_data.get("Disease / Pest")
                            or raw_data.get("Disease Name (Marathi)")
                        )
                        db.add(
                            AgriculturalSourceRecord(
                                source_id=source.id,
                                sheet_name=sheet_name,
                                source_row=excel_row,
                                crop_name=str(crop).strip() if crop is not None else None,
                                problem_name=(
                                    str(problem).strip() if problem is not None else None
                                ),
                                raw_data=raw_data,
                                verification_status="needs_review",
                                is_active=False,
                            )
                        )
                        inserted += 1

                db.commit()
                print("Excel import completed.")
                print(f"Knowledge source ID: {source.id}")
                print(f"New records inserted: {inserted}")
                print(f"Existing records skipped: {skipped}")
                print("Verification status: needs_review")
                print("All imported records remain inactive.")
            except Exception:
                db.rollback()
                raise


if __name__ == "__main__":
    main()
