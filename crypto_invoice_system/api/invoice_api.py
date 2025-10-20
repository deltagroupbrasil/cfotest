#!/usr/bin/env python3
"""
Flask API for Crypto Invoice System
Web interface for creating and managing crypto invoices
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime, date, timedelta
import logging
from typing import Dict, Any

# Load environment variables
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database_postgresql import CryptoInvoiceDatabaseManager, InvoiceStatus
from services.mexc_service import MEXCService, MEXCAPIError
from services.invoice_generator import InvoiceGenerator
from services.payment_poller import PaymentPoller


# Initialize Flask app
app = Flask(__name__,
           template_folder='../templates',
           static_folder='../static')

# Configuration
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services with absolute paths
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
invoice_dir = os.path.join(base_dir, "generated_invoices")

# Initialize PostgreSQL database manager (no longer using SQLite)
db_manager = CryptoInvoiceDatabaseManager()
invoice_generator = InvoiceGenerator(invoice_dir)

# Initialize MEXC service (API keys from environment)
mexc_api_key = os.getenv('MEXC_API_KEY') or 'mx0vglFBKknNUwIGuR'
mexc_api_secret = os.getenv('MEXC_API_SECRET') or 'c4eeba8fd03f4132bb34b48e30e84872'

logger.info(f"MEXC API Key: {mexc_api_key[:10]}... (loaded)")

if mexc_api_key and mexc_api_secret:
    mexc_service = MEXCService(mexc_api_key, mexc_api_secret)

    # Initialize payment poller
    payment_poller = PaymentPoller(
        mexc_service=mexc_service,
        db_manager=db_manager,
        poll_interval=30
    )
    payment_poller.start()
    logger.info("Payment polling service started")
else:
    mexc_service = None
    payment_poller = None
    logger.warning("MEXC API credentials not found - payment polling disabled")


# Routes

@app.route('/')
def index():
    """Dashboard homepage"""
    return render_template('dashboard.html')


@app.route('/create-invoice')
def create_invoice_page():
    """Invoice creation form"""
    clients = db_manager.get_all_clients()
    return render_template('create_invoice.html', clients=clients)


@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get all clients"""
    try:
        clients = db_manager.get_all_clients()
        return jsonify({"success": True, "clients": clients})
    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/crypto-price/<currency>', methods=['GET'])
