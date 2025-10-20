#!/usr/bin/env python3
"""
Invoice Upload Interface
Interface web dedicada para upload manual de faturas
"""

import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

# Add parent to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import PROCESSING_CONFIG, UPLOAD_DIR, PROCESSED_DIR
from services.claude_vision import ClaudeVisionService
from integration import MainSystemIntegrator

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.urandom(24)  # For flash messages

class InvoiceUploadHandler:
    """Handler para upload e processamento de faturas"""

    def __init__(self):
        self.claude_service = ClaudeVisionService()
        self.integrator = MainSystemIntegrator()
        self.upload_dir = UPLOAD_DIR
        self.processed_dir = PROCESSED_DIR

        # Ensure directories exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def is_allowed_file(self, filename: str) -> bool:
        """Check if file type is allowed"""
        return Path(filename).suffix.lower() in PROCESSING_CONFIG['ALLOWED_EXTENSIONS']

    def save_uploaded_file(self, file) -> dict:
        """Save uploaded file and return file info"""
        try:
            if not file or not file.filename:
                return {'error': 'No file provided'}

            if not self.is_allowed_file(file.filename):
                return {'error': f'File type not supported. Allowed: {", ".join(PROCESSING_CONFIG["ALLOWED_EXTENSIONS"])}'}

            # Generate unique filename
            file_ext = Path(file.filename).suffix.lower()
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = self.upload_dir / unique_filename

            # Save file
            file.save(str(file_path))

            # Check file size
            file_size = file_path.stat().st_size
            if file_size > PROCESSING_CONFIG['MAX_FILE_SIZE']:
                file_path.unlink()  # Delete file
                return {'error': f'File too large. Max size: {PROCESSING_CONFIG["MAX_FILE_SIZE"] / 1024 / 1024:.1f}MB'}

            file_info = {
                'original_filename': file.filename,
                'saved_filename': unique_filename,
                'file_path': str(file_path),
                'file_size': file_size,
                'upload_time': datetime.now().isoformat(),
                'file_type': file_ext
            }

            return {'success': True, 'file_info': file_info}

        except Exception as e:
            return {'error': f'Failed to save file: {str(e)}'}

    def process_uploaded_invoice(self, file_path: str) -> dict:
        """Process uploaded invoice file"""
        try:
            # Extract data with Claude Vision
            extracted_data = self.claude_service.extract_invoice_data(file_path)

            if extracted_data.get('status') == 'error':
                return extracted_data

            # Enhance with Delta business intelligence
            enhanced_data = self.enhance_with_business_intelligence(extracted_data)

            # Save to database
            invoice_id = self.integrator.save_invoice(enhanced_data)

            # Move file to processed directory
            processed_path = self.processed_dir / Path(file_path).name
            Path(file_path).rename(processed_path)

            return {
                'success': True,
                'invoice_id': invoice_id,
                'extracted_data': enhanced_data,
                'file_processed': str(processed_path)
            }

        except Exception as e:
            return {'error': f'Processing failed: {str(e)}'}

    def enhance_with_business_intelligence(self, extracted_data: dict) -> dict:
        """Enhance extracted data with Delta business intelligence"""
        # Import Delta classifier
        from ..core.delta_classifier import DeltaBusinessClassifier

        classifier = DeltaBusinessClassifier()

        # Get enhanced classification
        classification_result = classifier.classify_invoice(extracted_data)

        # Merge with original data
        enhanced = extracted_data.copy()
        enhanced.update(classification_result)

        # Add summary
        enhanced['classification_summary'] = classifier.get_classification_summary(classification_result)

        return enhanced

    def classify_business_unit(self, data: dict) -> str:
        """Classify which Delta business unit this invoice belongs to"""
        vendor_name = data.get('vendor_name', '').lower()
        category = data.get('category', '').lower()
        amount = data.get('total_amount', 0)

        # Technology expenses → Delta LLC
        if any(tech in vendor_name for tech in ['aws', 'amazon', 'microsoft', 'google', 'github', 'anthropic', 'openai']):
            return 'Delta LLC'

        # Cloud/Software services → Delta LLC
        if any(service in vendor_name for service in ['saas', 'software', 'cloud', 'api', 'platform']):
            return 'Delta LLC'

        # Paraguay operations
        if any(py in vendor_name for py in ['paraguay', 'asuncion', 'ande', 'copaco']):
            return 'Delta Mining Paraguay S.A.'

        # Brazilian operations
        if any(br in vendor_name for br in ['brasil', 'brazil', 'porto seguro', 'nubank', 'itau']):
            return 'Delta Brazil'

        # Crypto/Trading related
        if any(crypto in vendor_name for crypto in ['coinbase', 'binance', 'mexc', 'crypto', 'trading']):
            return 'Delta Prop Shop LLC'

        # Mining/Validator operations
        if any(mining in vendor_name for mining in ['mining', 'validator', 'subnet', 'bittensor']):
            return 'Infinity Validator'

        # High-value transactions likely go to main holding
        if amount > 10000:
            return 'Delta LLC'

        # Default to main entity
        return 'Delta LLC'

    def classify_category(self, data: dict) -> str:
        """Classify expense category"""
        vendor_name = data.get('vendor_name', '').lower()
        description = data.get('processing_notes', '').lower()

        # Technology
        if any(tech in vendor_name for tech in ['aws', 'google', 'microsoft', 'github', 'software', 'api']):
            return 'Technology Expenses'

        # Utilities
        if any(util in vendor_name for util in ['electric', 'power', 'energy', 'ande', 'copaco', 'internet']):
            return 'Utilities'

        # Insurance
        if any(ins in vendor_name for ins in ['insurance', 'seguro', 'porto seguro']):
            return 'Insurance'

        # Legal/Professional
        if any(prof in vendor_name for prof in ['legal', 'lawyer', 'attorney', 'accounting', 'consultant']):
            return 'Professional Services'

        # Banking/Financial
        if any(bank in vendor_name for bank in ['bank', 'financial', 'transfer', 'wire', 'payment']):
            return 'Bank Fees'

        # Travel
        if any(travel in vendor_name for travel in ['airline', 'hotel', 'uber', 'transport']):
            return 'Travel Expenses'

        # Office
        if any(office in vendor_name for office in ['office', 'supplies', 'equipment', 'furniture']):
            return 'Office Expenses'

        return 'Other'

    def detect_currency_type(self, data: dict) -> str:
        """Detect if transaction involves crypto or fiat currency"""
        currency = data.get('currency', 'USD').upper()
        vendor_name = data.get('vendor_name', '').lower()
        description = data.get('processing_notes', '').lower()

        # Crypto currencies
        crypto_currencies = ['BTC', 'ETH', 'TAO', 'USDC', 'USDT', 'BNB', 'SOL']
        if currency in crypto_currencies:
            return 'cryptocurrency'

        # Crypto-related vendors
        crypto_vendors = ['coinbase', 'binance', 'mexc', 'kraken', 'crypto', 'blockchain']
        if any(vendor in vendor_name for vendor in crypto_vendors):
            return 'cryptocurrency'

        # Mining/staking references
        mining_keywords = ['mining', 'staking', 'validator', 'subnet', 'rewards']
        if any(keyword in description for keyword in mining_keywords):
            return 'cryptocurrency'

        # Default to fiat
        return 'fiat'

    def classify_vendor_type(self, data: dict) -> str:
        """Classify type of vendor/client"""
        vendor_name = data.get('vendor_name', '').lower()

        # Technology vendors
        if any(tech in vendor_name for tech in ['aws', 'microsoft', 'google', 'github']):
            return 'Technology Provider'

        # Crypto exchanges
        if any(exchange in vendor_name for exchange in ['coinbase', 'binance', 'mexc']):
            return 'Crypto Exchange'

        # Utility companies
        if any(util in vendor_name for util in ['electric', 'power', 'ande', 'copaco']):
            return 'Utility Company'

        # Financial institutions
        if any(bank in vendor_name for bank in ['bank', 'credit', 'financial']):
            return 'Financial Institution'

        # Government/Tax
        if any(gov in vendor_name for gov in ['tax', 'government', 'irs', 'receita']):
            return 'Government Agency'

        return 'Other Vendor'

    def calculate_classification_confidence(self, original_data: dict, enhanced_data: dict) -> float:
        """Calculate overall classification confidence"""
        base_confidence = original_data.get('confidence', 0.8)

        # Adjust based on business unit classification certainty
        bu_confidence = 1.0 if enhanced_data['business_unit'] != 'Delta LLC' else 0.9  # Default = lower confidence

        # Adjust based on category classification
        cat_confidence = 1.0 if enhanced_data['category'] != 'Other' else 0.8

        # Adjust based on currency detection
        currency_confidence = 1.0 if enhanced_data['currency_type'] == 'cryptocurrency' else 0.95

        # Calculate weighted average
        overall_confidence = (base_confidence * 0.4 + bu_confidence * 0.3 + cat_confidence * 0.2 + currency_confidence * 0.1)

        return min(overall_confidence, 1.0)  # Cap at 1.0

