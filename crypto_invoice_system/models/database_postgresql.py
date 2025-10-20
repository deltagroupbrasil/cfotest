#!/usr/bin/env python3
"""
Database models for Crypto Invoice Payment System
Delta Energy - Paraguay Colocation Operations
PostgreSQL implementation using centralized DatabaseManager
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import json
from pathlib import Path

# Add main project path for DatabaseManager import
current_dir = Path(__file__).parent.parent.parent
sys.path.append(str(current_dir / 'web_ui'))

from database import db_manager


class InvoiceStatus(Enum):
    """Invoice status enumeration"""
    DRAFT = "draft"
    SENT = "sent"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentStatus(Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class CryptoNetwork(Enum):
    """Supported cryptocurrency networks"""
    BTC = "BTC"
    USDT_TRC20 = "USDT-TRC20"
    USDT_ERC20 = "USDT-ERC20"
    USDT_BEP20 = "USDT-BEP20"
    TAO = "TAO"


class CryptoInvoiceDatabaseManager:
    """Database manager for crypto invoice system using PostgreSQL"""

    def __init__(self):
        """Initialize using centralized DatabaseManager"""
        self.db = db_manager
        self.init_database()

    def init_database(self):
        """Initialize database schema for crypto invoice system"""
        try:
            if self.db.db_type == 'postgresql':
                # PostgreSQL schema for crypto invoice system
                schema_queries = [
                    # Clients table
                    """
                    CREATE TABLE IF NOT EXISTS crypto_clients (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        contact_email VARCHAR(255),
                        contact_person VARCHAR(255),
                        wallet_addresses JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """,

                    # Invoices table
                    """
                    CREATE TABLE IF NOT EXISTS crypto_invoices (
                        id SERIAL PRIMARY KEY,
                        invoice_number VARCHAR(50) NOT NULL UNIQUE,
                        client_id INTEGER NOT NULL REFERENCES crypto_clients(id),
                        status VARCHAR(20) NOT NULL DEFAULT 'sent',
                        amount_usd DECIMAL(18,2) NOT NULL,
                        crypto_currency VARCHAR(10) NOT NULL,
                        crypto_amount DECIMAL(18,8) NOT NULL,
                        crypto_network VARCHAR(20) NOT NULL,
                        exchange_rate DECIMAL(18,8) NOT NULL,
                        deposit_address VARCHAR(255) NOT NULL,
                        memo_tag VARCHAR(255),
                        qr_code_path VARCHAR(500),
                        billing_period VARCHAR(100),
                        description TEXT,
                        line_items JSONB,
                        due_date DATE NOT NULL,
                        issue_date DATE NOT NULL,
                        payment_tolerance DECIMAL(6,5) DEFAULT 0.005,
                        pdf_path VARCHAR(500),
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        paid_at TIMESTAMP
                    );
                    """,

                    # Payment transactions table
                    """
                    CREATE TABLE IF NOT EXISTS crypto_payment_transactions (
                        id SERIAL PRIMARY KEY,
                        invoice_id INTEGER NOT NULL REFERENCES crypto_invoices(id),
                        transaction_hash VARCHAR(255) UNIQUE,
                        amount_received DECIMAL(18,8) NOT NULL,
                        currency VARCHAR(10) NOT NULL,
                        network VARCHAR(20) NOT NULL,
                        deposit_address VARCHAR(255) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'detected',
                        confirmations INTEGER DEFAULT 0,
                        required_confirmations INTEGER DEFAULT 6,
                        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        confirmed_at TIMESTAMP,
                        block_height BIGINT,
                        memo_tag VARCHAR(255),
                        is_manual_verification BOOLEAN DEFAULT FALSE,
                        verified_by VARCHAR(255),
                        mexc_transaction_id VARCHAR(255),
                        raw_api_response JSONB
                    );
                    """,

                    # MEXC addresses cache table
                    """
                    CREATE TABLE IF NOT EXISTS crypto_mexc_addresses (
                        id SERIAL PRIMARY KEY,
                        currency VARCHAR(10) NOT NULL,
                        network VARCHAR(20) NOT NULL,
                        address VARCHAR(255) NOT NULL,
                        memo_tag VARCHAR(255),
                        is_used BOOLEAN DEFAULT FALSE,
                        used_for_invoice_id INTEGER REFERENCES crypto_invoices(id),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(currency, network, address)
                    );
                    """,

                    # Payment polling log table
                    """
                    CREATE TABLE IF NOT EXISTS crypto_polling_log (
                        id SERIAL PRIMARY KEY,
                        invoice_id INTEGER NOT NULL REFERENCES crypto_invoices(id),
                        poll_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status VARCHAR(50),
                        deposits_found INTEGER DEFAULT 0,
                        error_message TEXT,
                        api_response JSONB
                    );
                    """,

                    # Notifications table
                    """
                    CREATE TABLE IF NOT EXISTS crypto_notifications (
                        id SERIAL PRIMARY KEY,
                        invoice_id INTEGER NOT NULL REFERENCES crypto_invoices(id),
                        notification_type VARCHAR(50) NOT NULL,
                        recipient VARCHAR(255) NOT NULL,
                        subject VARCHAR(500),
                        message TEXT NOT NULL,
                        sent_at TIMESTAMP,
                        status VARCHAR(20) DEFAULT 'pending',
                        error_message TEXT
                    );
                    """,

                    # System configuration table
                    """
                    CREATE TABLE IF NOT EXISTS crypto_system_config (
                        key VARCHAR(100) PRIMARY KEY,
                        value TEXT NOT NULL,
                        description TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """,

                    # Create indexes for performance
                    """
                    CREATE INDEX IF NOT EXISTS idx_crypto_invoices_status ON crypto_invoices(status);
                    CREATE INDEX IF NOT EXISTS idx_crypto_invoices_due_date ON crypto_invoices(due_date);
                    CREATE INDEX IF NOT EXISTS idx_crypto_invoices_client ON crypto_invoices(client_id);
                    CREATE INDEX IF NOT EXISTS idx_crypto_payments_invoice ON crypto_payment_transactions(invoice_id);
                    CREATE INDEX IF NOT EXISTS idx_crypto_payments_status ON crypto_payment_transactions(status);
                    CREATE INDEX IF NOT EXISTS idx_crypto_payments_txhash ON crypto_payment_transactions(transaction_hash);
                    CREATE INDEX IF NOT EXISTS idx_crypto_polling_invoice ON crypto_polling_log(invoice_id);
                    CREATE INDEX IF NOT EXISTS idx_crypto_notifications_invoice ON crypto_notifications(invoice_id);
                    """,
                ]
            else:
                # SQLite fallback schema
                schema_queries = [
                    """
                    CREATE TABLE IF NOT EXISTS crypto_clients (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        contact_email TEXT,
                        contact_person TEXT,
                        wallet_addresses TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS crypto_invoices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        invoice_number TEXT NOT NULL UNIQUE,
                        client_id INTEGER NOT NULL,
                        status TEXT NOT NULL DEFAULT 'sent',
                        amount_usd REAL NOT NULL,
                        crypto_currency TEXT NOT NULL,
                        crypto_amount REAL NOT NULL,
                        crypto_network TEXT NOT NULL,
                        exchange_rate REAL NOT NULL,
                        deposit_address TEXT NOT NULL,
                        memo_tag TEXT,
                        qr_code_path TEXT,
                        billing_period TEXT,
                        description TEXT,
                        line_items TEXT,
                        due_date TEXT NOT NULL,
                        issue_date TEXT NOT NULL,
                        payment_tolerance REAL DEFAULT 0.005,
                        pdf_path TEXT,
                        notes TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        paid_at TEXT,
                        FOREIGN KEY (client_id) REFERENCES crypto_clients(id)
                    );
                    """
                ]

            # Execute schema creation
            for query in schema_queries:
                if query.strip():
                    self.db.execute_query(query)

            print(f"✅ Crypto Invoice database schema initialized on {self.db.db_type}")

            # Insert default data
            self._insert_default_clients()
            self._insert_default_config()

        except Exception as e:
            print(f"❌ Error initializing crypto invoice database: {e}")
            raise

    def _insert_default_clients(self):
        """Insert default Paraguay colocation clients"""
        default_clients = [
            {
                "name": "Alps Blockchain",
                "contact_email": "ops@alpsblockchain.com",
                "contact_person": "Alps Operations Team"
            },
            {
                "name": "Exos Capital",
                "contact_email": "billing@exoscapital.com",
                "contact_person": "Exos Finance Team"
            },
            {
                "name": "GM Data Centers",
                "contact_email": "billing@gmdatacenters.com",
                "contact_person": "GM Accounting"
            },
            {
                "name": "Other",
                "contact_email": "",
                "contact_person": ""
            }
        ]

        for client in default_clients:
            try:
                if self.db.db_type == 'postgresql':
                    query = """
                        INSERT INTO crypto_clients (name, contact_email, contact_person)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (name) DO NOTHING
                    """
                else:
                    query = """
                        INSERT OR IGNORE INTO crypto_clients (name, contact_email, contact_person)
                        VALUES (?, ?, ?)
                    """

                self.db.execute_query(query, (
                    client["name"],
                    client["contact_email"],
                    client["contact_person"]
                ))
            except Exception as e:
                print(f"Warning: Error inserting client {client['name']}: {e}")

    def _insert_default_config(self):
        """Insert default system configuration"""
        default_config = [
            ("polling_interval_seconds", "30", "Interval for polling MEXC API for payments"),
            ("payment_tolerance_percent", "0.5", "Payment amount tolerance percentage"),
            ("btc_confirmations_required", "3", "Required confirmations for BTC payments"),
            ("usdt_confirmations_required", "20", "Required confirmations for USDT payments"),
            ("tao_confirmations_required", "12", "Required confirmations for TAO payments"),
            ("invoice_overdue_days", "7", "Days after due date before invoice marked overdue"),
            ("notification_email_from", "billing@deltaenergy.com", "From email for notifications"),
            ("notification_email_cc", "aldo@deltaenergy.com,tiago@deltaenergy.com", "CC emails for notifications")
        ]

        for key, value, description in default_config:
            try:
                if self.db.db_type == 'postgresql':
                    query = """
                        INSERT INTO crypto_system_config (key, value, description, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (key) DO NOTHING
                    """
                else:
                    query = """
                        INSERT OR IGNORE INTO crypto_system_config (key, value, description)
                        VALUES (?, ?, ?)
                    """

                self.db.execute_query(query, (key, value, description))
            except Exception as e:
                print(f"Warning: Error inserting config {key}: {e}")

    # Invoice CRUD operations

    def create_invoice(self, invoice_data: Dict[str, Any]) -> int:
        """Create new invoice"""
        try:
            if self.db.db_type == 'postgresql':
                query = """
                    INSERT INTO crypto_invoices (
                        invoice_number, client_id, status, amount_usd, crypto_currency,
                        crypto_amount, crypto_network, exchange_rate, deposit_address,
                        memo_tag, billing_period, description, line_items, due_date,
                        issue_date, payment_tolerance
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
            else:
                query = """
                    INSERT INTO crypto_invoices (
                        invoice_number, client_id, status, amount_usd, crypto_currency,
                        crypto_amount, crypto_network, exchange_rate, deposit_address,
                        memo_tag, billing_period, description, line_items, due_date,
                        issue_date, payment_tolerance
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

            params = (
                invoice_data["invoice_number"],
                invoice_data["client_id"],
                invoice_data.get("status", "sent"),
                invoice_data["amount_usd"],
                invoice_data["crypto_currency"],
                invoice_data["crypto_amount"],
                invoice_data["crypto_network"],
                invoice_data["exchange_rate"],
                invoice_data["deposit_address"],
                invoice_data.get("memo_tag"),
                invoice_data.get("billing_period"),
                invoice_data.get("description"),
                json.dumps(invoice_data.get("line_items", [])),
                invoice_data["due_date"],
                invoice_data["issue_date"],
                invoice_data.get("payment_tolerance", 0.005)
            )

            if self.db.db_type == 'postgresql':
                result = self.db.execute_query(query, params, fetch_one=True)
                return result['id']
            else:
                self.db.execute_query(query, params)
                result = self.db.execute_query("SELECT last_insert_rowid() as id", fetch_one=True)
                return result['id']

        except Exception as e:
            print(f"❌ Error creating invoice: {e}")
            raise

    def get_invoice(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Get invoice by ID"""
        try:
            query = """
                SELECT i.*, c.name as client_name, c.contact_email
                FROM crypto_invoices i
                JOIN crypto_clients c ON i.client_id = c.id
                WHERE i.id = %s
            """ if self.db.db_type == 'postgresql' else """
                SELECT i.*, c.name as client_name, c.contact_email
                FROM crypto_invoices i
                JOIN crypto_clients c ON i.client_id = c.id
                WHERE i.id = ?
            """

            row = self.db.execute_query(query, (invoice_id,), fetch_one=True)

            if row:
                invoice = dict(row) if hasattr(row, 'keys') else dict(zip(row.keys(), row))
                # Parse JSON fields
                if invoice.get("line_items"):
                    try:
                        invoice["line_items"] = json.loads(invoice["line_items"])
                    except (json.JSONDecodeError, TypeError):
                        invoice["line_items"] = []
                return invoice
            return None

        except Exception as e:
            print(f"❌ Error getting invoice {invoice_id}: {e}")
            return None

    def get_pending_invoices(self) -> List[Dict[str, Any]]:
        """Get all pending/unpaid invoices for payment polling"""
        try:
            query = """
                SELECT i.*, c.name as client_name
                FROM crypto_invoices i
                JOIN crypto_clients c ON i.client_id = c.id
                WHERE i.status IN ('sent', 'partially_paid')
                ORDER BY i.due_date ASC
            """

            rows = self.db.execute_query(query, fetch_all=True)

            invoices = []
            for row in rows:
                invoice = dict(row) if hasattr(row, 'keys') else dict(zip(row.keys(), row))
                # Parse JSON fields
                if invoice.get("line_items"):
                    try:
                        invoice["line_items"] = json.loads(invoice["line_items"])
                    except (json.JSONDecodeError, TypeError):
                        invoice["line_items"] = []
                invoices.append(invoice)

            return invoices

        except Exception as e:
            print(f"❌ Error getting pending invoices: {e}")
            return []

    def update_invoice_status(self, invoice_id: int, status: str, paid_at: Optional[datetime] = None):
        """Update invoice status"""
        try:
            if paid_at:
                if self.db.db_type == 'postgresql':
                    query = """
                        UPDATE crypto_invoices
                        SET status = %s, paid_at = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """
                else:
                    query = """
                        UPDATE crypto_invoices
                        SET status = ?, paid_at = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """
                params = (status, paid_at, invoice_id)
            else:
                if self.db.db_type == 'postgresql':
                    query = """
                        UPDATE crypto_invoices
                        SET status = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """
                else:
                    query = """
                        UPDATE crypto_invoices
                        SET status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """
                params = (status, invoice_id)

            self.db.execute_query(query, params)

        except Exception as e:
            print(f"❌ Error updating invoice status: {e}")
            raise

    def update_invoice_pdf_path(self, invoice_id: int, pdf_path: str):
        """Update invoice PDF path"""
        try:
            if self.db.db_type == 'postgresql':
                query = """
                    UPDATE crypto_invoices SET pdf_path = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
            else:
                query = """
                    UPDATE crypto_invoices SET pdf_path = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """

            self.db.execute_query(query, (pdf_path, invoice_id))

        except Exception as e:
            print(f"❌ Error updating invoice PDF path: {e}")
            raise

    # Payment transaction operations

    def create_payment_transaction(self, payment_data: Dict[str, Any]) -> int:
        """Record payment transaction"""
        try:
            if self.db.db_type == 'postgresql':
                query = """
                    INSERT INTO crypto_payment_transactions (
                        invoice_id, transaction_hash, amount_received, currency,
                        network, deposit_address, status, confirmations,
                        required_confirmations, block_height, memo_tag,
                        is_manual_verification, verified_by, mexc_transaction_id,
                        raw_api_response
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
            else:
                query = """
                    INSERT INTO crypto_payment_transactions (
                        invoice_id, transaction_hash, amount_received, currency,
                        network, deposit_address, status, confirmations,
                        required_confirmations, block_height, memo_tag,
                        is_manual_verification, verified_by, mexc_transaction_id,
                        raw_api_response
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

            params = (
                payment_data["invoice_id"],
                payment_data.get("transaction_hash"),
                payment_data["amount_received"],
                payment_data["currency"],
                payment_data["network"],
                payment_data["deposit_address"],
                payment_data.get("status", "detected"),
                payment_data.get("confirmations", 0),
                payment_data.get("required_confirmations", 6),
                payment_data.get("block_height"),
                payment_data.get("memo_tag"),
                payment_data.get("is_manual_verification", False),
                payment_data.get("verified_by"),
                payment_data.get("mexc_transaction_id"),
                json.dumps(payment_data.get("raw_api_response")) if payment_data.get("raw_api_response") else None
            )

            if self.db.db_type == 'postgresql':
                result = self.db.execute_query(query, params, fetch_one=True)
                return result['id']
            else:
                self.db.execute_query(query, params)
                result = self.db.execute_query("SELECT last_insert_rowid() as id", fetch_one=True)
                return result['id']

        except Exception as e:
            print(f"❌ Error creating payment transaction: {e}")
            raise

    def get_payments_for_invoice(self, invoice_id: int) -> List[Dict[str, Any]]:
        """Get all payment transactions for an invoice"""
        try:
            query = """
                SELECT * FROM crypto_payment_transactions
                WHERE invoice_id = %s
                ORDER BY detected_at DESC
            """ if self.db.db_type == 'postgresql' else """
                SELECT * FROM crypto_payment_transactions
                WHERE invoice_id = ?
                ORDER BY detected_at DESC
            """

            rows = self.db.execute_query(query, (invoice_id,), fetch_all=True)
            return [dict(row) if hasattr(row, 'keys') else dict(zip(row.keys(), row)) for row in rows]

        except Exception as e:
            print(f"❌ Error getting payments for invoice {invoice_id}: {e}")
            return []

    def update_payment_confirmations(self, payment_id: int, confirmations: int, status: str = None):
        """Update payment confirmation count"""
        try:
            if status:
                if self.db.db_type == 'postgresql':
                    query = """
                        UPDATE crypto_payment_transactions
                        SET confirmations = %s, status = %s, confirmed_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """
                else:
                    query = """
                        UPDATE crypto_payment_transactions
                        SET confirmations = ?, status = ?, confirmed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """
                params = (confirmations, status, payment_id)
            else:
                if self.db.db_type == 'postgresql':
                    query = """
                        UPDATE crypto_payment_transactions
                        SET confirmations = %s
                        WHERE id = %s
                    """
                else:
                    query = """
                        UPDATE crypto_payment_transactions
                        SET confirmations = ?
                        WHERE id = ?
                    """
                params = (confirmations, payment_id)

            self.db.execute_query(query, params)

        except Exception as e:
            print(f"❌ Error updating payment confirmations: {e}")
            raise

    # Client operations

    def get_all_clients(self) -> List[Dict[str, Any]]:
        """Get all clients"""
        try:
            query = "SELECT * FROM crypto_clients ORDER BY name"
            rows = self.db.execute_query(query, fetch_all=True)
            return [dict(row) if hasattr(row, 'keys') else dict(zip(row.keys(), row)) for row in rows]

        except Exception as e:
            print(f"❌ Error getting all clients: {e}")
            return []

    def get_client_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get client by name"""
        try:
            query = "SELECT * FROM crypto_clients WHERE name = %s" if self.db.db_type == 'postgresql' else "SELECT * FROM crypto_clients WHERE name = ?"
            row = self.db.execute_query(query, (name,), fetch_one=True)
            return dict(row) if row and hasattr(row, 'keys') else (dict(zip(row.keys(), row)) if row else None)

        except Exception as e:
            print(f"❌ Error getting client by name {name}: {e}")
            return None

    # MEXC address cache operations

    def cache_mexc_address(self, currency: str, network: str, address: str, memo_tag: str = None):
        """Cache MEXC deposit address"""
        try:
            if self.db.db_type == 'postgresql':
                query = """
                    INSERT INTO crypto_mexc_addresses (currency, network, address, memo_tag)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (currency, network, address) DO NOTHING
                """
            else:
                query = """
                    INSERT OR IGNORE INTO crypto_mexc_addresses (currency, network, address, memo_tag)
                    VALUES (?, ?, ?, ?)
                """

            self.db.execute_query(query, (currency, network, address, memo_tag))

        except Exception as e:
            print(f"❌ Error caching MEXC address: {e}")

    def mark_address_used(self, address: str, invoice_id: int):
        """Mark address as used for an invoice"""
        try:
            if self.db.db_type == 'postgresql':
                query = """
                    UPDATE crypto_mexc_addresses
                    SET is_used = TRUE, used_for_invoice_id = %s
                    WHERE address = %s
                """
            else:
                query = """
                    UPDATE crypto_mexc_addresses
                    SET is_used = 1, used_for_invoice_id = ?
                    WHERE address = ?
                """

            self.db.execute_query(query, (invoice_id, address))

        except Exception as e:
            print(f"❌ Error marking address as used: {e}")

    # Configuration operations

    def get_config(self, key: str) -> Optional[str]:
        """Get configuration value"""
        try:
            query = "SELECT value FROM crypto_system_config WHERE key = %s" if self.db.db_type == 'postgresql' else "SELECT value FROM crypto_system_config WHERE key = ?"
            row = self.db.execute_query(query, (key,), fetch_one=True)
            return row["value"] if row else None

        except Exception as e:
            print(f"❌ Error getting config {key}: {e}")
            return None

    def set_config(self, key: str, value: str):
        """Set configuration value"""
        try:
            if self.db.db_type == 'postgresql':
                query = """
                    INSERT INTO crypto_system_config (key, value, updated_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (key)
                    DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
                """
            else:
                query = """
                    INSERT OR REPLACE INTO crypto_system_config (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """

            self.db.execute_query(query, (key, value))

        except Exception as e:
            print(f"❌ Error setting config {key}: {e}")

    # Polling log operations

    def log_polling_event(self, invoice_id: int, status: str, deposits_found: int = 0,
                         error_message: str = None, api_response: str = None):
        """Log a polling event"""
        try:
            if self.db.db_type == 'postgresql':
                query = """
                    INSERT INTO crypto_polling_log (invoice_id, status, deposits_found, error_message, api_response)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                """
            else:
                query = """
                    INSERT INTO crypto_polling_log (invoice_id, status, deposits_found, error_message, api_response)
                    VALUES (?, ?, ?, ?, ?)
                """

            self.db.execute_query(query, (invoice_id, status, deposits_found, error_message, api_response))

        except Exception as e:
            print(f"❌ Error logging polling event: {e}")

    # Notification operations

    def create_notification(self, invoice_id: int, notification_type: str,
                          recipient: str, subject: str, message: str) -> int:
        """Create notification record"""
        try:
            if self.db.db_type == 'postgresql':
                query = """
                    INSERT INTO crypto_notifications (invoice_id, notification_type, recipient, subject, message)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """
            else:
                query = """
                    INSERT INTO crypto_notifications (invoice_id, notification_type, recipient, subject, message)
                    VALUES (?, ?, ?, ?, ?)
                """

            if self.db.db_type == 'postgresql':
                result = self.db.execute_query(query, (invoice_id, notification_type, recipient, subject, message), fetch_one=True)
                return result['id']
            else:
                self.db.execute_query(query, (invoice_id, notification_type, recipient, subject, message))
                result = self.db.execute_query("SELECT last_insert_rowid() as id", fetch_one=True)
                return result['id']

        except Exception as e:
            print(f"❌ Error creating notification: {e}")
            return 0

    def mark_notification_sent(self, notification_id: int, status: str = "sent", error_message: str = None):
        """Mark notification as sent"""
        try:
            if self.db.db_type == 'postgresql':
                query = """
                    UPDATE crypto_notifications
                    SET status = %s, sent_at = CURRENT_TIMESTAMP, error_message = %s
                    WHERE id = %s
                """
            else:
                query = """
                    UPDATE crypto_notifications
                    SET status = ?, sent_at = CURRENT_TIMESTAMP, error_message = ?
                    WHERE id = ?
                """

            self.db.execute_query(query, (status, error_message, notification_id))

        except Exception as e:
            print(f"❌ Error marking notification as sent: {e}")

    def get_pending_notifications(self) -> List[Dict[str, Any]]:
        """Get pending notifications"""
        try:
            query = """
                SELECT * FROM crypto_notifications
                WHERE status = 'pending'
                ORDER BY id ASC
            """

            rows = self.db.execute_query(query, fetch_all=True)
            return [dict(row) if hasattr(row, 'keys') else dict(zip(row.keys(), row)) for row in rows]

        except Exception as e:
            print(f"❌ Error getting pending notifications: {e}")
            return []


# Global instance for backward compatibility
db_manager_crypto = CryptoInvoiceDatabaseManager()

# For compatibility with existing code
DatabaseManager = CryptoInvoiceDatabaseManager