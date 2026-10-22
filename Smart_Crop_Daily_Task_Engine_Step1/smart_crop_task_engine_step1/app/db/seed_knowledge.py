"""Import the supplied fertigation schedule as inactive, review-pending records.

The PDF itself is not present in this checkout. Values below are the user's
provided transcription and must be checked against the source before activation.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models import FertilizerRule, KnowledgeSource

FERTIGATION_TITLE = "Fertigation Schedule - Tomato and Chilli"
FERTIGATION_FILE = "ferti_schedule.pdf"
F1_CHILLI_TITLE = "F1 Chilli Crop Schedule"
F1_CHILLI_FILE = None

# Values are kg of fertilizer per hectare for the full listed stage, as
# transcribed by the user. Stage bounds are provisional and non-overlapping.
# Tuples: crop, stage, day_start, day_end, fertilizer, stage_amount_kg_per_ha
RULES = [
    ("tomato", "Plant establishment", 0, 9, "19:19:19", 65.78),
    ("tomato", "Plant establishment", 0, 9, "13:0:45", 27.77),
    ("tomato", "Plant establishment", 0, 9, "Urea", 8.44),
    ("tomato", "Flower initiation to flowering", 10, 39, "12:61:0", 40.98),
    ("tomato", "Flower initiation to flowering", 10, 39, "13:0:45", 222.22),
    ("tomato", "Flower initiation to flowering", 10, 39, "Urea", 100.27),
    ("tomato", "Flowering to fruit set", 40, 69, "19:19:19", 65.78),
    ("tomato", "Flowering to fruit set", 40, 69, "13:0:45", 138.88),
    ("tomato", "Flowering to fruit set", 40, 69, "Urea", 63.90),
    ("tomato", "Picking period", 70, 149, "12:61:0", 20.49),
    ("tomato", "Picking period", 70, 149, "13:0:45", 111.11),
    ("tomato", "Picking period", 70, 149, "Urea", 50.14),
    ("chilli", "Plant establishment", 0, 9, "19:19:19", 21.05),
    ("chilli", "Plant establishment", 0, 9, "13:0:45", 8.88),
    ("chilli", "Plant establishment", 0, 9, "Urea", 14.86),
    ("chilli", "Flower initiation to flowering", 10, 39, "12:61:0", 13.11),
    ("chilli", "Flower initiation to flowering", 10, 39, "13:0:45", 71.04),
    ("chilli", "Flower initiation to flowering", 10, 39, "Urea", 80.72),
    ("chilli", "Flowering set to fruit picking", 40, 69, "19:19:19", 21.05),
    ("chilli", "Flowering set to fruit picking", 40, 69, "13:0:45", 44.40),
    ("chilli", "Flowering set to fruit picking", 40, 69, "Urea", 56.91),
    ("chilli", "Picking period", 70, 77, "12:61:0", 6.52),
    ("chilli", "Picking period", 70, 77, "13:0:45", 35.52),
    ("chilli", "Picking period", 70, 77, "Urea", 40.38),
]


def get_or_create_source(
    db: Session, *, title: str, file_name: str | None, notes: str
) -> KnowledgeSource:
    source = db.scalar(
        select(KnowledgeSource).where(
            KnowledgeSource.title == title,
            KnowledgeSource.file_name == file_name,
        )
    )
    if source is None:
        source = KnowledgeSource(
            title=title,
            file_name=file_name,
            notes=notes,
            verification_status="needs_review",
        )
        db.add(source)
        db.flush()
    elif source.notes != notes:
        source.notes = notes
    return source


def seed_knowledge(db: Session) -> tuple[int, int]:
    fertigation_source = get_or_create_source(
        db,
        title=FERTIGATION_TITLE,
        file_name=FERTIGATION_FILE,
        notes=(
            "Source: user-supplied ferti_schedule.pdf. The source is available "
            "in the conversation but may not be copied into the local project. "
            "The schedule lists hybrid NPK requirements of 200:250:250 kg/ha "
            "for tomato and 120:80:80 kg/ha for chilli, with 75% of phosphorus "
            "applied basally. Stage amounts and day ranges in this database are "
            "pending verification. Keep all imported rules inactive until "
            "the source, crop stage, units, and application instructions are reviewed."
        ),
    )
    # Keep this distinct source registered for provenance. No F1 quantities are
    # imported by this seed; that schedule uses a separate basis and dataset.
    get_or_create_source(
        db,
        title=F1_CHILLI_TITLE,
        file_name=F1_CHILLI_FILE,
        notes=(
            "Separate per-acre chilli schedule. Reference only; no rules imported "
            "by the fertigation seed. Add its actual source file before transcription."
        ),
    )

    inserted = 0
    for crop, stage, start, end, fertilizer, amount in RULES:
        existing = db.scalar(
            select(FertilizerRule.id).where(
                FertilizerRule.source_file == FERTIGATION_FILE,
                FertilizerRule.crop_name == crop,
                FertilizerRule.stage_name == stage,
                FertilizerRule.day_start == start,
                FertilizerRule.day_end == end,
                FertilizerRule.fertilizer_name == fertilizer,
            )
        )
        if existing is not None:
            continue
        db.add(
            FertilizerRule(
                crop_name=crop,
                stage_name=stage,
                day_start=start,
                day_end=end,
                days_basis="after_transplanting",
                fertilizer_name=fertilizer,
                amount=amount,
                unit="kg",
                area_basis="per hectare per stage",
                application_method="fertigation",
                frequency="once every 3 days during stage",
                instructions=(
                    "Stage total transcribed from the supplied schedule; do not "
                    "treat as a per-event dose. Stage bounds are provisional."
                ),
                source_file=FERTIGATION_FILE,
                verification_status="needs_review",
                is_active=False,
            )
        )
        inserted += 1

    db.commit()
    return fertigation_source.id, inserted


def main() -> None:
    init_db()
    with SessionLocal() as db:
        source_id, inserted = seed_knowledge(db)
    print(f"Knowledge source ID: {source_id}")
    print(f"New fertilizer rules inserted: {inserted}")
    print("All imported rules remain inactive pending verification.")


if __name__ == "__main__":
    main()
