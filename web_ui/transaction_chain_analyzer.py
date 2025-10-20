"""
Transaction Chain Analyzer
Advanced system for detecting and analyzing related transactions automatically
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
import sqlite3
import psycopg2
from .database import db_manager


class TransactionChainAnalyzer:
    """
    Inteligent system to detect transaction chains based on multiple patterns:
    1. Crypto transaction sequences (same asset, related amounts)
    2. Recurring vendor patterns (same vendor, temporal proximity)
    3. Entity relationship chains (related business entities)
    4. Amount correlation patterns (split transactions, refunds)
    5. Sequential invoice-transaction matches
    """

    def __init__(self):
        self.chain_patterns = {
            'crypto_sequence': self._detect_crypto_chains,
            'vendor_recurring': self._detect_vendor_chains,
            'entity_related': self._detect_entity_chains,
            'amount_correlation': self._detect_amount_chains,
            'invoice_sequence': self._detect_invoice_chains
        }

    def find_transaction_chains(self, transaction_id: str = None, limit: int = 50) -> Dict:
        """
        Main method to find all transaction chains for a specific transaction or system-wide

        Returns:
        {
            "transaction_id": "abc123",
            "chains": [
                {
                    "chain_type": "crypto_sequence",
                    "confidence": 0.92,
                    "related_transactions": [...],
                    "pattern_description": "USDT sequence with temporal proximity",
                    "chain_strength": "high",
                    "navigation_path": ["tx1", "tx2", "tx3"]
                }
            ],
            "total_chains": 3,
            "suggested_actions": ["Link crypto sequence", "Review entity patterns"]
        }
        """

        if transaction_id:
            return self._analyze_single_transaction_chains(transaction_id)
        else:
            return self._analyze_all_transaction_chains(limit)

    def _analyze_single_transaction_chains(self, transaction_id: str) -> Dict:
        """Analyze chains for a specific transaction"""

        # Get the base transaction
        base_transaction = self._get_transaction_by_id(transaction_id)
        if not base_transaction:
            return {"error": "Transaction not found", "transaction_id": transaction_id}

        chains = []

        # Run all pattern detectors
        for pattern_name, detector_func in self.chain_patterns.items():
            try:
                detected_chains = detector_func(base_transaction)
                chains.extend(detected_chains)
            except Exception as e:
                print(f"Error in {pattern_name}: {e}")
                continue

        # Sort chains by confidence
        chains.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        return {
            "transaction_id": transaction_id,
            "base_transaction": {
                "description": base_transaction.get('description', ''),
                "amount": base_transaction.get('amount', 0),
                "date": base_transaction.get('date', ''),
                "entity": base_transaction.get('classified_entity', '')
            },
            "chains": chains[:10],  # Top 10 chains
            "total_chains": len(chains),
            "suggested_actions": self._generate_suggestions(chains)
        }

    def _detect_crypto_chains(self, base_transaction: Dict) -> List[Dict]:
        """
        Detect cryptocurrency transaction chains

        Patterns:
        - Same cryptocurrency (USDT, BTC, ETH)
        - Similar amounts or incremental patterns
        - Temporal proximity (same day/week)
        - Same exchange or wallet patterns
        """
        chains = []
        description = base_transaction.get('description', '').upper()

        # Check if this is a crypto transaction
        crypto_patterns = [
            r'(TETHER|USDT)',
            r'(BITCOIN|BTC)',
            r'(ETHEREUM|ETH)',
            r'(\d+\.?\d*)\s+(USDT|BTC|ETH)',
            r'TRANSACTION.*(\d+\.?\d*)\s+(USDT|BTC|ETH)'
        ]

        crypto_match = None
        crypto_type = None
        crypto_amount = None

        for pattern in crypto_patterns:
            match = re.search(pattern, description)
            if match:
                crypto_match = match
                if len(match.groups()) >= 2:
                    crypto_amount = match.group(1) if match.group(1).replace('.', '').isdigit() else None
                    crypto_type = match.group(2) if len(match.groups()) >= 2 else match.group(1)
                else:
                    crypto_type = match.group(1)
                break

        if not crypto_match:
            return chains

        # Find similar crypto transactions
        base_date = datetime.strptime(base_transaction['date'], '%m/%d/%Y' if '/' in base_transaction['date'] else '%Y-%m-%d')
        date_range_start = base_date - timedelta(days=30)
        date_range_end = base_date + timedelta(days=30)

        # Query for similar crypto transactions
        similar_transactions = self._find_similar_crypto_transactions(
            crypto_type,
            crypto_amount,
            date_range_start,
            date_range_end,
            base_transaction['transaction_id']
        )

        if similar_transactions:
            confidence = self._calculate_crypto_chain_confidence(
                base_transaction, similar_transactions, crypto_type, crypto_amount
            )

            chain = {
                "chain_type": "crypto_sequence",
                "confidence": confidence,
                "crypto_type": crypto_type,
                "crypto_amount": crypto_amount,
                "related_transactions": similar_transactions,
                "pattern_description": f"{crypto_type} transaction sequence with {len(similar_transactions)} related transactions",
                "chain_strength": "high" if confidence > 0.8 else "medium" if confidence > 0.6 else "low",
                "navigation_path": [base_transaction['transaction_id']] + [tx['transaction_id'] for tx in similar_transactions],
                "timespan_days": (max([datetime.strptime(tx['date'], '%m/%d/%Y' if '/' in tx['date'] else '%Y-%m-%d') for tx in similar_transactions]) -
                                min([datetime.strptime(tx['date'], '%m/%d/%Y' if '/' in tx['date'] else '%Y-%m-%d') for tx in similar_transactions])).days,
                "total_crypto_volume": self._calculate_total_crypto_volume(similar_transactions, crypto_type)
            }
            chains.append(chain)

        return chains

    def _detect_vendor_chains(self, base_transaction: Dict) -> List[Dict]:
        """
        Detect recurring vendor transaction chains

        Patterns:
        - Same vendor (ANTHROPIC, GOOGLE, VERCEL)
        - Regular intervals (monthly, weekly)
        - Progressive amounts (subscriptions, usage-based)
        """
        chains = []
        description = base_transaction.get('description', '').upper()

        # Extract vendor name from description
        vendor_patterns = [
            r'^([A-Z\s]{3,20})',  # First words
            r'(ANTHROPIC|GOOGLE|VERCEL|MICROSOFT|AMAZON|APPLE)',  # Known vendors
            r'([A-Z]{3,15})\s',  # Capital word patterns
        ]

        vendor_name = None
        for pattern in vendor_patterns:
            match = re.search(pattern, description)
            if match:
                candidate = match.group(1).strip()
                if len(candidate) >= 3 and not candidate.isdigit():
                    vendor_name = candidate
                    break

        if not vendor_name:
            return chains

        # Find transactions with same vendor
        base_date = datetime.strptime(base_transaction['date'], '%m/%d/%Y' if '/' in base_transaction['date'] else '%Y-%m-%d')
        similar_transactions = self._find_vendor_transactions(
            vendor_name,
            base_date - timedelta(days=90),
            base_date + timedelta(days=90),
            base_transaction['transaction_id']
        )

        if len(similar_transactions) >= 2:  # At least 2 other transactions
            confidence = self._calculate_vendor_chain_confidence(
                base_transaction, similar_transactions, vendor_name
            )

            # Analyze intervals
            intervals = self._analyze_transaction_intervals(similar_transactions)

            chain = {
                "chain_type": "vendor_recurring",
                "confidence": confidence,
                "vendor_name": vendor_name,
                "related_transactions": similar_transactions,
                "pattern_description": f"Recurring {vendor_name} transactions with {intervals['pattern']} pattern",
                "chain_strength": "high" if confidence > 0.8 else "medium" if confidence > 0.6 else "low",
                "navigation_path": [base_transaction['transaction_id']] + [tx['transaction_id'] for tx in similar_transactions],
                "interval_pattern": intervals,
                "total_amount": sum([abs(float(tx['amount'])) for tx in similar_transactions]),
                "average_amount": sum([abs(float(tx['amount'])) for tx in similar_transactions]) / len(similar_transactions)
            }
            chains.append(chain)

        return chains

    def _detect_entity_chains(self, base_transaction: Dict) -> List[Dict]:
        """
        Detect entity relationship chains (Delta LLC, Delta Prop Shop LLC, etc.)
        """
        chains = []
        base_entity = base_transaction.get('classified_entity', '')

        if not base_entity or base_entity in ['NEEDS REVIEW', 'Unclassified']:
            return chains

        # Find related entities
        related_entities = self._find_related_entities(base_entity)

        if related_entities:
            base_date = datetime.strptime(base_transaction['date'], '%m/%d/%Y' if '/' in base_transaction['date'] else '%Y-%m-%d')
            entity_transactions = self._find_entity_transactions(
                related_entities,
                base_date - timedelta(days=60),
                base_date + timedelta(days=60),
                base_transaction['transaction_id']
            )

            if entity_transactions:
                confidence = min(0.9, 0.6 + (len(entity_transactions) * 0.05))

                chain = {
                    "chain_type": "entity_related",
                    "confidence": confidence,
                    "base_entity": base_entity,
                    "related_entities": related_entities,
                    "related_transactions": entity_transactions,
                    "pattern_description": f"Transactions across related Delta entities",
                    "chain_strength": "high" if confidence > 0.8 else "medium",
                    "navigation_path": [base_transaction['transaction_id']] + [tx['transaction_id'] for tx in entity_transactions]
                }
                chains.append(chain)

        return chains

    def _detect_amount_chains(self, base_transaction: Dict) -> List[Dict]:
        """
        Detect amount correlation patterns (splits, refunds, complementary amounts)
        """
        chains = []
        base_amount = abs(float(base_transaction.get('amount', 0)))

        if base_amount == 0:
            return chains

        # Define amount correlation ranges
        correlation_ranges = [
            (base_amount * 0.95, base_amount * 1.05, "exact_match"),  # +/- 5%
            (base_amount * 0.4, base_amount * 0.6, "half_amount"),    # ~50%
            (base_amount * 1.8, base_amount * 2.2, "double_amount"),  # ~200%
            (base_amount * 0.2, base_amount * 0.35, "split_partial")  # ~25%
        ]

        base_date = datetime.strptime(base_transaction['date'], '%m/%d/%Y' if '/' in base_transaction['date'] else '%Y-%m-%d')

        for min_amount, max_amount, pattern_type in correlation_ranges:
            correlated_transactions = self._find_amount_correlated_transactions(
                min_amount, max_amount,
                base_date - timedelta(days=14),
                base_date + timedelta(days=14),
                base_transaction['transaction_id']
            )

            if correlated_transactions:
                confidence = 0.7 if pattern_type == "exact_match" else 0.6

                chain = {
                    "chain_type": "amount_correlation",
                    "confidence": confidence,
                    "correlation_type": pattern_type,
                    "base_amount": base_amount,
                    "related_transactions": correlated_transactions,
                    "pattern_description": f"Amount correlation: {pattern_type.replace('_', ' ')}",
                    "chain_strength": "medium",
                    "navigation_path": [base_transaction['transaction_id']] + [tx['transaction_id'] for tx in correlated_transactions]
                }
                chains.append(chain)

        return chains

    def _detect_invoice_chains(self, base_transaction: Dict) -> List[Dict]:
        """
        Detect invoice sequence chains (transactions that follow invoice patterns)
        """
        chains = []

        # Check if transaction is already matched to an invoice
        invoice_matches = self._get_invoice_matches(base_transaction['transaction_id'])

        if invoice_matches:
            # Find related invoices from same vendor
            related_invoices = self._find_related_invoices(invoice_matches)

            if related_invoices:
                confidence = 0.85
                chain = {
                    "chain_type": "invoice_sequence",
                    "confidence": confidence,
                    "base_invoice": invoice_matches[0],
                    "related_transactions": related_invoices,
                    "pattern_description": f"Invoice sequence from {invoice_matches[0].get('vendor_name', 'vendor')}",
                    "chain_strength": "high",
                    "navigation_path": [base_transaction['transaction_id']] + [tx['transaction_id'] for tx in related_invoices]
                }
                chains.append(chain)

        return chains

    # Helper methods for database queries
    def _get_transaction_by_id(self, transaction_id: str) -> Optional[Dict]:
        """Get transaction by ID"""
        query = "SELECT * FROM transactions WHERE transaction_id = %s"
        result = db_manager.execute_query(query, (transaction_id,), fetch_one=True)
        return dict(result) if result else None

    def _find_similar_crypto_transactions(self, crypto_type: str, crypto_amount: Optional[str],
                                        start_date: datetime, end_date: datetime,
                                        exclude_id: str) -> List[Dict]:
        """Find similar cryptocurrency transactions"""
        query = """
            SELECT transaction_id, description, amount, date, classified_entity
            FROM transactions
            WHERE UPPER(description) LIKE %s
            AND transaction_id != %s
            AND STR_TO_DATE(date, '%%m/%%d/%%Y') BETWEEN %s AND %s
            ORDER BY date DESC
            LIMIT 10
        """

        pattern = f"%{crypto_type}%"
        results = db_manager.execute_query(
            query,
            (pattern, exclude_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')),
            fetch_all=True
        )

        return [dict(row) for row in results] if results else []

    def _find_vendor_transactions(self, vendor_name: str, start_date: datetime,
                                end_date: datetime, exclude_id: str) -> List[Dict]:
        """Find transactions from same vendor"""
        query = """
            SELECT transaction_id, description, amount, date, classified_entity
            FROM transactions
            WHERE UPPER(description) LIKE %s
            AND transaction_id != %s
            AND STR_TO_DATE(date, '%%m/%%d/%%Y') BETWEEN %s AND %s
            ORDER BY date DESC
            LIMIT 15
        """

        pattern = f"%{vendor_name}%"
        results = db_manager.execute_query(
            query,
            (pattern, exclude_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')),
            fetch_all=True
        )

        return [dict(row) for row in results] if results else []

    def _find_related_entities(self, base_entity: str) -> List[str]:
        """Find related business entities"""
        entity_families = {
            'Delta': ['Delta LLC', 'Delta Prop Shop LLC', 'Delta Mining Paraguay S.A.', 'Delta Mining'],
            'Infinity': ['Infinity Validator', 'Infinity Staking', 'Infinity Pool']
        }

        for family_name, entities in entity_families.items():
            if any(family_name.lower() in base_entity.lower() for family_name in [family_name]):
                return [e for e in entities if e != base_entity]

        return []

    def _find_entity_transactions(self, entities: List[str], start_date: datetime,
                                end_date: datetime, exclude_id: str) -> List[Dict]:
        """Find transactions from related entities"""
        if not entities:
            return []

        placeholders = ','.join(['%s'] * len(entities))
        query = f"""
            SELECT transaction_id, description, amount, date, classified_entity
            FROM transactions
            WHERE classified_entity IN ({placeholders})
            AND transaction_id != %s
            AND STR_TO_DATE(date, '%%m/%%d/%%Y') BETWEEN %s AND %s
            ORDER BY date DESC
            LIMIT 20
        """

        params = entities + [exclude_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
        results = db_manager.execute_query(query, params, fetch_all=True)

        return [dict(row) for row in results] if results else []

    def _find_amount_correlated_transactions(self, min_amount: float, max_amount: float,
                                           start_date: datetime, end_date: datetime,
                                           exclude_id: str) -> List[Dict]:
        """Find transactions with correlated amounts"""
        query = """
            SELECT transaction_id, description, amount, date, classified_entity
            FROM transactions
            WHERE ABS(CAST(amount AS DECIMAL(10,2))) BETWEEN %s AND %s
            AND transaction_id != %s
            AND STR_TO_DATE(date, '%%m/%%d/%%Y') BETWEEN %s AND %s
            ORDER BY date DESC
            LIMIT 8
        """

        results = db_manager.execute_query(
            query,
            (min_amount, max_amount, exclude_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')),
            fetch_all=True
        )

        return [dict(row) for row in results] if results else []

    def _get_invoice_matches(self, transaction_id: str) -> List[Dict]:
        """Get invoice matches for transaction"""
        query = """
            SELECT i.id, i.invoice_number, i.vendor_name, i.total_amount, pim.match_score
            FROM pending_invoice_matches pim
            JOIN invoices i ON pim.invoice_id = i.id
            WHERE pim.transaction_id = %s
        """

        results = db_manager.execute_query(query, (transaction_id,), fetch_all=True)
        return [dict(row) for row in results] if results else []

    def _find_related_invoices(self, invoice_matches: List[Dict]) -> List[Dict]:
        """Find related invoices from same vendor"""
        if not invoice_matches:
            return []

        vendor = invoice_matches[0].get('vendor_name')
        if not vendor:
            return []

        query = """
            SELECT t.transaction_id, t.description, t.amount, t.date, t.classified_entity
            FROM pending_invoice_matches pim
            JOIN transactions t ON pim.transaction_id = t.transaction_id
            JOIN invoices i ON pim.invoice_id = i.id
            WHERE i.vendor_name = %s
            AND pim.transaction_id != %s
            ORDER BY t.date DESC
            LIMIT 10
        """

        base_transaction_id = invoice_matches[0].get('transaction_id')
        results = db_manager.execute_query(query, (vendor, base_transaction_id), fetch_all=True)
        return [dict(row) for row in results] if results else []

    # Confidence calculation methods
    def _calculate_crypto_chain_confidence(self, base_transaction: Dict, similar_transactions: List[Dict],
                                         crypto_type: str, crypto_amount: Optional[str]) -> float:
        """Calculate confidence for crypto chains"""
        confidence = 0.5  # Base confidence

        # Number of similar transactions
        confidence += min(0.2, len(similar_transactions) * 0.05)

        # Crypto type match precision
        if crypto_type in ['USDT', 'BTC', 'ETH']:
            confidence += 0.15

        # Amount correlation if available
        if crypto_amount:
            confidence += 0.1

        # Entity consistency
        base_entity = base_transaction.get('classified_entity', '')
        if base_entity and base_entity != 'NEEDS REVIEW':
            consistent_entities = sum(1 for tx in similar_transactions
                                    if tx.get('classified_entity') == base_entity)
            if consistent_entities > 0:
                confidence += min(0.15, consistent_entities * 0.03)

        return min(1.0, confidence)

    def _calculate_vendor_chain_confidence(self, base_transaction: Dict, similar_transactions: List[Dict],
                                         vendor_name: str) -> float:
        """Calculate confidence for vendor chains"""
        confidence = 0.6  # Base confidence for vendor matching

        # Number of transactions
        confidence += min(0.2, len(similar_transactions) * 0.02)

        # Vendor name precision
        if len(vendor_name) >= 5:
            confidence += 0.1

        # Amount consistency (subscription-like)
        amounts = [abs(float(tx['amount'])) for tx in similar_transactions + [base_transaction]]
        if len(set(amounts)) <= 3:  # Similar amounts
            confidence += 0.15

        return min(1.0, confidence)

    def _analyze_transaction_intervals(self, transactions: List[Dict]) -> Dict:
        """Analyze time intervals between transactions"""
        if len(transactions) < 2:
            return {"pattern": "insufficient_data"}

        dates = []
        for tx in transactions:
            try:
                date_str = tx['date']
                date_obj = datetime.strptime(date_str, '%m/%d/%Y' if '/' in date_str else '%Y-%m-%d')
                dates.append(date_obj)
            except:
                continue

        if len(dates) < 2:
            return {"pattern": "invalid_dates"}

        dates.sort()
        intervals = []

        for i in range(1, len(dates)):
            interval = (dates[i] - dates[i-1]).days
            intervals.append(interval)

        avg_interval = sum(intervals) / len(intervals)

        if 25 <= avg_interval <= 35:
            pattern = "monthly"
        elif 6 <= avg_interval <= 8:
            pattern = "weekly"
        elif avg_interval <= 3:
            pattern = "frequent"
        else:
            pattern = "irregular"

        return {
            "pattern": pattern,
            "average_days": round(avg_interval, 1),
            "intervals": intervals,
            "regularity_score": 1.0 - (max(intervals) - min(intervals)) / (avg_interval + 1) if intervals else 0
        }

    def _calculate_total_crypto_volume(self, transactions: List[Dict], crypto_type: str) -> Optional[float]:
        """Calculate total crypto volume from transactions"""
        total = 0.0

        for tx in transactions:
            description = tx.get('description', '')
            # Try to extract crypto amount from description
            pattern = rf'(\d+\.?\d*)\s+{crypto_type}'
            match = re.search(pattern, description.upper())
            if match:
                try:
                    amount = float(match.group(1))
                    total += amount
                except:
                    continue

        return total if total > 0 else None

    def _generate_suggestions(self, chains: List[Dict]) -> List[str]:
        """Generate actionable suggestions based on detected chains"""
        suggestions = []

        chain_types = [chain['chain_type'] for chain in chains]
        high_confidence_chains = [chain for chain in chains if chain.get('confidence', 0) > 0.8]

        if 'crypto_sequence' in chain_types:
            suggestions.append("Link cryptocurrency transaction sequence for better traceability")

        if 'vendor_recurring' in chain_types:
            suggestions.append("Set up automatic categorization for recurring vendor transactions")

        if 'entity_related' in chain_types:
            suggestions.append("Review entity relationship mapping for consolidated reporting")

        if len(high_confidence_chains) > 2:
            suggestions.append("Multiple high-confidence chains detected - consider automated linking")

        if 'invoice_sequence' in chain_types:
            suggestions.append("Review invoice matching patterns for process optimization")

        return suggestions[:5]  # Limit to 5 suggestions

    def _analyze_all_transaction_chains(self, limit: int = 50) -> Dict:
        """Analyze chains across all transactions (system-wide analysis)"""

        # Get recent transactions for system analysis
        query = """
            SELECT transaction_id, description, amount, date, classified_entity
            FROM transactions
            ORDER BY STR_TO_DATE(date, '%m/%d/%Y') DESC
            LIMIT %s
        """

        transactions = db_manager.execute_query(query, (limit,), fetch_all=True)

        if not transactions:
            return {"error": "No transactions found"}

        system_chains = []
        pattern_summary = defaultdict(int)

        # Analyze each transaction for chains
        for transaction in transactions[:20]:  # Limit to 20 for performance
            transaction_dict = dict(transaction)
            chains = []

            for pattern_name, detector_func in self.chain_patterns.items():
                try:
                    detected_chains = detector_func(transaction_dict)
                    chains.extend(detected_chains)
                    pattern_summary[pattern_name] += len(detected_chains)
                except Exception as e:
                    continue

            if chains:
                # Get best chain for this transaction
                best_chain = max(chains, key=lambda x: x.get('confidence', 0))
                best_chain['source_transaction'] = transaction_dict['transaction_id']
                system_chains.append(best_chain)

        # Sort by confidence
        system_chains.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        return {
            "system_analysis": True,
            "total_transactions_analyzed": len(transactions),
            "chains_detected": len(system_chains),
            "pattern_distribution": dict(pattern_summary),
            "top_chains": system_chains[:15],  # Top 15 system chains
            "recommendations": self._generate_system_recommendations(system_chains, pattern_summary)
        }

    def _generate_system_recommendations(self, chains: List[Dict], pattern_summary: Dict) -> List[str]:
        """Generate system-wide recommendations"""
        recommendations = []

        total_chains = len(chains)
        high_confidence = len([c for c in chains if c.get('confidence', 0) > 0.8])

        if total_chains > 10:
            recommendations.append(f"High chain activity detected ({total_chains} chains) - consider automated linking")

        if pattern_summary.get('crypto_sequence', 0) > 3:
            recommendations.append("Multiple crypto sequences - implement crypto portfolio tracking")

        if pattern_summary.get('vendor_recurring', 0) > 5:
            recommendations.append("Many recurring vendors - set up subscription management")

        if high_confidence / max(total_chains, 1) > 0.7:
            recommendations.append("High confidence patterns - enable automatic chain suggestions")

        return recommendations


# API Integration Function
def create_chain_api_endpoint():
    """
    Creates the API endpoint for transaction chain analysis
    Add this to app_db.py in the routes section
    """

    endpoint_code = '''
@app.route('/api/transactions/<transaction_id>/chains', methods=['GET'])
def get_transaction_chains(transaction_id):
    """Get transaction chains for a specific transaction"""
    try:
        analyzer = TransactionChainAnalyzer()
        chains = analyzer.find_transaction_chains(transaction_id)
        return jsonify(chains)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/transaction-chains', methods=['GET'])
def get_system_transaction_chains():
    """Get system-wide transaction chain analysis"""
    try:
        limit = request.args.get('limit', 50, type=int)
        analyzer = TransactionChainAnalyzer()
        chains = analyzer.find_transaction_chains(limit=limit)
        return jsonify(chains)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''

    return endpoint_code
