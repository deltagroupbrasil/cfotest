#!/usr/bin/env python3
"""
Teste para validar a funcionalidade de edição de invoices
"""

import requests
import json

def test_edit_functionality():
    """Testa se a edição de invoices está funcionando"""
    base_url = "http://localhost:5007"

    print("Testando funcionalidade de edicao de invoices...")

    # Primeiro, vamos testar se conseguimos acessar a API de dados do invoice
    try:
        # Teste 1: Verificar se existe algum invoice na base
        response = requests.get(f"{base_url}/")
        print(f"OK Pagina principal acessivel: {response.status_code}")

        # Buscar invoices na página para pegar um ID
        if "No invoices found" not in response.text:
            print("OK Existem invoices na base de dados")

            # Vamos simular um teste de edição
            # Usando ID real do Coinbase Pro
            test_invoice_id = "5ced2bd8"

            # Teste 2: Buscar dados de um invoice específico
            get_response = requests.get(f"{base_url}/api/invoice/{test_invoice_id}")
            print(f"Busca de invoice ID {test_invoice_id}: {get_response.status_code}")

            if get_response.status_code == 200:
                invoice_data = get_response.json()
                print("OK Dados do invoice recuperados com sucesso")
                print(f"   Dados: {json.dumps(invoice_data.get('data', {}), indent=2)}")

                # Teste 3: Tentar atualizar o invoice
                updated_data = {
                    "invoice_number": invoice_data.get('data', {}).get('invoice_number', 'TEST-001'),
                    "vendor_name": "Fornecedor Teste Atualizado",
                    "total_amount": 999.99,
                    "currency": "USD",
                    "business_unit": "Test Unit Updated",
                    "category": "Testing Updated"
                }

                update_response = requests.put(
                    f"{base_url}/api/invoice/{test_invoice_id}/update",
                    headers={'Content-Type': 'application/json'},
                    json=updated_data
                )

                print(f"Atualizacao do invoice: {update_response.status_code}")

                if update_response.status_code == 200:
                    print("OK Invoice atualizado com sucesso!")

                    # Verificar se a atualização foi salva
                    verify_response = requests.get(f"{base_url}/api/invoice/{test_invoice_id}")
                    if verify_response.status_code == 200:
                        verify_data = verify_response.json()
                        print("OK Verificacao pos-atualizacao:")
                        print(f"   Fornecedor: {verify_data.get('data', {}).get('vendor_name')}")
                        print(f"   Valor: {verify_data.get('data', {}).get('total_amount')}")
                else:
                    print(f"ERRO na atualizacao: {update_response.text}")

            elif get_response.status_code == 404:
                print("INFO Invoice ID 1 nao encontrado - base de dados vazia")
            else:
                print(f"ERRO ao buscar invoice: {get_response.text}")

        else:
            print("INFO Nenhum invoice encontrado na base de dados")
            print("   Para testar a edicao, primeiro faca upload de um arquivo")

    except requests.exceptions.ConnectionError:
        print("ERRO: Servidor nao esta rodando na porta 5007")
        print("   Certifique-se de que o servidor esta ativo")

    except Exception as e:
        print(f"ERRO inesperado: {e}")

if __name__ == "__main__":
    test_edit_functionality()