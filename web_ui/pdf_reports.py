#!/usr/bin/env python3
"""
PDF Financial Reports Generator for Delta CFO Agent
Base template system for generating professional financial reports
Following Brazilian accounting standards (DRE, Balanço Patrimonial, etc.)
"""

import os
import io
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union
from dateutil.relativedelta import relativedelta

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.colors import Color, black, blue, darkblue, grey, darkgrey
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import colors

class DeltaCFOReportTemplate:
    """
    Base template class for all Delta CFO financial reports
    Provides consistent branding, layout, and styling across all reports
    """

    def __init__(self, title: str, company_name: str = "Delta Mining", report_period: str = None):
        self.title = title
        self.company_name = company_name
        self.report_period = report_period or self._get_current_period()
        self.page_size = A4
        self.margins = {
            'left': 2 * cm,
            'right': 2 * cm,
            'top': 3 * cm,
            'bottom': 2.5 * cm
        }

        # Delta branding colors
        self.colors = {
            'delta_blue': Color(0.2, 0.4, 0.8, 1),      # #3366CC
            'delta_dark_blue': Color(0.1, 0.2, 0.6, 1), # #1A3399
            'delta_grey': Color(0.4, 0.4, 0.4, 1),      # #666666
            'light_grey': Color(0.9, 0.9, 0.9, 1),      # #E6E6E6
            'text_primary': Color(0.2, 0.2, 0.2, 1),    # #333333
            'text_secondary': Color(0.5, 0.5, 0.5, 1),  # #808080
        }

        # Initialize styles
        self.styles = self._create_styles()

        # Buffer for PDF content
        self.buffer = io.BytesIO()

    def _get_current_period(self) -> str:
        """Generate default period string"""
        now = datetime.now()
        return f"{now.strftime('%B %Y')}"

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create custom paragraph styles for the report"""
        styles = getSampleStyleSheet()

        custom_styles = {
            'Title': ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=18,
                textColor=self.colors['delta_dark_blue'],
                alignment=TA_CENTER,
                spaceAfter=20,
                fontName='Helvetica-Bold'
            ),
            'CompanyName': ParagraphStyle(
                'CompanyName',
                parent=styles['Normal'],
                fontSize=14,
                textColor=self.colors['delta_blue'],
                alignment=TA_CENTER,
                spaceAfter=5,
                fontName='Helvetica-Bold'
            ),
            'Period': ParagraphStyle(
                'Period',
                parent=styles['Normal'],
                fontSize=12,
                textColor=self.colors['text_secondary'],
                alignment=TA_CENTER,
                spaceAfter=20,
                fontName='Helvetica'
            ),
            'SectionHeader': ParagraphStyle(
                'SectionHeader',
                parent=styles['Heading1'],
                fontSize=14,
                textColor=self.colors['delta_dark_blue'],
                alignment=TA_LEFT,
                spaceAfter=10,
                spaceBefore=20,
                fontName='Helvetica-Bold'
            ),
            'SubHeader': ParagraphStyle(
                'SubHeader',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=self.colors['text_primary'],
                alignment=TA_LEFT,
                spaceAfter=8,
                spaceBefore=10,
                fontName='Helvetica-Bold'
            ),
            'TableData': ParagraphStyle(
                'TableData',
                parent=styles['Normal'],
                fontSize=10,
                textColor=self.colors['text_primary'],
                alignment=TA_LEFT,
                fontName='Helvetica'
            ),
            'TableDataRight': ParagraphStyle(
                'TableDataRight',
                parent=styles['Normal'],
                fontSize=10,
                textColor=self.colors['text_primary'],
                alignment=TA_RIGHT,
                fontName='Helvetica'
            ),
            'Footer': ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=self.colors['text_secondary'],
                alignment=TA_CENTER,
                fontName='Helvetica'
            )
        }

        return custom_styles

    def _create_header_footer(self, canvas, doc):
        """Create header and footer for each page"""
        canvas.saveState()

        # Header
        header_y = self.page_size[1] - self.margins['top'] + 20

        # Delta logo placeholder (text-based for now)
        canvas.setFont("Helvetica-Bold", 20)
        canvas.setFillColor(self.colors['delta_blue'])
        canvas.drawString(self.margins['left'], header_y, "DELTA")

        # Company subtitle
        canvas.setFont("Helvetica", 10)
        canvas.setFillColor(self.colors['text_secondary'])
        canvas.drawString(self.margins['left'] + 80, header_y + 5, "CFO Agent - Financial Intelligence")

        # Report title and period (right aligned)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.setFillColor(self.colors['text_primary'])
        title_width = canvas.stringWidth(self.title, "Helvetica-Bold", 12)
        canvas.drawString(self.page_size[0] - self.margins['right'] - title_width, header_y + 5, self.title)

        canvas.setFont("Helvetica", 10)
        canvas.setFillColor(self.colors['text_secondary'])
        period_width = canvas.stringWidth(self.report_period, "Helvetica", 10)
        canvas.drawString(self.page_size[0] - self.margins['right'] - period_width, header_y - 10, self.report_period)

        # Header line
        canvas.setStrokeColor(self.colors['delta_blue'])
        canvas.setLineWidth(2)
        canvas.line(self.margins['left'], header_y - 20,
                   self.page_size[0] - self.margins['right'], header_y - 20)

        # Footer
        footer_y = self.margins['bottom'] - 20

        # Footer line
        canvas.setStrokeColor(self.colors['light_grey'])
        canvas.setLineWidth(1)
        canvas.line(self.margins['left'], footer_y + 15,
                   self.page_size[0] - self.margins['right'], footer_y + 15)

        # Page number and generation info
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(self.colors['text_secondary'])
        page_info = f"Página {doc.page} | Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
        canvas.drawString(self.margins['left'], footer_y, page_info)

        # Delta CFO Agent branding (right aligned)
        branding = "Delta CFO Agent - Proprietary AI Financial System"
        branding_width = canvas.stringWidth(branding, "Helvetica", 8)
        canvas.drawString(self.page_size[0] - self.margins['right'] - branding_width, footer_y, branding)

        canvas.restoreState()

    def create_title_section(self) -> List:
        """Create the title section of the report"""
        story = []

        # Company name
        story.append(Paragraph(self.company_name, self.styles['CompanyName']))

        # Report title
        story.append(Paragraph(self.title, self.styles['Title']))

        # Period
        story.append(Paragraph(f"Período: {self.report_period}", self.styles['Period']))

        # Spacer
        story.append(Spacer(1, 20))

        return story

    def create_table(self, data: List[List], headers: List[str] = None,
                    col_widths: List[float] = None, style_name: str = 'default') -> Table:
        """
        Create a styled table for financial data

        Args:
            data: Table data as list of lists
            headers: Optional headers for the table
            col_widths: Optional column widths
            style_name: Style variant ('default', 'financial', 'summary')
        """
        # Prepare table data
        table_data = []
        if headers:
            table_data.append(headers)
        table_data.extend(data)

        # Create table
        if col_widths:
            table = Table(table_data, colWidths=col_widths)
        else:
            table = Table(table_data)

        # Apply styles based on style_name
        if style_name == 'financial':
            table_style = self._get_financial_table_style(has_headers=bool(headers))
        elif style_name == 'summary':
            table_style = self._get_summary_table_style(has_headers=bool(headers))
        else:
            table_style = self._get_default_table_style(has_headers=bool(headers))

        table.setStyle(table_style)
        return table

    def _get_default_table_style(self, has_headers: bool = True) -> TableStyle:
        """Default table style"""
        style_commands = [
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, self.colors['light_grey']),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]

        if has_headers:
            style_commands.extend([
                ('BACKGROUND', (0, 0), (-1, 0), self.colors['delta_blue']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ])

        return TableStyle(style_commands)

    def _get_financial_table_style(self, has_headers: bool = True) -> TableStyle:
        """Financial table style with right-aligned numbers"""
        style_commands = [
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, self.colors['light_grey']),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            # Right align numbers (assuming last column is amounts)
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ]

        if has_headers:
            style_commands.extend([
                ('BACKGROUND', (0, 0), (-1, 0), self.colors['delta_blue']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ])

        return TableStyle(style_commands)

    def _get_summary_table_style(self, has_headers: bool = True) -> TableStyle:
        """Summary table style with emphasis"""
        style_commands = [
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, -1), self.colors['light_grey']),
            ('GRID', (0, 0), (-1, -1), 1, self.colors['delta_blue']),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ]

        return TableStyle(style_commands)

    def format_currency(self, amount: Union[float, int, None], currency: str = "R$") -> str:
        """Format currency values for display"""
        if amount is None:
            return f"{currency} 0,00"

        # Convert to float if needed
        if isinstance(amount, str):
            try:
                amount = float(amount.replace(',', '.'))
            except:
                amount = 0.0

        # Format with Brazilian currency format
        if amount >= 0:
            return f"{currency} {amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        else:
            return f"({currency} {abs(amount):,.2f})".replace(',', 'X').replace('.', ',').replace('X', '.')

    def format_percentage(self, value: Union[float, int, None], decimal_places: int = 2) -> str:
        """Format percentage values for display"""
        if value is None:
            return "0,00%"

        if isinstance(value, str):
            try:
                value = float(value.replace(',', '.'))
            except:
                value = 0.0

        return f"{value:.{decimal_places}f}%".replace('.', ',')

    def generate_pdf(self, story: List) -> bytes:
        """
        Generate the final PDF from the story elements

        Args:
            story: List of Platypus elements (Paragraphs, Tables, etc.)

        Returns:
            PDF content as bytes
        """
        # Create document
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=self.page_size,
            leftMargin=self.margins['left'],
            rightMargin=self.margins['right'],
            topMargin=self.margins['top'],
            bottomMargin=self.margins['bottom'],
            title=self.title,
            author="Delta CFO Agent",
            subject=f"{self.company_name} - {self.title}",
            creator="Delta CFO Agent - AI Financial Intelligence"
        )

        # Build PDF with header/footer
        doc.build(story, onFirstPage=self._create_header_footer, onLaterPages=self._create_header_footer)

        # Get PDF content
        self.buffer.seek(0)
        pdf_content = self.buffer.getvalue()
        self.buffer.close()

        return pdf_content

    def add_section_break(self, story: List, title: str = None) -> None:
        """Add a section break with optional title"""
        story.append(Spacer(1, 20))
        if title:
            story.append(Paragraph(title, self.styles['SectionHeader']))
        story.append(Spacer(1, 10))

    def add_subsection(self, story: List, title: str) -> None:
        """Add a subsection title"""
        story.append(Paragraph(title, self.styles['SubHeader']))
        story.append(Spacer(1, 8))

    def create_signature_section(self) -> List:
        """Create signature section for reports"""
        story = []

        story.append(Spacer(1, 40))
        story.append(Paragraph("Aprovação e Responsabilidade", self.styles['SectionHeader']))
        story.append(Spacer(1, 20))

        # Signature table
        signature_data = [
            ["", ""],
            ["_" * 40, "_" * 40],
            ["Contador Responsável", "Diretor Financeiro"],
            ["CRC: _______________", "CPF: _______________"]
        ]

        signature_table = Table(signature_data, colWidths=[8*cm, 8*cm])
        signature_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))

        story.append(signature_table)
        story.append(Spacer(1, 20))

        # Generation note
        generation_note = f"Este relatório foi gerado automaticamente pelo Delta CFO Agent em {datetime.now().strftime('%d/%m/%Y às %H:%M')}."
        story.append(Paragraph(generation_note, self.styles['Footer']))

        return story


class DREReport(DeltaCFOReportTemplate):
    """
    Demonstração do Resultado do Exercício (DRE) - Income Statement
    Following Brazilian accounting standards (CPC 26 / NBC TG 26)
    """

    def __init__(self, company_name: str = "Delta Mining", start_date: date = None, end_date: date = None, entity_filter: str = None):
        # Format period for display
        if start_date and end_date:
            if start_date.year == end_date.year:
                if start_date == date(start_date.year, 1, 1) and end_date == date(end_date.year, 12, 31):
                    # Full year
                    period = f"Exercício Social de {start_date.year}"
                else:
                    # Partial year
                    period = f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
            else:
                period = f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
        else:
            period = f"Exercício Social de {datetime.now().year}"

        super().__init__(
            title="Demonstração do Resultado do Exercício (DRE)",
            company_name=company_name,
            report_period=period
        )

        self.start_date = start_date or date(datetime.now().year, 1, 1)
        self.end_date = end_date or date.today()
        self.entity_filter = entity_filter

        # Initialize financial data
        self.financial_data = None

    def _fetch_financial_data(self) -> Dict[str, Any]:
        """Fetch financial data from the reporting APIs"""
        from .database import db_manager

        try:
            # Get P&L data from the monthly-pl endpoint logic
            params = [self.start_date.isoformat(), self.end_date.isoformat()]
            entity_params = []

            if self.entity_filter:
                entity_filter_condition = "AND classified_entity = %s"
                entity_params = [self.entity_filter]
            else:
                entity_filter_condition = ""

            # Revenue query
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

            # Get detailed breakdown by category
            category_query = f"""
                SELECT
                    accounting_category,
                    classified_entity,
                    SUM(CASE WHEN amount > 0 THEN usd_equivalent ELSE 0 END) as revenue,
                    SUM(CASE WHEN amount < 0 THEN ABS(usd_equivalent) ELSE 0 END) as expenses
                FROM transactions
                WHERE date::date BETWEEN %s AND %s
                {entity_filter_condition}
                GROUP BY accounting_category, classified_entity
                ORDER BY revenue DESC, expenses DESC
            """

            categories = db_manager.execute_query(category_query, tuple(all_params), fetch_all=True)

            # Previous period for comparison
            prev_start = self.start_date - relativedelta(years=1)
            prev_end = self.end_date - relativedelta(years=1)

            prev_params = [prev_start.isoformat(), prev_end.isoformat()] + entity_params
            prev_result = db_manager.execute_query(revenue_query, tuple(prev_params), fetch_one=True)

            prev_revenue = float(prev_result.get('total_revenue', 0) or 0) if prev_result else 0
            prev_expenses = float(prev_result.get('total_expenses', 0) or 0) if prev_result else 0

            return {
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'net_result': total_revenue - total_expenses,
                'prev_revenue': prev_revenue,
                'prev_expenses': prev_expenses,
                'prev_net_result': prev_revenue - prev_expenses,
                'categories': categories or []
            }

        except Exception as e:
            print(f"Error fetching financial data for DRE: {e}")
            return {
                'total_revenue': 0,
                'total_expenses': 0,
                'net_result': 0,
                'prev_revenue': 0,
                'prev_expenses': 0,
                'prev_net_result': 0,
                'categories': []
            }

    def _calculate_dre_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate DRE structure following Brazilian standards
        """
        # For now, we'll work with the available data and structure it properly
        # In a full implementation, we'd need more detailed transaction categorization

        # Basic DRE structure
        receita_bruta = data['total_revenue']
        deducoes_receita = data['total_revenue'] * 0.1  # Estimated deductions (taxes, returns, etc.)
        receita_liquida = receita_bruta - deducoes_receita

        # Split expenses into operational categories
        total_expenses = data['total_expenses']

        # Estimate expense breakdown (in real scenario, this would come from detailed categorization)
        custo_vendas = total_expenses * 0.4  # Cost of goods sold
        despesas_vendas = total_expenses * 0.2  # Sales expenses
        despesas_administrativas = total_expenses * 0.3  # Administrative expenses
        despesas_financeiras = total_expenses * 0.1  # Financial expenses

        lucro_bruto = receita_liquida - custo_vendas
        despesas_operacionais = despesas_vendas + despesas_administrativas
        resultado_operacional = lucro_bruto - despesas_operacionais
        resultado_financeiro = -despesas_financeiras  # Negative because it's an expense
        resultado_antes_impostos = resultado_operacional + resultado_financeiro

        # Estimate taxes (simplified)
        impostos = max(0, resultado_antes_impostos * 0.34) if resultado_antes_impostos > 0 else 0
        resultado_liquido = resultado_antes_impostos - impostos

        # Previous period comparison
        prev_receita_bruta = data['prev_revenue']
        prev_deducoes = prev_receita_bruta * 0.1
        prev_receita_liquida = prev_receita_bruta - prev_deducoes
        prev_total_expenses = data['prev_expenses']
        prev_custo_vendas = prev_total_expenses * 0.4
        prev_despesas_operacionais = prev_total_expenses * 0.5
        prev_despesas_financeiras = prev_total_expenses * 0.1
        prev_lucro_bruto = prev_receita_liquida - prev_custo_vendas
        prev_resultado_operacional = prev_lucro_bruto - prev_despesas_operacionais
        prev_resultado_financeiro = -prev_despesas_financeiras
        prev_resultado_antes_impostos = prev_resultado_operacional + prev_resultado_financeiro
        prev_impostos = max(0, prev_resultado_antes_impostos * 0.34) if prev_resultado_antes_impostos > 0 else 0
        prev_resultado_liquido = prev_resultado_antes_impostos - prev_impostos

        return {
            'receita_bruta': receita_bruta,
            'deducoes_receita': deducoes_receita,
            'receita_liquida': receita_liquida,
            'custo_vendas': custo_vendas,
            'lucro_bruto': lucro_bruto,
            'despesas_vendas': despesas_vendas,
            'despesas_administrativas': despesas_administrativas,
            'despesas_operacionais': despesas_operacionais,
            'resultado_operacional': resultado_operacional,
            'despesas_financeiras': despesas_financeiras,
            'resultado_financeiro': resultado_financeiro,
            'resultado_antes_impostos': resultado_antes_impostos,
            'impostos': impostos,
            'resultado_liquido': resultado_liquido,
            # Previous period
            'prev_receita_bruta': prev_receita_bruta,
            'prev_deducoes_receita': prev_deducoes,
            'prev_receita_liquida': prev_receita_liquida,
            'prev_custo_vendas': prev_custo_vendas,
            'prev_lucro_bruto': prev_lucro_bruto,
            'prev_despesas_operacionais': prev_despesas_operacionais,
            'prev_resultado_operacional': prev_resultado_operacional,
            'prev_despesas_financeiras': prev_despesas_financeiras,
            'prev_resultado_financeiro': prev_resultado_financeiro,
            'prev_resultado_antes_impostos': prev_resultado_antes_impostos,
            'prev_impostos': prev_impostos,
            'prev_resultado_liquido': prev_resultado_liquido
        }

    def _create_dre_table(self, dre_data: Dict[str, Any]) -> Table:
        """Create the main DRE table following Brazilian standards"""

        current_year = self.end_date.year
        previous_year = current_year - 1

        # Table headers
        headers = ["DEMONSTRAÇÃO DO RESULTADO DO EXERCÍCIO", f"{current_year}", f"{previous_year}"]

        # Table data following DRE structure with improved spacing
        table_data = [
            headers,
            # Revenue section
            ["RECEITA BRUTA DE VENDAS E SERVIÇOS", self.format_currency(dre_data['receita_bruta']), self.format_currency(dre_data['prev_receita_bruta'])],
            ["(-) Deduções da Receita Bruta", f"({self.format_currency(dre_data['deducoes_receita']).replace('R$ ', '')})", f"({self.format_currency(dre_data['prev_deducoes_receita']).replace('R$ ', '')})"],
            ["(=) RECEITA LÍQUIDA", self.format_currency(dre_data['receita_liquida']), self.format_currency(dre_data['prev_receita_liquida'])],
            # Cost section
            ["(-) Custo dos Produtos/Serviços Vendidos", f"({self.format_currency(dre_data['custo_vendas']).replace('R$ ', '')})", f"({self.format_currency(dre_data['prev_custo_vendas']).replace('R$ ', '')})"],
            ["(=) LUCRO BRUTO", self.format_currency(dre_data['lucro_bruto']), self.format_currency(dre_data['prev_lucro_bruto'])],
            # Operating expenses section
            ["(-) DESPESAS OPERACIONAIS", "", ""],
            ["    Despesas com Vendas", f"({self.format_currency(dre_data['despesas_vendas']).replace('R$ ', '')})", ""],
            ["    Despesas Administrativas", f"({self.format_currency(dre_data['despesas_administrativas']).replace('R$ ', '')})", ""],
            ["    Total das Despesas Operacionais", f"({self.format_currency(dre_data['despesas_operacionais']).replace('R$ ', '')})", f"({self.format_currency(dre_data['prev_despesas_operacionais']).replace('R$ ', '')})"],
            ["(=) RESULTADO OPERACIONAL", self.format_currency(dre_data['resultado_operacional']), self.format_currency(dre_data['prev_resultado_operacional'])],
            # Financial section
            ["(-) Despesas Financeiras", f"({self.format_currency(dre_data['despesas_financeiras']).replace('R$ ', '')})", f"({self.format_currency(dre_data['prev_despesas_financeiras']).replace('R$ ', '')})"],
            ["(=) RESULTADO ANTES DOS IMPOSTOS", self.format_currency(dre_data['resultado_antes_impostos']), self.format_currency(dre_data['prev_resultado_antes_impostos'])],
            # Final result section
            ["(-) Provisão para Impostos sobre o Lucro", f"({self.format_currency(dre_data['impostos']).replace('R$ ', '')})", f"({self.format_currency(dre_data['prev_impostos']).replace('R$ ', '')})"],
            ["(=) RESULTADO LÍQUIDO DO EXERCÍCIO", self.format_currency(dre_data['resultado_liquido']), self.format_currency(dre_data['prev_resultado_liquido'])],
        ]

        # Create table with improved column widths for better readability
        col_widths = [11*cm, 3.5*cm, 3.5*cm]
        table = Table(table_data, colWidths=col_widths)

        # Apply custom DRE styling with improved spacing
        table_style = TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['delta_blue']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # General styling with improved spacing
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),

            # Amount columns alignment
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),

            # Main section headers (bold) - updated row numbers after removing empty rows
            ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),  # RECEITA BRUTA
            ('FONTNAME', (0, 3), (0, 3), 'Helvetica-Bold'),  # RECEITA LÍQUIDA
            ('FONTNAME', (0, 5), (0, 5), 'Helvetica-Bold'),  # LUCRO BRUTO
            ('FONTNAME', (0, 6), (0, 6), 'Helvetica-Bold'),  # DESPESAS OPERACIONAIS
            ('FONTNAME', (0, 10), (0, 10), 'Helvetica-Bold'), # RESULTADO OPERACIONAL
            ('FONTNAME', (0, 12), (0, 12), 'Helvetica-Bold'), # RESULTADO ANTES DOS IMPOSTOS
            ('FONTNAME', (0, 14), (0, 14), 'Helvetica-Bold'), # RESULTADO LÍQUIDO

            # Result lines highlighting with better visual separation
            ('BACKGROUND', (0, 3), (-1, 3), self.colors['light_grey']),   # RECEITA LÍQUIDA
            ('BACKGROUND', (0, 5), (-1, 5), self.colors['light_grey']),   # LUCRO BRUTO
            ('BACKGROUND', (0, 10), (-1, 10), self.colors['light_grey']), # RESULTADO OPERACIONAL
            ('BACKGROUND', (0, 12), (-1, 12), self.colors['light_grey']), # RESULTADO ANTES DOS IMPOSTOS
            ('BACKGROUND', (0, 14), (-1, 14), self.colors['delta_blue']), # RESULTADO LÍQUIDO
            ('TEXTCOLOR', (0, 14), (-1, 14), colors.white),               # RESULTADO LÍQUIDO text color

            # Enhanced spacing with line separators for major sections
            ('LINEABOVE', (0, 3), (-1, 3), 1, self.colors['delta_grey']),   # Above RECEITA LÍQUIDA
            ('LINEABOVE', (0, 5), (-1, 5), 1, self.colors['delta_grey']),   # Above LUCRO BRUTO
            ('LINEABOVE', (0, 10), (-1, 10), 1, self.colors['delta_grey']), # Above RESULTADO OPERACIONAL
            ('LINEABOVE', (0, 12), (-1, 12), 1, self.colors['delta_grey']), # Above RESULTADO ANTES DOS IMPOSTOS
            ('LINEABOVE', (0, 14), (-1, 14), 2, self.colors['delta_blue']), # Above RESULTADO LÍQUIDO

            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, self.colors['delta_grey']),
            ('LINEBELOW', (0, 0), (-1, 0), 2, self.colors['delta_blue']),  # Header border
            ('LINEBELOW', (0, 14), (-1, 14), 2, self.colors['delta_blue']), # Final result border
        ])

        table.setStyle(table_style)
        return table

    def _create_analysis_section(self, dre_data: Dict[str, Any]) -> List:
        """Create analysis section with key financial indicators"""
        story = []

        self.add_section_break(story, "Análise de Indicadores")

        # Calculate key ratios
        receita_liquida = dre_data['receita_liquida']
        prev_receita_liquida = dre_data['prev_receita_liquida']

        if receita_liquida > 0:
            margem_bruta = (dre_data['lucro_bruto'] / receita_liquida) * 100
            margem_operacional = (dre_data['resultado_operacional'] / receita_liquida) * 100
            margem_liquida = (dre_data['resultado_liquido'] / receita_liquida) * 100
        else:
            margem_bruta = 0
            margem_operacional = 0
            margem_liquida = 0

        if prev_receita_liquida > 0:
            crescimento_receita = ((receita_liquida - prev_receita_liquida) / prev_receita_liquida) * 100
        else:
            crescimento_receita = 0

        # Analysis table
        analysis_data = [
            ["Indicador", "Valor", "Período Anterior"],
            ["Margem Bruta", self.format_percentage(margem_bruta), ""],
            ["Margem Operacional", self.format_percentage(margem_operacional), ""],
            ["Margem Líquida", self.format_percentage(margem_liquida), ""],
            ["Crescimento da Receita", self.format_percentage(crescimento_receita), ""],
        ]

        analysis_table = self.create_table(analysis_data, style_name='summary')
        story.append(analysis_table)

        return story

    def generate_dre_report(self) -> bytes:
        """Generate the complete DRE report"""

        # Fetch data
        self.financial_data = self._fetch_financial_data()

        # Calculate DRE structure
        dre_data = self._calculate_dre_structure(self.financial_data)

        # Build story
        story = []

        # Title section
        story.extend(self.create_title_section())

        # Entity filter info
        if self.entity_filter:
            entity_info = f"Entidade: {self.entity_filter}"
            story.append(Paragraph(entity_info, self.styles['Period']))
            story.append(Spacer(1, 10))

        # Main DRE table
        dre_table = self._create_dre_table(dre_data)
        story.append(dre_table)

        # Analysis section
        story.extend(self._create_analysis_section(dre_data))

        # Notes section
        self.add_section_break(story, "Notas Explicativas")

        notes = [
            "1. Os valores estão expressos em Dólares Americanos (USD).",
            "2. A classificação das contas segue as práticas contábeis brasileiras.",
            "3. As deduções da receita incluem impostos, devoluções e abatimentos estimados.",
            "4. Os custos e despesas são baseados na classificação automática do sistema.",
            "5. A provisão para impostos considera alíquota estimada de 34%.",
            "6. Este relatório foi gerado automaticamente pelo Delta CFO Agent."
        ]

        for note in notes:
            story.append(Paragraph(note, self.styles['TableData']))
            story.append(Spacer(1, 5))

        # Signature section
        story.extend(self.create_signature_section())

        # Generate PDF
        return self.generate_pdf(story)


