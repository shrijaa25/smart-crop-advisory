from datetime import date

from app.db.session import SessionLocal
from app.services.task_engine import generate_daily_tasks


def main() -> None:
    with SessionLocal() as db:
        count = generate_daily_tasks(db, target_date=date.today())

    print(f"New eligible reminders created: {count}")
    print("Unverified fertilizer rules were excluded.")


if __name__ == "__main__":
    main()
