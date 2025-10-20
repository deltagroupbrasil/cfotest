#!/usr/bin/env python3
"""
Invoice Generation Service with PDF Output
Generates professional crypto invoices with QR codes and payment instructions
"""

import os
import sys
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import qrcode
from io import BytesIO
import base64

# Try to import ReportLab for PDF generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("WARNING: ReportLab not installed. PDF generation will be limited.")


class InvoiceGenerator:
    """Generate professional crypto invoices with QR codes"""

    def __init__(self, output_dir: str = "generated_invoices"):
        """
        Initialize invoice generator

        Args:
            output_dir: Directory to save generated invoices
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "qr_codes"), exist_ok=True)

    def generate_invoice_number(self, date_obj: date = None) -> str:
        """
        Generate unique invoice number in format DPY-YYYY-MM-####

        Args:
            date_obj: Invoice date (defaults to today)

        Returns:
            Invoice number string
        """
        if not date_obj:
            date_obj = date.today()

        # Generate sequential number based on year and month
        year_month = date_obj.strftime("%Y-%m")
        sequence = self._get_next_sequence_number(year_month)

        return f"DPY-{year_month}-{sequence:04d}"

    def _get_next_sequence_number(self, year_month: str) -> int:
        """Get next sequence number for invoice numbering"""
        # In production, this should query the database for the last invoice number
        # For now, use a simple timestamp-based approach
        return int(datetime.now().strftime("%H%M"))

    def generate_qr_code(self, data: str, filename: str = None) -> str:
        """
        Generate QR code for payment address

        Args:
            data: Data to encode (payment address or payment URI)
            filename: Optional filename for QR code image

        Returns:
            Path to generated QR code image
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        if not filename:
            filename = f"qr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        qr_path = os.path.join(self.output_dir, "qr_codes", filename)
        img.save(qr_path)

        return qr_path

    def create_payment_uri(self, currency: str, address: str, amount: float,
                          label: str = None, message: str = None) -> str:
        """
        Create payment URI for QR code

        Args:
            currency: Cryptocurrency (BTC, USDT, etc.)
            address: Payment address
            amount: Amount to request
            label: Optional label
            message: Optional message

        Returns:
            Payment URI string
        """
        # Bitcoin BIP21 format: bitcoin:address?amount=X&label=Y&message=Z
        # For other cryptos, adapt format accordingly

        if currency == "BTC":
            uri = f"bitcoin:{address}?amount={amount}"
        elif currency.startswith("USDT"):
            # USDT doesn't have standard URI, use address
            return address
        elif currency == "TAO":
            # TAO format (adjust based on Bittensor standards)
            return address
        else:
            return address

        if label:
            uri += f"&label={label}"
        if message:
            uri += f"&message={message}"

        return uri

    def calculate_crypto_amount(self, usd_amount: float, crypto_price: float) -> float:
        """
        Calculate cryptocurrency amount from USD

        Args:
            usd_amount: Amount in USD
            crypto_price: Current price of crypto in USD

        Returns:
            Amount in cryptocurrency
        """
        return round(usd_amount / crypto_price, 8)

    def generate_pdf_invoice(self, invoice_data: Dict[str, Any]) -> str:
        """
        Generate PDF invoice

        Args:
            invoice_data: Dictionary containing all invoice information
                {
                    "invoice_number": "DPY-2025-10-0001",
                    "client_name": "Alps Blockchain",
                    "client_contact": "ops@alpsblockchain.com",
                    "issue_date": "2025-10-01",
                    "due_date": "2025-10-08",
                    "amount_usd": 5000.00,
                    "crypto_currency": "USDT",
                    "crypto_network": "TRC20",
                    "crypto_amount": 5000.25,
                    "exchange_rate": 0.9995,
                    "deposit_address": "TXyz123...",
                    "memo_tag": null,
                    "billing_period": "October 2025",
                    "description": "Bitcoin Mining Colocation Services",
                    "line_items": [
                        {"description": "Power consumption (1000 kWh @ $0.08)", "amount": 80.00},
                        {"description": "Hosting fees", "amount": 4920.00}
                    ],
                    "qr_code_path": "/path/to/qr.png",
                    "notes": "Payment must be made to the exact address shown above."
                }

        Returns:
            Path to generated PDF file
        """
        if not REPORTLAB_AVAILABLE:
            return self._generate_simple_text_invoice(invoice_data)

        pdf_filename = f"{invoice_data['invoice_number']}.pdf"
        pdf_path = os.path.join(self.output_dir, pdf_filename)

        # Create PDF document
        doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                               rightMargin=0.5*inch, leftMargin=0.5*inch,
                               topMargin=0.5*inch, bottomMargin=0.5*inch)

        # Container for PDF elements
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            spaceBefore=12
        )

        normal_style = styles['Normal']
        small_style = ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666')
        )

        # Title
        title = Paragraph("CRYPTO INVOICE", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))

        # Company header
        company_info = [
            ["<b>Delta Energy - Paraguay Operations</b>", f"<b>Invoice #:</b> {invoice_data['invoice_number']}"],
            ["Asunción, Paraguay", f"<b>Issue Date:</b> {invoice_data['issue_date']}"],
            ["Email: billing@deltaenergy.com", f"<b>Due Date:</b> {invoice_data['due_date']}"]
        ]

        company_table = Table(company_info, colWidths=[3.5*inch, 3.5*inch])
        company_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('FONT', (0, 0), (0, 0), 'Helvetica-Bold', 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        elements.append(company_table)
        elements.append(Spacer(1, 0.3*inch))

        # Bill to section
        elements.append(Paragraph("<b>BILL TO:</b>", heading_style))
        bill_to_data = [
            [invoice_data['client_name']],
            [invoice_data.get('client_contact', '')],
        ]
        bill_to_table = Table(bill_to_data, colWidths=[7*inch])
        bill_to_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('FONT', (0, 0), (0, 0), 'Helvetica-Bold', 11),
        ]))
        elements.append(bill_to_table)
        elements.append(Spacer(1, 0.2*inch))

        # Service description
        if invoice_data.get('billing_period'):
            desc = Paragraph(f"<b>Billing Period:</b> {invoice_data['billing_period']}", normal_style)
            elements.append(desc)
            elements.append(Spacer(1, 0.1*inch))

        if invoice_data.get('description'):
            desc = Paragraph(f"<b>Description:</b> {invoice_data['description']}", normal_style)
            elements.append(desc)
            elements.append(Spacer(1, 0.2*inch))

        # Line items table
        if invoice_data.get('line_items'):
            elements.append(Paragraph("<b>LINE ITEMS:</b>", heading_style))

            line_items_data = [["Description", "Amount (USD)"]]
            for item in invoice_data['line_items']:
                line_items_data.append([
                    item['description'],
                    f"${item['amount']:,.2f}"
                ])

            # Add total row
            line_items_data.append(["<b>TOTAL</b>", f"<b>${invoice_data['amount_usd']:,.2f}</b>"])

            line_items_table = Table(line_items_data, colWidths=[5*inch, 2*inch])
            line_items_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
                ('FONT', (0, 0), (1, 0), 'Helvetica-Bold', 10),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0e0e0')),
                ('GRID', (0, 0), (-1, -2), 1, colors.HexColor('#cccccc')),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#333333')),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(line_items_table)
            elements.append(Spacer(1, 0.3*inch))

        # Payment instructions section
        elements.append(Paragraph("<b>PAYMENT INSTRUCTIONS:</b>", heading_style))

        network_display = invoice_data['crypto_network']
        if invoice_data['crypto_currency'] == "USDT":
            network_display = f"USDT ({invoice_data['crypto_network']})"

        payment_info_data = [
            ["Currency:", f"{network_display}"],
            ["Amount to Pay:", f"{invoice_data['crypto_amount']} {invoice_data['crypto_currency']}"],
            ["USD Equivalent:", f"${invoice_data['amount_usd']:,.2f}"],
            ["Exchange Rate:", f"1 {invoice_data['crypto_currency']} = ${invoice_data['exchange_rate']:.4f}"],
        ]

        payment_info_table = Table(payment_info_data, colWidths=[1.5*inch, 5.5*inch])
        payment_info_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(payment_info_table)
        elements.append(Spacer(1, 0.2*inch))

        # Deposit address box
        address_para = Paragraph(
            f"<b>DEPOSIT ADDRESS:</b><br/>"
            f"<font size=12 face='Courier'>{invoice_data['deposit_address']}</font>",
            normal_style
        )
        elements.append(address_para)

        if invoice_data.get('memo_tag'):
            memo_para = Paragraph(
                f"<b>MEMO/TAG:</b> <font face='Courier'>{invoice_data['memo_tag']}</font>",
                normal_style
            )
            elements.append(Spacer(1, 0.1*inch))
            elements.append(memo_para)

        elements.append(Spacer(1, 0.2*inch))

        # QR code
        if invoice_data.get('qr_code_path') and os.path.exists(invoice_data['qr_code_path']):
            qr_image = Image(invoice_data['qr_code_path'], width=2*inch, height=2*inch)
            qr_caption = Paragraph("<i>Scan to pay</i>", small_style)
            elements.append(qr_image)
            elements.append(qr_caption)
            elements.append(Spacer(1, 0.2*inch))

        # Important notes
        warning_style = ParagraphStyle(
            'Warning',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#cc0000'),
            spaceBefore=6,
            spaceAfter=6
        )

        warning = Paragraph(
            "<b>⚠ IMPORTANT:</b> Payment must be made to the EXACT address shown above. "
            "Amount should match within 0.5% tolerance. Only send on the specified network. "
            "Incorrect network or address may result in permanent loss of funds.",
            warning_style
        )
        elements.append(warning)
        elements.append(Spacer(1, 0.2*inch))

        # Additional notes
        if invoice_data.get('notes'):
            notes_para = Paragraph(f"<b>Notes:</b><br/>{invoice_data['notes']}", small_style)
            elements.append(notes_para)

        # Footer
        elements.append(Spacer(1, 0.3*inch))
        footer_text = (
            "For questions or support, please contact billing@deltaenergy.com<br/>"
            "Thank you for your business!"
        )
        footer = Paragraph(footer_text, small_style)
        elements.append(footer)

        # Build PDF
        doc.build(elements)

        return pdf_path

    def _generate_simple_text_invoice(self, invoice_data: Dict[str, Any]) -> str:
        """
        Generate simple text-based invoice when ReportLab not available

        Args:
            invoice_data: Invoice information

        Returns:
            Path to text file
        """
        txt_filename = f"{invoice_data['invoice_number']}.txt"
        txt_path = os.path.join(self.output_dir, txt_filename)

        with open(txt_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("CRYPTO INVOICE\n")
            f.write("Delta Energy - Paraguay Operations\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Invoice Number: {invoice_data['invoice_number']}\n")
            f.write(f"Issue Date: {invoice_data['issue_date']}\n")
            f.write(f"Due Date: {invoice_data['due_date']}\n\n")

            f.write(f"BILL TO:\n")
            f.write(f"  {invoice_data['client_name']}\n")
            if invoice_data.get('client_contact'):
                f.write(f"  {invoice_data['client_contact']}\n")
            f.write("\n")

            if invoice_data.get('billing_period'):
                f.write(f"Billing Period: {invoice_data['billing_period']}\n")
            if invoice_data.get('description'):
                f.write(f"Description: {invoice_data['description']}\n")
            f.write("\n")

            if invoice_data.get('line_items'):
                f.write("LINE ITEMS:\n")
                f.write("-" * 80 + "\n")
                for item in invoice_data['line_items']:
                    f.write(f"  {item['description']:<60} ${item['amount']:>10,.2f}\n")
                f.write("-" * 80 + "\n")
                f.write(f"  {'TOTAL':<60} ${invoice_data['amount_usd']:>10,.2f}\n\n")

            f.write("PAYMENT INSTRUCTIONS:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Currency: {invoice_data['crypto_currency']} ({invoice_data['crypto_network']})\n")
            f.write(f"Amount to Pay: {invoice_data['crypto_amount']} {invoice_data['crypto_currency']}\n")
            f.write(f"USD Equivalent: ${invoice_data['amount_usd']:,.2f}\n")
            f.write(f"Exchange Rate: 1 {invoice_data['crypto_currency']} = ${invoice_data['exchange_rate']:.4f}\n\n")

            f.write(f"DEPOSIT ADDRESS:\n")
            f.write(f"  {invoice_data['deposit_address']}\n\n")

            if invoice_data.get('memo_tag'):
                f.write(f"MEMO/TAG: {invoice_data['memo_tag']}\n\n")

            f.write("⚠ IMPORTANT:\n")
            f.write("Payment must be made to the EXACT address shown above.\n")
            f.write("Amount should match within 0.5% tolerance.\n")
            f.write("Only send on the specified network.\n\n")

            if invoice_data.get('notes'):
                f.write(f"Notes: {invoice_data['notes']}\n\n")

            f.write("=" * 80 + "\n")
            f.write("For questions: billing@deltaenergy.com\n")
            f.write("Thank you for your business!\n")

        return txt_path

    def get_crypto_price(self, currency: str, network: str = None) -> float:
        """
        Get current crypto price in USD
        In production, this should integrate with CoinGecko or similar API

        Args:
            currency: Cryptocurrency code
            network: Network type (for USDT variants)

        Returns:
            Price in USD
        """
        # Placeholder prices - integrate with crypto_pricing.py or external API
        default_prices = {
            "BTC": 45000.00,
            "USDT": 0.9995,  # Stablecoin ~$1
            "TAO": 450.00
        }

        return default_prices.get(currency, 1.0)
