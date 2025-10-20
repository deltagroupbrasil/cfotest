#!/usr/bin/env python3
"""
Cash Dashboard Generator
Provides real-time cash position tracking and trend analysis for CFO decision making

Features:
- Current cash position across all entities
- 7-day and 30-day cash trends
- Entity-specific cash analysis
- Cash flow velocity and burn rate calculations
"""

import os
import sys
import logging
import decimal
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, OrderedDict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui.database import db_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CashDashboard:
    """Generates comprehensive cash position analytics for executive decision making"""

    def __init__(self):
        self.db = db_manager

    def get_current_cash_position(self, entity: Optional[str] = None,
                                 as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Get current cash position (cumulative sum of all transactions)

        Args:
            entity: Specific entity to analyze (Delta LLC, Prop Shop, etc.)
            as_of_date: Calculate position as of specific date (defaults to today)

        Returns:
            Dict with current cash position and breakdown
        """
        start_time = datetime.now()

        try:
            if not as_of_date:
                as_of_date = date.today()

            as_of_date_str = as_of_date.strftime('%Y-%m-%d')

            logger.info(f"Calculating cash position as of {as_of_date_str}")
            if entity:
                logger.info(f"Filtering for entity: {entity}")

            # Build query based on entity filter
            entity_filter = ""
            params = [as_of_date_str]

            if entity:
                if self.db.db_type == 'postgresql':
                    entity_filter = "AND classified_entity = %s"
                else:
                    entity_filter = "AND classified_entity = ?"
                params.append(entity)

            # Query all transactions up to the specified date with NaN filtering
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
                        currency,
                        origin,
                        destination
                    FROM transactions
                    WHERE date <= %s
                    AND amount::text != 'NaN' AND amount IS NOT NULL
                    {entity_filter}
                    ORDER BY date, amount DESC
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
                        currency,
                        origin,
                        destination
                    FROM transactions
                    WHERE date <= ?
                    AND amount IS NOT NULL
                    {entity_filter}
                    ORDER BY date, amount DESC
                """

            transactions = self.db.execute_query(query, tuple(params), fetch_all=True)

            # Calculate cash position
            total_cash = Decimal('0')
            cash_by_entity = defaultdict(lambda: Decimal('0'))
            cash_by_currency = defaultdict(lambda: Decimal('0'))
            inflows = Decimal('0')
            outflows = Decimal('0')
            transaction_count = len(transactions)

            for txn in transactions:
                # Safe decimal conversion with validation
                try:
                    usd_equiv = txn.get('usd_equivalent')
                    amount_raw = txn.get('amount', 0)

                    # Use USD equivalent if available and valid, otherwise use amount
                    if usd_equiv is not None and str(usd_equiv).strip() != '':
                        amount = Decimal(str(usd_equiv))
                    elif amount_raw is not None and str(amount_raw).strip() != '':
                        amount = Decimal(str(amount_raw))
                    else:
                        amount = Decimal('0')

                except (ValueError, decimal.InvalidOperation):
                    logger.warning(f"Invalid amount in transaction {txn.get('transaction_id', 'unknown')}: {txn.get('amount')} / {txn.get('usd_equivalent')}")
                    amount = Decimal('0')

                entity_name = txn.get('classified_entity', 'Unknown Entity')
                currency = txn.get('currency', 'USD')

                total_cash += amount
                cash_by_entity[entity_name] += amount

                # Track original currency amounts for crypto tracking
                if currency != 'USD' and txn.get('amount'):
                    try:
                        raw_amount = str(txn.get('amount', 0))
                        # Skip NaN values for crypto currencies
                        if raw_amount.strip() != '' and raw_amount != 'NaN':
                            cash_by_currency[currency] += Decimal(raw_amount)
                    except (ValueError, decimal.InvalidOperation):
                        pass  # Skip invalid amounts
                else:
                    cash_by_currency['USD'] += amount

                # Track inflows and outflows
                if amount > 0:
                    inflows += amount
                else:
                    outflows += abs(amount)

            # Calculate generation time
            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Format response
            cash_position = {
                'as_of_date': as_of_date_str,
                'entity_filter': entity,
                'total_cash_usd': float(total_cash),
                'total_inflows': float(inflows),
                'total_outflows': float(outflows),
                'net_position': float(total_cash),
                'transaction_count': transaction_count,

                'cash_by_entity': {
                    entity: float(amount)
                    for entity, amount in sorted(cash_by_entity.items(),
                                               key=lambda x: x[1], reverse=True)
                },

                'cash_by_currency': {
                    currency: float(amount)
                    for currency, amount in cash_by_currency.items()
                    if amount != 0
                },

                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': generation_time_ms
            }

            logger.info(f"Cash position calculated: ${total_cash:,.2f} USD ({transaction_count} transactions)")
            return cash_position

        except Exception as e:
            logger.error(f"Error calculating cash position: {e}")
            raise

    def get_cash_trend(self, days: int = 30, entity: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cash position trend over specified number of days - OPTIMIZED VERSION

        Args:
            days: Number of days to analyze (7, 30, 90, etc.)
            entity: Specific entity to analyze

        Returns:
            Dict with daily cash positions and trend analysis
        """
        start_time = datetime.now()

        try:
            today = date.today()
            start_date = today - timedelta(days=days-1)  # Include today

            logger.info(f"Calculating {days}-day cash trend for period: {start_date} to {today}")
            if entity:
                logger.info(f"Filtering for entity: {entity}")

            # OPTIMIZATION: Get ALL transactions once and process efficiently
            entity_filter = ""
            params = []

            if entity:
                if self.db.db_type == 'postgresql':
                    entity_filter = "AND classified_entity = %s"
                else:
                    entity_filter = "AND classified_entity = ?"
                params.append(entity)

            # Get all transactions ordered by date
            if self.db.db_type == 'postgresql':
                query = f"""
                    SELECT
                        date,
                        amount,
                        usd_equivalent,
                        classified_entity,
                        currency
                    FROM transactions
                    WHERE amount::text != 'NaN' AND amount IS NOT NULL
                    {entity_filter}
                    ORDER BY date
                """
            else:
                query = f"""
                    SELECT
                        date,
                        amount,
                        usd_equivalent,
                        classified_entity,
                        currency
                    FROM transactions
                    WHERE amount IS NOT NULL
                    {entity_filter}
                    ORDER BY date
                """

            all_transactions = self.db.execute_query(query, tuple(params), fetch_all=True)

            # Calculate running cash position for each day
            daily_positions = OrderedDict()
            daily_changes = []

            # Pre-populate all dates with zero positions
            for i in range(days):
                current_date = start_date + timedelta(days=i)
                date_str = current_date.strftime('%Y-%m-%d')
                daily_positions[date_str] = {
                    'date': date_str,
                    'cash_position': 0.0,
                    'transaction_count': 0,
                    'daily_change': 0.0
                }

            # Process transactions efficiently
            running_total = Decimal('0')
            transaction_count = 0

            for txn in all_transactions:
                try:
                    # Safe decimal conversion
                    usd_equiv = txn.get('usd_equivalent')
                    amount_raw = txn.get('amount', 0)

                    if usd_equiv is not None and str(usd_equiv).strip() != '':
                        amount = Decimal(str(usd_equiv))
                    elif amount_raw is not None and str(amount_raw).strip() != '':
                        amount = Decimal(str(amount_raw))
                    else:
                        amount = Decimal('0')

                except (ValueError, decimal.InvalidOperation):
                    amount = Decimal('0')

                running_total += amount
                transaction_count += 1

                txn_date_str = str(txn['date'])

                # Update all days from this transaction date forward
                for date_str in daily_positions.keys():
                    if date_str >= txn_date_str:
                        daily_positions[date_str]['cash_position'] = float(running_total)
                        daily_positions[date_str]['transaction_count'] = transaction_count

            # Calculate daily changes efficiently
            prev_position = None
            for date_str, data in daily_positions.items():
                if prev_position is not None:
                    daily_change = data['cash_position'] - prev_position
                    data['daily_change'] = daily_change
                    daily_changes.append(daily_change)
                prev_position = data['cash_position']

            # Calculate trend metrics
            current_position = list(daily_positions.values())[-1]['cash_position']
            starting_position = list(daily_positions.values())[0]['cash_position']
            total_change = current_position - starting_position
            total_change_percent = (total_change / starting_position * 100) if starting_position != 0 else 0

            avg_daily_change = sum(daily_changes) / len(daily_changes) if daily_changes else 0

            # Calculate burn rate (negative average for cash burn)
            burn_rate_daily = -avg_daily_change if avg_daily_change < 0 else 0
            burn_rate_monthly = burn_rate_daily * 30

            # Calculate runway (days until cash runs out at current burn rate)
            runway_days = None
            if burn_rate_daily > 0 and current_position > 0:
                runway_days = int(current_position / burn_rate_daily)

            # Calculate generation time
            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            trend_analysis = {
                'period': {
                    'days': days,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': today.strftime('%Y-%m-%d')
                },
                'entity_filter': entity,

                'current_metrics': {
                    'current_cash_position': current_position,
                    'starting_cash_position': starting_position,
                    'total_change': total_change,
                    'total_change_percent': round(total_change_percent, 2),
                    'avg_daily_change': round(avg_daily_change, 2)
                },

                'burn_rate_analysis': {
                    'daily_burn_rate': round(burn_rate_daily, 2),
                    'monthly_burn_rate': round(burn_rate_monthly, 2),
                    'runway_days': runway_days,
                    'is_burning_cash': burn_rate_daily > 0
                },

                'daily_positions': list(daily_positions.values()),

                'trend_direction': 'increasing' if avg_daily_change > 0 else 'decreasing' if avg_daily_change < 0 else 'stable',

                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': generation_time_ms
            }

            logger.info(f"Cash trend calculated: {days} days, ${total_change:,.2f} change ({total_change_percent:.1f}%)")
            return trend_analysis

        except Exception as e:
            logger.error(f"Error calculating cash trend: {e}")
            raise

    def get_cash_flow_velocity(self, days: int = 30, entity: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate cash flow velocity metrics (how fast money moves in/out)

        Args:
            days: Number of days to analyze
            entity: Specific entity to analyze

        Returns:
            Dict with velocity metrics and flow analysis
        """
        start_time = datetime.now()

        try:
            today = date.today()
            start_date = today - timedelta(days=days-1)

            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')

            logger.info(f"Calculating cash flow velocity for period: {start_date_str} to {end_date_str}")

            # Build entity filter
            entity_filter = ""
            params = [start_date_str, end_date_str]

            if entity:
                if self.db.db_type == 'postgresql':
                    entity_filter = "AND classified_entity = %s"
                else:
                    entity_filter = "AND classified_entity = ?"
                params.append(entity)

            # Query transactions in the period
            if self.db.db_type == 'postgresql':
                query = f"""
                    SELECT
                        date,
                        amount,
                        usd_equivalent,
                        classified_entity,
                        accounting_category,
                        description
                    FROM transactions
                    WHERE date >= %s AND date <= %s
                    {entity_filter}
                    ORDER BY date
                """
            else:
                query = f"""
                    SELECT
                        date,
                        amount,
                        usd_equivalent,
                        classified_entity,
                        accounting_category,
                        description
                    FROM transactions
                    WHERE date >= ? AND date <= ?
                    {entity_filter}
                    ORDER BY date
                """

            transactions = self.db.execute_query(query, tuple(params), fetch_all=True)

            # Analyze cash flows
            total_inflows = Decimal('0')
            total_outflows = Decimal('0')
            daily_flows = defaultdict(lambda: {'inflows': Decimal('0'), 'outflows': Decimal('0')})
            category_flows = defaultdict(lambda: {'inflows': Decimal('0'), 'outflows': Decimal('0')})

            for txn in transactions:
                # Safe decimal conversion with validation
                try:
                    usd_equiv = txn.get('usd_equivalent')
                    amount_raw = txn.get('amount', 0)

                    # Use USD equivalent if available and valid, otherwise use amount
                    if usd_equiv is not None and str(usd_equiv).strip() != '':
                        amount = Decimal(str(usd_equiv))
                    elif amount_raw is not None and str(amount_raw).strip() != '':
                        amount = Decimal(str(amount_raw))
                    else:
                        amount = Decimal('0')

                except (ValueError, decimal.InvalidOperation):
                    logger.warning(f"Invalid amount in velocity calculation: {txn.get('amount')} / {txn.get('usd_equivalent')}")
                    amount = Decimal('0')

                txn_date = txn['date']
                category = txn.get('accounting_category', 'Uncategorized')

                if amount > 0:
                    total_inflows += amount
                    daily_flows[txn_date]['inflows'] += amount
                    category_flows[category]['inflows'] += amount
                else:
                    outflow_amount = abs(amount)
                    total_outflows += outflow_amount
                    daily_flows[txn_date]['outflows'] += outflow_amount
                    category_flows[category]['outflows'] += outflow_amount

            # Calculate velocity metrics
            net_flow = total_inflows - total_outflows
            avg_daily_inflows = total_inflows / days if days > 0 else 0
            avg_daily_outflows = total_outflows / days if days > 0 else 0
            avg_daily_net = net_flow / days if days > 0 else 0

            # Calculate flow volatility (standard deviation of daily flows)
            daily_nets = [flows['inflows'] - flows['outflows'] for flows in daily_flows.values()]
            avg_net = sum(daily_nets) / len(daily_nets) if daily_nets else 0
            variance = sum((float(net) - float(avg_net)) ** 2 for net in daily_nets) / len(daily_nets) if daily_nets else 0
            volatility = variance ** 0.5

            # Top flow categories
            top_inflow_categories = sorted(
                [(cat, float(flows['inflows'])) for cat, flows in category_flows.items()
                 if flows['inflows'] > 0],
                key=lambda x: x[1], reverse=True
            )[:5]

            top_outflow_categories = sorted(
                [(cat, float(flows['outflows'])) for cat, flows in category_flows.items()
                 if flows['outflows'] > 0],
                key=lambda x: x[1], reverse=True
            )[:5]

            # Calculate generation time
            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            velocity_analysis = {
                'period': {
                    'days': days,
                    'start_date': start_date_str,
                    'end_date': end_date_str
                },
                'entity_filter': entity,

                'flow_totals': {
                    'total_inflows': float(total_inflows),
                    'total_outflows': float(total_outflows),
                    'net_flow': float(net_flow),
                    'transaction_count': len(transactions)
                },

                'velocity_metrics': {
                    'avg_daily_inflows': float(avg_daily_inflows),
                    'avg_daily_outflows': float(avg_daily_outflows),
                    'avg_daily_net_flow': float(avg_daily_net),
                    'flow_volatility': round(volatility, 2),
                    'turnover_ratio': float(total_inflows + total_outflows) / 2 if days > 0 else 0
                },

                'top_categories': {
                    'top_inflow_sources': top_inflow_categories,
                    'top_outflow_destinations': top_outflow_categories
                },

                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': generation_time_ms
            }

            logger.info(f"Cash flow velocity calculated: {len(transactions)} transactions, ${net_flow:,.2f} net flow")
            return velocity_analysis

        except Exception as e:
            logger.error(f"Error calculating cash flow velocity: {e}")
            raise

    def get_entity_cash_comparison(self, days: int = 30) -> Dict[str, Any]:
        """
        Compare cash positions across all Delta entities - OPTIMIZED VERSION

        Args:
            days: Number of days for trend analysis

        Returns:
            Dict with multi-entity cash comparison
        """
        start_time = datetime.now()

        try:
            logger.info(f"Calculating entity cash comparison for {days} days")

            # OPTIMIZATION: Get all data in a single query and process efficiently
            query = """
                SELECT
                    classified_entity,
                    date,
                    amount,
                    usd_equivalent
                FROM transactions
                WHERE classified_entity IS NOT NULL
                    AND classified_entity != ''
                    AND amount::text != 'NaN' AND amount IS NOT NULL
                ORDER BY classified_entity, date
            """

            all_transactions = self.db.execute_query(query, fetch_all=True)

            # Process all entities efficiently
            entity_data = defaultdict(list)
            entities = set()

            for txn in all_transactions:
                entity = txn.get('classified_entity')
                if entity:
                    entities.add(entity)
                    entity_data[entity].append(txn)

            # Calculate analysis for each entity efficiently
            entity_analysis = {}
            today = date.today()
            trend_start_date = today - timedelta(days=days-1)

            for entity in entities:
                transactions = entity_data[entity]

                # Calculate current position (all transactions)
                total_cash = Decimal('0')
                transaction_count = len(transactions)

                for txn in transactions:
                    try:
                        usd_equiv = txn.get('usd_equivalent')
                        amount_raw = txn.get('amount', 0)

                        if usd_equiv is not None and str(usd_equiv).strip() != '':
                            amount = Decimal(str(usd_equiv))
                        elif amount_raw is not None and str(amount_raw).strip() != '':
                            amount = Decimal(str(amount_raw))
                        else:
                            amount = Decimal('0')
                    except (ValueError, decimal.InvalidOperation):
                        amount = Decimal('0')

                    total_cash += amount

                # Calculate trend for this entity (transactions in the trend period)
                trend_transactions = [
                    txn for txn in transactions
                    if str(txn.get('date', '')) >= trend_start_date.strftime('%Y-%m-%d')
                ]

                # Calculate starting position (as of trend start date)
                starting_cash = Decimal('0')
                for txn in transactions:
                    if str(txn.get('date', '')) <= trend_start_date.strftime('%Y-%m-%d'):
                        try:
                            usd_equiv = txn.get('usd_equivalent')
                            amount_raw = txn.get('amount', 0)

                            if usd_equiv is not None and str(usd_equiv).strip() != '':
                                amount = Decimal(str(usd_equiv))
                            elif amount_raw is not None and str(amount_raw).strip() != '':
                                amount = Decimal(str(amount_raw))
                            else:
                                amount = Decimal('0')
                        except (ValueError, decimal.InvalidOperation):
                            amount = Decimal('0')

                        starting_cash += amount

                # Calculate trend metrics
                current_position = float(total_cash)
                starting_position = float(starting_cash)
                total_change = current_position - starting_position
                total_change_percent = (total_change / starting_position * 100) if starting_position != 0 else 0
                avg_daily_change = total_change / days if days > 0 else 0

                # Burn rate analysis
                burn_rate_daily = -avg_daily_change if avg_daily_change < 0 else 0
                runway_days = None
                if burn_rate_daily > 0 and current_position > 0:
                    runway_days = int(current_position / burn_rate_daily)

                entity_analysis[entity] = {
                    'current_cash_position': current_position,
                    'transaction_count': transaction_count,
                    'trend_change': total_change,
                    'trend_change_percent': round(total_change_percent, 2),
                    'avg_daily_change': round(avg_daily_change, 2),
                    'burn_rate_daily': round(burn_rate_daily, 2),
                    'runway_days': runway_days,
                    'trend_direction': 'increasing' if avg_daily_change > 0 else 'decreasing' if avg_daily_change < 0 else 'stable'
                }

            # Calculate overall totals
            total_cash = sum(data['current_cash_position'] for data in entity_analysis.values())
            total_transactions = sum(data['transaction_count'] for data in entity_analysis.values())

            # Rank entities by cash position
            ranked_entities = sorted(
                entity_analysis.items(),
                key=lambda x: x[1]['current_cash_position'],
                reverse=True
            )

            # Calculate generation time
            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            comparison = {
                'analysis_period': {
                    'days': days,
                    'end_date': date.today().strftime('%Y-%m-%d')
                },

                'overall_summary': {
                    'total_cash_all_entities': total_cash,
                    'total_transactions': total_transactions,
                    'entity_count': len(entities),
                    'largest_entity': ranked_entities[0][0] if ranked_entities else None,
                    'largest_entity_cash': ranked_entities[0][1]['current_cash_position'] if ranked_entities else 0
                },

                'entity_details': dict(entity_analysis),
                'entity_ranking': ranked_entities,

                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': generation_time_ms
            }

            logger.info(f"Entity comparison calculated: {len(entities)} entities, ${total_cash:,.2f} total cash")
            return comparison

        except Exception as e:
            logger.error(f"Error calculating entity cash comparison: {e}")
            raise


# Convenience functions for quick access
def get_quick_cash_position(entity: Optional[str] = None) -> Dict[str, Any]:
    """Quick function to get current cash position"""
    dashboard = CashDashboard()
    return dashboard.get_current_cash_position(entity=entity)


def get_quick_cash_trend(days: int = 7, entity: Optional[str] = None) -> Dict[str, Any]:
    """Quick function to get cash trend"""
    dashboard = CashDashboard()
    return dashboard.get_cash_trend(days=days, entity=entity)


def get_quick_entity_comparison() -> Dict[str, Any]:
    """Quick function to get entity comparison"""
    dashboard = CashDashboard()
    return dashboard.get_entity_cash_comparison(days=30)


if __name__ == '__main__':
    """Test the Cash Dashboard"""
    dashboard = CashDashboard()

    print("=== CASH DASHBOARD TEST ===")

    # Test current position
    print("\n1. Current Cash Position:")
    position = dashboard.get_current_cash_position()
    print(f"   Total Cash: ${position['total_cash_usd']:,.2f}")
    print(f"   Transactions: {position['transaction_count']}")

    # Test 7-day trend
    print("\n2. 7-Day Cash Trend:")
    trend = dashboard.get_cash_trend(days=7)
    print(f"   7-Day Change: ${trend['current_metrics']['total_change']:,.2f}")
    print(f"   Daily Avg: ${trend['current_metrics']['avg_daily_change']:,.2f}")

    # Test entity comparison
    print("\n3. Entity Comparison:")
    comparison = dashboard.get_entity_cash_comparison(days=30)
    print(f"   Total Entities: {comparison['overall_summary']['entity_count']}")
    print(f"   Combined Cash: ${comparison['overall_summary']['total_cash_all_entities']:,.2f}")

    print("\n=== TEST COMPLETE ===")