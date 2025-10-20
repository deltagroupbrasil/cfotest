#!/bin/bash
# ===============================================
# Delta CFO Agent - Cloud SQL Validation Script
# ===============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo -e "${BLUE}"
echo "==============================================="
echo "🔍 Delta CFO Agent - Validação do Setup"
echo "==============================================="
echo -e "${NC}"

# Load configuration
if [ -f ".env.production" ]; then
    source .env.production
    print_success "Configuração carregada de .env.production"
else
    print_warning "Arquivo .env.production não encontrado"
    read -p "Digite o PROJECT_ID: " GOOGLE_CLOUD_PROJECT
    read -p "Digite a URL do serviço: " SERVICE_URL
fi

echo ""
print_info "Projeto: $GOOGLE_CLOUD_PROJECT"
print_info "Service URL: $SERVICE_URL"

# Test 1: Cloud SQL Instance
echo ""
echo "🔍 Teste 1: Verificando instância Cloud SQL"

if [ ! -z "$CLOUD_SQL_CONNECTION_NAME" ]; then
    INSTANCE_NAME=$(echo $CLOUD_SQL_CONNECTION_NAME | cut -d: -f3)

    if gcloud sql instances describe $INSTANCE_NAME --project=$GOOGLE_CLOUD_PROJECT &>/dev/null; then
        STATUS=$(gcloud sql instances describe $INSTANCE_NAME --project=$GOOGLE_CLOUD_PROJECT --format="value(state)")
        if [ "$STATUS" = "RUNNABLE" ]; then
            print_success "Instância Cloud SQL está rodando"
        else
            print_error "Instância Cloud SQL não está ativa (Status: $STATUS)"
        fi
    else
        print_error "Instância Cloud SQL não encontrada"
    fi
else
    print_warning "CLOUD_SQL_CONNECTION_NAME não definido"
fi

# Test 2: Secrets
echo ""
echo "🔍 Teste 2: Verificando secrets"

if gcloud secrets describe db_password --project=$GOOGLE_CLOUD_PROJECT &>/dev/null; then
    print_success "Secret db_password existe"
else
    print_error "Secret db_password não encontrado"
fi

if gcloud secrets describe anthropic_key --project=$GOOGLE_CLOUD_PROJECT &>/dev/null; then
    print_success "Secret anthropic_key existe"
else
    print_error "Secret anthropic_key não encontrado"
fi

# Test 3: Cloud Run Service
echo ""
echo "🔍 Teste 3: Verificando serviço Cloud Run"

SERVICE_NAME=$(echo $SERVICE_URL | sed 's|https://||' | sed 's|-[^-]*\..*||')
REGION=$(echo $SERVICE_URL | sed 's|.*-\([^.]*\)\..*|\1|')

if gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --project=$GOOGLE_CLOUD_PROJECT &>/dev/null; then
    print_success "Serviço Cloud Run existe"

    # Check service status
    SERVICE_STATUS=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --project=$GOOGLE_CLOUD_PROJECT --format="value(status.conditions[0].status)")
    if [ "$SERVICE_STATUS" = "True" ]; then
        print_success "Serviço Cloud Run está ativo"
    else
        print_error "Serviço Cloud Run não está ativo"
    fi
else
    print_error "Serviço Cloud Run não encontrado"
fi

# Test 4: API Endpoints
echo ""
echo "🔍 Teste 4: Testando endpoints da API"

if [ ! -z "$SERVICE_URL" ]; then
    # Test health endpoint
    echo "Testando endpoint de saúde..."
    if curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/health" | grep -q "200"; then
        print_success "Endpoint /health respondendo (200)"
    else
        print_error "Endpoint /health não está funcionando"
    fi

    # Test stats endpoint
    echo "Testando endpoint de estatísticas..."
    STATS_RESPONSE=$(curl -s "$SERVICE_URL/api/stats")
    if echo "$STATS_RESPONSE" | grep -q "total_transactions"; then
        print_success "Endpoint /api/stats respondendo corretamente"

        # Show stats
        TOTAL_TX=$(echo "$STATS_RESPONSE" | grep -o '"total_transactions":[0-9]*' | cut -d: -f2)
        print_info "Total de transações no banco: $TOTAL_TX"
    else
        print_error "Endpoint /api/stats não está retornando dados corretos"
        echo "Resposta recebida: $STATS_RESPONSE"
    fi

    # Test transactions endpoint
    echo "Testando endpoint de transações..."
    if curl -s "$SERVICE_URL/api/transactions" | grep -q "transactions"; then
        print_success "Endpoint /api/transactions respondendo"
    else
        print_error "Endpoint /api/transactions não está funcionando"
    fi
