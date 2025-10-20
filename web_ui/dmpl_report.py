"""
DMPL Report Implementation
Demonstração das Mutações do Patrimônio Líquido (DMPL) - Statement of Changes in Equity
"""

import os
import sys
import logging
from datetime import date, timedelta
from decimal import Decimal
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
        Fetch equity movements data from database
        Returns structured data for DMPL calculation
        """
        try:
            # Base date filters
            date_filter = ""
            params = []

            if self.start_date and self.end_date:
                date_filter = "WHERE date::date >= %s::date AND date::date <= %s::date"
                params = [self.start_date.isoformat(), self.end_date.isoformat()]

            # Entity filter
            entity_filter_clause = ""
            if self.entity_filter:
                if date_filter:
                    entity_filter_clause = " AND (classified_entity = %s OR accounting_category = %s)"
                else:
                    entity_filter_clause = " WHERE (classified_entity = %s OR accounting_category = %s)"
                params.extend([self.entity_filter, self.entity_filter])

            # Get capital contributions and distributions
            capital_query = f"""
                SELECT
                    'Capital Contributions' as type,
                    SUM(CASE WHEN amount > 0 THEN usd_equivalent ELSE 0 END) as total_inflows,
                    SUM(CASE WHEN amount < 0 THEN ABS(usd_equivalent) ELSE 0 END) as total_outflows,
                    COUNT(*) as transaction_count
                FROM transactions
                {date_filter}
                {entity_filter_clause}
                AND (
                    LOWER(COALESCE(description, '')) LIKE '%capital%' OR
                    LOWER(COALESCE(description, '')) LIKE '%contribution%' OR
                    LOWER(COALESCE(description, '')) LIKE '%investment%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%equity%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%capital%'
                )
            """

            capital_data = db_manager.execute_query(capital_query, tuple(params), fetch_one=True) or {}

            # Get dividend/distribution transactions
            dividend_query = f"""
                SELECT
                    'Dividends & Distributions' as type,
                    SUM(CASE WHEN amount > 0 THEN usd_equivalent ELSE 0 END) as total_inflows,
                    SUM(CASE WHEN amount < 0 THEN ABS(usd_equivalent) ELSE 0 END) as total_outflows,
                    COUNT(*) as transaction_count
                FROM transactions
                {date_filter}
                {entity_filter_clause}
                AND (
                    LOWER(COALESCE(description, '')) LIKE '%dividend%' OR
                    LOWER(COALESCE(description, '')) LIKE '%distribution%' OR
                    LOWER(COALESCE(description, '')) LIKE '%withdrawal%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%dividend%'
                )
            """

            dividend_data = db_manager.execute_query(dividend_query, tuple(params), fetch_one=True) or {}

            # Get retained earnings (net income calculation)
            revenue_query = f"""
                SELECT
                    SUM(CASE WHEN amount > 0 THEN usd_equivalent ELSE 0 END) as total_revenue,
                    SUM(CASE WHEN amount < 0 THEN ABS(usd_equivalent) ELSE 0 END) as total_expenses
                FROM transactions
                {date_filter}
                {entity_filter_clause}
            """

            pnl_data = db_manager.execute_query(revenue_query, tuple(params), fetch_one=True) or {}

            # Calculate beginning equity (approximate from historical data)
            beginning_date = self.start_date - timedelta(days=1) if self.start_date else date(date.today().year-1, 12, 31)

            beginning_equity_query = f"""
                SELECT
                    COALESCE(SUM(usd_equivalent), 0) as cumulative_equity
                FROM transactions
                WHERE date::date <= %s::date
                {entity_filter_clause.replace('WHERE', 'AND').replace('AND AND', 'AND') if entity_filter_clause else ''}
            """

            beginning_params = [beginning_date.isoformat()]
            if self.entity_filter:
                beginning_params.extend([self.entity_filter, self.entity_filter])

            beginning_data = db_manager.execute_query(beginning_equity_query, tuple(beginning_params), fetch_one=True) or {}

            # Calculate components
            total_revenue = Decimal(str(pnl_data.get('total_revenue', 0) or 0))
            total_expenses = Decimal(str(pnl_data.get('total_expenses', 0) or 0))
            net_income = total_revenue - total_expenses

            capital_inflows = Decimal(str(capital_data.get('total_inflows', 0) or 0))
            capital_outflows = Decimal(str(capital_data.get('total_outflows', 0) or 0))
            net_capital_change = capital_inflows - capital_outflows

            dividend_outflows = Decimal(str(dividend_data.get('total_outflows', 0) or 0))

            beginning_equity = Decimal(str(beginning_data.get('cumulative_equity', 0) or 0))
            ending_equity = beginning_equity + net_income + net_capital_change - dividend_outflows

            return {
                'period': {
                    'start_date': self.start_date.isoformat(),
                    'end_date': self.end_date.isoformat()
                },
                'beginning_equity': float(beginning_equity),
                'net_income': float(net_income),
                'capital_contributions': float(capital_inflows),
                'capital_distributions': float(capital_outflows),
                'dividends_paid': float(dividend_outflows),
                'other_changes': 0,  # Can be expanded for other equity movements
                'ending_equity': float(ending_equity),
                'components': {
                    'total_revenue': float(total_revenue),
                    'total_expenses': float(total_expenses),
                    'capital_transactions': {
                        'inflows': float(capital_inflows),
                        'outflows': float(capital_outflows),
                        'count': capital_data.get('transaction_count', 0)
                    },
                    'dividend_transactions': {
                        'outflows': float(dividend_outflows),
                        'count': dividend_data.get('transaction_count', 0)
                    }
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

    def _create_dmpl_analysis_section(self, dmpl_data: Dict[str, Any]) -> List:
        """
        Create analysis section with key metrics and insights
        """
        content = []

        # Analysis header
        content.append(Paragraph("📊 ANÁLISE DAS MUTAÇÕES PATRIMONIAIS", self.styles['SectionHeader']))
        content.append(Spacer(1, 12))

        # Key metrics
        beginning_equity = dmpl_data.get('beginning_equity', 0)
        ending_equity = dmpl_data.get('ending_equity', 0)
        net_income = dmpl_data.get('net_income', 0)

        # Calculate growth rate
        equity_growth = ((ending_equity - beginning_equity) / beginning_equity * 100) if beginning_equity != 0 else 0

        # Create metrics table
        roe_percentage = (net_income / beginning_equity * 100) if beginning_equity != 0 else 0
        contribution_percentage = (abs(net_income / (ending_equity - beginning_equity)) * 100) if (ending_equity - beginning_equity) != 0 else 0

        metrics_data = [
            ['Métrica', 'Valor', 'Análise'],
            ['Crescimento do Patrimônio', f"{equity_growth:+.1f}%",
             '✅ Crescimento positivo' if equity_growth > 0 else ('⚠️ Decrescimento' if equity_growth < -5 else '➖ Estável')],
            ['Rentabilidade sobre PL Inicial', f"{roe_percentage:.1f}%" if beginning_equity != 0 else "N/A",
             '📈 Boa rentabilidade' if roe_percentage > 15 else '📊 Rentabilidade moderada' if beginning_equity != 0 else 'N/A'],
            ['Contribuição do Resultado', f"{contribution_percentage:.1f}%" if (ending_equity - beginning_equity) != 0 else "N/A",
             '💼 Resultado impulsiona crescimento' if net_income > 0 else '⚠️ Prejuízo impacta patrimônio'],
        ]

        metrics_table = Table(metrics_data, colWidths=[2*inch, 1.5*inch, 2.5*inch])
        metrics_table.setStyle(self._get_default_table_style())
        content.append(metrics_table)
        content.append(Spacer(1, 15))

        # Insights paragraph
        insights = []

        if equity_growth > 10:
            insights.append("• O patrimônio líquido apresentou crescimento significativo no período.")
        elif equity_growth < -10:
            insights.append("• Houve redução considerável no patrimônio líquido.")
        else:
            insights.append("• O patrimônio líquido manteve-se relativamente estável.")

        if net_income > 0:
            insights.append(f"• O resultado positivo de {self.format_currency(net_income)} contribuiu para o fortalecimento patrimonial.")
        else:
            insights.append(f"• O prejuízo de {self.format_currency(abs(net_income))} impactou negativamente o patrimônio.")

        capital_net = dmpl_data.get('capital_contributions', 0) - dmpl_data.get('capital_distributions', 0)
        if capital_net > 0:
            insights.append(f"• Houve aporte líquido de capital no valor de {self.format_currency(capital_net)}.")
        elif capital_net < 0:
            insights.append(f"• Ocorreram retiradas líquidas de capital no valor de {self.format_currency(abs(capital_net))}.")

        if dmpl_data.get('dividends_paid', 0) > 0:
            insights.append(f"• Foram distribuídos dividendos no valor de {self.format_currency(dmpl_data.get('dividends_paid', 0))}.")

        content.append(Paragraph("🔍 Principais Observações:", self.styles['SubHeader']))
        content.append(Spacer(1, 8))

        for insight in insights:
            content.append(Paragraph(insight, self.styles['TableData']))
            content.append(Spacer(1, 4))

        return content

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

        # Analysis section
        story.extend(self._create_dmpl_analysis_section(self.dmpl_data))

        # Notes section
        self.add_section_break(story, "Notas Explicativas")

        notes = [
            "1. Os valores estão expressos em Dólares Americanos (USD).",
            "2. A demonstração segue as normas brasileiras de contabilidade (CPC 26).",
            "3. Patrimônio Líquido inicial baseado em transações históricas acumuladas.",
            "4. Lucro/Prejuízo calculado pela diferença entre receitas e despesas do período.",
            "5. Movimentações de capital incluem aportes e retiradas dos sócios/acionistas.",
            "6. Este relatório foi gerado automaticamente pelo Delta CFO Agent."
        ]

        for note in notes:
            story.append(Paragraph(note, self.styles['TableData']))
            story.append(Spacer(1, 5))

        # Signature section
        story.extend(self.create_signature_section())

        # Generate PDF
        return self.generate_pdf(story)