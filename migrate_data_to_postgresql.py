#!/usr/bin/env python3
"""
DeltaCFOAgent - Data Migration Script
====================================

This script migrates all existing data from SQLite databases to PostgreSQL.
Run this after setting up the PostgreSQL schema to transfer all data.

Usage:
    python migrate_data_to_postgresql.py [--dry-run] [--force]

Options:
    --dry-run    Show what would be migrated without actually doing it
    --force      Force migration even if target tables have data
"""

import os
import sys
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Import centralized database manager
from web_ui.database import db_manager

class DataMigrator:
    """Handles migration from SQLite databases to PostgreSQL"""

    def __init__(self, dry_run=False, force=False):
        self.dry_run = dry_run
        self.force = force
        self.pg_db = db_manager
        self.stats = {
            'tables_migrated': 0,
            'records_migrated': 0,
            'errors': 0,
            'skipped': 0
        }

    def migrate_all(self):
        """Run complete migration from all SQLite sources"""
        print("🚀 Starting DeltaCFOAgent Data Migration to PostgreSQL")
        print(f"Target Database: {self.pg_db.db_type}")
        print(f"Dry Run: {self.dry_run}")
        print(f"Force: {self.force}")
        print("=" * 60)

        # Main transactions database
        self.migrate_main_transactions()

        # Crypto pricing database
        self.migrate_crypto_pricing()

        # Crypto invoice system
        self.migrate_crypto_invoices()

        # Summary
        print("\n" + "=" * 60)
        print("📊 Migration Summary:")
        print(f"✅ Tables migrated: {self.stats['tables_migrated']}")
        print(f"📄 Records migrated: {self.stats['records_migrated']}")
        print(f"⚠️ Errors: {self.stats['errors']}")
        print(f"⏭️ Skipped: {self.stats['skipped']}")

        if self.dry_run:
            print("\n🔍 This was a DRY RUN - no data was actually migrated")
        else:
            print("\n🎉 Migration completed successfully!")

    def migrate_main_transactions(self):
        """Migrate main transactions database"""
        print("\n📊 Migrating Main Transactions Database...")

        db_path = "web_ui/delta_transactions.db"
        if not os.path.exists(db_path):
            print(f"⚠️ Main database not found at {db_path}")
            return

        sqlite_conn = sqlite3.connect(db_path)
        sqlite_conn.row_factory = sqlite3.Row

        # Migrate transactions table
        self._migrate_table(
            sqlite_conn=sqlite_conn,
            table_name="transactions",
            source_query="""
                SELECT id, date, description, amount, type, category, subcategory,
                       entity, origin, destination, confidence_score, ai_generated,
                       created_at, updated_at
                FROM transactions ORDER BY id
            """
        )

        # Migrate learned patterns
        self._migrate_table(
            sqlite_conn=sqlite_conn,
            table_name="learned_patterns",
            source_query="""
                SELECT id, description_pattern, suggested_category, suggested_subcategory,
                       suggested_entity, confidence_score, usage_count, created_at, updated_at
                FROM learned_patterns ORDER BY id
            """
        )

        # Migrate user interactions
        self._migrate_table(
            sqlite_conn=sqlite_conn,
            table_name="user_interactions",
            source_query="""
                SELECT id, transaction_id, original_category, user_category,
                       original_entity, user_entity, feedback_type, created_at
                FROM user_interactions ORDER BY id
            """
        )

        sqlite_conn.close()

    def migrate_crypto_pricing(self):
        """Migrate crypto pricing data"""
        print("\n💰 Migrating Crypto Pricing Database...")

        # Check if crypto pricing system exists and has a database
        db_path = "crypto_invoices.db"  # Legacy path
        if os.path.exists(db_path):
            sqlite_conn = sqlite3.connect(db_path)
            sqlite_conn.row_factory = sqlite3.Row

            # Check if crypto_historic_prices table exists
            cursor = sqlite_conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='crypto_historic_prices'
            """)

            if cursor.fetchone():
                self._migrate_table(
                    sqlite_conn=sqlite_conn,
                    table_name="crypto_historic_prices",
                    source_query="""
                        SELECT date, symbol, price_usd, created_at, updated_at
                        FROM crypto_historic_prices ORDER BY date, symbol
                    """
                )
            else:
                print("ℹ️ No crypto_historic_prices table found in legacy database")

            sqlite_conn.close()
        else:
            print("ℹ️ No legacy crypto pricing database found - this is expected if already migrated")

    def migrate_crypto_invoices(self):
        """Migrate crypto invoice system data"""
        print("\n🧾 Migrating Crypto Invoice System...")

        invoice_db_path = "crypto_invoice_system/crypto_invoices.db"
        if not os.path.exists(invoice_db_path):
            print(f"ℹ️ Invoice database not found at {invoice_db_path}")
            return

        sqlite_conn = sqlite3.connect(invoice_db_path)
        sqlite_conn.row_factory = sqlite3.Row

        # Migrate clients
        self._migrate_table(
            sqlite_conn=sqlite_conn,
            table_name="clients",
            source_query="""
                SELECT id, name, contact_email, billing_address, tax_id, notes,
                       created_at, updated_at
                FROM clients ORDER BY id
            """
        )

        # Migrate invoices
        self._migrate_table(
            sqlite_conn=sqlite_conn,
            table_name="invoices",
            source_query="""
                SELECT id, invoice_number, client_id, status, amount_usd, crypto_currency,
                       crypto_amount, crypto_network, exchange_rate, deposit_address, memo_tag,
                       billing_period, description, line_items, due_date, issue_date, paid_at,
                       payment_tolerance, pdf_path, qr_code_path, notes, created_at, updated_at
                FROM invoices ORDER BY id
            """
        )

        # Migrate payment transactions
        self._migrate_table(
            sqlite_conn=sqlite_conn,
            table_name="payment_transactions",
            source_query="""
                SELECT id, invoice_id, transaction_hash, amount_received, currency, network,
                       deposit_address, status, confirmations, required_confirmations,
                       is_manual_verification, verified_by, mexc_transaction_id, raw_api_response,
                       detected_at, confirmed_at, created_at
                FROM payment_transactions ORDER BY id
            """
        )

        # Migrate other invoice system tables if they exist
        for table in ["mexc_addresses", "address_usage", "polling_logs", "notifications", "system_config"]:
            try:
                cursor = sqlite_conn.cursor()
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if cursor.fetchone():
                    self._migrate_table(
                        sqlite_conn=sqlite_conn,
                        table_name=table,
                        source_query=f"SELECT * FROM {table} ORDER BY id"
                    )
            except Exception as e:
                print(f"⚠️ Could not migrate table {table}: {e}")

        sqlite_conn.close()

    def _migrate_table(self, sqlite_conn, table_name, source_query):
        """Migrate a single table from SQLite to PostgreSQL"""
        print(f"  📋 Migrating table: {table_name}")

        try:
            # Check if table exists in PostgreSQL
            pg_check = self.pg_db.execute_query(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
                (table_name,),
                fetch_one=True
            )

            if not pg_check or pg_check[0] == 0:
                print(f"    ⚠️ Table {table_name} does not exist in PostgreSQL - skipping")
                self.stats['skipped'] += 1
                return

            # Check if target table has data
            existing_count = self.pg_db.execute_query(
                f"SELECT COUNT(*) FROM {table_name}",
                fetch_one=True
            )[0]

            if existing_count > 0 and not self.force:
                print(f"    ⏭️ Table {table_name} already has {existing_count} records - skipping (use --force to override)")
                self.stats['skipped'] += 1
                return

            # Get data from SQLite
            cursor = sqlite_conn.cursor()
            cursor.execute(source_query)
            rows = cursor.fetchall()

            if not rows:
                print(f"    ℹ️ No data found in source table {table_name}")
                return

            print(f"    📊 Found {len(rows)} records to migrate")

            if self.dry_run:
                print(f"    🔍 DRY RUN: Would migrate {len(rows)} records")
                self.stats['records_migrated'] += len(rows)
                self.stats['tables_migrated'] += 1
                return

            # Clear existing data if force is enabled
            if existing_count > 0 and self.force:
                print(f"    🗑️ Clearing {existing_count} existing records (force mode)")
                self.pg_db.execute_query(f"DELETE FROM {table_name}")

            # Prepare insert statement
            first_row = dict(rows[0])
            columns = list(first_row.keys())
            placeholders = ', '.join(['%s'] * len(columns))
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            # Batch insert data
            batch_size = 100
            inserted_count = 0

            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                batch_data = []

                for row in batch:
                    row_dict = dict(row)
                    # Handle JSON fields
                    for key, value in row_dict.items():
                        if key in ['line_items', 'raw_api_response'] and value:
                            try:
                                if isinstance(value, str):
                                    # Validate JSON
                                    json.loads(value)
                                    row_dict[key] = value
                            except (json.JSONDecodeError, TypeError):
                                row_dict[key] = None

                    batch_data.append(tuple(row_dict[col] for col in columns))

                # Execute batch insert
                conn = self.pg_db.get_connection()
                cursor = conn.cursor()

                try:
                    cursor.executemany(insert_sql, batch_data)
                    conn.commit()
                    inserted_count += len(batch_data)
                    print(f"    ✅ Inserted batch {i//batch_size + 1}: {len(batch_data)} records")
                except Exception as e:
                    conn.rollback()
                    print(f"    ❌ Error inserting batch {i//batch_size + 1}: {e}")
                    self.stats['errors'] += 1
                finally:
                    conn.close()

            print(f"    🎉 Successfully migrated {inserted_count} records to {table_name}")
            self.stats['records_migrated'] += inserted_count
            self.stats['tables_migrated'] += 1

        except Exception as e:
            print(f"    ❌ Error migrating table {table_name}: {e}")
            self.stats['errors'] += 1

def main():
    parser = argparse.ArgumentParser(description='Migrate DeltaCFOAgent data from SQLite to PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without doing it')
    parser.add_argument('--force', action='store_true', help='Force migration even if target tables have data')

    args = parser.parse_args()

    # Check if PostgreSQL is available
    if db_manager.db_type != 'postgresql':
        print("❌ Error: DatabaseManager is not configured for PostgreSQL")
        print("Please check your database configuration in web_ui/database.py")
        sys.exit(1)

    # Run migration
    migrator = DataMigrator(dry_run=args.dry_run, force=args.force)
    migrator.migrate_all()

if __name__ == '__main__':
    main()