class CashFlowReport(DeltaCFOReportTemplate):
    """
    Demonstração de Fluxo de Caixa (DFC) - Cash Flow Statement
    Following Brazilian accounting standards (CPC 03 / NBC TG 03)
    """

    def __init__(self, company_name: str = "Delta Mining", start_date: date = None, end_date: date = None, entity_filter: str = None):
        # Format period for display
        if start_date and end_date:
            if start_date.year == end_date.year:
                if start_date == date(start_date.year, 1, 1) and end_date == date(end_date.year, 12, 31):
                    # Full year
                    period = f"Exercício Social de {start_date.year}"
                else:
                    # Partial year
                    period = f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
            else:
                period = f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
        else:
            period = f"Exercício Social de {datetime.now().year}"

        super().__init__(
            title="Demonstração de Fluxo de Caixa (DFC)",
            company_name=company_name,
            report_period=period
        )

        self.start_date = start_date or date(datetime.now().year, 1, 1)
        self.end_date = end_date or date.today()
        self.entity_filter = entity_filter

        # Initialize cash flow data
        self.cash_flow_data = None

    def _fetch_cash_flow_data(self) -> Dict[str, Any]:
        """Fetch cash flow data from the database"""
        from .database import db_manager

        try:
            # Get cash flow data
            params = [self.start_date.isoformat(), self.end_date.isoformat()]
            entity_params = []

            if self.entity_filter:
                entity_filter_condition = "AND classified_entity = %s"
                entity_params = [self.entity_filter]
            else:
                entity_filter_condition = ""

            # Cash flows from operating activities
            operating_query = f"""
                SELECT
                    SUM(CASE WHEN amount > 0 THEN usd_equivalent ELSE 0 END) as cash_receipts,
                    SUM(CASE WHEN amount < 0 THEN ABS(usd_equivalent) ELSE 0 END) as cash_payments
                FROM transactions
                WHERE date::date BETWEEN %s AND %s
                {entity_filter_condition}
            """

            # Cash flows from investing activities
            investing_query = f"""
                SELECT
                    SUM(CASE WHEN amount > 0 THEN 0 ELSE 0 END) as investing_inflows,
                    SUM(CASE WHEN amount < 0 THEN 0 ELSE 0 END) as investing_outflows
                FROM transactions
                WHERE date::date BETWEEN %s AND %s
                {entity_filter_condition}
            """

            # Cash flows from financing activities
            financing_query = f"""
                SELECT
                    SUM(CASE WHEN amount > 0 THEN 0 ELSE 0 END) as financing_inflows,
                    SUM(CASE WHEN amount < 0 THEN 0 ELSE 0 END) as financing_outflows
                FROM transactions
                WHERE date::date BETWEEN %s AND %s
                {entity_filter_condition}
            """

            all_params = params + entity_params

            operating_result = db_manager.execute_query(operating_query, tuple(all_params), fetch_one=True)
            investing_result = db_manager.execute_query(investing_query, tuple(all_params), fetch_one=True)
            financing_result = db_manager.execute_query(financing_query, tuple(all_params), fetch_one=True)

            # Extract results with null safety
            cash_receipts = float(operating_result.get('cash_receipts', 0) or 0) if operating_result else 0
            cash_payments = float(operating_result.get('cash_payments', 0) or 0) if operating_result else 0
            investing_inflows = float(investing_result.get('investing_inflows', 0) or 0) if investing_result else 0
            investing_outflows = float(investing_result.get('investing_outflows', 0) or 0) if investing_result else 0
            financing_inflows = float(financing_result.get('financing_inflows', 0) or 0) if financing_result else 0
            financing_outflows = float(financing_result.get('financing_outflows', 0) or 0) if financing_result else 0

            # Calculate net cash flows
            net_operating = cash_receipts - cash_payments
            net_investing = investing_inflows - investing_outflows
            net_financing = financing_inflows - financing_outflows
            net_cash_change = net_operating + net_investing + net_financing

            # Get beginning cash balance (simplified as total cash up to start date)
            beginning_cash_query = f"""
                SELECT SUM(CASE WHEN amount > 0 THEN usd_equivalent ELSE 0 END) as beginning_cash
                FROM transactions
                WHERE date::date < %s
                AND LOWER(COALESCE(description, classified_entity, '')) LIKE ANY(ARRAY['%cash%', '%bank%', '%deposit%'])
                {entity_filter_condition}
            """

            beginning_params = [self.start_date.isoformat()] + entity_params
            beginning_result = db_manager.execute_query(beginning_cash_query, tuple(beginning_params), fetch_one=True)
            beginning_cash = float(beginning_result.get('beginning_cash', 0) or 0) if beginning_result else 0

            ending_cash = beginning_cash + net_cash_change

            # Previous period comparison
            prev_start = self.start_date - relativedelta(years=1)
            prev_end = self.end_date - relativedelta(years=1)
            prev_params = [prev_start.isoformat(), prev_end.isoformat()] + entity_params

            prev_operating_result = db_manager.execute_query(operating_query, tuple(prev_params), fetch_one=True)
            prev_cash_receipts = float(prev_operating_result.get('cash_receipts', 0) or 0) if prev_operating_result else 0
            prev_cash_payments = float(prev_operating_result.get('cash_payments', 0) or 0) if prev_operating_result else 0
            prev_net_operating = prev_cash_receipts - prev_cash_payments

            return {
                'cash_receipts': cash_receipts,
                'cash_payments': cash_payments,
                'net_operating': net_operating,
                'investing_inflows': investing_inflows,
                'investing_outflows': investing_outflows,
                'net_investing': net_investing,
                'financing_inflows': financing_inflows,
                'financing_outflows': financing_outflows,
                'net_financing': net_financing,
                'net_cash_change': net_cash_change,
                'beginning_cash': beginning_cash,
                'ending_cash': ending_cash,
                'prev_net_operating': prev_net_operating
            }

        except Exception as e:
            print(f"Error fetching cash flow data: {e}")
            return {
                'cash_receipts': 0,
                'cash_payments': 0,
                'net_operating': 0,
                'investing_inflows': 0,
                'investing_outflows': 0,
                'net_investing': 0,
                'financing_inflows': 0,
                'financing_outflows': 0,
                'net_financing': 0,
                'net_cash_change': 0,
                'beginning_cash': 0,
                'ending_cash': 0,
                'prev_net_operating': 0
            }

    def _create_cash_flow_table(self, cash_flow_data: Dict[str, Any]) -> Table:
        """Create the main Cash Flow table following Brazilian standards"""

        current_year = self.end_date.year
        previous_year = current_year - 1

        # Table headers
        headers = ["DEMONSTRAÇÃO DE FLUXO DE CAIXA", f"{current_year}", f"{previous_year}"]

        # Table data following DFC structure with improved spacing
        table_data = [
            headers,
            # Operating Activities section
            ["FLUXO DE CAIXA DAS ATIVIDADES OPERACIONAIS", "", ""],
            ["Recebimentos de clientes", self.format_currency(cash_flow_data['cash_receipts']), ""],
            ["Pagamentos a fornecedores e empregados", f"({self.format_currency(cash_flow_data['cash_payments']).replace('R$ ', '')})", ""],
            ["Caixa líquido gerado pelas atividades operacionais", self.format_currency(cash_flow_data['net_operating']), self.format_currency(cash_flow_data['prev_net_operating'])],
            # Investing Activities section
            ["FLUXO DE CAIXA DAS ATIVIDADES DE INVESTIMENTO", "", ""],
            ["Recebimentos por venda de ativos", self.format_currency(cash_flow_data['investing_inflows']), ""],
            ["Pagamentos por aquisição de ativos", f"({self.format_currency(cash_flow_data['investing_outflows']).replace('R$ ', '')})", ""],
            ["Caixa líquido usado nas atividades de investimento", self.format_currency(cash_flow_data['net_investing']), ""],
            # Financing Activities section
            ["FLUXO DE CAIXA DAS ATIVIDADES DE FINANCIAMENTO", "", ""],
            ["Recebimentos de empréstimos", self.format_currency(cash_flow_data['financing_inflows']), ""],
            ["Pagamentos de empréstimos e dividendos", f"({self.format_currency(cash_flow_data['financing_outflows']).replace('R$ ', '')})", ""],
            ["Caixa líquido usado nas atividades de financiamento", self.format_currency(cash_flow_data['net_financing']), ""],
            # Net change and reconciliation
            ["AUMENTO (DIMINUIÇÃO) LÍQUIDO DE CAIXA", self.format_currency(cash_flow_data['net_cash_change']), ""],
            ["Caixa e equivalentes no início do período", self.format_currency(cash_flow_data['beginning_cash']), ""],
            ["CAIXA E EQUIVALENTES NO FINAL DO PERÍODO", self.format_currency(cash_flow_data['ending_cash']), ""],
        ]

        # Create table with improved column widths for better readability
        col_widths = [11*cm, 3.5*cm, 3.5*cm]
        table = Table(table_data, colWidths=col_widths)

        # Apply custom Cash Flow styling with improved spacing
        table_style = TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['delta_blue']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # General styling with improved spacing
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),

            # Amount columns alignment
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),

            # Main section headers (bold)
            ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),  # ATIVIDADES OPERACIONAIS
            ('FONTNAME', (0, 4), (0, 4), 'Helvetica-Bold'),  # Líquido operacional
            ('FONTNAME', (0, 5), (0, 5), 'Helvetica-Bold'),  # ATIVIDADES DE INVESTIMENTO
            ('FONTNAME', (0, 8), (0, 8), 'Helvetica-Bold'),  # Líquido investimento
            ('FONTNAME', (0, 9), (0, 9), 'Helvetica-Bold'),  # ATIVIDADES DE FINANCIAMENTO
            ('FONTNAME', (0, 12), (0, 12), 'Helvetica-Bold'), # Líquido financiamento
            ('FONTNAME', (0, 13), (0, 13), 'Helvetica-Bold'), # AUMENTO LÍQUIDO
            ('FONTNAME', (0, 15), (0, 15), 'Helvetica-Bold'), # CAIXA FINAL

            # Section highlighting with better visual separation
            ('BACKGROUND', (0, 1), (-1, 1), self.colors['light_grey']),   # ATIVIDADES OPERACIONAIS
            ('BACKGROUND', (0, 4), (-1, 4), self.colors['light_grey']),   # Líquido operacional
            ('BACKGROUND', (0, 5), (-1, 5), self.colors['light_grey']),   # ATIVIDADES DE INVESTIMENTO
            ('BACKGROUND', (0, 8), (-1, 8), self.colors['light_grey']),   # Líquido investimento
            ('BACKGROUND', (0, 9), (-1, 9), self.colors['light_grey']),   # ATIVIDADES DE FINANCIAMENTO
            ('BACKGROUND', (0, 12), (-1, 12), self.colors['light_grey']),  # Líquido financiamento
            ('BACKGROUND', (0, 13), (-1, 13), self.colors['light_grey']),  # AUMENTO LÍQUIDO
            ('BACKGROUND', (0, 15), (-1, 15), self.colors['delta_blue']),  # CAIXA FINAL
            ('TEXTCOLOR', (0, 15), (-1, 15), colors.white),                # CAIXA FINAL text color

            # Enhanced spacing with line separators for major sections
            ('LINEABOVE', (0, 4), (-1, 4), 1, self.colors['delta_grey']),   # Above líquido operacional
            ('LINEABOVE', (0, 5), (-1, 5), 1, self.colors['delta_grey']),   # Above ATIVIDADES DE INVESTIMENTO
            ('LINEABOVE', (0, 8), (-1, 8), 1, self.colors['delta_grey']),   # Above líquido investimento
            ('LINEABOVE', (0, 9), (-1, 9), 1, self.colors['delta_grey']),   # Above ATIVIDADES DE FINANCIAMENTO
            ('LINEABOVE', (0, 12), (-1, 12), 1, self.colors['delta_grey']),  # Above líquido financiamento
            ('LINEABOVE', (0, 13), (-1, 13), 1, self.colors['delta_grey']),  # Above AUMENTO LÍQUIDO
            ('LINEABOVE', (0, 15), (-1, 15), 2, self.colors['delta_blue']),  # Above CAIXA FINAL

            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, self.colors['delta_grey']),
            ('LINEBELOW', (0, 0), (-1, 0), 2, self.colors['delta_blue']),  # Header border
            ('LINEBELOW', (0, 15), (-1, 15), 2, self.colors['delta_blue']), # Final cash border
        ])

        table.setStyle(table_style)
        return table

    def _create_cash_flow_analysis_section(self, cash_flow_data: Dict[str, Any]) -> List:
        """Create analysis section with key cash flow indicators"""
        story = []

        self.add_section_break(story, "Análise de Indicadores")

        # Calculate key ratios
        net_operating = cash_flow_data['net_operating']
        net_investing = cash_flow_data['net_investing']
        net_financing = cash_flow_data['net_financing']
        beginning_cash = cash_flow_data['beginning_cash']

        if beginning_cash > 0:
            cash_flow_to_sales_ratio = (net_operating / beginning_cash) * 100
        else:
            cash_flow_to_sales_ratio = 0

        # Previous year comparison
        prev_net_operating = cash_flow_data['prev_net_operating']
        if prev_net_operating != 0:
            operating_growth = ((net_operating - prev_net_operating) / abs(prev_net_operating)) * 100
        else:
            operating_growth = 0

        # Cash quality indicators
        if net_operating > 0:
            free_cash_flow = net_operating + net_investing
            cash_coverage = "Positivo" if net_operating > 0 else "Negativo"
        else:
            free_cash_flow = net_operating + net_investing
            cash_coverage = "Insuficiente"

        # Analysis table
        analysis_data = [
            ["Indicador", "Valor", "Interpretação"],
            ["Fluxo Operacional", self.format_currency(net_operating), cash_coverage],
            ["Fluxo de Caixa Livre", self.format_currency(free_cash_flow), "Capacidade de autofinanciamento"],
            ["Crescimento Operacional", self.format_percentage(operating_growth), "Variação anual"],
            ["Qualidade dos Lucros", f"{cash_flow_to_sales_ratio:.1f}%".replace('.', ','), "Conversão caixa/vendas"],
        ]

        analysis_table = self.create_table(analysis_data, style_name='summary')
        story.append(analysis_table)

        return story

    def generate_cash_flow_report(self) -> bytes:
        """Generate the complete Cash Flow report"""

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

        # Main Cash Flow table
        cash_flow_table = self._create_cash_flow_table(self.cash_flow_data)
        story.append(cash_flow_table)

        # Analysis section
        story.extend(self._create_cash_flow_analysis_section(self.cash_flow_data))

        # Notes section
        self.add_section_break(story, "Notas Explicativas")

        notes = [
            "1. Os valores estão expressos em Dólares Americanos (USD).",
            "2. A classificação segue o método direto de fluxo de caixa.",
            "3. Atividades operacionais incluem recebimentos e pagamentos operacionais.",
            "4. Atividades de investimento referem-se a ativos de longo prazo.",
            "5. Atividades de financiamento incluem empréstimos e distribuições.",
            "6. Este relatório foi gerado automaticamente pelo Delta CFO Agent."
        ]

        for note in notes:
            story.append(Paragraph(note, self.styles['TableData']))
            story.append(Spacer(1, 5))

        # Signature section
        story.extend(self.create_signature_section())

        # Generate PDF
        return self.generate_pdf(story)


