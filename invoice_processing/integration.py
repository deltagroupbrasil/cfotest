#!/usr/bin/env python3
"""
Integration Layer with Main Delta CFO System
MINIMAL integration points to avoid conflicts with other developers
"""

import sqlite3
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

# Add main system to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class MainSystemIntegrator:
    """
    Minimal integration with main Delta CFO system
    Only touches database and provides isolated web routes
    """

    def __init__(self, db_path: Optional[str] = None):
        # Use main system database
        if db_path is None:
            main_web_ui = Path(__file__).parent.parent / "web_ui"
            self.db_path = main_web_ui / "delta_transactions.db"
        else:
            self.db_path = Path(db_path)

    def create_invoice_tables(self):
        """
        Create invoice tables in main database
        ISOLATED from main transaction tables
        """
        with sqlite3.connect(self.db_path) as conn:
            # Main invoices table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id TEXT PRIMARY KEY,
                    invoice_number TEXT UNIQUE NOT NULL,
                    date TEXT NOT NULL,
                    due_date TEXT,
                    vendor_name TEXT NOT NULL,
                    vendor_data TEXT,  -- JSON blob
                    total_amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    tax_amount REAL,
                    subtotal REAL,
                    line_items TEXT,  -- JSON blob
                    payment_terms TEXT,
                    status TEXT DEFAULT 'pending',
                    invoice_type TEXT DEFAULT 'other',
                    confidence_score REAL DEFAULT 0.0,
                    processing_notes TEXT,
                    source_file TEXT,
                    email_id TEXT,
                    processed_at TEXT,
                    created_at TEXT NOT NULL,
                    business_unit TEXT,
                    category TEXT,
                    -- Integration with main system
                    linked_transaction_id TEXT,
                    FOREIGN KEY (linked_transaction_id) REFERENCES transactions(transaction_id)
                )
            ''')

            # Email processing log
            conn.execute('''
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

            # Processing queue
            conn.execute('''
                CREATE TABLE IF NOT EXISTS invoice_processing_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    email_id TEXT,
                    status TEXT DEFAULT 'queued',
                    priority INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT
                )
            ''')

            conn.commit()
            print("Invoice tables created in main database")

    def save_invoice(self, invoice_dict: Dict[str, Any]) -> str:
        """
        Save invoice to database
        Returns invoice ID
        """
        with sqlite3.connect(self.db_path) as conn:
            # Generate ID if not provided
            if not invoice_dict.get('id'):
                import uuid
                invoice_dict['id'] = str(uuid.uuid4())

            conn.execute('''
                INSERT OR REPLACE INTO invoices (
                    id, invoice_number, date, due_date, vendor_name, vendor_data,
                    total_amount, currency, tax_amount, subtotal, line_items,
                    payment_terms, status, invoice_type, confidence_score,
                    processing_notes, source_file, email_id, processed_at,
                    created_at, business_unit, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_dict['id'],
                invoice_dict['invoice_number'],
                invoice_dict['date'],
                invoice_dict.get('due_date'),
                invoice_dict['vendor']['name'],
                json.dumps(invoice_dict['vendor']),
                invoice_dict['total_amount'],
                invoice_dict['currency'],
                invoice_dict.get('tax_amount'),
                invoice_dict.get('subtotal'),
                json.dumps(invoice_dict['line_items']),
                invoice_dict.get('payment_terms'),
                invoice_dict['status'],
                invoice_dict['invoice_type'],
                invoice_dict['confidence_score'],
                invoice_dict.get('processing_notes'),
                invoice_dict.get('source_file'),
                invoice_dict.get('email_id'),
                invoice_dict.get('processed_at'),
                invoice_dict['created_at'],
                invoice_dict.get('business_unit'),
                invoice_dict.get('category')
            ))
            conn.commit()
            return invoice_dict['id']

    def get_invoices(self, limit: int = 50, offset: int = 0, filters: Optional[Dict] = None) -> List[Dict]:
        """Get invoices with pagination and filtering"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM invoices WHERE 1=1"
            params = []

            if filters:
                if filters.get('status'):
                    query += " AND status = ?"
                    params.append(filters['status'])

                if filters.get('business_unit'):
                    query += " AND business_unit = ?"
                    params.append(filters['business_unit'])

                if filters.get('vendor_name'):
                    query += " AND vendor_name LIKE ?"
                    params.append(f"%{filters['vendor_name']}%")

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def create_transaction_from_invoice(self, invoice_dict: Dict[str, Any]) -> Optional[str]:
        """
        Create a transaction in main system from invoice
        MINIMAL integration - just creates a transaction record
        """
        try:
            # Import main system's transaction creation logic
            # This is the ONLY place we touch main system code
            from main import DeltaCFOAgent

            # Create a transaction-like record for the invoice
            transaction_data = {
                'Date': invoice_dict['date'],
                'Description': f"Invoice {invoice_dict['invoice_number']} - {invoice_dict['vendor']['name']}",
                'Amount': -float(invoice_dict['total_amount']),  # Negative for expense
                'classified_entity': invoice_dict.get('business_unit', 'Delta LLC'),
                'confidence': invoice_dict['confidence_score'],
                'classification_reason': f"Automated invoice processing",
                'source_file': f"invoice_{invoice_dict['invoice_number']}",
                'Business_Unit': invoice_dict.get('business_unit', 'Delta LLC'),
                'Justification': f"Invoice processing: {invoice_dict.get('processing_notes', '')}"
            }

            # Save to main transactions table
            agent = DeltaCFOAgent()
            # This would integrate with main system - implement later
            print(f"🔗 Integration point: Would create transaction for invoice {invoice_dict['invoice_number']}")
            return None

        except Exception as e:
            print(f"⚠️  Transaction creation failed: {e}")
            return None

# Flask Integration (Isolated routes)
def register_invoice_routes(app):
    """
    Register invoice routes with main Flask app
    ISOLATED routes that don't interfere with main system
    """

    @app.route('/invoices')
    def invoice_dashboard():
        """Invoice management dashboard"""
        # Import templates from our isolated module
        try:
            from flask import render_template
            integrator = MainSystemIntegrator()
            invoices = integrator.get_invoices(limit=20)
            return render_template('invoice_dashboard.html', invoices=invoices)
        except Exception as e:
            return f"Invoice module not ready: {e}", 500

    @app.route('/api/v1/invoices')
    def api_list_invoices():
        """API endpoint for invoices"""
        from flask import jsonify, request
        try:
            integrator = MainSystemIntegrator()
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 20))
            offset = (page - 1) * limit

            invoices = integrator.get_invoices(limit=limit, offset=offset)
            return jsonify({
                'invoices': invoices,
                'page': page,
                'limit': limit,
                'total': len(invoices)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# Initialization function
def initialize_invoice_system():
    """Initialize invoice system with main system"""
    try:
        integrator = MainSystemIntegrator()
        integrator.create_invoice_tables()
        print("✅ Invoice system initialized and integrated")
        return integrator
    except Exception as e:
        print(f"❌ Invoice system initialization failed: {e}")
        return None