#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar dados do banco de dados
"""

import sqlite3
import os

def check_database():
    db_path = "advanced_invoices.db"

    if not os.path.exists(db_path):
        print("ERRO: Banco de dados nao encontrado!")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Verificar estrutura da tabela
        cursor.execute("PRAGMA table_info(invoices)")
        columns = cursor.fetchall()
        print("Estrutura da tabela 'invoices':")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        print()

        # Contar total de registros
        cursor.execute("SELECT COUNT(*) FROM invoices")
        total_count = cursor.fetchone()[0]
        print(f"Total de invoices: {total_count}")

        if total_count > 0:
            # Verificar registros com problemas
            cursor.execute("SELECT COUNT(*) FROM invoices WHERE total_amount IS NULL OR total_amount = 0")
            null_amounts = cursor.fetchone()[0]
            print(f"PROBLEMA: Invoices com valor nulo/zero: {null_amounts}")

            cursor.execute("SELECT COUNT(*) FROM invoices WHERE vendor_name IS NULL OR vendor_name = ''")
            null_vendors = cursor.fetchone()[0]
            print(f"PROBLEMA: Invoices com fornecedor nulo/vazio: {null_vendors}")

            cursor.execute("SELECT COUNT(*) FROM invoices WHERE business_unit = vendor_name")
            wrong_business_units = cursor.fetchone()[0]
            print(f"PROBLEMA: Invoices com business_unit igual ao vendor_name: {wrong_business_units}")

            # Mostrar alguns exemplos
            print("\nPrimeiros 5 registros:")
            cursor.execute("SELECT id, vendor_name, total_amount, currency, business_unit FROM invoices LIMIT 5")
            records = cursor.fetchall()
            for record in records:
                print(f"  ID: {record[0]}, Vendor: {record[1]}, Amount: {record[2]}, Currency: {record[3]}, Business Unit: {record[4]}")

            # Verificar se há registros com vendor_name igual ao business_unit
            print("\nRegistros com vendor_name = business_unit:")
            cursor.execute("SELECT id, vendor_name, business_unit FROM invoices WHERE vendor_name = business_unit LIMIT 3")
            problem_records = cursor.fetchall()
            for record in problem_records:
                print(f"  ID: {record[0]}, Vendor/Business Unit: {record[1]}")

        conn.close()

    except Exception as e:
        print(f"ERRO ao acessar banco de dados: {e}")

if __name__ == "__main__":
    check_database()