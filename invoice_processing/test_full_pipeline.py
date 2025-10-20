#!/usr/bin/env python3
"""
Full Pipeline Test - Upload com Claude Vision Real
Teste completo do pipeline de upload com processamento real de faturas
"""

import os
import sys
import sqlite3
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime
import uuid
import json
import anthropic
import base64

# Configuração do Claude
CLAUDE_API_KEY = os.getenv('ANTHROPIC_API_KEY') or input("Cole sua API key da Anthropic: ")

app = Flask(__name__)
app.secret_key = 'test_secret_key'

# Database setup
DB_PATH = Path(__file__).parent / "full_pipeline_test.db"

def init_db():
    """Initialize complete test database"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            invoice_number TEXT,
            date TEXT,
            vendor_name TEXT,
            vendor_data TEXT,
            total_amount REAL,
            currency TEXT,
            business_unit TEXT,
            category TEXT,
            confidence_score REAL,
            processing_notes TEXT,
            source_file TEXT,
            processed_at TEXT,
            created_at TEXT,
            extraction_method TEXT,
            raw_claude_response TEXT
        )
    ''')
    conn.commit()
    conn.close()

class SimplifiedClaudeVision:
    """Simplified Claude Vision for testing"""

    def __init__(self, api_key):
        self.client = anthropic.Anthropic(api_key=api_key)

    def extract_invoice_data(self, file_path):
        """Extract data from text file or PDF"""
        try:
            content = ""

            # Handle different file types
            if file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                extraction_type = "text_analysis"

            elif file_path.endswith('.pdf'):
                # Convert PDF to image and use vision
                image_base64 = self._pdf_to_image_base64(file_path)
                return self._call_claude_vision_with_image(image_base64, file_path)

            else:
                return {
                    'status': 'error',
                    'error': f'Unsupported file type: {os.path.splitext(file_path)[1]}'
                }

            # For text files, use text analysis
            prompt = f"""
Analyze this invoice text and extract information in JSON format:

{content}

Return ONLY a JSON object with this structure:
{{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "vendor_name": "string",
    "total_amount": 1234.56,
    "currency": "USD",
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Analysis notes"
}}
"""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response_text = response.content[0].text.strip()

            # Clean JSON response
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            extracted_data = json.loads(response_text)

            # Add metadata
            extracted_data.update({
                'source_file': os.path.basename(file_path),
                'extraction_method': extraction_type,
                'processed_at': datetime.now().isoformat(),
                'status': 'success'
            })

            return extracted_data

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def _pdf_to_image_base64(self, pdf_path):
        """Convert PDF first page to base64 image using PyMuPDF"""
        try:
            import fitz  # PyMuPDF
            from io import BytesIO

            # Open PDF and get first page
            doc = fitz.open(pdf_path)
            if doc.page_count == 0:
                raise ValueError("PDF has no pages")

            # Get first page as image
            page = doc.load_page(0)  # First page
            mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)

            # Convert to PNG bytes
            image_bytes = pix.pil_tobytes(format="PNG")
            doc.close()

            return base64.b64encode(image_bytes).decode('utf-8')

        except ImportError:
            raise ValueError("PyMuPDF not installed. Run: pip install PyMuPDF")
        except Exception as e:
            raise ValueError(f"PDF conversion failed: {e}")

    def _call_claude_vision_with_image(self, image_base64, file_path):
        """Call Claude Vision API with image"""
        try:
            prompt = """
Analyze this invoice image and extract the following information in JSON format.

Extract these fields with high accuracy:

REQUIRED FIELDS:
- invoice_number: The invoice/bill number
- date: Invoice date (YYYY-MM-DD format)
- vendor_name: Company/vendor name
- total_amount: Total amount (numeric value only)
- currency: Currency (USD, BRL, etc.)

CLASSIFICATION HINTS:
Based on the vendor, suggest:
- business_unit: One of ["Delta LLC", "Delta Prop Shop LLC", "Delta Mining Paraguay S.A.", "Delta Brazil", "Personal"]
- category: One of ["Technology Expenses", "Utilities", "Insurance", "Professional Services", "Trading Expenses", "Other"]

Return ONLY a JSON object with this structure:
{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "vendor_name": "string",
    "total_amount": 1234.56,
    "currency": "USD",
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Analysis notes"
}

