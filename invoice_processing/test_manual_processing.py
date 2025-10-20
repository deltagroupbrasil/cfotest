#!/usr/bin/env python3
"""
Manual Processing Test - MVP Core Functionality
Teste o pipeline completo: PDF → Claude Vision → Database → Integration
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from services.claude_vision import ClaudeVisionService
from integration import MainSystemIntegrator
from models.invoice import Invoice, InvoiceVendor, InvoiceStatus
from datetime import datetime, date
from decimal import Decimal

class ManualProcessingPipeline:
    """Pipeline completo para teste manual de faturas"""

    def __init__(self):
        self.claude_service = ClaudeVisionService()
        self.integrator = MainSystemIntegrator()
        print("🚀 Manual Processing Pipeline initialized")

    def process_invoice_file(self, file_path: str) -> dict:
        """
        Processa um arquivo de fatura completo
        Este é o teste do pipeline MVP
        """
        print(f"\n=== PROCESSING INVOICE: {os.path.basename(file_path)} ===")

        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        try:
            # Step 1: Extract data with Claude Vision
            print("1️⃣  Extracting data with Claude Vision...")
            extracted_data = self.claude_service.extract_invoice_data(file_path)

            if extracted_data.get('status') == 'error':
                print(f"❌ Extraction failed: {extracted_data.get('error_message')}")
                return extracted_data

            print(f"✅ Data extracted successfully")
            print(f"   Invoice #: {extracted_data.get('invoice_number')}")
            print(f"   Vendor: {extracted_data.get('vendor_name')}")
            print(f"   Amount: ${extracted_data.get('total_amount')} {extracted_data.get('currency')}")

            # Step 2: Create Invoice object
            print("2️⃣  Creating Invoice object...")
            invoice = self._create_invoice_from_data(extracted_data)

            if not invoice.is_valid():
                print("❌ Invalid invoice data")
                return {"error": "Invalid invoice data", "data": extracted_data}

            print(f"✅ Valid invoice created")

            # Step 3: Save to database
            print("3️⃣  Saving to database...")
            invoice_id = self.integrator.save_invoice(invoice.to_dict())
            print(f"✅ Invoice saved with ID: {invoice_id}")

            # Step 4: Integration with main system (optional)
            print("4️⃣  Integration with main system...")
            transaction_id = self.integrator.create_transaction_from_invoice(invoice.to_dict())
            if transaction_id:
                print(f"✅ Transaction created: {transaction_id}")
            else:
                print("ℹ️  Transaction integration skipped (not implemented yet)")

            # Step 5: Summary
            result = {
                "status": "success",
                "invoice_id": invoice_id,
                "transaction_id": transaction_id,
                "extracted_data": extracted_data,
                "invoice_data": invoice.to_dict(),
                "confidence": extracted_data.get('confidence', 0),
                "processing_time": "~30 seconds"  # Will implement timing later
            }

            print(f"\n✅ PROCESSING COMPLETED SUCCESSFULLY")
            print(f"   Invoice ID: {invoice_id}")
            print(f"   Confidence: {result['confidence']:.1%}")

            return result

        except Exception as e:
            error_result = {
                "status": "error",
                "error_message": str(e),
                "file_path": file_path
            }
            print(f"❌ Processing failed: {e}")
            return error_result

    def _create_invoice_from_data(self, extracted_data: dict) -> Invoice:
        """Create Invoice object from extracted data"""
        try:
            # Create vendor
            vendor = InvoiceVendor(
                name=extracted_data.get('vendor_name', 'Unknown'),
                address=extracted_data.get('vendor_address'),
                tax_id=extracted_data.get('vendor_tax_id')
            )

            # Parse date
            invoice_date = None
            if extracted_data.get('date'):
                try:
                    invoice_date = datetime.strptime(extracted_data['date'], '%Y-%m-%d').date()
                except:
                    invoice_date = date.today()  # Fallback

            # Create invoice
            invoice = Invoice(
                invoice_number=extracted_data.get('invoice_number', 'UNKNOWN'),
                date=invoice_date or date.today(),
                vendor=vendor,
                total_amount=Decimal(str(extracted_data.get('total_amount', 0))),
                currency=extracted_data.get('currency', 'USD'),
                tax_amount=Decimal(str(extracted_data.get('tax_amount', 0))) if extracted_data.get('tax_amount') else None,
                subtotal=Decimal(str(extracted_data.get('subtotal', 0))) if extracted_data.get('subtotal') else None,
                status=InvoiceStatus.COMPLETED if extracted_data.get('confidence', 0) > 0.8 else InvoiceStatus.REVIEW_REQUIRED,
                confidence_score=extracted_data.get('confidence', 0.0),
                processing_notes=extracted_data.get('processing_notes', ''),
                source_file=extracted_data.get('source_file'),
                business_unit=extracted_data.get('business_unit') or self._classify_business_unit(extracted_data.get('vendor_name', '')),
                category=extracted_data.get('category') or self._classify_category(extracted_data.get('vendor_name', ''))
            )

            return invoice

        except Exception as e:
            raise ValueError(f"Failed to create invoice object: {e}")

    def _classify_business_unit(self, vendor_name: str) -> str:
        """Simple business unit classification"""
        vendor_lower = vendor_name.lower()

        if any(tech in vendor_lower for tech in ['aws', 'amazon', 'microsoft', 'google', 'software']):
            return 'Delta LLC'
        elif any(py in vendor_lower for py in ['paraguay', 'ande']):
            return 'Delta Mining Paraguay S.A.'
        elif any(br in vendor_lower for br in ['brasil', 'brazil', 'porto seguro']):
            return 'Delta Brazil'
        else:
            return 'Delta LLC'  # Default

    def _classify_category(self, vendor_name: str) -> str:
        """Simple category classification"""
        vendor_lower = vendor_name.lower()

        if any(tech in vendor_lower for tech in ['aws', 'microsoft', 'google', 'software', 'saas']):
            return 'Technology Expenses'
        elif any(util in vendor_lower for util in ['electric', 'power', 'energy', 'ande']):
            return 'Utilities'
        elif any(ins in vendor_lower for ins in ['insurance', 'seguro']):
            return 'Insurance'
        else:
            return 'Other'

    def batch_process_folder(self, folder_path: str) -> list:
        """Process all invoice files in a folder"""
        print(f"\n=== BATCH PROCESSING FOLDER: {folder_path} ===")

        if not os.path.exists(folder_path):
            print(f"❌ Folder not found: {folder_path}")
            return []

        # Find all supported files
        supported_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff']
        files = []
        for ext in supported_extensions:
            files.extend(Path(folder_path).glob(f"*{ext}"))

        if not files:
            print("ℹ️  No supported files found")
            return []

        print(f"📁 Found {len(files)} files to process")

        results = []
        for file_path in files:
            try:
                result = self.process_invoice_file(str(file_path))
                results.append(result)
            except Exception as e:
                print(f"❌ Failed to process {file_path}: {e}")
                results.append({"error": str(e), "file": str(file_path)})

        # Summary
        successful = len([r for r in results if r.get('status') == 'success'])
        print(f"\n📊 BATCH PROCESSING SUMMARY:")
        print(f"   Total files: {len(files)}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {len(files) - successful}")

        return results

    def test_with_sample_data(self):
        """Test with sample data if no real files available"""
        print("\n=== TESTING WITH SAMPLE DATA ===")

        # Create sample extracted data (simulating Claude Vision output)
        sample_data = {
            "invoice_number": "TEST-2024-001",
            "date": "2024-09-25",
            "vendor_name": "AWS - Amazon Web Services",
            "vendor_address": "Seattle, WA, USA",
            "vendor_tax_id": "91-1646860",
            "total_amount": 1247.50,
            "currency": "USD",
            "tax_amount": 124.75,
            "subtotal": 1122.75,
            "business_unit": "Delta LLC",
            "category": "Technology Expenses",
            "confidence": 0.95,
            "processing_notes": "Sample test data",
            "source_file": "test_sample.pdf"
        }

        # Process sample data
        try:
            invoice = self._create_invoice_from_data(sample_data)
            invoice_id = self.integrator.save_invoice(invoice.to_dict())

            print(f"✅ Sample invoice processed successfully")
            print(f"   Invoice ID: {invoice_id}")
            print(f"   Ready for real file testing!")

            return {"status": "success", "invoice_id": invoice_id}

        except Exception as e:
            print(f"❌ Sample processing failed: {e}")
            return {"error": str(e)}


def main():
    """Main testing function"""
    print("=" * 60)
    print("MANUAL INVOICE PROCESSING - MVP TEST")
    print("=" * 60)

    pipeline = ManualProcessingPipeline()

    # Test 1: Sample data processing
    print("\n🧪 TEST 1: Sample Data Processing")
    sample_result = pipeline.test_with_sample_data()

    # Test 2: Look for real test files
    print("\n🧪 TEST 2: Real File Processing")
    test_files = [
        "test_invoice.pdf",
        "sample_invoice.png",
        "test_data/invoice.pdf",
        "../test_invoice.pdf"
    ]

    processed_any = False
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"📄 Found test file: {test_file}")
            result = pipeline.process_invoice_file(test_file)
            processed_any = True
            break

    if not processed_any:
        print("ℹ️  No test files found. To test with real files:")
        print("   1. Place a PDF invoice as 'test_invoice.pdf'")
        print("   2. Run: python test_manual_processing.py")

    # Test 3: Check database
    print("\n🧪 TEST 3: Database Check")
    invoices = pipeline.integrator.get_invoices(limit=5)
    print(f"📊 Database contains {len(invoices)} invoices")

    for inv in invoices[:3]:
        print(f"  - {inv['invoice_number']}: {inv['vendor_name']} (${inv['total_amount']})")

    print("\n" + "=" * 60)
    print("MVP TESTING COMPLETED")
    print("Next steps: Add real invoice files and test extraction accuracy")
    print("=" * 60)

if __name__ == "__main__":
    main()