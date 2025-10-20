#!/usr/bin/env python3
"""
DeltaCFOAgent - SQLite Cleanup Script
====================================

This script helps clean up obsolete SQLite files after migration to PostgreSQL.
Run this script to remove old database files and update documentation.

Usage:
    python cleanup_sqlite_files.py [--dry-run] [--backup]

Options:
    --dry-run    Show what would be removed without actually doing it
    --backup     Create backup copies before removing files
"""

import os
import sys
import argparse
import shutil
import glob
from pathlib import Path
from datetime import datetime

class SQLiteCleanup:
    """Handles cleanup of obsolete SQLite files after PostgreSQL migration"""

    def __init__(self, dry_run=False, backup=False):
        self.dry_run = dry_run
        self.backup = backup
        self.project_root = Path(__file__).parent
        self.backup_dir = self.project_root / "sqlite_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")

        # Files and directories to clean up
        self.sqlite_files = [
            "web_ui/delta_transactions.db",
            "crypto_invoices.db",
            "crypto_invoice_system/crypto_invoices.db",
            "invoice_processing/invoices.db",
            "*.db",
            "*.sqlite",
            "*.sqlite3"
        ]

        # Legacy files that reference SQLite
        self.legacy_files = [
            "crypto_invoice_system/models/database.py",  # Keep but mark as deprecated
            "database_utils.py",  # Might be legacy
            "setup_database_fix.py",  # Legacy setup script
            "emergency_database_fix.py",  # Legacy fix script
            "analyze_db_schema.py"  # Legacy analysis script
        ]

    def cleanup_all(self):
        """Run complete cleanup process"""
        print("🧹 Starting SQLite Cleanup Process")
        print(f"Project Root: {self.project_root}")
        print(f"Dry Run: {self.dry_run}")
        print(f"Create Backups: {self.backup}")
        print("=" * 60)

        if self.backup and not self.dry_run:
            self._create_backup_directory()

        # Find and process SQLite database files
        self._cleanup_database_files()

        # Handle legacy Python files
        self._handle_legacy_files()

        # Update gitignore
        self._update_gitignore()

        print("\n" + "=" * 60)
        print("✅ Cleanup completed!")

        if not self.dry_run:
            print("\nNext steps:")
            print("1. Review changes and test the system")
            print("2. Commit the cleaned up codebase")
            print("3. Deploy with PostgreSQL configuration")
        else:
            print("\n🔍 This was a DRY RUN - no files were actually modified")

    def _create_backup_directory(self):
        """Create backup directory structure"""
        print(f"\n📦 Creating backup directory: {self.backup_dir}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _cleanup_database_files(self):
        """Find and remove SQLite database files"""
        print("\n🗂️ Cleaning up SQLite database files...")

        found_files = []

        # Find all SQLite files
        for pattern in self.sqlite_files:
            file_path = self.project_root / pattern
            if '*' in pattern:
                # Handle glob patterns
                for found_file in glob.glob(str(file_path)):
                    found_files.append(Path(found_file))
            else:
                if file_path.exists():
                    found_files.append(file_path)

        if not found_files:
            print("  ✅ No SQLite database files found")
            return

        for file_path in found_files:
            relative_path = file_path.relative_to(self.project_root)
            print(f"  📁 Found: {relative_path}")

            if self.backup and not self.dry_run:
                backup_path = self.backup_dir / relative_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, backup_path)
                print(f"    💾 Backed up to: {backup_path}")

            if self.dry_run:
                print(f"    🔍 Would remove: {relative_path}")
            else:
                file_path.unlink()
                print(f"    🗑️ Removed: {relative_path}")

    def _handle_legacy_files(self):
        """Handle legacy Python files that reference SQLite"""
        print("\n📄 Handling legacy files...")

        for file_path_str in self.legacy_files:
            file_path = self.project_root / file_path_str

            if not file_path.exists():
                continue

            relative_path = file_path.relative_to(self.project_root)

            if file_path_str == "crypto_invoice_system/models/database.py":
                # Keep this file but add deprecation notice
                self._add_deprecation_notice(file_path)
                print(f"  📝 Added deprecation notice: {relative_path}")
            else:
                print(f"  ⚠️ Legacy file found: {relative_path}")

                if self.backup and not self.dry_run:
                    backup_path = self.backup_dir / relative_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, backup_path)
                    print(f"    💾 Backed up to: {backup_path}")

                # For now, just flag these files for manual review
                print(f"    👀 Manual review recommended for: {relative_path}")

    def _add_deprecation_notice(self, file_path):
        """Add deprecation notice to a file"""
        if self.dry_run:
            print(f"    🔍 Would add deprecation notice to: {file_path}")
            return

        try:
            content = file_path.read_text(encoding='utf-8')

            # Check if deprecation notice already exists
            if "DEPRECATED" in content:
                return

            # Add deprecation notice at the top
            deprecation_notice = '''#!/usr/bin/env python3
"""
⚠️  DEPRECATED: This file is deprecated after PostgreSQL migration
====================================================================

This SQLite-based database implementation has been replaced by:
- models/database_postgresql.py (PostgreSQL implementation)
- Centralized DatabaseManager in web_ui/database.py

This file is kept for reference only. Use database_postgresql.py for new development.
"""

'''

            # Insert after shebang if it exists, otherwise at the beginning
            lines = content.split('\n')
            if lines[0].startswith('#!'):
                # Insert after shebang
                lines.insert(1, deprecation_notice.strip())
            else:
                # Insert at beginning
                lines.insert(0, deprecation_notice.strip())

            file_path.write_text('\n'.join(lines), encoding='utf-8')

        except Exception as e:
            print(f"    ❌ Error adding deprecation notice: {e}")

    def _update_gitignore(self):
        """Update .gitignore to ignore SQLite files"""
        print("\n📝 Updating .gitignore...")

        gitignore_path = self.project_root / ".gitignore"

        sqlite_ignores = [
            "# SQLite databases (migrated to PostgreSQL)",
            "*.db",
            "*.sqlite",
            "*.sqlite3",
            "delta_transactions.db",
            "crypto_invoices.db",
            "invoices.db"
        ]

        if self.dry_run:
            print("  🔍 Would add SQLite ignore patterns to .gitignore")
            return

        try:
            if gitignore_path.exists():
                content = gitignore_path.read_text(encoding='utf-8')
            else:
                content = ""

            # Check if SQLite patterns already exist
            if "*.db" in content:
                print("  ✅ SQLite patterns already in .gitignore")
                return

            # Add SQLite patterns
            if content and not content.endswith('\n'):
                content += '\n'

            content += '\n' + '\n'.join(sqlite_ignores) + '\n'

            gitignore_path.write_text(content, encoding='utf-8')
            print("  ✅ Added SQLite ignore patterns to .gitignore")

        except Exception as e:
            print(f"  ❌ Error updating .gitignore: {e}")

def main():
    parser = argparse.ArgumentParser(description='Clean up obsolete SQLite files after PostgreSQL migration')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be removed without doing it')
    parser.add_argument('--backup', action='store_true', help='Create backup copies before removing files')

    args = parser.parse_args()

    # Run cleanup
    cleanup = SQLiteCleanup(dry_run=args.dry_run, backup=args.backup)
    cleanup.cleanup_all()

if __name__ == '__main__':
    main()