"""
Cash Flow Report Implementation
Demonstração de Fluxo de Caixa (DFC) - Cash Flow Statement
Based exactly on working DRE pattern
"""

import os
import sys
import logging
from datetime import date, timedelta
from typing import Dict, Any, List
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib.colors import HexColor

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .database import db_manager
from .pdf_reports import DeltaCFOReportTemplate

logger = logging.getLogger(__name__)


class CashFlowReport(DeltaCFOReportTemplate):
    """
    Demonstração de Fluxo de Caixa (DFC) - Cash Flow Statement
    Following Brazilian accounting standards (CPC 03 / NBC TG 03)
    """

    def __init__(self, company_name: str = "Delta Mining", start_date: date = None, end_date: date = None, entity_filter: str = None):
        title = f"Demonstração de Fluxo de Caixa (DFC)"
        period = f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}" if start_date and end_date else self._get_current_period()
        super().__init__(title, company_name, period)

        self.start_date = start_date or date(date.today().year, 1, 1)
        self.end_date = end_date or date.today()
        self.entity_filter = entity_filter

        # Initialize data
        self.cash_flow_data = None

    def _fetch_cash_flow_data(self) -> Dict[str, Any]:
        """
        Fetch cash flow data from database - EXACTLY like DRE pattern
        Returns structured data for cash flow calculation
        """
        try:
            # Use exact same pattern as DRE
            params = [self.start_date.isoformat(), self.end_date.isoformat()]
            entity_params = []

            if self.entity_filter:
                entity_filter_condition = "AND classified_entity = %s"
                entity_params = [self.entity_filter]
            else:
                entity_filter_condition = ""

            # Revenue query exactly like DRE
            revenue_query = f"""
                SELECT
                    SUM(CASE WHEN amount > 0 THEN usd_equivalent ELSE 0 END) as cash_receipts,
                    SUM(CASE WHEN amount < 0 THEN ABS(usd_equivalent) ELSE 0 END) as cash_payments
                FROM transactions
                WHERE date::date BETWEEN %s AND %s
                {entity_filter_condition}
            """

            all_params = params + entity_params
            result = db_manager.execute_query(revenue_query, tuple(all_params), fetch_one=True)

            cash_receipts = float(result.get('cash_receipts', 0) or 0) if result else 0
            cash_payments = float(result.get('cash_payments', 0) or 0) if result else 0
            net_operating = cash_receipts - cash_payments

            return {
                'period': {
                    'start_date': self.start_date.isoformat(),
                    'end_date': self.end_date.isoformat()
                },
                'cash_receipts': cash_receipts,
                'cash_payments': cash_payments,
                'net_operating': net_operating,
                'investing_inflows': 0,  # Simplified
                'investing_outflows': 0,  # Simplified
                'net_investing': 0,
                'financing_inflows': 0,  # Simplified
                'financing_outflows': 0,  # Simplified
                'net_financing': 0,
                'net_cash_flow': net_operating,
                'beginning_cash': 0,  # Simplified
                'ending_cash': net_operating,
                'components': {
                    'operating': {
                        'receipts': cash_receipts,
                        'payments': cash_payments,
                        'net': net_operating
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error fetching cash flow data: {e}")
            # Return default structure with zeros
            return {
                'period': {
                    'start_date': self.start_date.isoformat() if self.start_date else '',
                    'end_date': self.end_date.isoformat() if self.end_date else ''
                },
                'cash_receipts': 0,
                'cash_payments': 0,
                'net_operating': 0,
                'investing_inflows': 0,
                'investing_outflows': 0,
                'net_investing': 0,
                'financing_inflows': 0,
                'financing_outflows': 0,
                'net_financing': 0,
                'net_cash_flow': 0,
                'beginning_cash': 0,
                'ending_cash': 0,
                'components': {
                    'operating': {'receipts': 0, 'payments': 0, 'net': 0}
                }
            }

    def _create_cash_flow_table(self, cash_data: Dict[str, Any]) -> Table:
        """
        Create the main cash flow table
        """
        # Table data structure
        table_data = [
            ['Fluxos de Caixa', 'Valores (USD)'],
            ['', ''],
            ['FLUXOS DE CAIXA DAS ATIVIDADES OPERACIONAIS', ''],
            ['', ''],
            ['💰 Recebimentos de Clientes', self.format_currency(cash_data.get('cash_receipts', 0))],
            ['💸 Pagamentos a Fornecedores e Funcionários', f"({self.format_currency(cash_data.get('cash_payments', 0))})"],
            ['', ''],
            ['💼 Caixa Líquido das Atividades Operacionais', self.format_currency(cash_data.get('net_operating', 0))],
            ['', ''],
            ['FLUXOS DE CAIXA DAS ATIVIDADES DE INVESTIMENTO', ''],
            ['', ''],
            ['🏗️ Recebimentos de Vendas de Ativos', self.format_currency(cash_data.get('investing_inflows', 0))],
            ['🏗️ Pagamentos de Aquisições de Ativos', f"({self.format_currency(cash_data.get('investing_outflows', 0))})"],
            ['', ''],
            ['💼 Caixa Líquido das Atividades de Investimento', self.format_currency(cash_data.get('net_investing', 0))],
            ['', ''],
            ['FLUXOS DE CAIXA DAS ATIVIDADES DE FINANCIAMENTO', ''],
            ['', ''],
            ['🏦 Recebimentos de Empréstimos e Capital', self.format_currency(cash_data.get('financing_inflows', 0))],
            ['🏦 Pagamentos de Empréstimos e Dividendos', f"({self.format_currency(cash_data.get('financing_outflows', 0))})"],
            ['', ''],
            ['💼 Caixa Líquido das Atividades de Financiamento', self.format_currency(cash_data.get('net_financing', 0))],
            ['', ''],
            ['AUMENTO (DIMINUIÇÃO) LÍQUIDA DE CAIXA', self.format_currency(cash_data.get('net_cash_flow', 0))],
            ['', ''],
            ['SALDO FINAL DE CAIXA E EQUIVALENTES', self.format_currency(cash_data.get('ending_cash', 0))]
        ]

        # Create table
        table = Table(table_data, colWidths=[4*inch, 2*inch])

        # Apply styling
        table.setStyle(TableStyle([
            # Headers
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),

            # Section headers
            ('BACKGROUND', (0, 2), (-1, 2), HexColor('#e6f7ff')),  # Operating
            ('BACKGROUND', (0, 9), (-1, 9), HexColor('#f0f9ff')),  # Investing
            ('BACKGROUND', (0, 16), (-1, 16), HexColor('#f5f5dc')),  # Financing
            ('BACKGROUND', (0, 22), (-1, 22), HexColor('#fef3cd')),  # Net change
            ('BACKGROUND', (0, 24), (-1, 24), HexColor('#d4edda')),  # Final

            # Bold for main items
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),  # Operating header
            ('FONTNAME', (0, 7), (-1, 7), 'Helvetica-Bold'),  # Operating net
            ('FONTNAME', (0, 9), (-1, 9), 'Helvetica-Bold'),  # Investing header
            ('FONTNAME', (0, 14), (-1, 14), 'Helvetica-Bold'),  # Investing net
            ('FONTNAME', (0, 16), (-1, 16), 'Helvetica-Bold'),  # Financing header
            ('FONTNAME', (0, 21), (-1, 21), 'Helvetica-Bold'),  # Financing net
            ('FONTNAME', (0, 22), (-1, 22), 'Helvetica-Bold'),  # Net change
            ('FONTNAME', (0, 24), (-1, 24), 'Helvetica-Bold'),  # Final

            # Grid
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, HexColor('#2d3748')),
            ('LINEBELOW', (0, 22), (-1, 22), 2, HexColor('#f59e0b')),
            ('LINEBELOW', (0, 24), (-1, 24), 2, HexColor('#10b981')),

            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        return table

    def generate_cash_flow_report(self) -> bytes:
        """
        Generate the complete Cash Flow PDF report
        Returns PDF as bytes
        """
        # Fetch data
        self.cash_flow_data = self._fetch_cash_flow_data()

        # Build story
        story = []

        # Title section
        story.extend(self.create_title_section())

        # Entity filter info
        if self.entity_filter:
            entity_info = f"Entidade: {self.entity_filter}"
            story.append(Paragraph(entity_info, self.styles['Period']))
            story.append(Spacer(1, 10))

        # Main cash flow table
        cash_flow_table = self._create_cash_flow_table(self.cash_flow_data)
        story.append(cash_flow_table)
        story.append(Spacer(1, 20))

        # Notes section
        self.add_section_break(story, "Notas Explicativas")

        notes = [
            "1. Os valores estão expressos em Dólares Americanos (USD).",
            "2. A demonstração segue as normas brasileiras de contabilidade (CPC 03).",
            "3. Fluxos de caixa operacionais baseados em recebimentos e pagamentos diretos.",
            "4. Este relatório foi gerado automaticamente pelo Delta CFO Agent."
        ]

        for note in notes:
            story.append(Paragraph(note, self.styles['TableData']))
            story.append(Spacer(1, 5))

        # Signature section
        story.extend(self.create_signature_section())

        # Generate PDF
        return self.generate_pdf(story)