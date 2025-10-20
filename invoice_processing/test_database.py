#!/usr/bin/env python3
"""
Test Database Setup
Primeiro teste prático - verificar se conseguimos salvar/carregar invoices
"""

from integration import MainSystemIntegrator
from models.invoice import Invoice, InvoiceVendor, InvoiceStatus
from decimal import Decimal
from datetime import date
import json

def test_database_operations():
    """Teste completo das operações de banco"""
    print("=== TESTE DATABASE OPERATIONS ===")

    # Setup
    integrator = MainSystemIntegrator()
    integrator.create_invoice_tables()

    # Test 1: Create Invoice
    print("\n1. Testing Invoice Creation...")
    vendor = InvoiceVendor(
        name="AWS - Amazon Web Services",
        address="Seattle, WA, USA",
        tax_id="91-1646860",
        email="billing@aws.amazon.com"
    )

    invoice = Invoice(
        invoice_number="AWS-2024-TEST-001",
        date=date.today(),
        vendor=vendor,
        total_amount=Decimal('1247.50'),
        currency="USD",
        status=InvoiceStatus.COMPLETED,
        business_unit="Delta LLC",
        category="Technology Expenses",
        processing_notes="Test invoice for database validation"
    )

    # Save invoice
    invoice_id = integrator.save_invoice(invoice.to_dict())
    print(f"✅ Invoice created with ID: {invoice_id}")

    # Test 2: Retrieve Invoice
    print("\n2. Testing Invoice Retrieval...")
    invoices = integrator.get_invoices(limit=5)
    print(f"✅ Retrieved {len(invoices)} invoices")

    for inv in invoices:
        print(f"  - {inv['invoice_number']}: ${inv['total_amount']} ({inv['vendor_name']})")

    # Test 3: Filter Invoices
    print("\n3. Testing Invoice Filtering...")
    filtered = integrator.get_invoices(
        filters={'business_unit': 'Delta LLC', 'status': 'completed'}
    )
    print(f"✅ Filtered results: {len(filtered)} invoices")

    # Test 4: JSON Serialization
    print("\n4. Testing Data Serialization...")
    if invoices:
        sample = invoices[0]
        vendor_data = json.loads(sample['vendor_data']) if sample['vendor_data'] else {}
        line_items = json.loads(sample['line_items']) if sample['line_items'] else []
        print(f"✅ Vendor data: {vendor_data.get('name', 'N/A')}")
        print(f"✅ Line items: {len(line_items)} items")

    print("\n=== DATABASE TESTS COMPLETED ===")
    return True

def test_error_handling():
    """Teste de tratamento de erros"""
    print("\n=== TESTE ERROR HANDLING ===")

    integrator = MainSystemIntegrator()

    # Test duplicate invoice number
    try:
        invoice_data = {
            'id': 'test-duplicate',
            'invoice_number': 'DUPLICATE-TEST',
            'date': '2024-09-25',
            'vendor': {'name': 'Test Vendor'},
            'total_amount': 100.0,
            'currency': 'USD',
            'status': 'pending',
            'invoice_type': 'other',
            'confidence_score': 0.9,
            'created_at': '2024-09-25T10:00:00'
        }

        # Insert twice - should handle gracefully
        id1 = integrator.save_invoice(invoice_data)
        id2 = integrator.save_invoice(invoice_data)  # Should replace

        print(f"✅ Duplicate handling: {id1} -> {id2}")

    except Exception as e:
        print(f"❌ Error handling failed: {e}")
        return False

    print("✅ Error handling tests passed")
    return True

if __name__ == "__main__":
    success = test_database_operations() and test_error_handling()
    print(f"\n{'SUCCESS' if success else 'FAILED'}: Database setup {'complete' if success else 'needs fixes'}")