#!/usr/bin/env python3
"""
Delta Business Intelligence Classifier
Classificação específica para as empresas Delta baseada em conhecimento de negócio
"""

from typing import Dict, Any, List, Tuple
import re
from decimal import Decimal
from datetime import date, datetime

class DeltaBusinessClassifier:
    """
    Classificador inteligente específico para as empresas Delta
    Baseado no conhecimento do negócio para classificação precisa
    """

    def __init__(self):
        # Delta Business Units
        self.business_units = {
            'Delta LLC': 'US Holding Company - Main operations',
            'Delta Prop Shop LLC': 'Trading Operations - TAO, Crypto',
            'Infinity Validator': 'Bitcoin Mining - Subnet 89',
            'Delta Mining Paraguay S.A.': 'Paraguay Operations',
            'Delta Brazil': 'Brazil Operations',
            'Personal': 'Owner Personal Expenses'
        }

        # Initialize classification rules
        self._init_vendor_patterns()
        self._init_category_patterns()
        self._init_crypto_patterns()
        self._init_amount_thresholds()

    def _init_vendor_patterns(self):
        """Initialize vendor-to-business-unit mapping patterns"""
        self.vendor_patterns = {
            # Technology & Cloud Services → Delta LLC
            'Delta LLC': [
                r'aws.*amazon',
                r'microsoft.*azure',
                r'google.*cloud',
                r'github',
                r'anthropic',
                r'openai',
                r'vercel',
                r'netlify',
                r'cloudflare',
                r'digital.*ocean',
                r'software',
                r'saas',
                r'api',
                r'subscription'
            ],

            # Trading & Crypto Operations → Delta Prop Shop LLC
            'Delta Prop Shop LLC': [
                r'coinbase',
                r'binance',
                r'mexc',
                r'kraken',
                r'trading',
                r'exchange',
                r'taoshi',
                r'bittensor',
                r'crypto.*platform',
                r'defi'
            ],

            # Mining Operations → Infinity Validator
            'Infinity Validator': [
                r'mining.*pool',
                r'validator',
                r'subnet.*89',
                r'bitcoin.*mining',
                r'btc.*pool',
                r'mining.*farm',
                r'asic',
                r'miner'
            ],

            # Paraguay Operations → Delta Mining Paraguay S.A.
            'Delta Mining Paraguay S.A.': [
                r'ande',
                r'copaco',
                r'paraguay',
                r'asuncion',
                r'administration.*nacional.*electric',
                r'aldo',
                r'anderson',
                r'exos.*capital',
                r'alps.*blockchain'
            ],

            # Brazil Operations → Delta Brazil
            'Delta Brazil': [
                r'brasil',
                r'brazil',
                r'porto.*seguro',
                r'nubank',
                r'itau',
                r'tiago',
                r'victor',
                r'vanessa',
                r'daniele',
                r'leap.*solucoes'
            ]
        }

    def _init_category_patterns(self):
        """Initialize expense category patterns"""
        self.category_patterns = {
            'Technology Expenses': [
                r'aws', r'amazon.*web.*services',
                r'microsoft', r'azure',
                r'google.*cloud',
                r'github', r'gitlab',
                r'anthropic', r'openai',
                r'software', r'saas',
                r'api', r'subscription',
                r'hosting', r'cloud'
            ],

            'Utilities': [
                r'electric', r'electricity',
                r'power', r'energy',
                r'ande',
                r'copaco',
                r'internet',
                r'telecommunications',
                r'utility'
            ],

            'Insurance': [
                r'insurance',
                r'seguro',
                r'porto.*seguro',
                r'liability',
                r'coverage'
            ],

            'Professional Services': [
                r'legal', r'lawyer', r'attorney',
                r'accounting', r'accountant',
                r'consultant', r'consulting',
                r'professional.*services',
                r'leap.*solucoes'
            ],

            'Bank Fees': [
                r'bank.*fee',
                r'wire.*transfer',
                r'international.*transfer',
                r'service.*charge',
                r'overdraft',
                r'monthly.*service'
            ],

            'Travel Expenses': [
                r'airline', r'flight',
                r'hotel', r'accommodation',
                r'uber', r'taxi',
                r'transport', r'travel',
                r'airbnb'
            ],

            'Office Expenses': [
                r'office.*supplies',
                r'equipment',
                r'furniture',
                r'stationery',
                r'printer'
            ],

            'Mining Expenses': [
                r'mining.*equipment',
                r'asic', r'miner',
                r'cooling', r'ventilation',
                r'electricity.*mining'
            ]
        }

    def _init_crypto_patterns(self):
        """Initialize cryptocurrency detection patterns"""
        self.crypto_currencies = {
            'BTC': ['bitcoin', 'btc'],
            'TAO': ['tao', 'bittensor'],
            'ETH': ['ethereum', 'eth'],
            'USDC': ['usdc', 'usd.*coin'],
            'USDT': ['usdt', 'tether'],
            'BNB': ['bnb', 'binance.*coin'],
            'SOL': ['solana', 'sol']
        }

        self.crypto_vendors = [
            'coinbase', 'binance', 'mexc', 'kraken',
            'crypto', 'blockchain', 'defi',
            'mining', 'validator', 'staking'
        ]

    def _init_amount_thresholds(self):
        """Initialize amount-based classification thresholds"""
        self.amount_thresholds = {
            'high_value': 10000,      # $10K+ likely strategic/corporate
            'medium_value': 1000,     # $1K-10K operational
            'low_value': 100          # <$100 minor expenses
        }

    def classify_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main classification function
        Returns enhanced invoice data with Delta-specific classifications
        """
        vendor_name = invoice_data.get('vendor_name', '').lower()
        amount = float(invoice_data.get('total_amount', 0))
        currency = invoice_data.get('currency', 'USD').upper()
        description = invoice_data.get('processing_notes', '').lower()

        # Perform classifications
        business_unit = self._classify_business_unit(vendor_name, amount, currency, description)
        category = self._classify_category(vendor_name, description, business_unit)
        currency_type = self._detect_currency_type(currency, vendor_name, description)
        vendor_type = self._classify_vendor_type(vendor_name)
        client_info = self._extract_client_info(vendor_name, description)

        # Calculate confidence scores
        bu_confidence = self._calculate_business_unit_confidence(vendor_name, business_unit, amount)
        cat_confidence = self._calculate_category_confidence(vendor_name, category)
        overall_confidence = self._calculate_overall_confidence(
            invoice_data, business_unit, category, currency_type
        )

        # Generate insights and recommendations
        insights = self._generate_insights(invoice_data, business_unit, category, amount)

        # Enhanced classification result
        classification_result = {
            'business_unit': business_unit,
            'category': category,
            'currency_type': currency_type,
            'vendor_type': vendor_type,
            'client_info': client_info,
            'confidence_scores': {
                'business_unit': bu_confidence,
                'category': cat_confidence,
                'overall': overall_confidence
            },
            'insights': insights,
            'classification_method': 'delta_business_intelligence',
            'classifier_version': '1.0.0'
        }

        return classification_result

    def _classify_business_unit(self, vendor_name: str, amount: float, currency: str, description: str) -> str:
        """Classify business unit based on vendor and transaction context"""

        # Check vendor patterns first (highest priority)
        for unit, patterns in self.vendor_patterns.items():
            for pattern in patterns:
                if re.search(pattern, vendor_name, re.IGNORECASE):
                    return unit

        # Check description patterns
        for unit, patterns in self.vendor_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    return unit

        # Amount-based classification for high-value transactions
        if amount > self.amount_thresholds['high_value']:
            return 'Delta LLC'  # High value → main holding company

        # Crypto currency transactions
        if currency in ['BTC', 'TAO', 'ETH']:
            if currency == 'BTC':
                return 'Infinity Validator'  # BTC → Mining
            elif currency == 'TAO':
                return 'Delta Prop Shop LLC'  # TAO → Trading
            else:
                return 'Delta Prop Shop LLC'  # Other crypto → Trading

        # Geographic indicators
        if any(geo in vendor_name for geo in ['paraguay', 'asuncion']):
            return 'Delta Mining Paraguay S.A.'
        elif any(geo in vendor_name for geo in ['brasil', 'brazil']):
            return 'Delta Brazil'

        # Default to main entity
        return 'Delta LLC'

    def _classify_category(self, vendor_name: str, description: str, business_unit: str) -> str:
        """Classify expense category"""

        combined_text = f"{vendor_name} {description}"

        # Check category patterns
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    return category

        # Business unit specific defaults
        bu_category_defaults = {
            'Delta LLC': 'Technology Expenses',
            'Delta Prop Shop LLC': 'Trading Expenses',
            'Infinity Validator': 'Mining Expenses',
            'Delta Mining Paraguay S.A.': 'Utilities',
            'Delta Brazil': 'Professional Services'
        }

        return bu_category_defaults.get(business_unit, 'Other')

    def _detect_currency_type(self, currency: str, vendor_name: str, description: str) -> str:
        """Detect if transaction involves cryptocurrency or fiat"""

        # Direct currency detection
        if currency in self.crypto_currencies.keys():
            return 'cryptocurrency'

        # Vendor-based detection
        for vendor_pattern in self.crypto_vendors:
            if vendor_pattern in vendor_name.lower():
                return 'cryptocurrency'

        # Description-based detection
        crypto_keywords = ['mining', 'staking', 'validator', 'blockchain', 'crypto', 'defi']
        if any(keyword in description.lower() for keyword in crypto_keywords):
            return 'cryptocurrency'

        return 'fiat'

    def _classify_vendor_type(self, vendor_name: str) -> str:
        """Classify type of vendor/supplier"""

        vendor_types = {
            'Technology Provider': ['aws', 'microsoft', 'google', 'github', 'software'],
            'Crypto Exchange': ['coinbase', 'binance', 'mexc', 'kraken'],
            'Utility Company': ['electric', 'power', 'ande', 'copaco'],
            'Financial Institution': ['bank', 'credit', 'financial'],
            'Insurance Company': ['insurance', 'seguro'],
            'Professional Services': ['legal', 'accounting', 'consultant'],
            'Government Agency': ['tax', 'government', 'administration']
        }

        for vendor_type, keywords in vendor_types.items():
            if any(keyword in vendor_name.lower() for keyword in keywords):
                return vendor_type

        return 'Other Vendor'

    def _extract_client_info(self, vendor_name: str, description: str) -> Dict[str, Any]:
        """Extract client/customer information if this is revenue"""

        client_patterns = {
            'EXOS Capital': r'exos.*capital',
            'Alps Blockchain': r'alps.*blockchain',
            'Taoshi Client': r'taoshi',
            'Mining Client': r'mining.*client'
        }

        for client_name, pattern in client_patterns.items():
            if re.search(pattern, f"{vendor_name} {description}", re.IGNORECASE):
                return {
                    'client_name': client_name,
                    'client_type': 'B2B Customer',
                    'relationship': 'Active Client'
                }

        return {'client_name': None, 'client_type': 'N/A', 'relationship': 'Vendor'}

    def _calculate_business_unit_confidence(self, vendor_name: str, business_unit: str, amount: float) -> float:
        """Calculate confidence score for business unit classification"""

        # High confidence for direct pattern matches
        if business_unit in self.vendor_patterns:
            for pattern in self.vendor_patterns[business_unit]:
                if re.search(pattern, vendor_name, re.IGNORECASE):
                    return 0.95

        # Medium confidence for amount-based classification
        if amount > self.amount_thresholds['high_value'] and business_unit == 'Delta LLC':
            return 0.8

        # Lower confidence for defaults
        return 0.7

    def _calculate_category_confidence(self, vendor_name: str, category: str) -> float:
        """Calculate confidence score for category classification"""

        if category in self.category_patterns:
            for pattern in self.category_patterns[category]:
                if re.search(pattern, vendor_name, re.IGNORECASE):
                    return 0.9

        return 0.75  # Default confidence

    def _calculate_overall_confidence(self, invoice_data: Dict[str, Any], business_unit: str,
                                    category: str, currency_type: str) -> float:
        """Calculate overall classification confidence"""

        base_confidence = invoice_data.get('confidence', 0.8)

        # Adjust based on classification certainty
        bu_adjustment = 0.1 if business_unit != 'Delta LLC' else 0.0  # Non-default = higher confidence
        cat_adjustment = 0.05 if category != 'Other' else -0.1
        crypto_adjustment = 0.05 if currency_type == 'cryptocurrency' else 0.0

        overall = base_confidence + bu_adjustment + cat_adjustment + crypto_adjustment

        return min(max(overall, 0.5), 1.0)  # Clamp between 0.5 and 1.0

    def _generate_insights(self, invoice_data: Dict[str, Any], business_unit: str,
                          category: str, amount: float) -> List[str]:
        """Generate business insights for the transaction"""

        insights = []

        # Amount-based insights
        if amount > self.amount_thresholds['high_value']:
            insights.append(f"High-value transaction (${amount:,.2f}) - requires executive review")
        elif amount < self.amount_thresholds['low_value']:
            insights.append("Low-value transaction - suitable for automated processing")

        # Business unit insights
        if business_unit == 'Delta Prop Shop LLC':
            insights.append("Trading operation - monitor for crypto tax implications")
        elif business_unit == 'Infinity Validator':
            insights.append("Mining operation - potential tax deduction for equipment/electricity")
        elif business_unit == 'Delta Mining Paraguay S.A.':
            insights.append("International operation - check transfer pricing rules")

        # Category insights
        if category == 'Technology Expenses':
            insights.append("Technology expense - eligible for R&D tax credits")
        elif category == 'Professional Services':
            insights.append("Professional service - verify 1099 requirements")

        # Currency insights
        currency_type = self._detect_currency_type(
            invoice_data.get('currency', 'USD'),
            invoice_data.get('vendor_name', ''),
            invoice_data.get('processing_notes', '')
        )
        if currency_type == 'cryptocurrency':
            insights.append("Crypto transaction - track for fair market value at transaction date")

        return insights

    def get_classification_summary(self, classification_result: Dict[str, Any]) -> str:
        """Generate human-readable classification summary"""

        bu = classification_result['business_unit']
        cat = classification_result['category']
        conf = classification_result['confidence_scores']['overall']
        currency_type = classification_result['currency_type']

        summary = f"Classified as {cat} for {bu} ({currency_type}) with {conf:.1%} confidence"

        if classification_result['insights']:
            summary += f"\nKey insights: {'; '.join(classification_result['insights'][:2])}"

        return summary

    def get_business_unit_info(self, business_unit: str) -> Dict[str, Any]:
        """Get detailed information about a business unit"""
        return {
            'name': business_unit,
            'description': self.business_units.get(business_unit, 'Unknown business unit'),
            'typical_categories': self._get_typical_categories_for_unit(business_unit),
            'currency_types': self._get_typical_currencies_for_unit(business_unit)
        }

    def _get_typical_categories_for_unit(self, business_unit: str) -> List[str]:
        """Get typical expense categories for a business unit"""
        unit_categories = {
            'Delta LLC': ['Technology Expenses', 'Professional Services', 'Office Expenses'],
            'Delta Prop Shop LLC': ['Trading Expenses', 'Technology Expenses', 'Bank Fees'],
            'Infinity Validator': ['Mining Expenses', 'Utilities', 'Technology Expenses'],
            'Delta Mining Paraguay S.A.': ['Utilities', 'Professional Services', 'Office Expenses'],
            'Delta Brazil': ['Professional Services', 'Insurance', 'Office Expenses']
        }
        return unit_categories.get(business_unit, ['Other'])

    def _get_typical_currencies_for_unit(self, business_unit: str) -> List[str]:
        """Get typical currencies for a business unit"""
        unit_currencies = {
            'Delta LLC': ['USD'],
            'Delta Prop Shop LLC': ['USD', 'BTC', 'TAO', 'USDC'],
            'Infinity Validator': ['BTC', 'USD'],
            'Delta Mining Paraguay S.A.': ['USD', 'PYG'],
            'Delta Brazil': ['USD', 'BRL']
        }
        return unit_currencies.get(business_unit, ['USD'])


def test_delta_classifier():
    """Test the Delta Business Classifier"""
    print("=== TESTING DELTA BUSINESS CLASSIFIER ===")

    classifier = DeltaBusinessClassifier()

    # Test cases
    test_invoices = [
        {
            'vendor_name': 'AWS - Amazon Web Services',
            'total_amount': 2500.75,
            'currency': 'USD',
            'processing_notes': 'Cloud computing services'
        },
        {
            'vendor_name': 'Coinbase Inc',
            'total_amount': 15000.00,
            'currency': 'BTC',
            'processing_notes': 'Bitcoin trading transaction'
        },
        {
            'vendor_name': 'ANDE Paraguay',
            'total_amount': 850.50,
            'currency': 'USD',
            'processing_notes': 'Electric power utility bill'
        }
    ]

    for i, invoice in enumerate(test_invoices, 1):
        print(f"\n🧪 TEST {i}: {invoice['vendor_name']}")

        result = classifier.classify_invoice(invoice)

        print(f"   Business Unit: {result['business_unit']}")
        print(f"   Category: {result['category']}")
        print(f"   Currency Type: {result['currency_type']}")
        print(f"   Vendor Type: {result['vendor_type']}")
        print(f"   Confidence: {result['confidence_scores']['overall']:.1%}")

        if result['insights']:
            print(f"   Insights: {result['insights'][0]}")

    print(f"\n✅ Delta Business Classifier test completed")

if __name__ == "__main__":
    test_delta_classifier()