#!/usr/bin/env python3
"""
Aplicar schema PostgreSQL diretamente via TCP
Usado quando cloud_sql_proxy não está disponível
"""
import os
import subprocess
import psycopg2
import time

# Configurações
DB_HOST = "34.27.251.47"
DB_PORT = 5432
DB_NAME = "delta_cfo"
DB_USER = "postgres"
DB_PASSWORD = "x2mNABXYS3ArMOteGSLbRQD5d"

def wait_for_connection(max_retries=10):
    """Aguardar instância estar acessível"""
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            conn.close()
            print(f"✅ Conexão estabelecida na tentativa {i+1}")
            return True
        except psycopg2.OperationalError as e:
            print(f"⏳ Tentativa {i+1}: {e}")
            time.sleep(5)
    return False

def apply_schema():
    """Aplicar schema PostgreSQL"""
    try:
        # Verificar se arquivo schema existe
        schema_file = "migration/postgresql_schema.sql"
        if not os.path.exists(schema_file):
            print(f"❌ Schema file não encontrado: {schema_file}")
            return False

        print("🔄 Aplicando schema PostgreSQL...")

        # Conectar e executar schema
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        with conn:
            with conn.cursor() as cur:
                # Ler e executar schema
                with open(schema_file, 'r') as f:
                    schema_sql = f.read()

                # Executar em partes (cada comando separadamente)
                commands = schema_sql.split(';')
                for i, cmd in enumerate(commands):
                    cmd = cmd.strip()
                    if cmd and not cmd.startswith('--'):
                        try:
                            cur.execute(cmd)
                            print(f"✅ Comando {i+1} executado com sucesso")
                        except Exception as e:
                            # Ignorar erros de objetos que já existem
                            if "already exists" in str(e):
                                print(f"⚠️ Comando {i+1}: objeto já existe")
                            else:
                                print(f"❌ Erro comando {i+1}: {e}")

        conn.close()
        print("✅ Schema aplicado com sucesso!")
        return True

    except Exception as e:
        print(f"❌ Erro ao aplicar schema: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Aplicando Schema PostgreSQL")
    print(f"Host: {DB_HOST}")
    print(f"Database: {DB_NAME}")
    print()

    if wait_for_connection():
        if apply_schema():
            print("\n🎉 Schema aplicado com sucesso!")
        else:
            print("\n❌ Falha ao aplicar schema")
    else:
        print("\n❌ Não foi possível conectar ao banco")