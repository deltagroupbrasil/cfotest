"""
DMPL Report Implementation
Demonstração das Mutações do Patrimônio Líquido (DMPL) - Statement of Changes in Equity
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


class DMPLReport(DeltaCFOReportTemplate):
    """
    Demonstração das Mutações do Patrimônio Líquido (DMPL) - Statement of Changes in Equity
    Following Brazilian accounting standards (CPC 26 / NBC TG 26)
    """

    def __init__(self, company_name: str = "Delta Mining", start_date: date = None, end_date: date = None, entity_filter: str = None):
        title = f"Demonstração das Mutações do Patrimônio Líquido (DMPL)"
        period = f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}" if start_date and end_date else self._get_current_period()
        super().__init__(title, company_name, period)

        self.start_date = start_date or date(date.today().year, 1, 1)
        self.end_date = end_date or date.today()
        self.entity_filter = entity_filter

        # Initialize data
        self.dmpl_data = None

    def _fetch_equity_data(self) -> Dict[str, Any]:
        """
        Fetch equity movements data from database - EXACTLY like DRE pattern
        Returns structured data for DMPL calculation
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
                    SUM(CASE WHEN amount > 0 THEN usd_equivalent ELSE 0 END) as total_revenue,
                    SUM(CASE WHEN amount < 0 THEN ABS(usd_equivalent) ELSE 0 END) as total_expenses
                FROM transactions
                WHERE date::date BETWEEN %s AND %s
                {entity_filter_condition}
            """

            all_params = params + entity_params
            result = db_manager.execute_query(revenue_query, tuple(all_params), fetch_one=True)

            total_revenue = float(result.get('total_revenue', 0) or 0) if result else 0
            total_expenses = float(result.get('total_expenses', 0) or 0) if result else 0
            net_income = total_revenue - total_expenses

            # Calculate beginning equity (previous year end)
            prev_year_end = date(self.start_date.year - 1, 12, 31)
            beginning_query = f"""
                SELECT
                    SUM(CASE WHEN amount > 0 THEN usd_equivalent ELSE 0 END) -
                    SUM(CASE WHEN amount < 0 THEN ABS(usd_equivalent) ELSE 0 END) as cumulative_equity
                FROM transactions
                WHERE date::date <= %s
                {entity_filter_condition}
            """

            beginning_params = [prev_year_end.isoformat()] + entity_params
            beginning_result = db_manager.execute_query(beginning_query, tuple(beginning_params), fetch_one=True)
            beginning_equity = float(beginning_result.get('cumulative_equity', 0) or 0) if beginning_result else 0

            # Calculate ending equity
            ending_equity = beginning_equity + net_income

            return {
                'period': {
                    'start_date': self.start_date.isoformat(),
                    'end_date': self.end_date.isoformat()
                },
                'beginning_equity': beginning_equity,
                'net_income': net_income,
                'capital_contributions': 0,  # Simplified for now
                'capital_distributions': 0,  # Simplified for now
                'dividends_paid': 0,  # Simplified for now
                'other_changes': 0,
                'ending_equity': ending_equity,
                'components': {
                    'total_revenue': total_revenue,
                    'total_expenses': total_expenses,
                    'capital_transactions': {'inflows': 0, 'outflows': 0, 'count': 0},
                    'dividend_transactions': {'outflows': 0, 'count': 0}
                }
            }

        except Exception as e:
            logger.error(f"Error fetching equity data: {e}")
            # Return default structure with zeros
            return {
                'period': {
                    'start_date': self.start_date.isoformat() if self.start_date else '',
                    'end_date': self.end_date.isoformat() if self.end_date else ''
                },
                'beginning_equity': 0,
                'net_income': 0,
                'capital_contributions': 0,
                'capital_distributions': 0,
                'dividends_paid': 0,
                'other_changes': 0,
                'ending_equity': 0,
                'components': {
                    'total_revenue': 0,
                    'total_expenses': 0,
                    'capital_transactions': {'inflows': 0, 'outflows': 0, 'count': 0},
                    'dividend_transactions': {'outflows': 0, 'count': 0}
                }
            }

    def _create_dmpl_table(self, dmpl_data: Dict[str, Any]) -> Table:
        """
        Create the main DMPL table with equity movements
        """
        # Table data structure
        table_data = [
            ['Componentes', 'Valores (USD)'],
            ['', ''],
            ['PATRIMÔNIO LÍQUIDO - INÍCIO DO PERÍODO', self.format_currency(dmpl_data.get('beginning_equity', 0))],
            ['', ''],
            ['MUTAÇÕES DO PERÍODO:', ''],
            ['', ''],
            ['💰 Lucro/Prejuízo do Exercício', self.format_currency(dmpl_data.get('net_income', 0))],
            ['  • Receitas do Período', self.format_currency(dmpl_data.get('components', {}).get('total_revenue', 0))],
            ['  • Despesas do Período', f"({self.format_currency(dmpl_data.get('components', {}).get('total_expenses', 0))})"],
            ['', ''],
            ['🏦 Movimentações de Capital', ''],
            ['  • Aportes de Capital', self.format_currency(dmpl_data.get('capital_contributions', 0))],
            ['  • Retiradas de Capital', f"({self.format_currency(dmpl_data.get('capital_distributions', 0))})"],
            ['', ''],
            ['💸 Distribuição de Resultados', ''],
            ['  • Dividendos Pagos', f"({self.format_currency(dmpl_data.get('dividends_paid', 0))})"],
            ['  • Outras Distribuições', f"({self.format_currency(dmpl_data.get('other_changes', 0))})"],
            ['', ''],
            ['TOTAL DAS MUTAÇÕES', self.format_currency(
                dmpl_data.get('net_income', 0) +
                dmpl_data.get('capital_contributions', 0) -
                dmpl_data.get('capital_distributions', 0) -
                dmpl_data.get('dividends_paid', 0) -
                dmpl_data.get('other_changes', 0)
            )],
            ['', ''],
            ['PATRIMÔNIO LÍQUIDO - FINAL DO PERÍODO', self.format_currency(dmpl_data.get('ending_equity', 0))]
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

            # Section headers (beginning, mutations, total, ending)
            ('BACKGROUND', (0, 2), (-1, 2), HexColor('#e6f7ff')),  # Beginning
            ('BACKGROUND', (0, 4), (-1, 4), HexColor('#f0f9ff')),  # Mutations header
            ('BACKGROUND', (0, 17), (-1, 17), HexColor('#fef3cd')),  # Total mutations
            ('BACKGROUND', (0, 19), (-1, 19), HexColor('#d4edda')),  # Ending

            # Bold for main items
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),  # Beginning
            ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),  # Mutations
            ('FONTNAME', (0, 6), (-1, 6), 'Helvetica-Bold'),  # Net income
            ('FONTNAME', (0, 10), (-1, 10), 'Helvetica-Bold'),  # Capital
            ('FONTNAME', (0, 14), (-1, 14), 'Helvetica-Bold'),  # Distributions
            ('FONTNAME', (0, 17), (-1, 17), 'Helvetica-Bold'),  # Total
            ('FONTNAME', (0, 19), (-1, 19), 'Helvetica-Bold'),  # Ending

            # Grid
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, HexColor('#2d3748')),
            ('LINEBELOW', (0, 17), (-1, 17), 2, HexColor('#f59e0b')),
            ('LINEBELOW', (0, 19), (-1, 19), 2, HexColor('#10b981')),

            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        return table

    def generate_dmpl_report(self) -> bytes:
        """
        Generate the complete DMPL PDF report
        Returns PDF as bytes
        """
        # Fetch data
        self.dmpl_data = self._fetch_equity_data()

        # Build story
        story = []

        # Title section
        story.extend(self.create_title_section())

        # Entity filter info
        if self.entity_filter:
            entity_info = f"Entidade: {self.entity_filter}"
            story.append(Paragraph(entity_info, self.styles['Period']))
            story.append(Spacer(1, 10))

        # Main DMPL table
        dmpl_table = self._create_dmpl_table(self.dmpl_data)
        story.append(dmpl_table)
        story.append(Spacer(1, 20))

        # Notes section
        self.add_section_break(story, "Notas Explicativas")

        notes = [
            "1. Os valores estão expressos em Dólares Americanos (USD).",
            "2. A demonstração segue as normas brasileiras de contabilidade (CPC 26).",
            "3. Patrimônio Líquido inicial baseado em transações históricas acumuladas.",
            "4. Lucro/Prejuízo calculado pela diferença entre receitas e despesas do período.",
            "5. Este relatório foi gerado automaticamente pelo Delta CFO Agent."
        ]

        for note in notes:
            story.append(Paragraph(note, self.styles['TableData']))
            story.append(Spacer(1, 5))

        # Signature section
        story.extend(self.create_signature_section())

        # Generate PDF
        return self.generate_pdf(story)