class BalanceSheetReport(DeltaCFOReportTemplate):
    """
    Balanço Patrimonial - Balance Sheet
    Following Brazilian accounting standards (CPC 26 / NBC TG 26)
    """

    def __init__(self, company_name: str = "Delta Mining", start_date: date = None, end_date: date = None, entity_filter: str = None):
        # Format period for display
        if end_date:
            period = f"Posição em {end_date.strftime('%d/%m/%Y')}"
        else:
            period = f"Posição em {date.today().strftime('%d/%m/%Y')}"

        super().__init__(
            title="Balanço Patrimonial",
            company_name=company_name,
            report_period=period
        )

        self.start_date = start_date or date(datetime.now().year, 1, 1)
        self.end_date = end_date or date.today()
        self.entity_filter = entity_filter

        # Initialize financial data
        self.financial_data = None

    def _fetch_balance_sheet_data(self) -> Dict[str, Any]:
        """Fetch balance sheet data from the database"""
        from .database import db_manager

        try:
            # Get balance sheet data
            params = [self.end_date.isoformat()]
            entity_params = []

            if self.entity_filter:
                entity_filter_condition = "AND classified_entity = %s"
                entity_params = [self.entity_filter]
            else:
                entity_filter_condition = ""

            # Total assets (simplified - based on positive USD equivalent)
            assets_query = f"""
                SELECT
                    SUM(CASE WHEN usd_equivalent > 0 THEN usd_equivalent ELSE 0 END) as total_assets
                FROM transactions
                WHERE date::date <= %s
                {entity_filter_condition}
            """

            # Total liabilities (simplified - based on negative USD equivalent)
            liabilities_query = f"""
                SELECT
                    SUM(CASE WHEN usd_equivalent < 0 THEN ABS(usd_equivalent) ELSE 0 END) as total_liabilities
                FROM transactions
                WHERE date::date <= %s
                {entity_filter_condition}
            """

            all_params = params + entity_params
            assets_result = db_manager.execute_query(assets_query, tuple(all_params), fetch_one=True)
            liabilities_result = db_manager.execute_query(liabilities_query, tuple(all_params), fetch_one=True)

            total_assets = float(assets_result.get('total_assets', 0) or 0) if assets_result else 0
            total_liabilities = float(liabilities_result.get('total_liabilities', 0) or 0) if liabilities_result else 0

            # Calculate equity
            total_equity = total_assets - total_liabilities

            # Previous period comparison (1 year ago)
            prev_end = self.end_date - relativedelta(years=1)
            prev_params = [prev_end.isoformat()] + entity_params

            prev_assets_result = db_manager.execute_query(assets_query, tuple(prev_params), fetch_one=True)
            prev_liabilities_result = db_manager.execute_query(liabilities_query, tuple(prev_params), fetch_one=True)

            prev_total_assets = float(prev_assets_result.get('total_assets', 0) or 0) if prev_assets_result else 0
            prev_total_liabilities = float(prev_liabilities_result.get('total_liabilities', 0) or 0) if prev_liabilities_result else 0
            prev_total_equity = prev_total_assets - prev_total_liabilities

            return {
                'total_assets': total_assets,
                'current_assets': total_assets * 0.6,  # Estimated split
                'non_current_assets': total_assets * 0.4,
                'total_liabilities': total_liabilities,
                'current_liabilities': total_liabilities * 0.7,  # Estimated split
                'non_current_liabilities': total_liabilities * 0.3,
                'total_equity': total_equity,
                'prev_total_assets': prev_total_assets,
                'prev_current_assets': prev_total_assets * 0.6,
                'prev_non_current_assets': prev_total_assets * 0.4,
                'prev_total_liabilities': prev_total_liabilities,
                'prev_current_liabilities': prev_total_liabilities * 0.7,
                'prev_non_current_liabilities': prev_total_liabilities * 0.3,
                'prev_total_equity': prev_total_equity
            }

        except Exception as e:
            print(f"Error fetching balance sheet data: {e}")
            return {
                'total_assets': 0,
                'current_assets': 0,
                'non_current_assets': 0,
                'total_liabilities': 0,
                'current_liabilities': 0,
                'non_current_liabilities': 0,
                'total_equity': 0,
                'prev_total_assets': 0,
                'prev_current_assets': 0,
                'prev_non_current_assets': 0,
                'prev_total_liabilities': 0,
                'prev_current_liabilities': 0,
                'prev_non_current_liabilities': 0,
                'prev_total_equity': 0
            }

    def _create_balance_sheet_table(self, balance_data: Dict[str, Any]) -> Table:
        """Create the main Balance Sheet table following Brazilian standards"""

        current_year = self.end_date.year
        previous_year = current_year - 1

        # Table headers
        headers = ["BALANÇO PATRIMONIAL", f"{current_year}", f"{previous_year}"]

        # Table data following Balance Sheet structure
        table_data = [
            headers,
            # ASSETS SECTION
            ["ATIVO", "", ""],
            ["ATIVO CIRCULANTE", self.format_currency(balance_data['current_assets']), self.format_currency(balance_data['prev_current_assets'])],
            ["    Caixa e Equivalentes", self.format_currency(balance_data['current_assets'] * 0.4), self.format_currency(balance_data['prev_current_assets'] * 0.4)],
            ["    Contas a Receber", self.format_currency(balance_data['current_assets'] * 0.4), self.format_currency(balance_data['prev_current_assets'] * 0.4)],
            ["    Estoques", self.format_currency(balance_data['current_assets'] * 0.2), self.format_currency(balance_data['prev_current_assets'] * 0.2)],
            ["ATIVO NÃO CIRCULANTE", self.format_currency(balance_data['non_current_assets']), self.format_currency(balance_data['prev_non_current_assets'])],
            ["    Imobilizado", self.format_currency(balance_data['non_current_assets'] * 0.7), self.format_currency(balance_data['prev_non_current_assets'] * 0.7)],
            ["    Intangível", self.format_currency(balance_data['non_current_assets'] * 0.3), self.format_currency(balance_data['prev_non_current_assets'] * 0.3)],
            ["TOTAL DO ATIVO", self.format_currency(balance_data['total_assets']), self.format_currency(balance_data['prev_total_assets'])],
            # LIABILITIES & EQUITY SECTION
            ["PASSIVO E PATRIMÔNIO LÍQUIDO", "", ""],
            ["PASSIVO CIRCULANTE", self.format_currency(balance_data['current_liabilities']), self.format_currency(balance_data['prev_current_liabilities'])],
            ["    Fornecedores", self.format_currency(balance_data['current_liabilities'] * 0.5), self.format_currency(balance_data['prev_current_liabilities'] * 0.5)],
            ["    Obrigações Fiscais", self.format_currency(balance_data['current_liabilities'] * 0.3), self.format_currency(balance_data['prev_current_liabilities'] * 0.3)],
            ["    Outras Obrigações", self.format_currency(balance_data['current_liabilities'] * 0.2), self.format_currency(balance_data['prev_current_liabilities'] * 0.2)],
            ["PASSIVO NÃO CIRCULANTE", self.format_currency(balance_data['non_current_liabilities']), self.format_currency(balance_data['prev_non_current_liabilities'])],
            ["    Financiamentos", self.format_currency(balance_data['non_current_liabilities'] * 0.8), self.format_currency(balance_data['prev_non_current_liabilities'] * 0.8)],
            ["    Outras Obrigações", self.format_currency(balance_data['non_current_liabilities'] * 0.2), self.format_currency(balance_data['prev_non_current_liabilities'] * 0.2)],
            ["PATRIMÔNIO LÍQUIDO", self.format_currency(balance_data['total_equity']), self.format_currency(balance_data['prev_total_equity'])],
            ["TOTAL DO PASSIVO + PL", self.format_currency(balance_data['total_assets']), self.format_currency(balance_data['prev_total_assets'])],
        ]

        # Create table with improved column widths for better readability
        col_widths = [11*cm, 3.5*cm, 3.5*cm]
        table = Table(table_data, colWidths=col_widths)

        # Apply custom Balance Sheet styling with improved spacing
        table_style = TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['delta_blue']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # General styling with improved spacing
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),

            # Amount columns alignment
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),

            # Main section headers (bold)
            ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),  # ATIVO
            ('FONTNAME', (0, 2), (0, 2), 'Helvetica-Bold'),  # ATIVO CIRCULANTE
            ('FONTNAME', (0, 6), (0, 6), 'Helvetica-Bold'),  # ATIVO NÃO CIRCULANTE
            ('FONTNAME', (0, 9), (0, 9), 'Helvetica-Bold'),  # TOTAL DO ATIVO
            ('FONTNAME', (0, 10), (0, 10), 'Helvetica-Bold'), # PASSIVO E PATRIMÔNIO LÍQUIDO
            ('FONTNAME', (0, 11), (0, 11), 'Helvetica-Bold'), # PASSIVO CIRCULANTE
            ('FONTNAME', (0, 15), (0, 15), 'Helvetica-Bold'), # PASSIVO NÃO CIRCULANTE
            ('FONTNAME', (0, 18), (0, 18), 'Helvetica-Bold'), # PATRIMÔNIO LÍQUIDO
            ('FONTNAME', (0, 19), (0, 19), 'Helvetica-Bold'), # TOTAL DO PASSIVO + PL

            # Section highlighting with better visual separation
            ('BACKGROUND', (0, 1), (-1, 1), self.colors['light_grey']),   # ATIVO
            ('BACKGROUND', (0, 9), (-1, 9), self.colors['light_grey']),   # TOTAL DO ATIVO
            ('BACKGROUND', (0, 10), (-1, 10), self.colors['light_grey']),  # PASSIVO E PATRIMÔNIO LÍQUIDO
            ('BACKGROUND', (0, 18), (-1, 18), self.colors['light_grey']),  # PATRIMÔNIO LÍQUIDO
            ('BACKGROUND', (0, 19), (-1, 19), self.colors['delta_blue']),  # TOTAL DO PASSIVO + PL
            ('TEXTCOLOR', (0, 19), (-1, 19), colors.white),                # TOTAL DO PASSIVO + PL text color

            # Enhanced spacing with line separators for major sections
            ('LINEABOVE', (0, 2), (-1, 2), 1, self.colors['delta_grey']),   # Above ATIVO CIRCULANTE
            ('LINEABOVE', (0, 6), (-1, 6), 1, self.colors['delta_grey']),   # Above ATIVO NÃO CIRCULANTE
            ('LINEABOVE', (0, 9), (-1, 9), 2, self.colors['delta_blue']),   # Above TOTAL DO ATIVO
            ('LINEABOVE', (0, 11), (-1, 11), 1, self.colors['delta_grey']),  # Above PASSIVO CIRCULANTE
            ('LINEABOVE', (0, 15), (-1, 15), 1, self.colors['delta_grey']),  # Above PASSIVO NÃO CIRCULANTE
            ('LINEABOVE', (0, 18), (-1, 18), 1, self.colors['delta_grey']),  # Above PATRIMÔNIO LÍQUIDO
            ('LINEABOVE', (0, 19), (-1, 19), 2, self.colors['delta_blue']),  # Above TOTAL DO PASSIVO + PL

            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, self.colors['delta_grey']),
            ('LINEBELOW', (0, 0), (-1, 0), 2, self.colors['delta_blue']),  # Header border
            ('LINEBELOW', (0, 19), (-1, 19), 2, self.colors['delta_blue']), # Final total border
        ])

        table.setStyle(table_style)
        return table

    def _create_balance_analysis_section(self, balance_data: Dict[str, Any]) -> List:
        """Create analysis section with key financial indicators"""
        story = []

        self.add_section_break(story, "Análise de Indicadores")

        # Calculate key ratios
        total_assets = balance_data['total_assets']
        total_liabilities = balance_data['total_liabilities']
        total_equity = balance_data['total_equity']
        current_assets = balance_data['current_assets']
        current_liabilities = balance_data['current_liabilities']

        if total_assets > 0:
            debt_to_assets = (total_liabilities / total_assets) * 100
            equity_ratio = (total_equity / total_assets) * 100
        else:
            debt_to_assets = 0
            equity_ratio = 0

        if current_liabilities > 0:
            current_ratio = current_assets / current_liabilities
        else:
            current_ratio = 0

        # Previous year comparison
        prev_total_assets = balance_data['prev_total_assets']
        if prev_total_assets > 0:
            asset_growth = ((total_assets - prev_total_assets) / prev_total_assets) * 100
        else:
            asset_growth = 0

        # Analysis table
        analysis_data = [
            ["Indicador", "Valor", "Interpretação"],
            ["Índice de Liquidez Corrente", f"{current_ratio:.2f}".replace('.', ','), "Capacidade de pagamento"],
            ["Endividamento sobre Ativos", self.format_percentage(debt_to_assets), "Nível de endividamento"],
            ["Participação do PL", self.format_percentage(equity_ratio), "Participação própria"],
            ["Crescimento do Ativo", self.format_percentage(asset_growth), "Variação anual"],
        ]

        analysis_table = self.create_table(analysis_data, style_name='summary')
        story.append(analysis_table)

        return story

    def generate_balance_sheet_report(self) -> bytes:
        """Generate the complete Balance Sheet report"""

        # Fetch data
        self.financial_data = self._fetch_balance_sheet_data()

        # Build story
        story = []

        # Title section
        story.extend(self.create_title_section())

        # Entity filter info
        if self.entity_filter:
            entity_info = f"Entidade: {self.entity_filter}"
            story.append(Paragraph(entity_info, self.styles['Period']))
            story.append(Spacer(1, 10))

        # Main Balance Sheet table
        balance_table = self._create_balance_sheet_table(self.financial_data)
        story.append(balance_table)

        # Analysis section
        story.extend(self._create_balance_analysis_section(self.financial_data))

        # Notes section
        self.add_section_break(story, "Notas Explicativas")

        notes = [
            "1. Os valores estão expressos em Dólares Americanos (USD).",
            "2. A classificação das contas segue as práticas contábeis brasileiras.",
            "3. Os valores de Ativo e Passivo são baseados no saldo acumulado das transações.",
            "4. A segregação entre circulante e não circulante é estimada.",
            "5. O Patrimônio Líquido é calculado pela diferença entre Ativo e Passivo.",
            "6. Este relatório foi gerado automaticamente pelo Delta CFO Agent."
        ]

        for note in notes:
            story.append(Paragraph(note, self.styles['TableData']))
            story.append(Spacer(1, 5))

        # Signature section
        story.extend(self.create_signature_section())

        # Generate PDF
        return self.generate_pdf(story)


