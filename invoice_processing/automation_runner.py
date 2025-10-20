#!/usr/bin/env python3
"""
Automation Runner - Complete Invoice Processing Pipeline
Sistema completo de processamento automatizado de faturas
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from core.email_monitor import InvoiceEmailMonitor
from test_manual_processing import ManualProcessingPipeline
from integration import MainSystemIntegrator
from config.settings import LOGGING_CONFIG, EMAIL_SETTINGS

class InvoiceAutomationRunner:
    """Complete automation system for invoice processing"""

    def __init__(self):
        self.email_monitor = InvoiceEmailMonitor()
        self.pipeline = ManualProcessingPipeline()
        self.integrator = MainSystemIntegrator()

        # Setup logging
        self.setup_logging()

        # Statistics
        self.stats = {
            'emails_processed': 0,
            'invoices_extracted': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'total_amount_processed': 0.0,
            'start_time': datetime.now(),
            'last_run': None
        }

        print("🤖 Invoice Automation Runner initialized")

    def setup_logging(self):
        """Setup logging configuration"""
        try:
            log_file = LOGGING_CONFIG['FILE']
            log_file.parent.mkdir(exist_ok=True)

            logging.basicConfig(
                level=getattr(logging, LOGGING_CONFIG['LEVEL']),
                format=LOGGING_CONFIG['FORMAT'],
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )

            self.logger = logging.getLogger('InvoiceAutomation')
            self.logger.info("Logging system initialized")

        except Exception as e:
            print(f"⚠️  Logging setup failed: {e}")
            # Fallback to basic logging
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger('InvoiceAutomation')

    def run_single_cycle(self) -> Dict[str, Any]:
        """Run single automation cycle"""
        self.logger.info("Starting automation cycle")
        cycle_start = datetime.now()

        try:
            # Step 1: Scan emails
            self.logger.info("Scanning for invoice emails...")
            invoice_emails = self.email_monitor.scan_for_invoices()

            if not invoice_emails:
                self.logger.info("No new invoice emails found")
                return {
                    'status': 'success',
                    'emails_found': 0,
                    'invoices_processed': 0,
                    'cycle_time': (datetime.now() - cycle_start).total_seconds()
                }

            self.logger.info(f"Found {len(invoice_emails)} invoice emails")

            # Step 2: Process emails
            results = []
            successful_invoices = 0
            total_amount = 0.0

            for email_info in invoice_emails:
                try:
                    self.logger.info(f"Processing email: {email_info['subject'][:50]}...")

                    email_results = self._process_single_email(email_info)
                    results.extend(email_results)

                    # Update statistics
                    for result in email_results:
                        if result.get('status') == 'success':
                            successful_invoices += 1
                            total_amount += result.get('extracted_data', {}).get('total_amount', 0)

                    self.stats['emails_processed'] += 1

                except Exception as e:
                    self.logger.error(f"Failed to process email {email_info['email_id']}: {e}")
                    results.append({
                        'status': 'error',
                        'email_id': email_info['email_id'],
                        'error': str(e)
                    })

            # Step 3: Update statistics
            self.stats['invoices_extracted'] += len(results)
            self.stats['successful_extractions'] += successful_invoices
            self.stats['failed_extractions'] += len(results) - successful_invoices
            self.stats['total_amount_processed'] += total_amount
            self.stats['last_run'] = datetime.now()

            # Step 4: Generate summary
            cycle_summary = {
                'status': 'success',
                'emails_found': len(invoice_emails),
                'invoices_processed': len(results),
                'successful': successful_invoices,
                'failed': len(results) - successful_invoices,
                'total_amount': total_amount,
                'cycle_time': (datetime.now() - cycle_start).total_seconds(),
                'results': results
            }

            self.logger.info(f"Automation cycle completed: {successful_invoices}/{len(results)} successful")
            return cycle_summary

        except Exception as e:
            self.logger.error(f"Automation cycle failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'cycle_time': (datetime.now() - cycle_start).total_seconds()
            }

    def _process_single_email(self, email_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process single email with all attachments"""
        results = []

        for attachment in email_info['attachments']:
            try:
                # Save attachment temporarily
                temp_file = self._save_temp_attachment(attachment, email_info['email_id'])

                if temp_file:
                    # Process with full pipeline
                    result = self.pipeline.process_invoice_file(temp_file)

                    # Add email metadata
                    result.update({
                        'email_id': email_info['email_id'],
                        'email_subject': email_info['subject'],
                        'email_sender': email_info['sender'],
                        'attachment_filename': attachment['filename']
                    })

                    results.append(result)

                    # Cleanup
                    os.remove(temp_file)

                else:
                    results.append({
                        'status': 'error',
                        'error': 'Failed to save attachment',
                        'attachment': attachment['filename']
                    })

            except Exception as e:
                self.logger.error(f"Failed to process attachment {attachment['filename']}: {e}")
                results.append({
                    'status': 'error',
                    'attachment': attachment['filename'],
                    'error': str(e)
                })

        return results

    def _save_temp_attachment(self, attachment: Dict[str, Any], email_id: str) -> str:
        """Save attachment to temp file"""
        try:
            temp_dir = Path("temp_processing")
            temp_dir.mkdir(exist_ok=True)

            filename = f"{email_id}_{attachment['filename']}"
            temp_file = temp_dir / filename

            with open(temp_file, 'wb') as f:
                f.write(attachment['content'])

            return str(temp_file)

        except Exception as e:
            self.logger.error(f"Failed to save temp attachment: {e}")
            return None

    def start_continuous_automation(self, check_interval: int = None):
        """Start continuous automation monitoring"""
        interval = check_interval or EMAIL_SETTINGS['CHECK_INTERVAL']

        self.logger.info(f"Starting continuous automation (interval: {interval}s)")
        print(f"🚀 CONTINUOUS INVOICE AUTOMATION STARTED")
        print(f"   Check interval: {interval} seconds")
        print(f"   Email: {EMAIL_SETTINGS['EMAIL_ADDRESS']}")
        print(f"   Press Ctrl+C to stop")

        try:
            while True:
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Running automation cycle...")

                # Run single cycle
                cycle_result = self.run_single_cycle()

                # Print summary
                if cycle_result['status'] == 'success':
                    print(f"✅ Cycle completed:")
                    print(f"   Emails: {cycle_result['emails_found']}")
                    print(f"   Invoices: {cycle_result.get('successful', 0)}/{cycle_result['invoices_processed']}")
                    print(f"   Amount: ${cycle_result.get('total_amount', 0):.2f}")
                    print(f"   Time: {cycle_result['cycle_time']:.1f}s")
                else:
                    print(f"❌ Cycle failed: {cycle_result.get('error', 'Unknown error')}")

                # Wait for next cycle
                print(f"⏸️  Waiting {interval}s for next check...")
                time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n⏹️  Automation stopped by user")
            self.print_final_statistics()
        except Exception as e:
            self.logger.error(f"Automation error: {e}")
            print(f"❌ Automation failed: {e}")

    def test_full_automation(self) -> Dict[str, Any]:
        """Test complete automation system"""
        print("=" * 60)
        print("FULL AUTOMATION SYSTEM TEST")
        print("=" * 60)

        # Test 1: System components
        print("\n🧪 TEST 1: System Components")

        # Test email connection
        if not self.email_monitor.test_email_connection():
            return {'status': 'failed', 'error': 'Email connection failed'}

        # Test database
        try:
            self.integrator.create_invoice_tables()
            print("✅ Database connection OK")
        except Exception as e:
            return {'status': 'failed', 'error': f'Database failed: {e}'}

        # Test Claude API
        try:
            from services.claude_vision import ClaudeVisionService
            claude_service = ClaudeVisionService()
            print("✅ Claude Vision service OK")
        except Exception as e:
            return {'status': 'failed', 'error': f'Claude Vision failed: {e}'}

        # Test 2: Single automation cycle
        print("\n🧪 TEST 2: Single Automation Cycle")
        cycle_result = self.run_single_cycle()

        if cycle_result['status'] == 'success':
            print("✅ Automation cycle completed successfully")
            print(f"   Found {cycle_result['emails_found']} emails")
            print(f"   Processed {cycle_result['invoices_processed']} invoices")
        else:
            print(f"⚠️  Automation cycle completed with issues: {cycle_result.get('error', 'Unknown')}")

        # Test 3: Statistics and logging
        print("\n🧪 TEST 3: Statistics and Logging")
        self.print_statistics()

        print("\n" + "=" * 60)
        print("AUTOMATION SYSTEM TEST COMPLETED")

        if cycle_result['status'] == 'success':
            print("✅ System ready for production automation!")
            print("\nTo start continuous monitoring:")
            print("  python automation_runner.py --continuous")
        else:
            print("⚠️  System has issues - review logs and configuration")

        print("=" * 60)

        return {
            'status': 'success',
            'components_ok': True,
            'cycle_result': cycle_result,
            'statistics': self.stats
        }

    def print_statistics(self):
        """Print current statistics"""
        runtime = datetime.now() - self.stats['start_time']

        print(f"📊 AUTOMATION STATISTICS:")
        print(f"   Runtime: {runtime}")
        print(f"   Emails processed: {self.stats['emails_processed']}")
        print(f"   Invoices extracted: {self.stats['invoices_extracted']}")
        print(f"   Success rate: {self.stats['successful_extractions']}/{self.stats['invoices_extracted']} ({self._success_rate():.1%})")
        print(f"   Total amount: ${self.stats['total_amount_processed']:.2f}")
        print(f"   Last run: {self.stats['last_run'] or 'Never'}")

    def print_final_statistics(self):
        """Print final statistics when stopping"""
        print(f"\n📊 FINAL AUTOMATION STATISTICS:")
        self.print_statistics()

        # Save statistics to file
        stats_file = Path("automation_statistics.json")
        try:
            with open(stats_file, 'w') as f:
                # Convert datetime objects to strings for JSON serialization
                json_stats = self.stats.copy()
                json_stats['start_time'] = json_stats['start_time'].isoformat()
                json_stats['last_run'] = json_stats['last_run'].isoformat() if json_stats['last_run'] else None

                json.dump(json_stats, f, indent=2)
            print(f"📁 Statistics saved to: {stats_file}")
        except Exception as e:
            print(f"⚠️  Failed to save statistics: {e}")

    def _success_rate(self) -> float:
        """Calculate success rate"""
        if self.stats['invoices_extracted'] == 0:
            return 0.0
        return self.stats['successful_extractions'] / self.stats['invoices_extracted']

    def get_recent_invoices(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get invoices processed in recent hours"""
        try:
            # This would filter by processing date
            # For now, just return recent invoices
            invoices = self.integrator.get_invoices(limit=20)
            return invoices
        except Exception as e:
            self.logger.error(f"Failed to get recent invoices: {e}")
            return []


def main():
    """Main automation function"""
    import argparse

    parser = argparse.ArgumentParser(description='Invoice Processing Automation')
    parser.add_argument('--continuous', action='store_true', help='Start continuous monitoring')
    parser.add_argument('--test', action='store_true', help='Run system tests')
    parser.add_argument('--cycle', action='store_true', help='Run single automation cycle')
    parser.add_argument('--interval', type=int, default=300, help='Check interval in seconds')

    args = parser.parse_args()

    automation = InvoiceAutomationRunner()

    if args.test:
        automation.test_full_automation()
    elif args.cycle:
        result = automation.run_single_cycle()
        print(f"Cycle result: {result}")
    elif args.continuous:
        automation.start_continuous_automation(args.interval)
    else:
        # Default: run test
        automation.test_full_automation()

if __name__ == "__main__":
    main()