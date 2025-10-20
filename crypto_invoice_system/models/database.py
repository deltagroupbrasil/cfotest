#!/usr/bin/env python3
"""
Database models for Crypto Invoice Payment System
Delta Energy - Paraguay Colocation Operations
Migrated to use PostgreSQL via centralized DatabaseManager
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
    """Database manager for crypto invoice system using centralized DatabaseManager"""

    def __init__(self):
        """Initialize using centralized DatabaseManager"""
        self.db = db_manager
        self.init_database()

    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Clients table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                contact_email TEXT,
                contact_person TEXT,
                wallet_addresses TEXT,  -- JSON array of preferred wallet addresses
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Invoices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
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
                line_items TEXT,  -- JSON array of line items
                due_date DATE NOT NULL,
                issue_date DATE NOT NULL,
                payment_tolerance REAL DEFAULT 0.005,  -- 0.5% tolerance
                pdf_path TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        """)

        # Payment transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                transaction_hash TEXT UNIQUE,
                amount_received REAL NOT NULL,
                currency TEXT NOT NULL,
                network TEXT NOT NULL,
                deposit_address TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'detected',
                confirmations INTEGER DEFAULT 0,
                required_confirmations INTEGER DEFAULT 6,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TIMESTAMP,
                block_height INTEGER,
                memo_tag TEXT,
                is_manual_verification BOOLEAN DEFAULT 0,
                verified_by TEXT,
                mexc_transaction_id TEXT,
                raw_api_response TEXT,  -- JSON of MEXC API response
                FOREIGN KEY (invoice_id) REFERENCES invoices(id)
            )
        """)

        # MEXC deposit addresses cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mexc_addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                currency TEXT NOT NULL,
                network TEXT NOT NULL,
                address TEXT NOT NULL,
                memo_tag TEXT,
                is_used BOOLEAN DEFAULT 0,
                used_for_invoice_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(currency, network, address)
            )
        """)

        # Payment polling log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS polling_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                poll_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                deposits_found INTEGER DEFAULT 0,
                error_message TEXT,
                api_response TEXT,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id)
            )
        """)

        # Notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,  -- payment_detected, payment_confirmed, invoice_overdue
                recipient TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                sent_at TIMESTAMP,
                status TEXT DEFAULT 'pending',  -- pending, sent, failed
                error_message TEXT,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id)
            )
        """)

        # System configuration table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_due_date ON invoices(due_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_client ON invoices(client_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payment_transactions(invoice_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payment_transactions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_txhash ON payment_transactions(transaction_hash)")

        conn.commit()
        conn.close()

        # Insert default clients
        self._insert_default_clients()
        self._insert_default_config()

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

        conn = self.get_connection()
        cursor = conn.cursor()

        for client in default_clients:
            try:
                cursor.execute("""
                    INSERT INTO clients (name, contact_email, contact_person)
                    VALUES (?, ?, ?)
                """, (client["name"], client["contact_email"], client["contact_person"]))
            except sqlite3.IntegrityError:
                # Client already exists
                pass

        conn.commit()
        conn.close()

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

        conn = self.get_connection()
        cursor = conn.cursor()

        for key, value, description in default_config:
            cursor.execute("""
                INSERT OR IGNORE INTO system_config (key, value, description)
                VALUES (?, ?, ?)
            """, (key, value, description))

        conn.commit()
        conn.close()

    # Invoice CRUD operations

    def create_invoice(self, invoice_data: Dict[str, Any]) -> int:
        """Create new invoice"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO invoices (
                invoice_number, client_id, status, amount_usd, crypto_currency,
                crypto_amount, crypto_network, exchange_rate, deposit_address,
                memo_tag, billing_period, description, line_items, due_date,
                issue_date, payment_tolerance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
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
        ))

        invoice_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return invoice_id

    def get_invoice(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Get invoice by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT i.*, c.name as client_name, c.contact_email
            FROM invoices i
            JOIN clients c ON i.client_id = c.id
            WHERE i.id = ?
        """, (invoice_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            invoice = dict(row)
            invoice["line_items"] = json.loads(invoice["line_items"]) if invoice["line_items"] else []
            return invoice
        return None

    def get_pending_invoices(self) -> List[Dict[str, Any]]:
        """Get all pending/unpaid invoices for payment polling"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT i.*, c.name as client_name
            FROM invoices i
            JOIN clients c ON i.client_id = c.id
            WHERE i.status IN ('sent', 'partially_paid')
            ORDER BY i.due_date ASC
        """)

        rows = cursor.fetchall()
        conn.close()

        invoices = []
        for row in rows:
            invoice = dict(row)
            invoice["line_items"] = json.loads(invoice["line_items"]) if invoice["line_items"] else []
            invoices.append(invoice)

        return invoices

    def update_invoice_status(self, invoice_id: int, status: str, paid_at: Optional[datetime] = None):
        """Update invoice status"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if paid_at:
            cursor.execute("""
                UPDATE invoices
                SET status = ?, paid_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, paid_at, invoice_id))
        else:
            cursor.execute("""
                UPDATE invoices
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, invoice_id))

        conn.commit()
        conn.close()

    def update_invoice_pdf_path(self, invoice_id: int, pdf_path: str):
        """Update invoice PDF path"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE invoices SET pdf_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (pdf_path, invoice_id))

        conn.commit()
        conn.close()

    # Payment transaction operations

    def create_payment_transaction(self, payment_data: Dict[str, Any]) -> int:
        """Record payment transaction"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO payment_transactions (
                invoice_id, transaction_hash, amount_received, currency,
                network, deposit_address, status, confirmations,
                required_confirmations, block_height, memo_tag,
                is_manual_verification, verified_by, mexc_transaction_id,
                raw_api_response
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
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
        ))

        payment_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return payment_id

    def get_payments_for_invoice(self, invoice_id: int) -> List[Dict[str, Any]]:
        """Get all payment transactions for an invoice"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM payment_transactions
            WHERE invoice_id = ?
            ORDER BY detected_at DESC
        """, (invoice_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_payment_confirmations(self, payment_id: int, confirmations: int, status: str = None):
        """Update payment confirmation count"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                UPDATE payment_transactions
                SET confirmations = ?, status = ?, confirmed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (confirmations, status, payment_id))
        else:
            cursor.execute("""
                UPDATE payment_transactions
                SET confirmations = ?
                WHERE id = ?
            """, (confirmations, payment_id))

        conn.commit()
        conn.close()

    # Client operations

    def get_all_clients(self) -> List[Dict[str, Any]]:
        """Get all clients"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM clients ORDER BY name")
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_client_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get client by name"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM clients WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    # MEXC address cache operations

    def cache_mexc_address(self, currency: str, network: str, address: str, memo_tag: str = None):
        """Cache MEXC deposit address"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO mexc_addresses (currency, network, address, memo_tag)
                VALUES (?, ?, ?, ?)
            """, (currency, network, address, memo_tag))
            conn.commit()
        except sqlite3.IntegrityError:
            # Address already cached
            pass

        conn.close()

    def mark_address_used(self, address: str, invoice_id: int):
        """Mark address as used for an invoice"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE mexc_addresses
            SET is_used = 1, used_for_invoice_id = ?
            WHERE address = ?
        """, (invoice_id, address))

        conn.commit()
        conn.close()

    # Configuration operations

    def get_config(self, key: str) -> Optional[str]:
        """Get configuration value"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()

        return row["value"] if row else None

    def set_config(self, key: str, value: str):
        """Set configuration value"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO system_config (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))

        conn.commit()
        conn.close()

    # Polling log operations

    def log_polling_event(self, invoice_id: int, status: str, deposits_found: int = 0,
                         error_message: str = None, api_response: str = None):
        """Log a polling event"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO polling_log (invoice_id, status, deposits_found, error_message, api_response)
            VALUES (?, ?, ?, ?, ?)
        """, (invoice_id, status, deposits_found, error_message, api_response))

        conn.commit()
        conn.close()

    # Notification operations

    def create_notification(self, invoice_id: int, notification_type: str,
                          recipient: str, subject: str, message: str) -> int:
        """Create notification record"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO notifications (invoice_id, notification_type, recipient, subject, message)
            VALUES (?, ?, ?, ?, ?)
        """, (invoice_id, notification_type, recipient, subject, message))

        notification_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return notification_id

    def mark_notification_sent(self, notification_id: int, status: str = "sent", error_message: str = None):
        """Mark notification as sent"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE notifications
            SET status = ?, sent_at = CURRENT_TIMESTAMP, error_message = ?
            WHERE id = ?
        """, (status, error_message, notification_id))

        conn.commit()
        conn.close()

    def get_pending_notifications(self) -> List[Dict[str, Any]]:
        """Get pending notifications"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM notifications
            WHERE status = 'pending'
            ORDER BY id ASC
        """)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]
