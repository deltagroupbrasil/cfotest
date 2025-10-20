#!/usr/bin/env python3
"""
MEXC API Service for Crypto Invoice System
Handles deposit address generation and payment detection
"""

import requests
import hmac
import hashlib
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json


class MEXCAPIError(Exception):
    """MEXC API error exception"""
    pass


class MEXCService:
    """MEXC API integration service"""

    # MEXC API endpoints
    BASE_URL = "https://api.mexc.com"

    # Supported currencies and networks
    SUPPORTED_CURRENCIES = {
        "BTC": ["BTC"],
        "USDT": ["TRC20", "ERC20", "BEP20"],
        "TAO": ["TAO"]  # Bittensor native network
    }

    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize MEXC service

        Args:
            api_key: MEXC API key
            api_secret: MEXC API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update({
            "X-MEXC-APIKEY": self.api_key,
            "Content-Type": "application/json"
        })

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Generate HMAC SHA256 signature for API request

        Args:
            params: Request parameters

        Returns:
            Signature string
        """
        # Sort parameters alphabetically
        sorted_params = sorted(params.items())
        query_string = "&".join([f"{k}={v}" for k, v in sorted_params])

        # Generate signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def _make_request(self, method: str, endpoint: str, params: Dict[str, Any] = None,
                     signed: bool = True) -> Dict[str, Any]:
        """
        Make API request to MEXC

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether to sign the request

        Returns:
            API response as dictionary

        Raises:
            MEXCAPIError: If API request fails
        """
        url = f"{self.BASE_URL}{endpoint}"

        if params is None:
            params = {}

        # Add timestamp for signed requests
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._generate_signature(params)

        try:
            if method == "GET":
                response = self.session.get(url, params=params, timeout=30)
            elif method == "POST":
                response = self.session.post(url, json=params, timeout=30)
            else:
                raise MEXCAPIError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            data = response.json()

            # Check for API-level errors
            if data.get("code") and data["code"] != 200:
                raise MEXCAPIError(f"MEXC API error: {data.get('msg', 'Unknown error')}")

            return data

        except requests.exceptions.RequestException as e:
            raise MEXCAPIError(f"Request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise MEXCAPIError(f"Invalid JSON response: {str(e)}")

    def get_primary_deposit_address(self, currency: str, network: str = None) -> Dict[str, str]:
        """
        Get the primary/main deposit address for an account
        (Used when unique addresses per invoice are not available)
        """
        return self.get_deposit_address(currency, network)

    def get_deposit_address(self, currency: str, network: str = None) -> Dict[str, str]:
        """
        Get deposit address for a specific currency and network

        Args:
            currency: Currency code (BTC, USDT, TAO)
            network: Network type (BTC, TRC20, ERC20, BEP20, TAO)

        Returns:
            Dictionary with address and optional memo/tag
            {
                "address": "0x123...",
                "memo": "12345" (optional),
                "network": "TRC20"
            }

        Raises:
            MEXCAPIError: If unable to get deposit address
        """
        # Validate currency and network
        if currency not in self.SUPPORTED_CURRENCIES:
            raise MEXCAPIError(f"Unsupported currency: {currency}")

        if network and network not in self.SUPPORTED_CURRENCIES[currency]:
            raise MEXCAPIError(f"Unsupported network {network} for currency {currency}")

        # Default network if not specified
        if not network:
            network = self.SUPPORTED_CURRENCIES[currency][0]

        params = {
            "coin": currency,
            "network": network
        }

        try:
            response = self._make_request("GET", "/api/v3/capital/deposit/address", params)

            if not response.get("address"):
                raise MEXCAPIError(f"No deposit address returned for {currency} on {network}")

            result = {
                "address": response["address"],
                "network": network,
                "currency": currency
            }

            # Some networks require memo/tag (like XRP, XLM, EOS)
            if response.get("tag"):
                result["memo"] = response["tag"]

            return result

        except Exception as e:
            raise MEXCAPIError(f"Failed to get deposit address: {str(e)}")

    def get_deposit_history(self, currency: str = None, status: int = None,
                           start_time: int = None, end_time: int = None,
                           limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get deposit history from MEXC

        Args:
            currency: Filter by currency
            status: Deposit status (0=pending, 1=success, 6=credited)
            start_time: Start timestamp (milliseconds)
            end_time: End timestamp (milliseconds)
            limit: Maximum number of records

        Returns:
            List of deposit records
            [
                {
                    "txId": "0x123...",
                    "coin": "USDT",
                    "network": "TRC20",
                    "address": "0x456...",
                    "amount": "100.50",
                    "status": 1,
                    "confirmations": 20,
                    "insertTime": 1234567890000
                }
            ]
        """
        params = {
            "limit": limit
        }

        if currency:
            params["coin"] = currency
        if status is not None:
            params["status"] = status
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        try:
            response = self._make_request("GET", "/api/v3/capital/deposit/hisrec", params)
            return response if isinstance(response, list) else []
        except Exception as e:
            raise MEXCAPIError(f"Failed to get deposit history: {str(e)}")

    def check_deposit_for_address(self, address: str, currency: str,
                                  expected_amount: float,
                                  tolerance: float = 0.005,
                                  start_time: datetime = None) -> Optional[Dict[str, Any]]:
        """
        Check if a deposit was received to a specific address

        Args:
            address: Deposit address to check
            currency: Expected currency
            expected_amount: Expected amount (for validation)
            tolerance: Acceptable tolerance (default 0.5%)
            start_time: Only check deposits after this time

        Returns:
            Deposit information if found, None otherwise
        """
        # Set start time to 24 hours ago if not specified
        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)

        start_timestamp = int(start_time.timestamp() * 1000)

        try:
            deposits = self.get_deposit_history(
                currency=currency,
                start_time=start_timestamp,
                status=None  # Check all statuses
            )

            # Filter deposits for our address
            for deposit in deposits:
                if deposit.get("address") == address:
                    amount = float(deposit.get("amount", 0))

                    # Check if amount is within tolerance
                    min_amount = expected_amount * (1 - tolerance)
                    max_amount = expected_amount * (1 + tolerance)

                    if min_amount <= amount <= max_amount:
                        return {
                            "transaction_hash": deposit.get("txId"),
                            "amount": amount,
                            "currency": deposit.get("coin"),
                            "network": deposit.get("network"),
                            "confirmations": deposit.get("confirmations", 0),
                            "status": deposit.get("status"),
                            "timestamp": deposit.get("insertTime"),
                            "raw_data": deposit
                        }

            return None

        except Exception as e:
            raise MEXCAPIError(f"Failed to check deposits: {str(e)}")

    def get_network_info(self, currency: str) -> List[Dict[str, Any]]:
        """
        Get network information for a currency

        Args:
            currency: Currency code

        Returns:
            List of available networks with details
        """
        try:
            response = self._make_request("GET", "/api/v3/capital/config/getall", {})

            # Find currency in response
            for coin_info in response:
                if coin_info.get("coin") == currency:
                    return coin_info.get("networkList", [])

            return []

        except Exception as e:
            raise MEXCAPIError(f"Failed to get network info: {str(e)}")

    def verify_transaction_manually(self, txid: str, currency: str) -> Optional[Dict[str, Any]]:
        """
        Manually verify a transaction by TxID

        Args:
            txid: Transaction ID/hash
            currency: Currency code

        Returns:
            Transaction details if found
        """
        try:
            # Get recent deposit history
            deposits = self.get_deposit_history(currency=currency, limit=1000)

            # Search for matching transaction
            for deposit in deposits:
                if deposit.get("txId") == txid:
                    return {
                        "transaction_hash": deposit.get("txId"),
                        "amount": float(deposit.get("amount", 0)),
                        "currency": deposit.get("coin"),
                        "network": deposit.get("network"),
                        "address": deposit.get("address"),
                        "confirmations": deposit.get("confirmations", 0),
                        "status": deposit.get("status"),
                        "timestamp": deposit.get("insertTime"),
                        "raw_data": deposit
                    }

            return None

        except Exception as e:
            raise MEXCAPIError(f"Failed to verify transaction: {str(e)}")

    def get_account_balance(self, currency: str = None) -> Dict[str, float]:
        """
        Get account balance for currencies

        Args:
            currency: Specific currency (optional)

        Returns:
            Dictionary of currency balances
        """
        try:
            response = self._make_request("GET", "/api/v3/account", {})

            balances = {}
            for balance in response.get("balances", []):
                asset = balance.get("asset")
                free = float(balance.get("free", 0))
                locked = float(balance.get("locked", 0))

                if currency and asset != currency:
                    continue

                if free > 0 or locked > 0:
                    balances[asset] = {
                        "free": free,
                        "locked": locked,
                        "total": free + locked
                    }

            return balances

        except Exception as e:
            raise MEXCAPIError(f"Failed to get account balance: {str(e)}")

    @staticmethod
    def get_required_confirmations(currency: str, network: str) -> int:
        """
        Get required confirmations for a currency/network

        Args:
            currency: Currency code
            network: Network type

        Returns:
            Required number of confirmations
        """
        confirmations_map = {
            "BTC": {"BTC": 3},
            "USDT": {"TRC20": 20, "ERC20": 12, "BEP20": 15},
            "TAO": {"TAO": 12}
        }

        return confirmations_map.get(currency, {}).get(network, 6)

    @staticmethod
    def format_network_name(currency: str, network: str) -> str:
        """
        Format network name for display

        Args:
            currency: Currency code
            network: Network type

        Returns:
            Formatted network name
        """
        if currency == "USDT":
            return f"USDT-{network}"
        return currency

    def test_connection(self) -> bool:
        """
        Test MEXC API connection

        Returns:
            True if connection successful
        """
        try:
            self._make_request("GET", "/api/v3/ping", {}, signed=False)
            return True
        except Exception:
            return False

    def get_server_time(self) -> int:
        """
        Get MEXC server time

        Returns:
            Server timestamp in milliseconds
        """
        try:
            response = self._make_request("GET", "/api/v3/time", {}, signed=False)
            return response.get("serverTime", 0)
        except Exception:
            return 0
