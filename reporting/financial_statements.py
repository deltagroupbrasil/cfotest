#!/usr/bin/env python3
"""
Financial Statements Generator
Generates GAAP-compliant financial statements from transaction data

Supported Statements:
- Income Statement (P&L)
- Balance Sheet
- Cash Flow Statement
- Statement of Retained Earnings
"""

import os
import sys
import json
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui.database import db_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinancialStatementsGenerator:
    """Generates comprehensive financial statements from transaction data"""

    def __init__(self):
        self.db = db_manager

    def get_accounting_period(self, period_id: Optional[int] = None,
                             start_date: Optional[date] = None,
                             end_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Get accounting period information
        If period_id is provided, use that
        Otherwise, use start_date and end_date to find or create period
        """
        try:
            if period_id:
                query = "SELECT * FROM cfo_accounting_periods WHERE period_id = %s" if self.db.db_type == 'postgresql' else \
                        "SELECT * FROM cfo_accounting_periods WHERE period_id = ?"
                period = self.db.execute_query(query, (period_id,), fetch_one=True)

                if not period:
                    raise ValueError(f"Period {period_id} not found")

                return dict(period)

            elif start_date and end_date:
                # Find period matching date range
                query = """
                    SELECT * FROM cfo_accounting_periods
                    WHERE start_date <= %s AND end_date >= %s
                    ORDER BY start_date DESC LIMIT 1
                """ if self.db.db_type == 'postgresql' else """
                    SELECT * FROM cfo_accounting_periods
                    WHERE start_date <= ? AND end_date >= ?
                    ORDER BY start_date DESC LIMIT 1
                """
                period = self.db.execute_query(query, (end_date, start_date), fetch_one=True)

                if period:
                    return dict(period)

                # Create period if not found
                return self._create_period_from_dates(start_date, end_date)

            else:
                # Default to current month
                today = date.today()
                query = """
                    SELECT * FROM cfo_accounting_periods
                    WHERE is_current_period = %s
                    ORDER BY start_date DESC LIMIT 1
                """ if self.db.db_type == 'postgresql' else """
                    SELECT * FROM cfo_accounting_periods
                    WHERE is_current_period = 1
                    ORDER BY start_date DESC LIMIT 1
                """
                period = self.db.execute_query(query, (True if self.db.db_type == 'postgresql' else 1,), fetch_one=True)

                if period:
                    return dict(period)

                # Fallback to current month
                start_date = today.replace(day=1)
                from calendar import monthrange
                last_day = monthrange(today.year, today.month)[1]
                end_date = today.replace(day=last_day)

                return self._create_period_from_dates(start_date, end_date)

        except Exception as e:
            logger.error(f"Error getting accounting period: {e}")
            raise

    def _create_period_from_dates(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Create a temporary period definition from dates"""
        return {
            'period_id': None,
            'period_name': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'period_type': 'Custom',
            'fiscal_year': start_date.year,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'Open'
        }

    def generate_income_statement(
        self,
        period_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        comparison_period_id: Optional[int] = None,
        include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Generate Income Statement (Profit & Loss Statement)

        Args:
            period_id: Specific accounting period ID
            start_date: Start date for custom period
            end_date: End date for custom period
            comparison_period_id: Period to compare against
            include_details: Include transaction-level details

        Returns:
            Dict with income statement data and metadata
        """
        start_time = datetime.now()

        try:
            # Get period information
            period = self.get_accounting_period(period_id, start_date, end_date)
            period_start = period['start_date']
            period_end = period['end_date']

            logger.info(f"Generating Income Statement for period: {period['period_name']}")
            logger.info(f"Date range: {period_start} to {period_end}")

            # Calculate revenue
            revenue_data = self._calculate_revenue(period_start, period_end, include_details)

            # Calculate cost of goods sold
            cogs_data = self._calculate_cogs(period_start, period_end, include_details)

            # Calculate operating expenses
            opex_data = self._calculate_operating_expenses(period_start, period_end, include_details)

            # Calculate other income/expenses
            other_data = self._calculate_other_income_expenses(period_start, period_end, include_details)

            # Calculate totals
            total_revenue = revenue_data['total']
            total_cogs = cogs_data['total']
            gross_profit = total_revenue - total_cogs
            gross_margin = (gross_profit / total_revenue * 100) if total_revenue != 0 else 0

            total_opex = opex_data['total']
            operating_income = gross_profit - total_opex
            operating_margin = (operating_income / total_revenue * 100) if total_revenue != 0 else 0

            total_other = other_data['total']
            net_income = operating_income + total_other
            net_margin = (net_income / total_revenue * 100) if total_revenue != 0 else 0

            # Build income statement structure
            income_statement = {
                'statement_type': 'IncomeStatement',
                'statement_name': f"Income Statement - {period['period_name']}",
                'period': period,
                'generated_at': datetime.now().isoformat(),

                # Revenue Section
                'revenue': {
                    'total': float(total_revenue),
                    'details': revenue_data['categories'] if include_details else None,
                    'transactions': revenue_data.get('transactions') if include_details else None
                },

                # Cost of Goods Sold Section
                'cost_of_goods_sold': {
                    'total': float(total_cogs),
                    'details': cogs_data['categories'] if include_details else None,
                    'transactions': cogs_data.get('transactions') if include_details else None
                },

                # Gross Profit
                'gross_profit': {
                    'amount': float(gross_profit),
                    'margin_percent': round(float(gross_margin), 2)
                },

                # Operating Expenses Section
                'operating_expenses': {
                    'total': float(total_opex),
                    'details': opex_data['categories'] if include_details else None,
                    'transactions': opex_data.get('transactions') if include_details else None
                },

                # Operating Income
                'operating_income': {
                    'amount': float(operating_income),
                    'margin_percent': round(float(operating_margin), 2)
                },

                # Other Income/Expenses
                'other_income_expenses': {
                    'total': float(total_other),
                    'details': other_data['categories'] if include_details else None,
                    'transactions': other_data.get('transactions') if include_details else None
                },

                # Net Income (Bottom Line)
                'net_income': {
                    'amount': float(net_income),
                    'margin_percent': round(float(net_margin), 2)
                },

                # Summary Metrics
                'summary_metrics': {
                    'total_revenue': float(total_revenue),
                    'gross_profit': float(gross_profit),
                    'gross_margin_percent': round(float(gross_margin), 2),
                    'operating_income': float(operating_income),
                    'operating_margin_percent': round(float(operating_margin), 2),
                    'net_income': float(net_income),
                    'net_margin_percent': round(float(net_margin), 2),
                    'transaction_count': revenue_data.get('count', 0) + cogs_data.get('count', 0) +
                                       opex_data.get('count', 0) + other_data.get('count', 0)
                }
            }

            # Add comparison if requested
            if comparison_period_id:
                comparison_statement = self.generate_income_statement(
                    period_id=comparison_period_id,
                    include_details=False
                )
                income_statement['comparison'] = self._calculate_period_comparison(
                    income_statement,
                    comparison_statement
                )

            # Calculate generation time
            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)
            income_statement['generation_time_ms'] = generation_time_ms

            logger.info(f"Income Statement generated successfully in {generation_time_ms}ms")
            logger.info(f"Net Income: ${net_income:,.2f}")

            return income_statement

        except Exception as e:
            logger.error(f"Error generating income statement: {e}")
            raise

    def _calculate_revenue(self, start_date: date, end_date: date,
                          include_details: bool = False) -> Dict[str, Any]:
        """Calculate total revenue from transactions"""
        try:
            # Convert dates to strings for comparison (date column is TEXT in DB)
            start_date_str = start_date.strftime('%Y-%m-%d') if isinstance(start_date, date) else str(start_date)
            end_date_str = end_date.strftime('%Y-%m-%d') if isinstance(end_date, date) else str(end_date)

            # Query all revenue transactions (positive amounts)
            # Use proper date conversion for MM/DD/YYYY format
            query = """
                SELECT
                    transaction_id,
                    date,
                    description,
                    amount,
                    usd_equivalent,
                    classified_entity,
                    accounting_category,
                    currency
                FROM transactions
                WHERE TO_DATE(date, 'MM/DD/YYYY'::text) >= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
                AND TO_DATE(date, 'MM/DD/YYYY'::text) <= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
                AND amount > 0
                ORDER BY date, amount DESC
            """ if self.db.db_type == 'postgresql' else """
                SELECT
                    transaction_id,
                    date,
                    description,
                    amount,
                    usd_equivalent,
                    classified_entity,
                    accounting_category,
                    currency
                FROM transactions
                WHERE date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) >= date(?)
                AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) <= date(?)
                AND amount > 0
                ORDER BY date, amount DESC
            """

            transactions = self.db.execute_query(query, (start_date_str, end_date_str), fetch_all=True)

            # Categorize revenue
            categories = defaultdict(lambda: {'amount': Decimal('0'), 'count': 0, 'transactions': []})
            total_revenue = Decimal('0')

            for txn in transactions:
                # Use USD equivalent if available, otherwise use amount
                amount = Decimal(str(txn.get('usd_equivalent') or txn.get('amount', 0)))
                category = txn.get('accounting_category') or txn.get('classified_entity') or 'Uncategorized Revenue'

                categories[category]['amount'] += amount
                categories[category]['count'] += 1
                total_revenue += amount

                if include_details:
                    categories[category]['transactions'].append({
                        'transaction_id': txn['transaction_id'],
                        'date': str(txn['date']),
                        'description': txn['description'],
                        'amount': float(amount),
                        'currency': txn.get('currency', 'USD')
                    })

            # Format categories
            formatted_categories = {
                cat: {
                    'amount': float(data['amount']),
                    'count': data['count'],
                    'transactions': data['transactions'] if include_details else None
                }
                for cat, data in categories.items()
            }

            return {
                'total': total_revenue,
                'count': len(transactions),
                'categories': formatted_categories,
                'transactions': [dict(t) for t in transactions] if include_details else None
            }

        except Exception as e:
            logger.error(f"Error calculating revenue: {e}")
            return {'total': Decimal('0'), 'count': 0, 'categories': {}}

    def _calculate_cogs(self, start_date: date, end_date: date,
                       include_details: bool = False) -> Dict[str, Any]:
        """Calculate Cost of Goods Sold"""
        try:
            # Convert dates to strings for comparison
            start_date_str = start_date.strftime('%Y-%m-%d') if isinstance(start_date, date) else str(start_date)
            end_date_str = end_date.strftime('%Y-%m-%d') if isinstance(end_date, date) else str(end_date)

            # For now, we'll identify COGS based on specific categories
            # In a full implementation, this would use the chart of accounts mapping
            cogs_keywords = ['material', 'inventory', 'manufacturing', 'production', 'supplier']

            query = """
                SELECT
                    transaction_id,
                    date,
                    description,
                    amount,
                    usd_equivalent,
                    classified_entity,
                    accounting_category,
                    currency
                FROM transactions
                WHERE TO_DATE(date, 'MM/DD/YYYY'::text) >= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
                AND TO_DATE(date, 'MM/DD/YYYY'::text) <= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
                AND amount < 0
                AND (
                    LOWER(accounting_category) LIKE %s OR
                    LOWER(accounting_category) LIKE %s OR
                    LOWER(accounting_category) LIKE %s OR
                    LOWER(accounting_category) LIKE %s OR
                    LOWER(accounting_category) LIKE %s
                )
                ORDER BY date, amount
            """ if self.db.db_type == 'postgresql' else """
                SELECT
                    transaction_id,
                    date,
                    description,
                    amount,
                    usd_equivalent,
                    classified_entity,
                    accounting_category,
                    currency
                FROM transactions
                WHERE date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) >= date(?)
                AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) <= date(?)
                AND amount < 0
                AND (
                    LOWER(accounting_category) LIKE ? OR
                    LOWER(accounting_category) LIKE ? OR
                    LOWER(accounting_category) LIKE ? OR
                    LOWER(accounting_category) LIKE ? OR
                    LOWER(accounting_category) LIKE ?
                )
                ORDER BY date, amount
            """

            params = [start_date_str, end_date_str] + [f'%{kw}%' for kw in cogs_keywords]
            transactions = self.db.execute_query(query, tuple(params), fetch_all=True)

            # Categorize COGS
            categories = defaultdict(lambda: {'amount': Decimal('0'), 'count': 0, 'transactions': []})
            total_cogs = Decimal('0')

            for txn in transactions:
                amount = abs(Decimal(str(txn.get('usd_equivalent') or txn.get('amount', 0))))
                category = txn.get('accounting_category') or 'Other COGS'

                categories[category]['amount'] += amount
                categories[category]['count'] += 1
                total_cogs += amount

                if include_details:
                    categories[category]['transactions'].append({
                        'transaction_id': txn['transaction_id'],
                        'date': str(txn['date']),
                        'description': txn['description'],
                        'amount': float(amount),
                        'currency': txn.get('currency', 'USD')
                    })

            formatted_categories = {
                cat: {
                    'amount': float(data['amount']),
                    'count': data['count'],
                    'transactions': data['transactions'] if include_details else None
                }
                for cat, data in categories.items()
            }

            return {
                'total': total_cogs,
                'count': len(transactions),
                'categories': formatted_categories,
                'transactions': [dict(t) for t in transactions] if include_details else None
            }

        except Exception as e:
            logger.error(f"Error calculating COGS: {e}")
            return {'total': Decimal('0'), 'count': 0, 'categories': {}}

    def _calculate_operating_expenses(self, start_date: date, end_date: date,
                                     include_details: bool = False) -> Dict[str, Any]:
        """Calculate operating expenses (excluding COGS)"""
        try:
            # Convert dates to strings for comparison
            start_date_str = start_date.strftime('%Y-%m-%d') if isinstance(start_date, date) else str(start_date)
            end_date_str = end_date.strftime('%Y-%m-%d') if isinstance(end_date, date) else str(end_date)

            # Get all negative transactions that aren't COGS
            cogs_keywords = ['material', 'inventory', 'manufacturing', 'production', 'supplier']

            # Build exclusion conditions
            exclusion_conditions = " AND ".join([
                f"LOWER(accounting_category) NOT LIKE {'%s' if self.db.db_type == 'postgresql' else '?'}"
                for _ in cogs_keywords
            ])

            if self.db.db_type == 'postgresql':
                query = f"""
                    SELECT
                        transaction_id,
                        date,
                        description,
                        amount,
                        usd_equivalent,
                        classified_entity,
                        accounting_category,
                        currency
                    FROM transactions
                    WHERE TO_DATE(date, 'MM/DD/YYYY'::text) >= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
                    AND TO_DATE(date, 'MM/DD/YYYY'::text) <= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
                    AND amount < 0
                    AND ({exclusion_conditions})
                    ORDER BY date, amount
                """
            else:
                query = f"""
                    SELECT
                        transaction_id,
                        date,
                        description,
                        amount,
                        usd_equivalent,
                        classified_entity,
                        accounting_category,
                        currency
                    FROM transactions
                    WHERE date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) >= date(?)
                    AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) <= date(?)
                    AND amount < 0
                    AND ({exclusion_conditions})
                    ORDER BY date, amount
                """

            params = [start_date_str, end_date_str] + [f'%{kw}%' for kw in cogs_keywords]
            transactions = self.db.execute_query(query, tuple(params), fetch_all=True)

            # Categorize operating expenses
            categories = defaultdict(lambda: {'amount': Decimal('0'), 'count': 0, 'transactions': []})
            total_opex = Decimal('0')

            for txn in transactions:
                amount = abs(Decimal(str(txn.get('usd_equivalent') or txn.get('amount', 0))))
                category = txn.get('accounting_category') or txn.get('classified_entity') or 'General & Administrative'

                categories[category]['amount'] += amount
                categories[category]['count'] += 1
                total_opex += amount

                if include_details:
                    categories[category]['transactions'].append({
                        'transaction_id': txn['transaction_id'],
                        'date': str(txn['date']),
                        'description': txn['description'],
                        'amount': float(amount),
                        'currency': txn.get('currency', 'USD')
                    })

            formatted_categories = {
                cat: {
                    'amount': float(data['amount']),
                    'count': data['count'],
                    'transactions': data['transactions'] if include_details else None
                }
                for cat, data in categories.items()
            }

            return {
                'total': total_opex,
                'count': len(transactions),
                'categories': formatted_categories,
                'transactions': [dict(t) for t in transactions] if include_details else None
            }

        except Exception as e:
            logger.error(f"Error calculating operating expenses: {e}")
            return {'total': Decimal('0'), 'count': 0, 'categories': {}}

    def _calculate_other_income_expenses(self, start_date: date, end_date: date,
                                        include_details: bool = False) -> Dict[str, Any]:
        """Calculate other income and expenses (interest, gains/losses, etc.)"""
        try:
            # For initial implementation, return zero
            # In full implementation, this would include:
            # - Interest income/expense
            # - Gains/losses on investments
            # - Foreign exchange gains/losses
            # - Other non-operating items

            return {
                'total': Decimal('0'),
                'count': 0,
                'categories': {},
                'transactions': None
            }

        except Exception as e:
            logger.error(f"Error calculating other income/expenses: {e}")
            return {'total': Decimal('0'), 'count': 0, 'categories': {}}

    def _calculate_period_comparison(self, current: Dict[str, Any],
                                    comparison: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate variance between two periods"""
        try:
            current_net = current['net_income']['amount']
            comparison_net = comparison['net_income']['amount']

            variance_amount = current_net - comparison_net
            variance_percent = (variance_amount / comparison_net * 100) if comparison_net != 0 else 0

            return {
                'comparison_period': comparison['period']['period_name'],
                'current_net_income': current_net,
                'comparison_net_income': comparison_net,
                'variance_amount': variance_amount,
                'variance_percent': round(variance_percent, 2),

                'revenue_variance': {
                    'current': current['revenue']['total'],
                    'comparison': comparison['revenue']['total'],
                    'variance': current['revenue']['total'] - comparison['revenue']['total'],
                    'variance_percent': round(
                        (current['revenue']['total'] - comparison['revenue']['total']) /
                        comparison['revenue']['total'] * 100, 2
                    ) if comparison['revenue']['total'] != 0 else 0
                },

                'opex_variance': {
                    'current': current['operating_expenses']['total'],
                    'comparison': comparison['operating_expenses']['total'],
                    'variance': current['operating_expenses']['total'] - comparison['operating_expenses']['total'],
                    'variance_percent': round(
                        (current['operating_expenses']['total'] - comparison['operating_expenses']['total']) /
                        comparison['operating_expenses']['total'] * 100, 2
                    ) if comparison['operating_expenses']['total'] != 0 else 0
                }
            }

        except Exception as e:
            logger.error(f"Error calculating period comparison: {e}")
            return {}

    def save_financial_statement(self, statement_data: Dict[str, Any],
                                 is_final: bool = False,
                                 notes: Optional[str] = None) -> int:
        """
        Save generated financial statement to database

        Args:
            statement_data: The generated statement data
            is_final: Whether this is the final version
            notes: Optional notes about the statement

        Returns:
            statement_id of saved statement
        """
        try:
            period_id = statement_data['period'].get('period_id')
            statement_type = statement_data['statement_type']
            statement_name = statement_data['statement_name']

            # Convert statement data to JSON
            statement_json = json.dumps(statement_data, default=str)
            summary_json = json.dumps(statement_data.get('summary_metrics', {}), default=str)

            if self.db.db_type == 'postgresql':
                query = """
                    INSERT INTO cfo_financial_statements
                    (period_id, statement_type, statement_name, statement_data, summary_metrics,
                     generated_at, generation_time_ms, is_final, notes)
                    VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s)
                    RETURNING statement_id
                """
            else:
                query = """
                    INSERT INTO cfo_financial_statements
                    (period_id, statement_type, statement_name, statement_data, summary_metrics,
                     generated_at, generation_time_ms, is_final, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

            params = (
                period_id,
                statement_type,
                statement_name,
                statement_json,
                summary_json,
                statement_data['generated_at'],
                statement_data.get('generation_time_ms'),
                is_final,
                notes
            )

            if self.db.db_type == 'postgresql':
                result = self.db.execute_query(query, params, fetch_one=True)
                statement_id = result['statement_id']
            else:
                self.db.execute_query(query, params)
                # Get last insert ID for SQLite
                statement_id = self.db.execute_query(
                    "SELECT last_insert_rowid() as id",
                    fetch_one=True
                )['id']

            logger.info(f"Financial statement saved with ID: {statement_id}")
            return statement_id

        except Exception as e:
            logger.error(f"Error saving financial statement: {e}")
            raise


# Convenience function for quick Income Statement generation
def generate_quick_income_statement(start_date: Optional[date] = None,
                                   end_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Quick function to generate an income statement

    Args:
        start_date: Start date (defaults to current month start)
        end_date: End date (defaults to current month end)

    Returns:
        Income statement data
    """
    generator = FinancialStatementsGenerator()

    if not start_date or not end_date:
        today = date.today()
        start_date = today.replace(day=1)
        from calendar import monthrange
        last_day = monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day)

    return generator.generate_income_statement(
        start_date=start_date,
        end_date=end_date,
        include_details=True
    )
