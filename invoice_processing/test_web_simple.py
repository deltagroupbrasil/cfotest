#!/usr/bin/env python3
"""
Teste simples de upload via web - sem unicode
"""

import requests
import os

def test_web_upload():
    url = "http://localhost:5006"
    test_file = "test_invoice_coinbase.csv"

    if not os.path.exists(test_file):
        print(f"ERRO: Arquivo {test_file} não encontrado!")
        return

    print(f"Testando upload do arquivo: {test_file}")

    try:
        with open(test_file, 'rb') as f:
            files = {'files': (test_file, f, 'text/csv')}
            response = requests.post(url, files=files)

            print(f"Status: {response.status_code}")
            print(f"Response size: {len(response.text)} chars")

            # Check se mostra página de sucesso
            if response.status_code == 200:
                if "processado" in response.text.lower() or "sucesso" in response.text.lower():
                    print("SUCCESS: Upload funcionou!")
                elif "nenhum arquivo selecionado" in response.text.lower():
                    print("ERROR: Interface mostra 'Nenhum arquivo selecionado'")
                elif len(response.text) > 30000:
                    print("SUCCESS: Página completa retornada (provável sucesso)")
                else:
                    print("WARNING: Status 200 mas resposta suspeita")
                    print("Primeiros 500 chars da resposta:")
                    print(response.text[:500])
            else:
                print(f"ERROR: Status {response.status_code}")

    except Exception as e:
        print(f"ERRO na requisição: {e}")

if __name__ == "__main__":
    test_web_upload()