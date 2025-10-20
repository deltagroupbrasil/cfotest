#!/bin/bash
# ===============================================
# Delta CFO Agent - Cloud SQL Automated Setup
# ===============================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Progress indicators
STEP=1
TOTAL_STEPS=12

print_step() {
    echo -e "${BLUE}[${STEP}/${TOTAL_STEPS}] $1${NC}"
    STEP=$((STEP + 1))
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Default configuration
DEFAULT_PROJECT_ID=""
DEFAULT_REGION="us-central1"
DEFAULT_INSTANCE_NAME="delta-cfo-db"
DEFAULT_DB_NAME="delta_cfo"
DEFAULT_DB_USER="delta_user"
DEFAULT_SERVICE_NAME="delta-cfo-agent"

echo -e "${BLUE}"
echo "==============================================="
echo "🚀 Delta CFO Agent - Cloud SQL Setup"
echo "==============================================="
echo -e "${NC}"

# Step 1: Configuration
print_step "Configuração inicial"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "Google Cloud CLI não está instalado!"
    echo "Instale em: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get current project or ask user
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
if [[ -z "$CURRENT_PROJECT" ]]; then
    echo -e "${YELLOW}Nenhum projeto configurado no gcloud.${NC}"
    echo "Projetos disponíveis:"
    gcloud projects list --format="table(projectId,name)" 2>/dev/null || echo "Execute 'gcloud auth login' primeiro"

    read -p "Digite o PROJECT_ID: " PROJECT_ID
    if [[ -z "$PROJECT_ID" ]]; then
        print_error "PROJECT_ID é obrigatório!"
        exit 1
    fi

    gcloud config set project $PROJECT_ID
else
    echo "Projeto atual: $CURRENT_PROJECT"
    read -p "Usar este projeto? (y/N): " use_current
    if [[ $use_current =~ ^[Yy]$ ]]; then
        PROJECT_ID=$CURRENT_PROJECT
    else
        read -p "Digite o PROJECT_ID: " PROJECT_ID
        gcloud config set project $PROJECT_ID
    fi
fi

# Get other configuration
read -p "Região (default: $DEFAULT_REGION): " REGION
REGION=${REGION:-$DEFAULT_REGION}

read -p "Nome da instância (default: $DEFAULT_INSTANCE_NAME): " INSTANCE_NAME
INSTANCE_NAME=${INSTANCE_NAME:-$DEFAULT_INSTANCE_NAME}

read -p "Nome do database (default: $DEFAULT_DB_NAME): " DB_NAME
DB_NAME=${DB_NAME:-$DEFAULT_DB_NAME}

read -p "Usuário do database (default: $DEFAULT_DB_USER): " DB_USER
DB_USER=${DB_USER:-$DEFAULT_DB_USER}

# Generate secure password
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
print_success "Senha do banco gerada automaticamente"

read -p "Nome do serviço Cloud Run (default: $DEFAULT_SERVICE_NAME): " SERVICE_NAME
SERVICE_NAME=${SERVICE_NAME:-$DEFAULT_SERVICE_NAME}

echo ""
echo "📋 Configuração:"
echo "   Projeto: $PROJECT_ID"
echo "   Região: $REGION"
echo "   Instância: $INSTANCE_NAME"
echo "   Database: $DB_NAME"
echo "   Usuário: $DB_USER"
echo "   Serviço: $SERVICE_NAME"
echo ""

read -p "Confirmar configuração? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "Setup cancelado."
    exit 1
fi

# Step 2: Enable APIs
print_step "Habilitando APIs necessárias"
gcloud services enable sqladmin.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
print_success "APIs habilitadas"

# Step 3: Create Cloud SQL instance
print_step "Criando instância Cloud SQL"

# Check if instance already exists
if gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID &>/dev/null; then
    print_warning "Instância $INSTANCE_NAME já existe"
else
    echo "Criando instância PostgreSQL (isso pode levar alguns minutos)..."
    gcloud sql instances create $INSTANCE_NAME \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-type=SSD \
        --storage-size=10GB \
        --storage-auto-increase \
        --backup-start-time=03:00 \
        --maintenance-window-day=SUN \
        --maintenance-window-hour=04 \
        --availability-type=zonal \
        --no-assign-ip \
        --project=$PROJECT_ID

    print_success "Instância Cloud SQL criada"
fi

# Step 4: Wait for instance to be ready
print_step "Aguardando instância ficar ativa"
echo "Verificando status da instância..."
max_wait=300  # 5 minutes
wait_time=0
while [ $wait_time -lt $max_wait ]; do
    instance_status=$(gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID --format="value(state)" 2>/dev/null || echo "PENDING")
    if [ "$instance_status" = "RUNNABLE" ]; then
        print_success "Instância está ativa"
        break
    fi
    echo "Status: $instance_status - Aguardando..."
    sleep 10
    wait_time=$((wait_time + 10))
done

# Step 5: Configure database user and password
print_step "Configurando usuário e senha"
gcloud sql users set-password postgres \
    --instance=$INSTANCE_NAME \
    --password=$DB_PASSWORD \
    --project=$PROJECT_ID

print_success "Senha do postgres configurada"

# Step 6: Create application database
print_step "Criando database da aplicação"
if gcloud sql databases describe $DB_NAME --instance=$INSTANCE_NAME --project=$PROJECT_ID &>/dev/null; then
    print_warning "Database $DB_NAME já existe"
else
    gcloud sql databases create $DB_NAME \
        --instance=$INSTANCE_NAME \
        --project=$PROJECT_ID
    print_success "Database $DB_NAME criado"
fi

# Step 7: Create application user
print_step "Criando usuário da aplicação"
if gcloud sql users describe $DB_USER --instance=$INSTANCE_NAME --project=$PROJECT_ID &>/dev/null; then
    print_warning "Usuário $DB_USER já existe"
else
    gcloud sql users create $DB_USER \
        --instance=$INSTANCE_NAME \
        --password=$DB_PASSWORD \
        --project=$PROJECT_ID
    print_success "Usuário $DB_USER criado"
fi

# Step 8: Get connection name
print_step "Obtendo informações de conexão"
CONNECTION_NAME=$(gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID --format="value(connectionName)")
INSTANCE_IP=$(gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID --format="value(ipAddresses[0].ipAddress)")

print_success "Connection name: $CONNECTION_NAME"
print_success "Instance IP: $INSTANCE_IP"

# Step 9: Create secrets
print_step "Configurando secrets no Secret Manager"

# Database password
if gcloud secrets describe db_password --project=$PROJECT_ID &>/dev/null; then
    print_warning "Secret db_password já existe"
    echo -n "$DB_PASSWORD" | gcloud secrets versions add db_password --data-file=- --project=$PROJECT_ID
else
    echo -n "$DB_PASSWORD" | gcloud secrets create db_password --data-file=- --project=$PROJECT_ID
fi

# Anthropic API Key (ask user)
read -s -p "Digite sua ANTHROPIC_API_KEY: " ANTHROPIC_KEY
echo ""

if [[ -z "$ANTHROPIC_KEY" ]]; then
    print_warning "ANTHROPIC_API_KEY não fornecida - você pode configurar depois"
else
    if gcloud secrets describe anthropic_key --project=$PROJECT_ID &>/dev/null; then
        print_warning "Secret anthropic_key já existe"
        echo -n "$ANTHROPIC_KEY" | gcloud secrets versions add anthropic_key --data-file=- --project=$PROJECT_ID
    else
        echo -n "$ANTHROPIC_KEY" | gcloud secrets create anthropic_key --data-file=- --project=$PROJECT_ID
    fi
    print_success "Secrets configurados"
fi

# Flask Secret Key
print_success "Configurando FLASK_SECRET_KEY"
FLASK_SECRET=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

if gcloud secrets describe flask_secret_key --project=$PROJECT_ID &>/dev/null; then
    print_warning "Secret flask_secret_key já existe"
    echo -n "$FLASK_SECRET" | gcloud secrets versions add flask_secret_key --data-file=- --project=$PROJECT_ID
else
    echo -n "$FLASK_SECRET" | gcloud secrets create flask_secret_key --data-file=- --project=$PROJECT_ID
fi
print_success "FLASK_SECRET_KEY configurada"

# Step 10: Apply PostgreSQL schema
print_step "Aplicando schema PostgreSQL"
echo "Executando schema via cloud_sql_proxy..."

# Download cloud_sql_proxy if needed
if [ ! -f "./cloud_sql_proxy" ]; then
    echo "Baixando cloud_sql_proxy..."
    curl -o cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64
    chmod +x cloud_sql_proxy
fi

# Start proxy in background
./cloud_sql_proxy -instances=$CONNECTION_NAME=tcp:5432 &
PROXY_PID=$!
sleep 5

# Apply schema using postgres superuser
if [ -f "migration/postgresql_schema.sql" ]; then
    PGPASSWORD=$DB_PASSWORD psql "host=127.0.0.1 port=5432 user=postgres dbname=$DB_NAME sslmode=disable" -f migration/postgresql_schema.sql
    print_success "Schema PostgreSQL aplicado"
else
    print_warning "Arquivo migration/postgresql_schema.sql não encontrado"
fi

# Kill proxy
kill $PROXY_PID 2>/dev/null || true

# Step 11: Grant permissions
print_step "Configurando permissões IAM"
SERVICE_ACCOUNT="$PROJECT_ID@appspot.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" &>/dev/null || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/cloudsql.client" &>/dev/null || true

print_success "Permissões configuradas"

# Step 12: Deploy to Cloud Run
print_step "Deploy para Cloud Run"
echo "Fazendo deploy da aplicação..."

gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --port 8080 \
    --timeout 900 \
    --set-env-vars="DB_TYPE=postgresql,DB_HOST=,DB_PORT=5432,DB_NAME=$DB_NAME,DB_USER=$DB_USER,DB_SOCKET_PATH=/cloudsql/$CONNECTION_NAME,FLASK_ENV=production" \
    --set-cloudsql-instances="$CONNECTION_NAME" \
    --set-secrets="DB_PASSWORD=db_password:latest,ANTHROPIC_API_KEY=anthropic_key:latest,FLASK_SECRET_KEY=flask_secret_key:latest" \
    --project=$PROJECT_ID

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --project=$PROJECT_ID --format 'value(status.url)')

