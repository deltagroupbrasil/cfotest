#!/usr/bin/env python3
"""
Database Setup & Lock Prevention
Configura bases de dados e previne locks futuros
"""

import os
import sys
import sqlite3
from pathlib import Path

def setup_main_database():
    """Setup main transaction database"""
    db_path = Path("web_ui/delta_transactions.db")

    # Create directory if needed
    db_path.parent.mkdir(exist_ok=True)

    print(f"Setting up main database: {db_path}")

    try:
        with sqlite3.connect(str(db_path), timeout=30.0) as conn:
            # Enable WAL mode
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA synchronous=NORMAL")

            # Create transactions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id TEXT PRIMARY KEY,
                    date TEXT,
                    description TEXT,
                    amount REAL,
                    currency TEXT,
                    usd_equivalent REAL,
                    classified_entity TEXT,
                    justification TEXT,
                    confidence REAL,
                    classification_reason TEXT,
                    origin TEXT,
                    destination TEXT,
                    identifier TEXT,
                    source_file TEXT,
                    crypto_amount TEXT,
                    conversion_note TEXT
                )
            """)

            # Test the configuration
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]

            print(f"SUCCESS: Main database ready (mode: {mode})")
            return True

    except Exception as e:
        print(f"ERROR: Failed to setup main database: {e}")
        return False

def setup_crypto_pricing_database():
    """Setup crypto pricing database"""
    db_path = Path("crypto_pricing.db")

    print(f"Setting up crypto pricing database: {db_path}")

    try:
        with sqlite3.connect(str(db_path), timeout=30.0) as conn:
            # Enable WAL mode
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA synchronous=NORMAL")

            # Create pricing table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS historic_prices (
                    date TEXT,
                    symbol TEXT,
                    price_usd REAL,
                    PRIMARY KEY (date, symbol)
                )
            """)

            print("SUCCESS: Crypto pricing database ready")
            return True

    except Exception as e:
        print(f"ERROR: Failed to setup crypto pricing database: {e}")
        return False

def setup_invoice_database():
    """Setup invoice database"""
    db_path = Path("crypto_invoice_system/crypto_invoices.db")

    # Create directory if needed
    db_path.parent.mkdir(exist_ok=True)

    print(f"Setting up invoice database: {db_path}")

    try:
        with sqlite3.connect(str(db_path), timeout=30.0) as conn:
            # Enable WAL mode
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA synchronous=NORMAL")

            # Create basic invoices table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id TEXT PRIMARY KEY,
                    invoice_number TEXT UNIQUE NOT NULL,
                    date TEXT NOT NULL,
                    vendor_name TEXT NOT NULL,
                    total_amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            print("SUCCESS: Invoice database ready")
            return True

    except Exception as e:
        print(f"ERROR: Failed to setup invoice database: {e}")
        return False

