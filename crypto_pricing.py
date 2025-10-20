#!/usr/bin/env python3
"""
Historic crypto pricing database for accurate USD conversions
Migrated to use PostgreSQL via DatabaseManager
"""

import sys
import os
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add web_ui to path for DatabaseManager import
current_dir = Path(__file__).parent
sys.path.append(str(current_dir / 'web_ui'))

from database import db_manager

class CryptoPricingDB:
    def __init__(self):
        """Initialize crypto pricing database using centralized DatabaseManager"""
        self.db = db_manager
        self.init_database()

    def init_database(self):
        """Initialize the pricing database using DatabaseManager"""
        try:
            if self.db.db_type == 'postgresql':
                # PostgreSQL syntax
                query = """
                    CREATE TABLE IF NOT EXISTS crypto_historic_prices (
                        date DATE NOT NULL,
                        symbol VARCHAR(10) NOT NULL,
                        price_usd DECIMAL(18,8) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (date, symbol)
                    );

                    CREATE INDEX IF NOT EXISTS idx_crypto_historic_prices_symbol ON crypto_historic_prices(symbol);
                    CREATE INDEX IF NOT EXISTS idx_crypto_historic_prices_date ON crypto_historic_prices(date);
                """
            else:
                # SQLite syntax (fallback)
                query = """
                    CREATE TABLE IF NOT EXISTS crypto_historic_prices (
                        date TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        price_usd REAL NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (date, symbol)
                    );
                """

            self.db.execute_query(query)
            print(f"📊 Crypto pricing database initialized on {self.db.db_type}")

        except Exception as e:
            print(f"❌ Error initializing crypto pricing database: {e}")
            raise


    def fetch_historic_prices_binance(self, symbol, start_date='2024-01-01', end_date=None):
        """Fetch historic prices from Binance public API"""
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # Binance symbols
        binance_symbols = {
            'BTC': 'BTCUSDT',
            'ETH': 'ETHUSDT',
            'BNB': 'BNBUSDT',
            'TAO': 'TAOUSDT',
            'USDC': None,  # Stablecoin
            'USDT': None   # Base currency
        }

        if symbol not in binance_symbols or binance_symbols[symbol] is None:
            # Only insert stable prices for actual stablecoins (USDC, USDT)
            if symbol in ['USDC', 'USDT']:
                print(f"💵 {symbol} is a stablecoin, inserting fixed $1.00 prices")
                self.insert_stable_prices(symbol, start_date, end_date, 1.0)
            else:
                print(f"❌ {symbol} not available on Binance and not a stablecoin - no price data available")
            return

        binance_symbol = binance_symbols[symbol]
        print(f"📈 Fetching {symbol} prices from Binance ({binance_symbol})...")

        try:
            # Binance Klines API
            url = "https://api.binance.com/api/v3/klines"

            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)

            params = {
                'symbol': binance_symbol,
                'interval': '1d',
                'startTime': start_ts,
                'endTime': end_ts,
                'limit': 1000
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Prepare batch insert operations
            insert_operations = []
            inserted_count = 0

            for kline in data:
                # kline format: [timestamp, open, high, low, close, volume, ...]
                timestamp_ms = kline[0]
                close_price = float(kline[4])

                date = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d')

                if self.db.db_type == 'postgresql':
                    query = """
                        INSERT INTO crypto_historic_prices (date, symbol, price_usd, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (date, symbol)
                        DO UPDATE SET price_usd = EXCLUDED.price_usd, updated_at = CURRENT_TIMESTAMP
                    """
                else:
                    query = """
                        INSERT OR REPLACE INTO crypto_historic_prices (date, symbol, price_usd, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """

                insert_operations.append({
                    'query': query,
                    'params': (date, symbol, close_price)
                })
                inserted_count += 1

            # Execute batch operation
            if insert_operations:
                batch_result = self.db.execute_batch_operation(insert_operations, batch_size=100)
                if batch_result['failed_batches'] > 0:
                    print(f"⚠️ Warning: {batch_result['failed_batches']} batches failed during insert")
                    for error in batch_result['errors']:
                        print(f"   Error: {error}")

            print(f"✅ Inserted {inserted_count} {symbol} price records from Binance")

        except Exception as e:
            print(f"❌ Error fetching {symbol} prices from Binance: {e}")

    def insert_stable_prices(self, symbol, start_date, end_date, price=1.0):
        """Insert stable prices for stablecoins"""
        print(f"💵 Inserting stable prices for {symbol} at ${price}")

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        current_date = start
        insert_operations = []

        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')

            if self.db.db_type == 'postgresql':
                query = """
                    INSERT INTO crypto_historic_prices (date, symbol, price_usd, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (date, symbol)
                    DO UPDATE SET price_usd = EXCLUDED.price_usd, updated_at = CURRENT_TIMESTAMP
                """
            else:
                query = """
                    INSERT OR REPLACE INTO crypto_historic_prices (date, symbol, price_usd, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """

            insert_operations.append({
                'query': query,
                'params': (date_str, symbol, price)
            })

            current_date += timedelta(days=1)

        # Execute batch operation
        if insert_operations:
            batch_result = self.db.execute_batch_operation(insert_operations, batch_size=100)
            inserted_count = batch_result['total_rows_affected']

            if batch_result['failed_batches'] > 0:
                print(f"⚠️ Warning: {batch_result['failed_batches']} batches failed during insert")
                for error in batch_result['errors']:
                    print(f"   Error: {error}")

            print(f"✅ Inserted {inserted_count} {symbol} stable price records")

    def get_price_on_date(self, symbol, date_str):
        """Get price for a specific date, with fallback logic"""
        try:
            # First try exact date
            if self.db.db_type == 'postgresql':
                query = """
                    SELECT price_usd FROM crypto_historic_prices
                    WHERE date = %s AND symbol = %s
                """
            else:
                query = """
                    SELECT price_usd FROM crypto_historic_prices
                    WHERE date = ? AND symbol = ?
                """

            result = self.db.execute_query(query, (date_str, symbol), fetch_one=True)
            if result:
                return float(result['price_usd']) if hasattr(result, 'get') else float(result[0])

            # Try nearest date within 7 days
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            for i in range(1, 8):
                # Check previous days
                prev_date = (target_date - timedelta(days=i)).strftime('%Y-%m-%d')
                result = self.db.execute_query(query, (prev_date, symbol), fetch_one=True)
                if result:
                    return float(result['price_usd']) if hasattr(result, 'get') else float(result[0])

                # Check next days
                next_date = (target_date + timedelta(days=i)).strftime('%Y-%m-%d')
                result = self.db.execute_query(query, (next_date, symbol), fetch_one=True)
                if result:
                    return float(result['price_usd']) if hasattr(result, 'get') else float(result[0])

            # No price data available - return None to signal missing data
            print(f"❌ No historic price found for {symbol} on {date_str} (checked ±7 days)")
            print(f"💡 Run 'python crypto_pricing.py' to populate historical price data from Binance")
            return None

        except Exception as e:
            print(f"❌ Error getting price for {symbol} on {date_str}: {e}")
            return None

    def populate_all_prices(self, start_date='2024-01-01'):
        """Populate all supported crypto prices from Binance"""
        symbols = ['BTC', 'TAO', 'ETH', 'BNB', 'USDC', 'USDT']

        for symbol in symbols:
            print(f"\n🔄 Processing {symbol}...")
            # Use Binance as primary source
            self.fetch_historic_prices_binance(symbol, start_date)
            time.sleep(1)  # Rate limiting

    def get_db_stats(self):
        """Get database statistics"""
        try:
            query = """
                SELECT symbol, COUNT(*) as count, MIN(date) as earliest, MAX(date) as latest
                FROM crypto_historic_prices
                GROUP BY symbol
                ORDER BY symbol
            """

            stats = self.db.execute_query(query, fetch_all=True)

            print(f"📊 Crypto Pricing Database Stats ({self.db.db_type}):")
            if stats:
                for row in stats:
                    if hasattr(row, 'get'):
                        symbol = row['symbol']
                        count = row['count']
                        earliest = row['earliest']
                        latest = row['latest']
                    else:
                        symbol, count, earliest, latest = row
                    print(f"  {symbol}: {count} records ({earliest} to {latest})")
            else:
                print("  No crypto pricing data found")

            return stats

        except Exception as e:
            print(f"❌ Error getting database stats: {e}")
            return []

def main():
    """Test the crypto pricing database"""
    db = CryptoPricingDB()

    # Populate with historic data
    db.populate_all_prices()

    # Show stats
    db.get_db_stats()

    # Test price lookup
    test_date = '2025-08-15'
    btc_price = db.get_price_on_date('BTC', test_date)
    tao_price = db.get_price_on_date('TAO', test_date)

    print(f"\n🧪 Test Price Lookup for {test_date}:")
    print(f"  BTC: ${btc_price:,.2f}")
    print(f"  TAO: ${tao_price:,.2f}")

if __name__ == '__main__':
    main()