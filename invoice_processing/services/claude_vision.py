#!/usr/bin/env python3
"""
Claude Vision Service - PDF Invoice Processing
Core service para extrair dados de faturas usando Claude Vision API
"""

import base64
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import anthropic
from ..config.settings import CLAUDE_CONFIG, PROCESSING_CONFIG

class ClaudeVisionService:
    """Service para processamento de faturas com Claude Vision"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or CLAUDE_CONFIG['API_KEY']
        if not self.api_key:
            raise ValueError("Claude API key not configured")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = CLAUDE_CONFIG['MODEL']

    def extract_invoice_data(self, file_path: str) -> Dict[str, Any]:
        """
        Extrai dados estruturados de uma fatura

        Args:
            file_path: Caminho para o arquivo da fatura (PDF/image)

        Returns:
            Dict com dados extraídos da fatura
        """
        try:
            # Validate file
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            file_size = os.path.getsize(file_path)
            if file_size > PROCESSING_CONFIG['MAX_FILE_SIZE']:
                raise ValueError(f"File too large: {file_size} bytes")

            # Check file type
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in PROCESSING_CONFIG['ALLOWED_EXTENSIONS']:
                raise ValueError(f"Unsupported file type: {file_ext}")

            print(f"Processing invoice: {os.path.basename(file_path)} ({file_size} bytes)")

            # Convert file to base64 for Claude Vision
            if file_ext == '.pdf':
                # For PDF, convert first page to image
                image_data = self._pdf_to_image_base64(file_path)
            else:
                # For images, encode directly
                image_data = self._encode_image_to_base64(file_path)

            # Send to Claude Vision
            extracted_data = self._call_claude_vision(image_data, file_path)

            # Validate and structure the response
            structured_data = self._validate_and_structure(extracted_data, file_path)

            print(f"✅ Invoice data extracted successfully")
            return structured_data

        except Exception as e:
            print(f"❌ Invoice extraction failed: {e}")
            return self._create_error_response(str(e), file_path)

    def _pdf_to_image_base64(self, pdf_path: str) -> str:
        """Convert PDF first page to base64 image"""
        try:
            from pdf2image import convert_from_path
            from io import BytesIO
            from PIL import Image

            # Convert first page to image
            pages = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=300)
            if not pages:
                raise ValueError("Could not convert PDF to image")

            # Convert to base64
            img = pages[0]
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            image_bytes = buffer.getvalue()

            return base64.b64encode(image_bytes).decode('utf-8')

        except ImportError:
            raise ValueError("PDF processing requires: pip install pdf2image Pillow")
        except Exception as e:
            raise ValueError(f"PDF conversion failed: {e}")

    def _encode_image_to_base64(self, image_path: str) -> str:
        """Encode image file to base64"""
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Image encoding failed: {e}")

    def _call_claude_vision(self, image_base64: str, file_path: str) -> Dict[str, Any]:
        """Call Claude Vision API to extract invoice data"""

        prompt = self._build_extraction_prompt(file_path)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=CLAUDE_CONFIG['MAX_TOKENS'],
                temperature=CLAUDE_CONFIG['TEMPERATURE'],
                messages=[
                    {
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
                    }
                ]
            )

            # Parse JSON response
            response_text = response.content[0].text.strip()

            # Try to extract JSON from response
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            return json.loads(response_text)

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response from Claude: {e}")
            print(f"Raw response: {response_text[:500]}...")
            raise ValueError("Invalid JSON response from Claude Vision")
        except Exception as e:
            raise ValueError(f"Claude Vision API call failed: {e}")

    def _build_extraction_prompt(self, file_path: str) -> str:
        """Build prompt for Claude to extract invoice data"""
        filename = os.path.basename(file_path)

        return f"""
Analyze this invoice image and extract the following information in JSON format.

File: {filename}

Extract these fields with high accuracy:

REQUIRED FIELDS:
- invoice_number: The invoice/bill number
- date: Invoice date (YYYY-MM-DD format)
- vendor_name: Company/vendor name
- total_amount: Total amount (numeric value only)
- currency: Currency (USD, BRL, etc.)

OPTIONAL FIELDS:
- due_date: Due date if present (YYYY-MM-DD format)
- vendor_address: Vendor address
- vendor_tax_id: Tax ID/CNPJ/EIN if present
- tax_amount: Tax amount if itemized
- subtotal: Subtotal before tax
- line_items: Array of line items with description, quantity, unit_price, total

