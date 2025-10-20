
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
