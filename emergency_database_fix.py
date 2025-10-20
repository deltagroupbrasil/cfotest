#!/usr/bin/env python3
"""
Emergency Database Lock Fix
Correção definitiva para erros de "database locked" em process_invoice_with_claude
"""

import os
import sqlite3
import time
import random
from contextlib import contextmanager

@contextmanager
def get_robust_connection(db_path, max_retries=5):
    """
    Connection manager com retry automático e configurações otimizadas
    """
    conn = None
    last_error = None

    for attempt in range(max_retries):
        try:
            # Configuração robusta de conexão
            conn = sqlite3.connect(
                db_path,
                timeout=60.0,  # Timeout mais longo
                check_same_thread=False,
                isolation_level=None  # Autocommit mode
            )

            # Configurações críticas para prevenir locks
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=60000")  # 60 segundos
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=memory")
            conn.execute("PRAGMA locking_mode=NORMAL")
            conn.execute("PRAGMA wal_autocheckpoint=1000")

            # Configurar row factory
            conn.row_factory = sqlite3.Row

            print(f"Database connection established (attempt {attempt + 1})")
            yield conn
            return

        except sqlite3.OperationalError as e:
            last_error = e
            if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                # Backoff exponencial com jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Database locked, retrying in {wait_time:.2f}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                print(f"Database error after {attempt + 1} attempts: {e}")
                raise
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

def execute_safe_query(db_path, query, params=None, fetch=False):
    """
    Executa query com proteção contra locks
    """
    with get_robust_connection(db_path) as conn:
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if fetch:
            return cursor.fetchall()
        else:
            conn.commit()
            return cursor.rowcount

def force_database_unlock(db_path):
    """
    Força desbloqueio do banco de dados
    """
    print(f"Force unlocking database: {db_path}")

    try:
        # Remove arquivos de lock se existirem
        lock_files = [
            f"{db_path}-wal",
            f"{db_path}-shm",
            f"{db_path}-journal"
        ]

        for lock_file in lock_files:
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                    print(f"Removed lock file: {lock_file}")
                except Exception as e:
                    print(f"Warning: Could not remove {lock_file}: {e}")

        # Força WAL checkpoint para liberar locks
        with sqlite3.connect(db_path, timeout=30.0) as conn:
            conn.execute("PRAGMA wal_checkpoint(RESTART)")
            conn.execute("PRAGMA journal_mode=WAL")  # Re-enable WAL
            print("Forced WAL checkpoint and re-enabled WAL mode")

        return True
    except Exception as e:
        print(f"Error forcing unlock: {e}")
        return False

def patch_process_invoice_function():
    """
    Aplica patch diretamente na função problemática
    """
    app_db_path = "web_ui/app_db.py"

    if not os.path.exists(app_db_path):
        print(f"Error: {app_db_path} not found")
        return False

    try:
        print("Patching process_invoice_with_claude function...")

        # Read current content
        with open(app_db_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find and replace the problematic connection code
        old_pattern = """        # Save to database
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO invoices ("""

        new_pattern = """        # Save to database with robust connection handling
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = get_db_connection()
                conn.execute('''
                    INSERT INTO invoices ("""

        if old_pattern in content:
            # Replace the connection opening
            content = content.replace(old_pattern, new_pattern)

            # Find the commit/close and wrap it in retry logic
            commit_pattern = """        conn.commit()
        conn.close()

        print(f"Invoice processed successfully: {invoice_data['invoice_number']}")
        return invoice_data"""

            commit_replacement = """                conn.commit()
                conn.close()
                print(f"Invoice processed successfully: {invoice_data['invoice_number']}")
                return invoice_data
            except sqlite3.OperationalError as e:
                if conn:
                    conn.close()
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"Database locked during invoice insert, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"Database error after {attempt + 1} attempts: {e}")
                    return {'error': f'Database locked after {attempt + 1} attempts: {str(e)}'}
            except Exception as e:
                if conn:
                    conn.close()
                print(f"Unexpected error during invoice insert: {e}")
                return {'error': str(e)}"""

            if commit_pattern in content:
                content = content.replace(commit_pattern, commit_replacement)

                # Add required import at the top
                if "import time" not in content:
                    import_line = "import time\n"
                    # Find first import and add after it
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith('import ') and 'os' in line:
                            lines.insert(i + 1, 'import time')
                            break
                    content = '\n'.join(lines)

                # Create backup
                backup_path = f"{app_db_path}.backup_emergency"
                if not os.path.exists(backup_path):
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        with open(app_db_path, 'r', encoding='utf-8') as orig:
                            f.write(orig.read())

                # Write patched version
                with open(app_db_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                print("SUCCESS: Patched process_invoice_with_claude function")
                return True

        print("WARNING: Could not find patterns to patch")
        return False

    except Exception as e:
        print(f"ERROR: Failed to patch process_invoice_with_claude: {e}")
        return False

def main():
    """
    Aplicação da correção de emergência
    """
    print("Emergency Database Lock Fix")
    print("=" * 40)

    # 1. Force unlock main databases
    databases = [
        "web_ui/delta_transactions.db",
        "crypto_pricing.db",
        "crypto_invoice_system/crypto_invoices.db"
    ]

    print("\n1. Forcing database unlocks...")
    for db in databases:
        if os.path.exists(db):
            force_database_unlock(db)

    # 2. Patch the problematic function
    print("\n2. Patching process_invoice_with_claude function...")
    if patch_process_invoice_function():
        print("Function patched successfully")
    else:
        print("Function patching failed")

    # 3. Test database connections
    print("\n3. Testing database connections...")
    for db in databases:
        if os.path.exists(db):
            try:
                result = execute_safe_query(db, "SELECT COUNT(*) FROM sqlite_master", fetch=True)
                print(f"SUCCESS: {db} - {result[0][0]} tables")
            except Exception as e:
                print(f"ERROR: {db} - {e}")

    print("\nEmergency fix completed!")
    print("\nRestart your web application:")
    print("cd web_ui && python app_db.py")

if __name__ == "__main__":
    main()