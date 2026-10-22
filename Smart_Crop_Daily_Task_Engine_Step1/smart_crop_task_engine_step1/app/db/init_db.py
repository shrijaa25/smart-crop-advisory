from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401
from sqlalchemy import inspect, text


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    # create_all does not alter existing SQLite tables. Apply additive changes
    # without resetting existing farmer/task data.
    inspector = inspect(engine)
    additions = {
        "daily_tasks": {"completed_at": "DATETIME", "weather_context": "JSON"},
        "image_predictions": {
            "task_id": "INTEGER REFERENCES daily_tasks(id)",
            "observation_id": "INTEGER REFERENCES farmer_observations(id)",
        },
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            if not inspector.has_table(table):
                continue
            present = {column["name"] for column in inspector.get_columns(table)}
            for name, sql_type in columns.items():
                if name not in present:
                    connection.execute(
                        text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {sql_type}')
                    )
