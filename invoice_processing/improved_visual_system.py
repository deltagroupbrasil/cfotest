#!/usr/bin/env python3
"""
Advanced Multi-Upload System
Sistema avançado de upload múltiplo com suporte a diversos tipos de arquivo
"""

import os
import sys
import sqlite3
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, send_from_directory, redirect, url_for
from datetime import datetime
import uuid
import json
import anthropic
import base64
import pandas as pd
import zipfile
import tempfile
import shutil
import concurrent.futures
from threading import Lock
from PIL import Image
import io
# Using Claude Vision only for simplicity
OPENAI_AVAILABLE = False
print("Sistema simplificado: apenas Claude Vision ativado.")

# Configuração
CLAUDE_API_KEY = os.getenv('ANTHROPIC_API_KEY') or input("Cole sua API key da Anthropic: ")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') if OPENAI_AVAILABLE else None

app = Flask(__name__)
app.secret_key = 'advanced_upload_secret'

# Database setup
DB_PATH = Path(__file__).parent / "advanced_invoices.db"
UPLOAD_DIR = Path(__file__).parent / "uploaded_files"
UPLOAD_DIR.mkdir(exist_ok=True)

def init_db():
    """Initialize advanced database with file storage"""
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
            file_path TEXT,
            file_type TEXT,
            file_size INTEGER,
            processed_at TEXT,
            created_at TEXT,
            extraction_method TEXT,
            raw_claude_response TEXT
        )
    ''')

    # Batch processing table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS batch_uploads (
            id TEXT PRIMARY KEY,
            total_files INTEGER,
            processed_files INTEGER,
            failed_files INTEGER,
            status TEXT,
            created_at TEXT,
            completed_at TEXT
        )
    ''')

    conn.commit()
    conn.close()

class AdvancedFileProcessor:
    """Advanced file processor supporting multiple formats"""

    def __init__(self, api_key):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.openai_client = None  # Simplified - Claude only
        self.supported_types = {
            # Documents
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            # Images
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            # Spreadsheets
            '.csv': 'text/csv',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            # Other formats
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.rtf': 'application/rtf',
            # Archives
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed'
        }

        # File types that can be processed directly
        self.processable_types = {'.pdf', '.txt', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.csv', '.xls', '.xlsx', '.docx', '.rtf'}
        # Archive types that need extraction
        self.archive_types = {'.zip', '.rar'}

    def is_supported_file(self, filename):
        """Check if file type is supported"""
        ext = Path(filename).suffix.lower()
        return ext in self.supported_types

    def extract_invoice_data(self, file_path):
        """Extract data from various file formats"""
        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext in self.archive_types:
                return self._process_archive(file_path)
            elif file_ext == '.pdf':
                return self._process_pdf(file_path)
            elif file_ext == '.csv':
                return self._process_csv(file_path)
            elif file_ext in ['.xls', '.xlsx']:
                return self._process_excel(file_path)
            elif file_ext == '.txt':
                return self._process_text(file_path)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
                return self._process_image(file_path)
            else:
                return {'status': 'error', 'error': f'Unsupported file type: {file_ext}'}

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _process_archive(self, archive_path):
        """Process archive files (ZIP/RAR) and extract contents"""
        try:
            results = []
            extracted_files = []

            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract archive
                if archive_path.lower().endswith('.zip'):
                    extracted_files = self._extract_zip(archive_path, temp_path)
                elif archive_path.lower().endswith('.rar'):
                    extracted_files = self._extract_rar(archive_path, temp_path)

                if not extracted_files:
                    return {'status': 'error', 'error': 'No supported files found in archive'}

                # Process each extracted file
                for file_path in extracted_files:
                    try:
                        file_result = self._process_single_file(file_path)
                        if file_result.get('status') == 'success':
                            file_result['archive_source'] = os.path.basename(archive_path)
                            file_result['original_filename'] = file_path.name
                            results.append(file_result)
                    except Exception as e:
                        print(f"Error processing {file_path.name}: {e}")
                        continue

            if not results:
                return {'status': 'error', 'error': 'No files could be processed from archive'}

            # Return combined results
            return {
                'status': 'success',
                'archive_processed': True,
                'total_files': len(results),
                'results': results,
                'source_file': os.path.basename(archive_path)
            }

        except Exception as e:
            return {'status': 'error', 'error': f'Archive processing failed: {str(e)}'}

    def _extract_zip(self, zip_path, extract_dir):
        """Extract ZIP file and return list of processable files"""
        extracted_files = []
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

                for file_info in zip_ref.filelist:
                    if not file_info.is_dir():
                        file_path = extract_dir / file_info.filename
                        if file_path.exists() and file_path.suffix.lower() in self.processable_types:
                            extracted_files.append(file_path)

        except Exception as e:
            print(f"ZIP extraction error: {e}")

        return extracted_files

    def _extract_rar(self, rar_path, extract_dir):
        """Extract RAR file and return list of processable files"""
        extracted_files = []
        try:
            # Try to use rarfile if available
            import rarfile
            with rarfile.RarFile(rar_path, 'r') as rar_ref:
                rar_ref.extractall(extract_dir)

                for file_info in rar_ref.infolist():
                    if not file_info.is_dir():
                        file_path = extract_dir / file_info.filename
                        if file_path.exists() and file_path.suffix.lower() in self.processable_types:
                            extracted_files.append(file_path)

        except ImportError:
            return []  # RAR support not available
        except Exception as e:
            print(f"RAR extraction error: {e}")

        return extracted_files

    def _process_single_file(self, file_path):
        """Process a single file (used internally for archive contents)"""
        file_ext = Path(file_path).suffix.lower()

        if file_ext == '.pdf':
            return self._process_pdf(file_path)
        elif file_ext == '.csv':
            return self._process_csv(file_path)
        elif file_ext in ['.xls', '.xlsx']:
            return self._process_excel(file_path)
        elif file_ext == '.txt':
            return self._process_text(file_path)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
            return self._process_image(file_path)
        else:
            return {'status': 'error', 'error': f'Unsupported file type: {file_ext}'}

    def _process_pdf(self, file_path):
        """Process PDF files"""
        try:
            import fitz
            doc = fitz.open(file_path)
            if doc.page_count == 0:
                raise ValueError("PDF has no pages")

            # Convert first page to image
            page = doc.load_page(0)
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            image_bytes = pix.pil_tobytes(format="PNG")
            doc.close()

            # Also extract text for hybrid processing
            doc = fitz.open(file_path)
            text_content = ""
            for page in doc:
                text_content += page.get_text()
            doc.close()

            # Use Claude Vision with both image and text
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            return self._call_claude_vision(image_base64, file_path, text_content)

        except Exception as e:
            return {'status': 'error', 'error': f'PDF processing failed: {e}'}

    def _process_csv(self, file_path):
        """Process CSV files"""
        try:
            df = pd.read_csv(file_path)

            # Convert DataFrame to readable text for Claude
            csv_content = f"CSV Data from {os.path.basename(file_path)}:\n\n"
            csv_content += f"Columns: {', '.join(df.columns.tolist())}\n\n"
            csv_content += df.to_string(max_rows=20)  # Limit to first 20 rows

            return self._call_claude_text_analysis(csv_content, file_path)

        except Exception as e:
            return {'status': 'error', 'error': f'CSV processing failed: {e}'}

    def _process_excel(self, file_path):
        """Process Excel files"""
        try:
            # Try to read Excel file
            df = pd.read_excel(file_path, sheet_name=0)  # Read first sheet

            excel_content = f"Excel Data from {os.path.basename(file_path)}:\n\n"
            excel_content += f"Columns: {', '.join(df.columns.tolist())}\n\n"
            excel_content += df.to_string(max_rows=20)

            return self._call_claude_text_analysis(excel_content, file_path)

        except Exception as e:
            return {'status': 'error', 'error': f'Excel processing failed: {e}'}

    def _process_text(self, file_path):
        """Process text files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self._call_claude_text_analysis(content, file_path)
        except Exception as e:
            return {'status': 'error', 'error': f'Text processing failed: {e}'}

    def _optimize_image_for_api(self, file_path, max_size_mb=5):
        """Optimize image for Claude API - resize if too large"""
        try:
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
            print(f"Original image size: {file_size:.2f}MB")

            if file_size <= max_size_mb:
                # File is already small enough, read normally
                with open(file_path, 'rb') as f:
                    return f.read()

            print(f"Image too large ({file_size:.2f}MB), optimizing...")

            # Open and optimize the image
            with Image.open(file_path) as img:
                # Convert to RGB if needed (removes transparency)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Convert to RGB to remove transparency
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGB')
                    else:
                        rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = rgb_img

                # Calculate new dimensions maintaining aspect ratio
                original_width, original_height = img.size
                max_dimension = 2048  # Maximum dimension for Claude Vision

                if original_width > max_dimension or original_height > max_dimension:
                    if original_width > original_height:
                        new_width = max_dimension
                        new_height = int((original_height * max_dimension) / original_width)
                    else:
                        new_height = max_dimension
                        new_width = int((original_width * max_dimension) / original_height)

                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    print(f"Resized from {original_width}x{original_height} to {new_width}x{new_height}")

                # Save to bytes with optimized quality
                output_buffer = io.BytesIO()
                img.save(output_buffer, format='JPEG', quality=85, optimize=True)
                optimized_bytes = output_buffer.getvalue()

                new_size = len(optimized_bytes) / (1024 * 1024)
                print(f"Optimized image size: {new_size:.2f}MB")

                return optimized_bytes

        except Exception as e:
            print(f"Image optimization failed: {e}, using original file")
            # Fall back to original file
            with open(file_path, 'rb') as f:
                return f.read()

    def _process_image(self, file_path):
        """Process image files with Claude Vision only"""
        try:
            # Optimize image before sending to API
            image_bytes = self._optimize_image_for_api(file_path)
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # Single validation with Claude Vision (simplified)
            print(f"🤖 Processando com Claude Vision: {file_path}")
            result = self._call_claude_vision(image_base64, file_path)
            if result['status'] == 'error':
                print(f"❌ Erro no processamento: {result['error']}")
                return result

            print(f"✅ Processamento concluído com sucesso para {file_path}")
            final_result = result
            final_result['validation_notes'] = "Single Claude Vision validation"
            return final_result

        except Exception as e:
            return {'status': 'error', 'error': f'Image processing failed: {e}'}


    def _call_claude_vision(self, image_base64, file_path, text_content=None):
        """Call Claude Vision API"""
        try:
            prompt = f"""
🌐 MULTILINGUAL INVOICE ANALYZER - Extract invoice data accurately from Spanish/Portuguese/English documents.

⚠️ CRITICAL: DO NOT confuse vendor/supplier with client/customer!
- VENDOR/SUPPLIER = Who is billing (the company sending the invoice)
- CLIENT/CUSTOMER = Who is receiving the invoice (often Delta entities)

File: {os.path.basename(file_path)}
{f"Text content available: {text_content[:500]}..." if text_content else ""}

LANGUAGE SUPPORT:
- 🇪🇸 Spanish: "Factura", "Proveedor", "Cliente", "Total", "Fecha"
- 🇵🇹 Portuguese: "Nota Fiscal", "Fornecedor", "Cliente", "Total", "Data"
- 🇺🇸 English: "Invoice", "Vendor", "Client", "Total", "Date"

EXTRACT WITH PRECISION:

REQUIRED FIELDS:
- invoice_number: Invoice/factura/nota fiscal number (exact from document)
- date: Invoice date in YYYY-MM-DD format
- vendor_name: EXACT company name that is BILLING/PROVIDING service (NOT the client!)
- total_amount: Final total amount (numeric only, no symbols)
- currency: Currency code (USD, BRL, PYG, EUR, ARS, etc.)

CLASSIFICATION:
- business_unit: Match the RECEIVING entity ["Delta LLC", "Delta Prop Shop LLC", "Delta Mining Paraguay S.A.", "Delta Brazil", "Personal"]
- category: ["Technology Expenses", "Trading Expenses", "Utilities", "Professional Services", "Consulting", "Marketing", "Legal", "Other"]

Return ONLY JSON:
{{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "vendor_name": "EXACT_VENDOR_NAME_FROM_DOCUMENT",
    "total_amount": 1234.56,
    "currency": "USD",
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Language: Spanish/Portuguese/English, Vendor confusion avoided"
}}
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
                    ] if image_base64 else [{"type": "text", "text": prompt}]
                }]
            )

            response_text = response.content[0].text.strip()
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            extracted_data = json.loads(response_text)
            return self._format_response(extracted_data, file_path)

        except Exception as e:
            return {'status': 'error', 'error': f'Claude Vision API error: {e}'}


    def _call_claude_text_analysis(self, content, file_path):
        """Call Claude for text analysis"""
        try:
            prompt = f"""
Analyze this financial data and extract invoice information in JSON format:

{content[:2000]}...

Extract invoice fields if this appears to be financial/invoice data. If not clearly an invoice, classify as best as possible.

Return ONLY JSON:
{{
    "invoice_number": "string or null",
    "date": "YYYY-MM-DD or null",
    "vendor_name": "string",
    "total_amount": 1234.56,
    "currency": "USD",
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Analysis details"
}}
"""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text.strip()
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            extracted_data = json.loads(response_text)
            return self._format_response(extracted_data, file_path)

        except Exception as e:
            return {'status': 'error', 'error': f'Claude text analysis error: {e}'}

    def _format_response(self, extracted_data, file_path):
        """Format and validate response"""
        extracted_data.update({
            'source_file': os.path.basename(file_path),
            'extraction_method': 'claude_advanced',
            'processed_at': datetime.now().isoformat(),
            'status': 'success'
        })
        return extracted_data

