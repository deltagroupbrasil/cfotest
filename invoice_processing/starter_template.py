#!/usr/bin/env python3
"""
Invoice Processing - Starter Template
Quick starter para começar desenvolvimento imediatamente
"""

from pathlib import Path
import sys

# Add module to path
sys.path.append(str(Path(__file__).parent))

from config.settings import CLAUDE_CONFIG, EMAIL_SETTINGS, PROCESSING_CONFIG
from integration import MainSystemIntegrator
from models.invoice import Invoice, InvoiceVendor, InvoiceStatus

class InvoiceProcessingStarter:
    """
    Template de início rápido para desenvolvimento de invoice processing
    """

    def __init__(self):
        self.integrator = MainSystemIntegrator()
        print("Invoice Processing Module - Started")

    def test_database_connection(self):
        """Testar conexão com banco de dados"""
        try:
            self.integrator.create_invoice_tables()
            print("Database connection OK")
            return True
        except Exception as e:
            print(f"Database error: {e}")
            return False

    def test_claude_api(self):
        """Testar Claude API"""
        try:
            import anthropic
            if CLAUDE_CONFIG['API_KEY']:
                client = anthropic.Anthropic(api_key=CLAUDE_CONFIG['API_KEY'])
                print("Claude API key configured")
                return True
            else:
                print("Claude API key not configured")
                return False
        except Exception as e:
            print(f"Claude API error: {e}")
            return False

    def test_email_config(self):
        """Testar configuração de email"""
        if EMAIL_SETTINGS['EMAIL_ADDRESS'] and EMAIL_SETTINGS['EMAIL_PASSWORD']:
            print("Email configuration OK")
            return True
        else:
            print("Email not configured - set INVOICE_EMAIL and INVOICE_EMAIL_PASSWORD")
            return False

    def create_sample_invoice(self):
        """Criar uma invoice de exemplo"""
        try:
            # Criar vendor
            vendor = InvoiceVendor(
                name="AWS - Amazon Web Services",
                address="Seattle, WA",
                tax_id="91-1646860"
            )

            # Criar invoice
            invoice = Invoice(
                invoice_number="AWS-2024-001",
                date=__import__('datetime').date.today(),
                vendor=vendor,
                total_amount=__import__('decimal').Decimal('150.75'),
                currency="USD",
                status=InvoiceStatus.COMPLETED,
                business_unit="Delta LLC",
                category="Technology Expenses",
                processing_notes="Sample invoice created via starter template"
            )

            # Salvar no banco
            invoice_id = self.integrator.save_invoice(invoice.to_dict())
            print(f"Sample invoice created: {invoice_id}")
            return invoice_id

        except Exception as e:
            print(f"Sample invoice creation failed: {e}")
            return None

    def list_invoices(self):
        """Listar invoices existentes"""
        try:
            invoices = self.integrator.get_invoices(limit=10)
            print(f"Found {len(invoices)} invoices:")
            for invoice in invoices:
                print(f"  - {invoice['invoice_number']}: {invoice['vendor_name']} (${invoice['total_amount']})")
            return invoices
        except Exception as e:
            print(f"Failed to list invoices: {e}")
            return []

    def run_system_check(self):
        """Executar verificação completa do sistema"""
        print("\n" + "="*50)
        print("INVOICE PROCESSING - SYSTEM CHECK")
        print("="*50)

        checks = [
            ("Database Connection", self.test_database_connection),
            ("Claude API", self.test_claude_api),
            ("Email Configuration", self.test_email_config),
        ]

        results = {}
        for check_name, check_func in checks:
            print(f"\n{check_name}...")
            results[check_name] = check_func()

        print(f"\nRESULTS:")
        for check_name, result in results.items():
            status = "PASS" if result else "FAIL"
            print(f"  {check_name}: {status}")

        # If basic checks pass, create sample data
        if results["Database Connection"]:
            print(f"\nCreating sample data...")
            self.create_sample_invoice()
            self.list_invoices()

        print(f"\nNEXT STEPS:")
        print(f"  1. Configure environment variables (API keys, email)")
        print(f"  2. Implement core/email_monitor.py")
        print(f"  3. Implement core/pdf_processor.py")
        print(f"  4. Implement services/claude_vision.py")
        print(f"  5. Run: python starter_template.py")

        return all(results.values())

def main():
    """Main function para teste rápido"""
    starter = InvoiceProcessingStarter()
    starter.run_system_check()

if __name__ == "__main__":
    main()