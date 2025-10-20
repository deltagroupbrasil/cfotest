#!/usr/bin/env python3
"""
Create Test PDF Invoice
Cria um PDF de fatura para teste do sistema
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from datetime import datetime, timedelta
import os

def create_test_invoice_pdf(filename="test_invoice.pdf"):
    """Create a test invoice PDF"""

    # Create PDF canvas
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 80, "INVOICE")

    # Invoice details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 120, "Invoice Number: INV-2024-002")
    c.drawString(50, height - 140, "Date: September 25, 2024")
    c.drawString(50, height - 160, "Due Date: October 25, 2024")

    # From section
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 200, "FROM:")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 220, "Coinbase Inc.")
    c.drawString(50, height - 240, "Cryptocurrency Exchange")
    c.drawString(50, height - 260, "San Francisco, CA 94103")

    # To section
    c.setFont("Helvetica-Bold", 14)
    c.drawString(350, height - 200, "BILL TO:")
    c.setFont("Helvetica", 12)
    c.drawString(350, height - 220, "Delta Prop Shop LLC")
    c.drawString(350, height - 240, "Trading Operations")
    c.drawString(350, height - 260, "Delaware, USA")

    # Services table header
    y_pos = height - 320
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_pos, "DESCRIPTION")
    c.drawString(300, y_pos, "QTY")
    c.drawString(350, y_pos, "RATE")
    c.drawString(450, y_pos, "TOTAL")

    # Draw line
    c.line(50, y_pos - 10, 500, y_pos - 10)

    # Services
    c.setFont("Helvetica", 11)
    services = [
        ("Trading Fees - BTC/USD", "1", "$1,250.00", "$1,250.00"),
        ("Trading Fees - ETH/USD", "1", "$875.00", "$875.00"),
        ("Pro Account Monthly Fee", "1", "$30.00", "$30.00"),
        ("API Usage Premium", "1", "$45.00", "$45.00")
    ]

    y_pos -= 30
    for desc, qty, rate, total in services:
        c.drawString(50, y_pos, desc)
        c.drawString(300, y_pos, qty)
        c.drawString(350, y_pos, rate)
        c.drawString(450, y_pos, total)
        y_pos -= 20

    # Totals
    y_pos -= 30
    c.line(400, y_pos, 500, y_pos)

    y_pos -= 20
    c.setFont("Helvetica", 12)
    c.drawString(350, y_pos, "SUBTOTAL:")
    c.drawString(450, y_pos, "$2,200.00")

    y_pos -= 20
    c.drawString(350, y_pos, "TAX (0%):")
    c.drawString(450, y_pos, "$0.00")

    y_pos -= 20
    c.setFont("Helvetica-Bold", 14)
    c.drawString(350, y_pos, "TOTAL:")
    c.drawString(450, y_pos, "$2,200.00")

    # Payment terms
    c.setFont("Helvetica", 10)
    c.drawString(50, y_pos - 60, "Payment Terms: Net 15 days")
    c.drawString(50, y_pos - 80, "Currency: USD")
    c.drawString(50, y_pos - 100, "Thank you for your business!")

    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(50, 50, "Coinbase Inc. - Cryptocurrency Trading Platform")

    # Save PDF
    c.save()
    print(f"Test invoice PDF created: {filename}")

def create_aws_pdf(filename="test_aws_invoice.pdf"):
    """Create AWS-style invoice PDF"""

    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # AWS Header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 60, "Amazon Web Services")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, "Invoice")

    # Invoice details
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, height - 120, "Invoice Number: 123456789")
    c.drawString(50, height - 140, "Invoice Date: 2024-09-25")
    c.drawString(50, height - 160, "Due Date: 2024-10-25")

    # Account info
    c.drawString(350, height - 120, "Account ID: 123456789012")
    c.drawString(350, height - 140, "Bill To: Delta LLC")
    c.drawString(350, height - 160, "Delaware, USA")

    # Services
    y_pos = height - 220
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y_pos, "Service")
    c.drawString(300, y_pos, "Usage")
    c.drawString(450, y_pos, "Cost")

    c.line(50, y_pos - 5, 500, y_pos - 5)

    c.setFont("Helvetica", 10)
    services = [
        ("Amazon Elastic Compute Cloud", "720 Hrs", "$1,440.00"),
        ("Amazon Simple Storage Service", "50 GB", "$115.00"),
        ("Amazon CloudWatch", "Standard Monitoring", "$65.00"),
        ("Data Transfer", "100 GB", "$90.00")
    ]

    y_pos -= 25
    for service, usage, cost in services:
        c.drawString(50, y_pos, service)
        c.drawString(300, y_pos, usage)
        c.drawString(450, y_pos, cost)
        y_pos -= 20

    # Total
    y_pos -= 20
    c.line(400, y_pos, 500, y_pos)
    y_pos -= 15
    c.setFont("Helvetica-Bold", 12)
    c.drawString(400, y_pos, "Total: $1,710.00")

    c.setFont("Helvetica", 9)
    c.drawString(50, 100, "AWS charges are in US Dollars")
    c.drawString(50, 80, "Questions? Visit aws.amazon.com/support")

    c.save()
    print(f"AWS test invoice PDF created: {filename}")

if __name__ == "__main__":
    try:
        # Install reportlab if needed
        from reportlab.lib.pagesizes import letter
        print("Creating test PDFs...")
        create_test_invoice_pdf()
        create_aws_pdf()
        print("Test PDFs created successfully!")
    except ImportError:
        print("Installing reportlab...")
        import subprocess
        subprocess.run(["pip", "install", "reportlab"])
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        create_test_invoice_pdf()
        create_aws_pdf()
        print("Test PDFs created successfully!")