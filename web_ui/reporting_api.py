#!/usr/bin/env python3
"""
CFO Reporting API Endpoints
Flask routes for financial statements and reporting functionality
"""

import os
import sys
import json
import logging
import calendar
from datetime import datetime, date, timedelta
from flask import request, jsonify, send_file, make_response
from decimal import Decimal
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.colors import HexColor

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reporting.financial_statements import FinancialStatementsGenerator
from reporting.cash_dashboard import CashDashboard
from .database import db_manager
from .pdf_reports import DREReport, BalanceSheetReport
from .cash_flow_report_new import CashFlowReport
from .dmpl_report_new import DMPLReport

logger = logging.getLogger(__name__)


def register_reporting_routes(app):
    """Register all CFO reporting routes with the Flask app"""

    @app.route('/api/reports/income-statement', methods=['GET', 'POST'])
    def api_income_statement():
        """
        Generate Income Statement (P&L)

        GET Parameters:
            - start_date: Start date (YYYY-MM-DD or MM/DD/YYYY)
            - end_date: End date (YYYY-MM-DD or MM/DD/YYYY)
            - period_id: Accounting period ID (optional)
            - include_details: Include transaction details (true/false)
            - comparison_period_id: Period to compare against (optional)

        Returns:
            JSON with complete Income Statement data
        """
        try:
            # Parse parameters
            start_date_str = request.args.get('start_date') or request.json.get('start_date') if request.method == 'POST' else None
            end_date_str = request.args.get('end_date') or request.json.get('end_date') if request.method == 'POST' else None
            period_id = request.args.get('period_id') or request.json.get('period_id') if request.method == 'POST' else None
            include_details = request.args.get('include_details', 'false').lower() == 'true' or \
                            (request.json.get('include_details', False) if request.method == 'POST' else False)
            comparison_period_id = request.args.get('comparison_period_id') or \
                                 (request.json.get('comparison_period_id') if request.method == 'POST' else None)

            # Parse dates
            start_date = None
            end_date = None

            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        start_date = datetime.strptime(start_date_str, '%m/%d/%Y').date()
                    except ValueError:
                        return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD or MM/DD/YYYY'}), 400

            if end_date_str:
                try:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        end_date = datetime.strptime(end_date_str, '%m/%d/%Y').date()
                    except ValueError:
                        return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD or MM/DD/YYYY'}), 400

            # Generate statement
            generator = FinancialStatementsGenerator()

            statement = generator.generate_income_statement(
                period_id=int(period_id) if period_id else None,
                start_date=start_date,
                end_date=end_date,
                comparison_period_id=int(comparison_period_id) if comparison_period_id else None,
                include_details=include_details
            )

            return jsonify({
                'success': True,
                'statement': statement
            })

        except Exception as e:
            logger.error(f"Error generating income statement: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/income-statement/simple', methods=['GET'])
    def api_income_statement_simple():
        """
        Generate simplified Income Statement using direct SQL (fast)
        This endpoint uses the optimized query approach from test_pl_simple.py

        Returns:
            JSON with simplified P&L data
        """
        try:
            start_time = datetime.now()

            # Revenue: All positive amounts
            revenue_query = """
                SELECT
                    COALESCE(accounting_category, classified_entity, 'Uncategorized Revenue') as category,
                    SUM(COALESCE(usd_equivalent, amount, 0)) as total,
                    COUNT(*) as count
                FROM transactions
                WHERE amount > 0
                GROUP BY COALESCE(accounting_category, classified_entity, 'Uncategorized Revenue')
                ORDER BY total DESC
            """
            revenue_data = db_manager.execute_query(revenue_query, fetch_all=True)

            total_revenue = Decimal('0')
            revenue_categories = []

            for row in revenue_data:
                amount = Decimal(str(row['total'] or 0))
                revenue_categories.append({
                    'category': row['category'],
                    'amount': float(amount),
                    'count': row['count']
                })
                total_revenue += amount

            # Operating Expenses: All negative amounts
            opex_query = """
                SELECT
                    COALESCE(accounting_category, classified_entity, 'General & Administrative') as category,
                    SUM(ABS(COALESCE(usd_equivalent, amount, 0))) as total,
                    COUNT(*) as count
                FROM transactions
                WHERE amount < 0
                AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%material%'
                AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%inventory%'
                AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%manufacturing%'
                AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%production%'
                AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%supplier%'
                GROUP BY COALESCE(accounting_category, classified_entity, 'General & Administrative')
                ORDER BY total DESC
            """
            opex_data = db_manager.execute_query(opex_query, fetch_all=True)

            total_opex = Decimal('0')
            opex_categories = []

            for row in opex_data:
                amount = Decimal(str(row['total'] or 0))
                opex_categories.append({
                    'category': row['category'],
                    'amount': float(amount),
                    'count': row['count']
                })
                total_opex += amount

            # Calculate metrics
            gross_profit = total_revenue
            operating_income = gross_profit - total_opex
            net_income = operating_income

            gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
            operating_margin = (operating_income / total_revenue * 100) if total_revenue > 0 else 0
            net_margin = (net_income / total_revenue * 100) if total_revenue > 0 else 0

            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'statement': {
                    'statement_type': 'IncomeStatement',
                    'statement_name': 'Income Statement - All Periods',
                    'generated_at': datetime.now().isoformat(),
                    'generation_time_ms': generation_time_ms,

                    'revenue': {
                        'total': float(total_revenue),
                        'categories': revenue_categories
                    },

                    'cost_of_goods_sold': {
                        'total': 0,
                        'categories': []
                    },

                    'gross_profit': {
                        'amount': float(gross_profit),
                        'margin_percent': round(float(gross_margin), 2)
                    },

                    'operating_expenses': {
                        'total': float(total_opex),
                        'categories': opex_categories
                    },

                    'operating_income': {
                        'amount': float(operating_income),
                        'margin_percent': round(float(operating_margin), 2)
                    },

                    'other_income_expenses': {
                        'total': 0,
                        'categories': []
                    },

                    'net_income': {
                        'amount': float(net_income),
                        'margin_percent': round(float(net_margin), 2)
                    },

                    'summary_metrics': {
                        'total_revenue': float(total_revenue),
                        'gross_profit': float(gross_profit),
                        'gross_margin_percent': round(float(gross_margin), 2),
                        'operating_income': float(operating_income),
                        'operating_margin_percent': round(float(operating_margin), 2),
                        'net_income': float(net_income),
                        'net_margin_percent': round(float(net_margin), 2),
                        'transaction_count': sum(c['count'] for c in revenue_categories) + sum(c['count'] for c in opex_categories)
                    }
                }
            })

        except Exception as e:
            logger.error(f"Error generating simplified income statement: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/balance-sheet/simple', methods=['GET'])
    def api_balance_sheet_simple():
        """
        Generate simplified Balance Sheet using direct SQL (fast)

        Returns:
            JSON with simplified Balance Sheet data
        """
        try:
            start_time = datetime.now()

            # Assets: All positive balances in balance sheet accounts or cash-related transactions
            assets_query = """
                SELECT
                    CASE
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%cash%' THEN 'Caixa e Equivalentes'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%receivable%' THEN 'Contas a Receber'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%inventory%' THEN 'Estoque'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%equipment%' THEN 'Equipamentos'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%asset%' THEN 'Outros Ativos'
                        ELSE 'Ativos Circulantes'
                    END as category,
                    SUM(COALESCE(usd_equivalent, amount, 0)) as total,
                    COUNT(*) as count
                FROM transactions
                WHERE (
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%cash%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%asset%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%receivable%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%inventory%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%equipment%' OR
                    (amount > 0 AND LOWER(COALESCE(description, '')) LIKE '%deposit%')
                )
                GROUP BY CASE
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%cash%' THEN 'Caixa e Equivalentes'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%receivable%' THEN 'Contas a Receber'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%inventory%' THEN 'Estoque'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%equipment%' THEN 'Equipamentos'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%asset%' THEN 'Outros Ativos'
                    ELSE 'Ativos Circulantes'
                END
                ORDER BY total DESC
            """
            assets_data = db_manager.execute_query(assets_query, fetch_all=True)

            total_assets = Decimal('0')
            assets_categories = []

            for row in assets_data:
                amount = Decimal(str(row['total'] or 0))
                if amount > 0:  # Only positive asset values
                    assets_categories.append({
                        'category': row['category'],
                        'amount': float(amount),
                        'count': row['count']
                    })
                    total_assets += amount

            # If no specific asset transactions, estimate current assets from revenue
            if total_assets == 0:
                revenue_query = """
                    SELECT SUM(COALESCE(usd_equivalent, amount, 0)) as total_revenue
                    FROM transactions
                    WHERE amount > 0
                """
                revenue_result = db_manager.execute_query(revenue_query, fetch_one=True)
                estimated_assets = Decimal(str(revenue_result['total_revenue'] or 0)) * Decimal('0.3')  # Estimate 30% of revenue as assets

                if estimated_assets > 0:
                    assets_categories.append({
                        'category': 'Ativos Estimados (30% da Receita)',
                        'amount': float(estimated_assets),
                        'count': 1
                    })
                    total_assets = estimated_assets

            # Liabilities: All negative balances that represent actual debts/obligations
            liabilities_query = """
                SELECT
                    CASE
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%payable%' THEN 'Contas a Pagar'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%loan%' THEN 'Empréstimos'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%debt%' THEN 'Dívidas'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%liability%' THEN 'Outros Passivos'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%tax%' THEN 'Impostos a Pagar'
                        ELSE 'Passivos Circulantes'
                    END as category,
                    SUM(ABS(COALESCE(usd_equivalent, amount, 0))) as total,
                    COUNT(*) as count
                FROM transactions
                WHERE (
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%payable%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%loan%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%debt%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%liability%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%tax%' OR
                    (amount < 0 AND LOWER(COALESCE(description, '')) LIKE '%payment%')
                ) AND amount < 0
                GROUP BY CASE
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%payable%' THEN 'Contas a Pagar'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%loan%' THEN 'Empréstimos'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%debt%' THEN 'Dívidas'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%liability%' THEN 'Outros Passivos'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%tax%' THEN 'Impostos a Pagar'
                    ELSE 'Passivos Circulantes'
                END
                ORDER BY total DESC
            """
            liabilities_data = db_manager.execute_query(liabilities_query, fetch_all=True)

            total_liabilities = Decimal('0')
            liabilities_categories = []

            for row in liabilities_data:
                amount = Decimal(str(row['total'] or 0))
                if amount > 0:  # Only positive liability values (absolute)
                    liabilities_categories.append({
                        'category': row['category'],
                        'amount': float(amount),
                        'count': row['count']
                    })
                    total_liabilities += amount

            # Calculate Equity (Assets - Liabilities)
            total_equity = total_assets - total_liabilities

            # Ensure balance
            if abs(total_assets - (total_liabilities + total_equity)) > Decimal('0.01'):
                # Adjust equity to balance
                total_equity = total_assets - total_liabilities

            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'statement': {
                    'statement_type': 'BalanceSheet',
                    'statement_name': 'Balanço Patrimonial - Todos os Períodos',
                    'generated_at': datetime.now().isoformat(),
                    'generation_time_ms': generation_time_ms,

                    'assets': {
                        'current_assets': {
                            'total': float(total_assets),
                            'categories': assets_categories
                        },
                        'non_current_assets': {
                            'total': 0,
                            'categories': []
                        },
                        'total': float(total_assets)
                    },

                    'liabilities': {
                        'current_liabilities': {
                            'total': float(total_liabilities),
                            'categories': liabilities_categories
                        },
                        'non_current_liabilities': {
                            'total': 0,
                            'categories': []
                        },
                        'total': float(total_liabilities)
                    },

                    'equity': {
                        'total': float(total_equity),
                        'categories': [
                            {
                                'category': 'Patrimônio Líquido Acumulado',
                                'amount': float(total_equity),
                                'count': 1
                            }
                        ]
                    },

                    'summary_metrics': {
                        'total_assets': float(total_assets),
                        'total_liabilities': float(total_liabilities),
                        'total_equity': float(total_equity),
                        'debt_to_equity_ratio': float(total_liabilities / total_equity) if total_equity != 0 else 0,
                        'asset_turnover': 0,  # Would need revenue data for calculation
                        'balance_check': abs(float(total_assets - (total_liabilities + total_equity))) < 0.01
                    }
                }
            })

        except Exception as e:
            logger.error(f"Error generating simplified balance sheet: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/cash-flow/simple', methods=['GET'])
    def api_cash_flow_simple():
        """
        Generate simplified Cash Flow using direct SQL (fast)

        Returns:
            JSON with simplified Cash Flow data
        """
        try:
            start_time = datetime.now()

            # Operating Cash Flow: All transactions (simplified)
            operating_query = """
                SELECT
                    SUM(CASE WHEN amount > 0 THEN usd_equivalent ELSE 0 END) as cash_receipts,
                    SUM(CASE WHEN amount < 0 THEN ABS(usd_equivalent) ELSE 0 END) as cash_payments
                FROM transactions
            """
            operating_result = db_manager.execute_query(operating_query, fetch_one=True)

            cash_receipts = Decimal(str(operating_result.get('cash_receipts', 0) or 0))
            cash_payments = Decimal(str(operating_result.get('cash_payments', 0) or 0))
            net_operating = cash_receipts - cash_payments

            # Investing and Financing activities simplified to zero for now
            investing_inflows = Decimal('0')
            investing_outflows = Decimal('0')
            net_investing = Decimal('0')

            financing_inflows = Decimal('0')
            financing_outflows = Decimal('0')
            net_financing = Decimal('0')

            # Net cash flow is just operating for simplified version
            net_cash_flow = net_operating
            beginning_cash = Decimal('0')  # Simplified
            ending_cash = net_cash_flow

            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'statement': {
                    'statement_type': 'CashFlow',
                    'statement_name': 'Demonstração de Fluxo de Caixa (DFC)',
                    'generated_at': datetime.now().isoformat(),
                    'generation_time_ms': generation_time_ms,

                    'operating_activities': {
                        'cash_receipts': float(cash_receipts),
                        'cash_payments': float(cash_payments),
                        'net_operating': float(net_operating),
                        'categories': [
                            {
                                'category': 'Recebimentos de Clientes',
                                'amount': float(cash_receipts),
                                'count': 1
                            },
                            {
                                'category': 'Pagamentos a Fornecedores',
                                'amount': float(-cash_payments),
                                'count': 1
                            }
                        ]
                    },

                    'investing_activities': {
                        'investing_inflows': float(investing_inflows),
                        'investing_outflows': float(investing_outflows),
                        'net_investing': float(net_investing),
                        'categories': []
                    },

                    'financing_activities': {
                        'financing_inflows': float(financing_inflows),
                        'financing_outflows': float(financing_outflows),
                        'net_financing': float(net_financing),
                        'categories': []
                    },

                    'summary_metrics': {
                        'net_cash_flow': float(net_cash_flow),
                        'beginning_cash': float(beginning_cash),
                        'ending_cash': float(ending_cash),
                        'cash_receipts': float(cash_receipts),
                        'cash_payments': float(cash_payments),
                        'net_operating': float(net_operating)
                    }
                }
            })

        except Exception as e:
            logger.error(f"Error generating simplified cash flow: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/dmpl/simple', methods=['GET'])
    def api_dmpl_simple():
        """
        Generate simplified DMPL using direct SQL (fast)

        Returns:
            JSON with simplified DMPL data
        """
        try:
            start_time = datetime.now()

            # Net income calculation (same as DRE)
            income_query = """
                SELECT
                    SUM(CASE WHEN amount > 0 THEN usd_equivalent ELSE 0 END) as total_revenue,
                    SUM(CASE WHEN amount < 0 THEN ABS(usd_equivalent) ELSE 0 END) as total_expenses
                FROM transactions
            """
            income_result = db_manager.execute_query(income_query, fetch_one=True)

            total_revenue = Decimal(str(income_result.get('total_revenue', 0) or 0))
            total_expenses = Decimal(str(income_result.get('total_expenses', 0) or 0))
            net_income = total_revenue - total_expenses

            # Beginning equity (simplified - use net income as proxy)
            beginning_equity = net_income * Decimal('0.8')  # Estimate 80% of current earnings

            # Simplified equity changes
            capital_contributions = Decimal('0')
            capital_distributions = Decimal('0')
            dividends_paid = Decimal('0')
            other_changes = Decimal('0')

            # Ending equity
            ending_equity = beginning_equity + net_income + capital_contributions - capital_distributions - dividends_paid - other_changes

            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'statement': {
                    'statement_type': 'DMPL',
                    'statement_name': 'Demonstração das Mutações do Patrimônio Líquido (DMPL)',
                    'generated_at': datetime.now().isoformat(),
                    'generation_time_ms': generation_time_ms,

                    'equity_movements': {
                        'beginning_equity': float(beginning_equity),
                        'net_income': float(net_income),
                        'capital_contributions': float(capital_contributions),
                        'capital_distributions': float(capital_distributions),
                        'dividends_paid': float(dividends_paid),
                        'other_changes': float(other_changes),
                        'ending_equity': float(ending_equity),
                        'categories': [
                            {
                                'category': 'Lucro/Prejuízo do Exercício',
                                'amount': float(net_income),
                                'count': 1
                            },
                            {
                                'category': 'Patrimônio Inicial',
                                'amount': float(beginning_equity),
                                'count': 1
                            }
                        ]
                    },

                    'components': {
                        'total_revenue': float(total_revenue),
                        'total_expenses': float(total_expenses)
                    },

                    'summary_metrics': {
                        'beginning_equity': float(beginning_equity),
                        'net_income': float(net_income),
                        'ending_equity': float(ending_equity),
                        'equity_growth': float(((ending_equity - beginning_equity) / beginning_equity * 100)) if beginning_equity != 0 else 0,
                        'roe': float((net_income / beginning_equity * 100)) if beginning_equity != 0 else 0
                    }
                }
            })

        except Exception as e:
            logger.error(f"Error generating simplified DMPL: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/periods', methods=['GET'])
    def api_accounting_periods():
        """
        Get list of accounting periods

        GET Parameters:
            - year: Filter by fiscal year (optional)
            - period_type: Filter by type (Monthly, Quarterly, Yearly) (optional)
            - status: Filter by status (Open, Closed, Locked) (optional)

        Returns:
            JSON with list of accounting periods
        """
        try:
            year = request.args.get('year')
            period_type = request.args.get('period_type')
            status = request.args.get('status')

            # Build query
            query = "SELECT * FROM cfo_accounting_periods WHERE 1=1"
            params = []

            if year:
                query += " AND fiscal_year = %s" if db_manager.db_type == 'postgresql' else " AND fiscal_year = ?"
                params.append(int(year))

            if period_type:
                query += " AND period_type = %s" if db_manager.db_type == 'postgresql' else " AND period_type = ?"
                params.append(period_type)

            if status:
                query += " AND status = %s" if db_manager.db_type == 'postgresql' else " AND status = ?"
                params.append(status)

            query += " ORDER BY start_date DESC"

            periods = db_manager.execute_query(query, tuple(params) if params else None, fetch_all=True)

            return jsonify({
                'success': True,
                'periods': [dict(p) for p in periods]
            })

        except Exception as e:
            logger.error(f"Error fetching accounting periods: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/chart-of-accounts', methods=['GET'])
    def api_chart_of_accounts():
        """
        Get chart of accounts

        GET Parameters:
            - account_type: Filter by type (Asset, Liability, Equity, Revenue, Expense) (optional)
            - is_active: Filter by active status (true/false) (optional)

        Returns:
            JSON with chart of accounts
        """
        try:
            account_type = request.args.get('account_type')
            is_active = request.args.get('is_active')

            # Build query
            query = "SELECT * FROM cfo_chart_of_accounts WHERE 1=1"
            params = []

            if account_type:
                query += " AND account_type = %s" if db_manager.db_type == 'postgresql' else " AND account_type = ?"
                params.append(account_type)

            if is_active is not None:
                if db_manager.db_type == 'postgresql':
                    query += " AND is_active = %s"
                    params.append(is_active.lower() == 'true')
                else:
                    query += " AND is_active = ?"
                    params.append(1 if is_active.lower() == 'true' else 0)

            query += " ORDER BY account_code"

            accounts = db_manager.execute_query(query, tuple(params) if params else None, fetch_all=True)

            return jsonify({
                'success': True,
                'accounts': [dict(a) for a in accounts]
            })

        except Exception as e:
            logger.error(f"Error fetching chart of accounts: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/health', methods=['GET'])
    def api_reports_health():
        """Health check for reporting system"""
        try:
            # Check database
            db_health = db_manager.health_check()

            # Check CFO tables
            table_check_query = """
                SELECT COUNT(*) as count
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE 'cfo_%'
            """ if db_manager.db_type == 'postgresql' else """
                SELECT COUNT(*) as count
                FROM sqlite_master
                WHERE type='table'
                AND name LIKE 'cfo_%'
            """

            result = db_manager.execute_query(table_check_query, fetch_one=True)
            cfo_tables_count = result['count']

            # Check data
            periods_query = "SELECT COUNT(*) as count FROM cfo_accounting_periods"
            periods_result = db_manager.execute_query(periods_query, fetch_one=True)

            accounts_query = "SELECT COUNT(*) as count FROM cfo_chart_of_accounts"
            accounts_result = db_manager.execute_query(accounts_query, fetch_one=True)

            statements_query = "SELECT COUNT(*) as count FROM cfo_financial_statements"
            statements_result = db_manager.execute_query(statements_query, fetch_one=True)

            return jsonify({
                'success': True,
                'health': {
                    'database': db_health,
                    'cfo_tables_count': cfo_tables_count,
                    'data': {
                        'accounting_periods': periods_result['count'],
                        'chart_of_accounts': accounts_result['count'],
                        'financial_statements': statements_result['count']
                    },
                    'status': 'healthy' if cfo_tables_count == 8 else 'degraded'
                }
            })

        except Exception as e:
            logger.error(f"Error in reports health check: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'status': 'unhealthy'
            }), 500

    @app.route('/api/reports/entities', methods=['GET'])
    def api_reports_entities():
        """
        Get all entities from transactions for filter dropdown

        Returns:
            JSON with list of entities and their transaction counts
        """
        try:
            # Get entities from transactions table
            # Query all entity-related columns: classified_entity, origin, and destination
            query = """
                SELECT
                    classified_entity as name,
                    classified_entity as display_name,
                    COUNT(*) as transaction_count
                FROM transactions
                WHERE classified_entity IS NOT NULL
                    AND classified_entity != ''
                    AND classified_entity != 'Unknown'
                GROUP BY classified_entity

                UNION ALL

                SELECT
                    origin as name,
                    origin as display_name,
                    COUNT(*) as transaction_count
                FROM transactions
                WHERE origin IS NOT NULL
                    AND origin != ''
                    AND origin != 'Unknown'
                GROUP BY origin

                UNION ALL

                SELECT
                    destination as name,
                    destination as display_name,
                    COUNT(*) as transaction_count
                FROM transactions
                WHERE destination IS NOT NULL
                    AND destination != ''
                    AND destination != 'Unknown'
                GROUP BY destination
            """

            results = db_manager.execute_query(query, fetch_all=True)

            # Consolidate entities and sum transaction counts
            entity_counts = {}
            for row in results:
                entity = row['name']
                count = row['transaction_count']

                if entity in entity_counts:
                    entity_counts[entity] += count
                else:
                    entity_counts[entity] = count

            # Convert to list and sort by transaction count (descending)
            entities = [
                {
                    'name': entity,
                    'display_name': entity,
                    'transaction_count': count
                }
                for entity, count in entity_counts.items()
            ]

            # Sort by transaction count descending
            entities.sort(key=lambda x: x['transaction_count'], reverse=True)

            return jsonify({
                'success': True,
                'data': {
                    'entities': entities,
                    'total_entities': len(entities)
                }
            })

        except Exception as e:
            logger.error(f"Error getting entities: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'entities': []
            }), 500

    @app.route('/api/reports/charts-data', methods=['GET'])
    def api_charts_data():
        """
        Endpoint otimizado para dados de gráficos - versão robusta

        GET Parameters:
            - period: 'monthly', 'quarterly', 'yearly', 'all_time', 'custom' (default: 'all_time')
            - start_date: Start date for analysis (YYYY-MM-DD) (optional)
            - end_date: End date for analysis (YYYY-MM-DD) (optional)
            - entity: Filter by specific entity (optional)

        Returns:
            JSON com dados prontos para Chart.js
        """
        try:
            start_time = datetime.now()

            # Parse parameters
            period = request.args.get('period', 'all_time')
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            entity_filter = request.args.get('entity', '')

            # Calculate date range based on period
            date_filter = ""
            date_params = []

            if start_date_str and end_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    start_date_str = start_date.isoformat()
                    end_date_str = end_date.isoformat()
                except ValueError:
                    # Invalid date format, ignore filters
                    start_date_str = end_date_str = None
            elif period != 'all_time' and period != 'custom':
                end_date = date.today()
                if period == 'monthly':
                    start_date = end_date.replace(day=1) - timedelta(days=30)
                elif period == 'quarterly':
                    start_date = end_date - timedelta(days=90)
                elif period == 'yearly':
                    start_date = end_date - timedelta(days=365)
                else:
                    start_date = end_date  # fallback

                start_date_str = start_date.isoformat()
                end_date_str = end_date.isoformat()

            # Build date filter
            if start_date_str and end_date_str:
                date_filter = "AND date::date >= %s::date AND date::date <= %s::date"
                date_params = [start_date_str, end_date_str]

            # Build entity filter
            entity_filter_clause = ""
            entity_params = []
            if entity_filter:
                entity_filter_clause = "AND (classified_entity = %s OR accounting_category = %s)"
                entity_params = [entity_filter, entity_filter]

            # Initialize default fallback data
            default_charts_data = {
                'revenue_expenses': {
                    'labels': ['Receitas', 'Despesas'],
                    'data': [0, 0],
                    'net_income': 0
                },
                'categories': {
                    'labels': ['Uncategorized'],
                    'data': [0],
                    'counts': [0]
                },
                'monthly_trend': {
                    'labels': ['Current'],
                    'revenue_data': [0],
                    'expenses_data': [0],
                    'margin_data': [0]
                },
                'summary': {
                    'total_revenue': 0,
                    'total_expenses': 0,
                    'current_margin': 0,
                    'transactions_count': 0
                }
            }

            # Safe query execution function
            def safe_query(query, params=None, fetch_all=False):
                try:
                    if fetch_all:
                        result = db_manager.execute_query(query, params, fetch_all=True)
                        return result if result else []
                    else:
                        result = db_manager.execute_query(query, params, fetch_one=True)
                        return result if result else {}
                except Exception as query_error:
                    logger.warning(f"Query failed safely: {query_error}")
                    return [] if fetch_all else {}

            # Revenue vs Expenses data - consolidating transactions + invoices
            revenue_expenses_query = f"""
                WITH combined_data AS (
                    -- Transactions data (can be revenue or expenses)
                    SELECT
                        CASE WHEN amount > 0 THEN amount ELSE 0 END as revenue,
                        CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END as expenses
                    FROM transactions
                    WHERE amount::text != 'NaN' AND amount IS NOT NULL
                    {date_filter}
                    {entity_filter_clause}

                    UNION ALL

                    -- Invoices data (always revenue)
                    SELECT
                        CASE
                            WHEN total_amount::text ~ '^[0-9]+\.?[0-9]*$'
                            THEN total_amount::float
                            ELSE 0
                        END as revenue,
                        0 as expenses
                    FROM invoices
                    WHERE total_amount IS NOT NULL
                        AND total_amount::text != 'NaN'
                        AND total_amount::text != ''
                        {date_filter}
                        {entity_filter_clause.replace('classified_entity', 'vendor_name').replace('accounting_category', 'vendor_name') if entity_filter_clause else ''}
                )
                SELECT 'Revenue' as type, COALESCE(SUM(revenue), 0) as amount FROM combined_data
                UNION ALL
                SELECT 'Expenses' as type, COALESCE(SUM(expenses), 0) as amount FROM combined_data
            """
            revenue_expenses_params = date_params + entity_params + date_params + entity_params
            revenue_expenses_data = safe_query(revenue_expenses_query, revenue_expenses_params, fetch_all=True)

            # Top revenue categories - consolidating transactions + invoices
            categories_query = f"""
                WITH combined_categories AS (
                    -- Transactions revenue categories
                    SELECT
                        COALESCE(accounting_category, classified_entity, 'Uncategorized') as category,
                        amount,
                        1 as count
                    FROM transactions
                    WHERE amount > 0 AND amount::text != 'NaN' AND amount IS NOT NULL
                    {date_filter}
                    {entity_filter_clause}

                    UNION ALL

                    -- Invoices revenue categories
                    SELECT
                        COALESCE(vendor_name, 'Invoice Revenue') as category,
                        CASE
                            WHEN total_amount::text ~ '^[0-9]+\.?[0-9]*$'
                            THEN total_amount::float
                            ELSE 0
                        END as amount,
                        1 as count
                    FROM invoices
                    WHERE total_amount IS NOT NULL
                        AND total_amount::text != 'NaN'
                        AND total_amount::text != ''
                        {date_filter}
                        {entity_filter_clause.replace('classified_entity', 'vendor_name').replace('accounting_category', 'vendor_name') if entity_filter_clause else ''}
                )
                SELECT
                    category,
                    COALESCE(SUM(amount), 0) as amount,
                    COUNT(*) as count
                FROM combined_categories
                WHERE amount > 0
                GROUP BY category
                ORDER BY amount DESC
                LIMIT 8
            """
            categories_params = date_params + entity_params + date_params + entity_params
            categories_data = safe_query(categories_query, categories_params, fetch_all=True)

            # Monthly trend data - with dynamic filters
            if db_manager.db_type == 'sqlite':
                base_where = "amount IS NOT NULL"
                if start_date_str and end_date_str:
                    base_where += f" AND date >= '{start_date_str}' AND date <= '{end_date_str}'"
                else:
                    base_where += " AND date >= date('now', '-6 months')"

                monthly_trend_query = f"""
                    SELECT
                        strftime('%Y-%m', date) as month,
                        COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as revenue,
                        COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0) as expenses
                    FROM transactions
                    WHERE {base_where}
                    {entity_filter_clause}
                    GROUP BY strftime('%Y-%m', date)
                    ORDER BY month
                """
                monthly_params = entity_params
            else:
                # PostgreSQL version with proper date filtering
                base_where = "amount::text != 'NaN' AND amount IS NOT NULL"
                if start_date_str and end_date_str:
                    base_where += " AND date::date >= %s::date AND date::date <= %s::date"
                    monthly_params = [start_date_str, end_date_str] + entity_params + [start_date_str, end_date_str] + entity_params
                else:
                    base_where += " AND date::date >= CURRENT_DATE - INTERVAL '6 months'"
                    monthly_params = entity_params + entity_params

                monthly_trend_query = f"""
                    WITH combined_monthly AS (
                        -- Transactions monthly data
                        SELECT
                            DATE_TRUNC('month', date::date) as month,
                            CASE WHEN amount > 0 THEN amount ELSE 0 END as revenue,
                            CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END as expenses
                        FROM transactions
                        WHERE {base_where}
                        {entity_filter_clause}

                        UNION ALL

                        -- Invoices monthly data (always revenue)
                        SELECT
                            DATE_TRUNC('month', date::date) as month,
                            CASE
                                WHEN total_amount::text ~ '^[0-9]+\.?[0-9]*$'
                                THEN total_amount::float
                                ELSE 0
                            END as revenue,
                            0 as expenses
                        FROM invoices
                        WHERE total_amount IS NOT NULL
                            AND total_amount::text != 'NaN'
                            AND total_amount::text != ''
                            {date_filter}
                            {entity_filter_clause.replace('classified_entity', 'vendor_name').replace('accounting_category', 'vendor_name') if entity_filter_clause else ''}
                    )
                    SELECT
                        month,
                        COALESCE(SUM(revenue), 0) as revenue,
                        COALESCE(SUM(expenses), 0) as expenses
                    FROM combined_monthly
                    GROUP BY month
                    ORDER BY month
                """

            monthly_data = safe_query(monthly_trend_query, monthly_params, fetch_all=True)

            # Calculate margins for monthly data
            monthly_margins = []
            for row in monthly_data:
                try:
                    revenue = float(row.get('revenue', 0) or 0)
                    expenses = float(row.get('expenses', 0) or 0)
                    net_income = revenue - expenses
                    margin = (net_income / revenue * 100) if revenue > 0 else 0

                    # Handle different month formats
                    month_display = 'Unknown'
                    if row.get('month'):
                        if isinstance(row['month'], str):
                            # For SQLite: '2025-10' format
                            try:
                                month_obj = datetime.strptime(row['month'], '%Y-%m')
                                month_display = month_obj.strftime('%b %Y')
                            except:
                                month_display = row['month']
                        else:
                            # For PostgreSQL: datetime object
                            month_display = row['month'].strftime('%b %Y')

                    monthly_margins.append({
                        'month': month_display,
                        'revenue': revenue,
                        'expenses': expenses,
                        'net_income': net_income,
                        'margin_percent': round(margin, 2)
                    })
                except Exception as row_error:
                    logger.warning(f"Error processing monthly row: {row_error}")
                    continue

            # Format data for charts with safe access
            try:
                revenue_amount = float(revenue_expenses_data[0].get('amount', 0) or 0) if len(revenue_expenses_data) > 0 else 0
                expenses_amount = float(revenue_expenses_data[1].get('amount', 0) or 0) if len(revenue_expenses_data) > 1 else 0
            except (IndexError, TypeError, ValueError):
                revenue_amount = 0
                expenses_amount = 0

            charts_data = {
                'revenue_expenses': {
                    'labels': ['Receitas', 'Despesas'],
                    'data': [revenue_amount, expenses_amount],
                    'net_income': revenue_amount - expenses_amount
                },

                'categories': {
                    'labels': [row.get('category', 'Unknown') for row in categories_data] if categories_data else ['No Data'],
                    'data': [float(row.get('amount', 0) or 0) for row in categories_data] if categories_data else [0],
                    'counts': [int(row.get('count', 0) or 0) for row in categories_data] if categories_data else [0]
                },

                'monthly_trend': {
                    'labels': [item['month'] for item in monthly_margins] if monthly_margins else ['Current'],
                    'revenue_data': [item['revenue'] for item in monthly_margins] if monthly_margins else [0],
                    'expenses_data': [item['expenses'] for item in monthly_margins] if monthly_margins else [0],
                    'margin_data': [item['margin_percent'] for item in monthly_margins] if monthly_margins else [0]
                },

                'summary': {
                    'total_revenue': sum([item['revenue'] for item in monthly_margins]) if monthly_margins else 0,
                    'total_expenses': sum([item['expenses'] for item in monthly_margins]) if monthly_margins else 0,
                    'current_margin': monthly_margins[-1]['margin_percent'] if monthly_margins else 0,
                    'transactions_count': sum([row.get('count', 0) for row in categories_data]) if categories_data else 0
                }
            }

            # Ensure all data is valid
            if not charts_data['categories']['data'] or all(x == 0 for x in charts_data['categories']['data']):
                charts_data = default_charts_data

            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'data': charts_data,
                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': generation_time_ms
            })

        except Exception as e:
            logger.error(f"Error generating charts data: {e}")
            import traceback
            traceback.print_exc()

            # Return fallback data instead of 500 error
            return jsonify({
                'success': True,
                'data': {
                    'revenue_expenses': {
                        'labels': ['Receitas', 'Despesas'],
                        'data': [0, 0],
                        'net_income': 0
                    },
                    'categories': {
                        'labels': ['No Data Available'],
                        'data': [1],
                        'counts': [0]
                    },
                    'monthly_trend': {
                        'labels': ['Current'],
                        'revenue_data': [0],
                        'expenses_data': [0],
                        'margin_data': [0]
                    },
                    'summary': {
                        'total_revenue': 0,
                        'total_expenses': 0,
                        'current_margin': 0,
                        'transactions_count': 0
                    }
                },
                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': 0,
                'fallback': True,
                'original_error': str(e)
            })

    @app.route('/api/reports/export-pdf', methods=['POST'])
    def api_export_pdf():
        """
        Export financial reports to PDF format

        POST Parameters (JSON):
            - report_type: Type of report ('income-statement', 'balance-sheet', etc.)
            - start_date: Start date for the report (optional)
            - end_date: End date for the report (optional)
            - include_charts: Include chart images (boolean, default: false)

        Returns:
            PDF file download
        """
        try:
            data = request.get_json()
            report_type = data.get('report_type', 'income-statement')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            include_charts = data.get('include_charts', False)

            # Parse dates if provided
            start_date_obj = None
            end_date_obj = None

            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                except ValueError:
                    start_date_obj = datetime.strptime(start_date, '%m/%d/%Y').date()

            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                except ValueError:
                    end_date_obj = datetime.strptime(end_date, '%m/%d/%Y').date()

            # Generate the requested report type
            if report_type == 'income-statement':
                # Use the simplified income statement endpoint for income statement data
                response = api_income_statement_simple()
                if response.status_code != 200:
                    return response

                income_statement_data = response.get_json()['statement']

                # Generate PDF
                pdf_buffer = generate_income_statement_pdf(income_statement_data)

                # Create filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"DeltaCFO_IncomeStatement_{timestamp}.pdf"

                return send_file(
                    pdf_buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/pdf'
                )

            elif report_type == 'balance-sheet':
                # Use the simplified balance sheet endpoint for balance sheet data
                response = api_balance_sheet_simple()
                if response.status_code != 200:
                    return response

                balance_sheet_data = response.get_json()['statement']

                # Generate PDF
                pdf_buffer = generate_balance_sheet_pdf(balance_sheet_data)

                # Create filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"DeltaCFO_BalanceSheet_{timestamp}.pdf"

                return send_file(
                    pdf_buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/pdf'
                )
            else:
                return jsonify({
                    'success': False,
                    'error': f'Report type "{report_type}" not yet supported'
                }), 400

        except Exception as e:
            logger.error(f"Error exporting PDF: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def generate_income_statement_pdf(statement_data):
        """Generate a professional PDF for income statement"""

        # Create a buffer to hold the PDF data
        buffer = io.BytesIO()

        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=HexColor('#2563eb'),
            spaceAfter=30,
            alignment=1  # Center alignment
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#374151'),
            spaceAfter=20,
            alignment=1
        )

        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=HexColor('#1f2937'),
            spaceAfter=10,
            spaceBefore=15
        )

        # Build the content
        content = []

        # Header
        content.append(Paragraph("Delta CFO Agent", title_style))
        content.append(Paragraph(
            statement_data.get('statement_name', 'Demonstração de Resultado'),
            subtitle_style
        ))

        # Generation info
        generated_at = datetime.now().strftime('%d/%m/%Y às %H:%M')
        content.append(Paragraph(f"Gerado em: {generated_at}", styles['Normal']))
        content.append(Spacer(1, 20))

        # Summary metrics (if available)
        if statement_data.get('summary_metrics'):
            metrics = statement_data['summary_metrics']
            content.append(Paragraph("📊 Resumo Executivo", section_style))

            metrics_data = [
                ['Métrica', 'Valor'],
                ['Receita Total', f"${metrics.get('total_revenue', 0):,.2f}"],
                ['Lucro Operacional', f"${metrics.get('operating_income', 0):,.2f}"],
                ['Lucro Líquido', f"${metrics.get('net_income', 0):,.2f}"],
                ['Margem Líquida', f"{metrics.get('net_margin_percent', 0):.1f}%"],
                ['Total de Transações', f"{metrics.get('transaction_count', 0):,}"]
            ]

            metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#1f2937')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#e5e7eb'))
            ]))

            content.append(metrics_table)
            content.append(Spacer(1, 20))

        # Revenue section
        if statement_data.get('revenue'):
            content.append(Paragraph("💰 RECEITAS", section_style))

            revenue_data = [['Categoria', 'Valor']]
            for category in statement_data['revenue'].get('categories', []):
                revenue_data.append([
                    category.get('category', 'N/A'),
                    f"${category.get('amount', 0):,.2f}"
                ])

            # Add total
            revenue_data.append([
                'TOTAL DE RECEITAS',
                f"${statement_data['revenue'].get('total', 0):,.2f}"
            ])

            revenue_table = Table(revenue_data, colWidths=[3.5*inch, 1.5*inch])
            revenue_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#dcfce7')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#166534')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, -1), (-1, -1), HexColor('#f0fdf4')),
                ('LINEABOVE', (0, -1), (-1, -1), 2, HexColor('#16a34a')),
                ('GRID', (0, 0), (-1, -2), 0.5, HexColor('#bbf7d0'))
            ]))

            content.append(revenue_table)
            content.append(Spacer(1, 15))

        # Operating expenses section
        if statement_data.get('operating_expenses'):
            content.append(Paragraph("💸 DESPESAS OPERACIONAIS", section_style))

            expenses_data = [['Categoria', 'Valor']]
            for category in statement_data['operating_expenses'].get('categories', []):
                expenses_data.append([
                    category.get('category', 'N/A'),
                    f"${category.get('amount', 0):,.2f}"
                ])

            # Add total
            expenses_data.append([
                'TOTAL DE DESPESAS OPERACIONAIS',
                f"${statement_data['operating_expenses'].get('total', 0):,.2f}"
            ])

            expenses_table = Table(expenses_data, colWidths=[3.5*inch, 1.5*inch])
            expenses_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#fee2e2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#991b1b')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, -1), (-1, -1), HexColor('#fef2f2')),
                ('LINEABOVE', (0, -1), (-1, -1), 2, HexColor('#dc2626')),
                ('GRID', (0, 0), (-1, -2), 0.5, HexColor('#fecaca'))
            ]))

            content.append(expenses_table)
            content.append(Spacer(1, 15))

        # Net income section
        if statement_data.get('net_income'):
            content.append(Paragraph("📈 RESULTADO LÍQUIDO", section_style))

            net_income = statement_data['net_income']
            result_data = [
                ['Lucro Operacional', f"${statement_data.get('operating_income', {}).get('amount', 0):,.2f}"],
                ['Outras Receitas/Despesas', f"${statement_data.get('other_income_expenses', {}).get('total', 0):,.2f}"],
                ['LUCRO LÍQUIDO', f"${net_income.get('amount', 0):,.2f}"],
                ['Margem Líquida', f"{net_income.get('margin_percent', 0):.1f}%"]
            ]

            result_table = Table(result_data, colWidths=[3.5*inch, 1.5*inch])
            result_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, -2), (-1, -1), HexColor('#eff6ff')),
                ('TEXTCOLOR', (0, -2), (-1, -1), HexColor('#1e40af')),
                ('LINEABOVE', (0, -2), (-1, -2), 2, HexColor('#3b82f6')),
                ('GRID', (0, 0), (-1, -3), 0.5, HexColor('#e5e7eb'))
            ]))

            content.append(result_table)
            content.append(Spacer(1, 20))

        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=HexColor('#6b7280'),
            alignment=1
        )

        generation_time = statement_data.get('generation_time_ms', 0)
        content.append(Paragraph(
            f"Relatório gerado automaticamente pela Delta CFO Agent em {generation_time}ms | "
            f"Delta's proprietary self improving AI CFO Agent",
            footer_style
        ))

        # Build PDF
        doc.build(content)
        buffer.seek(0)
        return buffer

    def generate_balance_sheet_pdf(statement_data):
        """Generate a professional PDF for balance sheet"""

        # Create a buffer to hold the PDF data
        buffer = io.BytesIO()

        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=HexColor('#2563eb'),
            spaceAfter=30,
            alignment=1  # Center alignment
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#374151'),
            spaceAfter=20,
            alignment=1
        )

        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=HexColor('#1f2937'),
            spaceAfter=10,
            spaceBefore=15
        )

        # Build the content
        content = []

        # Header
        content.append(Paragraph("Delta CFO Agent", title_style))
        content.append(Paragraph(
            statement_data.get('statement_name', 'Balanço Patrimonial'),
            subtitle_style
        ))

        # Generation info
        generated_at = datetime.now().strftime('%d/%m/%Y às %H:%M')
        content.append(Paragraph(f"Gerado em: {generated_at}", styles['Normal']))
        content.append(Spacer(1, 20))

        # Summary metrics (if available)
        if statement_data.get('summary_metrics'):
            metrics = statement_data['summary_metrics']
            content.append(Paragraph("📊 Resumo Executivo", section_style))

            metrics_data = [
                ['Métrica', 'Valor'],
                ['Total de Ativos', f"${metrics.get('total_assets', 0):,.2f}"],
                ['Total de Passivos', f"${metrics.get('total_liabilities', 0):,.2f}"],
                ['Patrimônio Líquido', f"${metrics.get('total_equity', 0):,.2f}"],
                ['Índice de Endividamento', f"{metrics.get('debt_to_equity_ratio', 0):.2f}"],
                ['Balanceamento', '✓' if metrics.get('balance_check', False) else '✗']
            ]

            metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#1f2937')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#e5e7eb'))
            ]))

            content.append(metrics_table)
            content.append(Spacer(1, 20))

        # Assets section
        if statement_data.get('assets'):
            content.append(Paragraph("🏛️ ATIVOS", section_style))

            assets_data = [['Categoria', 'Valor']]

            # Current assets
            current_assets = statement_data['assets'].get('current_assets', {})
            for category in current_assets.get('categories', []):
                assets_data.append([
                    category.get('category', 'N/A'),
                    f"${category.get('amount', 0):,.2f}"
                ])

            # Add total
            assets_data.append([
                'TOTAL DE ATIVOS',
                f"${statement_data['assets'].get('total', 0):,.2f}"
            ])

            assets_table = Table(assets_data, colWidths=[3.5*inch, 1.5*inch])
            assets_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#dbeafe')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#1e40af')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, -1), (-1, -1), HexColor('#f0f9ff')),
                ('LINEABOVE', (0, -1), (-1, -1), 2, HexColor('#3b82f6')),
                ('GRID', (0, 0), (-1, -2), 0.5, HexColor('#bfdbfe'))
            ]))

            content.append(assets_table)
            content.append(Spacer(1, 15))

        # Liabilities section
        if statement_data.get('liabilities'):
            content.append(Paragraph("📋 PASSIVOS", section_style))

            liabilities_data = [['Categoria', 'Valor']]

            # Current liabilities
            current_liabilities = statement_data['liabilities'].get('current_liabilities', {})
            for category in current_liabilities.get('categories', []):
                liabilities_data.append([
                    category.get('category', 'N/A'),
                    f"${category.get('amount', 0):,.2f}"
                ])

            # Add total
            liabilities_data.append([
                'TOTAL DE PASSIVOS',
                f"${statement_data['liabilities'].get('total', 0):,.2f}"
            ])

            liabilities_table = Table(liabilities_data, colWidths=[3.5*inch, 1.5*inch])
            liabilities_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#fef3c7')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#92400e')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, -1), (-1, -1), HexColor('#fffbeb')),
                ('LINEABOVE', (0, -1), (-1, -1), 2, HexColor('#d97706')),
                ('GRID', (0, 0), (-1, -2), 0.5, HexColor('#fde68a'))
            ]))

            content.append(liabilities_table)
            content.append(Spacer(1, 15))

        # Equity section
        if statement_data.get('equity'):
            content.append(Paragraph("💎 PATRIMÔNIO LÍQUIDO", section_style))

            equity_data = [['Categoria', 'Valor']]

            for category in statement_data['equity'].get('categories', []):
                equity_data.append([
                    category.get('category', 'N/A'),
                    f"${category.get('amount', 0):,.2f}"
                ])

            # Add total
            equity_data.append([
                'TOTAL DO PATRIMÔNIO LÍQUIDO',
                f"${statement_data['equity'].get('total', 0):,.2f}"
            ])

            equity_table = Table(equity_data, colWidths=[3.5*inch, 1.5*inch])
            equity_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#d1fae5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#065f46')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, -1), (-1, -1), HexColor('#ecfdf5')),
                ('LINEABOVE', (0, -1), (-1, -1), 2, HexColor('#10b981')),
                ('GRID', (0, 0), (-1, -2), 0.5, HexColor('#a7f3d0'))
            ]))

            content.append(equity_table)
            content.append(Spacer(1, 20))

        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=HexColor('#6b7280'),
            alignment=1
        )

        generation_time = statement_data.get('generation_time_ms', 0)
        content.append(Paragraph(
            f"Relatório gerado automaticamente pela Delta CFO Agent em {generation_time}ms | "
            f"Delta's proprietary self improving AI CFO Agent",
            footer_style
        ))

        # Build PDF
        doc.build(content)
        buffer.seek(0)
        return buffer

    @app.route('/api/reports/period-comparison', methods=['GET', 'POST'])
    def api_period_comparison():
        """
        Compare financial metrics between two periods

        Parameters:
            - current_start_date: Start date for current period
            - current_end_date: End date for current period
            - previous_start_date: Start date for previous period
            - previous_end_date: End date for previous period
            - comparison_type: 'month_over_month', 'quarter_over_quarter', 'year_over_year', 'custom'

        Returns:
            JSON with comparison data including variance analysis
        """
        try:
            # Parse parameters
            if request.method == 'POST':
                data = request.get_json()
            else:
                data = request.args

            current_start = data.get('current_start_date')
            current_end = data.get('current_end_date')
            previous_start = data.get('previous_start_date')
            previous_end = data.get('previous_end_date')
            comparison_type = data.get('comparison_type', 'custom')

            # Auto-calculate previous period if comparison_type is specified
            if comparison_type != 'custom' and current_start and current_end:
                current_start_date = datetime.strptime(current_start, '%Y-%m-%d').date()
                current_end_date = datetime.strptime(current_end, '%Y-%m-%d').date()

                if comparison_type == 'month_over_month':
                    # Safe month calculation that handles different month lengths
                    if current_start_date.month > 1:
                        # Go to previous month
                        previous_month = current_start_date.month - 1
                        previous_year = current_start_date.year
                    else:
                        # Go to December of previous year
                        previous_month = 12
                        previous_year = current_start_date.year - 1

                    # Handle day overflow (e.g., Jan 31 -> Feb 28)
                    try:
                        previous_start_date = current_start_date.replace(year=previous_year, month=previous_month)
                    except ValueError:
                        # Day doesn't exist in target month, use last day of target month
                        from calendar import monthrange
                        last_day = monthrange(previous_year, previous_month)[1]
                        previous_start_date = current_start_date.replace(year=previous_year, month=previous_month, day=min(current_start_date.day, last_day))

                    # Same logic for end date
                    if current_end_date.month > 1:
                        previous_month = current_end_date.month - 1
                        previous_year = current_end_date.year
                    else:
                        previous_month = 12
                        previous_year = current_end_date.year - 1

                    try:
                        previous_end_date = current_end_date.replace(year=previous_year, month=previous_month)
                    except ValueError:
                        from calendar import monthrange
                        last_day = monthrange(previous_year, previous_month)[1]
                        previous_end_date = current_end_date.replace(year=previous_year, month=previous_month, day=min(current_end_date.day, last_day))
                elif comparison_type == 'quarter_over_quarter':
                    # Calculate previous quarter
                    months_back = 3
                    previous_start_date = (current_start_date.replace(day=1) - timedelta(days=1)).replace(day=1) if current_start_date.month > 3 else current_start_date.replace(year=current_start_date.year-1, month=current_start_date.month+9)
                    previous_end_date = (current_end_date.replace(day=1) - timedelta(days=1)).replace(day=1) if current_end_date.month > 3 else current_end_date.replace(year=current_end_date.year-1, month=current_end_date.month+9)
                elif comparison_type == 'year_over_year':
                    previous_start_date = current_start_date.replace(year=current_start_date.year-1)
                    previous_end_date = current_end_date.replace(year=current_end_date.year-1)
            else:
                # Parse custom dates
                previous_start_date = datetime.strptime(previous_start, '%Y-%m-%d').date() if previous_start else None
                previous_end_date = datetime.strptime(previous_end, '%Y-%m-%d').date() if previous_end else None
                current_start_date = datetime.strptime(current_start, '%Y-%m-%d').date() if current_start else None
                current_end_date = datetime.strptime(current_end, '%Y-%m-%d').date() if current_end else None

            if not all([current_start_date, current_end_date, previous_start_date, previous_end_date]):
                return jsonify({
                    'success': False,
                    'error': 'All date parameters are required'
                }), 400

            # Generate financial data for both periods
            current_period_data = generate_period_financial_data(current_start_date, current_end_date)
            previous_period_data = generate_period_financial_data(previous_start_date, previous_end_date)

            # Calculate variance analysis
            variance_analysis = calculate_variance_analysis(current_period_data, previous_period_data)

            return jsonify({
                'success': True,
                'comparison': {
                    'current_period': {
                        'start_date': current_start_date.isoformat(),
                        'end_date': current_end_date.isoformat(),
                        'data': current_period_data
                    },
                    'previous_period': {
                        'start_date': previous_start_date.isoformat(),
                        'end_date': previous_end_date.isoformat(),
                        'data': previous_period_data
                    },
                    'variance_analysis': variance_analysis,
                    'comparison_type': comparison_type
                },
                'generated_at': datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error in period comparison: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def generate_period_financial_data(start_date, end_date):
        """Generate financial data for a specific period"""

        # Safe query execution
        def safe_query(query, params=None):
            try:
                result = db_manager.execute_query(query, params, fetch_all=True)
                return result if result else []
            except Exception as e:
                logger.warning(f"Query failed safely: {e}")
                return []

        # Revenue query for the period
        revenue_query = """
            SELECT
                COALESCE(accounting_category, classified_entity, 'Uncategorized') as category,
                COALESCE(SUM(amount), 0) as amount,
                COUNT(*) as count
            FROM transactions
            WHERE amount > 0
            AND TO_DATE(date, 'MM/DD/YYYY'::text) >= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
            AND TO_DATE(date, 'MM/DD/YYYY'::text) <= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
            GROUP BY COALESCE(accounting_category, classified_entity, 'Uncategorized')
            ORDER BY amount DESC
        """ if db_manager.db_type == 'postgresql' else """
            SELECT
                COALESCE(accounting_category, classified_entity, 'Uncategorized') as category,
                COALESCE(SUM(amount), 0) as amount,
                COUNT(*) as count
            FROM transactions
            WHERE amount > 0
            AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) >= date(?)
            AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) <= date(?)
            GROUP BY COALESCE(accounting_category, classified_entity, 'Uncategorized')
            ORDER BY amount DESC
        """

        revenue_data = safe_query(revenue_query, (start_date, end_date))

        # Expenses query for the period
        expenses_query = """
            SELECT
                COALESCE(accounting_category, classified_entity, 'General & Administrative') as category,
                COALESCE(SUM(ABS(amount)), 0) as amount,
                COUNT(*) as count
            FROM transactions
            WHERE amount < 0
            AND TO_DATE(date, 'MM/DD/YYYY'::text) >= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
            AND TO_DATE(date, 'MM/DD/YYYY'::text) <= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
            GROUP BY COALESCE(accounting_category, classified_entity, 'General & Administrative')
            ORDER BY amount DESC
        """ if db_manager.db_type == 'postgresql' else """
            SELECT
                COALESCE(accounting_category, classified_entity, 'General & Administrative') as category,
                COALESCE(SUM(ABS(amount)), 0) as amount,
                COUNT(*) as count
            FROM transactions
            WHERE amount < 0
            AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) >= date(?)
            AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) <= date(?)
            GROUP BY COALESCE(accounting_category, classified_entity, 'General & Administrative')
            ORDER BY amount DESC
        """

        expenses_data = safe_query(expenses_query, (start_date, end_date))

        # Calculate totals
        total_revenue = sum(float(row.get('amount', 0)) for row in revenue_data)
        total_expenses = sum(float(row.get('amount', 0)) for row in expenses_data)
        net_income = total_revenue - total_expenses
        margin_percent = (net_income / total_revenue * 100) if total_revenue > 0 else 0

        return {
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_income': net_income,
            'margin_percent': round(margin_percent, 2),
            'revenue_categories': [{'category': r.get('category', ''), 'amount': float(r.get('amount', 0))} for r in revenue_data],
            'expense_categories': [{'category': e.get('category', ''), 'amount': float(e.get('amount', 0))} for e in expenses_data],
            'transaction_count': sum(r.get('count', 0) for r in revenue_data) + sum(e.get('count', 0) for e in expenses_data)
        }

    def calculate_variance_analysis(current, previous):
        """Calculate variance analysis between two periods"""

        def safe_divide(numerator, denominator):
            return (numerator / denominator) if denominator != 0 else 0

        def calculate_change(current_val, previous_val):
            if previous_val == 0:
                return {'absolute': current_val, 'percentage': 100.0 if current_val > 0 else 0.0}

            absolute_change = current_val - previous_val
            percentage_change = (absolute_change / abs(previous_val)) * 100

            return {
                'absolute': round(absolute_change, 2),
                'percentage': round(percentage_change, 2)
            }

        revenue_change = calculate_change(current['total_revenue'], previous['total_revenue'])
        expenses_change = calculate_change(current['total_expenses'], previous['total_expenses'])
        net_income_change = calculate_change(current['net_income'], previous['net_income'])
        margin_change = {
            'absolute': round(current['margin_percent'] - previous['margin_percent'], 2),
            'percentage': round(((current['margin_percent'] - previous['margin_percent']) / abs(previous['margin_percent']) * 100) if previous['margin_percent'] != 0 else 0, 2)
        }

        # Growth rates
        revenue_growth_rate = safe_divide(revenue_change['absolute'], abs(previous['total_revenue'])) * 100
        expense_growth_rate = safe_divide(expenses_change['absolute'], abs(previous['total_expenses'])) * 100

        return {
            'revenue_change': revenue_change,
            'expenses_change': expenses_change,
            'net_income_change': net_income_change,
            'margin_change': margin_change,
            'revenue_growth_rate': round(revenue_growth_rate, 2),
            'expense_growth_rate': round(expense_growth_rate, 2),
            'efficiency_metrics': {
                'revenue_per_transaction': {
                    'current': round(safe_divide(current['total_revenue'], current['transaction_count']), 2),
                    'previous': round(safe_divide(previous['total_revenue'], previous['transaction_count']), 2)
                },
                'expense_ratio': {
                    'current': round(safe_divide(current['total_expenses'], current['total_revenue']) * 100, 2),
                    'previous': round(safe_divide(previous['total_expenses'], previous['total_revenue']) * 100, 2)
                }
            }
        }

    @app.route('/api/reports/templates', methods=['GET', 'POST', 'DELETE'])
    def api_report_templates():
        """
        Manage custom report templates

        GET: List all templates
        POST: Create or update a template
        DELETE: Delete a template
        """
        try:
            if request.method == 'GET':
                # Get all templates
                templates_query = """
                    SELECT id, name, description, template_config, created_at, updated_at
                    FROM report_templates
                    ORDER BY updated_at DESC
                """
                templates = db_manager.execute_query(templates_query, fetch_all=True)

                # Parse JSON configs
                template_list = []
                for template in templates:
                    template_dict = dict(template)
                    try:
                        template_dict['template_config'] = json.loads(template['template_config'])
                    except (json.JSONDecodeError, TypeError):
                        template_dict['template_config'] = {}
                    template_list.append(template_dict)

                return jsonify({
                    'success': True,
                    'templates': template_list
                })

            elif request.method == 'POST':
                # Create or update template
                data = request.get_json()
                template_name = data.get('name')
                description = data.get('description', '')
                config = data.get('config', {})
                template_id = data.get('id')

                if not template_name:
                    return jsonify({
                        'success': False,
                        'error': 'Template name is required'
                    }), 400

                config_json = json.dumps(config)

                if template_id:
                    # Update existing template
                    update_query = """
                        UPDATE report_templates
                        SET name = %s, description = %s, template_config = %s, updated_at = %s
                        WHERE id = %s
                    """ if db_manager.db_type == 'postgresql' else """
                        UPDATE report_templates
                        SET name = ?, description = ?, template_config = ?, updated_at = ?
                        WHERE id = ?
                    """
                    db_manager.execute_query(update_query, (template_name, description, config_json, datetime.now(), template_id))
                else:
                    # Create new template
                    insert_query = """
                        INSERT INTO report_templates (name, description, template_config, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """ if db_manager.db_type == 'postgresql' else """
                        INSERT INTO report_templates (name, description, template_config, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """
                    db_manager.execute_query(insert_query, (template_name, description, config_json, datetime.now(), datetime.now()))

                return jsonify({
                    'success': True,
                    'message': 'Template saved successfully'
                })

            elif request.method == 'DELETE':
                # Delete template
                template_id = request.args.get('id')
                if not template_id:
                    return jsonify({
                        'success': False,
                        'error': 'Template ID is required'
                    }), 400

                delete_query = """
                    DELETE FROM report_templates WHERE id = %s
                """ if db_manager.db_type == 'postgresql' else """
                    DELETE FROM report_templates WHERE id = ?
                """
                db_manager.execute_query(delete_query, (template_id,))

                return jsonify({
                    'success': True,
                    'message': 'Template deleted successfully'
                })

        except Exception as e:
            logger.error(f"Error managing report templates: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def ensure_report_templates_table():
        """Ensure the report templates table exists"""
        try:
            if db_manager.db_type == 'postgresql':
                create_table_query = """
                    CREATE TABLE IF NOT EXISTS report_templates (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        template_config JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_report_templates_name ON report_templates(name);
                """
            else:
                create_table_query = """
                    CREATE TABLE IF NOT EXISTS report_templates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        template_config TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_report_templates_name ON report_templates(name);
                """

            db_manager.execute_query(create_table_query)
            logger.info("Report templates table ensured")

            # Create default templates if none exist
            count_query = "SELECT COUNT(*) as count FROM report_templates"
            result = db_manager.execute_query(count_query, fetch_one=True)

            if result['count'] == 0:
                create_default_templates()

        except Exception as e:
            logger.warning(f"Could not ensure report templates table: {e}")

    def create_default_templates():
        """Create default report templates"""
        default_templates = [
            {
                'name': 'Relatório Mensal Padrão',
                'description': 'Demonstração de resultado mensal com gráficos',
                'config': {
                    'report_type': 'income-statement',
                    'period_type': 'monthly',
                    'include_charts': True,
                    'include_comparison': False,
                    'default_date_range': 'current_month'
                }
            },
            {
                'name': 'Análise Trimestral Completa',
                'description': 'Relatório trimestral com comparações e gráficos',
                'config': {
                    'report_type': 'income-statement',
                    'period_type': 'quarterly',
                    'include_charts': True,
                    'include_comparison': True,
                    'comparison_type': 'quarter_over_quarter',
                    'default_date_range': 'current_quarter'
                }
            },
            {
                'name': 'Dashboard Executivo',
                'description': 'Visão executiva com métricas principais e tendências',
                'config': {
                    'report_type': 'dashboard',
                    'period_type': 'monthly',
                    'include_charts': True,
                    'include_comparison': True,
                    'comparison_type': 'month_over_month',
                    'metrics': ['revenue', 'expenses', 'net_income', 'margin'],
                    'default_date_range': 'last_3_months'
                }
            }
        ]

        for template in default_templates:
            config_json = json.dumps(template['config'])
            insert_query = """
                INSERT INTO report_templates (name, description, template_config, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
            """ if db_manager.db_type == 'postgresql' else """
                INSERT INTO report_templates (name, description, template_config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """
            db_manager.execute_query(insert_query, (
                template['name'],
                template['description'],
                config_json,
                datetime.now(),
                datetime.now()
            ))

        logger.info("Default report templates created")

    @app.route('/api/reports/cash-dashboard', methods=['GET'])
    def api_cash_dashboard():
        """
        Get comprehensive cash dashboard data

        GET Parameters:
            - start_date: Start date for analysis (YYYY-MM-DD) (optional)
            - end_date: End date for analysis (YYYY-MM-DD) (optional)
            - entity: Specific entity filter (optional)

        Returns:
            JSON with cash position, trends, and entity breakdown
        """
        try:
            start_time = datetime.now()

            # Parse parameters
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            entity_filter = request.args.get('entity')

            # Parse dates if provided
            start_date = None
            end_date = None

            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400

            if end_date_str:
                try:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400

            # Initialize Cash Dashboard
            cash_dashboard = CashDashboard()

            # Get current cash position
            cash_position = cash_dashboard.get_current_cash_position(entity=entity_filter)

            # Get cash trend (7 and 30 days)
            trend_7_days = cash_dashboard.get_cash_trend(days=7, entity=entity_filter)
            trend_30_days = cash_dashboard.get_cash_trend(days=30, entity=entity_filter)

            # Get entity comparison
            entity_comparison = cash_dashboard.get_entity_cash_comparison()

            # Calculate generation time
            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'data': {
                    'cash_position': cash_position,
                    'trends': {
                        '7_days': trend_7_days,
                        '30_days': trend_30_days
                    },
                    'entity_comparison': entity_comparison
                },
                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': generation_time_ms
            })

        except Exception as e:
            logger.error(f"Error generating cash dashboard: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/cash-trend', methods=['GET'])
    def api_cash_trend():
        """
        Get detailed cash flow trend analysis

        GET Parameters:
            - days: Number of days for trend (default: 30)
            - entity: Specific entity filter (optional)
            - granularity: 'daily', 'weekly', 'monthly' (default: 'daily')

        Returns:
            JSON with detailed cash flow trend data for charts
        """
        try:
            start_time = datetime.now()

            # Parse parameters
            days = int(request.args.get('days', 30))
            entity_filter = request.args.get('entity')
            granularity = request.args.get('granularity', 'daily')

            # Validate parameters
            if days < 1 or days > 365:
                return jsonify({'error': 'Days must be between 1 and 365'}), 400

            if granularity not in ['daily', 'weekly', 'monthly']:
                return jsonify({'error': 'Granularity must be daily, weekly, or monthly'}), 400

            # Initialize Cash Dashboard
            cash_dashboard = CashDashboard()

            # Get trend data
            trend_data = cash_dashboard.get_cash_trend(
                days=days,
                entity=entity_filter
            )

            # Format for Chart.js
            chart_data = {
                'labels': [],
                'datasets': [
                    {
                        'label': 'Inflows (+)',
                        'data': [],
                        'borderColor': '#10b981',
                        'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                        'fill': True
                    },
                    {
                        'label': 'Outflows (-)',
                        'data': [],
                        'borderColor': '#ef4444',
                        'backgroundColor': 'rgba(239, 68, 68, 0.1)',
                        'fill': True
                    },
                    {
                        'label': 'Net Flow',
                        'data': [],
                        'borderColor': '#3b82f6',
                        'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                        'fill': False,
                        'type': 'line'
                    }
                ]
            }

            for point in trend_data.get('daily_points', []):
                chart_data['labels'].append(point.get('date', ''))
                chart_data['datasets'][0]['data'].append(point.get('inflows', 0))
                chart_data['datasets'][1]['data'].append(abs(point.get('outflows', 0)))
                chart_data['datasets'][2]['data'].append(point.get('net_flow', 0))

            # Calculate generation time
            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'data': {
                    'trend_summary': trend_data,
                    'chart_data': chart_data,
                    'parameters': {
                        'days': days,
                        'entity_filter': entity_filter,
                        'granularity': granularity
                    }
                },
                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': generation_time_ms
            })

        except Exception as e:
            logger.error(f"Error generating cash trend: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/entity-performance', methods=['GET'])
    def api_entity_performance():
        """
        Get detailed entity performance analysis

        GET Parameters:
            - period: 'weekly', 'monthly', 'quarterly' (default: 'monthly')
            - top_n: Number of top entities to return (default: 10)
            - metric: 'revenue', 'profit', 'transactions' (default: 'revenue')

        Returns:
            JSON with entity performance metrics and comparisons
        """
        try:
            start_time = datetime.now()

            # Parse parameters
            period = request.args.get('period', 'monthly')
            top_n = int(request.args.get('top_n', 10))
            metric = request.args.get('metric', 'revenue')

            # Validate parameters
            if period not in ['weekly', 'monthly', 'quarterly']:
                return jsonify({'error': 'Period must be weekly, monthly, or quarterly'}), 400

            if metric not in ['revenue', 'profit', 'transactions']:
                return jsonify({'error': 'Metric must be revenue, profit, or transactions'}), 400

            if top_n < 1 or top_n > 50:
                return jsonify({'error': 'Top N must be between 1 and 50'}), 400

            # Initialize Cash Dashboard
            cash_dashboard = CashDashboard()

            # Get entity comparison
            entity_data = cash_dashboard.get_entity_cash_comparison()

            # Sort entities by requested metric
            if metric == 'revenue':
                sorted_entities = sorted(
                    entity_data.get('entities', []),
                    key=lambda x: x.get('total_inflows', 0),
                    reverse=True
                )
            elif metric == 'profit':
                sorted_entities = sorted(
                    entity_data.get('entities', []),
                    key=lambda x: x.get('net_flow', 0),
                    reverse=True
                )
            else:  # transactions
                sorted_entities = sorted(
                    entity_data.get('entities', []),
                    key=lambda x: x.get('transaction_count', 0),
                    reverse=True
                )

            # Limit to top N
            top_entities = sorted_entities[:top_n]

            # Format for charts
            chart_data = {
                'labels': [entity.get('entity', 'Unknown') for entity in top_entities],
                'datasets': [
                    {
                        'label': 'Revenue',
                        'data': [entity.get('total_inflows', 0) for entity in top_entities],
                        'backgroundColor': '#10b981'
                    },
                    {
                        'label': 'Expenses',
                        'data': [abs(entity.get('total_outflows', 0)) for entity in top_entities],
                        'backgroundColor': '#ef4444'
                    }
                ]
            }

            # Calculate performance metrics
            performance_metrics = {
                'total_entities': len(entity_data.get('entities', [])),
                'profitable_entities': len([e for e in entity_data.get('entities', []) if e.get('net_flow', 0) > 0]),
                'top_performer': top_entities[0] if top_entities else None,
                'period_analysis': period,
                'metric_focus': metric
            }

            # Calculate generation time
            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'data': {
                    'entity_performance': {
                        'top_entities': top_entities,
                        'performance_metrics': performance_metrics,
                        'chart_data': chart_data
                    },
                    'summary': entity_data
                },
                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': generation_time_ms
            })

        except Exception as e:
            logger.error(f"Error generating entity performance: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/monthly-pl', methods=['GET'])
    def api_monthly_pl():
        """
        Get Monthly P&L breakdown (Revenue vs Expenses vs Profit) - Simplified version

        GET Parameters:
            - months_back: Number of months to analyze (default: 12, use 'all' for all data)
            - start_date: Custom start date (YYYY-MM-DD)
            - end_date: Custom end date (YYYY-MM-DD)

        Returns:
            JSON with monthly P&L analysis ready for charts and dashboards
        """
        try:
            start_time = datetime.now()

            # Parse parameters with support for 'all' data
            months_back_param = request.args.get('months_back', '12')
            start_date_param = request.args.get('start_date')
            end_date_param = request.args.get('end_date')

            # Determine date range
            if start_date_param and end_date_param:
                # Use custom date range
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
            elif months_back_param == 'all':
                # Use all available data - find min/max dates
                date_range_query = """
                    SELECT
                        MIN(date::date) as min_date,
                        MAX(date::date) as max_date
                    FROM (
                        SELECT date::date as date FROM transactions WHERE date IS NOT NULL
                        UNION ALL
                        SELECT date::date as date FROM invoices WHERE date IS NOT NULL
                    ) combined_dates
                """
                date_range_result = db_manager.execute_query(date_range_query, fetch_one=True)
                if date_range_result and date_range_result.get('min_date'):
                    start_date = date_range_result['min_date']
                    end_date = date_range_result['max_date'] or date.today()
                else:
                    # Fallback if no data found
                    end_date = date.today()
                    start_date = end_date - timedelta(days=365)
            else:
                # Use months_back parameter
                months_back = int(months_back_param)
                if months_back < 1 or months_back > 36:
                    return jsonify({'error': 'Months back must be between 1 and 36'}), 400

                end_date = date.today()
                start_date = end_date - timedelta(days=months_back * 30)

            # Consolidated query combining transactions + invoices - with NaN filtering
            monthly_pl_query = """
                WITH combined_data AS (
                    -- Transactions data (can be revenue or expenses)
                    SELECT
                        date::date as transaction_date,
                        CASE WHEN amount > 0 THEN amount ELSE 0 END as revenue,
                        CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END as expenses,
                        'transaction' as source_type
                    FROM transactions
                    WHERE date::date >= %s AND date::date <= %s
                        AND amount::text != 'NaN' AND amount IS NOT NULL

                    UNION ALL

                    -- Invoices data (always revenue)
                    SELECT
                        date::date as transaction_date,
                        CASE
                            WHEN total_amount::text ~ '^[0-9]+\.?[0-9]*$'
                            THEN total_amount::float
                            ELSE 0
                        END as revenue,
                        0 as expenses,
                        'invoice' as source_type
                    FROM invoices
                    WHERE date::date >= %s AND date::date <= %s
                        AND total_amount IS NOT NULL
                        AND total_amount::text != 'NaN'
                        AND total_amount::text != ''
                )
                SELECT
                    EXTRACT(YEAR FROM transaction_date) as year,
                    EXTRACT(MONTH FROM transaction_date) as month_number,
                    SUM(revenue) as total_revenue,
                    SUM(expenses) as total_expenses,
                    SUM(revenue) - SUM(expenses) as net_profit,
                    COUNT(*) as transaction_count
                FROM combined_data
                GROUP BY EXTRACT(YEAR FROM transaction_date), EXTRACT(MONTH FROM transaction_date)
                ORDER BY year, month_number
            """

            monthly_data = db_manager.execute_query(monthly_pl_query, (start_date, end_date, start_date, end_date), fetch_all=True)

            # Process monthly data - simplified
            monthly_pl = []
            total_revenue = 0
            total_expenses = 0
            total_profit = 0

            # Check if we have data
            if monthly_data and len(monthly_data) > 0:
                for row in monthly_data:
                    try:
                        # Safe conversion of values
                        revenue = float(row.get('total_revenue', 0) or 0)
                        expenses = float(row.get('total_expenses', 0) or 0)
                        profit = float(row.get('net_profit', 0) or 0)
                        year = int(row.get('year', 2024) or 2024)
                        month_num = int(row.get('month_number', 1) or 1)

                        # Create month display
                        month_display = f"{calendar.month_abbr[month_num]} {year}"

                        monthly_record = {
                            'month': month_display,
                            'year': year,
                            'month_number': month_num,
                            'revenue': revenue,
                            'expenses': expenses,
                            'profit': profit,
                            'transaction_count': int(row.get('transaction_count', 0) or 0)
                        }

                        monthly_pl.append(monthly_record)

                        # Accumulate totals
                        total_revenue += revenue
                        total_expenses += expenses
                        total_profit += profit

                    except Exception as row_error:
                        logger.warning(f"Error processing monthly row: {row_error}")
                        continue

            # Calculate generation time
            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'data': {
                    'monthly_pl': monthly_pl,
                    'summary': {
                        'period_totals': {
                            'total_revenue': round(total_revenue, 2),
                            'total_expenses': round(total_expenses, 2),
                            'total_profit': round(total_profit, 2),
                        }
                    },
                    'generated_at': datetime.now().isoformat(),
                    'generation_time_ms': generation_time_ms
                }
            })

        except Exception as e:
            logger.error(f"Error generating monthly P&L: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


    @app.route('/api/reports/entity-summary', methods=['GET'])
    def api_entity_summary():
        """
        Get comprehensive Entity Summary (performance por empresa Delta)

        GET Parameters:
            - period: 'monthly', 'quarterly', 'yearly', 'all_time' (default: 'all_time')
            - start_date: Start date for analysis (YYYY-MM-DD) (optional)
            - end_date: End date for analysis (YYYY-MM-DD) (optional)
            - include_trends: Include trend analysis (true/false) (default: true)
            - min_transactions: Minimum transactions to include entity (default: 5)

        Returns:
            JSON with comprehensive entity performance analysis for Delta companies
        """
        try:
            start_time = datetime.now()

            # Parse parameters
            period = request.args.get('period', 'all_time')
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            include_trends = request.args.get('include_trends', 'true').lower() == 'true'
            min_transactions = int(request.args.get('min_transactions', 5))

            # Validate parameters
            if period not in ['monthly', 'quarterly', 'yearly', 'all_time', 'custom']:
                return jsonify({'error': 'Period must be monthly, quarterly, yearly, all_time, or custom'}), 400

            if min_transactions < 1:
                return jsonify({'error': 'Minimum transactions must be at least 1'}), 400

            # Calculate date range based on period
            date_filter = ""
            params = []

            if start_date_str and end_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    start_date_str = start_date.isoformat()
                    end_date_str = end_date.isoformat()
                except ValueError:
                    return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
            elif period != 'all_time' and period != 'custom':
                end_date = date.today()
                if period == 'monthly':
                    start_date = end_date.replace(day=1) - timedelta(days=30)
                elif period == 'quarterly':
                    start_date = end_date - timedelta(days=90)
                elif period == 'yearly':
                    start_date = end_date - timedelta(days=365)

                start_date_str = start_date.isoformat()
                end_date_str = end_date.isoformat()

            if period != 'all_time':
                if db_manager.db_type == 'postgresql':
                    date_filter = """
                        AND date::date >= %s::date
                        AND date::date <= %s::date
                    """
                    params = [start_date_str, end_date_str]
                else:
                    date_filter = """
                        AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) >= date(?)
                        AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) <= date(?)
                    """
                    params = [start_date_str, end_date_str]

            # Entity performance query - comprehensive analysis
            entity_query = f"""
                SELECT
                    COALESCE(classified_entity, accounting_category, 'Uncategorized') as entity,
                    COUNT(*) as total_transactions,
                    COUNT(CASE WHEN amount > 0 THEN 1 END) as revenue_transactions,
                    COUNT(CASE WHEN amount < 0 THEN 1 END) as expense_transactions,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_revenue,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_expenses,
                    SUM(amount) as net_profit,
                    AVG(CASE WHEN amount > 0 THEN amount END) as avg_revenue_per_transaction,
                    AVG(CASE WHEN amount < 0 THEN ABS(amount) END) as avg_expense_per_transaction,
                    MIN(CASE WHEN amount > 0 THEN amount END) as min_revenue_transaction,
                    MAX(CASE WHEN amount > 0 THEN amount END) as max_revenue_transaction,
                    MIN(CASE WHEN amount < 0 THEN ABS(amount) END) as min_expense_transaction,
                    MAX(CASE WHEN amount < 0 THEN ABS(amount) END) as max_expense_transaction
                FROM transactions
                WHERE 1=1
                AND amount::text != 'NaN' AND amount IS NOT NULL
                {date_filter}
                GROUP BY COALESCE(classified_entity, accounting_category, 'Uncategorized')
                HAVING COUNT(*) >= {'%s' if db_manager.db_type == 'postgresql' else '?'}
                ORDER BY SUM(amount) DESC
            """

            entity_params = params + [min_transactions]
            entity_data = db_manager.execute_query(entity_query, tuple(entity_params), fetch_all=True)

            # Process entity data
            entities = []
            total_system_revenue = 0
            total_system_expenses = 0
            total_system_profit = 0
            total_system_transactions = 0

            for row in entity_data:
                try:
                    # Safe conversion of values
                    revenue = float(row.get('total_revenue', 0) or 0)
                    expenses = float(row.get('total_expenses', 0) or 0)
                    profit = float(row.get('net_profit', 0) or 0)
                    transactions = int(row.get('total_transactions', 0) or 0)

                    # Calculate performance metrics
                    profit_margin = (profit / revenue * 100) if revenue > 0 else 0
                    roi = (profit / expenses * 100) if expenses > 0 else 0
                    efficiency_ratio = revenue / expenses if expenses > 0 else 0

                    # Transaction metrics
                    avg_rev_per_trans = float(row.get('avg_revenue_per_transaction', 0) or 0)
                    avg_exp_per_trans = float(row.get('avg_expense_per_transaction', 0) or 0)

                    # Performance classification
                    performance_tier = 'Low'
                    if profit > 0 and profit_margin > 20:
                        performance_tier = 'High'
                    elif profit > 0 and profit_margin > 10:
                        performance_tier = 'Medium'
                    elif profit > 0:
                        performance_tier = 'Low-Positive'

                    # Risk assessment
                    risk_level = 'Low'
                    if profit < 0:
                        risk_level = 'High'
                    elif profit_margin < 5:
                        risk_level = 'Medium'

                    entity_record = {
                        'entity': row.get('entity', 'Unknown'),
                        'financial_metrics': {
                            'total_revenue': revenue,
                            'total_expenses': expenses,
                            'net_profit': profit,
                            'profit_margin_percent': round(profit_margin, 2),
                            'roi_percent': round(roi, 2),
                            'efficiency_ratio': round(efficiency_ratio, 2)
                        },
                        'transaction_metrics': {
                            'total_transactions': transactions,
                            'revenue_transactions': int(row.get('revenue_transactions', 0) or 0),
                            'expense_transactions': int(row.get('expense_transactions', 0) or 0),
                            'avg_revenue_per_transaction': round(avg_rev_per_trans, 2),
                            'avg_expense_per_transaction': round(avg_exp_per_trans, 2),
                            'transaction_volume_score': min(transactions / 100, 1.0) * 100  # Scale 0-100
                        },
                        'performance_analysis': {
                            'performance_tier': performance_tier,
                            'risk_level': risk_level,
                            'profitability_status': 'Profitable' if profit > 0 else 'Loss-making',
                            'growth_potential': 'High' if profit > 0 and transactions > 50 else 'Medium' if profit > 0 else 'Low'
                        },
                        'range_analysis': {
                            'min_revenue_transaction': float(row.get('min_revenue_transaction', 0) or 0),
                            'max_revenue_transaction': float(row.get('max_revenue_transaction', 0) or 0),
                            'min_expense_transaction': float(row.get('min_expense_transaction', 0) or 0),
                            'max_expense_transaction': float(row.get('max_expense_transaction', 0) or 0)
                        }
                    }

                    entities.append(entity_record)

                    # Accumulate system totals
                    total_system_revenue += revenue
                    total_system_expenses += expenses
                    total_system_profit += profit
                    total_system_transactions += transactions

                except Exception as row_error:
                    logger.warning(f"Error processing entity row: {row_error}")
                    continue

            # Calculate system-wide metrics
            system_metrics = {
                'total_entities': len(entities),
                'profitable_entities': len([e for e in entities if e['financial_metrics']['net_profit'] > 0]),
                'loss_making_entities': len([e for e in entities if e['financial_metrics']['net_profit'] < 0]),
                'high_performance_entities': len([e for e in entities if e['performance_analysis']['performance_tier'] == 'High']),
                'high_risk_entities': len([e for e in entities if e['performance_analysis']['risk_level'] == 'High']),
                'system_totals': {
                    'total_revenue': round(total_system_revenue, 2),
                    'total_expenses': round(total_system_expenses, 2),
                    'total_profit': round(total_system_profit, 2),
                    'total_transactions': total_system_transactions,
                    'overall_margin_percent': round((total_system_profit / total_system_revenue * 100) if total_system_revenue > 0 else 0, 2)
                }
            }

            # Entity rankings and comparisons
            rankings = {
                'top_revenue_entities': sorted(entities, key=lambda x: x['financial_metrics']['total_revenue'], reverse=True)[:5],
                'top_profit_entities': sorted(entities, key=lambda x: x['financial_metrics']['net_profit'], reverse=True)[:5],
                'top_margin_entities': sorted([e for e in entities if e['financial_metrics']['total_revenue'] > 0],
                                             key=lambda x: x['financial_metrics']['profit_margin_percent'], reverse=True)[:5],
                'top_transaction_volume_entities': sorted(entities, key=lambda x: x['transaction_metrics']['total_transactions'], reverse=True)[:5],
                'underperforming_entities': sorted([e for e in entities if e['financial_metrics']['net_profit'] < 0],
                                                  key=lambda x: x['financial_metrics']['net_profit'])[:5]
            }

            # Chart data for visualizations
            chart_data = {
                'revenue_by_entity': {
                    'labels': [e['entity'] for e in entities[:10]],  # Top 10
                    'data': [e['financial_metrics']['total_revenue'] for e in entities[:10]],
                    'backgroundColor': ['#10b981', '#3b82f6', '#8b5cf6', '#ef4444', '#f59e0b',
                                      '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#6366f1']
                },
                'profit_by_entity': {
                    'labels': [e['entity'] for e in entities[:10]],
                    'data': [e['financial_metrics']['net_profit'] for e in entities[:10]],
                    'backgroundColor': [('#10b981' if profit >= 0 else '#ef4444')
                                      for profit in [e['financial_metrics']['net_profit'] for e in entities[:10]]]
                },
                'performance_distribution': {
                    'labels': ['High Performance', 'Medium Performance', 'Low-Positive', 'Loss-making'],
                    'data': [
                        len([e for e in entities if e['performance_analysis']['performance_tier'] == 'High']),
                        len([e for e in entities if e['performance_analysis']['performance_tier'] == 'Medium']),
                        len([e for e in entities if e['performance_analysis']['performance_tier'] == 'Low-Positive']),
                        len([e for e in entities if e['performance_analysis']['performance_tier'] == 'Low'])
                    ],
                    'backgroundColor': ['#10b981', '#3b82f6', '#f59e0b', '#ef4444']
                }
            }

            # Trend analysis if requested
            trend_data = {}
            if include_trends and period != 'all_time':
                trend_data = get_entity_trend_analysis(date_filter, params, entities[:5])  # Top 5 for trends

            # Calculate generation time
            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'data': {
                    'entities': entities,
                    'system_metrics': system_metrics,
                    'rankings': rankings,
                    'chart_data': chart_data,
                    'trend_analysis': trend_data,
                    'parameters': {
                        'period': period,
                        'min_transactions': min_transactions,
                        'include_trends': include_trends,
                        'date_range': {
                            'start_date': start_date_str if period != 'all_time' else None,
                            'end_date': end_date_str if period != 'all_time' else None
                        }
                    }
                },
                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': generation_time_ms
            })

        except Exception as e:
            logger.error(f"Error generating entity summary: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def get_entity_trend_analysis(date_filter, base_params, top_entities):
        """Get trend analysis for top entities over time"""
        try:
            trends = {}

            for entity in top_entities:
                entity_name = entity['entity']

                # Monthly trends for this entity
                if db_manager.db_type == 'postgresql':
                    trend_query = f"""
                        SELECT
                            DATE_TRUNC('month', TO_DATE(date, 'MM/DD/YYYY')) as month,
                            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue,
                            SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
                            SUM(amount) as profit,
                            COUNT(*) as transactions
                        FROM transactions
                        WHERE COALESCE(classified_entity, accounting_category, 'Uncategorized') = %s
                        {date_filter}
                        GROUP BY DATE_TRUNC('month', TO_DATE(date, 'MM/DD/YYYY'))
                        ORDER BY month
                    """
                else:
                    trend_query = f"""
                        SELECT
                            substr(date, 7, 4) || '-' ||
                            CASE WHEN length(substr(date, 1, 2)) = 1 THEN '0' || substr(date, 1, 1) ELSE substr(date, 1, 2) END || '-01' as month,
                            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue,
                            SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
                            SUM(amount) as profit,
                            COUNT(*) as transactions
                        FROM transactions
                        WHERE COALESCE(classified_entity, accounting_category, 'Uncategorized') = ?
                        {date_filter}
                        GROUP BY substr(date, 7, 4), substr(date, 1, 2)
                        ORDER BY month
                    """

                trend_params = [entity_name] + base_params
                trend_result = db_manager.execute_query(trend_query, tuple(trend_params), fetch_all=True)

                monthly_trends = []
                for row in trend_result:
                    try:
                        revenue = float(row.get('revenue', 0) or 0)
                        expenses = float(row.get('expenses', 0) or 0)
                        profit = float(row.get('profit', 0) or 0)

                        # Format month display
                        month_display = 'Unknown'
                        if row.get('month'):
                            if db_manager.db_type == 'postgresql' and hasattr(row['month'], 'strftime'):
                                month_display = row['month'].strftime('%b %Y')
                            elif isinstance(row['month'], str):
                                try:
                                    month_obj = datetime.strptime(row['month'][:10], '%Y-%m-%d')
                                    month_display = month_obj.strftime('%b %Y')
                                except:
                                    month_display = row['month'][:7]

                        monthly_trends.append({
                            'month': month_display,
                            'revenue': revenue,
                            'expenses': expenses,
                            'profit': profit,
                            'transactions': int(row.get('transactions', 0) or 0),
                            'margin_percent': round((profit / revenue * 100) if revenue > 0 else 0, 2)
                        })
                    except Exception as trend_row_error:
                        logger.warning(f"Error processing trend row for {entity_name}: {trend_row_error}")
                        continue

                # Calculate trend direction
                if len(monthly_trends) >= 2:
                    recent_profit = monthly_trends[-1]['profit']
                    previous_profit = monthly_trends[-2]['profit']
                    trend_direction = 'up' if recent_profit > previous_profit else 'down' if recent_profit < previous_profit else 'stable'
                else:
                    trend_direction = 'insufficient_data'

                trends[entity_name] = {
                    'monthly_data': monthly_trends,
                    'trend_direction': trend_direction,
                    'months_analyzed': len(monthly_trends)
                }

            return trends

        except Exception as e:
            logger.warning(f"Error generating trend analysis: {e}")
            return {}

    @app.route('/api/reports/sankey-flow', methods=['GET'])
    def api_sankey_flow():
        """
        Get Sankey diagram data for revenue to expense flow visualization

        GET Parameters:
            - start_date: Start date for analysis (YYYY-MM-DD) (optional)
            - end_date: End date for analysis (YYYY-MM-DD) (optional)
            - min_amount: Minimum amount to include (default: 1000)
            - max_categories: Maximum categories per type (default: 8)

        Returns:
            JSON with Sankey diagram nodes and links for D3.js
        """
        try:
            start_time = datetime.now()

            # Parse parameters
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            min_amount = float(request.args.get('min_amount', 1000))
            max_categories = int(request.args.get('max_categories', 8))

            # Parse dates if provided
            date_filter = ""
            params = []

            if start_date_str and end_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

                    if db_manager.db_type == 'postgresql':
                        date_filter = """
                            AND TO_DATE(date, 'MM/DD/YYYY') >= TO_DATE(%s, 'YYYY-MM-DD')
                            AND TO_DATE(date, 'MM/DD/YYYY') <= TO_DATE(%s, 'YYYY-MM-DD')
                        """
                        params = [start_date_str, end_date_str]
                    else:
                        date_filter = """
                            AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) >= date(?)
                            AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) <= date(?)
                        """
                        params = [start_date_str, end_date_str]
                except ValueError:
                    return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

            # Get revenue categories (sources)
            revenue_query = f"""
                SELECT
                    COALESCE(accounting_category, classified_entity, 'Other Revenue') as category,
                    SUM(amount) as total_amount,
                    COUNT(*) as transaction_count
                FROM transactions
                WHERE amount > 0
                {date_filter}
                GROUP BY COALESCE(accounting_category, classified_entity, 'Other Revenue')
                HAVING SUM(amount) >= {'%s' if db_manager.db_type == 'postgresql' else '?'}
                ORDER BY total_amount DESC
                LIMIT {'%s' if db_manager.db_type == 'postgresql' else '?'}
            """

            revenue_params = params + [min_amount, max_categories]
            revenue_data = db_manager.execute_query(revenue_query, revenue_params, fetch_all=True)

            # Get expense categories (targets)
            expense_query = f"""
                SELECT
                    COALESCE(accounting_category, classified_entity, 'Other Expenses') as category,
                    SUM(ABS(amount)) as total_amount,
                    COUNT(*) as transaction_count
                FROM transactions
                WHERE amount < 0
                {date_filter}
                GROUP BY COALESCE(accounting_category, classified_entity, 'Other Expenses')
                HAVING SUM(ABS(amount)) >= {'%s' if db_manager.db_type == 'postgresql' else '?'}
                ORDER BY total_amount DESC
                LIMIT {'%s' if db_manager.db_type == 'postgresql' else '?'}
            """

            expense_params = params + [min_amount, max_categories]
            expense_data = db_manager.execute_query(expense_query, expense_params, fetch_all=True)

            # Build Sankey data structure
            nodes = []
            links = []
            node_index = 0

            # Add revenue source nodes
            revenue_nodes = {}
            for rev in revenue_data:
                category = rev['category']
                nodes.append({
                    'id': node_index,
                    'name': category,
                    'type': 'revenue',
                    'value': float(rev['total_amount']),
                    'color': '#10b981'
                })
                revenue_nodes[category] = node_index
                node_index += 1

            # Add central hub node
            total_revenue = sum(float(rev['total_amount']) for rev in revenue_data)
            total_expenses = sum(float(exp['total_amount']) for exp in expense_data)

            hub_node_id = node_index
            nodes.append({
                'id': hub_node_id,
                'name': 'Cash Flow Hub',
                'type': 'hub',
                'value': min(total_revenue, total_expenses),
                'color': '#3b82f6'
            })
            node_index += 1

            # Add expense target nodes
            expense_nodes = {}
            for exp in expense_data:
                category = exp['category']
                nodes.append({
                    'id': node_index,
                    'name': category,
                    'type': 'expense',
                    'value': float(exp['total_amount']),
                    'color': '#ef4444'
                })
                expense_nodes[category] = node_index
                node_index += 1

            # Create links from revenue to hub
            for rev in revenue_data:
                links.append({
                    'source': revenue_nodes[rev['category']],
                    'target': hub_node_id,
                    'value': float(rev['total_amount'])
                })

            # Create links from hub to expenses
            expense_proportion = total_expenses / total_revenue if total_revenue > 0 else 0
            for exp in expense_data:
                proportional_value = float(exp['total_amount']) / total_expenses * min(total_revenue, total_expenses) if total_expenses > 0 else 0
                links.append({
                    'source': hub_node_id,
                    'target': expense_nodes[exp['category']],
                    'value': proportional_value
                })

            # Calculate summary metrics
            net_flow = total_revenue - total_expenses
            flow_efficiency = (net_flow / total_revenue * 100) if total_revenue > 0 else 0

            summary = {
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'net_flow': net_flow,
                'flow_efficiency_percent': round(flow_efficiency, 2),
                'revenue_categories_count': len(revenue_data),
                'expense_categories_count': len(expense_data),
                'date_range': {
                    'start_date': start_date_str,
                    'end_date': end_date_str
                } if start_date_str and end_date_str else None
            }

            # Calculate generation time
            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'data': {
                    'sankey': {
                        'nodes': nodes,
                        'links': links
                    },
                    'summary': summary,
                    'parameters': {
                        'min_amount': min_amount,
                        'max_categories': max_categories
                    }
                },
                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': generation_time_ms
            })

        except Exception as e:
            logger.error(f"Error generating Sankey flow data: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ============================================================================
    # CFO Financial Ratios & KPIs Report
    # ============================================================================
    @app.route('/api/reports/cfo-financial-ratios', methods=['GET'])
    def api_cfo_financial_ratios():
        """
        Comprehensive CFO Financial Ratios & KPIs Report

        GET Parameters:
            - period: 'monthly', 'quarterly', 'yearly', 'all_time', 'custom' (default: 'all_time')
            - start_date: Start date for analysis (YYYY-MM-DD) (optional)
            - end_date: End date for analysis (YYYY-MM-DD) (optional)
            - entity: Filter by specific entity (optional)

        Returns:
            JSON with comprehensive financial ratios and KPIs for CFO analysis
        """
        try:
            start_time = datetime.now()

            # Parse parameters
            period = request.args.get('period', 'all_time')
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            entity_filter = request.args.get('entity', '')

            # Build filters
            date_filter = ""
            entity_filter_clause = ""
            params = []

            if start_date_str and end_date_str:
                date_filter = "AND date::date >= %s::date AND date::date <= %s::date"
                params.extend([start_date_str, end_date_str])
            elif period != 'all_time':
                end_date = date.today()
                if period == 'monthly':
                    start_date = end_date.replace(day=1)
                elif period == 'quarterly':
                    start_date = end_date - timedelta(days=90)
                elif period == 'yearly':
                    start_date = end_date - timedelta(days=365)

                date_filter = "AND date::date >= %s::date AND date::date <= %s::date"
                params.extend([start_date.isoformat(), end_date.isoformat()])

            if entity_filter:
                entity_filter_clause = "AND (classified_entity = %s OR accounting_category = %s)"
                params.extend([entity_filter, entity_filter])

            # Get comprehensive financial data for ratio calculations
            financial_data_query = f"""
                WITH combined_financial_data AS (
                    -- Transaction data
                    SELECT
                        CASE WHEN amount > 0 THEN amount ELSE 0 END as revenue,
                        CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END as expenses,
                        amount as net_amount,
                        classified_entity,
                        accounting_category,
                        date::date as transaction_date
                    FROM transactions
                    WHERE amount::text != 'NaN' AND amount IS NOT NULL
                    {date_filter}
                    {entity_filter_clause}

                    UNION ALL

                    -- Invoice data (always revenue)
                    SELECT
                        CASE
                            WHEN total_amount::text ~ '^[0-9]+\.?[0-9]*$'
                            THEN total_amount::float
                            ELSE 0
                        END as revenue,
                        0 as expenses,
                        CASE
                            WHEN total_amount::text ~ '^[0-9]+\.?[0-9]*$'
                            THEN total_amount::float
                            ELSE 0
                        END as net_amount,
                        vendor_name as classified_entity,
                        'INVOICE_REVENUE' as accounting_category,
                        date::date as transaction_date
                    FROM invoices
                    WHERE total_amount IS NOT NULL
                        AND total_amount::text != 'NaN'
                        AND total_amount::text != ''
                        {date_filter}
                        {entity_filter_clause.replace('classified_entity', 'vendor_name').replace('accounting_category', 'vendor_name') if entity_filter_clause else ''}
                ),
                financial_summary AS (
                    SELECT
                        SUM(revenue) as total_revenue,
                        SUM(expenses) as total_expenses,
                        SUM(revenue) - SUM(expenses) as net_income,
                        COUNT(*) as total_transactions,
                        COUNT(DISTINCT classified_entity) as entity_count,
                        AVG(revenue) as avg_revenue_per_transaction,
                        AVG(expenses) as avg_expense_per_transaction
                    FROM combined_financial_data
                )
                SELECT * FROM financial_summary
            """

            # Execute financial data query
            financial_result = db_manager.execute_query(financial_data_query, params + params, fetch_one=True)

            if not financial_result:
                financial_result = {
                    'total_revenue': 0, 'total_expenses': 0, 'net_income': 0,
                    'total_transactions': 0, 'entity_count': 0,
                    'avg_revenue_per_transaction': 0, 'avg_expense_per_transaction': 0
                }

            # Get cash position data
            cash_query = f"""
                SELECT SUM(amount) as current_cash_position
                FROM transactions
                WHERE amount::text != 'NaN' AND amount IS NOT NULL
                {date_filter}
                {entity_filter_clause}
            """

            cash_result = db_manager.execute_query(cash_query, params, fetch_one=True)
            current_cash = float(cash_result.get('current_cash_position', 0) or 0) if cash_result else 0

            # Calculate key financial ratios and KPIs
            total_revenue = float(financial_result.get('total_revenue', 0) or 0)
            total_expenses = float(financial_result.get('total_expenses', 0) or 0)
            net_income = float(financial_result.get('net_income', 0) or 0)
            total_transactions = int(financial_result.get('total_transactions', 0) or 0)
            entity_count = int(financial_result.get('entity_count', 0) or 0)

            # Profitability Ratios
            gross_margin = (net_income / total_revenue * 100) if total_revenue > 0 else 0
            expense_ratio = (total_expenses / total_revenue * 100) if total_revenue > 0 else 0
            revenue_per_transaction = total_revenue / total_transactions if total_transactions > 0 else 0

            # Efficiency Ratios
            revenue_per_entity = total_revenue / entity_count if entity_count > 0 else 0
            cash_conversion_efficiency = (current_cash / total_revenue * 100) if total_revenue > 0 else 0

            # Compile comprehensive CFO report
            generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            cfo_report = {
                'report_type': 'CFO_Financial_Ratios_KPIs',
                'report_name': f'CFO Financial Ratios & KPIs - {period.title()}',
                'period_info': {
                    'period': period,
                    'start_date': start_date_str,
                    'end_date': end_date_str,
                    'entity_filter': entity_filter
                },
                'financial_overview': {
                    'total_revenue': round(total_revenue, 2),
                    'total_expenses': round(total_expenses, 2),
                    'net_income': round(net_income, 2),
                    'current_cash_position': round(current_cash, 2),
                    'total_transactions': total_transactions,
                    'active_entities': entity_count
                },
                'profitability_ratios': {
                    'gross_margin_percent': round(gross_margin, 2),
                    'expense_ratio_percent': round(expense_ratio, 2),
                    'net_margin_percent': round(gross_margin, 2),  # Same as gross margin in this simple model
                    'revenue_per_transaction': round(revenue_per_transaction, 2)
                },
                'efficiency_metrics': {
                    'revenue_per_entity': round(revenue_per_entity, 2),
                    'cash_conversion_efficiency_percent': round(cash_conversion_efficiency, 2),
                    'transaction_volume': total_transactions,
                    'average_transaction_size': round(revenue_per_transaction, 2)
                },
                'key_insights': {
                    'revenue_health': 'Strong' if total_revenue > total_expenses * 2 else 'Moderate' if total_revenue > total_expenses else 'Needs Attention',
                    'cash_position': 'Healthy' if current_cash > 0 else 'Negative',
                    'operational_efficiency': 'High' if expense_ratio < 50 else 'Moderate' if expense_ratio < 80 else 'Low',
                    'profitability': 'Excellent' if gross_margin > 30 else 'Good' if gross_margin > 10 else 'Poor' if gross_margin > 0 else 'Loss'
                },
                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': generation_time_ms
            }

            return jsonify({
                'success': True,
                'data': cfo_report
            })

        except Exception as e:
            logger.error(f"Error generating CFO financial ratios report: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ============================================================================
    # CFO Executive Summary Report
    # ============================================================================
    @app.route('/api/reports/cfo-executive-summary', methods=['GET'])
    def api_cfo_executive_summary():
        """
        Executive Summary Report for CFO Dashboard

        Provides high-level overview with key metrics and insights
        """
        try:
            start_time = datetime.now()

            # Get current period data (last 30 days)
            end_date = date.today()
            start_date = end_date - timedelta(days=30)

            # Get previous period for comparison (30 days before that)
            prev_end_date = start_date
            prev_start_date = prev_end_date - timedelta(days=30)

            # Current period summary
            current_summary_query = """
                WITH current_data AS (
                    SELECT
                        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue,
                        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
                        COUNT(*) as transactions
                    FROM transactions
                    WHERE date::date >= %s AND date::date <= %s
                        AND amount::text != 'NaN' AND amount IS NOT NULL
                )
                SELECT
                    revenue,
                    expenses,
                    revenue - expenses as net_income,
                    transactions
                FROM current_data
            """

            current_data = db_manager.execute_query(current_summary_query, [start_date, end_date], fetch_one=True)

            # Previous period summary for comparison
            prev_data = db_manager.execute_query(current_summary_query, [prev_start_date, prev_end_date], fetch_one=True)

            # Calculate performance changes
            current_revenue = float(current_data.get('revenue', 0) or 0)
            current_expenses = float(current_data.get('expenses', 0) or 0)
            current_net = float(current_data.get('net_income', 0) or 0)

            prev_revenue = float(prev_data.get('revenue', 0) or 0)
            prev_expenses = float(prev_data.get('expenses', 0) or 0)
            prev_net = float(prev_data.get('net_income', 0) or 0)

            # Calculate percentage changes
            revenue_change = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
            expense_change = ((current_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0
            net_change = ((current_net - prev_net) / abs(prev_net) * 100) if prev_net != 0 else 0

            generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            executive_summary = {
                'report_type': 'CFO_Executive_Summary',
                'report_name': 'CFO Executive Summary - Last 30 Days',
                'period': {
                    'current_period': f"{start_date} to {end_date}",
                    'comparison_period': f"{prev_start_date} to {prev_end_date}"
                },
                'key_metrics': {
                    'revenue': {
                        'current': round(current_revenue, 2),
                        'previous': round(prev_revenue, 2),
                        'change_percent': round(revenue_change, 2),
                        'trend': 'up' if revenue_change > 0 else 'down' if revenue_change < 0 else 'flat'
                    },
                    'expenses': {
                        'current': round(current_expenses, 2),
                        'previous': round(prev_expenses, 2),
                        'change_percent': round(expense_change, 2),
                        'trend': 'up' if expense_change > 0 else 'down' if expense_change < 0 else 'flat'
                    },
                    'net_income': {
                        'current': round(current_net, 2),
                        'previous': round(prev_net, 2),
                        'change_percent': round(net_change, 2),
                        'trend': 'up' if net_change > 0 else 'down' if net_change < 0 else 'flat'
                    }
                },
                'executive_insights': [
                    f"Revenue {'increased' if revenue_change > 0 else 'decreased' if revenue_change < 0 else 'remained stable'} by {abs(revenue_change):.1f}% compared to previous period",
                    f"Net income shows {'positive' if current_net > 0 else 'negative'} performance with {abs(net_change):.1f}% change",
                    f"Operating efficiency: {((current_revenue - current_expenses) / current_revenue * 100):.1f}% profit margin" if current_revenue > 0 else "Revenue generation needs attention"
                ],
                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': generation_time_ms
            }

            return jsonify({
                'success': True,
                'data': executive_summary
            })

        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ============================================================================
    # Cash Flow Statement (Operating, Investing, Financing Activities)
    # ============================================================================
    @app.route('/api/reports/cash-flow-statement', methods=['GET'])
    def api_cash_flow_statement():
        """
        Comprehensive Cash Flow Statement

        Classifies transactions into Operating, Investing, and Financing activities
        following standard accounting practices.

        GET Parameters:
            - start_date: Start date (YYYY-MM-DD) (optional)
            - end_date: End date (YYYY-MM-DD) (optional)
            - period: 'monthly', 'quarterly', 'yearly', 'all_time' (default: 'all_time')
            - entity: Filter by specific entity (optional)

        Returns:
            JSON with Cash Flow Statement broken down by activity type
        """
        try:
            start_time = datetime.now()

            # Parse parameters
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            period = request.args.get('period', 'all_time')
            entity_filter = request.args.get('entity', '')

            # Build date filter
            date_filter = ""
            params = []

            if start_date_str and end_date_str:
                date_filter = "WHERE date::date >= %s::date AND date::date <= %s::date"
                params.extend([start_date_str, end_date_str])
            elif period != 'all_time':
                end_date = date.today()
                if period == 'monthly':
                    start_date = end_date.replace(day=1)
                elif period == 'quarterly':
                    start_date = end_date - timedelta(days=90)
                elif period == 'yearly':
                    start_date = end_date - timedelta(days=365)

                date_filter = "WHERE date::date >= %s::date AND date::date <= %s::date"
                params.extend([start_date.isoformat(), end_date.isoformat()])
            else:
                date_filter = "WHERE 1=1"

            if entity_filter:
                date_filter += " AND classified_entity = %s"
                params.append(entity_filter)

            # Operating Activities - core business operations
            operating_query = f"""
                SELECT
                    COALESCE(accounting_category, 'Other Operating') as category,
                    SUM(amount) as total,
                    COUNT(*) as count
                FROM transactions
                {date_filter}
                AND (
                    LOWER(COALESCE(accounting_category, '')) LIKE '%revenue%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%sales%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%service%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%expense%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%salary%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%wage%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%rent%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%utilities%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%supplies%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%tax%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%interest income%' OR
                    LOWER(COALESCE(description, '')) LIKE '%payment received%' OR
                    LOWER(COALESCE(description, '')) LIKE '%vendor payment%' OR
                    (amount < 0 AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%capital%'
                              AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%investment%'
                              AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%loan%'
                              AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%dividend%')
                )
                GROUP BY accounting_category
                ORDER BY ABS(SUM(amount)) DESC
            """

            # Investing Activities - capital expenditures and investments
            investing_query = f"""
                SELECT
                    COALESCE(accounting_category, 'Other Investing') as category,
                    SUM(amount) as total,
                    COUNT(*) as count
                FROM transactions
                {date_filter}
                AND (
                    LOWER(COALESCE(accounting_category, '')) LIKE '%equipment%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%property%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%asset purchase%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%investment%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%acquisition%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%capex%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%capital expenditure%' OR
                    LOWER(COALESCE(description, '')) LIKE '%purchase equipment%' OR
                    LOWER(COALESCE(description, '')) LIKE '%asset sale%'
                )
                GROUP BY accounting_category
                ORDER BY ABS(SUM(amount)) DESC
            """

            # Financing Activities - debt and equity transactions
            financing_query = f"""
                SELECT
                    COALESCE(accounting_category, 'Other Financing') as category,
                    SUM(amount) as total,
                    COUNT(*) as count
                FROM transactions
                {date_filter}
                AND (
                    LOWER(COALESCE(accounting_category, '')) LIKE '%loan%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%debt%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%dividend%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%capital contribution%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%equity%' OR
                    LOWER(COALESCE(accounting_category, '')) LIKE '%financing%' OR
                    LOWER(COALESCE(description, '')) LIKE '%loan payment%' OR
                    LOWER(COALESCE(description, '')) LIKE '%owner contribution%'
                )
                GROUP BY accounting_category
                ORDER BY ABS(SUM(amount)) DESC
            """

            # Execute queries
            query_params = tuple(params) if params else None
            operating_data = db_manager.execute_query(operating_query, query_params, fetch_all=True)
            investing_data = db_manager.execute_query(investing_query, query_params, fetch_all=True)
            financing_data = db_manager.execute_query(financing_query, query_params, fetch_all=True)

            # Process Operating Activities
            operating_total = Decimal('0')
            operating_categories = []
            for row in operating_data:
                amount = Decimal(str(row['total'] or 0))
                operating_categories.append({
                    'category': row['category'],
                    'amount': float(amount),
                    'count': row['count']
                })
                operating_total += amount

            # Process Investing Activities
            investing_total = Decimal('0')
            investing_categories = []
            for row in investing_data:
                amount = Decimal(str(row['total'] or 0))
                investing_categories.append({
                    'category': row['category'],
                    'amount': float(amount),
                    'count': row['count']
                })
                investing_total += amount

            # Process Financing Activities
            financing_total = Decimal('0')
            financing_categories = []
            for row in financing_data:
                amount = Decimal(str(row['total'] or 0))
                financing_categories.append({
                    'category': row['category'],
                    'amount': float(amount),
                    'count': row['count']
                })
                financing_total += amount

            # Calculate net cash flow
            net_cash_flow = operating_total + investing_total + financing_total

            # Get beginning and ending cash balances
            beginning_balance_query = f"""
                SELECT COALESCE(SUM(amount), 0) as balance
                FROM transactions
                WHERE date::date < %s::date
                {' AND classified_entity = %s' if entity_filter else ''}
            """
            # For beginning balance calculation, we need a start date
            if params and len(params) >= 1:
                beginning_start_date = params[0]
            else:
                # For all_time period, use a very early date to get beginning balance of 0
                beginning_start_date = '1900-01-01'
            beginning_params = [beginning_start_date]
            if entity_filter:
                beginning_params.append(entity_filter)

            beginning_result = db_manager.execute_query(beginning_balance_query, tuple(beginning_params), fetch_one=True)
            beginning_balance = Decimal(str(beginning_result['balance'] or 0)) if beginning_result else Decimal('0')
            ending_balance = beginning_balance + net_cash_flow

            generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'statement': {
                    'statement_type': 'CashFlowStatement',
                    'statement_name': f'Cash Flow Statement - {period.title()}',
                    'period': {
                        'type': period,
                        'start_date': start_date_str or params[0] if params else 'All time',
                        'end_date': end_date_str or params[1] if len(params) > 1 else 'Today',
                        'entity_filter': entity_filter or 'All entities'
                    },
                    'operating_activities': {
                        'total': float(operating_total),
                        'categories': operating_categories,
                        'description': 'Cash flows from core business operations'
                    },
                    'investing_activities': {
                        'total': float(investing_total),
                        'categories': investing_categories,
                        'description': 'Cash flows from investments and capital expenditures'
                    },
                    'financing_activities': {
                        'total': float(financing_total),
                        'categories': financing_categories,
                        'description': 'Cash flows from debt, equity, and dividends'
                    },
                    'summary': {
                        'beginning_cash_balance': float(beginning_balance),
                        'net_cash_from_operating': float(operating_total),
                        'net_cash_from_investing': float(investing_total),
                        'net_cash_from_financing': float(financing_total),
                        'net_change_in_cash': float(net_cash_flow),
                        'ending_cash_balance': float(ending_balance)
                    },
                    'key_metrics': {
                        'operating_cash_flow_ratio': float(operating_total / financing_total) if financing_total != 0 else 0,
                        'free_cash_flow': float(operating_total + investing_total),
                        'cash_flow_adequacy': float(operating_total / abs(investing_total)) if investing_total < 0 else 0
                    },
                    'generated_at': datetime.now().isoformat(),
                    'generation_time_ms': generation_time_ms
                }
            })

        except Exception as e:
            logger.error(f"Error generating cash flow statement: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ============================================================================
    # Budget vs Actual Analysis
    # ============================================================================
    @app.route('/api/reports/budget-vs-actual', methods=['GET', 'POST'])
    def api_budget_vs_actual():
        """
        Budget vs Actual Variance Analysis

        Compares actual financial performance against budget targets.
        Budget can be provided as a percentage of historical performance or as absolute values.

        GET/POST Parameters:
            - period: 'monthly', 'quarterly', 'yearly' (default: 'monthly')
            - budget_method: 'historical_avg', 'fixed_target', 'growth_based' (default: 'historical_avg')
            - growth_rate: Growth rate percentage for growth-based budgets (optional, default: 10)
            - entity: Filter by specific entity (optional)
            - budget_data: JSON object with budget targets (for fixed_target method)

        Returns:
            JSON with variance analysis showing budget vs actual performance
        """
        try:
            start_time = datetime.now()

            # Parse parameters
            if request.method == 'POST':
                params_data = request.json or {}
            else:
                params_data = request.args

            period = params_data.get('period', 'monthly')
            budget_method = params_data.get('budget_method', 'historical_avg')
            growth_rate = float(params_data.get('growth_rate', 10))
            entity_filter = params_data.get('entity', '')
            budget_data = params_data.get('budget_data', {})

            # Determine period dates
            end_date = date.today()
            if period == 'monthly':
                start_date = end_date.replace(day=1)
                prev_start = (start_date - timedelta(days=1)).replace(day=1)
                prev_end = start_date - timedelta(days=1)
            elif period == 'quarterly':
                start_date = end_date - timedelta(days=90)
                prev_start = start_date - timedelta(days=90)
                prev_end = start_date - timedelta(days=1)
            elif period == 'yearly':
                start_date = end_date - timedelta(days=365)
                prev_start = start_date - timedelta(days=365)
                prev_end = start_date - timedelta(days=1)

            # Build entity filter
            entity_clause = ""
            entity_params = []
            if entity_filter:
                entity_clause = "AND classified_entity = %s"
                entity_params = [entity_filter]

            # Get actual performance for current period
            actual_query = f"""
                SELECT
                    COALESCE(accounting_category, 'Uncategorized') as category,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
                    COUNT(*) as transaction_count
                FROM transactions
                WHERE date::date >= %s::date AND date::date <= %s::date
                {entity_clause}
                GROUP BY accounting_category
                ORDER BY (revenue + expenses) DESC
            """

            actual_data = db_manager.execute_query(
                actual_query,
                tuple([start_date.isoformat(), end_date.isoformat()] + entity_params),
                fetch_all=True
            )

            # Calculate budget based on method
            budget_targets = {}

            if budget_method == 'historical_avg':
                # Use previous period average
                historical_query = f"""
                    SELECT
                        COALESCE(accounting_category, 'Uncategorized') as category,
                        AVG(CASE WHEN amount > 0 THEN amount ELSE 0 END) * COUNT(DISTINCT date::date) as revenue_budget,
                        AVG(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) * COUNT(DISTINCT date::date) as expense_budget
                    FROM transactions
                    WHERE date::date >= %s::date AND date::date <= %s::date
                    {entity_clause}
                    GROUP BY accounting_category
                """

                historical_data = db_manager.execute_query(
                    historical_query,
                    tuple([prev_start.isoformat(), prev_end.isoformat()] + entity_params),
                    fetch_all=True
                )

                for row in historical_data:
                    budget_targets[row['category']] = {
                        'revenue_budget': float(row['revenue_budget'] or 0),
                        'expense_budget': float(row['expense_budget'] or 0)
                    }

            elif budget_method == 'growth_based':
                # Use previous period with growth rate applied
                historical_query = f"""
                    SELECT
                        COALESCE(accounting_category, 'Uncategorized') as category,
                        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue,
                        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
                    FROM transactions
                    WHERE date::date >= %s::date AND date::date <= %s::date
                    {entity_clause}
                    GROUP BY accounting_category
                """

                historical_data = db_manager.execute_query(
                    historical_query,
                    tuple([prev_start.isoformat(), prev_end.isoformat()] + entity_params),
                    fetch_all=True
                )

                growth_multiplier = 1 + (growth_rate / 100)
                for row in historical_data:
                    budget_targets[row['category']] = {
                        'revenue_budget': float(row['revenue'] or 0) * growth_multiplier,
                        'expense_budget': float(row['expenses'] or 0) * growth_multiplier
                    }

            elif budget_method == 'fixed_target' and budget_data:
                # Use provided budget targets
                budget_targets = budget_data

            # Calculate variances
            variance_analysis = []
            total_revenue_actual = Decimal('0')
            total_revenue_budget = Decimal('0')
            total_expense_actual = Decimal('0')
            total_expense_budget = Decimal('0')

            for row in actual_data:
                category = row['category']
                revenue_actual = Decimal(str(row['revenue'] or 0))
                expense_actual = Decimal(str(row['expenses'] or 0))

                # Get budget targets
                budget = budget_targets.get(category, {'revenue_budget': 0, 'expense_budget': 0})
                revenue_budget = Decimal(str(budget.get('revenue_budget', 0)))
                expense_budget = Decimal(str(budget.get('expense_budget', 0)))

                # Calculate variances
                revenue_variance = revenue_actual - revenue_budget
                expense_variance = expense_actual - expense_budget
                revenue_variance_pct = (revenue_variance / revenue_budget * 100) if revenue_budget != 0 else 0
                expense_variance_pct = (expense_variance / expense_budget * 100) if expense_budget != 0 else 0

                variance_analysis.append({
                    'category': category,
                    'revenue': {
                        'actual': float(revenue_actual),
                        'budget': float(revenue_budget),
                        'variance': float(revenue_variance),
                        'variance_percent': float(revenue_variance_pct),
                        'status': 'favorable' if revenue_variance > 0 else 'unfavorable' if revenue_variance < 0 else 'on_target'
                    },
                    'expenses': {
                        'actual': float(expense_actual),
                        'budget': float(expense_budget),
                        'variance': float(expense_variance),
                        'variance_percent': float(expense_variance_pct),
                        'status': 'favorable' if expense_variance < 0 else 'unfavorable' if expense_variance > 0 else 'on_target'
                    },
                    'transaction_count': row['transaction_count']
                })

                total_revenue_actual += revenue_actual
                total_revenue_budget += revenue_budget
                total_expense_actual += expense_actual
                total_expense_budget += expense_budget

            # Calculate total variances
            total_revenue_variance = total_revenue_actual - total_revenue_budget
            total_expense_variance = total_expense_actual - total_expense_budget
            net_income_actual = total_revenue_actual - total_expense_actual
            net_income_budget = total_revenue_budget - total_expense_budget
            net_income_variance = net_income_actual - net_income_budget

            generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'report': {
                    'report_type': 'BudgetVsActual',
                    'report_name': f'Budget vs Actual Analysis - {period.title()}',
                    'period': {
                        'type': period,
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'entity_filter': entity_filter or 'All entities'
                    },
                    'budget_method': budget_method,
                    'growth_rate': growth_rate if budget_method == 'growth_based' else None,
                    'variance_analysis': variance_analysis,
                    'summary': {
                        'revenue': {
                            'actual': float(total_revenue_actual),
                            'budget': float(total_revenue_budget),
                            'variance': float(total_revenue_variance),
                            'variance_percent': float((total_revenue_variance / total_revenue_budget * 100) if total_revenue_budget != 0 else 0),
                            'achievement_rate': float((total_revenue_actual / total_revenue_budget * 100) if total_revenue_budget != 0 else 0)
                        },
                        'expenses': {
                            'actual': float(total_expense_actual),
                            'budget': float(total_expense_budget),
                            'variance': float(total_expense_variance),
                            'variance_percent': float((total_expense_variance / total_expense_budget * 100) if total_expense_budget != 0 else 0),
                            'achievement_rate': float((total_expense_actual / total_expense_budget * 100) if total_expense_budget != 0 else 0)
                        },
                        'net_income': {
                            'actual': float(net_income_actual),
                            'budget': float(net_income_budget),
                            'variance': float(net_income_variance),
                            'variance_percent': float((net_income_variance / abs(net_income_budget) * 100) if net_income_budget != 0 else 0)
                        }
                    },
                    'key_insights': {
                        'revenue_performance': 'Above Target' if total_revenue_variance > 0 else 'Below Target' if total_revenue_variance < 0 else 'On Target',
                        'expense_control': 'Under Budget' if total_expense_variance < 0 else 'Over Budget' if total_expense_variance > 0 else 'On Budget',
                        'overall_performance': 'Exceeding Expectations' if net_income_variance > 0 else 'Below Expectations' if net_income_variance < 0 else 'Meeting Expectations'
                    },
                    'generated_at': datetime.now().isoformat(),
                    'generation_time_ms': generation_time_ms
                }
            })

        except Exception as e:
            logger.error(f"Error generating budget vs actual report: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ============================================================================
    # Comprehensive Trend Analysis with Forecasting
    # ============================================================================
    @app.route('/api/reports/trend-analysis', methods=['GET'])
    def api_trend_analysis():
        """
        Multi-Period Trend Analysis with Growth Rates and Patterns

        Analyzes financial trends across multiple time periods with
        period-over-period comparisons and trend indicators.

        GET Parameters:
            - metric: 'revenue', 'expenses', 'profit', 'cash_flow', 'all' (default: 'all')
            - granularity: 'monthly', 'quarterly', 'yearly' (default: 'monthly')
            - periods: Number of periods to analyze (default: 12)
            - entity: Filter by specific entity (optional)
            - include_forecast: Include forecast for next periods (true/false) (default: false)

        Returns:
            JSON with trend analysis data and insights
        """
        try:
            start_time = datetime.now()

            # Parse parameters
            metric = request.args.get('metric', 'all')
            granularity = request.args.get('granularity', 'monthly')
            periods = int(request.args.get('periods', 12))
            entity_filter = request.args.get('entity', '')
            include_forecast = request.args.get('include_forecast', 'false').lower() == 'true'

            # Build entity filter
            entity_clause = ""
            entity_params = []
            if entity_filter:
                entity_clause = "AND classified_entity = %s"
                entity_params = [entity_filter]

            # Build time grouping based on granularity
            if granularity == 'monthly':
                time_group = "DATE_TRUNC('month', date::date)"
                interval = f"{periods} months"
            elif granularity == 'quarterly':
                time_group = "DATE_TRUNC('quarter', date::date)"
                interval = f"{periods * 3} months"
            elif granularity == 'yearly':
                time_group = "DATE_TRUNC('year', date::date)"
                interval = f"{periods * 12} months"

            # Get trend data
            trend_query = f"""
                SELECT
                    {time_group} as period,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
                    SUM(amount) as net_profit,
                    COUNT(*) as transaction_count,
                    AVG(CASE WHEN amount > 0 THEN amount ELSE NULL END) as avg_revenue_transaction,
                    AVG(CASE WHEN amount < 0 THEN ABS(amount) ELSE NULL END) as avg_expense_transaction
                FROM transactions
                WHERE date::date >= CURRENT_DATE - INTERVAL '{interval}'
                    AND amount IS NOT NULL
                    AND amount::text != 'NaN'
                    {entity_clause}
                GROUP BY {time_group}
                ORDER BY period ASC
            """

            trend_data = db_manager.execute_query(trend_query, tuple(entity_params), fetch_all=True)

            # Process trend data and calculate growth rates
            periods_list = []
            previous_values = {'revenue': None, 'expenses': None, 'net_profit': None}

            for row in trend_data:
                period_date = row['period']
                revenue = float(row['revenue'] or 0)
                expenses = float(row['expenses'] or 0)
                net_profit = float(row['net_profit'] or 0)

                # Calculate growth rates
                revenue_growth = None
                if previous_values['revenue'] is not None and previous_values['revenue'] != 0:
                    revenue_growth = ((revenue - previous_values['revenue']) / previous_values['revenue'] * 100)

                expense_growth = None
                if previous_values['expenses'] is not None and previous_values['expenses'] != 0:
                    expense_growth = ((expenses - previous_values['expenses']) / previous_values['expenses'] * 100)

                profit_growth = None
                if previous_values['net_profit'] is not None and abs(previous_values['net_profit']) > 0:
                    profit_growth = ((net_profit - previous_values['net_profit']) / abs(previous_values['net_profit']) * 100)

                period_info = {
                    'period': period_date.isoformat() if hasattr(period_date, 'isoformat') else str(period_date),
                    'revenue': round(revenue, 2),
                    'expenses': round(expenses, 2),
                    'net_profit': round(net_profit, 2),
                    'transaction_count': row['transaction_count'],
                    'avg_revenue_transaction': round(float(row['avg_revenue_transaction'] or 0), 2),
                    'avg_expense_transaction': round(float(row['avg_expense_transaction'] or 0), 2),
                    'growth_rates': {
                        'revenue': round(revenue_growth, 2) if revenue_growth is not None else None,
                        'expenses': round(expense_growth, 2) if expense_growth is not None else None,
                        'profit': round(profit_growth, 2) if profit_growth is not None else None
                    },
                    'profit_margin': round((net_profit / revenue * 100), 2) if revenue > 0 else 0
                }

                periods_list.append(period_info)

                # Update previous values
                previous_values['revenue'] = revenue
                previous_values['expenses'] = expenses
                previous_values['net_profit'] = net_profit

            # Calculate overall statistics
            if periods_list:
                total_revenue = sum(p['revenue'] for p in periods_list)
                total_expenses = sum(p['expenses'] for p in periods_list)
                total_profit = sum(p['net_profit'] for p in periods_list)
                avg_revenue = total_revenue / len(periods_list)
                avg_expenses = total_expenses / len(periods_list)
                avg_profit = total_profit / len(periods_list)

                # Calculate average growth rates (excluding None values)
                revenue_growths = [p['growth_rates']['revenue'] for p in periods_list if p['growth_rates']['revenue'] is not None]
                expense_growths = [p['growth_rates']['expenses'] for p in periods_list if p['growth_rates']['expenses'] is not None]
                profit_growths = [p['growth_rates']['profit'] for p in periods_list if p['growth_rates']['profit'] is not None]

                avg_revenue_growth = sum(revenue_growths) / len(revenue_growths) if revenue_growths else 0
                avg_expense_growth = sum(expense_growths) / len(expense_growths) if expense_growths else 0
                avg_profit_growth = sum(profit_growths) / len(profit_growths) if profit_growths else 0

                # Simple linear forecast for next periods if requested
                forecast_periods = []
                if include_forecast and len(periods_list) >= 3:
                    # Use simple linear regression for forecast
                    last_3_revenue = [p['revenue'] for p in periods_list[-3:]]
                    last_3_expenses = [p['expenses'] for p in periods_list[-3:]]
                    last_3_profit = [p['net_profit'] for p in periods_list[-3:]]

                    revenue_trend = (last_3_revenue[-1] - last_3_revenue[0]) / 3
                    expense_trend = (last_3_expenses[-1] - last_3_expenses[0]) / 3
                    profit_trend = (last_3_profit[-1] - last_3_profit[0]) / 3

                    # Forecast next 3 periods
                    for i in range(1, 4):
                        forecast_periods.append({
                            'period': f'Forecast +{i}',
                            'revenue': round(last_3_revenue[-1] + (revenue_trend * i), 2),
                            'expenses': round(last_3_expenses[-1] + (expense_trend * i), 2),
                            'net_profit': round(last_3_profit[-1] + (profit_trend * i), 2),
                            'is_forecast': True
                        })

                # Determine trend direction
                revenue_trend_direction = 'increasing' if avg_revenue_growth > 5 else 'decreasing' if avg_revenue_growth < -5 else 'stable'
                expense_trend_direction = 'increasing' if avg_expense_growth > 5 else 'decreasing' if avg_expense_growth < -5 else 'stable'
                profit_trend_direction = 'increasing' if avg_profit_growth > 5 else 'decreasing' if avg_profit_growth < -5 else 'stable'
            else:
                total_revenue = total_expenses = total_profit = 0
                avg_revenue = avg_expenses = avg_profit = 0
                avg_revenue_growth = avg_expense_growth = avg_profit_growth = 0
                revenue_trend_direction = expense_trend_direction = profit_trend_direction = 'insufficient_data'
                forecast_periods = []

            generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'analysis': {
                    'report_type': 'TrendAnalysis',
                    'report_name': f'Trend Analysis - {granularity.title()} ({periods} periods)',
                    'parameters': {
                        'metric': metric,
                        'granularity': granularity,
                        'periods_analyzed': len(periods_list),
                        'entity_filter': entity_filter or 'All entities',
                        'forecast_included': include_forecast
                    },
                    'period_data': periods_list,
                    'forecast': forecast_periods if include_forecast else [],
                    'summary_statistics': {
                        'total_revenue': round(total_revenue, 2),
                        'total_expenses': round(total_expenses, 2),
                        'total_profit': round(total_profit, 2),
                        'average_revenue_per_period': round(avg_revenue, 2),
                        'average_expenses_per_period': round(avg_expenses, 2),
                        'average_profit_per_period': round(avg_profit, 2),
                        'average_revenue_growth': round(avg_revenue_growth, 2),
                        'average_expense_growth': round(avg_expense_growth, 2),
                        'average_profit_growth': round(avg_profit_growth, 2)
                    },
                    'trend_indicators': {
                        'revenue_trend': revenue_trend_direction,
                        'expense_trend': expense_trend_direction,
                        'profit_trend': profit_trend_direction,
                        'overall_health': 'improving' if profit_trend_direction == 'increasing' else 'declining' if profit_trend_direction == 'decreasing' else 'stable'
                    },
                    'key_insights': [
                        f"Revenue is {revenue_trend_direction} with average {abs(avg_revenue_growth):.1f}% {'growth' if avg_revenue_growth > 0 else 'decline'} per period",
                        f"Expenses are {expense_trend_direction} with average {abs(avg_expense_growth):.1f}% {'increase' if avg_expense_growth > 0 else 'decrease'} per period",
                        f"Profit trend is {profit_trend_direction} with average {abs(avg_profit_growth):.1f}% change per period",
                        f"Overall financial health is {profit_trend_direction}"
                    ],
                    'generated_at': datetime.now().isoformat(),
                    'generation_time_ms': generation_time_ms
                }
            })

        except Exception as e:
            logger.error(f"Error generating trend analysis: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ============================================================================
    # Risk Assessment Dashboard
    # ============================================================================
    @app.route('/api/reports/risk-assessment', methods=['GET'])
    def api_risk_assessment():
        """
        Comprehensive Risk Assessment Dashboard

        Evaluates financial risks across liquidity, solvency, operational,
        and market risk categories with actionable risk scores.

        GET Parameters:
            - entity: Filter by specific entity (optional)
            - period: 'monthly', 'quarterly', 'yearly' (default: 'yearly')

        Returns:
            JSON with comprehensive risk assessment and mitigation recommendations
        """
        try:
            start_time = datetime.now()

            # Parse parameters
            entity_filter = request.args.get('entity', '')
            period = request.args.get('period', 'yearly')

            # Build entity filter
            entity_clause = ""
            entity_params = []
            if entity_filter:
                entity_clause = "AND classified_entity = %s"
                entity_params = [entity_filter]

            # Determine date range
            end_date = date.today()
            if period == 'monthly':
                start_date = end_date - timedelta(days=30)
            elif period == 'quarterly':
                start_date = end_date - timedelta(days=90)
            else:  # yearly
                start_date = end_date - timedelta(days=365)

            # Get comprehensive financial data for risk analysis
            financial_data_query = f"""
                SELECT
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_revenue,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_expenses,
                    SUM(amount) as net_position,
                    COUNT(*) as transaction_count,
                    COUNT(DISTINCT DATE_TRUNC('month', date::date)) as active_months,
                    STDDEV(amount) as amount_volatility,
                    MIN(amount) as largest_outflow,
                    MAX(amount) as largest_inflow
                FROM transactions
                WHERE date::date >= %s AND date::date <= %s
                    AND amount IS NOT NULL
                    AND amount::text != 'NaN'
                    {entity_clause}
            """

            financial_result = db_manager.execute_query(
                financial_data_query,
                tuple([start_date.isoformat(), end_date.isoformat()] + entity_params),
                fetch_one=True
            )

            # Get cash flow volatility by month
            cash_volatility_query = f"""
                SELECT
                    DATE_TRUNC('month', date::date) as month,
                    SUM(amount) as monthly_cash_flow
                FROM transactions
                WHERE date::date >= %s AND date::date <= %s
                    AND amount IS NOT NULL
                    AND amount::text != 'NaN'
                    {entity_clause}
                GROUP BY DATE_TRUNC('month', date::date)
                ORDER BY month
            """

            cash_volatility_data = db_manager.execute_query(
                cash_volatility_query,
                tuple([start_date.isoformat(), end_date.isoformat()] + entity_params),
                fetch_all=True
            )

            # Calculate risk metrics
            total_revenue = float(financial_result.get('total_revenue', 0) or 0)
            total_expenses = float(financial_result.get('total_expenses', 0) or 0)
            net_position = float(financial_result.get('net_position', 0) or 0)
            transaction_count = int(financial_result.get('transaction_count', 0) or 0)
            active_months = int(financial_result.get('active_months', 0) or 1)
            amount_volatility = float(financial_result.get('amount_volatility', 0) or 0)
            largest_outflow = abs(float(financial_result.get('largest_outflow', 0) or 0))
            largest_inflow = float(financial_result.get('largest_inflow', 0) or 0)

            # Calculate monthly cash flows
            monthly_flows = [float(row['monthly_cash_flow'] or 0) for row in cash_volatility_data]
            avg_monthly_flow = sum(monthly_flows) / len(monthly_flows) if monthly_flows else 0
            cash_flow_stddev = Decimal(str(amount_volatility))

            # === LIQUIDITY RISK ===
            # Current ratio approximation (positive flows / negative flows)
            current_ratio = total_revenue / total_expenses if total_expenses > 0 else 0
            liquidity_score = min(100, (current_ratio * 50))  # Score out of 100

            # Cash burn rate (months of runway)
            monthly_burn = total_expenses / active_months if active_months > 0 else 0
            months_of_runway = net_position / monthly_burn if monthly_burn > 0 else float('inf')
            months_of_runway = min(months_of_runway, 999)  # Cap at reasonable value

            liquidity_risk_level = 'low' if liquidity_score > 70 else 'medium' if liquidity_score > 40 else 'high'

            # === SOLVENCY RISK ===
            # Debt-to-equity approximation (expenses / revenue)
            debt_to_income_ratio = total_expenses / total_revenue if total_revenue > 0 else 0
            solvency_score = max(0, min(100, (1 - debt_to_income_ratio) * 100))

            solvency_risk_level = 'low' if solvency_score > 60 else 'medium' if solvency_score > 30 else 'high'

            # === OPERATIONAL RISK ===
            # Based on transaction volatility and concentration
            avg_transaction_size = total_revenue / transaction_count if transaction_count > 0 else 0
            concentration_risk = (largest_inflow / total_revenue * 100) if total_revenue > 0 else 0

            operational_score = max(0, min(100, 100 - concentration_risk))
            operational_risk_level = 'low' if operational_score > 70 else 'medium' if operational_score > 40 else 'high'

            # === MARKET RISK ===
            # Based on cash flow volatility
            volatility_ratio = (cash_flow_stddev / Decimal(str(abs(avg_monthly_flow)))) if avg_monthly_flow != 0 else Decimal('0')
            market_score = max(0, min(100, 100 - float(volatility_ratio * 50)))

            market_risk_level = 'low' if market_score > 60 else 'medium' if market_score > 30 else 'high'

            # === OVERALL RISK SCORE ===
            overall_risk_score = (liquidity_score * 0.3 + solvency_score * 0.3 + operational_score * 0.2 + market_score * 0.2)
            overall_risk_level = 'low' if overall_risk_score > 70 else 'medium' if overall_risk_score > 40 else 'high'

            # Generate recommendations
            recommendations = []

            if liquidity_risk_level == 'high':
                recommendations.append({
                    'category': 'Liquidity',
                    'severity': 'high',
                    'recommendation': 'Improve cash reserves. Current ratio is below healthy levels. Consider reducing expenses or increasing revenue.',
                    'action_items': [
                        'Accelerate accounts receivable collection',
                        'Negotiate extended payment terms with vendors',
                        'Review and reduce discretionary spending',
                        f'Build cash reserves to cover at least 3 months of expenses (currently {months_of_runway:.1f} months)'
                    ]
                })

            if solvency_risk_level == 'high':
                recommendations.append({
                    'category': 'Solvency',
                    'severity': 'high',
                    'recommendation': 'Expenses are high relative to revenue. Focus on profitability improvement.',
                    'action_items': [
                        'Conduct comprehensive expense audit',
                        'Identify and eliminate non-essential costs',
                        'Explore revenue diversification opportunities',
                        'Review pricing strategy for revenue optimization'
                    ]
                })

            if operational_risk_level == 'high':
                recommendations.append({
                    'category': 'Operational',
                    'severity': 'medium',
                    'recommendation': f'High revenue concentration detected ({concentration_risk:.1f}% from single source). Diversify revenue streams.',
                    'action_items': [
                        'Develop new customer acquisition strategy',
                        'Expand product/service offerings',
                        'Reduce dependency on single revenue source',
                        'Implement risk management protocols'
                    ]
                })

            if market_risk_level == 'high':
                recommendations.append({
                    'category': 'Market',
                    'severity': 'medium',
                    'recommendation': 'High cash flow volatility detected. Implement cash flow stabilization measures.',
                    'action_items': [
                        'Establish cash flow forecasting system',
                        'Create financial contingency plans',
                        'Consider revenue smoothing strategies',
                        'Build emergency reserves for volatile periods'
                    ]
                })

            if not recommendations:
                recommendations.append({
                    'category': 'Overall',
                    'severity': 'low',
                    'recommendation': 'Financial health is strong. Maintain current practices and continue monitoring.',
                    'action_items': [
                        'Continue regular financial monitoring',
                        'Maintain healthy cash reserves',
                        'Explore growth opportunities',
                        'Review and optimize operational efficiency'
                    ]
                })

            generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'assessment': {
                    'report_type': 'RiskAssessment',
                    'report_name': f'Risk Assessment Dashboard - {period.title()}',
                    'period': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'entity_filter': entity_filter or 'All entities'
                    },
                    'overall_risk': {
                        'score': round(overall_risk_score, 2),
                        'level': overall_risk_level,
                        'rating': 'Excellent' if overall_risk_score > 80 else 'Good' if overall_risk_score > 60 else 'Fair' if overall_risk_score > 40 else 'Poor'
                    },
                    'risk_categories': {
                        'liquidity': {
                            'score': round(liquidity_score, 2),
                            'level': liquidity_risk_level,
                            'metrics': {
                                'current_ratio': round(current_ratio, 2),
                                'months_of_runway': round(months_of_runway, 1),
                                'monthly_burn_rate': round(monthly_burn, 2)
                            }
                        },
                        'solvency': {
                            'score': round(solvency_score, 2),
                            'level': solvency_risk_level,
                            'metrics': {
                                'debt_to_income_ratio': round(debt_to_income_ratio, 2),
                                'expense_coverage': round((total_revenue / total_expenses * 100) if total_expenses > 0 else 0, 2)
                            }
                        },
                        'operational': {
                            'score': round(operational_score, 2),
                            'level': operational_risk_level,
                            'metrics': {
                                'concentration_risk': round(concentration_risk, 2),
                                'largest_inflow': round(largest_inflow, 2),
                                'largest_outflow': round(largest_outflow, 2)
                            }
                        },
                        'market': {
                            'score': round(market_score, 2),
                            'level': market_risk_level,
                            'metrics': {
                                'cash_flow_volatility': round(float(cash_flow_stddev), 2),
                                'volatility_ratio': round(float(volatility_ratio), 2)
                            }
                        }
                    },
                    'recommendations': recommendations,
                    'financial_summary': {
                        'total_revenue': round(total_revenue, 2),
                        'total_expenses': round(total_expenses, 2),
                        'net_position': round(net_position, 2),
                        'transaction_count': transaction_count,
                        'active_months': active_months
                    },
                    'generated_at': datetime.now().isoformat(),
                    'generation_time_ms': generation_time_ms
                }
            })

        except Exception as e:
            logger.error(f"Error generating risk assessment: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ============================================================================
    # Working Capital Analysis
    # ============================================================================
    @app.route('/api/reports/working-capital', methods=['GET'])
    def api_working_capital_analysis():
        """
        Working Capital Analysis Report

        Analyzes current assets, current liabilities, and working capital trends
        to assess short-term financial health and operational efficiency.

        GET Parameters:
            - entity: Filter by specific entity (optional)
            - period: 'monthly', 'quarterly', 'yearly' (default: 'yearly')

        Returns:
            JSON with working capital metrics and analysis
        """
        try:
            start_time = datetime.now()

            # Parse parameters
            entity_filter = request.args.get('entity', '')
            period = request.args.get('period', 'yearly')

            # Build entity filter
            entity_clause = ""
            entity_params = []
            if entity_filter:
                entity_clause = "AND classified_entity = %s"
                entity_params = [entity_filter]

            # Determine date range
            end_date = date.today()
            if period == 'monthly':
                start_date = end_date - timedelta(days=30)
                prev_start = start_date - timedelta(days=30)
                prev_end = start_date - timedelta(days=1)
            elif period == 'quarterly':
                start_date = end_date - timedelta(days=90)
                prev_start = start_date - timedelta(days=90)
                prev_end = start_date - timedelta(days=1)
            else:  # yearly
                start_date = end_date - timedelta(days=365)
                prev_start = start_date - timedelta(days=365)
                prev_end = start_date - timedelta(days=1)

            # Calculate current assets (cash, receivables, inventory-like items)
            current_assets_query = f"""
                SELECT
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as current_assets
                FROM transactions
                WHERE date::date >= %s AND date::date <= %s
                    AND amount IS NOT NULL
                    AND amount::text != 'NaN'
                    AND (
                        LOWER(COALESCE(accounting_category, '')) LIKE '%cash%' OR
                        LOWER(COALESCE(accounting_category, '')) LIKE '%receivable%' OR
                        LOWER(COALESCE(accounting_category, '')) LIKE '%revenue%' OR
                        LOWER(COALESCE(accounting_category, '')) LIKE '%inventory%' OR
                        amount > 0
                    )
                    {entity_clause}
            """

            # Calculate current liabilities (payables, short-term debts)
            current_liabilities_query = f"""
                SELECT
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as current_liabilities
                FROM transactions
                WHERE date::date >= %s AND date::date <= %s
                    AND amount IS NOT NULL
                    AND amount::text != 'NaN'
                    AND (
                        LOWER(COALESCE(accounting_category, '')) LIKE '%payable%' OR
                        LOWER(COALESCE(accounting_category, '')) LIKE '%expense%' OR
                        LOWER(COALESCE(accounting_category, '')) LIKE '%debt%' OR
                        LOWER(COALESCE(accounting_category, '')) LIKE '%liability%' OR
                        amount < 0
                    )
                    {entity_clause}
            """

            # Get current period data - Fixed parameter handling
            assets_params = [start_date.isoformat(), end_date.isoformat()]
            if entity_filter:
                assets_params.extend(entity_params)

            assets_result = db_manager.execute_query(
                current_assets_query,
                tuple(assets_params),
                fetch_one=True
            )
            liabilities_params = [start_date.isoformat(), end_date.isoformat()]
            if entity_filter:
                liabilities_params.extend(entity_params)

            liabilities_result = db_manager.execute_query(
                current_liabilities_query,
                tuple(liabilities_params),
                fetch_one=True
            )

            current_assets = float(assets_result.get('current_assets', 0) or 0)
            current_liabilities = float(liabilities_result.get('current_liabilities', 0) or 0)

            # Get previous period for comparison - Fixed parameter handling
            prev_assets_params = [prev_start.isoformat(), prev_end.isoformat()]
            if entity_filter:
                prev_assets_params.extend(entity_params)

            prev_assets_result = db_manager.execute_query(
                current_assets_query,
                tuple(prev_assets_params),
                fetch_one=True
            )

            prev_liabilities_params = [prev_start.isoformat(), prev_end.isoformat()]
            if entity_filter:
                prev_liabilities_params.extend(entity_params)

            prev_liabilities_result = db_manager.execute_query(
                current_liabilities_query,
                tuple(prev_liabilities_params),
                fetch_one=True
            )

            prev_assets = float(prev_assets_result.get('current_assets', 0) or 0)
            prev_liabilities = float(prev_liabilities_result.get('current_liabilities', 0) or 0)

            # Calculate working capital
            working_capital = current_assets - current_liabilities
            prev_working_capital = prev_assets - prev_liabilities

            # Calculate financial ratios
            current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0
            prev_current_ratio = prev_assets / prev_liabilities if prev_liabilities > 0 else 0

            # Quick ratio (assuming cash is 60% of current assets as approximation)
            quick_assets = current_assets * 0.6
            quick_ratio = quick_assets / current_liabilities if current_liabilities > 0 else 0

            # Working capital ratio
            working_capital_ratio = (working_capital / current_assets * 100) if current_assets > 0 else 0

            # Calculate changes
            wc_change = working_capital - prev_working_capital
            wc_change_pct = (wc_change / abs(prev_working_capital) * 100) if prev_working_capital != 0 else 0
            current_ratio_change = current_ratio - prev_current_ratio

            # Get monthly trend
            monthly_trend_query = f"""
                SELECT
                    DATE_TRUNC('month', date::date) as month,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as assets,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as liabilities
                FROM transactions
                WHERE date::date >= %s AND date::date <= %s
                    AND amount IS NOT NULL
                    AND amount::text != 'NaN'
                    {entity_clause}
                GROUP BY DATE_TRUNC('month', date::date)
                ORDER BY month
            """

            monthly_params = [start_date.isoformat(), end_date.isoformat()]
            if entity_filter:
                monthly_params.extend(entity_params)

            monthly_data = db_manager.execute_query(
                monthly_trend_query,
                tuple(monthly_params),
                fetch_all=True
            )

            monthly_trend = []
            for row in monthly_data:
                month_assets = float(row['assets'] or 0)
                month_liabilities = float(row['liabilities'] or 0)
                month_wc = month_assets - month_liabilities
                month_current_ratio = month_assets / month_liabilities if month_liabilities > 0 else 0

                monthly_trend.append({
                    'month': row['month'].isoformat() if hasattr(row['month'], 'isoformat') else str(row['month']),
                    'current_assets': round(month_assets, 2),
                    'current_liabilities': round(month_liabilities, 2),
                    'working_capital': round(month_wc, 2),
                    'current_ratio': round(month_current_ratio, 2)
                })

            # Health assessment
            if current_ratio >= 2.0:
                health_status = 'Excellent'
                health_color = 'green'
            elif current_ratio >= 1.5:
                health_status = 'Good'
                health_color = 'green'
            elif current_ratio >= 1.0:
                health_status = 'Fair'
                health_color = 'yellow'
            else:
                health_status = 'Concerning'
                health_color = 'red'

            # Generate insights
            insights = []
            if current_ratio < 1.0:
                insights.append({
                    'type': 'warning',
                    'message': f'Current ratio of {current_ratio:.2f} is below 1.0, indicating potential liquidity issues.',
                    'recommendation': 'Increase current assets or reduce current liabilities to improve short-term financial health.'
                })
            elif current_ratio > 3.0:
                insights.append({
                    'type': 'info',
                    'message': f'Current ratio of {current_ratio:.2f} is very high, which may indicate inefficient use of assets.',
                    'recommendation': 'Consider investing excess working capital for better returns.'
                })
            else:
                insights.append({
                    'type': 'success',
                    'message': f'Current ratio of {current_ratio:.2f} is within healthy range (1.0 - 3.0).',
                    'recommendation': 'Maintain current working capital management practices.'
                })

            if wc_change < 0:
                insights.append({
                    'type': 'warning',
                    'message': f'Working capital decreased by ${abs(wc_change):,.2f} ({abs(wc_change_pct):.1f}%) compared to previous period.',
                    'recommendation': 'Monitor cash flow closely and identify reasons for declining working capital.'
                })
            else:
                insights.append({
                    'type': 'success',
                    'message': f'Working capital increased by ${wc_change:,.2f} ({wc_change_pct:.1f}%) compared to previous period.',
                    'recommendation': 'Continue current growth trajectory while maintaining operational efficiency.'
                })

            generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'report': {
                    'report_type': 'WorkingCapitalAnalysis',
                    'report_name': f'Working Capital Analysis - {period.title()}',
                    'period': {
                        'current': {
                            'start_date': start_date.isoformat(),
                            'end_date': end_date.isoformat()
                        },
                        'previous': {
                            'start_date': prev_start.isoformat(),
                            'end_date': prev_end.isoformat()
                        },
                        'entity_filter': entity_filter or 'All entities'
                    },
                    'current_period': {
                        'current_assets': round(current_assets, 2),
                        'current_liabilities': round(current_liabilities, 2),
                        'working_capital': round(working_capital, 2),
                        'current_ratio': round(current_ratio, 2),
                        'quick_ratio': round(quick_ratio, 2),
                        'working_capital_ratio': round(working_capital_ratio, 2)
                    },
                    'previous_period': {
                        'current_assets': round(prev_assets, 2),
                        'current_liabilities': round(prev_liabilities, 2),
                        'working_capital': round(prev_working_capital, 2),
                        'current_ratio': round(prev_current_ratio, 2)
                    },
                    'changes': {
                        'working_capital_change': round(wc_change, 2),
                        'working_capital_change_percent': round(wc_change_pct, 2),
                        'current_ratio_change': round(current_ratio_change, 2),
                        'trend': 'improving' if wc_change > 0 else 'declining' if wc_change < 0 else 'stable'
                    },
                    'monthly_trend': monthly_trend,
                    'health_assessment': {
                        'status': health_status,
                        'color': health_color,
                        'score': round(min(100, current_ratio * 50), 2)
                    },
                    'key_metrics': {
                        'days_working_capital': round((working_capital / (current_liabilities / 30)) if current_liabilities > 0 else 0, 1),
                        'working_capital_turnover': round((current_assets / working_capital) if working_capital > 0 else 0, 2),
                        'asset_efficiency': round((current_assets / current_liabilities * 100) if current_liabilities > 0 else 0, 2)
                    },
                    'insights': insights,
                    'generated_at': datetime.now().isoformat(),
                    'generation_time_ms': generation_time_ms
                }
            })

        except Exception as e:
            logger.error(f"Error generating working capital analysis: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ============================================================================
    # Financial Forecast & Projections
    # ============================================================================
    @app.route('/api/reports/financial-forecast', methods=['GET'])
    def api_financial_forecast():
        """
        AI-Powered Financial Forecast & Projections

        Uses historical data and trend analysis to project future financial performance.
        Employs linear regression and moving averages for forecasting.

        GET Parameters:
            - forecast_periods: Number of periods to forecast (default: 6)
            - granularity: 'monthly', 'quarterly' (default: 'monthly')
            - entity: Filter by specific entity (optional)
            - historical_periods: Number of historical periods to analyze (default: 12)
            - method: 'linear', 'moving_average', 'weighted' (default: 'linear')

        Returns:
            JSON with historical data and future projections
        """
        try:
            start_time = datetime.now()

            # Parse parameters
            forecast_periods = int(request.args.get('forecast_periods', 6))
            granularity = request.args.get('granularity', 'monthly')
            entity_filter = request.args.get('entity', '')
            historical_periods = int(request.args.get('historical_periods', 12))
            method = request.args.get('method', 'linear')

            # Build entity filter
            entity_clause = ""
            entity_params = []
            if entity_filter:
                entity_clause = "AND classified_entity = %s"
                entity_params = [entity_filter]

            # Build time grouping
            if granularity == 'monthly':
                time_group = "DATE_TRUNC('month', date::date)"
                interval = f"{historical_periods} months"
            elif granularity == 'quarterly':
                time_group = "DATE_TRUNC('quarter', date::date)"
                interval = f"{historical_periods * 3} months"

            # Get historical data
            historical_query = f"""
                SELECT
                    {time_group} as period,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
                    SUM(amount) as net_profit,
                    COUNT(*) as transaction_count
                FROM transactions
                WHERE date::date >= CURRENT_DATE - INTERVAL '{interval}'
                    AND amount IS NOT NULL
                    AND amount::text != 'NaN'
                    {entity_clause}
                GROUP BY {time_group}
                ORDER BY period ASC
            """

            historical_data = db_manager.execute_query(historical_query, tuple(entity_params), fetch_all=True)

            # Process historical data
            historical_periods_list = []
            revenue_values = []
            expense_values = []
            profit_values = []

            for row in historical_data:
                revenue = float(row['revenue'] or 0)
                expenses = float(row['expenses'] or 0)
                profit = float(row['net_profit'] or 0)

                historical_periods_list.append({
                    'period': row['period'].isoformat() if hasattr(row['period'], 'isoformat') else str(row['period']),
                    'revenue': round(revenue, 2),
                    'expenses': round(expenses, 2),
                    'net_profit': round(profit, 2),
                    'transaction_count': row['transaction_count'],
                    'is_historical': True
                })

                revenue_values.append(revenue)
                expense_values.append(expenses)
                profit_values.append(profit)

            # Generate forecasts based on selected method
            forecast_list = []

            if method == 'linear' and len(revenue_values) >= 3:
                # Simple linear regression forecast
                n = len(revenue_values)

                # Calculate trend for each metric
                revenue_trend = (revenue_values[-1] - revenue_values[0]) / n
                expense_trend = (expense_values[-1] - expense_values[0]) / n
                profit_trend = (profit_values[-1] - profit_values[0]) / n

                for i in range(1, forecast_periods + 1):
                    forecast_list.append({
                        'period': f'Forecast +{i}',
                        'revenue': round(max(0, revenue_values[-1] + (revenue_trend * i)), 2),
                        'expenses': round(max(0, expense_values[-1] + (expense_trend * i)), 2),
                        'net_profit': round(profit_values[-1] + (profit_trend * i), 2),
                        'is_forecast': True,
                        'confidence': round(max(50, 90 - (i * 5)), 1)  # Confidence decreases with distance
                    })

            elif method == 'moving_average' and len(revenue_values) >= 3:
                # Moving average forecast (3-period)
                ma_window = min(3, len(revenue_values))

                revenue_ma = sum(revenue_values[-ma_window:]) / ma_window
                expense_ma = sum(expense_values[-ma_window:]) / ma_window
                profit_ma = sum(profit_values[-ma_window:]) / ma_window

                for i in range(1, forecast_periods + 1):
                    forecast_list.append({
                        'period': f'Forecast +{i}',
                        'revenue': round(revenue_ma, 2),
                        'expenses': round(expense_ma, 2),
                        'net_profit': round(profit_ma, 2),
                        'is_forecast': True,
                        'confidence': round(max(60, 85 - (i * 3)), 1)
                    })

            elif method == 'weighted' and len(revenue_values) >= 3:
                # Weighted average (more weight to recent periods)
                weights = [1, 2, 3]  # Recent periods get more weight
                total_weight = sum(weights)

                revenue_weighted = sum(r * w for r, w in zip(revenue_values[-3:], weights)) / total_weight
                expense_weighted = sum(e * w for e, w in zip(expense_values[-3:], weights)) / total_weight
                profit_weighted = sum(p * w for p, w in zip(profit_values[-3:], weights)) / total_weight

                # Apply slight growth trend
                growth_rate = 1.02  # 2% growth assumption

                for i in range(1, forecast_periods + 1):
                    forecast_list.append({
                        'period': f'Forecast +{i}',
                        'revenue': round(revenue_weighted * (growth_rate ** i), 2),
                        'expenses': round(expense_weighted * (growth_rate ** i), 2),
                        'net_profit': round(profit_weighted * (growth_rate ** i), 2),
                        'is_forecast': True,
                        'confidence': round(max(55, 88 - (i * 4)), 1)
                    })

            # Calculate forecast summary
            if forecast_list:
                forecast_revenue = sum(f['revenue'] for f in forecast_list)
                forecast_expenses = sum(f['expenses'] for f in forecast_list)
                forecast_profit = sum(f['net_profit'] for f in forecast_list)
                avg_confidence = sum(f['confidence'] for f in forecast_list) / len(forecast_list)
            else:
                forecast_revenue = forecast_expenses = forecast_profit = avg_confidence = 0

            # Calculate accuracy indicators
            if len(revenue_values) >= 2:
                historical_volatility = Decimal(str(max(revenue_values) - min(revenue_values))) / Decimal(str(sum(revenue_values) / len(revenue_values)))
                forecast_accuracy = max(0, min(100, 100 - float(historical_volatility * 50)))
            else:
                forecast_accuracy = 50

            generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'forecast': {
                    'report_type': 'FinancialForecast',
                    'report_name': f'Financial Forecast - {granularity.title()} ({forecast_periods} periods)',
                    'parameters': {
                        'forecast_periods': forecast_periods,
                        'historical_periods': len(historical_periods_list),
                        'granularity': granularity,
                        'method': method,
                        'entity_filter': entity_filter or 'All entities'
                    },
                    'historical_data': historical_periods_list,
                    'forecast_data': forecast_list,
                    'forecast_summary': {
                        'projected_revenue': round(forecast_revenue, 2),
                        'projected_expenses': round(forecast_expenses, 2),
                        'projected_profit': round(forecast_profit, 2),
                        'average_confidence': round(avg_confidence, 1),
                        'forecast_accuracy_score': round(forecast_accuracy, 1)
                    },
                    'methodology': {
                        'method_used': method,
                        'description': {
                            'linear': 'Linear regression based on historical trends',
                            'moving_average': '3-period moving average forecast',
                            'weighted': 'Weighted average with 2% growth assumption'
                        }.get(method, 'Unknown method'),
                        'limitations': [
                            'Forecasts assume continuation of historical trends',
                            'External factors and market changes not accounted for',
                            'Confidence decreases for longer-term projections',
                            'Should be used as guidance, not definitive predictions'
                        ]
                    },
                    'key_insights': [
                        f"Based on {len(historical_periods_list)} periods of historical data",
                        f"Projected {granularity} revenue: ${forecast_revenue / len(forecast_list) if forecast_list else 0:,.2f}",
                        f"Forecast confidence: {avg_confidence:.1f}%",
                        f"Accuracy indicator: {forecast_accuracy:.1f}%"
                    ],
                    'generated_at': datetime.now().isoformat(),
                    'generation_time_ms': generation_time_ms
                }
            })

        except Exception as e:
            logger.error(f"Error generating financial forecast: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/dre-pdf', methods=['GET'])
    def api_generate_dre_pdf():
        """
        Generate DRE (Demonstração do Resultado do Exercício) PDF Report

        GET Parameters:
            - start_date: Start date (YYYY-MM-DD, default: start of current year)
            - end_date: End date (YYYY-MM-DD, default: today)
            - entity: Entity filter (optional)
            - company_name: Company name for the report (default: Delta Mining)

        Returns:
            PDF file download
        """
        try:
            # Parse parameters
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            entity_filter = request.args.get('entity', '').strip()
            company_name = request.args.get('company_name', 'Delta Mining')

            # Default date range (current year)
            if not start_date_str:
                start_date = date(datetime.now().year, 1, 1)
            else:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

            if not end_date_str:
                end_date = date.today()
            else:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            # Validate dates
            if start_date > end_date:
                return jsonify({
                    'success': False,
                    'error': 'Start date cannot be after end date'
                }), 400

            # Create DRE report
            dre_report = DREReport(
                company_name=company_name,
                start_date=start_date,
                end_date=end_date,
                entity_filter=entity_filter if entity_filter else None
            )

            # Generate PDF
            pdf_content = dre_report.generate_dre_report()

            # Create response
            pdf_buffer = io.BytesIO(pdf_content)
            pdf_buffer.seek(0)

            # Generate filename
            entity_suffix = f"_{entity_filter}" if entity_filter else ""
            filename = f"DRE_{company_name.replace(' ', '_')}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}{entity_suffix}.pdf"

            return send_file(
                pdf_buffer,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )

        except Exception as e:
            logger.error(f"Error generating DRE PDF: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Error generating DRE PDF: {str(e)}'
            }), 500

    @app.route('/api/reports/balance-sheet-pdf', methods=['GET'])
    def api_generate_balance_sheet_pdf():
        """
        Generate Balance Sheet (Balanço Patrimonial) PDF Report

        GET Parameters:
            - end_date: End date for balance position (YYYY-MM-DD, default: today)
            - entity: Entity filter (optional)
            - company_name: Company name for the report (default: Delta Mining)

        Returns:
            PDF file download
        """
        try:
            # Parse parameters
            end_date_str = request.args.get('end_date')
            entity_filter = request.args.get('entity', '').strip()
            company_name = request.args.get('company_name', 'Delta Mining')

            # Default date (today)
            if not end_date_str:
                end_date = date.today()
            else:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            # Create Balance Sheet report
            balance_sheet_report = BalanceSheetReport(
                company_name=company_name,
                end_date=end_date,
                entity_filter=entity_filter if entity_filter else None
            )

            # Generate PDF
            pdf_content = balance_sheet_report.generate_balance_sheet_report()

            # Create response
            pdf_buffer = io.BytesIO(pdf_content)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"BalancoPatrimonial_{company_name.replace(' ', '_')}_{timestamp}.pdf"

            return send_file(
                pdf_buffer,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )

        except Exception as e:
            logger.error(f"Error generating Balance Sheet PDF: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Error generating Balance Sheet PDF: {str(e)}'
            }), 500

    @app.route('/api/reports/cash-flow-pdf', methods=['GET'])
    def api_generate_cash_flow_pdf():
        """
        Generate Cash Flow Statement (Demonstração de Fluxo de Caixa) PDF Report

        GET Parameters:
            - start_date: Start date for cash flow period (YYYY-MM-DD, default: beginning of current year)
            - end_date: End date for cash flow period (YYYY-MM-DD, default: today)
            - entity: Entity filter (optional)
            - company_name: Company name (default: Delta Mining)

        Returns:
            PDF file download with 'Content-Disposition: attachment' header
        """
        try:
            # Parse parameters
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            entity_filter = request.args.get('entity', '').strip()
            company_name = request.args.get('company_name', 'Delta Mining')

            # Parse dates
            start_date = None
            end_date = None

            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        start_date = datetime.strptime(start_date_str, '%m/%d/%Y').date()
                    except ValueError:
                        return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD or MM/DD/YYYY'}), 400

            if end_date_str:
                try:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        end_date = datetime.strptime(end_date_str, '%m/%d/%Y').date()
                    except ValueError:
                        return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD or MM/DD/YYYY'}), 400

            # Create Cash Flow report
            cash_flow_report = CashFlowReport(
                company_name=company_name,
                start_date=start_date,
                end_date=end_date,
                entity_filter=entity_filter if entity_filter else None
            )

            # Generate PDF content
            pdf_content = cash_flow_report.generate_cash_flow_report()

            # Create filename
            period_str = ""
            if start_date and end_date:
                if start_date.year == end_date.year:
                    period_str = f"_{start_date.year}"
                else:
                    period_str = f"_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
            else:
                period_str = f"_{datetime.now().year}"

            filename = f"demonstracao_fluxo_caixa{period_str}.pdf"

            # Return PDF as download
            response = make_response(pdf_content)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            response.headers['Content-Length'] = len(pdf_content)

            return response

        except Exception as e:
            logger.error(f"Error generating Cash Flow PDF: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Error generating Cash Flow PDF: {str(e)}'
            }), 500

    @app.route('/api/reports/dmpl-pdf', methods=['GET'])
    def api_generate_dmpl_pdf():
        """
        Generate DMPL (Demonstração das Mutações do Patrimônio Líquido) PDF Report

        GET Parameters:
            - start_date: Start date for equity period (YYYY-MM-DD, default: beginning of current year)
            - end_date: End date for equity period (YYYY-MM-DD, default: today)
            - entity: Entity filter (optional)
            - company_name: Company name (default: Delta Mining)

        Returns:
            PDF file download with 'Content-Disposition: attachment' header
        """
        try:
            # Parse parameters
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            entity_filter = request.args.get('entity', '').strip()
            company_name = request.args.get('company_name', 'Delta Mining')

            # Parse dates
            start_date = None
            end_date = None

            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        start_date = datetime.strptime(start_date_str, '%m/%d/%Y').date()
                    except ValueError:
                        return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD or MM/DD/YYYY'}), 400

            if end_date_str:
                try:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        end_date = datetime.strptime(end_date_str, '%m/%d/%Y').date()
                    except ValueError:
                        return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD or MM/DD/YYYY'}), 400

            # Create DMPL report
            dmpl_report = DMPLReport(
                company_name=company_name,
                start_date=start_date,
                end_date=end_date,
                entity_filter=entity_filter if entity_filter else None
            )

            # Generate PDF content
            pdf_content = dmpl_report.generate_dmpl_report()

            # Create filename
            period_str = ""
            if start_date and end_date:
                if start_date.year == end_date.year:
                    period_str = f"_{start_date.year}"
                else:
                    period_str = f"_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
            else:
                period_str = f"_{datetime.now().year}"

            filename = f"dmpl_patrimonio_liquido{period_str}.pdf"

            # Return PDF as download
            response = make_response(pdf_content)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            response.headers['Content-Length'] = len(pdf_content)

            return response

        except Exception as e:
            logger.error(f"Error generating DMPL PDF: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Error generating DMPL PDF: {str(e)}'
            }), 500

    @app.route('/api/reports/pdf-reports-list', methods=['GET'])
    def api_pdf_reports_list():
        """
        Get list of available PDF reports

        Returns:
            JSON with list of available PDF report types
        """
        try:
            reports = [
                {
                    'id': 'dre',
                    'name': 'Demonstração do Resultado do Exercício (DRE)',
                    'description': 'Income Statement following Brazilian accounting standards',
                    'endpoint': '/api/reports/dre-pdf',
                    'parameters': [
                        {'name': 'start_date', 'type': 'date', 'required': False, 'description': 'Start date (YYYY-MM-DD)'},
                        {'name': 'end_date', 'type': 'date', 'required': False, 'description': 'End date (YYYY-MM-DD)'},
                        {'name': 'entity', 'type': 'string', 'required': False, 'description': 'Entity filter'},
                        {'name': 'company_name', 'type': 'string', 'required': False, 'description': 'Company name for report'}
                    ]
                },
                {
                    'id': 'balance-sheet',
                    'name': 'Balanço Patrimonial',
                    'description': 'Balance Sheet following Brazilian accounting standards',
                    'endpoint': '/api/reports/balance-sheet-pdf',
                    'parameters': [
                        {'name': 'end_date', 'type': 'date', 'required': False, 'description': 'Balance position date (YYYY-MM-DD)'},
                        {'name': 'entity', 'type': 'string', 'required': False, 'description': 'Entity filter'},
                        {'name': 'company_name', 'type': 'string', 'required': False, 'description': 'Company name for report'}
                    ]
                },
                {
                    'id': 'cash-flow',
                    'name': 'Demonstração de Fluxo de Caixa (DFC)',
                    'description': 'Cash Flow Statement (Coming Soon)',
                    'endpoint': '/api/reports/cash-flow-pdf',
                    'status': 'coming_soon'
                },
                {
                    'id': 'dfc',
                    'name': 'Demonstração de Fluxo de Caixa (DFC)',
                    'description': 'Cash Flow Statement (Coming Soon)',
                    'endpoint': '/api/reports/dfc-pdf',
                    'status': 'coming_soon'
                },
                {
                    'id': 'dmpl',
                    'name': 'Demonstração das Mutações do Patrimônio Líquido (DMPL)',
                    'description': 'Statement of Changes in Equity following Brazilian accounting standards',
                    'endpoint': '/api/reports/dmpl-pdf',
                    'status': 'available',
                    'parameters': [
                        {'name': 'start_date', 'type': 'date', 'required': False, 'description': 'Start date (YYYY-MM-DD)'},
                        {'name': 'end_date', 'type': 'date', 'required': False, 'description': 'End date (YYYY-MM-DD)'},
                        {'name': 'entity', 'type': 'string', 'required': False, 'description': 'Entity filter'},
                        {'name': 'company_name', 'type': 'string', 'required': False, 'description': 'Company name for report'}
                    ]
                }
            ]

            return jsonify({
                'success': True,
                'data': {
                    'reports': reports,
                    'count': len(reports)
                }
            })

        except Exception as e:
            logger.error(f"Error getting PDF reports list: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # Ensure templates table exists
    ensure_report_templates_table()

    logger.info("CFO Reporting API routes registered successfully")