# Initialize processor
processor = AdvancedFileProcessor(CLAUDE_API_KEY)

# Thread lock for database operations
db_lock = Lock()

# Enhanced HTML Template
ADVANCED_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Delta CFO Agent - Advanced Upload System</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 20px auto; padding: 20px; background: #f8f9fa; }
        .container { display: flex; flex-direction: column; gap: 30px; }
        .upload-section, .results-section { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .multi-upload-area { border: 3px dashed #007bff; padding: 40px; text-align: center; border-radius: 12px; margin: 20px 0; transition: all 0.3s; }
        .multi-upload-area:hover { border-color: #0056b3; background: #f8f9ff; }
        .multi-upload-area.drag-over { border-color: #28a745; background: #f8fff8; }
        .btn { background: linear-gradient(135deg, #007bff, #0056b3); color: white; padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.3s; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,123,255,0.3); }
        .file-list { margin: 20px 0; min-height: 40px; border: 1px solid #e9ecef; border-radius: 8px; padding: 10px; background-color: #fafafa; }
        .file-item { background: #f8f9fa; padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 4px solid #007bff; }
        .processing { background: #fff3cd; border-left-color: #ffc107; }
        .success { background: #d4edda; border-left-color: #28a745; }
        .error { background: #f8d7da; border-left-color: #dc3545; }
        .supported-types { background: #e7f3ff; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .invoice-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        .invoice-table th, .invoice-table td { padding: 12px; text-align: left; border-bottom: 1px solid #e9ecef; }
        .invoice-table th { background: #f8f9fa; font-weight: 600; color: #495057; }
        .invoice-table tr:hover { background: #f8f9fa; cursor: pointer; }
        .invoice-row { transition: background-color 0.2s ease; }
        .progress-bar { width: 100%; height: 8px; background: #e9ecef; border-radius: 4px; margin: 10px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #007bff, #28a745); transition: width 0.3s; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat { background: white; padding: 15px; text-align: center; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 24px; font-weight: bold; color: #007bff; }
        .stat-label { font-size: 12px; color: #6c757d; margin-top: 5px; }
        .filters-section { background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #e9ecef; }
        .enhanced-card { transition: transform 0.2s ease, box-shadow 0.2s ease; }
        .enhanced-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .invoice-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .bu-tag { padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: bold; text-transform: uppercase; }
        .bu-delta-prop { background: #e3f2fd; color: #1976d2; }
        .bu-delta-mining { background: #fff3e0; color: #f57c00; }
        .bu-delta-land { background: #e8f5e8; color: #388e3c; }
        .bu-delta-agro { background: #f3e5f5; color: #7b1fa2; }
        .bu-other { background: #fafafa; color: #616161; }
        .confidence-badge { background: #e8f5e8; color: #2e7d32; padding: 2px 6px; border-radius: 8px; font-size: 11px; font-weight: bold; }
        .action-btn:hover { transform: translateY(-1px) !important; }
    </style>
</head>
<body>
    <h1>Delta CFO Agent - Advanced Upload System</h1>
    <p>Sistema avançado de upload múltiplo com suporte a diversos tipos de arquivo</p>

    <div class="container">
        <div class="upload-section">
            <h2>Multi-File Upload</h2>

            {% if batch_status %}
                <div class="file-item {{ batch_status.type }}">
                    {{ batch_status.message }}
                    {% if batch_status.progress %}
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {{ batch_status.progress }}%"></div>
                        </div>
                        <small>{{ batch_status.progress }}% completo</small>
                    {% endif %}
                </div>
            {% endif %}

            <form method="POST" enctype="multipart/form-data" id="uploadForm">
                <div class="multi-upload-area" id="dropArea">
                    <h3>📁 Arraste arquivos aqui ou clique para selecionar</h3>
                    <input type="file" name="files" id="files" multiple
                           accept=".pdf,.txt,.png,.jpg,.jpeg,.csv,.xls,.xlsx,.gif,.bmp,.tiff,.docx,.rtf,.zip,.rar" style="display: none;">
                    <p>Suporte a múltiplos arquivos simultâneos</p>
                </div>

                <div class="file-list" id="fileList"></div>

                <button type="submit" class="btn" id="uploadBtn" disabled>
                    🚀 Processar Arquivos Selecionados
                </button>
            </form>

            <div class="supported-types">
                <h4>📋 Tipos de Arquivo Suportados:</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                    <div><strong>Documentos:</strong> PDF, TXT, DOCX, RTF</div>
                    <div><strong>Planilhas:</strong> CSV, XLS, XLSX</div>
                    <div><strong>Imagens:</strong> PNG, JPG, GIF, BMP, TIFF</div>
                    <div><strong>📦 Arquivos Comprimidos:</strong> ZIP, RAR</div>
                </div>
                <p style="font-size: 12px; color: #666; margin-top: 10px;">
                    💡 <strong>Novo:</strong> Arquivos ZIP/RAR são automaticamente extraídos e todos os arquivos compatíveis dentro deles são processados!
                </p>
            </div>

            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{{ total_processed }}</div>
                    <div class="stat-label">Total Processado</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ success_rate }}%</div>
                    <div class="stat-label">Taxa de Sucesso</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ supported_types_count }}</div>
                    <div class="stat-label">Tipos Suportados</div>
                </div>
            </div>
        </div>

        <div class="results-section">
            <h2>Lista de Invoices</h2>

            <!-- Filtros -->
            <div class="filters-section">
                <div class="filter-group">
                    <input type="text" id="searchInput" placeholder="🔍 Buscar por número, fornecedor..." style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 10px;">
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 15px;">
                    <div style="display: flex; flex-direction: column; gap: 3px;">
                        <label style="font-size: 11px; color: #666; font-weight: bold;">🏢 Business Unit</label>
                        <select id="businessUnitFilter" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            <option value="">Todas as Units</option>
                        </select>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 3px;">
                        <label style="font-size: 11px; color: #666; font-weight: bold;">📂 Categoria</label>
                        <select id="categoryFilter" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            <option value="">Todas as Categorias</option>
                        </select>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 3px;">
                        <label style="font-size: 11px; color: #666; font-weight: bold;">📄 Itens por página</label>
                        <select id="itemsPerPage" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            <option value="50">50</option>
                            <option value="100">100</option>
                            <option value="200">200</option>
                        </select>
                    </div>
                </div>

                <!-- Bulk Actions -->
                <div id="bulkActions" style="display: none; margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 4px; border: 1px solid #dee2e6;">
                    <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                        <span id="selectedCount" style="font-weight: bold; color: #007bff;">0 selecionados</span>
                        <button onclick="bulkDownload()" style="padding: 8px 15px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">
                            📥 Download Selecionados
                        </button>
                        <button onclick="bulkDelete()" style="padding: 8px 15px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">
                            🗑️ Deletar Selecionados
                        </button>
                        <button onclick="clearSelection()" style="padding: 8px 15px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">
                            ✖️ Limpar Seleção
                        </button>
                    </div>
                </div>
                <button onclick="clearFilters()" style="background: #6c757d; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">Limpar Filtros</button>
            </div>

            <div id="invoiceContainer">
                <table class="invoice-table">
                    <thead>
                        <tr>
                            <th style="width: 40px;">
                                <input type="checkbox" id="selectAll" onchange="toggleSelectAll()" style="cursor: pointer;">
                            </th>
                            <th>Invoice #</th>
                            <th>Fornecedor</th>
                            <th>Valor</th>
                            <th>Business Unit</th>
                            <th>Data</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody id="invoiceTableBody">
                        {% for invoice in recent_invoices %}
                        <tr class="invoice-row"
                            data-vendor="{{ invoice[3] | lower }}"
                            data-bu="{{ invoice[7] | lower }}"
                            data-category="{{ invoice[8] | lower }}"
                            data-invoice-number="{{ invoice[1] | lower }}"
                            data-invoice-id="{{ invoice[0] }}">
                            <td style="text-align: center;">
                                <input type="checkbox" class="invoice-checkbox" value="{{ invoice[0] }}" onchange="updateBulkActions()" style="cursor: pointer;">
                            </td>
                            <td><strong style="color: #007bff;">{{ invoice[1] or 'N/A' }}</strong></td>
                            <td>{{ invoice[3] or 'Não identificado' }}</td>
                            <td><strong style="color: #28a745;">{{ "%.2f" | format(invoice[5] or 0) }} {{ invoice[6] or 'USD' }}</strong></td>
                            <td><span class="bu-tag bu-{{ (invoice[7] or 'Other') | lower | replace(' ', '-') }}">{{ invoice[7] or 'Other' }}</span></td>
                            <td style="color: #6c757d; font-size: 13px;">{{ invoice[2] or 'N/A' }}</td>
                            <td class="action-cell">
                                <div class="action-buttons">
                                    <button onclick="openDetailsModal('{{ invoice[0] }}')" class="btn-icon btn-details" title="Ver Detalhes">
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
                                        </svg>
                                    </button>
                                    <a href="/file/{{ invoice[0] }}" class="btn-icon btn-download" title="Download">
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
                                        </svg>
                                    </a>
                                    <button onclick="openEditModal('{{ invoice[0] }}')" class="btn-icon btn-edit" title="Editar">
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                                        </svg>
                                    </button>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>

                <div id="noResults" style="display: none; text-align: center; padding: 40px; color: #6c757d;">
                    <h4>Nenhum invoice encontrado</h4>
                    <p>Ajuste os filtros ou faça upload de novos documentos</p>
                </div>

                <!-- Paginação -->
                <div id="pagination" style="display: flex; justify-content: space-between; align-items: center; padding: 20px 0; border-top: 1px solid #e9ecef; margin-top: 20px;">
                    <div>
                        <span id="pageInfo">Mostrando 1-50 de 0 itens</span>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button id="prevPage" onclick="changePage(-1)" style="background: #007bff; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer;" disabled>
                            ← Anterior
                        </button>
                        <span id="currentPageDisplay">Página 1</span>
                        <button id="nextPage" onclick="changePage(1)" style="background: #007bff; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer;">
                            Próximo →
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal para edição de invoice -->
    <div id="editInvoiceModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeEditModal()">&times;</span>
            <h2>✏️ Editar Invoice</h2>
            <form id="editForm">
                <input type="hidden" id="editInvoiceId">

                <div class="form-group">
                    <label for="editInvoiceNumber">Número do Invoice:</label>
                    <input type="text" id="editInvoiceNumber" required>
                </div>

                <div class="form-group">
                    <label for="editVendorName">Fornecedor:</label>
                    <input type="text" id="editVendorName" required>
                </div>

                <div class="form-group">
                    <label for="editAmount">Valor:</label>
                    <input type="number" id="editAmount" step="0.01" required>
                </div>

                <div class="form-group">
                    <label for="editCurrency">Moeda:</label>
                    <select id="editCurrency" required>
                        <option value="USD">USD</option>
                        <option value="EUR">EUR</option>
                        <option value="PYG">PYG</option>
                        <option value="BRL">BRL</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="editBusinessUnit">Business Unit:</label>
                    <select id="editBusinessUnit" required>
                        <option value="Delta LLC">Delta LLC</option>
                        <option value="Delta Prop Shop LLC">Delta Prop Shop LLC</option>
                        <option value="Infinity Validator">Infinity Validator</option>
                        <option value="Delta Mining Paraguay S.A.">Delta Mining Paraguay S.A.</option>
                        <option value="Personal">Personal</option>
                        <option value="Other">Other</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="editCategory">Categoria:</label>
                    <select id="editCategory" required>
                        <option value="Technology Expenses">Technology Expenses</option>
                        <option value="Trading">Trading</option>
                        <option value="Mining">Mining</option>
                        <option value="Services">Services</option>
                        <option value="Other">Other</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="editDate">Data:</label>
                    <input type="date" id="editDate" required>
                </div>

                <div style="text-align: right; margin-top: 20px;">
                    <button type="button" onclick="closeEditModal()" class="btn" style="background: #6c757d; margin-right: 10px;">
                        Cancelar
                    </button>
                    <button type="submit" class="btn" style="background: #28a745;">
                        💾 Salvar Alterações
                    </button>
                </div>
            </form>
        </div>
    </div>

    <!-- Invoice Details Modal -->
    <div id="detailsModal" class="modal">
        <div class="modal-content" style="max-width: 800px; max-height: 90vh; overflow-y: auto;">
            <span class="close" onclick="closeDetailsModal()">&times;</span>
            <h2>👁️ Detalhes do Invoice</h2>

            <div class="details-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                <!-- Left Column -->
                <div class="details-column">
                    <div class="detail-item">
                        <label>Número do Invoice:</label>
                        <div id="detailInvoiceNumber" class="detail-value">-</div>
                    </div>

                    <div class="detail-item">
                        <label>Fornecedor:</label>
                        <div id="detailVendorName" class="detail-value">-</div>
                    </div>

                    <div class="detail-item">
                        <label>Valor Total:</label>
                        <div id="detailAmount" class="detail-value" style="color: #28a745; font-weight: bold; font-size: 18px;">-</div>
                    </div>

                    <div class="detail-item">
                        <label>Moeda:</label>
                        <div id="detailCurrency" class="detail-value">-</div>
                    </div>

                    <div class="detail-item">
                        <label>Data:</label>
                        <div id="detailDate" class="detail-value">-</div>
                    </div>
                </div>

                <!-- Right Column -->
                <div class="details-column">
                    <div class="detail-item">
                        <label>Business Unit:</label>
                        <div id="detailBusinessUnit" class="detail-value">
                            <span id="detailBusinessUnitTag" class="bu-tag">-</span>
                        </div>
                    </div>

                    <div class="detail-item">
                        <label>Categoria:</label>
                        <div id="detailCategory" class="detail-value">-</div>
                    </div>

                    <div class="detail-item">
                        <label>Confiança:</label>
                        <div id="detailConfidence" class="detail-value">-</div>
                    </div>

                    <div class="detail-item">
                        <label>Método de Extração:</label>
                        <div id="detailExtractionMethod" class="detail-value">-</div>
                    </div>

                    <div class="detail-item">
                        <label>Processado em:</label>
                        <div id="detailProcessedAt" class="detail-value">-</div>
                    </div>
                </div>
            </div>

            <!-- Processing Notes -->
            <div class="detail-item" style="margin-top: 20px;">
                <label>Notas de Processamento:</label>
                <div id="detailProcessingNotes" class="detail-value" style="background: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 4px solid #007bff;">-</div>
            </div>

            <!-- File Info -->
            <div class="detail-item" style="margin-top: 15px;">
                <label>Arquivo Fonte:</label>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div id="detailSourceFile" class="detail-value">-</div>
                    <a id="detailDownloadLink" href="#" class="btn" style="padding: 5px 10px; font-size: 12px; background: #28a745; color: white; text-decoration: none;">
                        📥 Download
                    </a>
                </div>
            </div>

            <!-- Action Buttons -->
            <div style="text-align: right; margin-top: 30px; border-top: 1px solid #dee2e6; padding-top: 20px;">
                <button type="button" onclick="closeDetailsModal()" class="btn" style="background: #6c757d; margin-right: 10px;">
                    Fechar
                </button>
                <button type="button" onclick="editFromDetails()" class="btn" style="background: #ffc107; color: #000;">
                    ✏️ Editar Invoice
                </button>
            </div>
        </div>
    </div>

    <style>
        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }

        .modal-content {
            background-color: #fefefe;
            margin: 5% auto;
            padding: 20px;
            border: none;
            border-radius: 8px;
            width: 80%;
            max-width: 600px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }

        .close:hover {
            color: black;
        }

        .form-group {
            margin-bottom: 15px;
        }

        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }

        .form-group input, .form-group select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }

        /* Details Modal Specific Styles */
        .detail-item {
            margin-bottom: 15px;
        }

        .detail-item label {
            display: block;
            font-weight: 600;
            color: #495057;
            margin-bottom: 5px;
            font-size: 14px;
        }

        .detail-value {
            background: #ffffff;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 10px;
            min-height: 20px;
            font-size: 14px;
            line-height: 1.4;
        }

        .details-grid {
            margin-top: 20px;
        }

        @media (max-width: 768px) {
            .details-grid {
                grid-template-columns: 1fr;
                gap: 10px;
            }
        }
    </style>

    <script>
        const dropArea = document.getElementById('dropArea');
        const fileInput = document.getElementById('files');
        const fileList = document.getElementById('fileList');
        const uploadBtn = document.getElementById('uploadBtn');
        let selectedFiles = [];

        // Pagination variables
        let currentPage = 1;
        let itemsPerPage = 50;
        let allRows = [];
        let filteredRows = [];

        // Drag and drop functionality
        dropArea.addEventListener('click', () => fileInput.click());

        dropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropArea.classList.add('drag-over');
        });

        dropArea.addEventListener('dragleave', () => {
            dropArea.classList.remove('drag-over');
        });

        dropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            dropArea.classList.remove('drag-over');
            handleFiles(e.dataTransfer.files);
        });

        fileInput.addEventListener('change', (e) => {
            console.log('=== FILE INPUT CHANGE EVENT ===');
            console.log('Files selected via input:', e.target.files.length);
            console.log('File details:', Array.from(e.target.files).map(f => ({name: f.name, size: f.size})));
            handleFiles(e.target.files);
        });

        function handleFiles(files) {
            selectedFiles = Array.from(files);
            displayFileList();
            if (uploadBtn) {
                uploadBtn.disabled = selectedFiles.length === 0;
            }
            console.log('Files handled:', selectedFiles.length, 'files selected');
        }

        function displayFileList() {
            console.log('=== DISPLAYING FILE LIST ===');
            console.log('fileList element:', fileList);
            console.log('selectedFiles:', selectedFiles);
            console.log('selectedFiles.length:', selectedFiles.length);

            if (!fileList) {
                console.error('ERROR: fileList element not found!');
                return;
            }

            fileList.innerHTML = '';

            if (selectedFiles.length === 0) {
                console.log('No files to display, showing placeholder');
                const placeholder = document.createElement('div');
                placeholder.style.cssText = 'color: #6c757d; text-align: center; padding: 20px; font-style: italic;';
                placeholder.innerHTML = '📁 Nenhum arquivo selecionado ainda';
                fileList.appendChild(placeholder);
                return;
            }

            selectedFiles.forEach((file, index) => {
                console.log(`Adding file ${index + 1}:`, file.name, file.size);
                const div = document.createElement('div');
                div.className = 'file-item';
                div.style.cssText = 'padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; background: #f8f9fa;';
                div.innerHTML = `
                    <strong>${file.name}</strong>
                    <span style="color: #6c757d;">(${(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                    <button type="button" onclick="removeFile(${index})" style="float: right; background: #dc3545; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer;">×</button>
                `;
                fileList.appendChild(div);
                console.log('File div added to fileList');
            });

            console.log('File list display completed. Children count:', fileList.children.length);
        }

        function removeFile(index) {
            selectedFiles.splice(index, 1);
            displayFileList();
            if (uploadBtn) {
                uploadBtn.disabled = selectedFiles.length === 0;
            }

            // Update file input
            try {
                const dt = new DataTransfer();
                selectedFiles.forEach(file => dt.items.add(file));
                fileInput.files = dt.files;
            } catch (error) {
                console.warn('Error updating file input:', error);
            }
        }

        // Filter functionality
        const searchInput = document.getElementById('searchInput');
        const businessUnitFilter = document.getElementById('businessUnitFilter');
        const categoryFilter = document.getElementById('categoryFilter');
        const invoiceContainer = document.getElementById('invoiceContainer');
        const noResults = document.getElementById('noResults');

        function applyFilters() {
            const searchTerm = searchInput.value.toLowerCase();
            const selectedBU = businessUnitFilter.value.toLowerCase();
            const selectedCategory = categoryFilter.value.toLowerCase();

            if (!allRows.length) {
                allRows = Array.from(document.querySelectorAll('.invoice-row'));
            }

            // Filter rows based on search criteria
            filteredRows = allRows.filter(row => {
                const vendor = row.getAttribute('data-vendor');
                const bu = row.getAttribute('data-bu');
                const category = row.getAttribute('data-category');
                const invoiceNumber = row.getAttribute('data-invoice-number');

                const matchesSearch = !searchTerm ||
                    vendor.includes(searchTerm) ||
                    invoiceNumber.includes(searchTerm);

                const matchesBU = !selectedBU || bu.includes(selectedBU);
                const matchesCategory = !selectedCategory || category.includes(selectedCategory);

                return matchesSearch && matchesBU && matchesCategory;
            });

            // Reset to first page when filters change
            currentPage = 1;
            displayPage();
        }

        function clearFilters() {
            searchInput.value = '';
            businessUnitFilter.value = '';
            categoryFilter.value = '';
            applyFilters();
        }

        function displayPage() {
            // Hide all rows first
            allRows.forEach(row => row.style.display = 'none');

            // Calculate pagination
            const startIndex = (currentPage - 1) * itemsPerPage;
            const endIndex = startIndex + itemsPerPage;
            const pageRows = filteredRows.slice(startIndex, endIndex);

            // Show rows for current page
            pageRows.forEach(row => row.style.display = 'table-row');

            // Update pagination info
            updatePaginationInfo();

            // Show/hide no results
            const noResults = document.getElementById('noResults');
            noResults.style.display = filteredRows.length === 0 ? 'block' : 'none';
        }

        function updatePaginationInfo() {
            const totalItems = filteredRows.length;
            const startItem = totalItems > 0 ? (currentPage - 1) * itemsPerPage + 1 : 0;
            const endItem = Math.min(currentPage * itemsPerPage, totalItems);
            const totalPages = Math.ceil(totalItems / itemsPerPage);

            document.getElementById('pageInfo').textContent =
                `Mostrando ${startItem}-${endItem} de ${totalItems} itens`;
            document.getElementById('currentPageDisplay').textContent =
                `Página ${currentPage} de ${totalPages}`;

            // Update button states
            document.getElementById('prevPage').disabled = currentPage <= 1;
            document.getElementById('nextPage').disabled = currentPage >= totalPages;
        }

        function changePage(direction) {
            const totalPages = Math.ceil(filteredRows.length / itemsPerPage);
            const newPage = currentPage + direction;

            if (newPage >= 1 && newPage <= totalPages) {
                currentPage = newPage;
                displayPage();
            }
        }

        function changeItemsPerPage() {
            itemsPerPage = parseInt(document.getElementById('itemsPerPage').value);
            currentPage = 1;
            displayPage();
        }

        // Load dynamic filter options
        function loadFilterOptions() {
            fetch('/api/filter_options')
                .then(response => response.json())
                .then(data => {
                    // Populate Business Units dropdown
                    const buSelect = document.getElementById('businessUnitFilter');
                    buSelect.innerHTML = '<option value="">Todas</option>';
                    data.business_units.forEach(bu => {
                        const option = document.createElement('option');
                        option.value = bu;
                        option.textContent = bu;
                        buSelect.appendChild(option);
                    });

                    // Populate Categories dropdown
                    const categorySelect = document.getElementById('categoryFilter');
                    categorySelect.innerHTML = '<option value="">Todas</option>';
                    data.categories.forEach(category => {
                        const option = document.createElement('option');
                        option.value = category;
                        option.textContent = category;
                        categorySelect.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error('Error loading filter options:', error);
                });
        }


        // Add event listeners for filters and pagination
        searchInput.addEventListener('input', applyFilters);
        businessUnitFilter.addEventListener('change', applyFilters);
        categoryFilter.addEventListener('change', applyFilters);
        document.getElementById('itemsPerPage').addEventListener('change', changeItemsPerPage);

        // Function to check if files were selected (polling method)
        function checkForFiles() {
            if (fileInput && fileInput.files && fileInput.files.length > 0) {
                if (selectedFiles.length !== fileInput.files.length) {
                    console.log('=== FILES DETECTED VIA POLLING ===');
                    console.log('New files detected:', fileInput.files.length);
                    console.log('File details:', Array.from(fileInput.files).map(f => ({name: f.name, size: f.size})));
                    handleFiles(fileInput.files);
                }
            }
        }

        // Initialize pagination on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadFilterOptions();
            // Initialize file list placeholder
            displayFileList();

            // Start file detection polling
            console.log('=== PAGE LOADED ===');
            console.log('fileInput element:', fileInput);
            console.log('fileList element:', fileList);
            checkForFiles();
            setInterval(checkForFiles, 1000); // Check every second

            // Initialize pagination with all rows
            setTimeout(() => {
                allRows = Array.from(document.querySelectorAll('.invoice-row'));
                filteredRows = allRows.slice();
                displayPage();
            }, 100);

            // Add form submission handler for loading animation
            const uploadForm = document.getElementById('uploadForm');
            if (uploadForm) {
                uploadForm.addEventListener('submit', function(e) {
                    e.preventDefault(); // CRITICAL: Prevent page reload
                    console.log('=== AJAX FORM SUBMIT EVENT ===');
                    console.log('selectedFiles.length:', selectedFiles.length);

                    // Validate files are selected
                    if (selectedFiles.length === 0) {
                        e.preventDefault();
                        alert('Por favor selecione pelo menos um arquivo para fazer upload.');
                        console.log('Form blocked: No files selected');
                        return false;
                    }

                    // Get the file input element
                    const fileInput = document.getElementById('files');
                    console.log('File input found:', fileInput ? 'YES' : 'NO');
                    console.log('File input files count:', fileInput ? fileInput.files.length : 'N/A');

                    if (fileInput) {
                        // If fileInput has no files, try to synchronize
                        if (fileInput.files.length === 0 && selectedFiles.length > 0) {
                            console.log('Attempting to synchronize files...');
                            try {
                                // Try modern DataTransfer API first
                                if (typeof DataTransfer !== 'undefined') {
                                    const dataTransfer = new DataTransfer();
                                    selectedFiles.forEach(file => {
                                        dataTransfer.items.add(file);
                                    });
                                    fileInput.files = dataTransfer.files;
                                    console.log('Files synchronized with DataTransfer API:', fileInput.files.length, 'files');
                                } else {
                                    console.log('DataTransfer API not available');
                                }
                            } catch (error) {
                                console.warn('DataTransfer synchronization failed:', error);
                            }
                        }

                        // Final check - if still no files in input, block submit
                        if (fileInput.files.length === 0) {
                            e.preventDefault();
                            alert('Erro: Não foi possível sincronizar os arquivos. Tente novamente.');
                            console.log('Form blocked: File input still empty after sync attempt');
                            return false;
                        }

                        console.log('Form will submit with', fileInput.files.length, 'files');
                    } else {
                        e.preventDefault();
                        alert('Erro: Input de arquivo não encontrado.');
                        console.log('Form blocked: File input not found');
                        return false;
                    }

                    // Show loading state immediately
                    showUploadProgress();

                    // Create FormData from selected files
                    const formData = new FormData();
                    selectedFiles.forEach(file => {
                        formData.append('files', file);
                    });

                    console.log('Uploading files via AJAX (no page reload)...');

                    // Upload via AJAX to prevent page reload
                    fetch('/', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.text())
                    .then(html => {
                        console.log('✅ Upload completed successfully!');
                        console.log('Response length:', html.length);

                        // Update the entire page content without reload
                        document.open();
                        document.write(html);
                        document.close();

                        console.log('Page updated - no reload needed!');
                    })
                    .catch(error => {
                        console.error('❌ Upload error:', error);
                        alert('Erro no upload: ' + error.message + '. Tente novamente.');

                        // Reset interface on error
                        location.reload();
                    });
                });
            }
        });

        // Upload progress functions
        function showUploadProgress() {
            const uploadBtn = document.getElementById('uploadBtn');
            const dropArea = document.getElementById('dropArea');

            // Change button text and disable it
            uploadBtn.innerHTML = '⏳ Processando arquivos... Por favor aguarde';
            uploadBtn.disabled = true;

            // Add loading animation to drop area
            dropArea.innerHTML = `
                <h3>🚀 Processando ${selectedFiles.length} arquivos...</h3>
                <div class="loading-spinner">
                    <div class="progress-bar">
                        <div class="progress-fill loading-animation" style="width: 100%;"></div>
                    </div>
                </div>
                <p>Esta operação pode levar alguns minutos. Não recarregue a página.</p>
            `;

            // Add CSS for loading animation if not exists
            if (!document.getElementById('loadingStyles')) {
                const style = document.createElement('style');
                style.id = 'loadingStyles';
                style.textContent = `
                    .loading-animation {
                        background: linear-gradient(90deg, #007bff, #28a745, #17a2b8, #ffc107);
                        background-size: 200% 200%;
                        animation: loadingGradient 2s ease-in-out infinite;
                    }
                    @keyframes loadingGradient {
                        0% { background-position: 200% 0; }
                        100% { background-position: -200% 0; }
                    }
                    .loading-spinner {
                        margin: 20px 0;
                    }
                `;
                document.head.appendChild(style);
            }

            // Scroll to top so user can see the progress
            window.scrollTo(0, 0);
        }

        // Bulk selection functions
        function toggleSelectAll() {
            const selectAll = document.getElementById('selectAll');
            const checkboxes = document.querySelectorAll('.invoice-checkbox');

            checkboxes.forEach(checkbox => {
                checkbox.checked = selectAll.checked;
            });

            updateBulkActions();
        }

        function updateBulkActions() {
            const checkboxes = document.querySelectorAll('.invoice-checkbox');
            const checkedBoxes = document.querySelectorAll('.invoice-checkbox:checked');
            const bulkActions = document.getElementById('bulkActions');
            const selectedCount = document.getElementById('selectedCount');
            const selectAll = document.getElementById('selectAll');

            // Update count
            selectedCount.textContent = `${checkedBoxes.length} selecionados`;

            // Show/hide bulk actions
            if (checkedBoxes.length > 0) {
                bulkActions.style.display = 'flex';
            } else {
                bulkActions.style.display = 'none';
            }

            // Update select all checkbox state
            if (checkedBoxes.length === 0) {
                selectAll.checked = false;
                selectAll.indeterminate = false;
            } else if (checkedBoxes.length === checkboxes.length) {
                selectAll.checked = true;
                selectAll.indeterminate = false;
            } else {
                selectAll.checked = false;
                selectAll.indeterminate = true;
            }
        }

        function clearSelection() {
            const checkboxes = document.querySelectorAll('.invoice-checkbox');
            const selectAll = document.getElementById('selectAll');

            checkboxes.forEach(checkbox => {
                checkbox.checked = false;
            });
            selectAll.checked = false;

            updateBulkActions();
        }

        function getSelectedIds() {
            const checkedBoxes = document.querySelectorAll('.invoice-checkbox:checked');
            return Array.from(checkedBoxes).map(checkbox => checkbox.value);
        }

        function bulkDownload() {
            const selectedIds = getSelectedIds();

            if (selectedIds.length === 0) {
                alert('Nenhum invoice selecionado');
                return;
            }

            // Show loading
            const button = event.target;
            const originalText = button.textContent;
            button.textContent = '⏳ Preparando download...';
            button.disabled = true;

            fetch('/api/bulk_download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    invoice_ids: selectedIds
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erro no download');
                }
                return response.blob();
            })
            .then(blob => {
                // Create download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `invoices_bulk_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.zip`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                // Clear selection after successful download
                clearSelection();
                alert(`${selectedIds.length} arquivos baixados com sucesso!`);
            })
            .catch(error => {
                console.error('Erro:', error);
                alert('Erro ao baixar arquivos');
            })
            .finally(() => {
                button.textContent = originalText;
                button.disabled = false;
            });
        }

        function bulkDelete() {
            const selectedIds = getSelectedIds();

            if (selectedIds.length === 0) {
                alert('Nenhum invoice selecionado');
                return;
            }

            if (!confirm(`Tem certeza que deseja deletar ${selectedIds.length} invoices? Esta ação não pode ser desfeita.`)) {
                return;
            }

            // Show loading
            const button = event.target;
            const originalText = button.textContent;
            button.textContent = '⏳ Deletando...';
            button.disabled = true;

            fetch('/api/bulk_delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    invoice_ids: selectedIds
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Remove deleted rows from the table
                    selectedIds.forEach(id => {
                        const checkbox = document.querySelector(`.invoice-checkbox[value="${id}"]`);
                        if (checkbox) {
                            const row = checkbox.closest('tr');
                            row.remove();
                        }
                    });

                    // Update arrays
                    allRows = Array.from(document.querySelectorAll('.invoice-row'));
                    applyFilters(); // This will update filteredRows and display

                    alert(data.message);
                    clearSelection();
                } else {
                    alert('Erro ao deletar: ' + (data.error || 'Erro desconhecido'));
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                alert('Erro ao deletar invoices');
            })
            .finally(() => {
                button.textContent = originalText;
                button.disabled = false;
            });
        }

        // Table helper functions
        function showTableMessage(message, type) {
            const existingMessage = document.querySelector('.table-message');
            if (existingMessage) {
                existingMessage.remove();
            }

            const messageDiv = document.createElement('div');
            messageDiv.className = `table-message ${type === 'success' ? 'success-message' : 'error-message'}`;
            messageDiv.textContent = message;
            messageDiv.style.position = 'fixed';
            messageDiv.style.top = '20px';
            messageDiv.style.right = '20px';
            messageDiv.style.zIndex = '1000';
            messageDiv.style.padding = '10px 20px';
            messageDiv.style.borderRadius = '4px';
            messageDiv.style.backgroundColor = type === 'success' ? '#d4edda' : '#f8d7da';
            messageDiv.style.color = type === 'success' ? '#155724' : '#721c24';
            messageDiv.style.border = `1px solid ${type === 'success' ? '#c3e6cb' : '#f5c6cb'}`;

            document.body.appendChild(messageDiv);

            setTimeout(() => {
                messageDiv.remove();
            }, 3000);
        }

        // Edit Invoice Modal Functions
        function openEditModal(invoiceId) {
            editInvoice(invoiceId);
        }

        function editInvoice(invoiceId) {
            // Fetch current invoice data
            fetch(`/api/invoice/${invoiceId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Populate modal form
                        document.getElementById('editInvoiceId').value = invoiceId;
                        document.getElementById('editInvoiceNumber').value = data.data.invoice_number || '';
                        document.getElementById('editVendorName').value = data.data.vendor_name || '';
                        document.getElementById('editAmount').value = data.data.total_amount || '';
                        document.getElementById('editCurrency').value = data.data.currency || '';
                        document.getElementById('editBusinessUnit').value = data.data.business_unit || '';
                        document.getElementById('editCategory').value = data.data.category || '';
                        document.getElementById('editDate').value = data.data.date || '';

                        // Show modal
                        document.getElementById('editInvoiceModal').style.display = 'block';
                    } else {
                        alert('Erro ao carregar dados do invoice: ' + (data.error || 'Erro desconhecido'));
                    }
                })
                .catch(error => {
                    console.error('Erro:', error);
                    alert('Erro ao carregar dados do invoice');
                });
        }

        function closeEditModal() {
            document.getElementById('editInvoiceModal').style.display = 'none';
        }

        // Details Modal Functions
        let currentDetailsInvoiceId = null;

        function openDetailsModal(invoiceId) {
            currentDetailsInvoiceId = invoiceId;

            // Fetch invoice details
            fetch(`/api/invoice/${invoiceId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        populateDetailsModal(data.data);
                        document.getElementById('detailsModal').style.display = 'block';
                    } else {
                        alert('Erro ao carregar detalhes: ' + (data.error || 'Erro desconhecido'));
                    }
                })
                .catch(error => {
                    console.error('Erro:', error);
                    alert('Erro ao carregar detalhes do invoice');
                });
        }

        function populateDetailsModal(invoiceData) {
            // Basic information
            document.getElementById('detailInvoiceNumber').textContent = invoiceData.invoice_number || 'N/A';
            document.getElementById('detailVendorName').textContent = invoiceData.vendor_name || 'N/A';
            document.getElementById('detailAmount').textContent =
                `${parseFloat(invoiceData.total_amount || 0).toFixed(2)} ${invoiceData.currency || 'USD'}`;
            document.getElementById('detailCurrency').textContent = invoiceData.currency || 'USD';
            document.getElementById('detailDate').textContent = invoiceData.date || 'N/A';

            // Business unit with styling
            const businessUnit = invoiceData.business_unit || 'Other';
            const businessUnitTag = document.getElementById('detailBusinessUnitTag');
            businessUnitTag.textContent = businessUnit;
            businessUnitTag.className = `bu-tag bu-${businessUnit.toLowerCase().replace(/\\s+/g, '-')}`;

            // Additional details
            document.getElementById('detailCategory').textContent = invoiceData.category || 'N/A';
            document.getElementById('detailConfidence').textContent =
                invoiceData.confidence_score ? `${(invoiceData.confidence_score * 100).toFixed(1)}%` : 'N/A';
            document.getElementById('detailExtractionMethod').textContent =
                invoiceData.extraction_method || 'N/A';

            // Process dates
            const processedAt = invoiceData.processed_at || invoiceData.created_at;
            document.getElementById('detailProcessedAt').textContent =
                processedAt ? new Date(processedAt).toLocaleString() : 'N/A';

            // Processing notes
            document.getElementById('detailProcessingNotes').textContent =
                invoiceData.processing_notes || 'Nenhuma nota disponível';

            // File information
            document.getElementById('detailSourceFile').textContent =
                invoiceData.source_file || 'N/A';

            // Update download link
            const downloadLink = document.getElementById('detailDownloadLink');
            downloadLink.href = `/file/${currentDetailsInvoiceId}`;
        }

        function closeDetailsModal() {
            document.getElementById('detailsModal').style.display = 'none';
            currentDetailsInvoiceId = null;
        }

        function editFromDetails() {
            console.log('editFromDetails called, currentDetailsInvoiceId:', currentDetailsInvoiceId);
            const invoiceId = currentDetailsInvoiceId;
            closeDetailsModal();
            if (invoiceId) {
                console.log('Opening edit modal for invoice:', invoiceId);
                setTimeout(() => {
                    openEditModal(invoiceId);
                }, 100); // Small delay to ensure modal transition
            } else {
                console.error('No invoice ID available for editing');
            }
        }

        // Handle form submission
        document.addEventListener('DOMContentLoaded', function() {
            const editForm = document.getElementById('editForm');
            if (editForm) {
                editForm.addEventListener('submit', function(e) {
                    e.preventDefault();

                    const invoiceId = document.getElementById('editInvoiceId').value;
                    const formData = {
                        invoice_number: document.getElementById('editInvoiceNumber').value,
                        vendor_name: document.getElementById('editVendorName').value,
                        total_amount: parseFloat(document.getElementById('editAmount').value) || 0,
                        currency: document.getElementById('editCurrency').value,
                        business_unit: document.getElementById('editBusinessUnit').value,
                        category: document.getElementById('editCategory').value,
                        date: document.getElementById('editDate').value
                    };

                    // Show loading
                    const submitBtn = document.querySelector('#editForm button[type="submit"]');
                    const originalText = submitBtn.textContent;
                    submitBtn.textContent = '⏳ Salvando...';
                    submitBtn.disabled = true;

                    fetch(`/api/invoice/${invoiceId}/update`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(formData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('Invoice atualizado com sucesso!');
                            closeEditModal();

                            // Refresh the table row with updated data
                            location.reload(); // Simple solution - could be optimized to update just the row
                        } else {
                            alert('Erro ao atualizar invoice: ' + (data.error || 'Erro desconhecido'));
                        }
                    })
                    .catch(error => {
                        console.error('Erro:', error);
                        alert('Erro ao atualizar invoice');
                    })
                    .finally(() => {
                        submitBtn.textContent = originalText;
                        submitBtn.disabled = false;
                    });
                });
            }

            // Close modals when clicking outside
            window.onclick = function(event) {
                const editModal = document.getElementById('editInvoiceModal');
                const detailsModal = document.getElementById('detailsModal');

                if (event.target == editModal) {
                    closeEditModal();
                } else if (event.target == detailsModal) {
                    closeDetailsModal();
                }
            }
        });
    </script>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def upload_form():
    """Advanced multi-file upload form"""
    batch_status = None

    if request.method == 'POST':
        print("=== UPLOAD REQUEST RECEIVED ===")
        files = request.files.getlist('files')
        print(f"Files received: {len(files) if files else 0}")
        if files:
            print(f"File names: {[f.filename for f in files]}")

        if not files or not files[0].filename:
            print("ERROR: No files selected")
            batch_status = {'type': 'error', 'message': 'Nenhum arquivo selecionado'}
        else:
            # Process multiple files
            batch_id = str(uuid.uuid4())[:8]
            print(f"Processing batch {batch_id} with {len(files)} files...")
            batch_status = process_batch_files(files, batch_id)
            print(f"Batch processing result: {batch_status}")

            # If successful, redirect to refresh the page and show new data
            if batch_status and batch_status.get('type') == 'success':
                print("SUCCESS: Redirecting to refresh page...")
                return redirect(url_for('upload_form'))
    # For GET requests, don't show any batch_status (no loading bars on page refresh)

    # Get stats and ALL invoices for pagination
    conn = sqlite3.connect(DB_PATH)
    all_invoices = conn.execute("SELECT * FROM invoices ORDER BY created_at DESC").fetchall()
    total_count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    success_count = conn.execute("SELECT COUNT(*) FROM invoices WHERE confidence_score > 0.5").fetchone()[0]
    success_rate = int((success_count / total_count * 100)) if total_count > 0 else 0
    conn.close()

    return render_template_string(ADVANCED_TEMPLATE,
                                 batch_status=batch_status,
                                 recent_invoices=all_invoices,
                                 total_processed=total_count,
                                 success_rate=success_rate,
                                 supported_types_count=len(processor.supported_types))

def process_single_file(file):
    """Process a single file - used by parallel processing"""
    try:
        # Save file
        file_id = str(uuid.uuid4())[:8]
        filename = f"{file_id}_{file.filename}"
        file_path = UPLOAD_DIR / filename
        file.save(str(file_path))

        # Process file
        extracted_data = processor.extract_invoice_data(str(file_path))

        results = {'processed': 0, 'failed': 0, 'invoice_ids': []}

        if extracted_data.get('status') == 'error':
            results['failed'] = 1
            print(f"Failed to process {file.filename}: {extracted_data['error']}")
        elif extracted_data.get('archive_processed'):
            # Handle archive files with multiple results
            archive_results = extracted_data.get('results', [])
            for archive_result in archive_results:
                try:
                    with db_lock:  # Thread-safe database operation
                        invoice_id = save_advanced_invoice(archive_result, str(file_path), file)
                    results['processed'] += 1
                    results['invoice_ids'].append(invoice_id)
                except Exception as e:
                    results['failed'] += 1
                    print(f"Failed to save archive file result: {e}")
        else:
            # Save to database (single file)
            try:
                with db_lock:  # Thread-safe database operation
                    invoice_id = save_advanced_invoice(extracted_data, str(file_path), file)
                results['processed'] = 1
                results['invoice_ids'].append(invoice_id)
            except Exception as e:
                results['failed'] = 1
                print(f"Failed to save invoice: {e}")

        return results

    except Exception as e:
        print(f"Error processing {file.filename}: {e}")
        return {'processed': 0, 'failed': 1, 'invoice_ids': []}

def process_batch_files(files, batch_id):
    """Process multiple files in batch using parallel processing"""
    try:
        valid_files = [f for f in files if f.filename and processor.is_supported_file(f.filename)]
        if not valid_files:
            return {'type': 'error', 'message': 'Nenhum arquivo com formato suportado'}

        processed = 0
        failed = 0
        all_results = []

        # Use parallel processing with ThreadPoolExecutor
        # Limit to 3 concurrent threads to avoid API rate limits
        max_workers = min(3, len(valid_files))

        print(f"Processando {len(valid_files)} arquivos em paralelo com {max_workers} threads...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all files for processing
            future_to_file = {executor.submit(process_single_file, file): file for file in valid_files}

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    result = future.result()
                    processed += result['processed']
                    failed += result['failed']
                    all_results.extend(result['invoice_ids'])
                    print(f"Concluído: {file.filename} - {result['processed']} processados, {result['failed']} falharam")
                except Exception as e:
                    failed += 1
                    print(f"Erro no processamento paralelo de {file.filename}: {e}")

        # Create success message
        message = f"Processados {processed} arquivos com sucesso"
        if failed > 0:
            message += f", {failed} falharam"

        print(f"Processamento em lote concluído: {processed} sucessos, {failed} falhas")

        return {
            'type': 'success' if processed > 0 else 'error',
            'message': message,
            'progress': int((processed / (processed + failed)) * 100) if (processed + failed) > 0 else 0,
            'processed': processed,
            'failed': failed
        }

    except Exception as e:
        print(f"Erro no processamento em lote: {e}")
        return {'type': 'error', 'message': f'Erro no processamento em lote: {str(e)}'}

def save_advanced_invoice(extracted_data, file_path, original_file):
    """Save invoice with file information"""
    conn = sqlite3.connect(DB_PATH)

    invoice_id = str(uuid.uuid4())[:8]
    file_stats = Path(file_path).stat()

    conn.execute('''
        INSERT INTO invoices (
            id, invoice_number, date, vendor_name, total_amount, currency,
            business_unit, category, confidence_score, processing_notes,
            source_file, file_path, file_type, file_size, processed_at,
            created_at, extraction_method
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        invoice_id,
        extracted_data.get('invoice_number'),
        extracted_data.get('date'),
        extracted_data.get('vendor_name'),
        extracted_data.get('total_amount'),
        extracted_data.get('currency'),
        extracted_data.get('business_unit'),
        extracted_data.get('category'),
        extracted_data.get('confidence'),
        extracted_data.get('processing_notes'),
        original_file.filename,
        str(file_path),
        original_file.content_type,
        file_stats.st_size,
        extracted_data.get('processed_at'),
        datetime.now().isoformat(),
        extracted_data.get('extraction_method')
    ))

    conn.commit()
    conn.close()
    return invoice_id

@app.route('/invoice/<invoice_id>')
def invoice_details(invoice_id):
    """Detailed view of specific invoice"""
    conn = sqlite3.connect(DB_PATH)
    invoice = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()

    if not invoice:
        return "Invoice not found", 404

    # Convert to dict for easier template usage
    invoice_dict = {
        'id': invoice[0], 'invoice_number': invoice[1], 'date': invoice[2],
        'vendor_name': invoice[3], 'total_amount': invoice[5], 'currency': invoice[6],
        'business_unit': invoice[7], 'category': invoice[8], 'confidence_score': invoice[9],
        'processing_notes': invoice[10], 'source_file': invoice[11], 'file_path': invoice[12],
        'file_type': invoice[13], 'file_size': invoice[14], 'processed_at': invoice[15]
    }

    detail_template = '''
    <!DOCTYPE html>
    <html><head><title>Invoice Details - {{ invoice.id }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px; }
        .detail-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .field { margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; position: relative; display: flex; justify-content: space-between; align-items: start; }
        .field-content { flex-grow: 1; }
        .label { font-weight: bold; color: #495057; font-size: 14px; margin-bottom: 8px; }
        .value { font-size: 16px; }
        .edit-input { width: 100%; padding: 8px; border: 2px solid #007bff; border-radius: 4px; font-size: 16px; }
        .edit-buttons { margin-top: 10px; }
        .btn { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 5px; border: none; cursor: pointer; }
        .btn-success { background: #28a745; }
        .btn-secondary { background: #6c757d; }
        .btn-warning { background: #ffc107; color: #000; }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        .btn-xs { padding: 4px 8px; font-size: 11px; }
        .readonly { background: #e9ecef !important; color: #6c757d; }
        .editable { background: #fff; border-left: 4px solid #007bff; }
        .success-message { background: #d4edda; color: #155724; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .edit-field-btn { margin-left: 10px; }

        /* Modern action buttons */
        .action-buttons {
            display: flex;
            gap: 6px;
            align-items: center;
            justify-content: center;
            flex-wrap: nowrap;
            width: 120px;
            margin: 0 auto;
        }

        .btn-icon {
            width: 36px;
            height: 36px;
            min-width: 36px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            text-decoration: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.12), 0 1px 4px rgba(0,0,0,0.08);
            position: relative;
            overflow: hidden;
        }

        .btn-icon:before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            transform: scale(0);
            transition: transform 0.3s ease;
        }

        .btn-icon:hover:before {
            transform: scale(1);
        }

        .btn-icon:hover {
            transform: translateY(-2px) scale(1.05);
            box-shadow: 0 4px 16px rgba(0,0,0,0.16), 0 2px 8px rgba(0,0,0,0.12);
        }

        .btn-icon:active {
            transform: translateY(-1px) scale(1.02);
            transition: all 0.1s ease;
        }

        .btn-details {
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
            color: white;
        }

        .btn-details:hover {
            background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
        }

        .btn-download {
            background: linear-gradient(135deg, #28a745 0%, #218838 100%);
            color: white;
        }

        .btn-download:hover {
            background: linear-gradient(135deg, #218838 0%, #1e7e34 100%);
        }

        .btn-edit {
            background: linear-gradient(135deg, #ffc107 0%, #e0a800 100%);
            color: #000;
        }

        .btn-edit:hover {
            background: linear-gradient(135deg, #e0a800 0%, #d39e00 100%);
        }

        .action-cell {
            white-space: nowrap;
            padding: 12px 8px !important;
            text-align: center;
            vertical-align: middle;
            min-width: 140px;
        }

        /* Improved table layout */
        .table {
            table-layout: fixed;
        }

        .table th:last-child,
        .table td:last-child {
            width: 140px;
            text-align: center;
        }

        /* Mobile responsiveness */
        @media (max-width: 768px) {
            .btn-icon {
                width: 32px;
                height: 32px;
                min-width: 32px;
                font-size: 14px;
            }

            .action-buttons {
                gap: 4px;
                width: 108px;
            }

            .action-cell {
                padding: 8px 4px !important;
                min-width: 120px;
            }

            .table th:last-child,
            .table td:last-child {
                width: 120px;
            }
        }

        @media (max-width: 480px) {
            .btn-icon {
                width: 28px;
                height: 28px;
                min-width: 28px;
                font-size: 12px;
                border-radius: 6px;
            }

            .action-buttons {
                gap: 3px;
                width: 96px;
            }

            .action-cell {
                padding: 6px 2px !important;
                min-width: 100px;
            }

            .table th:last-child,
            .table td:last-child {
                width: 100px;
            }
        }
    </style></head>
    <body>
        <div class="detail-card">
            <h1>Invoice Details</h1>

            <div class="field readonly">
                <div class="field-content">
                    <div class="label">Invoice ID:</div>
                    <div class="value">{{ invoice.id }}</div>
                </div>
            </div>

            <div class="field editable" data-field="invoice_number">
                <div class="field-content">
                    <div class="label">Invoice Number:</div>
                    <div class="value" data-original="{{ invoice.invoice_number or '' }}">{{ invoice.invoice_number or 'N/A' }}</div>
                </div>
                <button class="btn btn-warning btn-xs edit-field-btn" onclick="startEditField('invoice_number')">✏️ Editar</button>
            </div>

            <div class="field editable" data-field="date">
                <div class="field-content">
                    <div class="label">Date:</div>
                    <div class="value" data-original="{{ invoice.date or '' }}">{{ invoice.date or 'N/A' }}</div>
                </div>
                <button class="btn btn-warning btn-xs edit-field-btn" onclick="startEditField('date')">✏️ Editar</button>
            </div>

            <div class="field editable" data-field="vendor_name">
                <div class="field-content">
                    <div class="label">Vendor:</div>
                    <div class="value" data-original="{{ invoice.vendor_name or '' }}">{{ invoice.vendor_name or 'N/A' }}</div>
                </div>
                <button class="btn btn-warning btn-xs edit-field-btn" onclick="startEditField('vendor_name')">✏️ Editar</button>
            </div>

            <div class="field editable" data-field="total_amount">
                <div class="field-content">
                    <div class="label">Amount:</div>
                    <div class="value" data-original="{{ invoice.total_amount or 0 }}">${{ invoice.total_amount }} {{ invoice.currency }}</div>
                </div>
                <button class="btn btn-warning btn-xs edit-field-btn" onclick="startEditField('total_amount')">✏️ Editar</button>
            </div>

            <div class="field editable" data-field="currency">
                <div class="field-content">
                    <div class="label">Currency:</div>
                    <div class="value" data-original="{{ invoice.currency or '' }}">{{ invoice.currency or 'N/A' }}</div>
                </div>
                <button class="btn btn-warning btn-xs edit-field-btn" onclick="startEditField('currency')">✏️ Editar</button>
            </div>

            <div class="field editable" data-field="business_unit">
                <div class="field-content">
                    <div class="label">Business Unit:</div>
                    <div class="value" data-original="{{ invoice.business_unit or '' }}">{{ invoice.business_unit or 'N/A' }}</div>
                </div>
                <button class="btn btn-warning btn-xs edit-field-btn" onclick="startEditField('business_unit')">✏️ Editar</button>
            </div>

            <div class="field editable" data-field="category">
                <div class="field-content">
                    <div class="label">Category:</div>
                    <div class="value" data-original="{{ invoice.category or '' }}">{{ invoice.category or 'N/A' }}</div>
                </div>
                <button class="btn btn-warning btn-xs edit-field-btn" onclick="startEditField('category')">✏️ Editar</button>
            </div>

            <div class="field readonly"><div class="label">Confidence Score:</div><div class="value">{{ (invoice.confidence_score * 100) | round }}%</div></div>
            <div class="field readonly"><div class="label">Processing Notes:</div><div class="value">{{ invoice.processing_notes or 'N/A' }}</div></div>
            <div class="field readonly"><div class="label">Source File:</div><div class="value">{{ invoice.source_file }}</div></div>
            <div class="field readonly"><div class="label">File Size:</div><div class="value">{{ (invoice.file_size / 1024 / 1024) | round(2) }} MB</div></div>
            <div class="field readonly"><div class="label">Processed At:</div><div class="value">{{ invoice.processed_at }}</div></div>

            <div style="margin-top: 30px;">
                <a href="/file/{{ invoice.id }}" class="btn">📄 Ver Arquivo Original</a>
                <a href="/" class="btn btn-secondary">⬅️ Voltar</a>
            </div>
        </div>

        <script>
            const invoiceId = '{{ invoice.id }}';

            // Button-based editing system
            function startEditField(fieldName) {
                const fieldElement = document.querySelector(`[data-field="${fieldName}"]`);
                if (fieldElement.classList.contains('editing')) {
                    return; // Already editing
                }

                const valueElement = fieldElement.querySelector('.value');
                const currentValue = valueElement.dataset.original || '';

                fieldElement.classList.add('editing');

                let inputHtml;
                if (fieldName === 'date') {
                    inputHtml = `<input type="date" class="edit-input" value="${currentValue}">`;
                } else if (fieldName === 'total_amount') {
                    inputHtml = `<input type="number" step="0.01" class="edit-input" value="${currentValue}">`;
                } else if (fieldName === 'category') {
                    const categories = ['Technology Expenses', 'Trading', 'Mining', 'Services', 'Other'];
                    inputHtml = `<select class="edit-input">`;
                    categories.forEach(cat => {
                        const selected = cat === currentValue ? 'selected' : '';
                        inputHtml += `<option value="${cat}" ${selected}>${cat}</option>`;
                    });
                    inputHtml += `</select>`;
                } else if (fieldName === 'business_unit') {
                    const units = ['Delta LLC', 'Delta Prop Shop LLC', 'Infinity Validator', 'Delta Mining Paraguay S.A.', 'Personal'];
                    inputHtml = `<select class="edit-input">`;
                    units.forEach(unit => {
                        const selected = unit === currentValue ? 'selected' : '';
                        inputHtml += `<option value="${unit}" ${selected}>${unit}</option>`;
                    });
                    inputHtml += `</select>`;
                } else if (fieldName === 'currency') {
                    const currencies = ['USD', 'EUR', 'BRL', 'BTC', 'ETH'];
                    inputHtml = `<select class="edit-input">`;
                    currencies.forEach(curr => {
                        const selected = curr === currentValue ? 'selected' : '';
                        inputHtml += `<option value="${curr}" ${selected}>${curr}</option>`;
                    });
                    inputHtml += `</select>`;
                } else {
                    inputHtml = `<input type="text" class="edit-input" value="${currentValue}">`;
                }

                valueElement.innerHTML = inputHtml +
                    `<div class="edit-buttons">
                        <button class="btn btn-success btn-sm" onclick="saveField('${fieldName}', this)">💾 Salvar</button>
                        <button class="btn btn-secondary btn-sm" onclick="cancelEditField('${fieldName}')">❌ Cancelar</button>
                    </div>`;

                // Hide the edit button while editing
                const editButton = fieldElement.querySelector('.edit-field-btn');
                editButton.style.display = 'none';

                const input = fieldElement.querySelector('.edit-input');
                input.focus();
                if (input.type === 'text') {
                    input.select();
                }
            }

            function saveField(fieldName, button) {
                const fieldElement = button.closest('.field');
                const input = fieldElement.querySelector('.edit-input');
                const newValue = input.value;

                // Show loading
                button.textContent = '⏳ Salvando...';
                button.disabled = true;

                const updateData = {};
                updateData[fieldName] = newValue;

                // Include required fields for API
                const allFields = ['invoice_number', 'vendor_name', 'total_amount', 'currency', 'business_unit', 'category', 'date'];
                allFields.forEach(field => {
                    if (field !== fieldName) {
                        const fieldEl = document.querySelector(`[data-field="${field}"] .value`);
                        if (fieldEl) {
                            updateData[field] = fieldEl.dataset.original || '';
                        }
                    }
                });

                fetch(`/api/invoice/${invoiceId}/update`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(updateData)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Update the display
                        const valueElement = fieldElement.querySelector('.value');
                        valueElement.dataset.original = newValue;

                        let displayValue = newValue || 'N/A';
                        if (fieldName === 'total_amount') {
                            const currency = updateData.currency || 'USD';
                            displayValue = `$${newValue} ${currency}`;
                        }

                        valueElement.innerHTML = displayValue;
                        fieldElement.classList.remove('editing');

                        // Show the edit button again
                        const editButton = fieldElement.querySelector('.edit-field-btn');
                        editButton.style.display = 'block';

                        // Show success message
                        showMessage('Campo atualizado com sucesso!', 'success');
                    } else {
                        alert('Erro ao atualizar: ' + (data.error || 'Erro desconhecido'));
                        cancelEditField(fieldName);
                    }
                })
                .catch(error => {
                    console.error('Erro:', error);
                    alert('Erro ao salvar alterações');
                    cancelEditField(fieldName);
                })
                .finally(() => {
                    button.textContent = '💾 Salvar';
                    button.disabled = false;
                });
            }

            function cancelEditField(fieldName) {
                const fieldElement = document.querySelector(`[data-field="${fieldName}"]`);
                const valueElement = fieldElement.querySelector('.value');
                const originalValue = valueElement.dataset.original || 'N/A';

                let displayValue = originalValue;
                if (fieldName === 'total_amount' && originalValue !== 'N/A') {
                    const currencyElement = document.querySelector('[data-field="currency"] .value');
                    const currency = currencyElement ? currencyElement.dataset.original : 'USD';
                    displayValue = `$${originalValue} ${currency}`;
                }

                valueElement.innerHTML = displayValue;
                fieldElement.classList.remove('editing');

                // Show the edit button again
                const editButton = fieldElement.querySelector('.edit-field-btn');
                editButton.style.display = 'block';
            }

            function showMessage(message, type) {
                const messageDiv = document.createElement('div');
                messageDiv.className = type === 'success' ? 'success-message' : 'error-message';
                messageDiv.textContent = message;

                document.querySelector('.detail-card').insertBefore(messageDiv, document.querySelector('h1').nextSibling);

                setTimeout(() => {
                    messageDiv.remove();
                }, 3000);
            }
        </script>
    </body></html>
    '''
    return render_template_string(detail_template, invoice=invoice_dict)

@app.route('/file/<invoice_id>')
def serve_file(invoice_id):
    """Serve original uploaded file"""
    conn = sqlite3.connect(DB_PATH)
    invoice = conn.execute("SELECT file_path, source_file FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()

    if not invoice or not os.path.exists(invoice[0]):
        return "File not found", 404

    return send_from_directory(
        os.path.dirname(invoice[0]),
        os.path.basename(invoice[0]),
        as_attachment=True,
        download_name=invoice[1]
    )

@app.route('/api/stats')
def api_stats():
    """API for statistics"""
    conn = sqlite3.connect(DB_PATH)

    stats = {
        'total_invoices': conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0],
        'avg_confidence': conn.execute("SELECT AVG(confidence_score) FROM invoices").fetchone()[0] or 0,
        'file_types': {}
    }

    # File type breakdown
    file_types = conn.execute("SELECT file_type, COUNT(*) FROM invoices GROUP BY file_type").fetchall()
    for file_type, count in file_types:
        stats['file_types'][file_type or 'unknown'] = count

    conn.close()
    return jsonify(stats)

@app.route('/api/filter_options')
def api_filter_options():
    """API for filter dropdown options"""
    try:
        conn = sqlite3.connect(DB_PATH)

        # Get unique business units
        business_units = conn.execute('''
            SELECT DISTINCT business_unit
            FROM invoices
            WHERE business_unit IS NOT NULL AND business_unit != ''
            ORDER BY business_unit
        ''').fetchall()

        # Get unique categories
        categories = conn.execute('''
            SELECT DISTINCT category
            FROM invoices
            WHERE category IS NOT NULL AND category != ''
            ORDER BY category
        ''').fetchall()

        conn.close()

        return jsonify({
            'business_units': [bu[0] for bu in business_units],
            'categories': [cat[0] for cat in categories]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bulk_download', methods=['POST'])
def bulk_download():
    """Bulk download selected invoices as ZIP"""
    try:
        data = request.get_json()
        invoice_ids = data.get('invoice_ids', [])

        if not invoice_ids:
            return jsonify({'error': 'Nenhum invoice selecionado'}), 400

        # Create temporary zip file
        import io
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            conn = sqlite3.connect(DB_PATH)

            for invoice_id in invoice_ids:
                # Get invoice info
                invoice = conn.execute(
                    "SELECT * FROM invoices WHERE id = ?",
                    (invoice_id,)
                ).fetchone()

                if invoice and len(invoice) > 12 and invoice[12]:  # file_path exists
                    file_path = invoice[12]
                    if os.path.exists(file_path):
                        # Add to zip with a clean filename
                        invoice_number = invoice[1] or invoice_id
                        file_extension = os.path.splitext(file_path)[1]
                        clean_filename = f"{invoice_number}_{invoice_id}{file_extension}"
                        zip_file.write(file_path, clean_filename)

            conn.close()

        zip_buffer.seek(0)

        # Return zip file
        from flask import send_file
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=f'invoices_bulk_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip',
            mimetype='application/zip'
        )

    except Exception as e:
        return jsonify({'error': f'Erro ao criar ZIP: {str(e)}'}), 500

@app.route('/api/bulk_delete', methods=['POST'])
def bulk_delete():
    """Bulk delete selected invoices"""
    try:
        data = request.get_json()
        invoice_ids = data.get('invoice_ids', [])

        if not invoice_ids:
            return jsonify({'error': 'Nenhum invoice selecionado'}), 400

        conn = sqlite3.connect(DB_PATH)
        deleted_count = 0

        for invoice_id in invoice_ids:
            # Get file path before deletion
            invoice = conn.execute(
                "SELECT file_path FROM invoices WHERE id = ?",
                (invoice_id,)
            ).fetchone()

            # Delete from database
            result = conn.execute(
                "DELETE FROM invoices WHERE id = ?",
                (invoice_id,)
            )

            if result.rowcount > 0:
                deleted_count += 1

                # Delete physical file if exists
                if invoice and invoice[0] and os.path.exists(invoice[0]):
                    try:
                        os.remove(invoice[0])
                    except OSError:
                        pass  # Continue even if file deletion fails

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'{deleted_count} invoices deletados com sucesso'
        })

    except Exception as e:
        return jsonify({'error': f'Erro ao deletar: {str(e)}'}), 500

@app.route('/api/invoice/<invoice_id>', methods=['GET'])
def get_invoice_data(invoice_id):
    """Get invoice data for editing"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, invoice_number, date, vendor_name, total_amount,
                   currency, business_unit, category
            FROM invoices WHERE id = ?
        """, (invoice_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            invoice_data = {
                'id': row[0],
                'invoice_number': row[1],
                'date': row[2],
                'vendor_name': row[3],
                'total_amount': row[4],
                'currency': row[5],
                'business_unit': row[6],
                'category': row[7]
            }
            return jsonify({'success': True, 'data': invoice_data})
        else:
            return jsonify({'error': 'Invoice não encontrado'}), 404

    except Exception as e:
        return jsonify({'error': f'Erro ao buscar invoice: {str(e)}'}), 500

@app.route('/api/invoice/<invoice_id>/update', methods=['PUT'])
def update_invoice(invoice_id):
    """Update invoice data"""
    try:
        data = request.get_json()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE invoices
            SET invoice_number = ?, vendor_name = ?, total_amount = ?,
                currency = ?, business_unit = ?, category = ?, date = ?
            WHERE id = ?
        """, (
            data['invoice_number'],
            data['vendor_name'],
            data['total_amount'],
            data['currency'],
            data['business_unit'],
            data['category'],
            data.get('date', ''),
            invoice_id
        ))

        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Invoice atualizado com sucesso'})
        else:
            conn.close()
            return jsonify({'error': 'Invoice não encontrado'}), 404

    except Exception as e:
        return jsonify({'error': f'Erro ao atualizar invoice: {str(e)}'}), 500

if __name__ == '__main__':
    init_db()
    print("Advanced Upload System with Bulk Actions starting...")
    print("   Features: Multi-file upload, Multiple formats, File viewing, Bulk actions")
    print("   Access: http://localhost:5007")
    print("   Supported: PDF, CSV, XLS, XLSX, Images, Text files")
    print("   NEW: Bulk download and delete functionality!")

    app.run(host='0.0.0.0', port=5007, debug=True, use_reloader=False)