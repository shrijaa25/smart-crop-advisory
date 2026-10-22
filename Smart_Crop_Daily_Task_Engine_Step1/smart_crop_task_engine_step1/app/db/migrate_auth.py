from sqlalchemy import inspect, text

from app.db.session import engine


def main() -> None:
    inspector = inspect(engine)
    if "farmers" not in inspector.get_table_names():
        raise RuntimeError(
            "The farmers table does not exist. Initialize the database first."
        )

    columns = {column["name"] for column in inspector.get_columns("farmers")}
    if "password_hash" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE farmers ADD COLUMN password_hash VARCHAR(255)")
            )
        print("Added farmers.password_hash")
    else:
        print("farmers.password_hash already exists")
    print("Authentication database migration completed.")


if __name__ == "__main__":
    main()