else
    print_warning "SERVICE_URL não definida - pulando testes de API"
fi

# Test 5: Database Connection
echo ""
echo "🔍 Teste 5: Testando conexão com banco de dados"

if [ ! -z "$CLOUD_SQL_CONNECTION_NAME" ] && [ ! -z "$DB_NAME" ] && [ ! -z "$DB_USER" ]; then
    # Try to connect using cloud_sql_proxy
    if [ -f "./cloud_sql_proxy" ]; then
        echo "Testando conexão direta com PostgreSQL..."

        ./cloud_sql_proxy -instances=$CLOUD_SQL_CONNECTION_NAME=tcp:5433 &
        PROXY_PID=$!
        sleep 3

        # Get password from secret
        DB_PASSWORD=$(gcloud secrets versions access latest --secret="db_password" --project=$GOOGLE_CLOUD_PROJECT)

        # Test connection
        if PGPASSWORD=$DB_PASSWORD psql "host=127.0.0.1 port=5433 user=$DB_USER dbname=$DB_NAME sslmode=disable" -c "SELECT 1;" &>/dev/null; then
            print_success "Conexão direta com PostgreSQL funcionando"

            # Check tables
            TABLE_COUNT=$(PGPASSWORD=$DB_PASSWORD psql "host=127.0.0.1 port=5433 user=$DB_USER dbname=$DB_NAME sslmode=disable" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')
            print_info "Tabelas encontradas: $TABLE_COUNT"

        else
            print_error "Não foi possível conectar diretamente ao PostgreSQL"
        fi

        kill $PROXY_PID 2>/dev/null || true
    else
        print_warning "cloud_sql_proxy não encontrado - baixe com o script de setup"
    fi
else
    print_warning "Informações de conexão incompletas"
fi

# Test 6: Logs Analysis
echo ""
echo "🔍 Teste 6: Analisando logs recentes"

if gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" --limit=10 --project=$GOOGLE_CLOUD_PROJECT --format="table(timestamp,severity,textPayload)" &>/dev/null; then
    print_success "Logs do Cloud Run acessíveis"

    # Check for errors in recent logs
    ERROR_COUNT=$(gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND severity>=ERROR" --limit=100 --project=$GOOGLE_CLOUD_PROJECT --format="value(textPayload)" | wc -l)

    if [ $ERROR_COUNT -gt 0 ]; then
        print_warning "Encontrados $ERROR_COUNT erros nos logs recentes"
        echo "Para ver erros: gcloud logs read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND severity>=ERROR\" --limit=10 --project=$GOOGLE_CLOUD_PROJECT"
    else
        print_success "Nenhum erro encontrado nos logs recentes"
    fi
else
    print_warning "Não foi possível acessar logs"
fi

# Performance Test
echo ""
echo "🔍 Teste 7: Teste de performance"

if [ ! -z "$SERVICE_URL" ]; then
    echo "Medindo tempo de resposta..."

    # Test response time
    RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$SERVICE_URL/api/stats")

    if [ $(echo "$RESPONSE_TIME < 5.0" | bc -l) -eq 1 ]; then
        print_success "Tempo de resposta OK: ${RESPONSE_TIME}s"
    else
        print_warning "Tempo de resposta lento: ${RESPONSE_TIME}s"
    fi
fi

# Summary
echo ""
echo -e "${BLUE}==============================================="
echo "📋 Resumo da Validação"
echo "===============================================${NC}"

echo ""
echo "🔧 Comandos úteis:"
echo "   • Ver logs: gcloud logs tail --project=$GOOGLE_CLOUD_PROJECT"
echo "   • Status instância: gcloud sql instances describe $INSTANCE_NAME --project=$GOOGLE_CLOUD_PROJECT"
echo "   • Status serviço: gcloud run services describe $SERVICE_NAME --region $REGION --project=$GOOGLE_CLOUD_PROJECT"
echo "   • Teste manual: curl $SERVICE_URL/api/stats"

echo ""
echo "💰 Monitoramento de custos:"
echo "   • Console: https://console.cloud.google.com/billing/projects/$GOOGLE_CLOUD_PROJECT"
echo "   • Cloud SQL: https://console.cloud.google.com/sql/instances?project=$GOOGLE_CLOUD_PROJECT"

echo ""
print_success "Validação completa!"