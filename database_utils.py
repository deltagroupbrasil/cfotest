#!/usr/bin/env python3
"""
Database Utilities - SQLite Connection Management
Solução para problemas de "database locked" no DeltaCFOAgent
"""

import sqlite3
import os
import time
import threading
from contextlib import contextmanager
from typing import Optional, Generator
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Thread-safe database connection manager"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._init_database()

    def _init_database(self):
        """Initialize database with optimal settings"""
        try:
            with self.get_connection() as conn:
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")

                # Set timeout for locked database
                conn.execute("PRAGMA busy_timeout=30000")  # 30 seconds

                # Optimize for performance
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=memory")

                logger.info(f"✅ Database initialized with WAL mode: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get database connection with automatic cleanup
        Usage:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ...")
                conn.commit()
        """
        conn = None
        max_retries = 3

        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=30.0,  # 30 second timeout
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row

                # Set additional pragmas for this connection
                conn.execute("PRAGMA busy_timeout=30000")
                conn.execute("PRAGMA journal_mode=WAL")

                yield conn
                break

            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.warning(f"⚠️ Database locked, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Database error after {attempt + 1} attempts: {e}")
                    raise

            except Exception as e:
                logger.error(f"❌ Unexpected database error: {e}")
                raise

            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception as e:
                        logger.error(f"❌ Error closing connection: {e}")

    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute SELECT query and return results"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Query execution failed: {e}")
            raise

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"❌ Update execution failed: {e}")
            raise

    def execute_batch(self, queries: list) -> bool:
        """Execute multiple queries in a single transaction"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Start transaction
                conn.execute("BEGIN IMMEDIATE")

                for query, params in queries:
                    cursor.execute(query, params if params else ())

                # Commit all changes
                conn.commit()
                logger.info(f"✅ Batch executed: {len(queries)} queries")
                return True

        except Exception as e:
            logger.error(f"❌ Batch execution failed: {e}")
            # Transaction automatically rolled back by context manager
            raise

    def vacuum_database(self):
        """Vacuum database to optimize and fix corruption"""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                logger.info("✅ Database vacuumed successfully")
        except Exception as e:
            logger.error(f"❌ Vacuum failed: {e}")
            raise

    def check_integrity(self) -> bool:
        """Check database integrity"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()

                if result and result[0] == "ok":
                    logger.info("✅ Database integrity OK")
                    return True
                else:
                    logger.error(f"❌ Database integrity issues: {result}")
                    return False
        except Exception as e:
            logger.error(f"❌ Integrity check failed: {e}")
            return False

# Singleton instances for different databases
_db_managers = {}

def get_database_manager(db_path: str) -> DatabaseManager:
    """Get or create database manager for given path"""
    if db_path not in _db_managers:
        _db_managers[db_path] = DatabaseManager(db_path)
    return _db_managers[db_path]

# Utility functions for backwards compatibility
def get_safe_connection(db_path: str):
    """Get safe database connection (backwards compatible)"""
    manager = get_database_manager(db_path)
    return manager.get_connection()

def fix_database_locks(db_path: str) -> bool:
    """Fix common database lock issues"""
    logger.info(f"🔧 Fixing database locks for: {db_path}")

    try:
        # Remove lock files if they exist
        lock_files = [
            f"{db_path}-wal",
            f"{db_path}-shm",
            f"{db_path}-journal"
        ]

        for lock_file in lock_files:
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                    logger.info(f"🗑️ Removed lock file: {lock_file}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not remove {lock_file}: {e}")

        # Test database connection
        manager = get_database_manager(db_path)

        # Check integrity
        if not manager.check_integrity():
            logger.warning("⚠️ Database integrity issues detected")
            return False

        # Test basic operations
        with manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

            if result and result[0] == 1:
                logger.info("✅ Database connection test successful")
                return True
            else:
                logger.error("❌ Database connection test failed")
                return False

    except Exception as e:
        logger.error(f"❌ Failed to fix database locks: {e}")
        return False

if __name__ == "__main__":
    # Test the database manager
    test_db = "test_db_manager.db"

    try:
        manager = get_database_manager(test_db)

        # Test connection
        with manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
            cursor.execute("INSERT INTO test (name) VALUES (?)", ("test_entry",))
            conn.commit()

        # Test query
        results = manager.execute_query("SELECT * FROM test")
        print(f"✅ Test results: {results}")

        # Cleanup
        if os.path.exists(test_db):
            os.remove(test_db)

        print("✅ Database manager test completed successfully")

    except Exception as e:
        print(f"❌ Database manager test failed: {e}")