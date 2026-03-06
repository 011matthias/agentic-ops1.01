#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "sqlalchemy",
#   "psycopg2-binary",
#   "python-dotenv",
# ]
# ///
"""
Migration: Add period_end and interval columns to pending_orders.

Fix: fix1-a2-dashboard-missing-fields
Date: 2026-02-18

Run against local SQLite:
    uv run migrations/add_period_end_interval.py

Run against production (Railway):
    DATABASE_URL="postgresql://..." uv run migrations/add_period_end_interval.py
"""

import os
import sys
from pathlib import Path

# Load .env from the automations root
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

database_url = os.environ.get("DATABASE_URL", "sqlite:///./logs.db")

print(f"Connecting to: {database_url.split('@')[-1] if '@' in database_url else database_url}")

from sqlalchemy import create_engine, text

engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
)

is_sqlite = "sqlite" in database_url

migrations = [
    ("period_end", "ALTER TABLE pending_orders ADD COLUMN period_end DATE"),
    ("interval",   "ALTER TABLE pending_orders ADD COLUMN interval VARCHAR(50)"),
]

with engine.connect() as conn:
    for col_name, sql in migrations:
        try:
            if is_sqlite:
                conn.execute(text(sql))
            else:
                # PostgreSQL: IF NOT EXISTS goes after ADD COLUMN, before column name
                # e.g. ALTER TABLE t ADD COLUMN IF NOT EXISTS col_name TYPE
                pg_sql = sql.replace("ADD COLUMN ", "ADD COLUMN IF NOT EXISTS ")
                conn.execute(text(pg_sql))
            conn.commit()
            print(f"  ✓ Added column: {col_name}")
        except Exception as e:
            err = str(e).lower()
            if "duplicate column" in err or "already exists" in err:
                print(f"  - Skipped (already exists): {col_name}")
            else:
                print(f"  ✗ Error adding {col_name}: {e}")
                sys.exit(1)

print("\nMigration complete.")