# Flask routes
upload_handler = InvoiceUploadHandler()

@app.route('/')
def upload_form():
    """Upload form page"""
    return render_template('invoice_upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    try:
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)

        file = request.files['file']

        # Save file
        save_result = upload_handler.save_uploaded_file(file)

        if 'error' in save_result:
            flash(save_result['error'], 'error')
            return redirect(url_for('upload_form'))

        # Process invoice
        process_result = upload_handler.process_uploaded_invoice(save_result['file_info']['file_path'])

        if 'error' in process_result:
            flash(f"Processing failed: {process_result['error']}", 'error')
            return redirect(url_for('upload_form'))

        flash('Invoice processed successfully!', 'success')
        return redirect(url_for('invoice_result', invoice_id=process_result['invoice_id']))

    except Exception as e:
        flash(f'Upload failed: {str(e)}', 'error')
        return redirect(url_for('upload_form'))

@app.route('/result/<invoice_id>')
def invoice_result(invoice_id):
    """Show processing result"""
    try:
        # Get invoice from database
        invoices = upload_handler.integrator.get_invoices(limit=1, filters={'id': invoice_id})

        if not invoices:
            flash('Invoice not found', 'error')
            return redirect(url_for('upload_form'))

        invoice = invoices[0]
        return render_template('invoice_result.html', invoice=invoice)

    except Exception as e:
        flash(f'Error loading result: {str(e)}', 'error')
        return redirect(url_for('upload_form'))

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """API endpoint for file upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        # Save and process
        save_result = upload_handler.save_uploaded_file(file)
        if 'error' in save_result:
            return jsonify(save_result), 400

        process_result = upload_handler.process_uploaded_invoice(save_result['file_info']['file_path'])
        if 'error' in process_result:
            return jsonify(process_result), 500

        return jsonify({
            'success': True,
            'invoice_id': process_result['invoice_id'],
            'extracted_data': process_result['extracted_data']
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize database
    upload_handler.integrator.create_invoice_tables()
    print("🚀 Invoice Upload Interface starting...")
    print("   Access: http://localhost:5002")
    app.run(host='0.0.0.0', port=5002, debug=True)