def get_crypto_price(currency):
    """Get current cryptocurrency price"""
    try:
        network = request.args.get('network', '')
        price = invoice_generator.get_crypto_price(currency, network)
        return jsonify({"success": True, "price": price, "currency": currency})
    except Exception as e:
        logger.error(f"Error fetching crypto price: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/invoice/create', methods=['POST'])
def create_invoice():
    """Create new invoice"""
    try:
        data = request.json

        # Validate required fields
        required_fields = ['client_id', 'amount_usd', 'crypto_currency',
                          'crypto_network', 'billing_period', 'due_date']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

        # Get client info
        client = db_manager.get_all_clients()[int(data['client_id']) - 1]

        # Get primary deposit address from MEXC (shared address for all invoices)
        if mexc_service:
            try:
                address_info = mexc_service.get_primary_deposit_address(
                    currency=data['crypto_currency'],
                    network=data['crypto_network']
                )
                deposit_address = address_info['address']
                memo_tag = address_info.get('memo')
                logger.info(f"Using MEXC primary address for {data['crypto_currency']}/{data['crypto_network']}: {deposit_address}")
            except MEXCAPIError as e:
                logger.error(f"MEXC API error: {e}")
                return jsonify({"success": False, "error": f"MEXC API error: {str(e)}"}), 500
        else:
            # Demo mode - generate mock addresses for testing
            logger.warning("Using DEMO mode - generating mock deposit address")
            import hashlib
            mock_seed = f"{data['crypto_currency']}-{data['crypto_network']}-{datetime.now().timestamp()}"

            if data['crypto_currency'] == 'BTC':
                deposit_address = 'bc1q' + hashlib.sha256(mock_seed.encode()).hexdigest()[:38]
            elif data['crypto_currency'] == 'USDT' and data['crypto_network'] == 'TRC20':
                deposit_address = 'T' + hashlib.sha256(mock_seed.encode()).hexdigest()[:33]
            elif data['crypto_currency'] == 'USDT' and data['crypto_network'] == 'ERC20':
                deposit_address = '0x' + hashlib.sha256(mock_seed.encode()).hexdigest()[:40]
            elif data['crypto_currency'] == 'USDT' and data['crypto_network'] == 'BEP20':
                deposit_address = '0x' + hashlib.sha256(mock_seed.encode()).hexdigest()[:40]
            elif data['crypto_currency'] == 'TAO':
                deposit_address = '5' + hashlib.sha256(mock_seed.encode()).hexdigest()[:47]
            else:
                deposit_address = hashlib.sha256(mock_seed.encode()).hexdigest()

            memo_tag = None
            logger.info(f"DEMO: Generated mock address: {deposit_address}")

        # Get crypto price and calculate amount
        crypto_price = invoice_generator.get_crypto_price(
            data['crypto_currency'],
            data['crypto_network']
        )
        base_crypto_amount = invoice_generator.calculate_crypto_amount(
            float(data['amount_usd']),
            crypto_price
        )

        # Generate invoice number first
        invoice_number = invoice_generator.generate_invoice_number()

        # Create unique amount for better matching (adds tiny fraction based on invoice number)
        from services.amount_based_matcher import AmountBasedPaymentMatcher
        matcher = AmountBasedPaymentMatcher()
        crypto_amount = matcher.calculate_unique_amount(base_crypto_amount, invoice_number)

        # Generate QR code
        qr_filename = f"qr_{invoice_number}.png"
        payment_uri = invoice_generator.create_payment_uri(
            currency=data['crypto_currency'],
            address=deposit_address,
            amount=crypto_amount,
            label=f"Delta Energy Invoice {invoice_number}"
        )
        qr_code_path = invoice_generator.generate_qr_code(payment_uri, qr_filename)

        # Prepare invoice data
        invoice_data = {
            "invoice_number": invoice_number,
            "client_id": data['client_id'],
            "client_name": client['name'],
            "client_contact": client.get('contact_email', ''),
            "status": "sent",
            "amount_usd": float(data['amount_usd']),
            "crypto_currency": data['crypto_currency'],
            "crypto_amount": crypto_amount,
            "crypto_network": data['crypto_network'],
            "exchange_rate": crypto_price,
            "deposit_address": deposit_address,
            "memo_tag": memo_tag,
            "billing_period": data['billing_period'],
            "description": data.get('description', ''),
            "line_items": data.get('line_items', []),
            "due_date": data['due_date'],
            "issue_date": date.today().isoformat(),
            "payment_tolerance": 0.005,
            "qr_code_path": qr_code_path,
            "notes": data.get('notes', '')
        }

        # Save to database
        invoice_id = db_manager.create_invoice(invoice_data)

        # Generate PDF
        pdf_path = invoice_generator.generate_pdf_invoice(invoice_data)
        db_manager.update_invoice_pdf_path(invoice_id, pdf_path)

        # Cache MEXC address
        db_manager.cache_mexc_address(
            currency=data['crypto_currency'],
            network=data['crypto_network'],
            address=deposit_address,
            memo_tag=memo_tag
        )
        db_manager.mark_address_used(deposit_address, invoice_id)

        logger.info(f"Invoice created: {invoice_number} (ID: {invoice_id})")

        return jsonify({
            "success": True,
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "pdf_path": pdf_path,
            "deposit_address": deposit_address
        })

    except Exception as e:
        logger.error(f"Error creating invoice: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/invoices', methods=['GET'])
def get_invoices():
    """Get all invoices with filtering"""
    try:
        status_filter = request.args.get('status')

        conn = db_manager.get_connection()
        cursor = conn.cursor()

        if status_filter:
            cursor.execute("""
                SELECT i.*, c.name as client_name
                FROM invoices i
                JOIN clients c ON i.client_id = c.id
                WHERE i.status = ?
                ORDER BY i.created_at DESC
            """, (status_filter,))
        else:
            cursor.execute("""
                SELECT i.*, c.name as client_name
                FROM invoices i
                JOIN clients c ON i.client_id = c.id
                ORDER BY i.created_at DESC
            """)

        invoices = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({"success": True, "invoices": invoices})

    except Exception as e:
        logger.error(f"Error fetching invoices: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/invoice/<int:invoice_id>', methods=['GET'])
def get_invoice_details(invoice_id):
    """Get detailed invoice information"""
    try:
        invoice = db_manager.get_invoice(invoice_id)
        if not invoice:
            return jsonify({"success": False, "error": "Invoice not found"}), 404

        # Get payment transactions
        payments = db_manager.get_payments_for_invoice(invoice_id)

        return jsonify({
            "success": True,
            "invoice": invoice,
            "payments": payments
        })

    except Exception as e:
        logger.error(f"Error fetching invoice details: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/invoice/<int:invoice_id>/pdf', methods=['GET'])
def download_invoice_pdf(invoice_id):
    """Download invoice PDF"""
    try:
        invoice = db_manager.get_invoice(invoice_id)
        if not invoice:
            return jsonify({"success": False, "error": "Invoice not found"}), 404

        pdf_path = invoice.get('pdf_path')
        if not pdf_path or not os.path.exists(pdf_path):
            return jsonify({"success": False, "error": "PDF file not found"}), 404

        return send_file(pdf_path, as_attachment=True,
                        download_name=f"{invoice['invoice_number']}.pdf")

    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/invoice/<int:invoice_id>/verify-payment', methods=['POST'])
def verify_payment_manually(invoice_id):
    """Manually verify payment by transaction ID"""
    try:
        if not payment_poller:
            return jsonify({"success": False, "error": "Payment poller not initialized"}), 500

        data = request.json
        txid = data.get('txid')
        verified_by = data.get('verified_by', 'Admin')

        if not txid:
            return jsonify({"success": False, "error": "Transaction ID required"}), 400

        result = payment_poller.manual_payment_verification(
            invoice_id=invoice_id,
            txid=txid,
            verified_by=verified_by
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/polling-stats', methods=['GET'])
def get_polling_stats():
    """Get payment polling service statistics"""
    try:
        if not payment_poller:
            return jsonify({"success": False, "error": "Payment poller not initialized"}), 500

        stats = payment_poller.get_statistics()
        return jsonify({"success": True, "stats": stats})

    except Exception as e:
        logger.error(f"Error fetching polling stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        # Count invoices by status
        cursor.execute("""
            SELECT status, COUNT(*) as count, SUM(amount_usd) as total_usd
            FROM invoices
            GROUP BY status
        """)
        status_stats = [dict(row) for row in cursor.fetchall()]

        # Get recent invoices
        cursor.execute("""
            SELECT i.*, c.name as client_name
            FROM invoices i
            JOIN clients c ON i.client_id = c.id
            ORDER BY i.created_at DESC
            LIMIT 10
        """)
        recent_invoices = [dict(row) for row in cursor.fetchall()]

        # Get pending payments count
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM invoices
            WHERE status IN ('sent', 'partially_paid')
        """)
        pending_count = cursor.fetchone()['count']

        conn.close()

        return jsonify({
            "success": True,
            "stats": {
                "status_breakdown": status_stats,
                "recent_invoices": recent_invoices,
                "pending_count": pending_count
            }
        })

    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/test-mexc', methods=['GET'])
def test_mexc_connection():
    """Test MEXC API connection"""
    try:
        if not mexc_service:
            return jsonify({"success": False, "error": "MEXC service not configured"}), 500

        connected = mexc_service.test_connection()
        server_time = mexc_service.get_server_time()

        return jsonify({
            "success": connected,
            "server_time": server_time,
            "message": "MEXC API connection successful" if connected else "Connection failed"
        })

    except Exception as e:
        logger.error(f"Error testing MEXC connection: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Error handlers

@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"success": False, "error": "Internal server error"}), 500


# Startup and shutdown

def shutdown_services():
    """Shutdown background services"""
    if payment_poller:
        payment_poller.stop()
        logger.info("Payment poller stopped")


import atexit
atexit.register(shutdown_services)


if __name__ == '__main__':
    # Run development server
    port = int(os.getenv('FLASK_PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=False)