CLASSIFICATION HINTS:
Based on the vendor, suggest:
- business_unit: One of ["Delta LLC", "Delta Prop Shop LLC", "Delta Mining Paraguay S.A.", "Delta Brazil", "Personal"]
- category: One of ["Technology Expenses", "Utilities", "Insurance", "Professional Services", "Office Expenses", "Other"]

Return ONLY a JSON object with this structure:
{{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "vendor_name": "string",
    "vendor_address": "string",
    "vendor_tax_id": "string",
    "total_amount": 1234.56,
    "currency": "USD",
    "tax_amount": 123.45,
    "subtotal": 1111.11,
    "due_date": "YYYY-MM-DD",
    "line_items": [
        {{"description": "Item 1", "quantity": 1, "unit_price": 100.00, "total": 100.00}}
    ],
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Any issues or observations"
}}

Be precise with numbers and dates. If a field is not clearly visible, use null.
"""

    def _validate_and_structure(self, raw_data: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Validate and structure the extracted data"""
        try:
            # Required fields validation
            required_fields = ['invoice_number', 'date', 'vendor_name', 'total_amount', 'currency']
            for field in required_fields:
                if not raw_data.get(field):
                    print(f"⚠️  Missing required field: {field}")

            # Structure the response
            structured = {
                # Required fields
                'invoice_number': str(raw_data.get('invoice_number', '')),
                'date': raw_data.get('date'),
                'vendor_name': str(raw_data.get('vendor_name', '')),
                'total_amount': float(raw_data.get('total_amount', 0)),
                'currency': str(raw_data.get('currency', 'USD')),

                # Optional fields
                'due_date': raw_data.get('due_date'),
                'vendor_address': raw_data.get('vendor_address'),
                'vendor_tax_id': raw_data.get('vendor_tax_id'),
                'tax_amount': float(raw_data.get('tax_amount', 0)) if raw_data.get('tax_amount') else None,
                'subtotal': float(raw_data.get('subtotal', 0)) if raw_data.get('subtotal') else None,
                'line_items': raw_data.get('line_items', []),

                # Classification
                'business_unit': raw_data.get('business_unit'),
                'category': raw_data.get('category'),

                # Processing metadata
                'confidence': float(raw_data.get('confidence', 0.8)),
                'processing_notes': raw_data.get('processing_notes', ''),
                'source_file': os.path.basename(file_path),
                'extraction_method': 'claude_vision',
                'api_model': self.model
            }

            return structured

        except Exception as e:
            print(f"❌ Data validation failed: {e}")
            return self._create_error_response(f"Validation error: {e}", file_path)

    def _create_error_response(self, error_message: str, file_path: str) -> Dict[str, Any]:
        """Create error response structure"""
        return {
            'invoice_number': '',
            'date': None,
            'vendor_name': 'ERROR',
            'total_amount': 0.0,
            'currency': 'USD',
            'confidence': 0.0,
            'processing_notes': f"Extraction failed: {error_message}",
            'source_file': os.path.basename(file_path),
            'extraction_method': 'claude_vision',
            'status': 'error',
            'error_message': error_message
        }

    def test_with_sample_invoice(self, test_file_path: str) -> Dict[str, Any]:
        """Test extraction with a sample invoice file"""
        print(f"=== TESTING CLAUDE VISION WITH: {test_file_path} ===")

        if not os.path.exists(test_file_path):
            return {'error': f"Test file not found: {test_file_path}"}

        result = self.extract_invoice_data(test_file_path)

        print(f"📊 EXTRACTION RESULTS:")
        print(f"  Invoice #: {result.get('invoice_number')}")
        print(f"  Vendor: {result.get('vendor_name')}")
        print(f"  Amount: ${result.get('total_amount')} {result.get('currency')}")
        print(f"  Date: {result.get('date')}")
        print(f"  Confidence: {result.get('confidence', 0):.1%}")
        print(f"  Business Unit: {result.get('business_unit')}")

        return result


# Test function
def test_claude_vision():
    """Test Claude Vision service"""
    try:
        service = ClaudeVisionService()
        print("✅ Claude Vision service initialized")

        # Test with a sample file (you'll need to provide this)
        test_files = [
            "test_invoice.pdf",
            "sample_bill.png",
            "test_data/invoice_sample.pdf"
        ]

        for test_file in test_files:
            if os.path.exists(test_file):
                result = service.test_with_sample_invoice(test_file)
                return result

        print("ℹ️  No test files found. Create a test_invoice.pdf to test extraction.")
        return {'status': 'no_test_files'}

    except Exception as e:
        print(f"❌ Claude Vision test failed: {e}")
        return {'error': str(e)}

if __name__ == "__main__":
    test_claude_vision()