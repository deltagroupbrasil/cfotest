#!/usr/bin/env python3
"""
Verificar dados no banco PostgreSQL southamerica-east1
"""
import os
import psycopg2
import time
from datetime import datetime

# Configurações para southamerica-east1
DB_HOST = "34.39.143.82"
DB_PORT = 5432
DB_NAME = "delta_cfo"
DB_USER = "delta_user"
DB_PASSWORD = "nWr0Y8bU51ypLjMIfx8bTe+V/1iOV59r90T8wJEsSGo="

def check_data():
    """Verificar dados nas tabelas"""
    try:
        print("=== Conectando ao banco PostgreSQL ===")
        print(f"Host: {DB_HOST}")
        print(f"Database: {DB_NAME}")
        print()

        # Conectar ao banco
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        with conn:
            with conn.cursor() as cur:
                # Verificar tabelas existentes
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """)

                tables = cur.fetchall()
                print("=== TABELAS EXISTENTES ===")
                for table in tables:
                    print(f"- {table[0]}")
                print()

                # Verificar dados na tabela transactions
                if any('transactions' in str(table) for table in tables):
                    print("=== DADOS NA TABELA TRANSACTIONS ===")

                    # Contar registros
                    cur.execute("SELECT COUNT(*) FROM transactions;")
                    count = cur.fetchone()[0]
                    print(f"Total de registros: {count}")

                    if count > 0:
                        # Mostrar registros mais recentes
                        cur.execute("""
                            SELECT transaction_id, date, amount, description, category
                            FROM transactions
                            ORDER BY date DESC, transaction_id DESC
                            LIMIT 10;
                        """)

                        print("\n=== ÚLTIMOS 10 REGISTROS ===")
                        records = cur.fetchall()
                        for record in records:
                            tid, date, amount, desc, cat = record
                            print(f"ID: {tid}")
                            print(f"Data: {date}")
                            print(f"Valor: R$ {amount}")
                            print(f"Descrição: {desc}")
                            print(f"Categoria: {cat}")
                            print("-" * 40)
                    else:
                        print("Nenhum registro encontrado na tabela transactions.")

                else:
                    print("Tabela 'transactions' não encontrada.")

                # Verificar outras tabelas também
                for table in tables:
                    table_name = table[0]
                    if table_name != 'transactions':
                        cur.execute(f"SELECT COUNT(*) FROM {table_name};")
                        count = cur.fetchone()[0]
                        print(f"\nTabela '{table_name}': {count} registros")

        conn.close()
        print(f"\n=== Verificação concluída em {datetime.now()} ===")
        return True

    except Exception as e:
        print(f"ERRO ao verificar dados: {e}")
        return False

if __name__ == "__main__":
    check_data()