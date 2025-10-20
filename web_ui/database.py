#!/usr/bin/env python3
"""
Database Connection Manager for Delta CFO Agent
Supports both SQLite (development) and PostgreSQL (production)
"""

import os
import sqlite3
import psycopg2
import psycopg2.extras
import psycopg2.pool
from contextlib import contextmanager
from typing import Generator, Optional, Any, Dict, List
import time
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_type = os.getenv('DB_TYPE', 'postgresql')  # Default to PostgreSQL after migration
        self.connection_config = self._get_connection_config()
        self.connection_pool = None
        self._pooled_connections = set()  # Track connection IDs from pool
        self._init_connection_pool()

    def _get_connection_config(self) -> dict:
        """Get database connection configuration based on environment"""
        if self.db_type == 'postgresql':
            # Handle Cloud SQL socket path directly
            socket_path = os.getenv('DB_SOCKET_PATH')
            if socket_path:
                return {
                    'host': socket_path,
                    'port': os.getenv('DB_PORT', '5432'),
                    'database': os.getenv('DB_NAME', 'delta_cfo'),
                    'user': os.getenv('DB_USER', 'postgres'),
                    'password': os.getenv('DB_PASSWORD', ''),
                    'sslmode': 'disable',  # SSL disabled for Unix socket
                }
            else:
                return {
                    'host': os.getenv('DB_HOST', 'localhost'),
                    'port': os.getenv('DB_PORT', '5432'),
                    'database': os.getenv('DB_NAME', 'delta_cfo'),
                    'user': os.getenv('DB_USER', 'postgres'),
                    'password': os.getenv('DB_PASSWORD', ''),
                    'sslmode': os.getenv('DB_SSL_MODE', 'require'),
                }
        else:
            # SQLite configuration
            db_path = os.getenv('SQLITE_DB_PATH', 'delta_transactions.db')
            return {
                'database': db_path,
                'timeout': 60.0,
                'check_same_thread': False
            }

    def _init_connection_pool(self):
        """Initialize connection pool for PostgreSQL"""
        if self.db_type == 'postgresql':
            try:
                config = self.connection_config.copy()

                # Check if essential credentials are provided
                if not config.get('host') or not config.get('user'):
                    logger.warning("PostgreSQL credentials not configured - connection pool disabled")
                    self.connection_pool = None
                    return

                # Remove None values
                config = {k: v for k, v in config.items() if v is not None}

                # Create connection pool
                self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=2,  # Minimum connections
                    maxconn=20,  # Maximum connections for Cloud SQL
                    **config
                )
                logger.info("PostgreSQL connection pool initialized successfully")

            except Exception as e:
                logger.warning(f"Failed to initialize connection pool: {e}")
                self.connection_pool = None
        else:
            # SQLite doesn't need connection pooling
            self.connection_pool = None

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """Get database connection with proper error handling and retries"""
        connection = None
        max_retries = 3
        connection_acquired = False

        for attempt in range(max_retries):
            try:
                if self.db_type == 'postgresql':
                    connection = self._get_postgresql_connection()
                else:
                    connection = self._get_sqlite_connection()

                connection_acquired = True
                yield connection
                break

            except Exception as e:
                # Only clean up if we failed to acquire or use the connection
                if connection and not connection_acquired:
                    try:
                        if self.db_type == 'postgresql':
                            # Only return to pool if connection came from pool
                            conn_id = id(connection)
                            if conn_id in self._pooled_connections and self.connection_pool:
                                self._pooled_connections.discard(conn_id)
                                self.connection_pool.putconn(connection)
                            else:
                                connection.close()
                        else:
                            connection.close()
                    except:
                        pass
                    connection = None

                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                    logger.warning(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    connection_acquired = False
                    continue
                else:
                    logger.error(f"All database connection attempts failed: {e}")
                    raise
            finally:
                # Only return connection to pool if it was successfully acquired
                if connection and connection_acquired:
                    try:
                        if self.db_type == 'postgresql':
                            # Only return to pool if connection came from pool
                            conn_id = id(connection)
                            if conn_id in self._pooled_connections and self.connection_pool:
                                self._pooled_connections.discard(conn_id)
                                self.connection_pool.putconn(connection)
                            else:
                                # Direct connection, just close it
                                connection.close()
                        else:
                            connection.close()
                    except Exception as e:
                        logger.error(f"Error returning connection to pool: {e}")

    def _get_postgresql_connection(self):
        """Create PostgreSQL connection using pool if available"""
        if self.connection_pool:
            try:
                conn = self.connection_pool.getconn()
                if conn:
                    conn.autocommit = False  # Use transactions
                    # Track this connection as from pool
                    self._pooled_connections.add(id(conn))
                    return conn
            except Exception as e:
                logger.warning(f"Failed to get connection from pool, creating new one: {e}")

        # Fallback to direct connection
        config = self.connection_config.copy()

        # Remove None values
        config = {k: v for k, v in config.items() if v is not None}

        conn = psycopg2.connect(**config)
        conn.autocommit = False  # Use transactions
        # Direct connections are NOT tracked in _pooled_connections
        return conn

    def _get_sqlite_connection(self):
        """Create SQLite connection with optimizations"""
        config = self.connection_config
        conn = sqlite3.connect(**config)

        # Configure SQLite for better performance
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=60000")
        conn.execute("PRAGMA foreign_keys=ON")

        # Row factory for dict-like access
        conn.row_factory = sqlite3.Row

        return conn

    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
        """Execute a query and return results"""
        with self.get_connection() as conn:
            if self.db_type == 'postgresql':
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cursor = conn.cursor()

            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if fetch_one:
                    result = cursor.fetchone()
                elif fetch_all:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount

                conn.commit()
                return result

            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()

    def execute_many(self, query: str, params_list: list):
        """Execute a query multiple times with different parameters"""
        with self.get_connection() as conn:
            if self.db_type == 'postgresql':
                cursor = conn.cursor()
            else:
                cursor = conn.cursor()

            try:
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount

            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()

    @contextmanager
    def get_transaction(self):
        """
        Context manager for database transactions with automatic rollback on error
        Ensures data consistency for complex operations like matching
        """
        with self.get_connection() as conn:
            savepoint_name = None
            try:
                # For PostgreSQL, we can use savepoints for nested transactions
                if self.db_type == 'postgresql':
                    import uuid
                    savepoint_name = f"sp_{str(uuid.uuid4()).replace('-', '_')}"
                    cursor = conn.cursor()
                    cursor.execute(f"SAVEPOINT {savepoint_name}")
                    cursor.close()

                yield conn

                # If we reach here, commit the transaction
                if self.db_type == 'postgresql' and savepoint_name:
                    cursor = conn.cursor()
                    cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    cursor.close()

                conn.commit()
                logger.debug("Transaction committed successfully")

            except Exception as e:
                # Rollback on any error
                try:
                    if self.db_type == 'postgresql' and savepoint_name:
                        cursor = conn.cursor()
                        cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                        cursor.close()
                    else:
                        conn.rollback()
                    logger.warning(f"Transaction rolled back due to error: {e}")
                except Exception as rollback_error:
                    logger.error(f"Error during rollback: {rollback_error}")
                raise e

    def execute_batch_operation(self, operations: List[Dict], batch_size: int = 100) -> Dict[str, Any]:
        """
        Execute multiple database operations in batches with transaction safety
        Useful for processing large volumes of matching operations

        Args:
            operations: List of dicts with 'query', 'params', and optional 'operation_type'
            batch_size: Number of operations per batch

        Returns:
            Dict with success/failure statistics
        """
        results = {
            'total_operations': len(operations),
            'successful_batches': 0,
            'failed_batches': 0,
            'total_rows_affected': 0,
            'errors': []
        }

        # Process in batches
        for i in range(0, len(operations), batch_size):
            batch = operations[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            try:
                with self.get_transaction() as conn:
                    cursor = conn.cursor()
                    batch_rows_affected = 0

                    for operation in batch:
                        query = operation['query']
                        params = operation.get('params', ())

                        cursor.execute(query, params)
                        batch_rows_affected += cursor.rowcount

                    cursor.close()
                    results['successful_batches'] += 1
                    results['total_rows_affected'] += batch_rows_affected

                    logger.info(f"Batch {batch_num} completed successfully ({len(batch)} operations)")

            except Exception as e:
                results['failed_batches'] += 1
                error_msg = f"Batch {batch_num} failed: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)

                # Continue with next batch rather than failing completely
                continue

        logger.info(f"Batch processing completed: {results['successful_batches']}/{results['successful_batches'] + results['failed_batches']} batches successful")
        return results

    def execute_with_retry(self, query: str, params: tuple = None, max_retries: int = 3,
                          fetch_one: bool = False, fetch_all: bool = False):
        """
        Execute query with automatic retry for transient failures
        Particularly useful for Cloud SQL which may have temporary connectivity issues
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return self.execute_query(query, params, fetch_one, fetch_all)

            except psycopg2.OperationalError as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}): {e}")
                    logger.warning(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Database operation failed after {max_retries} attempts")
                    raise

            except Exception as e:
                # For non-operational errors, don't retry
                logger.error(f"Database operation failed with non-retryable error: {e}")
                raise

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception

    def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check
        Returns status information about database connectivity and performance
        """
        health_status = {
            'status': 'unknown',
            'db_type': self.db_type,
            'connection_pool_status': None,
            'response_time_ms': None,
            'error': None
        }

        try:
            start_time = time.time()

            # Simple connectivity test
            result = self.execute_query("SELECT 1 as health_check", fetch_one=True)

            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds

            # Handle both dict-like and tuple-like results
            health_check_value = None
            if result:
                if hasattr(result, 'get'):
                    health_check_value = result.get('health_check')
                elif hasattr(result, '__getitem__'):
                    try:
                        health_check_value = result[0]
                    except (IndexError, KeyError):
                        health_check_value = None
                elif hasattr(result, 'health_check'):
                    health_check_value = result.health_check

            if health_check_value == 1:
                health_status['status'] = 'healthy'
                health_status['response_time_ms'] = round(response_time, 2)

                # Check connection pool status for PostgreSQL
                if self.db_type == 'postgresql' and self.connection_pool:
                    health_status['connection_pool_status'] = {
                        'total_connections': len(self.connection_pool._pool),
                        'used_connections': len(self.connection_pool._used),
                        'available_connections': len(self.connection_pool._pool) - len(self.connection_pool._used)
                    }
            else:
                health_status['status'] = 'unhealthy'
                health_status['error'] = 'Health check query returned unexpected result'

        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
            logger.error(f"Database health check failed: {e}")

        return health_status

    def close_pool(self):
        """Close connection pool gracefully"""
        if self.connection_pool and self.db_type == 'postgresql':
            try:
                self.connection_pool.closeall()
                logger.info("Connection pool closed successfully")
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")

    def init_database(self):
        """Initialize database with schema"""
        if self.db_type == 'postgresql':
            self._init_postgresql_schema()
        else:
            self._init_sqlite_schema()

    def _init_postgresql_schema(self):
        """Initialize PostgreSQL schema"""
        schema_file = os.path.join(os.path.dirname(__file__), '..', 'migration', 'postgresql_schema.sql')

        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema_sql = f.read()

            with self.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    # Execute schema in chunks (split by semicolon)
                    statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                    for statement in statements:
                        if statement:
                            cursor.execute(statement)
                    conn.commit()
                    print("PostgreSQL schema initialized successfully")
                except Exception as e:
                    conn.rollback()
                    print(f"Error initializing PostgreSQL schema: {e}")
                    raise
                finally:
                    cursor.close()
        else:
            print("PostgreSQL schema file not found")

    def _init_sqlite_schema(self):
        """Initialize SQLite schema (existing logic)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id TEXT PRIMARY KEY,
                    date TEXT,
                    description TEXT,
                    amount REAL,
                    currency TEXT,
                    usd_equivalent REAL,
                    classified_entity TEXT,
                    justification TEXT,
                    confidence REAL,
                    classification_reason TEXT,
                    origin TEXT,
                    destination TEXT,
                    identifier TEXT,
                    source_file TEXT,
                    crypto_amount TEXT,
                    conversion_note TEXT,
                    accounting_category TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT
                )
            """)

            # Create invoices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id TEXT PRIMARY KEY,
                    invoice_number TEXT UNIQUE NOT NULL,
                    date TEXT NOT NULL,
                    vendor_name TEXT,
                    total_amount REAL,
                    currency TEXT DEFAULT 'USD',
                    payment_due_date TEXT,
                    payment_status TEXT DEFAULT 'pending',
                    items TEXT,
                    raw_text TEXT,
                    confidence REAL,
                    processing_notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    vendor_address TEXT,
                    vendor_tax_id TEXT,
                    vendor_contact TEXT,
                    vendor_type TEXT,
                    extraction_method TEXT,
                    customer_name TEXT,
                    customer_address TEXT,
                    customer_tax_id TEXT,
                    linked_transaction_id TEXT,
                    FOREIGN KEY (linked_transaction_id) REFERENCES transactions(transaction_id)
                )
            ''')

            # Create invoice email log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoice_email_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT UNIQUE NOT NULL,
                    subject TEXT,
                    sender TEXT,
                    received_at TEXT,
                    processed_at TEXT,
                    status TEXT DEFAULT 'pending',
                    attachments_count INTEGER DEFAULT 0,
                    invoices_extracted INTEGER DEFAULT 0,
                    error_message TEXT
                )
            ''')

            conn.commit()
            print("SQLite schema initialized successfully")

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for backward compatibility
def get_db_connection():
    """Get database connection (backward compatibility)"""
    return db_manager.get_connection()

def init_database():
    """Initialize database"""
    return db_manager.init_database()