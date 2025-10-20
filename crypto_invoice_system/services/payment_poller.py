#!/usr/bin/env python3
"""
Payment Polling Service
Continuously polls MEXC API every 30 seconds to detect crypto payments
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mexc_service import MEXCService, MEXCAPIError
from models.database_postgresql import CryptoInvoiceDatabaseManager, InvoiceStatus, PaymentStatus
from services.amount_based_matcher import AmountBasedPaymentMatcher


class PaymentPoller:
    """
    Automated payment detection service
    Polls MEXC API at regular intervals to detect incoming payments
    """

    def __init__(self, mexc_service: MEXCService, db_manager: CryptoInvoiceDatabaseManager,
                 poll_interval: int = 30, payment_callback: Callable = None,
                 amount_matcher: AmountBasedPaymentMatcher = None):
        """
        Initialize payment poller

        Args:
            mexc_service: MEXC API service instance
            db_manager: CryptoInvoiceDatabaseManager instance for PostgreSQL
            poll_interval: Polling interval in seconds (default 30)
            payment_callback: Optional callback function when payment detected
            amount_matcher: Amount-based matcher for shared addresses
        """
        self.mexc = mexc_service
        self.db = db_manager
        self.poll_interval = poll_interval
        self.payment_callback = payment_callback
        self.amount_matcher = amount_matcher or AmountBasedPaymentMatcher(tolerance_percent=0.1)

        self.is_running = False
        self.polling_thread = None

        # Setup logging
        self.logger = logging.getLogger("PaymentPoller")
        self.logger.setLevel(logging.INFO)

        # Statistics
        self.stats = {
            "total_polls": 0,
            "payments_detected": 0,
            "payments_confirmed": 0,
            "errors": 0,
            "last_poll_time": None
        }

    def start(self):
        """Start the polling service in a background thread"""
        if self.is_running:
            self.logger.warning("Polling service already running")
            return

        self.is_running = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        self.logger.info(f"Payment polling service started (interval: {self.poll_interval}s)")

    def stop(self):
        """Stop the polling service"""
        if not self.is_running:
            return

        self.is_running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=5)
        self.logger.info("Payment polling service stopped")

    def _polling_loop(self):
        """Main polling loop - runs in background thread"""
        while self.is_running:
            try:
                self._poll_pending_invoices()
                self.stats["total_polls"] += 1
                self.stats["last_poll_time"] = datetime.now()
            except Exception as e:
                self.logger.error(f"Error in polling loop: {e}")
                self.stats["errors"] += 1

            # Wait for next poll interval
            time.sleep(self.poll_interval)

    def _poll_pending_invoices(self):
        """Poll all pending invoices for payment detection"""
        # Get all unpaid invoices
        pending_invoices = self.db.get_pending_invoices()

        if not pending_invoices:
            self.logger.debug("No pending invoices to poll")
            return

        self.logger.info(f"Polling {len(pending_invoices)} pending invoices")

        for invoice in pending_invoices:
            try:
                self._check_invoice_payment(invoice)
            except Exception as e:
                self.logger.error(f"Error checking invoice {invoice['invoice_number']}: {e}")
                self.db.log_polling_event(
                    invoice_id=invoice['id'],
                    status='error',
                    error_message=str(e)
                )

    def _check_invoice_payment(self, invoice: Dict):
        """
        Check if payment has been received for a specific invoice
        Uses amount-based matching since we share deposit addresses

        Args:
            invoice: Invoice dictionary from database
        """
        invoice_id = invoice['id']
        invoice_number = invoice['invoice_number']
        expected_amount = invoice['crypto_amount']
        currency = invoice['crypto_currency']
        network = invoice['crypto_network']

        self.logger.debug(f"Checking invoice {invoice_number} for {expected_amount} {currency}/{network}")

        try:
            # Get all recent deposits for this currency
            issue_date = datetime.fromisoformat(invoice['issue_date'])
            start_time = max(issue_date, datetime.now() - timedelta(days=7))
            start_timestamp = int(start_time.timestamp() * 1000)

            deposits = self.mexc.get_deposit_history(
                currency=currency,
                start_time=start_timestamp,
                status=None  # Check all statuses
            )

            # Get existing payments to avoid duplicates
            existing_payments = self.db.get_payments_for_invoice(invoice_id)

            # Filter deposits for matching network and unprocessed
            for deposit in deposits:
                if deposit.get('network') != network:
                    continue

                deposit_amount = float(deposit.get('amount', 0))
                tx_hash = deposit.get('txId')

                # Skip if already processed
                if self.amount_matcher.detect_duplicate_payment(
                    deposit_amount, currency, network, tx_hash, existing_payments
                ):
                    continue

                # Check if amount matches this invoice
                min_amount = expected_amount * (1 - 0.001)  # 0.1% tolerance
                max_amount = expected_amount * (1 + 0.001)

                if min_amount <= deposit_amount <= max_amount:
                    # Found matching deposit!
                    deposit_info = {
                        'transaction_hash': tx_hash,
                        'amount': deposit_amount,
                        'currency': deposit.get('coin'),
                        'network': deposit.get('network'),
                        'confirmations': deposit.get('confirmations', 0),
                        'status': deposit.get('status'),
                        'timestamp': deposit.get('insertTime'),
                        'raw_data': deposit
                    }

                    deposit = deposit_info  # Reformat for compatibility
                    break
            else:
                deposit = None

            if deposit:
                self.logger.info(f"💰 Payment detected for invoice {invoice_number}!")
                self._handle_payment_detected(invoice, deposit)
                self.stats["payments_detected"] += 1

                # Log successful detection
                self.db.log_polling_event(
                    invoice_id=invoice_id,
                    status='payment_detected',
                    deposits_found=1,
                    api_response=str(deposit)
                )
            else:
                # No payment found yet
                self.db.log_polling_event(
                    invoice_id=invoice_id,
                    status='no_payment',
                    deposits_found=0
                )

        except MEXCAPIError as e:
            self.logger.error(f"MEXC API error for invoice {invoice_number}: {e}")
            self.db.log_polling_event(
                invoice_id=invoice_id,
                status='api_error',
                error_message=str(e)
            )

    def _handle_payment_detected(self, invoice: Dict, deposit: Dict):
        """
        Handle detected payment

        Args:
            invoice: Invoice record
            deposit: Deposit information from MEXC
        """
        invoice_id = invoice['id']
        invoice_number = invoice['invoice_number']

        # Check if payment already recorded
        existing_payments = self.db.get_payments_for_invoice(invoice_id)
        for payment in existing_payments:
            if payment['transaction_hash'] == deposit['transaction_hash']:
                self.logger.info(f"Payment already recorded for invoice {invoice_number}")
                return

        # Record payment transaction
        payment_data = {
            "invoice_id": invoice_id,
            "transaction_hash": deposit['transaction_hash'],
            "amount_received": deposit['amount'],
            "currency": deposit['currency'],
            "network": deposit['network'],
            "deposit_address": invoice['deposit_address'],
            "status": self._determine_payment_status(deposit),
            "confirmations": deposit.get('confirmations', 0),
            "required_confirmations": MEXCService.get_required_confirmations(
                deposit['currency'], deposit['network']
            ),
            "mexc_transaction_id": deposit.get('transaction_hash'),
            "raw_api_response": deposit.get('raw_data')
        }

        payment_id = self.db.create_payment_transaction(payment_data)
        self.logger.info(f"Payment transaction recorded (ID: {payment_id})")

        # Check if payment is confirmed
        if deposit.get('confirmations', 0) >= payment_data['required_confirmations']:
            self._confirm_payment(invoice, payment_id, deposit)
        else:
            # Update invoice status to partially paid
            self.db.update_invoice_status(invoice_id, InvoiceStatus.PARTIALLY_PAID.value)
            self.logger.info(f"Invoice {invoice_number} marked as partially paid (awaiting confirmations)")

        # Call payment callback if provided
        if self.payment_callback:
            try:
                self.payment_callback({
                    "event": "payment_detected",
                    "invoice": invoice,
                    "payment": deposit
                })
            except Exception as e:
                self.logger.error(f"Error in payment callback: {e}")

    def _determine_payment_status(self, deposit: Dict) -> str:
        """
        Determine payment status based on deposit info

        Args:
            deposit: Deposit information

        Returns:
            Payment status string
        """
        confirmations = deposit.get('confirmations', 0)
        required = MEXCService.get_required_confirmations(
            deposit['currency'], deposit['network']
        )

        if confirmations >= required:
            return PaymentStatus.CONFIRMED.value
        elif confirmations > 0:
            return PaymentStatus.DETECTED.value
        else:
            return PaymentStatus.PENDING.value

    def _confirm_payment(self, invoice: Dict, payment_id: int, deposit: Dict):
        """
        Confirm payment and mark invoice as paid

        Args:
            invoice: Invoice record
            payment_id: Payment transaction ID
            deposit: Deposit information
        """
        invoice_id = invoice['id']
        invoice_number = invoice['invoice_number']

        # Update payment status
        self.db.update_payment_confirmations(
            payment_id=payment_id,
            confirmations=deposit.get('confirmations', 0),
            status=PaymentStatus.CONFIRMED.value
        )

        # Mark invoice as paid
        self.db.update_invoice_status(
            invoice_id=invoice_id,
            status=InvoiceStatus.PAID.value,
            paid_at=datetime.now()
        )

        self.stats["payments_confirmed"] += 1

        self.logger.info(f"✅ Invoice {invoice_number} confirmed as PAID!")

        # Call payment callback for confirmation
        if self.payment_callback:
            try:
                self.payment_callback({
                    "event": "payment_confirmed",
                    "invoice": invoice,
                    "payment": deposit
                })
            except Exception as e:
                self.logger.error(f"Error in payment callback: {e}")

    def check_confirmations_update(self):
        """
        Check all detected payments for confirmation updates
        This should be called periodically to update confirmation counts
        """
        # Get all detected but unconfirmed payments
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.*, i.invoice_number, i.crypto_currency, i.deposit_address
            FROM payment_transactions p
            JOIN invoices i ON p.invoice_id = i.id
            WHERE p.status = 'detected'
            AND p.confirmations < p.required_confirmations
        """)

        unconfirmed_payments = [dict(row) for row in cursor.fetchall()]
        conn.close()

        self.logger.info(f"Checking confirmation updates for {len(unconfirmed_payments)} payments")

        for payment in unconfirmed_payments:
            try:
                # Query MEXC for updated confirmation count
                tx_info = self.mexc.verify_transaction_manually(
                    txid=payment['transaction_hash'],
                    currency=payment['currency']
                )

                if tx_info:
                    new_confirmations = tx_info.get('confirmations', 0)

                    if new_confirmations > payment['confirmations']:
                        self.logger.info(
                            f"Confirmation update for {payment['invoice_number']}: "
                            f"{new_confirmations}/{payment['required_confirmations']}"
                        )

                        # Update confirmation count
                        if new_confirmations >= payment['required_confirmations']:
                            # Payment now confirmed!
                            invoice = self.db.get_invoice(payment['invoice_id'])
                            self._confirm_payment(invoice, payment['id'], tx_info)
                        else:
                            self.db.update_payment_confirmations(
                                payment_id=payment['id'],
                                confirmations=new_confirmations
                            )

            except Exception as e:
                self.logger.error(f"Error checking confirmations for payment {payment['id']}: {e}")

    def manual_payment_verification(self, invoice_id: int, txid: str,
                                   verified_by: str) -> Dict[str, Any]:
        """
        Manually verify a payment by transaction ID

        Args:
            invoice_id: Invoice ID
            txid: Transaction ID/hash
            verified_by: Username of person verifying

        Returns:
            Verification result dictionary
        """
        invoice = self.db.get_invoice(invoice_id)
        if not invoice:
            return {"success": False, "error": "Invoice not found"}

        try:
            # Verify transaction with MEXC
            tx_info = self.mexc.verify_transaction_manually(
                txid=txid,
                currency=invoice['crypto_currency']
            )

            if not tx_info:
                return {"success": False, "error": "Transaction not found on MEXC"}

            # Check if amount matches
            expected_amount = invoice['crypto_amount']
            tolerance = invoice.get('payment_tolerance', 0.005)
            received_amount = tx_info['amount']

            min_amount = expected_amount * (1 - tolerance)
            max_amount = expected_amount * (1 + tolerance)

            if not (min_amount <= received_amount <= max_amount):
                return {
                    "success": False,
                    "error": f"Amount mismatch: expected {expected_amount}, received {received_amount}"
                }

            # Check if address matches
            if tx_info.get('address') != invoice['deposit_address']:
                return {
                    "success": False,
                    "error": "Deposit address mismatch"
                }

            # Record payment as manually verified
            payment_data = {
                "invoice_id": invoice_id,
                "transaction_hash": txid,
                "amount_received": received_amount,
                "currency": tx_info['currency'],
                "network": tx_info['network'],
                "deposit_address": tx_info['address'],
                "status": PaymentStatus.CONFIRMED.value,
                "confirmations": tx_info.get('confirmations', 999),
                "required_confirmations": 1,  # Manual verification bypasses confirmation requirement
                "is_manual_verification": True,
                "verified_by": verified_by,
                "mexc_transaction_id": txid,
                "raw_api_response": tx_info.get('raw_data')
            }

            payment_id = self.db.create_payment_transaction(payment_data)

            # Mark invoice as paid
            self.db.update_invoice_status(
                invoice_id=invoice_id,
                status=InvoiceStatus.PAID.value,
                paid_at=datetime.now()
            )

            self.logger.info(f"✅ Manual verification successful for invoice {invoice['invoice_number']}")

            return {
                "success": True,
                "payment_id": payment_id,
                "message": "Payment manually verified and invoice marked as paid"
            }

        except Exception as e:
            self.logger.error(f"Manual verification failed: {e}")
            return {"success": False, "error": str(e)}

    def get_statistics(self) -> Dict[str, Any]:
        """Get polling service statistics"""
        return {
            **self.stats,
            "is_running": self.is_running,
            "poll_interval": self.poll_interval,
            "uptime": (datetime.now() - self.stats.get("start_time", datetime.now())).total_seconds()
            if self.stats.get("start_time") else 0
        }

    def check_overdue_invoices(self):
        """Check for overdue invoices and update their status"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Get configuration for overdue threshold
        overdue_days = int(self.db.get_config('invoice_overdue_days') or 7)

        # Find invoices that are past due date and not paid
        cursor.execute("""
            UPDATE invoices
            SET status = 'overdue', updated_at = CURRENT_TIMESTAMP
            WHERE status IN ('sent', 'partially_paid')
            AND date(due_date) < date('now', ? || ' days')
        """, (f"-{overdue_days}",))

        updated_count = cursor.rowcount
        conn.commit()
        conn.close()

        if updated_count > 0:
            self.logger.warning(f"Marked {updated_count} invoices as overdue")

        return updated_count
