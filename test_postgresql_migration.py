#!/usr/bin/env python3
"""
DeltaCFOAgent - PostgreSQL Migration Test Suite
==============================================

Comprehensive testing script to validate complete migration from SQLite to PostgreSQL.
This script tests all components to ensure they work correctly with PostgreSQL.

Usage:
    python test_postgresql_migration.py [--verbose] [--component=all]

Options:
    --verbose       Show detailed test output
    --component     Test specific component: main, crypto_pricing, crypto_invoice, analytics, all
"""

import os
import sys
import argparse
import traceback
from datetime import datetime, date
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

class PostgreSQLMigrationTester:
    """Comprehensive test suite for PostgreSQL migration validation"""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.errors = []

    def run_all_tests(self, component='all'):
        """Run all migration tests"""
        print("🧪 DeltaCFOAgent PostgreSQL Migration Test Suite")
        print("=" * 60)
        print(f"Testing Component: {component}")
        print(f"Verbose Mode: {self.verbose}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        if component in ['all', 'main']:
            self.test_main_system()

        if component in ['all', 'crypto_pricing']:
            self.test_crypto_pricing_system()

        if component in ['all', 'crypto_invoice']:
            self.test_crypto_invoice_system()

        if component in ['all', 'analytics']:
            self.test_analytics_service()

        self._print_summary()

    def test_main_system(self):
        """Test main transaction system with PostgreSQL"""
        print("\n📊 Testing Main Transaction System...")

        try:
            from web_ui.database import db_manager

            # Test 1: Database connection
            self._test("Database Connection", self._test_db_connection, db_manager)

            # Test 2: Database type
            self._test("Database Type Check", self._test_db_type, db_manager)

            # Test 3: Table existence
            self._test("Core Tables Exist", self._test_core_tables, db_manager)

            # Test 4: Basic CRUD operations
            self._test("Basic CRUD Operations", self._test_crud_operations, db_manager)

            # Test 5: Transaction queries
            self._test("Transaction Queries", self._test_transaction_queries, db_manager)

        except Exception as e:
            self._fail("Main System Import", str(e))

    def test_crypto_pricing_system(self):
        """Test crypto pricing system with PostgreSQL"""
        print("\n💰 Testing Crypto Pricing System...")

        try:
            from crypto_pricing import CryptoPricingDB

            # Test 1: Initialization
            self._test("Crypto Pricing Init", self._test_crypto_pricing_init)

            # Test 2: Database schema
            self._test("Crypto Pricing Schema", self._test_crypto_pricing_schema)

            # Test 3: Price insertion and retrieval
            self._test("Price Operations", self._test_crypto_price_operations)

        except Exception as e:
            self._fail("Crypto Pricing Import", str(e))

    def test_crypto_invoice_system(self):
        """Test crypto invoice system with PostgreSQL"""
        print("\n🧾 Testing Crypto Invoice System...")

        try:
            from crypto_invoice_system.models.database_postgresql import CryptoInvoiceDatabaseManager

            # Test 1: Initialization
            self._test("Invoice DB Init", self._test_invoice_db_init)

            # Test 2: Schema validation
            self._test("Invoice Schema", self._test_invoice_schema)

            # Test 3: Client operations
            self._test("Client Operations", self._test_client_operations)

            # Test 4: Invoice operations
            self._test("Invoice Operations", self._test_invoice_operations)

        except Exception as e:
            self._fail("Crypto Invoice Import", str(e))

    def test_analytics_service(self):
        """Test analytics service with PostgreSQL"""
        print("\n📈 Testing Analytics Service...")

        try:
            sys.path.append(str(Path(__file__).parent / "services" / "analytics_service"))
            from app import AnalyticsEngine

            # Test 1: Initialization
            self._test("Analytics Init", self._test_analytics_init)

            # Test 2: Database connectivity
            self._test("Analytics DB Connection", self._test_analytics_db_connection)

            # Test 3: Query operations
            self._test("Analytics Queries", self._test_analytics_queries)

        except Exception as e:
            self._fail("Analytics Import", str(e))

    # Individual test methods
    def _test_db_connection(self, db_manager):
        """Test database connection"""
        conn = db_manager.get_connection()
        if conn is None:
            raise Exception("Failed to get database connection")
        conn.close()
        return "Connection successful"

    def _test_db_type(self, db_manager):
        """Test database type is PostgreSQL"""
        if db_manager.db_type != 'postgresql':
            raise Exception(f"Expected postgresql, got {db_manager.db_type}")
        return f"Database type: {db_manager.db_type}"

    def _test_core_tables(self, db_manager):
        """Test that core tables exist"""
        required_tables = ['transactions', 'learned_patterns', 'user_interactions', 'business_entities']

        for table in required_tables:
            result = db_manager.execute_query(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
                (table,),
                fetch_one=True
            )
            if not result or result[0] == 0:
                raise Exception(f"Table {table} does not exist")

        return f"All {len(required_tables)} core tables exist"

    def _test_crud_operations(self, db_manager):
        """Test basic CRUD operations"""
        # Test insert
        test_entity = f"Test Entity {datetime.now().strftime('%H%M%S')}"
        result = db_manager.execute_query(
            "INSERT INTO business_entities (name, description, entity_type) VALUES (%s, %s, %s) RETURNING id",
            (test_entity, "Test description", "test"),
            fetch_one=True
        )

        if not result:
            raise Exception("Failed to insert test entity")

        entity_id = result[0]

        # Test select
        result = db_manager.execute_query(
            "SELECT name FROM business_entities WHERE id = %s",
            (entity_id,),
            fetch_one=True
        )

        if not result or result[0] != test_entity:
            raise Exception("Failed to retrieve test entity")

        # Test update
        updated_name = f"Updated {test_entity}"
        db_manager.execute_query(
            "UPDATE business_entities SET name = %s WHERE id = %s",
            (updated_name, entity_id)
        )

        # Test delete
        db_manager.execute_query(
            "DELETE FROM business_entities WHERE id = %s",
            (entity_id,)
        )

        return "CRUD operations successful"

    def _test_transaction_queries(self, db_manager):
        """Test transaction-specific queries"""
        # Test transaction count
        result = db_manager.execute_query(
            "SELECT COUNT(*) FROM transactions",
            fetch_one=True
        )

        if result is None:
            raise Exception("Failed to count transactions")

        count = result[0]
        return f"Transaction queries work, found {count} transactions"

    def _test_crypto_pricing_init(self):
        """Test crypto pricing initialization"""
        from crypto_pricing import CryptoPricingDB
        db = CryptoPricingDB()

        if not hasattr(db, 'db') or db.db is None:
            raise Exception("CryptoPricingDB not properly initialized")

        return "CryptoPricingDB initialized successfully"

    def _test_crypto_pricing_schema(self):
        """Test crypto pricing schema"""
        from crypto_pricing import CryptoPricingDB
        db = CryptoPricingDB()

        # Check if table exists
        result = db.db.execute_query(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'crypto_historic_prices'",
            fetch_one=True
        )

        if not result or result[0] == 0:
            raise Exception("crypto_historic_prices table does not exist")

        return "Crypto pricing schema validated"

    def _test_crypto_price_operations(self):
        """Test crypto price operations"""
        from crypto_pricing import CryptoPricingDB
        db = CryptoPricingDB()

        # Test price insertion (simulate)
        test_date = "2025-01-01"
        test_symbol = "TEST"
        test_price = 100.0

        # Insert test price
        query = """
            INSERT INTO crypto_historic_prices (date, symbol, price_usd)
            VALUES (%s, %s, %s)
            ON CONFLICT (date, symbol) DO UPDATE SET price_usd = EXCLUDED.price_usd
        """
        db.db.execute_query(query, (test_date, test_symbol, test_price))

        # Retrieve test price
        retrieved_price = db.get_price_on_date(test_symbol, test_date)

        if retrieved_price != test_price:
            raise Exception(f"Price mismatch: expected {test_price}, got {retrieved_price}")

        # Clean up
        db.db.execute_query(
            "DELETE FROM crypto_historic_prices WHERE symbol = %s AND date = %s",
            (test_symbol, test_date)
        )

        return "Crypto price operations successful"

    def _test_invoice_db_init(self):
        """Test invoice database initialization"""
        from crypto_invoice_system.models.database_postgresql import CryptoInvoiceDatabaseManager
        db = CryptoInvoiceDatabaseManager()

        if not hasattr(db, 'db') or db.db is None:
            raise Exception("CryptoInvoiceDatabaseManager not properly initialized")

        return "Invoice database initialized successfully"

    def _test_invoice_schema(self):
        """Test invoice system schema"""
        from crypto_invoice_system.models.database_postgresql import CryptoInvoiceDatabaseManager
        db = CryptoInvoiceDatabaseManager()

        required_tables = ['clients', 'invoices', 'payment_transactions', 'mexc_addresses']

        for table in required_tables:
            result = db.db.execute_query(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
                (table,),
                fetch_one=True
            )
            if not result or result[0] == 0:
                raise Exception(f"Invoice table {table} does not exist")

        return f"All {len(required_tables)} invoice tables exist"

    def _test_client_operations(self):
        """Test client operations"""
        from crypto_invoice_system.models.database_postgresql import CryptoInvoiceDatabaseManager
        db = CryptoInvoiceDatabaseManager()

        # Get all clients
        clients = db.get_all_clients()

        if not isinstance(clients, list):
            raise Exception("get_all_clients did not return a list")

        return f"Client operations successful, found {len(clients)} clients"

    def _test_invoice_operations(self):
        """Test invoice operations"""
        from crypto_invoice_system.models.database_postgresql import CryptoInvoiceDatabaseManager
        db = CryptoInvoiceDatabaseManager()

        # Test get pending invoices
        pending = db.get_pending_invoices()

        if not isinstance(pending, list):
            raise Exception("get_pending_invoices did not return a list")

        return f"Invoice operations successful, found {len(pending)} pending invoices"

    def _test_analytics_init(self):
        """Test analytics initialization"""
        from app import AnalyticsEngine
        analytics = AnalyticsEngine()

        if not hasattr(analytics, 'db') or analytics.db is None:
            raise Exception("AnalyticsEngine not properly initialized")

        return "Analytics engine initialized successfully"

    def _test_analytics_db_connection(self):
        """Test analytics database connection"""
        from app import AnalyticsEngine
        analytics = AnalyticsEngine()

        conn = analytics.get_db_connection()

        if conn is None:
            raise Exception("Analytics failed to get database connection")

        conn.close()
        return "Analytics database connection successful"

    def _test_analytics_queries(self):
        """Test analytics queries"""
        from app import AnalyticsEngine
        analytics = AnalyticsEngine()

        # Test monthly summary
        result = analytics.get_monthly_summary(1)

        if not isinstance(result, dict) or 'summary' not in result:
            raise Exception("get_monthly_summary did not return expected format")

        # Test entity breakdown
        result = analytics.get_entity_breakdown()

        if not isinstance(result, dict) or 'entities' not in result:
            raise Exception("get_entity_breakdown did not return expected format")

        return "Analytics queries successful"

    # Helper methods
    def _test(self, test_name, test_func, *args):
        """Run a single test"""
        try:
            result = test_func(*args)
            self.passed += 1
            status = "✅ PASS"
            if self.verbose and result:
                status += f" - {result}"
            print(f"  {status}: {test_name}")
        except Exception as e:
            self.failed += 1
            self.errors.append(f"{test_name}: {str(e)}")
            print(f"  ❌ FAIL: {test_name} - {str(e)}")
            if self.verbose:
                print(f"    {traceback.format_exc()}")

    def _fail(self, test_name, error_msg):
        """Mark test as failed"""
        self.failed += 1
        self.errors.append(f"{test_name}: {error_msg}")
        print(f"  ❌ FAIL: {test_name} - {error_msg}")

    def _print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📋 Test Summary")
        print("=" * 60)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📊 Total: {self.passed + self.failed}")

        if self.failed > 0:
            print(f"\n❌ Failed Tests:")
            for error in self.errors:
                print(f"  - {error}")
            print(f"\n🚨 Migration validation FAILED - {self.failed} issues found")
            sys.exit(1)
        else:
            print(f"\n🎉 All tests passed! PostgreSQL migration is successful!")

def main():
    parser = argparse.ArgumentParser(description='Test PostgreSQL migration for DeltaCFOAgent')
    parser.add_argument('--verbose', action='store_true', help='Show detailed test output')
    parser.add_argument('--component', default='all', choices=['all', 'main', 'crypto_pricing', 'crypto_invoice', 'analytics'],
                        help='Test specific component')

    args = parser.parse_args()

    # Run tests
    tester = PostgreSQLMigrationTester(verbose=args.verbose)
    tester.run_all_tests(component=args.component)

if __name__ == '__main__':
    main()