Be precise with numbers and dates. If a field is not clearly visible, use reasonable defaults.
"""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            response_text = response.content[0].text.strip()

            # Clean JSON response
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            extracted_data = json.loads(response_text)

            # Add metadata
            extracted_data.update({
                'source_file': os.path.basename(file_path),
                'extraction_method': 'claude_vision',
                'processed_at': datetime.now().isoformat(),
                'status': 'success'
            })

            return extracted_data

        except Exception as e:
            return {
                'status': 'error',
                'error': f"Vision API error: {str(e)}"
            }

# Initialize Claude service
claude_service = SimplifiedClaudeVision(CLAUDE_API_KEY)

# Enhanced HTML template with results display
UPLOAD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Delta CFO Agent - Full Pipeline Test</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 20px auto; padding: 20px; }
        .container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .upload-section { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        .results-section { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        .upload-area { border: 2px dashed #ccc; padding: 30px; text-align: center; margin: 20px 0; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        .status { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .json-output { background: #f8f9fa; border: 1px solid #e9ecef; padding: 15px; border-radius: 5px; white-space: pre-wrap; font-family: monospace; font-size: 12px; }
        .invoice-details { background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .metric { display: inline-block; margin: 5px 10px; padding: 5px 10px; background: #f0f0f0; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Delta CFO Agent - Full Pipeline Test</h1>
    <p>Teste completo: Upload → Claude Vision → Business Classification → Database</p>

    <div class="container">
        <div class="upload-section">
            <h2>Upload & Processing</h2>

            {% if status %}
                <div class="status {{ status.type }}">{{ status.message }}</div>
            {% endif %}

            <form method="POST" enctype="multipart/form-data">
                <div class="upload-area">
                    <h3>Selecione uma fatura para processar</h3>
                    <input type="file" name="file" accept=".txt,.pdf,.png,.jpg,.jpeg" required>
                </div>
                <button type="submit" class="btn">Processar com Claude Vision</button>
            </form>

            <h3>Sistema Status</h3>
            <div class="metric">Database: ✅ Conectado</div>
            <div class="metric">Claude API: ✅ Configurado</div>
            <div class="metric">Total Processed: {{ total_invoices }}</div>
        </div>

        <div class="results-section">
            <h2>Últimos Resultados</h2>

            {% if latest_result %}
            <div class="invoice-details">
                <h3>Dados Extraídos:</h3>
                <p><strong>Invoice #:</strong> {{ latest_result.invoice_number }}</p>
                <p><strong>Vendor:</strong> {{ latest_result.vendor_name }}</p>
                <p><strong>Amount:</strong> ${{ latest_result.total_amount }} {{ latest_result.currency }}</p>
                <p><strong>Business Unit:</strong> {{ latest_result.business_unit }}</p>
                <p><strong>Category:</strong> {{ latest_result.category }}</p>
                <p><strong>Confidence:</strong> {{ (latest_result.confidence_score * 100) | round(1) }}%</p>
                <p><strong>Date:</strong> {{ latest_result.date }}</p>
            </div>
            {% endif %}

            <h3>Invoices Processadas ({{ total_invoices }})</h3>
            {% for invoice in recent_invoices %}
                <div style="border: 1px solid #ddd; padding: 8px; margin: 5px 0; font-size: 14px;">
                    <strong>{{ invoice[2] }}</strong> - ${{ invoice[5] }} - {{ invoice[7] }}
                    <br><small>{{ invoice[1] }} | Confidence: {{ (invoice[9] * 100) | round }}%</small>
                </div>
            {% endfor %}
        </div>
    </div>

    {% if claude_response %}
    <div style="margin-top: 20px;">
        <h3>Claude Response (Debug)</h3>
        <div class="json-output">{{ claude_response }}</div>
    </div>
    {% endif %}

</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def upload_form():
    """Full pipeline upload form"""
    status = None
    latest_result = None
    claude_response = None

    if request.method == 'POST':
        if 'file' not in request.files:
            status = {'type': 'error', 'message': 'Nenhum arquivo selecionado'}
        else:
            file = request.files['file']
            if file.filename == '':
                status = {'type': 'error', 'message': 'Nenhum arquivo selecionado'}
            else:
                try:
                    # Save uploaded file temporarily
                    temp_path = Path(__file__).parent / "temp_uploads"
                    temp_path.mkdir(exist_ok=True)
                    file_path = temp_path / file.filename
                    file.save(str(file_path))

                    print(f"\n Processing: {file.filename}")

                    # Extract with Claude Vision
                    extracted_data = claude_service.extract_invoice_data(str(file_path))

                    if extracted_data.get('status') == 'error':
                        status = {'type': 'error', 'message': f'Claude Vision error: {extracted_data["error"]}'}
                    else:
                        # Enhance with business intelligence
                        enhanced_data = enhance_with_business_intelligence(extracted_data)

                        # Save to database
                        invoice_id = save_invoice_to_db(enhanced_data)

                        status = {'type': 'success', 'message': f'Invoice processed! ID: {invoice_id}'}
                        latest_result = enhanced_data
                        claude_response = json.dumps(extracted_data, indent=2)

                    # Cleanup
                    file_path.unlink(missing_ok=True)

                except Exception as e:
                    status = {'type': 'error', 'message': f'Processing error: {str(e)}'}

    # Get recent invoices and stats
    conn = sqlite3.connect(DB_PATH)
    recent_invoices = conn.execute("SELECT * FROM invoices ORDER BY created_at DESC LIMIT 5").fetchall()
    total_count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    conn.close()

    return render_template_string(UPLOAD_TEMPLATE,
                                 status=status,
                                 recent_invoices=recent_invoices,
                                 total_invoices=total_count,
                                 latest_result=latest_result,
                                 claude_response=claude_response)

def enhance_with_business_intelligence(extracted_data):
    """Enhance extracted data with Delta business intelligence"""
    # Simple business unit classification
    vendor_name = extracted_data.get('vendor_name', '').lower()

    # Override business unit based on vendor analysis
    if any(tech in vendor_name for tech in ['aws', 'amazon', 'google', 'microsoft']):
        extracted_data['business_unit'] = 'Delta LLC'
        extracted_data['category'] = 'Technology Expenses'
    elif 'coinbase' in vendor_name or 'crypto' in vendor_name:
        extracted_data['business_unit'] = 'Delta Prop Shop LLC'
        extracted_data['category'] = 'Trading Expenses'

    # Add currency type detection
    extracted_data['currency_type'] = 'cryptocurrency' if 'crypto' in vendor_name else 'fiat'

    # Add enhanced confidence
    base_confidence = extracted_data.get('confidence', 0.8)
    bu_bonus = 0.1 if extracted_data['business_unit'] != 'Delta LLC' else 0
    extracted_data['confidence_score'] = min(base_confidence + bu_bonus, 1.0)

    # Add timestamps
    extracted_data['created_at'] = datetime.now().isoformat()
    extracted_data['id'] = str(uuid.uuid4())[:8]

    return extracted_data

def save_invoice_to_db(invoice_data):
    """Save invoice to database"""
    conn = sqlite3.connect(DB_PATH)

    conn.execute('''
        INSERT INTO invoices (
            id, invoice_number, date, vendor_name, total_amount, currency,
            business_unit, category, confidence_score, processing_notes,
            source_file, processed_at, created_at, extraction_method
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        invoice_data['id'],
        invoice_data.get('invoice_number'),
        invoice_data.get('date'),
        invoice_data.get('vendor_name'),
        invoice_data.get('total_amount'),
        invoice_data.get('currency'),
        invoice_data.get('business_unit'),
        invoice_data.get('category'),
        invoice_data.get('confidence_score'),
        invoice_data.get('processing_notes'),
        invoice_data.get('source_file'),
        invoice_data.get('processed_at'),
        invoice_data.get('created_at'),
        invoice_data.get('extraction_method')
    ))

    conn.commit()
    conn.close()

    return invoice_data['id']

@app.route('/api/stats')
def api_stats():
    """API endpoint for processing statistics"""
    conn = sqlite3.connect(DB_PATH)

    stats = {
        'total_invoices': conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0],
        'avg_confidence': conn.execute("SELECT AVG(confidence_score) FROM invoices").fetchone()[0] or 0,
        'business_units': {}
    }

    # Business unit breakdown
    bu_data = conn.execute("SELECT business_unit, COUNT(*), SUM(total_amount) FROM invoices GROUP BY business_unit").fetchall()
    for bu, count, total in bu_data:
        stats['business_units'][bu] = {'count': count, 'total_amount': total}

    conn.close()
    return jsonify(stats)

if __name__ == '__main__':
    init_db()
    print("Full Pipeline Test starting...")
    print("   Features: Claude Vision + Business Intelligence + Database")
    print("   Access: http://localhost:5004")
    print("   API Stats: http://localhost:5004/api/stats")

    app.run(host='0.0.0.0', port=5004, debug=True, use_reloader=False)