from sqlalchemy import text
import os

# Utility to apply a raw SQL file after tables are created
def apply_sql_file(path: str, engine) -> None:
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
    with engine.begin() as conn:
        conn.execute(text(sql))