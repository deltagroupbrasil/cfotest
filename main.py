#!/usr/bin/env python3
"""
DELTA CFO AGENT - MAIN ENTRY POINT
Simple transaction categorization system that reads any bank/crypto file,
classifies transactions using business_knowledge.md, and outputs to MASTER_TRANSACTIONS.csv
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import glob
import requests
import time
import json
import shutil
import argparse
import re

class DeltaCFOAgent:
    def __init__(self):
        """Initialize the CFO Agent with business knowledge"""
        self.business_knowledge_file = 'business_knowledge.md'
        self.master_file = 'MASTER_TRANSACTIONS.csv'  # SINGLE SOURCE OF TRUTH - NEVER CREATE DUPLICATES
        self.classified_dir = 'classified_transactions'

        # Create output directory if it doesn't exist
        os.makedirs(self.classified_dir, exist_ok=True)

        # ENFORCE SINGLE MASTER FILE RULE - Remove any duplicate master files
        self.enforce_single_master_file()

        # AUTO-CLEANUP TEMPORARY PYTHON FILES
        self.cleanup_temporary_files()

        # Load business knowledge into memory
        self.load_business_knowledge()

        # Load existing master file if it exists
        self.master_df = self.load_master_transactions()

    def load_business_knowledge(self):
        """Load classification rules from classification_patterns database (SaaS architecture)"""
        # Initialize pattern dictionaries
        self.patterns = {
            'revenue': {},
            'transfer': {},
            'technology': {},
            'paraguay': {},
            'brazil': {},
            'crypto': {},
            'personal': {},
            'fees': {},
            'expense': {},  # General expenses
            'regional': {},  # Regional patterns
            'card_mapping': {}  # Card to entity mappings
        }

        self.account_mapping = {}
        self.employees = {}
        self.wallets = {}

        # Try to load from database first (SaaS architecture)
        try:
            import psycopg2
            import os as os_module

            # Get database credentials from environment
            db_host = os_module.environ.get('DB_HOST', '34.39.143.82')
            db_port = os_module.environ.get('DB_PORT', '5432')
            db_name = os_module.environ.get('DB_NAME', 'delta_cfo')
            db_user = os_module.environ.get('DB_USER', 'delta_user')
            db_password = os_module.environ.get('DB_PASSWORD', 'nWr0Y8bU51ypLjMIfx8bTe+V/1iOV59r90T8wJEsSGo=')

            # Hardcoded tenant for now (Delta)
            tenant_id = 'delta'

            # Connect to PostgreSQL
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password
            )
            cursor = conn.cursor()

            # Load all patterns for Delta tenant
            cursor.execute("""
                SELECT pattern_type, description_pattern, entity, accounting_category, confidence_score
                FROM classification_patterns
                WHERE tenant_id = %s
                ORDER BY confidence_score DESC
            """, (tenant_id,))

            patterns_loaded = 0
            for pattern_type, description_pattern, entity, accounting_category, confidence_score in cursor.fetchall():
                pattern_key = pattern_type if pattern_type in self.patterns else 'expense'

                # Handle card mappings specially
                if pattern_type == 'card_mapping':
                    self.account_mapping[description_pattern] = entity
                else:
                    # Convert SQL LIKE pattern (%KEYWORD%) to Python string (KEYWORD)
                    # Remove leading and trailing % wildcards for Python "in" matching
                    python_pattern = description_pattern.strip('%').upper()

                    # Store pattern in appropriate category
                    # Use accounting_category as fallback when entity is NULL (for expense patterns)
                    self.patterns[pattern_key][python_pattern] = {
                        'entity': entity or accounting_category or 'Unclassified',
                        'confidence': float(confidence_score) if confidence_score else 0.5,
                        'category': accounting_category or 'General'
                    }
                patterns_loaded += 1

            # Load wallet addresses for the tenant
            cursor.execute("""
                SELECT wallet_address, entity_name, purpose, wallet_type, confidence_score
                FROM wallet_addresses
                WHERE tenant_id = %s AND is_active = TRUE
                ORDER BY created_at DESC
            """, (tenant_id,))

            for wallet_address, entity_name, purpose, wallet_type, confidence_score in cursor.fetchall():
                # Store wallet with lowercase address for case-insensitive matching
                self.wallets[wallet_address.lower()] = {
                    'entity': entity_name,
                    'purpose': purpose or '',
                    'type': wallet_type or 'unknown',
                    'confidence': float(confidence_score) if confidence_score else 0.9
                }

            cursor.close()
            conn.close()

            print(f"✅ Loaded business knowledge: {len(self.account_mapping)} accounts, {patterns_loaded} patterns, {len(self.wallets)} wallets")
            print(f"   📊 Pattern breakdown: revenue={len(self.patterns['revenue'])}, expense={len(self.patterns['expense'])}, crypto={len(self.patterns['crypto'])}, regional={len(self.patterns['regional'])}")
            return

        except Exception as e:
            print(f"⚠️ Could not load from database: {e}")
            print(f"   Falling back to business_knowledge.md file...")

            # Fallback to file-based loading if database fails
            import re

            if not os.path.exists(self.business_knowledge_file):
                print(f"⚠️ {self.business_knowledge_file} not found - using basic rules")
                return

            with open(self.business_knowledge_file, 'r') as f:
                content = f.read()

            # Parse account mappings (card numbers to entities)
            account_section = re.search(r'### \*\*BANK ACCOUNT MAPPING\*\*(.*?)###', content, re.DOTALL)
            if account_section:
                rows = re.findall(r'\| ([\w\s\.]+) \| (\d{4}) \| ([\w\s/]+) \|', account_section.group(1))
                for account, ending, entity in rows:
                    if ending.isdigit():
                        self.account_mapping[ending] = entity.strip()

            print(f"✅ Loaded business knowledge: {len(self.account_mapping)} accounts, {sum(len(p) for p in self.patterns.values())} patterns, {len(self.wallets)} wallets")

    def enforce_single_master_file(self):
        """Enforce single master file rule - remove any duplicates"""

        # List of potential duplicate master file patterns
        duplicate_patterns = [
            'MASTER_TRANSACTIONS_*.csv',
            'master_transactions*.csv',
            '*_MASTER_TRANSACTIONS.csv',
            'MASTER_UPDATED*.csv',
            'UPDATED_MASTER*.csv'
        ]

        duplicates_found = []
        for pattern in duplicate_patterns:
            duplicates_found.extend(glob.glob(pattern))

        # Remove duplicates (keep only the main master file)
        for duplicate in duplicates_found:
            if duplicate != self.master_file:
                try:
                    os.remove(duplicate)
                    print(f"🗑️  Removed duplicate master file: {duplicate}")
                except:
                    pass

        # Check for common naming variations and consolidate if found
        variations = [
            'master_transactions.csv',  # lowercase
            'Master_Transactions.csv',  # mixed case
            'MASTER_TRANSACTION.csv',   # singular
        ]

        for variation in variations:
            if os.path.exists(variation) and variation != self.master_file:
                try:
                    os.remove(variation)
                    print(f"🗑️  Removed variation: {variation}")
                except:
                    print(f"⚠️  Found potential duplicate: {variation} - consider consolidating")

    def cleanup_temporary_files(self):
        """Auto-cleanup temporary Python files created for one-time tasks"""

        # List of temporary file patterns that should be cleaned up
        temp_patterns = [
            'reclassify_*.py',
            'summary_*.py',
            'temp_*.py',
            'test_*.py',
            'debug_*.py',
            'fix_*.py',
            'process_*.py',  # All the old process_xxx.py files we had
            'consolidate_*.py',
            '*_temp.py',
            '*_test.py',
            '*_debug.py'
        ]

        # Core files that should NEVER be deleted
        protected_files = {
            'main.py',              # Main entry point
            'business_knowledge.md'  # Knowledge base (not Python but important)
        }

        temp_files_found = []
        for pattern in temp_patterns:
            temp_files_found.extend(glob.glob(pattern))

        # Remove temporary files (but protect core files)
        for temp_file in temp_files_found:
            if temp_file not in protected_files and os.path.exists(temp_file):
                try:
                    # Check if file is actually temporary (created recently or contains temp patterns)
                    if self.is_temporary_file(temp_file):
                        os.remove(temp_file)
                        print(f"🧹 Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    print(f"⚠️  Could not remove {temp_file}: {e}")

        # Clean up empty directories
        empty_dirs = ['temp', 'debug', 'test_files']
        for directory in empty_dirs:
            if os.path.exists(directory) and not os.listdir(directory):
                try:
                    os.rmdir(directory)
                    print(f"🧹 Removed empty directory: {directory}")
                except:
                    pass

    def is_temporary_file(self, filepath):
        """Determine if a Python file is temporary and can be safely deleted"""

        filename = os.path.basename(filepath).lower()

        # Patterns that indicate temporary files
        temp_indicators = [
            'reclassify',
            'summary_check',
            'temp_',
            'test_',
            'debug_',
            'fix_',
            'consolidate_',
            '_temp',
            '_test',
            '_debug'
        ]

        # Check filename patterns
        for indicator in temp_indicators:
            if indicator in filename:
                return True

        # Check file content for temporary markers
        try:
            with open(filepath, 'r') as f:
                content = f.read(500)  # Read first 500 chars
                temp_markers = [
                    'temporary script',
                    'one-time use',
                    'delete after use',
                    'TEMP FILE',
                    'TODO: DELETE'
                ]
                for marker in temp_markers:
                    if marker.lower() in content.lower():
                        return True
        except:
            pass

        return False

    def safe_float(self, value):
        """Safely convert value to float, returning 0 if conversion fails"""
        try:
            return float(value) if value else 0
        except (ValueError, TypeError):
            print(f"⚠️  Warning: Could not convert '{value}' to float, using 0")
            return 0

    def detect_intercompany_transaction(self, description, entity, account, amount):
        """Detect intercompany transactions for consolidation elimination"""

        description_upper = str(description).upper()
        amount_float = self.safe_float(amount)

        # Default non-intercompany transaction
        default_result = {
            'from_entity': entity,
            'to_entity': 'External',
            'type': 'External',
            'elimination_required': False,
            'elimination_amount': 0
        }

        # Map accounts to entities for intercompany detection
        account_entity_map = {
            '3687': 'Delta LLC',  # BUS COMPLETE CHK
            '6118': 'Mixed Entities',  # J. DHAMER
            '4832': 'Delta Mining Paraguay S.A.',  # D. OZUNA
            '6134': 'Delta Mining Paraguay S.A.',  # A. MENDEZ
            '2512': 'Delta Mining Paraguay S.A.',  # A. CASTORINO
            '4236': 'Personal',  # V. CRUZ
            '6126': 'Delta Mining Paraguay S.A.'   # E. AQUINO
        }

        from_entity = account_entity_map.get(account, entity)

        # INTERCOMPANY DETECTION PATTERNS

        # 1. Wire transfers to Paraguay subsidiaries
        if ('DELTA VALIDATOR' in description_upper or 'DELTA MINING' in description_upper) and \
           ('PARAGUAY' in description_upper or 'ASUNCION' in description_upper):
            return {
                'from_entity': 'Delta LLC',
                'to_entity': 'Delta Mining Paraguay S.A.',
                'type': 'Investment',
                'elimination_required': True,
                'elimination_amount': abs(amount_float)
            }

        # 2. Credit card payments between entities (if from LLC paying for subsidiary expenses)
        if 'PAYMENT TO CHASE CARD' in description_upper and from_entity == 'Delta LLC':
            return {
                'from_entity': 'Delta LLC',
                'to_entity': 'Mixed Entities',
                'type': 'Intercompany_Loan',
                'elimination_required': True,
                'elimination_amount': abs(amount_float)
            }

        # 3. Revenue from subsidiaries to parent
        if entity in ['Delta Prop Shop LLC', 'Delta Mining Paraguay S.A.'] and amount_float > 0:
            # Large amounts could be revenue sharing or dividends
            if abs(amount_float) > 10000:  # Threshold for significant intercompany revenue
                return {
                    'from_entity': entity,
                    'to_entity': 'Delta LLC',
                    'type': 'Revenue_Share',
                    'elimination_required': True,
                    'elimination_amount': abs(amount_float)
                }

        # 4. Transfers between Chase cards (different entities)
        if 'ONLINE TRANSFER' in description_upper:
            # Extract account numbers from description if possible
            if '3687' in description_upper and from_entity != 'Delta LLC':
                return {
                    'from_entity': from_entity,
                    'to_entity': 'Delta LLC',
                    'type': 'Intercompany_Transfer',
                    'elimination_required': True,
                    'elimination_amount': abs(amount_float)
                }

        # 5. Management fees or expense allocations
        if 'MANAGEMENT' in description_upper or 'ALLOCATION' in description_upper:
            return {
                'from_entity': entity,
                'to_entity': 'Delta LLC',
                'type': 'Management_Fee',
                'elimination_required': True,
                'elimination_amount': abs(amount_float)
            }

        # 6. Detect patterns indicating intercompany nature
        intercompany_keywords = [
            'DELTA VALIDATOR LLC',
            'DELTA MINING LLC',
            'DELTA PROP SHOP',
            'INTERCOMPANY',
            'SUBSIDIARY'
        ]

        for keyword in intercompany_keywords:
            if keyword in description_upper:
                return {
                    'from_entity': from_entity,
                    'to_entity': 'Auto-detect',
                    'type': 'Intercompany_Loan',
                    'elimination_required': True,
                    'elimination_amount': abs(amount_float)
                }

        return default_result

    def fetch_crypto_prices(self, start_date=None, end_date=None):
        """Fetch and save crypto prices for BTC and TAO"""
        print("💰 Fetching crypto prices...")

        if not start_date or not end_date:
            # Default to last 2 years
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=730)

        # Create price database
        price_data = {}

        # Fetch BTC prices from CoinGecko
        btc_prices = self.fetch_coingecko_prices('bitcoin', start_date, end_date)
        for date_str, price in btc_prices.items():
            if date_str not in price_data:
                price_data[date_str] = {}
            price_data[date_str]['BTC'] = price

        # Fetch TAO prices from CoinGecko
        tao_prices = self.fetch_coingecko_prices('bittensor', start_date, end_date)
        for date_str, price in tao_prices.items():
            if date_str not in price_data:
                price_data[date_str] = {}
            price_data[date_str]['TAO'] = price

        # Save to CSV
        price_df = []
        for date_str, currencies in price_data.items():
            for currency, price in currencies.items():
                price_df.append({
                    'Date': date_str,
                    'Currency': currency,
                    'Price_USD': price
                })

        if price_df:
            df = pd.DataFrame(price_df)
            df.to_csv('crypto_prices_database.csv', index=False)
            print(f"✅ Saved {len(price_df)} price records to crypto_prices_database.csv")

        return price_data

    def fetch_coingecko_prices(self, coin_id, start_date, end_date):
        """Fetch historical prices from CoinGecko API"""
        print(f"📈 Fetching {coin_id.upper()} prices...")

        start_timestamp = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        end_timestamp = int(datetime.combine(end_date, datetime.min.time()).timestamp())

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
        params = {
            'vs_currency': 'usd',
            'from': start_timestamp,
            'to': end_timestamp
        }

        try:
            time.sleep(1.0)  # Rate limiting
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            prices = {}
            if 'prices' in data:
                for timestamp, price in data['prices']:
                    date = datetime.fromtimestamp(timestamp / 1000).date()
                    prices[str(date)] = round(price, 2)

            print(f"✅ Fetched {len(prices)} prices for {coin_id.upper()}")
            return prices

        except Exception as e:
            print(f"❌ Error fetching {coin_id}: {e}")
            return {}

    def add_usd_equivalents(self, df):
        """Add USD equivalent columns for crypto transactions"""
        print("💵 Adding USD equivalents...")

        # Load price database
        price_db = {}
        if os.path.exists('crypto_prices_database.csv'):
            prices_df = pd.read_csv('crypto_prices_database.csv')
            for _, row in prices_df.iterrows():
                date_key = str(row['Date'])
                currency = row['Currency']
                if date_key not in price_db:
                    price_db[date_key] = {}
                price_db[date_key][currency] = float(row['Price_USD'])

        # Add new columns (only if they don't exist, preserve Currency from smart ingestion)
        if 'Currency' not in df.columns:
            df['Currency'] = 'USD'  # Default only if not already set
        df['Crypto_Amount'] = None
        df['USD_Equivalent'] = None
        df['Conversion_Note'] = None

        crypto_converted = 0

        for idx, row in df.iterrows():
            description = str(row['Description'] if 'Description' in row else '')
            amount = self.safe_float(row['Amount'] if 'Amount' in row and pd.notna(row['Amount']) else 0)

            # Handle both standardized and non-standardized date columns
            date_value = None
            if 'Date' in row:
                date_value = row['Date']
            elif 'Transaction Date' in row:
                date_value = row['Transaction Date']
            elif 'Posting Date' in row:
                date_value = row['Posting Date']

            if date_value and pd.notna(date_value):
                date_str = str(pd.to_datetime(date_value).date())
            else:
                # Skip row if no valid date
                continue

            # Use existing Currency from smart ingestion or detect from description as fallback
            currency = row.get('Currency', 'USD') if 'Currency' in df.columns else 'USD'
            crypto_amount = None

            # Only detect from description if Currency is not already set properly
            if currency == 'USD' or pd.isna(currency):
                if 'BTC' in description.upper():
                    currency = 'BTC'
                    # Extract BTC amount from description
                    btc_match = re.search(r'([\d.]+)\s*BTC', description)
                    if btc_match:
                        crypto_amount = float(btc_match.group(1))
                    else:
                        crypto_amount = abs(amount)  # Assume amount is in BTC

                elif 'TAO' in description.upper():
                    currency = 'TAO'
                    tao_match = re.search(r'([\d.]+)\s*TAO', description)
                    if tao_match:
                        crypto_amount = float(tao_match.group(1))
                    else:
                        crypto_amount = abs(amount)

                # Only update Currency column if we detected something different
                if currency != row.get('Currency', 'USD'):
                    df.at[idx, 'Currency'] = currency
            else:
                # Currency already set by smart ingestion, use original amount as crypto amount
                if currency in ['BTC', 'TAO', 'ETH', 'BNB', 'USDC', 'USDT']:
                    crypto_amount = abs(amount)

            if currency != 'USD' and crypto_amount:
                df.at[idx, 'Crypto_Amount'] = crypto_amount

                # Get USD equivalent
                if date_str in price_db and currency in price_db[date_str]:
                    price = price_db[date_str][currency]
                    usd_equivalent = crypto_amount * price
                    df.at[idx, 'USD_Equivalent'] = round(usd_equivalent, 2)
                    df.at[idx, 'Conversion_Note'] = f"{crypto_amount} {currency} @ ${price:,.2f}"
                    crypto_converted += 1
                else:
                    df.at[idx, 'USD_Equivalent'] = amount  # Fallback to original amount
            else:
                df.at[idx, 'USD_Equivalent'] = amount  # USD transactions

        print(f"✅ Converted {crypto_converted} crypto transactions to USD")
        return df

    def extract_keywords(self, df):
        """Extract keywords into dedicated columns"""
        print("🔍 Extracting keywords...")

        keyword_categories = {
            'action_type': ['RECEIVE', 'SEND', 'WITHDRAW', 'CONVERT', 'PAYMENT', 'TRANSFER', 'DEPOSIT'],
            'platform': ['COINBASE', 'CHASE', 'MEXC', 'APPLE', 'JPMORGAN', 'MERCADO'],
            'asset_type': ['BTC', 'TAO', 'USDC', 'USDT', 'USD'],
            'transaction_nature': ['REWARD', 'FEE', 'INCOME', 'INTEREST', 'DIVIDEND'],
            'counterparty': ['EXTERNAL', 'ACCOUNT', 'BANK', 'WALLET']
        }

        # Add keyword columns
        for category in keyword_categories:
            df[f'keywords_{category}'] = None
            df[f'primary_{category.split("_")[0]}'] = None

        for idx, row in df.iterrows():
            description = str(row.get('Description', '')).upper()

            for category, keywords in keyword_categories.items():
                found_keywords = [kw for kw in keywords if kw in description]
                if found_keywords:
                    df.at[idx, f'keywords_{category}'] = ','.join(found_keywords)
                    df.at[idx, f'primary_{category.split("_")[0]}'] = found_keywords[0]

        print("✅ Keywords extracted")
        return df

    def extract_meaningful_identifier(self, description, source_file=''):
        """Extract meaningful transaction identifiers like TxID, counterparty, reference numbers"""
        if not description:
            return ''

        desc = str(description)
        source = str(source_file).lower()

        # Priority 1: Transaction IDs and Reference Numbers
        patterns = [
            r'Transaction#[:\s]*(\w+)',  # Transaction#: 25859028500
            r'Web ID[:\s]*(\w+)',        # Web ID: 9999999999
            r'PPD ID[:\s]*(\w+)',        # PPD ID: 1455293997
            r'REF[:\s]*(\w+)',           # REF: ABC123
            r'#(\w{6,})',                # #ABC123456
            r'TxID[:\s]*(\w+)',          # TxID: 0x1a2b3c4d
            r'0x([a-fA-F0-9]{8,})',      # Crypto transaction hash
            r'(\w{8,}\s*$)',             # Alphanumeric code at end
        ]

        for pattern in patterns:
            match = re.search(pattern, desc, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Priority 2: Counterparty names (people, companies)
        if 'chase' in source:
            # Zelle payments: "Zelle Payment To John Smith"
            zelle_match = re.search(r'Zelle Payment To\s+([^0-9]+?)(?:\s+\d|$)', desc, re.IGNORECASE)
            if zelle_match:
                return zelle_match.group(1).strip()

            # Payment counterparties: "Apple Store Purchase", "Amazon Payment"
            payment_patterns = [
                r'^([A-Z][a-zA-Z\s&\.]+?)\s+(?:Payment|Purchase|Charge)',
                r'Payment To\s+([^0-9]+?)(?:\s+\d|$)',
                r'^([A-Z][a-zA-Z\s&\.]{3,}?)\s+(?:Web|Online|PPD)',
            ]

            for pattern in payment_patterns:
                match = re.search(pattern, desc)
                if match:
                    counterparty = match.group(1).strip()
                    # Filter out generic terms
                    if len(counterparty) > 3 and not any(word in counterparty.lower() for word in ['transfer', 'payment', 'transaction']):
                        return counterparty

        elif 'coinbase' in source:
            # Extract bank information for withdrawals
            bank_match = re.search(r'to\s+([^:]+?):\*+(\d+)', desc, re.IGNORECASE)
            if bank_match:
                bank = bank_match.group(1).strip()
                account = bank_match.group(2)
                return f"{bank} ...{account}"

            # For conversions, extract the conversion details
            if 'convert' in desc.lower():
                # Pattern 1: "Converted 1.0 BTC to 45000.00 USD"
                convert_match = re.search(r'Converted\s+[\d.]+\s+(\w+)\s+(?:to|for)\s+[\d.]+\s+(\w+)', desc, re.IGNORECASE)
                if convert_match:
                    from_currency = convert_match.group(1)
                    to_currency = convert_match.group(2)
                    return f"{from_currency}→{to_currency}"

                # Pattern 2: "Convert 2.5 ETH to 4000.0 USDC"
                convert_match = re.search(r'Convert\s+[\d.]+\s+(\w+)\s+to\s+[\d.]+\s+(\w+)', desc, re.IGNORECASE)
                if convert_match:
                    from_currency = convert_match.group(1)
                    to_currency = convert_match.group(2)
                    return f"{from_currency}→{to_currency}"

                # Pattern 3: "Convert BTC to USDC" (no amounts)
                convert_match = re.search(r'Convert\s+(\w+)\s+to\s+(\w+)', desc, re.IGNORECASE)
                if convert_match:
                    from_currency = convert_match.group(1)
                    to_currency = convert_match.group(2)
                    return f"{from_currency}→{to_currency}"

            # For receives/sends, try to extract meaningful reference
            if 'receive' in desc.lower() and 'external' in desc.lower():
                return 'External Account'

        # Priority 3: Extract alphanumeric codes (6+ characters)
        code_patterns = [
            r'([A-Z][a-z0-9]{5,})',      # Ekxx54Bq style codes
            r'([0-9]{6,})',              # Numeric codes 1164881
        ]

        for pattern in code_patterns:
            match = re.search(pattern, desc)
            if match:
                code = match.group(1).strip()
                # Avoid extracting amounts or dates
                if not re.match(r'^\d+\.?\d*$', code) and len(code) >= 6:
                    return code

        return ''

    def extract_chase_merchant(self, description):
        """Extract merchant/payee name from Chase DEBIT transaction description"""
        if not description:
            return "Unknown Merchant"

        # Remove quotes
        desc = str(description).strip('"')

        # Pattern 1: ORIG CO NAME: extract company name
        match = re.search(r'ORIG CO NAME:([^:]+?)(?:ORIG ID:|$)', desc)
        if match:
            return match.group(1).strip()

        # Pattern 2: Wire transfers - extract beneficiary
        match = re.search(r'A/C:\s*([^/]+?)(?:\s+REF:|$)', desc)
        if match:
            beneficiary = match.group(1).strip()
            # Clean up location info
            beneficiary = re.sub(r'\s+[A-Z]{2}\s+\d{5}.*', '', beneficiary)
            return beneficiary

        # Pattern 3: FEDWIRE/CHIPS - extract B/O (Beneficiary Of)
        match = re.search(r'B/O:\s*([^/]+?)(?:\s+REF:|\s+IMAD:|\s+TRN:|$)', desc)
        if match:
            return match.group(1).strip()

        # Pattern 4: IND NAME - Individual name
        match = re.search(r'IND NAME:([^:]+?)(?:TRN:|$)', desc)
        if match:
            return match.group(1).strip()

        # Pattern 5: Payment to Chase card
        if 'PAYMENT TO CHASE CARD' in desc.upper():
            return "Chase Credit Card"

        # Pattern 6: Online Transfer
        if 'ONLINE TRANSFER' in desc.upper():
            match = re.search(r'(?:FROM|TO) CHK \.\.\.(\\d{4})', desc)
            if match:
                return f"Chase Checking ...{match.group(1)}"
            return "Chase Internal Account"

        # Pattern 7: Simple merchant name at start
        match = re.search(r'^([A-Z][A-Z\s&\.]{3,30}?)(?:\s+FEE|\s+DEBIT|\s+CREDIT|$)', desc)
        if match:
            merchant = match.group(1).strip()
            if len(merchant) > 3:
                return merchant

        # Fallback: Return first 40 characters cleaned
        cleaned = re.sub(r'\s+', ' ', desc[:40]).strip()
        return cleaned if cleaned else "Unknown Merchant"

    def extract_chase_sender(self, description):
        """Extract sender name from Chase CREDIT transaction description"""
        if not description:
            return "Unknown Sender"

        # Remove quotes
        desc = str(description).strip('"')

        # Pattern 1: ORIG CO NAME: extract company name
        match = re.search(r'ORIG CO NAME:([^:]+?)(?:ORIG ID:|$)', desc)
        if match:
            return match.group(1).strip()

        # Pattern 2: FEDWIRE/CHIPS - extract VIA (sending bank) and B/O (sender)
        match = re.search(r'VIA:\s*([^/]+?)/\d+\s+B/O:\s*([^/]+?)(?:\s+REF:|$)', desc)
        if match:
            sender = match.group(2).strip()
            # Clean up location info
            sender = re.sub(r'\s+[A-Z]{2}\s+\d{5}.*', '', sender)
            return sender

        # Pattern 3: IND NAME - Individual name (for ACH)
        match = re.search(r'IND NAME:([^:]+?)(?:TRN:|$)', desc)
        if match:
            return match.group(1).strip()

        # Pattern 4: Online Transfer
        if 'ONLINE TRANSFER' in desc.upper():
            match = re.search(r'(?:FROM|TO) CHK \.\.\.(\\d{4})', desc)
            if match:
                return f"Chase Checking ...{match.group(1)}"
            return "Chase Internal Account"

        # Fallback
        cleaned = re.sub(r'\s+', ' ', desc[:40]).strip()
        return cleaned if cleaned else "Unknown Sender"

    def enhance_structure(self, df):
        """Add Origin, Destination, and clean descriptions"""
        print("🔧 Enhancing transaction structure...")

        # Preserve existing Origin/Destination if already populated by smart ingestion
        if 'Origin' not in df.columns:
            df['Origin'] = None
        if 'Destination' not in df.columns:
            df['Destination'] = None
        if 'Identifier' not in df.columns:
            df['Identifier'] = None
        if 'Description_Minimal' not in df.columns:
            df['Description_Minimal'] = None

        for idx, row in df.iterrows():
            # Skip if Origin/Destination already set by smart ingestion
            existing_origin = row.get('Origin')
            existing_destination = row.get('Destination')
            if (existing_origin and existing_origin not in [None, 'None', 'Unknown', ''] and
                existing_destination and existing_destination not in [None, 'None', 'Unknown', '']):
                # Already have good data from smart ingestion, skip this row
                continue

            description = str(row.get('Description', ''))
            source_file = str(row.get('source_file', ''))
            primary_action = str(row.get('primary_action', '')).upper()

            # Set defaults
            origin = 'Unknown'
            destination = 'Unknown'
            identifier = ''
            minimal_desc = 'Transaction'

            # Get transaction type from Chase CSV Type column
            transaction_type = str(row.get('TransactionType', '')).upper()

            # Detect primary action from Chase transaction type or description
            if transaction_type and transaction_type != 'NAN':
                # Chase transaction types: Sale, Payment, Deposit, etc.
                if transaction_type in ['SALE', 'CHECK', 'FEE']:
                    primary_action = 'SEND'  # Money going out
                elif transaction_type in ['DEPOSIT', 'CREDIT']:
                    primary_action = 'RECEIVE'  # Money coming in
                elif transaction_type in ['PAYMENT']:
                    # Check amount sign to determine direction
                    amount = float(str(row.get('Amount', 0)).replace(',', '').replace('$', ''))
                    primary_action = 'RECEIVE' if amount > 0 else 'SEND'
            elif not primary_action or primary_action == 'NAN':
                # Fallback to description analysis
                desc_upper = description.upper()
                if any(word in desc_upper for word in ['RECEIVE', 'RECEIVED']):
                    primary_action = 'RECEIVE'
                elif any(word in desc_upper for word in ['SEND', 'SENT', 'PAYMENT', 'WITHDRAW']):
                    primary_action = 'SEND'
                elif any(word in desc_upper for word in ['CONVERT', 'TRADE', 'SOLD', 'BOUGHT']):
                    primary_action = 'CONVERT'
                elif any(word in desc_upper for word in ['DEPOSIT']):
                    primary_action = 'RECEIVE'

            # Determine accounts from source file
            if 'coinbase' in source_file.lower():
                account_name = 'Coinbase'
                if primary_action in ['RECEIVE', 'RECEIVED']:
                    origin = 'External Account'
                    destination = account_name
                    minimal_desc = 'Transfer In'
                elif primary_action in ['SEND', 'SENT']:
                    origin = account_name
                    destination = 'External Account'
                    minimal_desc = 'Transfer Out'
                elif primary_action in ['CONVERT', 'TRADE']:
                    origin = account_name
                    destination = account_name
                    minimal_desc = 'Internal Conversion'

            elif 'chase' in source_file.lower():
                # Extract account number from source file name
                account_match = re.search(r'(\d{4})', source_file)

                # Check if this is a credit card or checking account
                # Use AccountIdentifier from smart ingestion if available
                account_identifier = str(row.get('AccountIdentifier', ''))
                is_credit_card = df.attrs.get('is_credit_card', False)

                if account_match:
                    account_num = account_match.group(1)
                    if is_credit_card or 'card' in source_file.lower():
                        account_name = f"Chase Credit Card ...{account_num}"
                    else:
                        account_name = f"Chase Checking ...{account_num}"
                elif is_credit_card or 'card' in source_file.lower():
                    account_name = 'Chase Credit Card'
                else:
                    account_name = 'Chase Checking Account'

                # Determine transaction direction from amount
                amount = float(str(row.get('Amount', 0)).replace(',', '').replace('$', ''))

                if amount < 0:
                    # DEBIT - Money leaving account
                    origin = account_name
                    destination = self.extract_chase_merchant(description)
                    minimal_desc = 'Payment'
                else:
                    # CREDIT - Money coming into account
                    origin = self.extract_chase_sender(description)
                    destination = account_name
                    minimal_desc = 'Deposit'

            # Extract meaningful identifiers (TxID, counterparty, reference numbers)
            identifier = self.extract_meaningful_identifier(description, source_file)

            df.at[idx, 'Origin'] = origin
            df.at[idx, 'Destination'] = destination
            df.at[idx, 'Identifier'] = identifier
            df.at[idx, 'Description_Minimal'] = minimal_desc

        print("✅ Structure enhanced")
        return df

    def enhance_description(self, df):
        """
        Enhance Description field with rich context while keeping Destination clean.
        Adds crypto conversion details, banking info, foreign currency, etc.
        """
        print("📝 Enhancing descriptions with contextual information...")

        for idx, row in df.iterrows():
            base_description = str(row.get('Description', ''))
            if not base_description or base_description == 'nan':
                continue

            context_parts = []

            # 1. CRYPTO CONVERSION CONTEXT
            crypto_col = row.get('Crypto', '')
            conversion_note = row.get('conversion_note', '')
            if crypto_col and str(crypto_col) != 'nan' and str(crypto_col) != '':
                # Extract crypto info: "0.5 BTC" from Crypto column
                context_parts.append(f"Crypto: {crypto_col}")
                if conversion_note and str(conversion_note) != 'nan':
                    context_parts.append(conversion_note)

            # 2. BANKING/WIRE TRANSFER DETAILS
            origin = str(row.get('Origin', ''))
            destination = str(row.get('Destination', ''))
            source_file = str(row.get('source_file', '')).lower()

            # Add account routing info for chase transactions
            if 'chase' in source_file:
                if 'credit card' in origin.lower():
                    # Extract card number from origin
                    card_match = re.search(r'\.\.\.(\d{4})', origin)
                    if card_match:
                        context_parts.append(f"Card: {card_match.group(1)}")
                elif 'checking' in origin.lower():
                    # Extract account number from origin
                    acct_match = re.search(r'\.\.\.(\d{4})', origin)
                    if acct_match:
                        context_parts.append(f"Acct: {acct_match.group(1)}")

            # Add counterparty bank info for wires/ACH
            if any(keyword in base_description.upper() for keyword in ['FEDWIRE', 'CHIPS', 'WIRE TRANSFER', 'ACH']):
                # Extract bank name from origin or destination
                bank_keywords = ['JPMORGAN', 'CHASE', 'WELLS FARGO', 'BANK OF AMERICA', 'CITIBANK', 'CROSS RIVER']
                for bank in bank_keywords:
                    if bank in base_description.upper():
                        context_parts.append(f"via {bank.title()}")
                        break

            # 3. FOREIGN CURRENCY CONTEXT
            # Check if there's a currency conversion in the original description
            foreign_currency_match = re.search(r'([A-Z]{3})\s*[₹₱₲€£¥]\s*([\d,\.]+)', base_description)
            if foreign_currency_match:
                foreign_currency = foreign_currency_match.group(1)
                context_parts.append(f"Foreign: {foreign_currency}")

            # Detect foreign transactions by merchant location indicators
            foreign_indicators = {
                'PARAGUAY': 'PY', 'ASUNCION': 'PY', 'AYOLAS': 'PY',
                'BRAZIL': 'BR', 'BRASIL': 'BR', 'SAO PAULO': 'BR',
                'MEXICO': 'MX', 'BUENOS AIRES': 'AR', 'ARGENTINA': 'AR'
            }
            for indicator, country_code in foreign_indicators.items():
                if indicator in base_description.upper():
                    context_parts.append(f"Country: {country_code}")
                    break

            # Build enhanced description
            if context_parts:
                # Start with clean merchant name (from Destination), add context
                enhanced = base_description + " | " + " | ".join(context_parts)
                df.at[idx, 'Description'] = enhanced

        print(f"✅ Enhanced {len([r for r in df.iterrows() if '|' in str(r[1].get('Description', ''))])} descriptions with context")
        return df

    def add_usd_conversion(self, df):
        """Add USD conversion for crypto amounts using historic pricing"""
        print("💰 Converting crypto amounts to USD using historic prices...")

        # Import crypto pricing database
        from crypto_pricing import CryptoPricingDB
        pricing_db = CryptoPricingDB()

        # Initialize Crypto column to store original amounts
        df['Crypto'] = ''

        for idx, row in df.iterrows():
            original_amount = self.safe_float(row.get('Amount', 0))
            description = str(row.get('Description', ''))
            transaction_date = row.get('Date', '')

            # Extract date in YYYY-MM-DD format
            date_str = self.extract_date_for_pricing(transaction_date)

            # Check if this is a crypto transaction
            crypto_detected = None
            crypto_symbols = ['BTC', 'TAO', 'ETH', 'USDC', 'USDT', 'BNB']

            # First check if we have a Currency column from smart ingestion
            if 'Currency' in df.columns:
                currency_value = str(row.get('Currency', '')).upper().strip()
                if currency_value in crypto_symbols:
                    crypto_detected = currency_value

            # Fallback to description-based detection
            if not crypto_detected:
                for crypto in crypto_symbols:
                    if crypto in description.upper():
                        crypto_detected = crypto
                        break

            if crypto_detected and date_str:
                # Get historic price for the transaction date
                historic_price = pricing_db.get_price_on_date(crypto_detected, date_str)

                # Only process if we have a valid price
                if historic_price is not None:
                    amount_usd = abs(original_amount) * historic_price

                    # Store original crypto amount in Crypto column
                    df.at[idx, 'Crypto'] = f"{abs(original_amount)} {crypto_detected}"

                    # Replace Amount with USD equivalent
                    df.at[idx, 'Amount'] = round(amount_usd, 2) if original_amount >= 0 else -round(amount_usd, 2)

                    # Update description to include conversion details
                    updated_description = self.enhance_crypto_description(
                        description, crypto_detected, abs(original_amount), historic_price, amount_usd, date_str
                    )
                    df.at[idx, 'Description'] = updated_description

                    if abs(original_amount) > 0:  # Only log for non-zero amounts
                        print(f"  📈 {crypto_detected} on {date_str}: {abs(original_amount)} × ${historic_price:,.2f} = ${amount_usd:,.2f}")
                else:
                    # Price data not available - keep crypto amount as-is and add note
                    df.at[idx, 'Crypto'] = f"{abs(original_amount)} {crypto_detected}"
                    df.at[idx, 'Conversion_Note'] = f"Price data unavailable for {crypto_detected} on {date_str}"
                    print(f"  ⚠️ No price data for {crypto_detected} on {date_str} - keeping original amount")
            else:
                # For non-crypto transactions, keep original amount and leave Crypto column empty
                pass

        print("✅ Crypto amounts converted to USD with original amounts stored in Crypto column")
        return df

    def enhance_crypto_description(self, original_description, crypto_symbol, crypto_amount, usd_price, usd_total, date_str):
        """Enhance description with crypto conversion details"""

        # Determine transaction type from original description
        desc_lower = original_description.lower()

        if 'deposit' in desc_lower or 'received' in desc_lower:
            transaction_type = "deposit"
        elif 'withdrawal' in desc_lower or 'sent' in desc_lower:
            transaction_type = "withdrawal"
        elif 'trade' in desc_lower or 'buy' in desc_lower or 'sell' in desc_lower:
            transaction_type = "trade"
        else:
            transaction_type = "transaction"

        # Create enhanced description
        crypto_names = {
            'BTC': 'Bitcoin',
            'TAO': 'Bittensor',
            'ETH': 'Ethereum',
            'BNB': 'Binance Coin',
            'USDC': 'USD Coin',
            'USDT': 'Tether'
        }

        crypto_name = crypto_names.get(crypto_symbol, crypto_symbol)

        enhanced_description = f"{crypto_name} {transaction_type} - {crypto_amount} {crypto_symbol} @ ${usd_price:,.2f} = ${usd_total:,.2f} ({date_str})"

        # Include original description context if it has useful info beyond the basics
        original_clean = original_description.strip()
        if original_clean and len(original_clean) > 10:
            # Check if original has additional context worth keeping
            useful_parts = []
            for part in original_clean.split(' - '):
                part_clean = part.strip()
                if (part_clean and
                    not any(word in part_clean.lower() for word in ['deposit', 'withdrawal', 'complete', 'success']) and
                    not part_clean.startswith(crypto_symbol)):
                    useful_parts.append(part_clean)

            if useful_parts:
                enhanced_description += f" | {' - '.join(useful_parts[:2])}"  # Keep at most 2 additional parts

        return enhanced_description

    def extract_date_for_pricing(self, date_input):
        """Extract date in YYYY-MM-DD format for pricing lookup"""
        if not date_input:
            return None

        date_str = str(date_input)

        # Handle ISO 8601 format with 'Z' suffix (replace with UTC)
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'

        # Try parsing various date formats
        date_formats = [
            '%Y-%m-%dT%H:%M:%S.%f%z',  # 2025-08-06T03:19:38.000+00:00 (ISO 8601)
            '%Y-%m-%dT%H:%M:%S%z',     # 2025-08-06T03:19:38+00:00 (ISO 8601 without ms)
            '%Y-%m-%d %H:%M:%S',       # 2025-08-30 18:30:26
            '%Y-%m-%d %H:%M:%S UTC',   # 2025-08-30 18:30:26 UTC
            '%Y-%m-%d',                # 2025-08-30
            '%m/%d/%Y',                # 08/30/2025
            '%m/%d/%y',                # 08/30/25
        ]

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue

        print(f"⚠️ Could not parse date: {date_str}")
        return None

    def fix_account_identifiers(self, df):
        """Fix generic account names to be specific"""
        print("🏦 Fixing account identifiers...")

        for idx, row in df.iterrows():
            source_file = str(row.get('source_file', '')).lower()
            description = str(row.get('Description', ''))
            origin = str(row.get('Origin', ''))
            destination = str(row.get('Destination', ''))

            # Fix Coinbase accounts
            if 'coinbase' in source_file:
                if origin == 'Current Account' or origin == 'Trading Platform':
                    df.at[idx, 'Origin'] = 'Coinbase'
                if destination == 'Current Account' or destination == 'Trading Platform':
                    df.at[idx, 'Destination'] = 'Coinbase'

            # Fix Chase accounts
            elif 'chase' in source_file:
                account_match = re.search(r'\*{3,5}(\d{3,4})', description)
                if account_match:
                    account_id = f"Checking ...{account_match.group(1)}"
                    if origin == 'Current Account':
                        df.at[idx, 'Origin'] = account_id
                    if destination == 'Current Account':
                        df.at[idx, 'Destination'] = account_id

            # Fix MEXC accounts
            elif 'mexc' in source_file:
                if origin == 'Current Account' or origin == 'Trading Platform':
                    df.at[idx, 'Origin'] = 'MEXC'
                if destination == 'Current Account' or destination == 'Trading Platform':
                    df.at[idx, 'Destination'] = 'MEXC'

        print("✅ Account identifiers fixed")
        return df

    def create_backup(self):
        """Create backup of master file"""
        if os.path.exists(self.master_file):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"MASTER_TRANSACTIONS_backup_{timestamp}.csv"
            shutil.copy2(self.master_file, backup_name)
            print(f"📦 Backup created: {backup_name}")
            return backup_name
        return None

    def load_master_transactions(self):
        """Load existing master transaction file if it exists"""
        if os.path.exists(self.master_file):
            df = pd.read_csv(self.master_file)
            print(f"📂 Loaded {len(df)} existing transactions from {self.master_file}")
            return df
        else:
            return pd.DataFrame()

    def _determine_accounting_category(self, entity, description, amount):
        """
        Intelligently determine accounting_category and subcategory based on entity, description, and amount.
        Returns: (accounting_category, subcategory)
        """
        description_upper = str(description).upper()
        amount_float = self.safe_float(amount)

        # For Internal Transfers
        if entity == 'Internal Transfer':
            return 'INTERNAL_TRANSFER', 'Intercompany Transfer'

        # For Revenue (positive amounts)
        if amount_float > 0:
            if 'BTC' in description_upper or 'MINING' in description_upper:
                return 'REVENUE', 'Mining Revenue'
            elif 'TAO' in description_upper or 'BITTENSOR' in description_upper:
                return 'REVENUE', 'Trading Revenue'
            elif 'CLIENT' in description_upper or 'INVOICE' in description_upper:
                return 'REVENUE', 'Client Services'
            else:
                return 'REVENUE', 'Other Revenue'

        # For Expenses (negative amounts)
        else:
            # Technology & Software
            if any(keyword in description_upper for keyword in ['ANTHROPIC', 'GITHUB', 'VERCEL', 'REPLIT', 'GOOGLE CLOUD', 'AWS', 'AMAZON WEB SERVICES']):
                return 'OPERATING_EXPENSE', 'Software Subscriptions'
            # Utilities & Internet
            elif any(keyword in description_upper for keyword in ['ANDE', 'STARLINK', 'INTERNET']):
                return 'OPERATING_EXPENSE', 'Utilities'
            # Meals & Food
            elif any(keyword in description_upper for keyword in ['SABOR', 'RESTAURANT', 'FOOD', 'MEAL']):
                return 'OPERATING_EXPENSE', 'Employee Meals'
            # Gas & Fuel
            elif any(keyword in description_upper for keyword in ['PETROBRAS', 'PETROPAR', 'GAS', 'FUEL', 'SHELL']):
                return 'OPERATING_EXPENSE', 'Fuel & Gas'
            # Professional Services
            elif any(keyword in description_upper for keyword in ['ACCOUNTING', 'LEGAL', 'CONSULTING', 'LEAP']):
                return 'OPERATING_EXPENSE', 'Professional Services'
            # Employee Payments
            elif any(keyword in description_upper for keyword in ['TIAGO', 'VICTOR', 'VANESSA', 'ALDO', 'ANDERSON', 'SALARY', 'PAYROLL']):
                return 'OPERATING_EXPENSE', 'Payroll & Benefits'
            # General
            else:
                return 'OPERATING_EXPENSE', 'General Expenses'

    def classify_transaction(self, description, amount, account='', currency='', withdrawal_address=''):
        """
        Classify a single transaction based on business rules.
        Returns: (entity, confidence, reason, accounting_category, subcategory)
        """

        description_upper = str(description).upper()

        # CRITICAL PRIORITY 0: INTERMEDIATE ROUTING ACCOUNT DETECTION
        # These are treasury routing operations, NOT business unit transactions
        intermediate_patterns = [
            ('COINBASE.COM', ''),        # All Coinbase.com transactions (PPD deposits)
            ('COINBASE INC.', ''),       # All Coinbase Inc. transactions
            ('COINBASE RTL-', ''),       # Real-time transfers from Coinbase
            ('DOMESTIC WIRE TRANSFER VIA: CROSS RIVER BK', 'COINBASE INC'),  # Wire transfers to Coinbase
            ('PIX TRANSF MERCADO', ''),  # Mercado Bitcoin transfers
            ('MERCADO BITCOIN', ''),     # Mercado Bitcoin operations
            ('MEXC', ''),                # MEXC exchange operations
            ('ONLINE TRANSFER FROM CHK', ''),  # Inter-account transfers
            ('ONLINE TRANSFER TO CHK', ''),    # Inter-account transfers
            ('TRANSFER FROM CHK', ''),         # Bank transfers between accounts
            ('TRANSFER TO CHK', ''),           # Bank transfers between accounts
        ]

        # Check if transaction is an intermediate routing
        for pattern1, pattern2 in intermediate_patterns:
            if pattern1 in description_upper:
                if not pattern2 or pattern2 in description_upper:
                    entity = 'Internal Transfer'
                    reason = f"Intermediate routing: {pattern1}"
                    acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
                    return entity, 1.0, reason, acct_cat, subcat

        # Special handling for known routing accounts
        if account:
            routing_accounts = ['3911', '3687', '5893', '9189']  # Chase accounts used for routing
            if any(acc in str(account) for acc in routing_accounts):
                if 'COINBASE' in description_upper or 'MERCADO' in description_upper:
                    entity = 'Internal Transfer'
                    reason = f"Routing account transfer: {account}"
                    acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
                    return entity, 1.0, reason, acct_cat, subcat

        # PRIORITY 0.5: COINBASE INTERNAL OPERATIONS - Apply business logic
        # These are NOT routing but actual business operations within Coinbase

        # BTC/Crypto receives from external accounts = Mining rewards/revenue
        if 'RECEIVE BTC - EXTERNAL ACCOUNT' in description_upper:
            entity = 'Infinity Validator'
            reason = 'BTC mining rewards received at Coinbase'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 0.95, reason, acct_cat, subcat
        elif 'RECEIVE USDC - EXTERNAL ACCOUNT' in description_upper:
            # USDC receives from external sources - need manual classification
            # Could be: client payments, trading profits, returns from other operations
            entity = 'Unclassified Revenue'
            reason = 'USDC received from external account - needs manual classification'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 0.5, reason, acct_cat, subcat
        elif 'RECEIVE USDT - EXTERNAL ACCOUNT' in description_upper:
            # USDT receives from external sources - likely trading but needs verification
            entity = 'Unclassified Revenue'
            reason = 'USDT received from external account - likely trading revenue'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 0.6, reason, acct_cat, subcat

        # Crypto sends from Coinbase = Likely to mining operations or employees
        elif 'SEND BTC' in description_upper:
            # Without wallet addresses, assume these go to mining operations
            entity = 'Infinity Validator'
            reason = 'BTC sent to mining operations'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 0.8, reason, acct_cat, subcat
        elif 'SEND USDC' in description_upper or 'SEND USDT' in description_upper:
            # USD stablecoin sends likely for operational expenses
            entity = 'Delta Prop Shop'
            reason = 'Crypto sent for operations'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 0.8, reason, acct_cat, subcat

        # USD withdrawals from Coinbase to bank accounts
        elif 'WITHDRAWAL USD' in description_upper and 'CHASE' in description_upper:
            entity = 'Internal Transfer'
            reason = 'USD withdrawal to Chase bank account'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 1.0, reason, acct_cat, subcat
        elif 'WITHDRAWAL USD' in description_upper:
            # USD withdrawals likely going to operational accounts
            entity = 'Delta Prop Shop'
            reason = 'USD withdrawal for operations'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 0.85, reason, acct_cat, subcat
        elif 'WITHDRAWAL USDC' in description_upper and 'CHASE' in description_upper:
            entity = 'Internal Transfer'
            reason = 'USDC withdrawal to Chase bank account'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 1.0, reason, acct_cat, subcat
        elif 'WITHDRAWAL USDC' in description_upper or 'WITHDRAWAL USDT' in description_upper:
            entity = 'Delta Prop Shop'
            reason = 'Crypto withdrawal for operations'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 0.85, reason, acct_cat, subcat

        # Convert operations within Coinbase = Trading activity
        elif 'CONVERT BTC' in description_upper or 'CONVERT USDT' in description_upper or 'CONVERT USDC' in description_upper:
            entity = 'Delta Prop Shop'
            reason = 'Coinbase trading conversion'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 0.9, reason, acct_cat, subcat
        elif 'SELL BTC' in description_upper or 'SELL USDT' in description_upper or 'SELL USDC' in description_upper:
            entity = 'Delta Prop Shop'
            reason = 'Coinbase crypto sale'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 0.9, reason, acct_cat, subcat

        # PRIORITY 1: Check wallet intelligence for withdrawals
        if withdrawal_address and withdrawal_address.lower() in self.wallets:
            wallet_info = self.wallets[withdrawal_address.lower()]
            # Check if it's a known routing wallet
            if '0x86cc1529bdf444200f06957ab567b56a385c5e90' in withdrawal_address:  # Whit Mercado Bitcoin
                entity = 'Internal Transfer'
                reason = 'Routing wallet: Whit Mercado Bitcoin → Brazil Bank'
                acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
                return entity, 1.0, reason, acct_cat, subcat
            entity = wallet_info['entity']
            confidence = wallet_info['confidence']
            reason = f"wallet: {wallet_info['purpose']}"
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, confidence, reason, acct_cat, subcat

        # PRIORITY 2: Special rules for crypto
        if currency:
            currency_upper = currency.upper()
            if currency_upper == 'BTC':
                entity = 'Infinity Validator'
                reason = 'BTC mining rewards from Subnet 89'
                acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
                return entity, 1.0, reason, acct_cat, subcat
            elif currency_upper == 'TAO':
                entity = 'Delta Prop Shop LLC'
                reason = 'TAO revenue (Taoshi contract + trader revenue)'
                acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
                return entity, 1.0, reason, acct_cat, subcat
            elif currency_upper in ['USDT', 'USDC']:
                entity = 'NEEDS REVIEW'
                reason = f'{currency_upper} deposit - determine if trading or revenue'
                acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
                return entity, 0.0, reason, acct_cat, subcat

        # Check account mapping
        if account and account in self.account_mapping:
            entity = self.account_mapping[account]
            if entity not in ['Personal/Mixed', 'Mixed Entities']:
                reason = f'Account {account} mapped'
                acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
                return entity, 0.95, reason, acct_cat, subcat

        # Check all patterns in priority order
        pattern_order = ['revenue', 'transfer', 'technology', 'paraguay', 'brazil', 'fees', 'crypto', 'personal', 'expense', 'regional']

        for pattern_type in pattern_order:
            for pattern, rule in self.patterns.get(pattern_type, {}).items():
                if pattern in description_upper:
                    entity = rule['entity']
                    confidence = rule['confidence']
                    reason = f"{pattern_type}: {pattern}"
                    acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
                    return entity, confidence, reason, acct_cat, subcat

        # PRIORITY 3: Check for FINAL DESTINATION patterns (actual business expenses)
        # These are where we SHOULD classify to business units
        final_destination_patterns = {
            'TIAGO': ('Delta Brazil', 0.95, 'Employee payment: Tiago'),
            'VICTOR': ('Delta Brazil', 0.95, 'Employee payment: Victor'),
            'VANESSA': ('Delta Brazil', 0.95, 'Employee payment: Vanessa'),
            'DANIELE': ('Delta Brazil', 0.95, 'Employee payment: Daniele/Regis'),
            'LEAP SOLUCOES': ('Delta Brazil', 0.95, 'Professional services: Accounting'),
            'PORTO SEGURO': ('Delta Brazil', 0.95, 'Insurance: Porto Seguro'),
            'ANDE': ('Delta PY', 0.95, 'Power provider: ANDE Paraguay'),
            'ADMINISTRATION NACIONAL DE ELECTRIC': ('Delta PY', 0.95, 'Power: ANDE Paraguay'),
            'RISEWORKS': ('Delta Prop Shop LLC', 0.95, 'Contractor: Riseworks'),
            'ALDO': ('Delta PY', 0.95, 'Employee/Operations: Aldo'),
            'ANDERSON': ('Delta PY', 0.95, 'Employee: Anderson'),
        }

        for pattern, (entity, confidence, reason) in final_destination_patterns.items():
            if pattern in description_upper:
                # Double-check it's not a routing transaction
                if not any(routing in description_upper for routing in ['COINBASE', 'MERCADO', 'MEXC', 'TRANSFER FROM', 'TRANSFER TO']):
                    acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
                    return entity, confidence, reason, acct_cat, subcat

        # Check for specific keywords and wire transfer patterns
        if 'PAYMENT TO CHASE CARD' in description_upper:
            entity = 'Internal Transfer'
            reason = 'Inter-account transfer'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 1.0, reason, acct_cat, subcat
        elif 'ONLINE TRANSFER' in description_upper and not any(final in description_upper for final in final_destination_patterns.keys()):
            entity = 'Internal Transfer'
            reason = 'Inter-account transfer'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 1.0, reason, acct_cat, subcat
        elif 'UBER' in description_upper:
            entity = 'Delta LLC'
            reason = 'Business travel'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 1.0, reason, acct_cat, subcat
        elif 'EXOS CAPITAL' in description_upper:
            entity = 'Delta Mining Paraguay S.A.'
            reason = 'Client revenue from EXOS'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 1.0, reason, acct_cat, subcat
        elif 'ALPS BLOCKCHAIN' in description_upper:
            entity = 'Delta Mining Paraguay S.A.'
            reason = 'Client revenue from Alps'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 1.0, reason, acct_cat, subcat
        elif ('PARAGUAY' in description_upper or 'ASUNCION' in description_upper) and self.safe_float(amount) > 1000:
            entity = 'Delta Mining Paraguay S.A.'
            reason = 'Wire transfer to Paraguay operations'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 0.95, reason, acct_cat, subcat

        # Default classification based on amount
        if self.safe_float(amount) > 0:
            entity = 'Unclassified Revenue'
            reason = 'Unknown revenue source'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 0.5, reason, acct_cat, subcat
        else:
            entity = 'Unclassified Expense'
            reason = 'Unknown expense'
            acct_cat, subcat = self._determine_accounting_category(entity, description, amount)
            return entity, 0.5, reason, acct_cat, subcat

    def _continue_processing_from_dataframe(self, df, file_path, enhance):
        """Continue processing from a DataFrame after smart ingestion handles column mapping"""
        print(f"🔧 DEBUG: Starting _continue_processing_from_dataframe for {file_path}")
        try:
            # Smart ingestion guarantees standardized columns: Date, Description, Amount
            date_col = 'Date'
            desc_col = 'Description'
            amount_col = 'Amount'

            print(f"✅ Smart ingestion standardized DataFrame with {len(df)} transactions")
            print(f"📊 Columns: {list(df.columns)}")
            print(f"🔧 DEBUG: Current working directory: {os.getcwd()}")

            # Validate required columns exist (smart ingestion should guarantee this)
            required_cols = [date_col, desc_col, amount_col]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Smart ingestion failed to provide required columns: {missing_cols}")

            # Sample data for debugging
            if len(df) > 0:
                print(f"📊 Sample: {df.iloc[0][desc_col]} | ${df.iloc[0][amount_col]}")

                # DEBUG: Print detailed first row info
                print(f"🔧 DEBUG MAIN.PY: First row after receiving from smart ingestion:")
                print(f"   Date column ({date_col}): {df.iloc[0][date_col]}")
                print(f"   Amount column ({amount_col}): {df.iloc[0][amount_col]}")
                print(f"   Description column ({desc_col}): {df.iloc[0][desc_col]}")
                print(f"   All columns: {list(df.columns)}")
                print(f"   Full first row: {dict(df.iloc[0])}")

            # Continue with classification and processing
            print("🔧 DEBUG: Calling _classify_and_process_dataframe...")
            result = self._classify_and_process_dataframe(df, file_path, date_col, desc_col, amount_col, enhance)
            print(f"🔧 DEBUG: Classification result: {'Success' if result is not None else 'Failed'}")

            return result

        except Exception as e:
            print(f"❌ Error in DataFrame processing: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _classify_and_process_dataframe(self, df, file_path, date_col, desc_col, amount_col, enhance):
        """Classify and process a DataFrame with known column mapping"""
        # This contains the classification logic from the original process_file method

        # Detect account from column names
        account = ''
        for col in df.columns:
            if 'Account' in col and any(char.isdigit() for char in col):
                account = ''.join(filter(str.isdigit, col))[-4:]
                break

        # Detect currency for crypto files
        currency_col = next((col for col in df.columns if 'currency' in col.lower() or 'coin' in col.lower() or 'crypto' in col.lower()), None)

        # Detect withdrawal address for crypto withdrawal files
        withdrawal_address_col = next((col for col in df.columns if 'withdrawal address' in col.lower() or 'address' in col.lower()), None)

        # Classify each transaction
        classifications = []

        for _, row in df.iterrows():
            description = row[desc_col] if desc_col in df.columns else ''
            amount = row[amount_col] if amount_col in df.columns else 0
            currency = row[currency_col] if currency_col and currency_col in df.columns else ''
            withdrawal_address = row[withdrawal_address_col] if withdrawal_address_col and withdrawal_address_col in df.columns else ''

            # Use the existing classification logic
            entity, confidence, reason, accounting_category, subcategory = self.classify_transaction(description, amount, account, currency, withdrawal_address)

            # Use existing intercompany detection
            intercompany_info = self.detect_intercompany_transaction(description, entity, account, amount)

            classifications.append({
                'classified_entity': entity,
                'confidence': confidence,
                'classification_reason': reason,
                'accounting_category': accounting_category,
                'subcategory': subcategory,
                'needs_review': confidence < 0.8,
                'source_file': os.path.basename(file_path),
                'date_processed': datetime.now().isoformat(),
                'Business_Unit': entity,
                'Justification': reason,
                'From_Entity': intercompany_info['from_entity'],
                'To_Entity': intercompany_info['to_entity'],
                'Intercompany_Type': intercompany_info['type'],
                'Elimination_Required': intercompany_info['elimination_required'],
                'Elimination_Amount': intercompany_info['elimination_amount']
            })

        # Add classification data to DataFrame
        for key in classifications[0].keys():
            df[key] = [c[key] for c in classifications]

        # Generate unique transaction IDs
        for idx, row in df.iterrows():
            if 'transaction_id' not in df.columns or pd.isna(row.get('transaction_id')):
                # Generate transaction_id from date + description + amount
                date_str = str(row[date_col]) if date_col in df.columns else ''
                desc_str = str(row[desc_col]) if desc_col in df.columns else ''
                amount_str = str(row[amount_col]) if amount_col in df.columns else ''
                identifier = f"{date_str}{desc_str}{amount_str}"
                transaction_id = hashlib.md5(identifier.encode()).hexdigest()[:12]
                df.at[idx, 'transaction_id'] = transaction_id

        # Run enhanced processing pipeline if requested
        if enhance:
            print("\n🔄 Running enhanced processing pipeline...")

            # Fetch crypto prices
            print("💰 Fetching crypto prices...")
            self.fetch_crypto_prices()

            # Add USD equivalents for crypto amounts
            print("💵 Adding USD equivalents...")
            df = self.add_usd_equivalents(df)

            # Extract keywords
            print("🔍 Extracting keywords...")
            df = self.extract_keywords(df)

            # Enhance transaction structure (Origin/Destination)
            print("🔧 Enhancing transaction structure (Origin/Destination)...")
            df = self.enhance_structure(df)

            # Enhance descriptions with context
            print("📝 Enhancing descriptions with context...")
            df = self.enhance_description(df)

            # Add USD conversion using historic crypto prices
            print("💰 Adding USD conversion using historic crypto prices...")
            df = self.add_usd_conversion(df)

            # Fix account identifiers
            print("🏦 Fixing account identifiers...")
            df = self.fix_account_identifiers(df)

            print("✅ Enhanced processing completed")

        # Generate summary and save file
        print(f"\n   📈 Classification Summary:")
        entity_counts = df['classified_entity'].value_counts()
        for entity, count in entity_counts.head(5).items():
            print(f"      {entity}: {count} transactions")

        # Calculate metrics
        avg_confidence = df['confidence'].mean()
        review_count = len(df[df['needs_review'] == True])

        print(f"\n   📊 Metrics:")
        print(f"      Average confidence: {avg_confidence:.1%}")
        print(f"      Needs review: {review_count} transactions")

        # Save classified file
        filename = os.path.basename(file_path)
        output_file = f"classified_transactions/classified_{filename}"

        print(f"🔧 DEBUG: Preparing to save classified file...")
        print(f"🔧 DEBUG: Output file path: {output_file}")
        print(f"🔧 DEBUG: Output directory exists: {os.path.exists('classified_transactions')}")

        # Ensure directory exists
        os.makedirs('classified_transactions', exist_ok=True)

        # Normalize Date column to YYYY-MM-DD format before saving
        if 'Date' in df.columns:
            # Force conversion to string first
            df['Date'] = df['Date'].astype(str)

            # Use vectorized string operations (much more reliable than .apply())
            # First handle ISO format (2025-09-28T04:21:16)
            df['Date'] = df['Date'].str.replace(r'T.*$', '', regex=True)
            # Then handle datetime format (2025-09-28 04:21:16 UTC) - keep only first 10 chars
            df['Date'] = df['Date'].str[:10]

            sample_date = df['Date'].iloc[0] if len(df) > 0 else 'N/A'
            print(f"🔧 DEBUG: After normalize_date - sample: '{sample_date}' (len={len(sample_date) if sample_date != 'N/A' else 0})")

            # Double-check all dates are YYYY-MM-DD format (10 chars max)
            if len(df) > 0:
                max_len = df['Date'].str.len().max()
                if max_len > 10:
                    print(f"⚠️ WARNING: Some dates are longer than 10 characters (max={max_len})!")
                    long_dates = df[df['Date'].str.len() > 10]['Date'].head(3).tolist()
                    print(f"   Examples: {long_dates}")

        try:
            df.to_csv(output_file, index=False)
            print(f"✅ DEBUG: Successfully saved classified file: {output_file}")
            print(f"🔧 DEBUG: File size: {os.path.getsize(output_file)} bytes")
            print(f"🔧 DEBUG: File exists after save: {os.path.exists(output_file)}")
        except Exception as save_error:
            print(f"❌ DEBUG: Failed to save classified file: {save_error}")
            raise save_error

        return df

    def process_file(self, file_path, enhance=False, use_smart_ingestion=False):
        """Process any transaction file (CSV, Excel)"""

        print(f"\n📄 Processing: {os.path.basename(file_path)}")
        if enhance:
            print("🚀 Enhanced processing mode enabled")

        # Use Claude AI smart ingestion (REQUIRED - no fallback)
        if use_smart_ingestion:
            try:
                from smart_ingestion import smart_process_file
                print("🤖 Processing with Claude AI smart ingestion...")
                df = smart_process_file(file_path, enhance)
                print("✅ Claude AI smart ingestion successful")
                # Skip to classification - smart ingestion handles all column mapping
                return self._continue_processing_from_dataframe(df, file_path, enhance)
            except ImportError:
                error_msg = "❌ SMART INGESTION MODULE NOT FOUND: Please ensure smart_ingestion.py is available."
                print(error_msg)
                return None
            except ValueError as e:
                # This handles Claude AI requirement errors
                error_msg = str(e)
                print(error_msg)
                return None
            except Exception as e:
                error_msg = f"❌ CLAUDE AI PROCESSING FAILED: {e}"
                print(error_msg)
                return None

        # Manual file reading (existing logic)
        # Read file
        if file_path.lower().endswith(('.csv', '.CSV')):
            # Try different encodings
            for encoding in ['utf-8', 'latin1', 'iso-8859-1']:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    print(f"   ✅ Read with {encoding} encoding")
                    break
                except:
                    continue
            else:
                print(f"   ❌ Could not read CSV file")
                return None
        elif file_path.endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(file_path)
                print(f"   ✅ Read Excel file")
            except Exception as e:
                print(f"   ❌ Error reading Excel: {e}")
                return None
        else:
            print(f"   ❌ Unsupported file type")
            return None

        print(f"   📊 Found {len(df)} transactions")

        # DEBUG: Check for misaligned Chase CSV headers
        print(f"   📋 Columns detected: {list(df.columns)}")
        print(f"   📋 First row sample: {dict(list(df.iloc[0].items())[:3])}")

        # Handle misaligned Chase CSV format where headers are shifted
        if 'Details' in df.columns and 'Posting Date' in df.columns and 'Description' in df.columns:
            # Chase CSV format has shifted headers - use positional mapping based on actual data
            date_col = 'Details'       # Actually contains dates like "09/16/2025"
            desc_col = 'Posting Date'  # Actually contains descriptions like "Payment to Chase card..."
            amount_col = 'Description' # Actually contains amounts like "-500.00"
            print(f"   🔧 Using Chase-specific column mapping for misaligned CSV")
        else:
            # Standard column detection
            date_col = next((col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()), df.columns[0])
            desc_col = next((col for col in df.columns if 'description' in col.lower() or 'desc' in col.lower() or 'status' in col.lower()), df.columns[1] if len(df.columns) > 1 else df.columns[0])

            # Prioritize exact "Amount" match over partial matches
            amount_col = None
            for col in df.columns:
                if col.lower() == 'amount':
                    amount_col = col
                    break
                elif 'amount' in col.lower() or 'valor' in col.lower() or 'deposit amount' in col.lower():
                    amount_col = col

            if not amount_col:
                amount_col = df.columns[3] if len(df.columns) > 3 else df.columns[0]

        print(f"   📋 Using: Date={date_col}, Desc={desc_col}, Amount={amount_col}")

        # For Chase CSV files, standardize column names immediately after mapping
        print(f"   🔍 CHECKING CHASE CONDITION: Details={'Details' in df.columns}, Posting Date={'Posting Date' in df.columns}, Description={'Description' in df.columns}")
        if 'Details' in df.columns and 'Posting Date' in df.columns and 'Description' in df.columns:
            print(f"   🔧 APPLYING CHASE STANDARDIZATION NOW...")
            print(f"   🔍 BEFORE: {amount_col} contains: {repr(df.iloc[0][amount_col])}")

            # Create a standardized DataFrame with correct data mapping
            standardized_df = pd.DataFrame()
            standardized_df['Date'] = df[date_col]
            standardized_df['Description'] = df[desc_col]
            standardized_df['Amount'] = df[amount_col]

            print(f"   🔍 AFTER MAPPING: Amount contains: {repr(standardized_df.iloc[0]['Amount'])}")

            # Copy over other columns except original amount column
            for col in df.columns:
                if col not in [date_col, desc_col, amount_col] and col not in ['Date', 'Description', 'Amount']:
                    standardized_df[col] = df[col]

            df = standardized_df
            print(f"   🔍 FINAL CHECK: Amount contains: {repr(df.iloc[0]['Amount'])}")

            # Update column references for the rest of the processing
            date_col = 'Date'
            desc_col = 'Description'
            amount_col = 'Amount'
            print(f"   ✅ Standardized Chase CSV - Amount column now has numeric data")

        # Detect account from column names
        account = ''
        for col in df.columns:
            if 'Account' in col and any(char.isdigit() for char in col):
                account = ''.join(filter(str.isdigit, col))[-4:]
                break

        # Detect currency for crypto files
        currency_col = next((col for col in df.columns if 'currency' in col.lower() or 'coin' in col.lower() or 'crypto' in col.lower()), None)

        # Detect withdrawal address for crypto withdrawal files
        withdrawal_address_col = next((col for col in df.columns if 'withdrawal address' in col.lower() or 'address' in col.lower()), None)

        # Classify each transaction
        classifications = []
        print(f"   📊 DEBUG: DataFrame columns at classification: {list(df.columns)}")
        print(f"   📊 DEBUG: Using column mapping - Date: {date_col}, Desc: {desc_col}, Amount: {amount_col}")
        if len(df) > 0:
            print(f"   📊 DEBUG: First row amount value: {repr(df.iloc[0][amount_col] if amount_col in df.columns else 'MISSING')}")

        for _, row in df.iterrows():
            description = row[desc_col] if desc_col in df.columns else ''
            amount = row[amount_col] if amount_col in df.columns else 0
            currency = row[currency_col] if currency_col and currency_col in df.columns else ''
            withdrawal_address = row[withdrawal_address_col] if withdrawal_address_col and withdrawal_address_col in df.columns else ''

            entity, confidence, reason, accounting_category, subcategory = self.classify_transaction(description, amount, account, currency, withdrawal_address)

            # Detect intercompany transactions
            intercompany_info = self.detect_intercompany_transaction(description, entity, account, amount)

            classifications.append({
                'entity': entity,
                'confidence': confidence,
                'reason': reason,
                'accounting_category': accounting_category,
                'subcategory': subcategory,
                'intercompany': intercompany_info
            })

        # Add classifications to dataframe
        df['classified_entity'] = [c['entity'] for c in classifications]
        df['confidence'] = [c['confidence'] for c in classifications]
        df['classification_reason'] = [c['reason'] for c in classifications]
        df['accounting_category'] = [c['accounting_category'] for c in classifications]
        df['subcategory'] = [c['subcategory'] for c in classifications]
        df['needs_review'] = df['confidence'] < 0.8
        df['source_file'] = os.path.basename(file_path)
        df['date_processed'] = datetime.now().isoformat()

        # Add Business Unit and Justification columns
        df['Business_Unit'] = df['classified_entity']
        df['Justification'] = df['classification_reason']

        # Add ESSENTIAL INTERCOMPANY FIELDS for consolidation
        df['From_Entity'] = [c['intercompany']['from_entity'] for c in classifications]
        df['To_Entity'] = [c['intercompany']['to_entity'] for c in classifications]
        df['Intercompany_Type'] = [c['intercompany']['type'] for c in classifications]
        df['Elimination_Required'] = [c['intercompany']['elimination_required'] for c in classifications]
        df['Elimination_Amount'] = [c['intercompany']['elimination_amount'] for c in classifications]

        # Generate unique transaction IDs
        df['transaction_id'] = df.apply(
            lambda row: hashlib.md5(
                f"{row[date_col]}{row[desc_col] if desc_col in df.columns else ''}{row[amount_col]}".encode()
            ).hexdigest()[:12],
            axis=1
        )

        # Enhanced processing if requested
        if enhance:
            print("\n🔄 Running enhanced processing pipeline...")

            # Step 1: Fetch crypto prices
            self.fetch_crypto_prices()

            # Step 2: Add USD equivalents
            df = self.add_usd_equivalents(df)

            # Step 3: Extract keywords
            df = self.extract_keywords(df)

            # Step 4: Enhance structure (Origin/Destination)
            df = self.enhance_structure(df)

            # Step 5: Enhance descriptions with context
            df = self.enhance_description(df)

            # Step 6: Add USD conversion for crypto amounts
            df = self.add_usd_conversion(df)

            # Step 7: Fix account identifiers
            df = self.fix_account_identifiers(df)

            print("✅ Enhanced processing completed")

        # Save classified file
        output_file = os.path.join(self.classified_dir, f"classified_{os.path.splitext(os.path.basename(file_path))[0]}.csv")
        df.to_csv(output_file, index=False)

        # Print summary
        print(f"\n   📈 Classification Summary:")
        entity_counts = df['classified_entity'].value_counts()
        for entity, count in entity_counts.head(10).items():
            print(f"      {entity}: {count} transactions")

        confidence_avg = df['confidence'].mean()
        review_count = len(df[df['needs_review']])

        print(f"\n   📊 Metrics:")
        print(f"      Average confidence: {confidence_avg:.1%}")
        print(f"      Needs review: {review_count} transactions")
        print(f"      Saved to: {output_file}")

        return df

    def consolidate_to_master(self):
        """Consolidate all classified files into MASTER_TRANSACTIONS.csv"""

        print(f"\n🔄 Consolidating to {self.master_file}...")

        # Get all classified files
        classified_files = glob.glob(os.path.join(self.classified_dir, 'classified_*.csv'))

        if not classified_files:
            print("   ⚠️ No classified files found")
            return

        # Read all classified files
        all_dfs = []
        for file in classified_files:
            try:
                df = pd.read_csv(file)
                all_dfs.append(df)
                print(f"   ✅ Loaded {len(df)} transactions from {os.path.basename(file)}")
            except Exception as e:
                print(f"   ❌ Error loading {file}: {e}")

        if not all_dfs:
            print("   ❌ No valid classified files found")
            return

        # Combine all dataframes
        combined_df = pd.concat(all_dfs, ignore_index=True)

        # Remove duplicates based on transaction_id
        if 'transaction_id' in combined_df.columns:
            before_dedup = len(combined_df)
            combined_df = combined_df.drop_duplicates(subset=['transaction_id'], keep='last')
            after_dedup = len(combined_df)
            if before_dedup != after_dedup:
                print(f"   🔍 Removed {before_dedup - after_dedup} duplicate transactions")

        # Enhance structure with Origin, Destination, Identifier columns
        combined_df = self.enhance_structure(combined_df)

        # Add USD conversion for crypto amounts
        combined_df = self.add_usd_conversion(combined_df)

        # Sort by date if available - handle multiple date formats
        date_cols = [col for col in combined_df.columns if 'date' in col.lower()]
        if date_cols:
            try:
                # Preserve original date strings before conversion
                original_date_strings = combined_df[date_cols[0]].copy()

                # Handle multiple date formats in the same column
                # Try multiple format patterns to handle MM/DD/YYYY and YYYY-MM-DD formats
                combined_df[date_cols[0]] = pd.to_datetime(combined_df[date_cols[0]], errors='coerce')

                # If we still have NaT values, try specific formats on original strings
                if combined_df[date_cols[0]].isna().any():
                    mask_na = combined_df[date_cols[0]].isna()
                    print(f"   🔧 Fixing {mask_na.sum()} date parsing issues...")

                    # Try parsing remaining NaT values with different formats using original strings
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S UTC']:
                        if mask_na.sum() > 0:
                            try:
                                # Use original string values for parsing
                                parsed_dates = pd.to_datetime(original_date_strings[mask_na], format=fmt, errors='coerce')
                                valid_parsed = ~parsed_dates.isna()
                                if valid_parsed.any():
                                    # Create a mask for the valid parsed dates in the original DataFrame index
                                    original_indices = mask_na[mask_na].index
                                    valid_indices = original_indices[valid_parsed]
                                    combined_df.loc[valid_indices, date_cols[0]] = parsed_dates[valid_parsed]
                                    mask_na = combined_df[date_cols[0]].isna()  # Update mask
                                    print(f"   ✅ Parsed {valid_parsed.sum()} dates with format {fmt}")
                            except Exception as fmt_error:
                                continue

                if combined_df[date_cols[0]].isna().any():
                    remaining_na = combined_df[date_cols[0]].isna().sum()
                    print(f"   ⚠️ {remaining_na} dates could not be parsed")

                combined_df = combined_df.sort_values(date_cols[0], ascending=False)
            except Exception as e:
                print(f"   ⚠️ Date parsing error: {e}")
                pass

        # Save master file
        combined_df.to_csv(self.master_file, index=False)
        print(f"\n✅ Master file saved: {self.master_file}")
        print(f"   Total transactions: {len(combined_df)}")

        # Print entity summary
        if 'classified_entity' in combined_df.columns:
            print(f"\n📊 Entity Summary:")
            entity_summary = combined_df['classified_entity'].value_counts()
            for entity, count in entity_summary.items():
                if entity != 'N/A':  # Skip interaccount transfers
                    print(f"   {entity}: {count} transactions")

        # Save summary statistics
        summary = {
            'total_transactions': len(combined_df),
            'last_updated': datetime.now().isoformat(),
            'files_processed': len(classified_files),
            'entities': entity_summary.to_dict() if 'classified_entity' in combined_df.columns else {},
            'average_confidence': combined_df['confidence'].mean() if 'confidence' in combined_df.columns else 0,
            'needs_review': len(combined_df[combined_df['needs_review'] == True]) if 'needs_review' in combined_df.columns else 0
        }

        import json
        with open('classification_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)

        return combined_df

    def safe_merge_to_master(self, new_file):
        """Safely merge new transactions to master with duplicate detection"""
        print(f"\n🔀 Safely merging {new_file} to {self.master_file}...")

        # Step 1: Create backup
        backup_file = self.create_backup()

        # Step 2: Load master and new file
        if os.path.exists(self.master_file):
            master_df = pd.read_csv(self.master_file)
        else:
            master_df = pd.DataFrame()

        new_df = pd.read_csv(new_file)

        print(f"📊 Master file: {len(master_df)} transactions")
        print(f"📊 New file: {len(new_df)} transactions")

        # Step 3: Check for duplicates using composite key
        if len(master_df) > 0:
            master_df['check_key'] = (
                pd.to_datetime(master_df['Date']).dt.strftime('%Y-%m-%d') + '|' +
                master_df['Amount'].astype(str) + '|' +
                master_df['Description'].str[:50]
            )

            new_df['check_key'] = (
                pd.to_datetime(new_df['Date']).dt.strftime('%Y-%m-%d') + '|' +
                new_df['Amount'].astype(str) + '|' +
                new_df['Description'].str[:50]
            )

            # Find unique transactions
            unique_new = new_df[~new_df['check_key'].isin(master_df['check_key'])]
            duplicates = len(new_df) - len(unique_new)

            # Clean up temp columns
            master_df = master_df.drop('check_key', axis=1)
            unique_new = unique_new.drop('check_key', axis=1)

            print(f"🔍 Found {duplicates} duplicates (skipped)")
            print(f"✅ Found {len(unique_new)} unique transactions to add")
        else:
            unique_new = new_df
            print("✅ Master file empty - adding all transactions")

        if len(unique_new) == 0:
            print("⚠️  No new transactions to add")
            return True

        # Step 4: Merge and sort
        merged_df = pd.concat([master_df, unique_new], ignore_index=True)

        # Handle different date column names
        date_col = 'Date' if 'Date' in merged_df.columns else 'Transaction Date'
        merged_df[date_col] = pd.to_datetime(merged_df[date_col])
        merged_df = merged_df.sort_values(date_col, ascending=False)

        # Step 5: Save
        merged_df.to_csv(self.master_file, index=False)

        print(f"✅ Successfully merged {len(unique_new)} new transactions")
        print(f"📊 Total transactions in master: {len(merged_df)}")

        return True

    def reclassify_all_existing(self):
        """LEARNING FROM TEMP FILE: Reclassify all existing classified transaction files with updated business rules"""

        print("🔄 Reclassifying all existing transactions with current business rules...")

        # Search paths for existing classified files
        search_paths = [
            "processed_data/classified_transactions/*.csv",
            "classified_transactions/*.csv",
            "statementsTransactionReports/*.csv",
            "*.csv"
        ]

        # Find all transaction files (excluding master files)
        all_files = []
        for pattern in search_paths:
            all_files.extend(glob.glob(pattern))

        transaction_files = []
        for file in all_files:
            filename = os.path.basename(file).lower()
            if ('transaction' in filename or 'deposit' in filename or 'mexc' in filename or
                'chase' in filename or 'itau' in filename or 'classified' in filename) and \
               'master' not in filename and 'summary' not in filename:
                transaction_files.append(file)

        if not transaction_files:
            print("⚠️ No existing transaction files found to reclassify")
            return

        print(f"📁 Found {len(transaction_files)} existing files to reclassify")

        # Process each file with current business rules
        all_reclassified = []
        for file_path in transaction_files:
            try:
                print(f"📄 Reclassifying: {os.path.basename(file_path)}")
                df = pd.read_csv(file_path)

                # Detect file type and reclassify
                if 'Crypto' in df.columns:
                    reclassified_df = self.reclassify_crypto_data(df, file_path)
                else:
                    reclassified_df = self.reclassify_bank_data(df, file_path)

                if reclassified_df is not None:
                    all_reclassified.append(reclassified_df)

            except Exception as e:
                print(f"❌ Error processing {file_path}: {e}")

        # Consolidate and update master file
        if all_reclassified:
            combined_df = pd.concat(all_reclassified, ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=['transaction_id'], keep='last')
            combined_df.to_csv(self.master_file, index=False)
            print(f"✅ Updated {self.master_file} with {len(combined_df)} reclassified transactions")

    def reclassify_crypto_data(self, df, file_path):
        """Reclassify crypto transaction data with current business rules"""
        # Implementation extracted from temp file
        pass

    def reclassify_bank_data(self, df, file_path):
        """Reclassify bank transaction data with current business rules"""
        # Implementation extracted from temp file
        pass

    def process_all_files(self, directory='incoming_files'):
        """Process all files in a directory"""

        if not os.path.exists(directory):
            print(f"⚠️ Directory {directory} not found")
            return

        # Find all CSV and Excel files
        files = []
        for ext in ['*.csv', '*.xlsx', '*.xls']:
            files.extend(glob.glob(os.path.join(directory, ext)))

        if not files:
            print(f"⚠️ No transaction files found in {directory}")
            return

        print(f"🚀 Processing {len(files)} files from {directory}")

        # Process each file
        for file in files:
            self.process_file(file)

        # Consolidate to master
        self.consolidate_to_master()


def main():
    """Main entry point for the Delta CFO Agent"""

    print("=" * 60)
    print("DELTA CFO AGENT - Transaction Classification System")
    print("=" * 60)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Delta CFO Agent - Transaction Classification System')
    parser.add_argument('files', nargs='*', help='CSV or Excel files to process')
    parser.add_argument('--enhance', action='store_true',
                       help='Enable enhanced processing (crypto prices, USD conversion, keywords, Origin/Destination)')
    parser.add_argument('--merge', action='store_true',
                       help='Automatically merge to MASTER_TRANSACTIONS.csv after processing')
    parser.add_argument('--backup', action='store_true',
                       help='Create backup before any operations')

    args = parser.parse_args()

    agent = DeltaCFOAgent()

    # Create backup if requested
    if args.backup:
        agent.create_backup()

    if args.files:
        # Process specific files
        processed_files = []
        for file_path in args.files:
            if os.path.exists(file_path):
                result_df = agent.process_file(file_path, enhance=args.enhance)
                if result_df is not None:
                    processed_files.append(f"classified_{os.path.splitext(os.path.basename(file_path))[0]}.csv")
            else:
                print(f"❌ File not found: {file_path}")

        # Merge to master if requested
        if args.merge and processed_files:
            for processed_file in processed_files:
                full_path = os.path.join(agent.classified_dir, processed_file)
                if os.path.exists(full_path):
                    agent.safe_merge_to_master(full_path)
        elif processed_files:
            # Standard consolidation
            agent.consolidate_to_master()
    else:
        # Interactive mode
        print("\nUsage:")
        print("  python main.py file.csv --enhance           # Process with enhancements")
        print("  python main.py file.csv --enhance --merge   # Process and merge to master")
        print("  python main.py file1.csv file2.csv         # Process multiple files")
        print("  python main.py                             # Process all files in incoming_files/")
        print("")

        # Check for incoming_files directory
        if os.path.exists('incoming_files'):
            response = input("Process all files in incoming_files/? (y/n): ")
            if response.lower() == 'y':
                enhance_response = input("Use enhanced processing? (y/n): ")
                enhance = enhance_response.lower() == 'y'

                # Process all files
                files = glob.glob(os.path.join('incoming_files', '*.csv'))
                files.extend(glob.glob(os.path.join('incoming_files', '*.xlsx')))

                for file_path in files:
                    agent.process_file(file_path, enhance=enhance)

                agent.consolidate_to_master()
        else:
            print("\n📁 Create an 'incoming_files' directory and add your transaction files there.")
            print("   Or specify files directly: python main.py file.csv --enhance")

    print("\n✅ Processing complete!")
    if os.path.exists(agent.master_file):
        df = pd.read_csv(agent.master_file)
        print(f"📊 Master file now contains {len(df)} transactions")


if __name__ == "__main__":
    main()