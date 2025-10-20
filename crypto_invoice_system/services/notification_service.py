#!/usr/bin/env python3
"""
Notification Service for Crypto Invoice System
Sends email/webhook notifications for payment events
"""

import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Optional
import logging
import json


class NotificationService:
    """Handle email and webhook notifications"""

    def __init__(self, smtp_config: Dict = None, webhook_url: str = None):
        """
        Initialize notification service

        Args:
            smtp_config: SMTP configuration dict
                {
                    "host": "smtp.gmail.com",
                    "port": 587,
                    "username": "user@example.com",
                    "password": "app_password",
                    "from_email": "billing@deltaenergy.com"
                }
            webhook_url: Optional webhook URL for notifications
        """
        self.smtp_config = smtp_config
        self.webhook_url = webhook_url
        self.logger = logging.getLogger("NotificationService")

    def send_payment_detected_email(self, invoice: Dict, payment: Dict) -> bool:
        """
        Send email notification when payment is detected

        Args:
            invoice: Invoice dictionary
            payment: Payment dictionary

        Returns:
            True if email sent successfully
        """
        subject = f"💰 Payment Detected - Invoice {invoice['invoice_number']}"

        body = f"""
        Payment Detected for Invoice {invoice['invoice_number']}

        Client: {invoice.get('client_name', 'N/A')}
        Amount Received: {payment['amount']} {payment['currency']}
        USD Equivalent: ${invoice['amount_usd']:,.2f}

        Transaction Hash: {payment['transaction_hash']}
        Confirmations: {payment.get('confirmations', 0)} / {payment.get('required_confirmations', 6)}

        Status: Awaiting confirmations

        This is an automated notification from Delta Energy Crypto Invoice System.
        """

        recipients = self._get_notification_recipients(invoice)
        return self._send_email(recipients, subject, body)

    def send_payment_confirmed_email(self, invoice: Dict, payment: Dict) -> bool:
        """
        Send email notification when payment is fully confirmed

        Args:
            invoice: Invoice dictionary
            payment: Payment dictionary

        Returns:
            True if email sent successfully
        """
        subject = f"✅ Payment Confirmed - Invoice {invoice['invoice_number']} PAID"

        body = f"""
        Payment Confirmed for Invoice {invoice['invoice_number']}

        Client: {invoice.get('client_name', 'N/A')}
        Amount: ${invoice['amount_usd']:,.2f}
        Cryptocurrency: {payment['amount']} {payment['currency']}

        Transaction Hash: {payment['transaction_hash']}
        Confirmations: {payment.get('confirmations', 0)} ✅

        Status: PAID

        Invoice has been marked as paid in the system.

        This is an automated notification from Delta Energy Crypto Invoice System.
        """

        recipients = self._get_notification_recipients(invoice)
        return self._send_email(recipients, subject, body)

    def send_invoice_overdue_email(self, invoice: Dict) -> bool:
        """
        Send email notification for overdue invoice

        Args:
            invoice: Invoice dictionary

        Returns:
            True if email sent successfully
        """
        subject = f"⚠️ Invoice Overdue - {invoice['invoice_number']}"

        body = f"""
        Invoice Overdue Notice

        Invoice Number: {invoice['invoice_number']}
        Client: {invoice.get('client_name', 'N/A')}
        Amount: ${invoice['amount_usd']:,.2f}
        Due Date: {invoice['due_date']}

        Status: OVERDUE

        Please follow up with client regarding payment.

        Payment Address: {invoice['deposit_address']}
        Currency: {invoice['crypto_currency']} ({invoice['crypto_network']})
        Amount: {invoice['crypto_amount']} {invoice['crypto_currency']}

        This is an automated notification from Delta Energy Crypto Invoice System.
        """

        recipients = self._get_notification_recipients(invoice)
        return self._send_email(recipients, subject, body)

    def send_invoice_created_email(self, invoice: Dict) -> bool:
        """
        Send email notification when invoice is created

        Args:
            invoice: Invoice dictionary

        Returns:
            True if email sent successfully
        """
        subject = f"📧 New Invoice Created - {invoice['invoice_number']}"

        body = f"""
        New Invoice Created

        Invoice Number: {invoice['invoice_number']}
        Client: {invoice.get('client_name', 'N/A')}
        Amount: ${invoice['amount_usd']:,.2f}
        Billing Period: {invoice.get('billing_period', 'N/A')}
        Due Date: {invoice['due_date']}

        Payment Instructions:
        Currency: {invoice['crypto_currency']} ({invoice['crypto_network']})
        Amount: {invoice['crypto_amount']} {invoice['crypto_currency']}
        Deposit Address: {invoice['deposit_address']}

        PDF invoice has been generated and payment monitoring is active.

        This is an automated notification from Delta Energy Crypto Invoice System.
        """

        recipients = self._get_notification_recipients(invoice)
        return self._send_email(recipients, subject, body)

    def _get_notification_recipients(self, invoice: Dict) -> list:
        """
        Get list of email recipients for notifications

        Args:
            invoice: Invoice dictionary

        Returns:
            List of email addresses
        """
        recipients = []

        # Default recipients (Aldo, Tiago)
        default_recipients = ['aldo@deltaenergy.com', 'tiago@deltaenergy.com']
        recipients.extend(default_recipients)

        # Add client contact email if available
        if invoice.get('client_contact'):
            recipients.append(invoice['client_contact'])

        return list(set(recipients))  # Remove duplicates

    def _send_email(self, recipients: list, subject: str, body: str) -> bool:
        """
        Send email using SMTP

        Args:
            recipients: List of recipient email addresses
            subject: Email subject
            body: Email body text

        Returns:
            True if email sent successfully
        """
        if not self.smtp_config:
            self.logger.warning("SMTP not configured - email not sent")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config.get('from_email', 'noreply@deltaenergy.com')
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            # Connect to SMTP server
            server = smtplib.SMTP(
                self.smtp_config['host'],
                self.smtp_config.get('port', 587)
            )
            server.starttls()
            server.login(
                self.smtp_config['username'],
                self.smtp_config['password']
            )

            # Send email
            server.send_message(msg)
            server.quit()

            self.logger.info(f"Email sent to {recipients}: {subject}")
            return True

        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False

    def send_webhook_notification(self, event: str, data: Dict) -> bool:
        """
        Send webhook notification

        Args:
            event: Event type (payment_detected, payment_confirmed, invoice_created, etc.)
            data: Event data dictionary

        Returns:
            True if webhook delivered successfully
        """
        if not self.webhook_url:
            return False

        try:
            payload = {
                "event": event,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            response.raise_for_status()
            self.logger.info(f"Webhook notification sent: {event}")
            return True

        except Exception as e:
            self.logger.error(f"Error sending webhook: {e}")
            return False

    def send_slack_notification(self, message: str, webhook_url: str = None) -> bool:
        """
        Send Slack notification

        Args:
            message: Message text
            webhook_url: Slack webhook URL (optional, uses default if not provided)

        Returns:
            True if message sent successfully
        """
        url = webhook_url or self.webhook_url

        if not url:
            return False

        try:
            payload = {
                "text": message,
                "username": "Delta Energy Invoice Bot",
                "icon_emoji": ":moneybag:"
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True

        except Exception as e:
            self.logger.error(f"Error sending Slack message: {e}")
            return False


# Integration with existing CFO system

def sync_to_cfo_system(invoice: Dict, payment: Dict = None) -> bool:
    """
    Sync invoice and payment data to existing AI CFO system

    Args:
        invoice: Invoice dictionary
        payment: Optional payment dictionary

    Returns:
        True if sync successful
    """
    try:
        # Import existing CFO system database
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

        from web_ui.app_db import get_db_connection

        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Prepare transaction data for CFO system
        transaction_data = {
            "Date": payment['timestamp'] if payment else invoice['issue_date'],
            "Description": f"Invoice {invoice['invoice_number']} - {invoice.get('client_name', 'Client')} - {invoice.get('billing_period', '')}",
            "Amount": invoice['amount_usd'] if not payment else payment['amount'] * invoice['exchange_rate'],
            "classified_entity": "Delta Mining Paraguay S.A.",  # Paraguay operations
            "Business_Unit": "Delta Mining Paraguay S.A.",
            "source_file": f"crypto_invoice_{invoice['invoice_number']}",
            "transaction_type": "Revenue",
            "confidence": 1.0,
            "classification_reason": f"Crypto invoice payment from {invoice.get('client_name', 'client')}",
            "Origin": "External Account",
            "Destination": "Delta Paraguay Operations",
            "Identifier": invoice.get('invoice_number', ''),
            "Currency": invoice.get('crypto_currency', 'USD')
        }

        if payment:
            transaction_data["Identifier"] = payment.get('transaction_hash', invoice['invoice_number'])

        # Insert into transactions table
        cursor.execute("""
            INSERT INTO transactions (
                Date, Description, Amount, classified_entity, Business_Unit,
                source_file, transaction_type, confidence, classification_reason,
                Origin, Destination, Identifier, Currency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_data["Date"],
            transaction_data["Description"],
            transaction_data["Amount"],
            transaction_data["classified_entity"],
            transaction_data["Business_Unit"],
            transaction_data["source_file"],
            transaction_data["transaction_type"],
            transaction_data["confidence"],
            transaction_data["classification_reason"],
            transaction_data["Origin"],
            transaction_data["Destination"],
            transaction_data["Identifier"],
            transaction_data["Currency"]
        ))

        conn.commit()
        conn.close()

        logging.info(f"Synced invoice {invoice['invoice_number']} to CFO system")
        return True

    except Exception as e:
        logging.error(f"Error syncing to CFO system: {e}")
        return False
