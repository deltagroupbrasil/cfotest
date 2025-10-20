#!/usr/bin/env python3
"""
Revenue Recognition Sync System
================================

Synchronizes transaction classifications with revenue recognition matches.
Runs automatically on dashboard loads to keep categorization aligned with matched invoices.

Architecture:
- Checks for newly applied invoice matches
- Updates transaction classifications to Revenue
- Tracks changes for user notification
- Non-blocking background operation
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
from .database import db_manager

logger = logging.getLogger(__name__)

class RevenueRecognitionSync:
    """
    Syncs transaction classifications with revenue recognition matches
    """

    def __init__(self):
        self.changes_made = []

    def sync_revenue_classifications(self, session_id: str = None) -> Dict[str, Any]:
        """
        Main sync function - updates transactions based on invoice matches

        Returns:
            Dict with sync results:
            {
                'success': bool,
                'transactions_updated': int,
                'changes': List[Dict],
                'timestamp': str
            }
        """
        try:
            logger.info(f"🔄 Starting revenue recognition sync (session: {session_id})")

            # 1. Find transactions that are linked to invoices but not classified as Revenue
            mismatched_transactions = self._find_mismatched_revenue_transactions()

            if not mismatched_transactions:
                logger.info("✅ No transactions need revenue classification sync")
                return {
                    'success': True,
                    'transactions_updated': 0,
                    'changes': [],
                    'timestamp': datetime.now().isoformat()
                }

            logger.info(f"📊 Found {len(mismatched_transactions)} transactions to sync")

            # 2. Update each transaction's classification
            changes = []
            for txn in mismatched_transactions:
                try:
                    updated = self._update_transaction_to_revenue(txn)
                    if updated:
                        changes.append({
                            'transaction_id': txn['transaction_id'],
                            'date': txn['date'],
                            'amount': txn['amount'],
                            'description': txn['description'],
                            'previous_entity': txn['classified_entity'],
                            'new_entity': 'Revenue',
                            'invoice_id': txn['linked_invoice_id'],
                            'invoice_number': txn.get('invoice_number', 'N/A')
                        })
                except Exception as e:
                    logger.error(f"❌ Error updating transaction {txn['transaction_id']}: {e}")
                    continue

            logger.info(f"✅ Revenue sync complete: {len(changes)} transactions updated")

            return {
                'success': True,
                'transactions_updated': len(changes),
                'changes': changes,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Revenue sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'transactions_updated': 0,
                'changes': [],
                'timestamp': datetime.now().isoformat()
            }

    def _find_mismatched_revenue_transactions(self) -> List[Dict]:
        """
        Find transactions that are linked to invoices but not classified as Revenue
        """
        query = """
            SELECT
                t.transaction_id,
                t.date,
                t.amount,
                t.description,
                t.classified_entity,
                t.accounting_category,
                t.subcategory,
                i.id as linked_invoice_id,
                i.invoice_number,
                i.vendor_name
            FROM transactions t
            INNER JOIN invoices i ON t.transaction_id = i.linked_transaction_id
            WHERE i.linked_transaction_id IS NOT NULL
              AND i.linked_transaction_id != ''
              AND i.status = 'paid'
              AND (
                  t.accounting_category != 'REVENUE'
                  OR t.accounting_category IS NULL
              )
              AND t.archived = false
        """

        if db_manager.db_type == 'postgresql':
            query = query.replace('?', '%s')

        try:
            results = db_manager.execute_with_retry(query, fetch_all=True)
            return results if results else []
        except Exception as e:
            logger.error(f"❌ Error finding mismatched transactions: {e}")
            return []

    def _update_transaction_to_revenue(self, transaction: Dict) -> bool:
        """
        Update a single transaction to Revenue classification
        """
        transaction_id = transaction['transaction_id']
        invoice_vendor = transaction.get('vendor_name', 'Customer')

        update_query = """
            UPDATE transactions
            SET
                classified_entity = ?,
                accounting_category = 'REVENUE',
                subcategory = 'Customer Payment',
                classification_reason = ?,
                confidence = 1.0,
                updated_at = CURRENT_TIMESTAMP
            WHERE transaction_id = ?
        """

        if db_manager.db_type == 'postgresql':
            update_query = update_query.replace('?', '%s')

        classification_reason = f"Matched to invoice from {invoice_vendor} (Revenue Recognition System)"

        try:
            db_manager.execute_query(
                update_query,
                (invoice_vendor, classification_reason, transaction_id)
            )
            logger.info(f"✅ Updated transaction {transaction_id} to Revenue")
            return True
        except Exception as e:
            logger.error(f"❌ Error updating transaction {transaction_id}: {e}")
            return False

    def get_recent_sync_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get summary of recent revenue sync activity
        Useful for displaying to users what changed recently
        """
        query = """
            SELECT
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM transactions
            WHERE accounting_category = 'REVENUE'
              AND classification_reason LIKE '%Revenue Recognition System%'
              AND updated_at >= datetime('now', '-{} hours')
        """.format(hours)

        if db_manager.db_type == 'postgresql':
            query = query.replace("datetime('now', '-{} hours')".format(hours),
                                 f"NOW() - INTERVAL '{hours} hours'")

        try:
            result = db_manager.execute_with_retry(query, fetch_one=True)
            if result:
                return {
                    'transactions_synced': result[0] or 0,
                    'total_revenue_amount': float(result[1]) if result[1] else 0.0,
                    'period_hours': hours
                }
        except Exception as e:
            logger.error(f"❌ Error getting sync summary: {e}")

        return {
            'transactions_synced': 0,
            'total_revenue_amount': 0.0,
            'period_hours': hours
        }


# Convenience function for use in Flask routes
def sync_revenue_now(session_id: str = None) -> Dict[str, Any]:
    """
    Execute revenue sync and return results
    Can be called from Flask routes or background jobs
    """
    syncer = RevenueRecognitionSync()
    return syncer.sync_revenue_classifications(session_id)
