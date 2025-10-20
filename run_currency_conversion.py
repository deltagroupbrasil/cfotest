#!/usr/bin/env python3
"""
Execute currency conversion for all invoices
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'web_ui'))

from database import db_manager
from historical_currency_converter import HistoricalCurrencyConverter

def run_conversion():
    print("=== RUNNING CURRENCY CONVERSION ===")

    # Initialize converter
    converter = HistoricalCurrencyConverter(db_manager)

    # Run bulk conversion for all non-USD invoices
    print("Converting foreign currency invoices to USD...")
    results = converter.bulk_convert_invoices(limit=100)

    print(f"\n[OK] CONVERSION RESULTS:")
    print(f"   Total processed: {results['total_processed']}")
    print(f"   Successful: {results['successful_conversions']}")
    print(f"   Failed: {results['failed_conversions']}")

    if results['conversion_details']:
        print(f"\n[INFO] CONVERSION DETAILS:")
        for detail in results['conversion_details'][:10]:  # Show first 10
            if 'conversion' in detail:
                conv = detail['conversion']
                print(f"   Invoice {detail['invoice_id'][:8]}: {conv['original_currency']} {conv['original_amount']:,.2f} -> USD {conv.get('converted_amount', 0):,.2f}")
            elif 'error' in detail:
                print(f"   Invoice {detail['invoice_id'][:8]}: ERROR - {detail['error']}")

    # Get conversion statistics
    print(f"\n[STATS] CONVERSION STATISTICS:")
    stats = converter.get_conversion_stats()
    if stats:
        print(f"   Total invoices: {stats['total_invoices']}")
        print(f"   USD invoices: {stats['usd_invoices']}")
        print(f"   Foreign currency: {stats['foreign_currency_invoices']}")
        print(f"   Converted invoices: {stats['converted_invoices']}")
        print(f"   Unique currencies: {stats['unique_currencies']}")
        print(f"   Currencies found: {stats['currencies']}")

if __name__ == "__main__":
    run_conversion()