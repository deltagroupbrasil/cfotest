#!/usr/bin/env python3
"""
Criar tabelas essenciais no PostgreSQL - Uma por vez
Testado em produção: southamerica-east1 (Cloud SQL)
"""
import psycopg2

# Configurações usando variáveis de ambiente (mais seguro)
import os
DB_HOST = os.getenv('DB_HOST', '34.39.143.82')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'delta_cfo')
DB_USER = os.getenv('DB_USER', 'delta_user')
DB_PASSWORD = os.getenv('DB_PASSWORD')  # DEVE vir de variável de ambiente

if not DB_PASSWORD:
    print("❌ ERROR: DB_PASSWORD environment variable not set!")
    print("💡 Set it with: export DB_PASSWORD=your_password")
    exit(1)

def create_tables():
    """Criar tabelas principais uma por vez"""

    tables = [
        # Tabela transactions (principal)
        """
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            date DATE,
            amount DECIMAL(15, 2),
            description TEXT,
            category TEXT,
            type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,

        # Tabela invoices
        """
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id TEXT PRIMARY KEY,
            invoice_number TEXT UNIQUE,
            vendor_name TEXT,
            invoice_date DATE,
            due_date DATE,
            total_amount DECIMAL(15, 2),
            status TEXT DEFAULT 'pending',
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,

        # Tabela categories
        """
        CREATE TABLE IF NOT EXISTS categories (
            category_id SERIAL PRIMARY KEY,
            category_name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,

        # Tabela transaction_history
        """
        CREATE TABLE IF NOT EXISTS transaction_history (
            history_id SERIAL PRIMARY KEY,
            transaction_id TEXT REFERENCES transactions(transaction_id),
            old_values JSONB,
            new_values JSONB,
            changed_by TEXT,
            change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,

        # Índices importantes
        "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_amount ON transactions(amount)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)"
    ]

    try:
        print("=== Conectando ao banco PostgreSQL ===")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True  # Cada comando será commitado automaticamente

        print("Conectado com sucesso!")

        with conn.cursor() as cur:
            for i, sql in enumerate(tables, 1):
                try:
                    print(f"Executando comando {i}...")
                    cur.execute(sql)
                    print(f"Comando {i} executado com sucesso")
                except Exception as e:
                    print(f"Erro no comando {i}: {e}")

        conn.close()
        print("\nTodas as tabelas foram criadas/verificadas!")
        return True

    except Exception as e:
        print(f"Erro de conexao: {e}")
        return False

if __name__ == "__main__":
    create_tables()