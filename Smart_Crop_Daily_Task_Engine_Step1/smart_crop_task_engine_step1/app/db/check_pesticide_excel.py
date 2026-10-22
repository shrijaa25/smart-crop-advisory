"""Read-only status summary for imported pesticide workbook rows."""

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import AgriculturalSourceRecord, KnowledgeSource


def main() -> None:
    with SessionLocal() as db:
        source = db.scalar(
            select(KnowledgeSource).where(
                KnowledgeSource.file_name == "Cleaned_Crop_Pesticide_Guide.xlsx"
            )
        )
        if source is None:
            print("Pesticide workbook source not found.")
            return

        print(f"Source: {source.title} ({source.file_name})")
        print("Counts by sheet, verification status, and active state:")

        grouped_counts = db.execute(
            select(
                AgriculturalSourceRecord.sheet_name,
                AgriculturalSourceRecord.verification_status,
                AgriculturalSourceRecord.is_active,
                func.count(AgriculturalSourceRecord.id),
            )
            .where(AgriculturalSourceRecord.source_id == source.id)
            .group_by(
                AgriculturalSourceRecord.sheet_name,
                AgriculturalSourceRecord.verification_status,
                AgriculturalSourceRecord.is_active,
            )
            .order_by(
                AgriculturalSourceRecord.sheet_name,
                AgriculturalSourceRecord.verification_status,
                AgriculturalSourceRecord.is_active,
            )
        ).all()

        if not grouped_counts:
            print("No imported worksheet rows found.")
            return

        total = 0
        all_inactive = True
        all_need_review = True
        for sheet_name, verification_status, is_active, count in grouped_counts:
            print(
                f"{sheet_name} | status={verification_status} | "
                f"active={is_active} | records={count}"
            )
            total += count
            all_inactive = all_inactive and not is_active
            all_need_review = all_need_review and verification_status == "needs_review"

        print(f"Total imported records: {total}")
        print(f"All records inactive: {all_inactive}")
        print(f"All records marked needs_review: {all_need_review}")
        print(
            "These rows are preserved source material, not approved recommendations. "
            "Verify labels, crop applicability, dose units, pre-harvest intervals, "
            "and safety restrictions before use."
        )


if __name__ == "__main__":
    main()
