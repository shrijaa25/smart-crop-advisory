from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import FertilizerRule, KnowledgeSource


def main() -> None:
    with SessionLocal() as db:
        print("\n========== KNOWLEDGE SOURCES ==========")

        sources = db.scalars(
            select(KnowledgeSource).order_by(KnowledgeSource.id)
        ).all()

        for source in sources:
            print(
                f"ID: {source.id} | "
                f"Title: {source.title} | "
                f"File: {source.file_name} | "
                f"Status: {source.verification_status}"
            )

        print("\n========== FERTILIZER RULE SUMMARY ==========")

        total = db.scalar(select(func.count()).select_from(FertilizerRule))
        inactive = db.scalar(
            select(func.count())
            .select_from(FertilizerRule)
            .where(FertilizerRule.is_active.is_(False))
        )

        print(f"Total fertilizer rules: {total}")
        print(f"Inactive fertilizer rules: {inactive}")

        print("\n========== FERTIGATION RULES ==========")

        rules = db.scalars(
            select(FertilizerRule)
            .where(FertilizerRule.source_file == "ferti_schedule.pdf")
            .order_by(
                FertilizerRule.crop_name,
                FertilizerRule.day_start,
                FertilizerRule.fertilizer_name,
            )
        ).all()

        print(f"Rules from ferti_schedule.pdf: {len(rules)}")

        for rule in rules:
            print(
                f"{rule.crop_name} | "
                f"Days {rule.day_start}-{rule.day_end} | "
                f"{rule.stage_name} | "
                f"{rule.fertilizer_name} | "
                f"{rule.amount} {rule.unit} | "
                f"Active: {rule.is_active} | "
                f"Status: {rule.verification_status}"
            )


if __name__ == "__main__":
    main()
