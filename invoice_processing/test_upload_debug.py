#!/usr/bin/env python3
"""
Teste de upload para debug - simula o upload via web
"""

import requests
import os

def test_upload():
    # URL do servidor
    url = "http://localhost:5005"

    # Verificar se o arquivo de teste existe
    test_file = "test_invoice_coinbase.csv"
    if not os.path.exists(test_file):
        print(f"ERRO: Arquivo {test_file} não encontrado!")
        return

    print(f"Testando upload do arquivo: {test_file}")

    try:
        # Preparar o arquivo para upload
        with open(test_file, 'rb') as f:
            files = {'files': (test_file, f, 'text/csv')}

            # Fazer o POST request
            response = requests.post(url, files=files)

            print(f"Status Code: {response.status_code}")
            print(f"Response Length: {len(response.text)}")

            # Verificar se houve redirecionamento ou mensagem de sucesso
            if response.status_code == 200:
                if "sucesso" in response.text.lower() or "processado" in response.text.lower():
                    print("✅ Upload parece ter funcionado!")
                elif "nenhum arquivo selecionado" in response.text.lower():
                    print("❌ Erro: 'Nenhum arquivo selecionado' - problema no upload!")
                else:
                    print("⚠️  Upload completou mas não identificou se foi bem sucedido")
            else:
                print(f"❌ Erro HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ Erro ao fazer upload: {e}")

if __name__ == "__main__":
    test_upload()