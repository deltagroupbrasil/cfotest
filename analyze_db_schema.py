#!/usr/bin/env python3
"""
Analyze SQLite database schema for Cloud SQL migration
"""
import sqlite3
import os

def analyze_sqlite_schema():
    """Analyze current SQLite database schema"""
    db_path = "web_ui/delta_cfo.db"

    if not os.path.exists(db_path):
        print("Database not found at:", db_path)
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print("=== CURRENT DATABASE SCHEMA ===")
        print(f"Database: {db_path}")
        print(f"Tables found: {len(tables)}")
        print()

        for (table_name,) in tables:
            print(f"Table: {table_name}")
            print("-" * 40)

            # Get table schema
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            schema = cursor.fetchone()
            if schema:
                print(schema[0])

            # Get sample data count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"Records: {count}")

            # Show column info
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            print("Columns:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]}) {'NOT NULL' if col[3] else 'NULL'} {'PRIMARY KEY' if col[5] else ''}")

            print()

        conn.close()

    except Exception as e:
        print(f"Error analyzing database: {e}")

if __name__ == "__main__":
    analyze_sqlite_schema()