def patch_web_app():
    """Patch web_ui/app_db.py to use better connection handling"""
    app_path = Path("web_ui/app_db.py")

    if not app_path.exists():
        print("WARNING: web_ui/app_db.py not found - cannot patch")
        return False

    print("Patching web_ui/app_db.py for better database handling...")

    try:
        # Read current content
        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if already patched
        if "PRAGMA busy_timeout=30000" in content:
            print("Already patched - skipping")
            return True

        # Find the get_db_connection function and add timeout settings
        old_pattern = "conn = sqlite3.connect(DB_PATH)"
        new_pattern = """conn = sqlite3.connect(DB_PATH, timeout=30.0)
    # Prevent database locks
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=WAL")"""

        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)

            # Create backup
            backup_path = f"{app_path}.backup_original"
            if not Path(backup_path).exists():
                with open(backup_path, 'w', encoding='utf-8') as f:
                    # Read original again for backup
                    with open(app_path, 'r', encoding='utf-8') as orig:
                        f.write(orig.read())

            # Write patched version
            with open(app_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print("SUCCESS: Patched web_ui/app_db.py")
            return True
        else:
            print("WARNING: Could not find pattern to patch in app_db.py")
            return False

    except Exception as e:
        print(f"ERROR: Failed to patch web_ui/app_db.py: {e}")
        return False

def patch_crypto_pricing():
    """Patch crypto_pricing.py for better connection handling"""
    pricing_path = Path("crypto_pricing.py")

    if not pricing_path.exists():
        print("WARNING: crypto_pricing.py not found - cannot patch")
        return False

    print("Patching crypto_pricing.py...")

    try:
        with open(pricing_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if already patched
        if "timeout=30.0" in content:
            print("Already patched - skipping")
            return True

        # Replace all sqlite3.connect calls
        old_pattern = "sqlite3.connect(self.db_path)"
        new_pattern = "sqlite3.connect(self.db_path, timeout=30.0)"

        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)

            # Backup and save
            backup_path = f"{pricing_path}.backup_original"
            if not Path(backup_path).exists():
                with open(backup_path, 'w', encoding='utf-8') as f:
                    with open(pricing_path, 'r', encoding='utf-8') as orig:
                        f.write(orig.read())

            with open(pricing_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print("SUCCESS: Patched crypto_pricing.py")
            return True

    except Exception as e:
        print(f"ERROR: Failed to patch crypto_pricing.py: {e}")
        return False

def create_usage_guide():
    """Create a usage guide for preventing database locks"""
    guide_content = """
# Database Lock Prevention Guide

## Problem Solved
This setup prevents "database locked" errors in DeltaCFOAgent by:
- Enabling WAL (Write-Ahead Logging) mode for better concurrency
- Setting 30-second timeout for locked database scenarios
- Patching existing code to use safer connection patterns

## Files Modified
- web_ui/app_db.py (patched for better connection handling)
- crypto_pricing.py (patched for timeouts)

## Databases Created
- web_ui/delta_transactions.db (main transactions)
- crypto_pricing.db (cryptocurrency prices)
- crypto_invoice_system/crypto_invoices.db (invoice system)

## Best Practices Going Forward

### 1. Always use timeouts
```python
conn = sqlite3.connect('database.db', timeout=30.0)
```

### 2. Use context managers when possible
```python
with sqlite3.connect('database.db', timeout=30.0) as conn:
    # Your operations here
    pass  # Connection automatically closed
```

### 3. Set WAL mode for new databases
```python
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=30000")
```

### 4. Avoid long-running transactions
- Commit frequently
- Break large operations into smaller chunks

### 5. Check for running processes
Before running scripts that access databases, make sure no other
Python processes are using the same database files.

## Troubleshooting

If you still get "database locked" errors:
1. Check for running Python processes: `tasklist | findstr python`
2. Remove lock files: `del *.db-wal *.db-shm *.db-journal`
3. Run this setup script again: `python setup_database_fix.py`

## Usage
Simply run your application normally:
```bash
cd web_ui && python app_db.py
```

The patches will automatically prevent most database lock issues.
"""

    with open("DATABASE_LOCK_FIX_GUIDE.md", "w") as f:
        f.write(guide_content)

    print("Created DATABASE_LOCK_FIX_GUIDE.md")

def main():
    """Main setup function"""
    print("DeltaCFOAgent Database Setup & Lock Prevention")
    print("=" * 50)

    success_count = 0
    total_tasks = 6

    # Setup databases
    if setup_main_database():
        success_count += 1

    if setup_crypto_pricing_database():
        success_count += 1

    if setup_invoice_database():
        success_count += 1

    # Patch existing code
    if patch_web_app():
        success_count += 1

    if patch_crypto_pricing():
        success_count += 1

    # Create guide
    create_usage_guide()
    success_count += 1

    # Summary
    print(f"\nSUMMARY:")
    print(f"  Completed: {success_count}/{total_tasks} tasks")

    if success_count == total_tasks:
        print("\nSUCCESS: Database lock prevention setup complete!")
        print("\nNext steps:")
        print("1. Test the web application: cd web_ui && python app_db.py")
        print("2. Check for any remaining lock issues")
        print("3. Read DATABASE_LOCK_FIX_GUIDE.md for best practices")
        return True
    else:
        print("\nWARNING: Some tasks failed - check error messages above")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)