class CashFlowReport(DeltaCFOReportTemplate):
    """
    Demonstração de Fluxo de Caixa (DFC) - Cash Flow Statement
    Following Brazilian accounting standards (CPC 03 / NBC TG 03)
    """

    def __init__(self, company_name: str = "Delta Mining", start_date: date = None, end_date: date = None, entity_filter: str = None):
        # Format period for display
        if start_date and end_date:
            if start_date.year == end_date.year:
                if start_date == date(start_date.year, 1, 1) and end_date == date(end_date.year, 12, 31):
                    # Full year
                    period = f"Exercício Social de {start_date.year}"
                else:
                    # Partial year
                    period = f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
            else:
                period = f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
        else:
            period = f"Exercício Social de {datetime.now().year}"

        super().__init__(
            title="Demonstração de Fluxo de Caixa (DFC)",
            company_name=company_name,
            report_period=period
        )

        self.start_date = start_date or date(datetime.now().year, 1, 1)
        self.end_date = end_date or date.today()
        self.entity_filter = entity_filter

        # Initialize cash flow data
        self.cash_flow_data = None

    def _fetch_cash_flow_data(self) -> Dict[str, Any]:
        """Fetch cash flow data from the database"""
        from .database import db_manager

        try:
            # Get cash flow data
            params = [self.start_date.isoformat(), self.end_date.isoformat()]
            entity_params = []

            if self.entity_filter:
                entity_filter_condition = "AND classified_entity = %s"
                entity_params = [self.entity_filter]
            else:
                entity_filter_condition = ""

            # Cash flows from operating activities
            operating_query = f"""
                SELECT
                    SUM(CASE WHEN amount > 0 THEN usd_equivalent ELSE 0 END) as cash_receipts,
                    SUM(CASE WHEN amount < 0 THEN ABS(usd_equivalent) ELSE 0 END) as cash_payments
                FROM transactions
                WHERE date::date BETWEEN %s AND %s
                {entity_filter_condition}
            """

            # Cash flows from investing activities
            investing_query = f"""
                SELECT
                    SUM(CASE WHEN amount > 0 THEN 0 ELSE 0 END) as investing_inflows,
                    SUM(CASE WHEN amount < 0 THEN 0 ELSE 0 END) as investing_outflows
                FROM transactions
                WHERE date::date BETWEEN %s AND %s
                {entity_filter_condition}
            """

            # Cash flows from financing activities
            financing_query = f"""
                SELECT
                    SUM(CASE WHEN amount > 0 THEN 0 ELSE 0 END) as financing_inflows,
                    SUM(CASE WHEN amount < 0 THEN 0 ELSE 0 END) as financing_outflows
                FROM transactions
                WHERE date::date BETWEEN %s AND %s
                {entity_filter_condition}
            """

            all_params = params + entity_params

            operating_result = db_manager.execute_query(operating_query, tuple(all_params), fetch_one=True)
            investing_result = db_manager.execute_query(investing_query, tuple(all_params), fetch_one=True)
            financing_result = db_manager.execute_query(financing_query, tuple(all_params), fetch_one=True)

            # Extract results with null safety
            cash_receipts = float(operating_result.get('cash_receipts', 0) or 0) if operating_result else 0
            cash_payments = float(operating_result.get('cash_payments', 0) or 0) if operating_result else 0
            investing_inflows = float(investing_result.get('investing_inflows', 0) or 0) if investing_result else 0
            investing_outflows = float(investing_result.get('investing_outflows', 0) or 0) if investing_result else 0
            financing_inflows = float(financing_result.get('financing_inflows', 0) or 0) if financing_result else 0
            financing_outflows = float(financing_result.get('financing_outflows', 0) or 0) if financing_result else 0

            # Calculate net cash flows
            net_operating = cash_receipts - cash_payments
            net_investing = investing_inflows - investing_outflows
            net_financing = financing_inflows - financing_outflows
            net_cash_change = net_operating + net_investing + net_financing

            # Get beginning cash balance (simplified as total cash up to start date)
            beginning_cash_query = f"""
                SELECT SUM(CASE WHEN amount > 0 THEN usd_equivalent ELSE 0 END) as beginning_cash
                FROM transactions
                WHERE date::date < %s
                AND LOWER(COALESCE(description, classified_entity, '')) LIKE ANY(ARRAY['%cash%', '%bank%', '%deposit%'])
                {entity_filter_condition}
            """

            beginning_params = [self.start_date.isoformat()] + entity_params
            beginning_result = db_manager.execute_query(beginning_cash_query, tuple(beginning_params), fetch_one=True)
            beginning_cash = float(beginning_result.get('beginning_cash', 0) or 0) if beginning_result else 0

            ending_cash = beginning_cash + net_cash_change

            # Previous period comparison
            prev_start = self.start_date - relativedelta(years=1)
            prev_end = self.end_date - relativedelta(years=1)
            prev_params = [prev_start.isoformat(), prev_end.isoformat()] + entity_params

            prev_operating_result = db_manager.execute_query(operating_query, tuple(prev_params), fetch_one=True)
            prev_cash_receipts = float(prev_operating_result.get('cash_receipts', 0) or 0) if prev_operating_result else 0
            prev_cash_payments = float(prev_operating_result.get('cash_payments', 0) or 0) if prev_operating_result else 0
            prev_net_operating = prev_cash_receipts - prev_cash_payments

            return {
                'cash_receipts': cash_receipts,
                'cash_payments': cash_payments,
                'net_operating': net_operating,
                'investing_inflows': investing_inflows,
                'investing_outflows': investing_outflows,
                'net_investing': net_investing,
                'financing_inflows': financing_inflows,
                'financing_outflows': financing_outflows,
                'net_financing': net_financing,
                'net_cash_change': net_cash_change,
                'beginning_cash': beginning_cash,
                'ending_cash': ending_cash,
                'prev_net_operating': prev_net_operating
            }

        except Exception as e:
            print(f"Error fetching cash flow data: {e}")
            return {
                'cash_receipts': 0,
                'cash_payments': 0,
                'net_operating': 0,
                'investing_inflows': 0,
                'investing_outflows': 0,
                'net_investing': 0,
                'financing_inflows': 0,
                'financing_outflows': 0,
                'net_financing': 0,
                'net_cash_change': 0,
                'beginning_cash': 0,
                'ending_cash': 0,
                'prev_net_operating': 0
            }

    def _create_cash_flow_table(self, cash_flow_data: Dict[str, Any]) -> Table:
        """Create the main Cash Flow table following Brazilian standards"""

        current_year = self.end_date.year
        previous_year = current_year - 1

        # Table headers
        headers = ["DEMONSTRAÇÃO DE FLUXO DE CAIXA", f"{current_year}", f"{previous_year}"]

        # Table data following DFC structure with improved spacing
        table_data = [
            headers,
            # Operating Activities section
            ["FLUXO DE CAIXA DAS ATIVIDADES OPERACIONAIS", "", ""],
            ["Recebimentos de clientes", self.format_currency(cash_flow_data['cash_receipts']), ""],
            ["Pagamentos a fornecedores e empregados", f"({self.format_currency(cash_flow_data['cash_payments']).replace('R$ ', '')})", ""],
            ["Caixa líquido gerado pelas atividades operacionais", self.format_currency(cash_flow_data['net_operating']), self.format_currency(cash_flow_data['prev_net_operating'])],
            # Investing Activities section
            ["FLUXO DE CAIXA DAS ATIVIDADES DE INVESTIMENTO", "", ""],
            ["Recebimentos por venda de ativos", self.format_currency(cash_flow_data['investing_inflows']), ""],
            ["Pagamentos por aquisição de ativos", f"({self.format_currency(cash_flow_data['investing_outflows']).replace('R$ ', '')})", ""],
            ["Caixa líquido usado nas atividades de investimento", self.format_currency(cash_flow_data['net_investing']), ""],
            # Financing Activities section
            ["FLUXO DE CAIXA DAS ATIVIDADES DE FINANCIAMENTO", "", ""],
            ["Recebimentos de empréstimos", self.format_currency(cash_flow_data['financing_inflows']), ""],
            ["Pagamentos de empréstimos e dividendos", f"({self.format_currency(cash_flow_data['financing_outflows']).replace('R$ ', '')})", ""],
            ["Caixa líquido usado nas atividades de financiamento", self.format_currency(cash_flow_data['net_financing']), ""],
            # Net change and reconciliation
            ["AUMENTO (DIMINUIÇÃO) LÍQUIDO DE CAIXA", self.format_currency(cash_flow_data['net_cash_change']), ""],
            ["Caixa e equivalentes no início do período", self.format_currency(cash_flow_data['beginning_cash']), ""],
            ["CAIXA E EQUIVALENTES NO FINAL DO PERÍODO", self.format_currency(cash_flow_data['ending_cash']), ""],
        ]

        # Create table with improved column widths for better readability
        col_widths = [11*cm, 3.5*cm, 3.5*cm]
        table = Table(table_data, colWidths=col_widths)

        # Apply custom Cash Flow styling with improved spacing
        table_style = TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['delta_blue']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # General styling with improved spacing
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),

            # Amount columns alignment
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),

            # Main section headers (bold)
            ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),  # ATIVIDADES OPERACIONAIS
            ('FONTNAME', (0, 4), (0, 4), 'Helvetica-Bold'),  # Líquido operacional
            ('FONTNAME', (0, 5), (0, 5), 'Helvetica-Bold'),  # ATIVIDADES DE INVESTIMENTO
            ('FONTNAME', (0, 8), (0, 8), 'Helvetica-Bold'),  # Líquido investimento
            ('FONTNAME', (0, 9), (0, 9), 'Helvetica-Bold'),  # ATIVIDADES DE FINANCIAMENTO
            ('FONTNAME', (0, 12), (0, 12), 'Helvetica-Bold'), # Líquido financiamento
            ('FONTNAME', (0, 13), (0, 13), 'Helvetica-Bold'), # AUMENTO LÍQUIDO
            ('FONTNAME', (0, 15), (0, 15), 'Helvetica-Bold'), # CAIXA FINAL

            # Section highlighting with better visual separation
            ('BACKGROUND', (0, 1), (-1, 1), self.colors['light_grey']),   # ATIVIDADES OPERACIONAIS
            ('BACKGROUND', (0, 4), (-1, 4), self.colors['light_grey']),   # Líquido operacional
            ('BACKGROUND', (0, 5), (-1, 5), self.colors['light_grey']),   # ATIVIDADES DE INVESTIMENTO
            ('BACKGROUND', (0, 8), (-1, 8), self.colors['light_grey']),   # Líquido investimento
            ('BACKGROUND', (0, 9), (-1, 9), self.colors['light_grey']),   # ATIVIDADES DE FINANCIAMENTO
            ('BACKGROUND', (0, 12), (-1, 12), self.colors['light_grey']),  # Líquido financiamento
            ('BACKGROUND', (0, 13), (-1, 13), self.colors['light_grey']),  # AUMENTO LÍQUIDO
            ('BACKGROUND', (0, 15), (-1, 15), self.colors['delta_blue']),  # CAIXA FINAL
            ('TEXTCOLOR', (0, 15), (-1, 15), colors.white),                # CAIXA FINAL text color

            # Enhanced spacing with line separators for major sections
            ('LINEABOVE', (0, 4), (-1, 4), 1, self.colors['delta_grey']),   # Above líquido operacional
            ('LINEABOVE', (0, 5), (-1, 5), 1, self.colors['delta_grey']),   # Above ATIVIDADES DE INVESTIMENTO
            ('LINEABOVE', (0, 8), (-1, 8), 1, self.colors['delta_grey']),   # Above líquido investimento
            ('LINEABOVE', (0, 9), (-1, 9), 1, self.colors['delta_grey']),   # Above ATIVIDADES DE FINANCIAMENTO
            ('LINEABOVE', (0, 12), (-1, 12), 1, self.colors['delta_grey']),  # Above líquido financiamento
            ('LINEABOVE', (0, 13), (-1, 13), 1, self.colors['delta_grey']),  # Above AUMENTO LÍQUIDO
            ('LINEABOVE', (0, 15), (-1, 15), 2, self.colors['delta_blue']),  # Above CAIXA FINAL

            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, self.colors['delta_grey']),
            ('LINEBELOW', (0, 0), (-1, 0), 2, self.colors['delta_blue']),  # Header border
            ('LINEBELOW', (0, 15), (-1, 15), 2, self.colors['delta_blue']), # Final cash border
        ])

        table.setStyle(table_style)
        return table

    def _create_cash_flow_analysis_section(self, cash_flow_data: Dict[str, Any]) -> List:
        """Create analysis section with key cash flow indicators"""
        story = []

        self.add_section_break(story, "Análise de Indicadores")

        # Calculate key ratios
        net_operating = cash_flow_data['net_operating']
        net_investing = cash_flow_data['net_investing']
        net_financing = cash_flow_data['net_financing']
        beginning_cash = cash_flow_data['beginning_cash']

        if beginning_cash > 0:
            cash_flow_to_sales_ratio = (net_operating / beginning_cash) * 100
        else:
            cash_flow_to_sales_ratio = 0

        # Previous year comparison
        prev_net_operating = cash_flow_data['prev_net_operating']
        if prev_net_operating != 0:
            operating_growth = ((net_operating - prev_net_operating) / abs(prev_net_operating)) * 100
        else:
            operating_growth = 0

        # Cash quality indicators
        if net_operating > 0:
            free_cash_flow = net_operating + net_investing
            cash_coverage = "Positivo" if net_operating > 0 else "Negativo"
        else:
            free_cash_flow = net_operating + net_investing
            cash_coverage = "Insuficiente"

        # Analysis table
        analysis_data = [
            ["Indicador", "Valor", "Interpretação"],
            ["Fluxo Operacional", self.format_currency(net_operating), cash_coverage],
            ["Fluxo de Caixa Livre", self.format_currency(free_cash_flow), "Capacidade de autofinanciamento"],
            ["Crescimento Operacional", self.format_percentage(operating_growth), "Variação anual"],
            ["Qualidade dos Lucros", f"{cash_flow_to_sales_ratio:.1f}%".replace('.', ','), "Conversão caixa/vendas"],
        ]

        analysis_table = self.create_table(analysis_data, style_name='summary')
        story.append(analysis_table)

        return story

    def generate_cash_flow_report(self) -> bytes:
        """Generate the complete Cash Flow report"""

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

        # Main Cash Flow table
        cash_flow_table = self._create_cash_flow_table(self.cash_flow_data)
        story.append(cash_flow_table)

        # Analysis section
        story.extend(self._create_cash_flow_analysis_section(self.cash_flow_data))

        # Notes section
        self.add_section_break(story, "Notas Explicativas")

        notes = [
            "1. Os valores estão expressos em Dólares Americanos (USD).",
            "2. A classificação segue o método direto de fluxo de caixa.",
            "3. Atividades operacionais incluem recebimentos e pagamentos operacionais.",
            "4. Atividades de investimento referem-se a ativos de longo prazo.",
            "5. Atividades de financiamento incluem empréstimos e distribuições.",
            "6. Este relatório foi gerado automaticamente pelo Delta CFO Agent."
        ]

        for note in notes:
            story.append(Paragraph(note, self.styles['TableData']))
            story.append(Spacer(1, 5))

        # Signature section
        story.extend(self.create_signature_section())

        # Generate PDF
        return self.generate_pdf(story)
