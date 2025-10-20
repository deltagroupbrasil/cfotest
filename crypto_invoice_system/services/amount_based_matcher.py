#!/usr/bin/env python3
"""
Amount-Based Payment Matcher
Matches deposits to invoices based on exact amount when unique addresses aren't available
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging


class AmountBasedPaymentMatcher:
    """
    Matches incoming deposits to pending invoices based on amount matching
    Used when exchange doesn't support unique deposit addresses per invoice
    """

    def __init__(self, tolerance_percent: float = 0.1):
        """
        Initialize matcher

        Args:
            tolerance_percent: Tolerance for amount matching (default 0.1% = very strict)
        """
        self.tolerance = tolerance_percent / 100
        self.logger = logging.getLogger("AmountMatcher")

    def find_matching_invoice(
        self,
        deposit_amount: float,
        currency: str,
        network: str,
        pending_invoices: List[Dict],
        deposit_timestamp: datetime = None
    ) -> Optional[Dict]:
        """
        Find invoice that matches the deposit amount

        Args:
            deposit_amount: Amount received
            currency: Currency (BTC, USDT, TAO)
            network: Network (BTC, TRC20, ERC20, etc.)
            pending_invoices: List of unpaid invoices
            deposit_timestamp: When deposit was received

        Returns:
            Matching invoice or None
        """
        if not deposit_timestamp:
            deposit_timestamp = datetime.now()

        # Filter invoices by currency and network
        matching_currency_invoices = [
            inv for inv in pending_invoices
            if inv['crypto_currency'] == currency and inv['crypto_network'] == network
        ]

        if not matching_currency_invoices:
            self.logger.debug(f"No pending invoices for {currency}/{network}")
            return None

        # Find exact or near-exact amount matches
        matches = []
        for invoice in matching_currency_invoices:
            expected_amount = float(invoice['crypto_amount'])
            min_amount = expected_amount * (1 - self.tolerance)
            max_amount = expected_amount * (1 + self.tolerance)

            if min_amount <= deposit_amount <= max_amount:
                # Calculate match quality
                amount_diff = abs(deposit_amount - expected_amount)
                match_quality = 1 - (amount_diff / expected_amount)

                # Prefer more recent invoices
                issue_date = datetime.fromisoformat(invoice['issue_date'])
                days_old = (deposit_timestamp - issue_date).days
                recency_score = max(0, 1 - (days_old / 30))  # Decay over 30 days

                # Combined score
                score = (match_quality * 0.7) + (recency_score * 0.3)

                matches.append({
                    'invoice': invoice,
                    'score': score,
                    'amount_diff': amount_diff,
                    'match_quality': match_quality
                })

        if not matches:
            self.logger.warning(
                f"No invoice matches for {deposit_amount} {currency}/{network}. "
                f"Pending invoices: {len(matching_currency_invoices)}"
            )
            return None

        # Return best match
        best_match = max(matches, key=lambda x: x['score'])

        self.logger.info(
            f"Found match for {deposit_amount} {currency}: "
            f"Invoice {best_match['invoice']['invoice_number']} "
            f"(diff: {best_match['amount_diff']:.8f}, quality: {best_match['match_quality']:.2%})"
        )

        return best_match['invoice']

    def detect_duplicate_payment(
        self,
        deposit_amount: float,
        currency: str,
        network: str,
        transaction_hash: str,
        existing_payments: List[Dict]
    ) -> bool:
        """
        Check if this deposit has already been recorded

        Args:
            deposit_amount: Deposit amount
            currency: Currency
            network: Network
            transaction_hash: Transaction ID
            existing_payments: List of existing payment records

        Returns:
            True if duplicate detected
        """
        for payment in existing_payments:
            # Check by transaction hash (most reliable)
            if payment.get('transaction_hash') == transaction_hash:
                self.logger.warning(f"Duplicate payment detected: {transaction_hash}")
                return True

            # Check by amount + currency + time (within 5 minutes)
            if (payment.get('currency') == currency and
                payment.get('network') == network and
                abs(float(payment.get('amount_received', 0)) - deposit_amount) < 0.00000001):

                payment_time = datetime.fromisoformat(payment.get('detected_at', '2000-01-01'))
                if (datetime.now() - payment_time).total_seconds() < 300:
                    self.logger.warning(f"Possible duplicate payment: {deposit_amount} {currency}")
                    return True

        return False

    def create_ambiguous_payment_alert(
        self,
        deposit_amount: float,
        currency: str,
        network: str,
        possible_invoices: List[Dict]
    ) -> Dict:
        """
        Create alert when deposit could match multiple invoices

        Args:
            deposit_amount: Deposit amount
            currency: Currency
            network: Network
            possible_invoices: List of possible matching invoices

        Returns:
            Alert data dictionary
        """
        return {
            'type': 'ambiguous_payment',
            'deposit_amount': deposit_amount,
            'currency': currency,
            'network': network,
            'possible_matches': [
                {
                    'invoice_number': inv['invoice_number'],
                    'expected_amount': inv['crypto_amount'],
                    'client_name': inv.get('client_name', 'Unknown'),
                    'issue_date': inv['issue_date']
                }
                for inv in possible_invoices
            ],
            'action_required': 'Manual review needed - multiple invoices with similar amounts',
            'timestamp': datetime.now().isoformat()
        }

    def calculate_unique_amount(
        self,
        base_amount: float,
        invoice_number: str,
        precision: int = 8
    ) -> float:
        """
        Calculate a slightly unique amount to help with matching
        Adds tiny fractional amount based on invoice number

        Args:
            base_amount: Base USD amount
            invoice_number: Invoice number (e.g., DPY-2025-10-0001)
            precision: Decimal precision

        Returns:
            Slightly modified amount
        """
        # Extract number from invoice (last 4 digits)
        import re
        match = re.search(r'(\d{4})$', invoice_number)
        if match:
            invoice_num = int(match.group(1))
            # Add tiny fractional amount (e.g., 0.00000123)
            fraction = invoice_num / 100000000  # 8 decimal places
            unique_amount = base_amount + fraction
            return round(unique_amount, precision)

        return base_amount