print_success "Deploy concluído!"

# Final summary
echo ""
echo -e "${GREEN}==============================================="
echo "🎉 Setup Cloud SQL Concluído com Sucesso!"
echo "===============================================${NC}"
echo ""
echo "📊 Resumo da configuração:"
echo "   • Projeto: $PROJECT_ID"
echo "   • Instância Cloud SQL: $INSTANCE_NAME"
echo "   • Database: $DB_NAME"
echo "   • Usuário: $DB_USER"
echo "   • Connection: $CONNECTION_NAME"
echo "   • Service URL: $SERVICE_URL"
echo ""
echo "🔧 Próximos passos:"
echo "   1. Teste sua aplicação: curl $SERVICE_URL/api/stats"
echo "   2. Acesse via browser: $SERVICE_URL"
echo "   3. Monitore logs: gcloud logs tail --project=$PROJECT_ID"
echo ""
echo "💰 Custos estimados: ~$10-25/mês"
echo ""
echo -e "${BLUE}Configuração salva em: .env.production${NC}"

# Save configuration to file
cat > .env.production << EOF
# Configuração gerada automaticamente
DB_TYPE=postgresql
DB_HOST=$INSTANCE_IP
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_SOCKET_PATH=/cloudsql/$CONNECTION_NAME
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
CLOUD_SQL_CONNECTION_NAME=$CONNECTION_NAME
SERVICE_URL=$SERVICE_URL
EOF

print_success "Setup automatizado concluído!"