#!/usr/bin/env python3
"""
Email Monitor - Automated Invoice Detection
Monitora emails automaticamente e detecta anexos de faturas
"""

import imaplib
import email
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
import hashlib

# Add parent to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import EMAIL_SETTINGS, PROCESSING_CONFIG
from integration import MainSystemIntegrator

class InvoiceEmailMonitor:
    """Monitor emails for invoice attachments and process automatically"""

    def __init__(self):
        self.email_config = EMAIL_SETTINGS
        self.integrator = MainSystemIntegrator()
        self.processed_emails = set()  # Track processed emails
        self.running = False

        print("📧 Invoice Email Monitor initialized")

    def connect_to_email(self) -> imaplib.IMAP4_SSL:
        """Connect to email server"""
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(
                self.email_config['IMAP_SERVER'],
                self.email_config['IMAP_PORT']
            )

            # Login
            mail.login(
                self.email_config['EMAIL_ADDRESS'],
                self.email_config['EMAIL_PASSWORD']
            )

            print(f"✅ Connected to {self.email_config['IMAP_SERVER']}")
            return mail

        except Exception as e:
            print(f"❌ Email connection failed: {e}")
            raise

    def scan_for_invoices(self) -> List[Dict[str, Any]]:
        """Scan inbox for emails with invoice attachments"""
        invoice_emails = []

        try:
            mail = self.connect_to_email()

            # Select inbox
            mail.select(self.email_config['INBOX_FOLDER'])

            # Search for emails with attachments from last 7 days
            since_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%d-%b-%Y")
            search_criteria = f'(SINCE "{since_date}" UNSEEN)'

            print(f"🔍 Searching for emails since {since_date}")

            # Search emails
            status, messages = mail.search(None, search_criteria)

            if status != 'OK':
                print("❌ Email search failed")
                return []

            email_ids = messages[0].split()
            print(f"📨 Found {len(email_ids)} unread emails")

            for email_id in email_ids:
                try:
                    # Fetch email
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue

                    # Parse email
                    email_message = email.message_from_bytes(msg_data[0][1])
                    email_info = self._analyze_email(email_message, email_id.decode())

                    if email_info and self._is_invoice_email(email_info):
                        invoice_emails.append(email_info)
                        print(f"📧 Invoice email detected: {email_info['subject'][:50]}...")

                except Exception as e:
                    print(f"⚠️  Error processing email {email_id}: {e}")
                    continue

            mail.close()
            mail.logout()

            print(f"✅ Scan completed: {len(invoice_emails)} invoice emails found")
            return invoice_emails

        except Exception as e:
            print(f"❌ Email scan failed: {e}")
            return []

    def _analyze_email(self, email_message, email_id: str) -> Optional[Dict[str, Any]]:
        """Analyze email and extract metadata"""
        try:
            # Extract basic info
            subject = email_message.get('Subject', '')
            sender = email_message.get('From', '')
            date_str = email_message.get('Date', '')
            message_id = email_message.get('Message-ID', email_id)

            # Create unique ID
            unique_id = hashlib.md5(f"{message_id}{sender}{subject}".encode()).hexdigest()[:12]

            # Check if already processed
            if unique_id in self.processed_emails:
                return None

            # Extract attachments
            attachments = self._extract_attachments(email_message)

            email_info = {
                'email_id': unique_id,
                'raw_email_id': email_id,
                'subject': subject,
                'sender': sender,
                'date': date_str,
                'message_id': message_id,
                'attachments': attachments,
                'attachment_count': len(attachments)
            }

            return email_info

        except Exception as e:
            print(f"❌ Email analysis failed: {e}")
            return None

    def _extract_attachments(self, email_message) -> List[Dict[str, Any]]:
        """Extract attachments from email"""
        attachments = []

        try:
            for part in email_message.walk():
                # Skip non-attachment parts
                if part.get_content_maintype() == 'multipart':
                    continue

                # Check if it's an attachment
                content_disposition = part.get('Content-Disposition', '')
                if 'attachment' not in content_disposition:
                    continue

                # Extract attachment info
                filename = part.get_filename()
                if not filename:
                    continue

                # Check if it's a supported file type
                file_ext = Path(filename).suffix.lower()
                if file_ext not in PROCESSING_CONFIG['ALLOWED_EXTENSIONS']:
                    continue

                # Get file content
                file_content = part.get_payload(decode=True)
                if not file_content:
                    continue

                attachment_info = {
                    'filename': filename,
                    'size': len(file_content),
                    'content_type': part.get_content_type(),
                    'extension': file_ext,
                    'content': file_content
                }

                attachments.append(attachment_info)

        except Exception as e:
            print(f"❌ Attachment extraction failed: {e}")

        return attachments

    def _is_invoice_email(self, email_info: Dict[str, Any]) -> bool:
        """Determine if email contains invoices"""
        # Check if has relevant attachments
        if email_info['attachment_count'] == 0:
            return False

        # Check subject for invoice keywords
        subject = email_info['subject'].lower()
        invoice_keywords = [
            'invoice', 'bill', 'statement', 'receipt', 'fatura',
            'cobrança', 'billing', 'payment', 'account'
        ]

        has_invoice_keyword = any(keyword in subject for keyword in invoice_keywords)

        # Check sender for known vendors
        sender = email_info['sender'].lower()
        known_vendors = [
            'aws', 'amazon', 'microsoft', 'google', 'billing',
            'noreply', 'accounts', 'invoices', 'finance'
        ]

        has_known_vendor = any(vendor in sender for vendor in known_vendors)

        # Must have either invoice keyword OR known vendor + attachments
        return has_invoice_keyword or has_known_vendor

    def process_invoice_emails(self, invoice_emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process list of invoice emails"""
        results = []

        print(f"\n🔄 Processing {len(invoice_emails)} invoice emails...")

        for email_info in invoice_emails:
            try:
                # Log email processing
                self._log_email_processing(email_info)

                # Process each attachment
                for attachment in email_info['attachments']:
                    result = self._process_attachment(attachment, email_info)
                    results.append(result)

                # Mark as processed
                self.processed_emails.add(email_info['email_id'])

            except Exception as e:
                print(f"❌ Failed to process email {email_info['email_id']}: {e}")
                results.append({
                    'status': 'error',
                    'email_id': email_info['email_id'],
                    'error': str(e)
                })

        return results

    def _process_attachment(self, attachment: Dict[str, Any], email_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual attachment"""
        try:
            # Save attachment to temp file
            temp_file = self._save_temp_attachment(attachment, email_info['email_id'])

            if not temp_file:
                return {'status': 'error', 'error': 'Failed to save attachment'}

            # Import processing pipeline
            from ..test_manual_processing import ManualProcessingPipeline
            pipeline = ManualProcessingPipeline()

            # Process with full pipeline
            result = pipeline.process_invoice_file(temp_file)

            # Add email metadata
            result['email_id'] = email_info['email_id']
            result['email_subject'] = email_info['subject']
            result['email_sender'] = email_info['sender']

            # Clean up temp file
            os.remove(temp_file)

            return result

        except Exception as e:
            return {
                'status': 'error',
                'email_id': email_info['email_id'],
                'attachment': attachment['filename'],
                'error': str(e)
            }

    def _save_temp_attachment(self, attachment: Dict[str, Any], email_id: str) -> Optional[str]:
        """Save attachment to temporary file"""
        try:
            # Create temp directory
            temp_dir = Path("temp_attachments")
            temp_dir.mkdir(exist_ok=True)

            # Create unique filename
            filename = f"{email_id}_{attachment['filename']}"
            temp_file = temp_dir / filename

            # Write content
            with open(temp_file, 'wb') as f:
                f.write(attachment['content'])

            return str(temp_file)

        except Exception as e:
            print(f"❌ Failed to save attachment: {e}")
            return None

    def _log_email_processing(self, email_info: Dict[str, Any]):
        """Log email to processing log"""
        try:
            # This would integrate with the database logging
            # For now, just print
            print(f"📧 Processing email: {email_info['subject'][:50]}...")
            print(f"   From: {email_info['sender']}")
            print(f"   Attachments: {email_info['attachment_count']}")

        except Exception as e:
            print(f"⚠️  Logging failed: {e}")

    def start_monitoring(self, check_interval: Optional[int] = None):
        """Start continuous email monitoring"""
        interval = check_interval or self.email_config['CHECK_INTERVAL']

        print(f"🚀 Starting email monitoring (checking every {interval} seconds)")
        print(f"   Email: {self.email_config['EMAIL_ADDRESS']}")
        print(f"   Server: {self.email_config['IMAP_SERVER']}")

        self.running = True

        try:
            while self.running:
                print(f"\n⏰ Checking for new invoice emails...")

                # Scan for invoices
                invoice_emails = self.scan_for_invoices()

                if invoice_emails:
                    # Process found emails
                    results = self.process_invoice_emails(invoice_emails)

                    # Summary
                    successful = len([r for r in results if r.get('status') == 'success'])
                    print(f"📊 Processed {len(results)} attachments: {successful} successful")
                else:
                    print("✅ No new invoice emails found")

                # Wait for next check
                print(f"⏸️  Waiting {interval} seconds for next check...")
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
            self.running = False
        except Exception as e:
            print(f"❌ Monitoring error: {e}")
            self.running = False

    def test_email_connection(self) -> bool:
        """Test email connection and configuration"""
        print("=== TESTING EMAIL CONNECTION ===")

        try:
            mail = self.connect_to_email()

            # Test inbox selection
            mail.select('INBOX')

            # Test search
            mail.search(None, 'ALL')

            mail.close()
            mail.logout()

            print("✅ Email connection test successful")
            return True

        except Exception as e:
            print(f"❌ Email connection test failed: {e}")
            print("\nTroubleshooting:")
            print("1. Check EMAIL_ADDRESS and EMAIL_PASSWORD environment variables")
            print("2. Enable 'Less secure app access' or use app-specific password")
            print("3. Check IMAP server settings")
            return False

    def test_single_scan(self) -> List[Dict[str, Any]]:
        """Test single email scan"""
        print("=== TESTING SINGLE EMAIL SCAN ===")

        invoice_emails = self.scan_for_invoices()

        if invoice_emails:
            print(f"📧 Found {len(invoice_emails)} invoice emails:")
            for email_info in invoice_emails:
                print(f"  - {email_info['subject'][:60]}...")
                print(f"    From: {email_info['sender']}")
                print(f"    Attachments: {email_info['attachment_count']}")
        else:
            print("ℹ️  No invoice emails found in recent messages")

        return invoice_emails


def main():
    """Test email monitoring"""
    print("=" * 60)
    print("EMAIL MONITORING - TEST")
    print("=" * 60)

    monitor = InvoiceEmailMonitor()

    # Test 1: Connection
    print("\n🧪 TEST 1: Email Connection")
    if not monitor.test_email_connection():
        print("❌ Email connection failed - check configuration")
        return

    # Test 2: Single scan
    print("\n🧪 TEST 2: Single Email Scan")
    invoice_emails = monitor.test_single_scan()

    # Test 3: Process one email if found
    if invoice_emails:
        print("\n🧪 TEST 3: Process First Invoice Email")
        results = monitor.process_invoice_emails(invoice_emails[:1])  # Process just first one

        if results and results[0].get('status') == 'success':
            print("✅ Email processing test successful!")
        else:
            print(f"❌ Email processing test failed: {results[0] if results else 'No results'}")
    else:
        print("\n🧪 TEST 3: Skipped (no invoice emails found)")

    print("\n" + "=" * 60)
    print("EMAIL MONITORING TEST COMPLETED")
    print("\nTo start continuous monitoring:")
    print("  monitor.start_monitoring()")
    print("=" * 60)

if __name__ == "__main__":
    main()