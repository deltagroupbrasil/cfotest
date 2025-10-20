"""
Historical Currency Converter System
Converts invoice amounts to USD using historical exchange rates from the invoice date
Prevents currency fluctuation from affecting historical financial records
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os


class HistoricalCurrencyConverter:
    """
    Provides historical currency conversion for invoice amounts.
    Uses multiple APIs for reliability and caches rates to prevent redundant API calls.
    """

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.api_key = os.getenv('EXCHANGE_RATES_API_KEY')  # From exchangerate-api.com
        self.backup_apis = {
            'fixer': os.getenv('FIXER_API_KEY'),  # fixer.io backup
            'currencylayer': os.getenv('CURRENCYLAYER_API_KEY')  # currencylayer.com backup
        }

        # Ensure historical rates table exists
        self._ensure_historical_rates_table()

    def _ensure_historical_rates_table(self):
        """Create historical exchange rates table if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS historical_exchange_rates (
            id SERIAL PRIMARY KEY,
            from_currency VARCHAR(3) NOT NULL,
            to_currency VARCHAR(3) NOT NULL,
            rate_date DATE NOT NULL,
            exchange_rate DECIMAL(15, 8) NOT NULL,
            api_source VARCHAR(50) NOT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(from_currency, to_currency, rate_date)
        );

        CREATE INDEX IF NOT EXISTS idx_exchange_rates_lookup
        ON historical_exchange_rates (from_currency, to_currency, rate_date);
        """

        try:
            self.db_manager.execute_query(create_table_sql)
            print("[OK] Historical exchange rates table ensured")
        except Exception as e:
            print(f"[WARNING] Could not create historical rates table: {e}")

    def convert_invoice_amount(
        self,
        amount: float,
        from_currency: str,
        invoice_date: str,
        to_currency: str = 'USD'
    ) -> Dict:
        """
        Convert invoice amount to USD using historical rate from invoice date.

        Returns:
        {
            'original_amount': float,
            'original_currency': str,
            'converted_amount': float,
            'converted_currency': str,
            'exchange_rate': float,
            'rate_date': str,
            'conversion_successful': bool,
            'source': str,
            'note': str
        }
        """

        # Parse invoice date
        if isinstance(invoice_date, str):
            try:
                if 'GMT' in invoice_date:
                    invoice_date = datetime.strptime(invoice_date.split(' GMT')[0], '%a, %d %b %Y %H:%M:%S')
                else:
                    # Try different date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                        try:
                            invoice_date = datetime.strptime(invoice_date, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        invoice_date = datetime.strptime(invoice_date, '%Y-%m-%d %H:%M:%S')
            except ValueError as e:
                return {
                    'original_amount': amount,
                    'original_currency': from_currency,
                    'converted_amount': amount,  # Fallback to original
                    'converted_currency': to_currency,
                    'exchange_rate': 1.0,
                    'rate_date': str(invoice_date),
                    'conversion_successful': False,
                    'source': 'error',
                    'note': f'Date parsing failed: {e}'
                }

        # Handle same currency
        if from_currency.upper() == to_currency.upper():
            return {
                'original_amount': amount,
                'original_currency': from_currency,
                'converted_amount': amount,
                'converted_currency': to_currency,
                'exchange_rate': 1.0,
                'rate_date': invoice_date.strftime('%Y-%m-%d'),
                'conversion_successful': True,
                'source': 'same_currency',
                'note': 'No conversion needed - same currency'
            }

        # Normalize currency codes
        from_currency = self._normalize_currency_code(from_currency.upper())
        to_currency = to_currency.upper()

        rate_date = invoice_date.strftime('%Y-%m-%d')

        # Try to get rate from cache first
        cached_rate = self._get_cached_rate(from_currency, to_currency, rate_date)
        if cached_rate:
            converted_amount = amount * cached_rate['exchange_rate']
            return {
                'original_amount': amount,
                'original_currency': from_currency,
                'converted_amount': round(converted_amount, 2),
                'converted_currency': to_currency,
                'exchange_rate': cached_rate['exchange_rate'],
                'rate_date': rate_date,
                'conversion_successful': True,
                'source': f"cached_{cached_rate['api_source']}",
                'note': 'Rate retrieved from cache'
            }

        # Fetch historical rate from API
        rate_data = self._fetch_historical_rate(from_currency, to_currency, invoice_date)
        if rate_data and rate_data['success']:
            converted_amount = amount * rate_data['rate']

            # Cache the rate
            self._cache_exchange_rate(
                from_currency, to_currency, rate_date,
                rate_data['rate'], rate_data['source']
            )

            return {
                'original_amount': amount,
                'original_currency': from_currency,
                'converted_amount': round(converted_amount, 2),
                'converted_currency': to_currency,
                'exchange_rate': rate_data['rate'],
                'rate_date': rate_date,
                'conversion_successful': True,
                'source': rate_data['source'],
                'note': f'Rate fetched from {rate_data["source"]}'
            }

        # Fallback: return original amount with error
        return {
            'original_amount': amount,
            'original_currency': from_currency,
            'converted_amount': amount,  # Fallback to original
            'converted_currency': to_currency,
            'exchange_rate': 1.0,
            'rate_date': rate_date,
            'conversion_successful': False,
            'source': 'fallback',
            'note': 'API fetch failed - using original amount'
        }

    def _normalize_currency_code(self, currency: str) -> str:
        """Normalize currency codes to standard format"""
        currency_mapping = {
            'GUA': 'PYG',  # Guarani paraguaio
            'GUARANI': 'PYG',
            'GUARANIS': 'PYG',
        }
        return currency_mapping.get(currency.upper(), currency.upper())

    def _get_cached_rate(self, from_currency: str, to_currency: str, rate_date: str) -> Optional[Dict]:
        """Get exchange rate from cache"""
        query = """
        SELECT exchange_rate, api_source, fetched_at
        FROM historical_exchange_rates
        WHERE from_currency = %s AND to_currency = %s AND rate_date = %s
        ORDER BY fetched_at DESC
        LIMIT 1
        """

        try:
            result = self.db_manager.execute_query(
                query, (from_currency, to_currency, rate_date), fetch_one=True
            )
            if result:
                return {
                    'exchange_rate': float(result['exchange_rate']),
                    'api_source': result['api_source'],
                    'fetched_at': result['fetched_at']
                }
        except Exception as e:
            print(f"Error fetching cached rate: {e}")

        return None

    def _cache_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: str,
        exchange_rate: float,
        source: str
    ):
        """Cache exchange rate in database"""
        insert_sql = """
        INSERT INTO historical_exchange_rates
        (from_currency, to_currency, rate_date, exchange_rate, api_source)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (from_currency, to_currency, rate_date)
        DO UPDATE SET
            exchange_rate = EXCLUDED.exchange_rate,
            api_source = EXCLUDED.api_source,
            fetched_at = CURRENT_TIMESTAMP
        """

        try:
            self.db_manager.execute_query(
                insert_sql,
                (from_currency, to_currency, rate_date, exchange_rate, source)
            )
        except Exception as e:
            print(f"Error caching exchange rate: {e}")

    def _fetch_historical_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: datetime
    ) -> Optional[Dict]:
        """Fetch historical exchange rate from external APIs"""

        # Try primary API first (exchangerate-api.com)
        if self.api_key:
            rate = self._fetch_from_exchangerate_api(from_currency, to_currency, rate_date)
            if rate:
                return rate

        # Try backup APIs
        for api_name, api_key in self.backup_apis.items():
            if api_key:
                if api_name == 'fixer':
                    rate = self._fetch_from_fixer_io(from_currency, to_currency, rate_date)
                elif api_name == 'currencylayer':
                    rate = self._fetch_from_currencylayer(from_currency, to_currency, rate_date)

                if rate:
                    return rate

        # Free API fallback (limited requests)
        rate = self._fetch_from_free_api(from_currency, to_currency, rate_date)
        if rate:
            return rate

        return None

    def _fetch_from_exchangerate_api(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: datetime
    ) -> Optional[Dict]:
        """Fetch from exchangerate-api.com (primary API)"""
        try:
            date_str = rate_date.strftime('%Y-%m-%d')
            url = f"https://v6.exchangerate-api.com/v6/{self.api_key}/history/{from_currency}/{date_str}"

            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('result') == 'success' and to_currency in data.get('conversion_rates', {}):
                    return {
                        'success': True,
                        'rate': data['conversion_rates'][to_currency],
                        'source': 'exchangerate-api',
                        'date': date_str
                    }
        except Exception as e:
            print(f"Error fetching from exchangerate-api: {e}")

        return None

    def _fetch_from_fixer_io(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: datetime
    ) -> Optional[Dict]:
        """Fetch from fixer.io (backup API)"""
        try:
            date_str = rate_date.strftime('%Y-%m-%d')
            url = f"http://data.fixer.io/api/{date_str}"
            params = {
                'access_key': self.backup_apis['fixer'],
                'base': from_currency,
                'symbols': to_currency
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and to_currency in data.get('rates', {}):
                    return {
                        'success': True,
                        'rate': data['rates'][to_currency],
                        'source': 'fixer.io',
                        'date': date_str
                    }
        except Exception as e:
            print(f"Error fetching from fixer.io: {e}")

        return None

    def _fetch_from_free_api(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: datetime
    ) -> Optional[Dict]:
        """Fallback to free API with rate limiting"""
        try:
            date_str = rate_date.strftime('%Y-%m-%d')

            # Use exchangerate.host (free API)
            url = f"https://api.exchangerate.host/{date_str}"
            params = {
                'base': from_currency,
                'symbols': to_currency
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and to_currency in data.get('rates', {}):
                    return {
                        'success': True,
                        'rate': data['rates'][to_currency],
                        'source': 'exchangerate.host',
                        'date': date_str
                    }
        except Exception as e:
            print(f"Error fetching from free API: {e}")

        return None

    def bulk_convert_invoices(self, limit: int = 50) -> Dict:
        """
        Convert all invoices that don't have USD equivalent amounts yet.
        Returns summary of conversion results.
        """

        # First, add USD equivalent columns if they don't exist
        self._ensure_usd_columns()

        # Get invoices that need conversion (non-USD and no USD equivalent yet)
        query = """
        SELECT id, total_amount, currency, date, vendor_name
        FROM invoices
        WHERE currency != 'USD'
        AND (usd_equivalent_amount IS NULL OR usd_equivalent_amount = 0)
        ORDER BY date DESC
        LIMIT %s
        """

        invoices_to_convert = self.db_manager.execute_query(query, (limit,), fetch_all=True)

        results = {
            'total_processed': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'conversion_details': []
        }

        for invoice in invoices_to_convert:
            try:
                conversion = self.convert_invoice_amount(
                    float(invoice['total_amount']),
                    invoice['currency'],
                    invoice['date']
                )

                # Update invoice with USD equivalent
                if conversion['conversion_successful']:
                    self._update_invoice_usd_amount(
                        invoice['id'],
                        conversion['converted_amount'],
                        conversion['exchange_rate'],
                        conversion['rate_date'],
                        conversion['source']
                    )
                    results['successful_conversions'] += 1
                else:
                    results['failed_conversions'] += 1

                results['conversion_details'].append({
                    'invoice_id': invoice['id'],
                    'vendor_name': invoice['vendor_name'],
                    'conversion': conversion
                })
                results['total_processed'] += 1

            except Exception as e:
                results['failed_conversions'] += 1
                results['conversion_details'].append({
                    'invoice_id': invoice['id'],
                    'vendor_name': invoice.get('vendor_name', 'Unknown'),
                    'error': str(e)
                })
                results['total_processed'] += 1

        return results

    def _ensure_usd_columns(self):
        """Add USD equivalent columns to invoices table"""
        alter_queries = [
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS usd_equivalent_amount DECIMAL(15, 2)",
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS historical_exchange_rate DECIMAL(15, 8)",
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS rate_date DATE",
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS rate_source VARCHAR(50)",
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS conversion_notes TEXT"
        ]

        for query in alter_queries:
            try:
                self.db_manager.execute_query(query)
            except Exception as e:
                print(f"Column might already exist: {e}")

    def _update_invoice_usd_amount(
        self,
        invoice_id: str,
        usd_amount: float,
        exchange_rate: float,
        rate_date: str,
        source: str
    ):
        """Update invoice with USD equivalent amount"""
        update_sql = """
        UPDATE invoices
        SET
            usd_equivalent_amount = %s,
            historical_exchange_rate = %s,
            rate_date = %s,
            rate_source = %s,
            conversion_notes = 'Converted using historical exchange rate'
        WHERE id = %s
        """

        self.db_manager.execute_query(
            update_sql,
            (usd_amount, exchange_rate, rate_date, source, invoice_id)
        )

    def get_conversion_stats(self) -> Dict:
        """Get statistics about currency conversions"""
        stats_query = """
        SELECT
            COUNT(*) as total_invoices,
            COUNT(CASE WHEN currency = 'USD' THEN 1 END) as usd_invoices,
            COUNT(CASE WHEN currency != 'USD' THEN 1 END) as foreign_currency_invoices,
            COUNT(CASE WHEN usd_equivalent_amount IS NOT NULL AND usd_equivalent_amount > 0 THEN 1 END) as converted_invoices,
            COUNT(DISTINCT currency) as unique_currencies,
            ARRAY_AGG(DISTINCT currency) as currencies
        FROM invoices
        """

        return self.db_manager.execute_query(stats_query, fetch_one=True)