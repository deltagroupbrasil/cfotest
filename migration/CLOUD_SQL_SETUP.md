# 🚀 Cloud SQL Setup Guide - Delta CFO Agent

Guia completo para migrar o Delta CFO Agent do SQLite para **Cloud SQL (PostgreSQL)** no Google Cloud Platform.

## 📋 Pré-requisitos

- Google Cloud CLI instalado
- Projeto no GCP configurado
- Cloud Build e Cloud Run habilitados
- Permissões de administrador no projeto

## 🎯 Parte 1: Criar Instância Cloud SQL

### 1.1 Configurar variáveis do projeto
```bash
# Substitua pelos seus valores
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export INSTANCE_NAME="delta-cfo-db"
export DB_NAME="delta_cfo"
export DB_USER="delta_user"
export DB_PASSWORD="your-secure-password"

gcloud config set project $PROJECT_ID
```

### 1.2 Criar instância PostgreSQL
```bash
# Criar instância Cloud SQL PostgreSQL (tier básico)
gcloud sql instances create $INSTANCE_NAME \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --storage-type=SSD \
    --storage-size=10GB \
    --storage-auto-increase \
    --backup-start-time=03:00 \
    --enable-bin-log \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04 \
    --availability-type=zonal

# Aguarde a criação completar (pode levar alguns minutos)
gcloud sql operations list --instance=$INSTANCE_NAME
```

### 1.3 Configurar usuário e database
```bash
# Definir senha do usuário postgres
gcloud sql users set-password postgres \
    --instance=$INSTANCE_NAME \
    --password=$DB_PASSWORD

# Criar database específico
gcloud sql databases create $DB_NAME \
    --instance=$INSTANCE_NAME

# Criar usuário da aplicação
gcloud sql users create $DB_USER \
    --instance=$INSTANCE_NAME \
    --password=$DB_PASSWORD
```

### 1.4 Configurar rede e segurança
```bash
# Autorizar acesso do Cloud Run (não precisa de IP específico)
gcloud sql instances patch $INSTANCE_NAME \
    --assign-ip \
    --authorized-networks=0.0.0.0/0

# Obter connection name para uso no Cloud Run
gcloud sql instances describe $INSTANCE_NAME \
    --format="value(connectionName)"
```

## 🔧 Parte 2: Configurar Schema PostgreSQL

### 2.1 Conectar à instância para teste local (opcional)
```bash
# Instalar cloud_sql_proxy (se não tiver)
curl -o cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64
chmod +x cloud_sql_proxy

# Conectar via proxy local
./cloud_sql_proxy -instances=$PROJECT_ID:$REGION:$INSTANCE_NAME=tcp:5432 &

# Testar conexão
psql "host=127.0.0.1 port=5432 sslmode=disable user=$DB_USER dbname=$DB_NAME"
```

### 2.2 Aplicar schema PostgreSQL
```bash
# Executar schema via gcloud (método recomendado)
gcloud sql connect $INSTANCE_NAME --user=$DB_USER --database=$DB_NAME

# No prompt do PostgreSQL, executar:
\i /path/to/migration/postgresql_schema.sql
\q
```

## 🐳 Parte 3: Atualizar Código e Deploy

### 3.1 Configurar variáveis de ambiente no Cloud Run
```bash
# Deploy com variáveis de ambiente
gcloud run deploy delta-cfo-agent \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --port 8080 \
    --set-env-vars="DB_TYPE=postgresql" \
    --set-env-vars="DB_HOST=" \
    --set-env-vars="DB_PORT=5432" \
    --set-env-vars="DB_NAME=$DB_NAME" \
    --set-env-vars="DB_USER=$DB_USER" \
    --set-env-vars="DB_SOCKET_PATH=/cloudsql/$PROJECT_ID:$REGION:$INSTANCE_NAME" \
    --set-cloudsql-instances="$PROJECT_ID:$REGION:$INSTANCE_NAME" \
    --set-secrets="DB_PASSWORD=db_password:latest,ANTHROPIC_API_KEY=anthropic_key:latest"
```

### 3.2 Configurar secrets no Secret Manager
```bash
# Armazenar senha do banco
echo -n "$DB_PASSWORD" | gcloud secrets create db_password --data-file=-

# Armazenar API key do Claude (substitua pelo valor real)
echo -n "your-anthropic-api-key" | gcloud secrets create anthropic_key --data-file=-

# Dar permissões ao Cloud Run para acessar secrets
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_ID@appspot.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## 📊 Parte 4: Migração de Dados (Se necessário)

### 4.1 Exportar dados SQLite existentes
```python
# Script para exportar dados (se houver banco SQLite existente)
import sqlite3
import pandas as pd
import psycopg2

# Conectar ao SQLite
sqlite_conn = sqlite3.connect('web_ui/delta_transactions.db')

# Exportar tabelas para CSV
tables = ['transactions', 'invoices', 'invoice_email_log']
for table in tables:
    df = pd.read_sql_query(f"SELECT * FROM {table}", sqlite_conn)
    df.to_csv(f'{table}_export.csv', index=False)

sqlite_conn.close()
```

### 4.2 Importar dados no PostgreSQL
```sql
-- No PostgreSQL, importar via COPY
\copy transactions FROM 'transactions_export.csv' WITH CSV HEADER;
\copy invoices FROM 'invoices_export.csv' WITH CSV HEADER;
\copy invoice_email_log FROM 'invoice_email_log_export.csv' WITH CSV HEADER;
```

## 🔍 Parte 5: Teste e Monitoramento

### 5.1 Testar aplicação
```bash
# Obter URL do Cloud Run
SERVICE_URL=$(gcloud run services describe delta-cfo-agent --platform managed --region $REGION --format 'value(status.url)')

# Testar endpoint de saúde
curl $SERVICE_URL/health

# Testar endpoint de transações
curl $SERVICE_URL/api/stats
```

### 5.2 Monitoramento
```bash
# Ver logs do Cloud Run
gcloud logs tail --source-type=gce_instance

# Ver métricas Cloud SQL
gcloud sql operations list --instance=$INSTANCE_NAME

# Monitorar performance
gcloud sql instances describe $INSTANCE_NAME
```

## 💰 Parte 6: Otimização de Custos

### 6.1 Configurações de economia
```bash
# Configurar auto-sleep (parar instância quando não usar)
gcloud sql instances patch $INSTANCE_NAME \
    --deletion-protection

# Monitorar custos
gcloud billing budgets list
```

### 6.2 Custos esperados
- **Cloud SQL (db-f1-micro)**: ~$7-15/mês
- **Storage (10GB SSD)**: ~$1.70/mês
- **Cloud Run**: Baseado no uso (geralmente $0-5/mês)
- **Total estimado**: $10-25/mês

## 🚨 Troubleshooting

### Problemas comuns:

**Erro de conexão**:
```bash
# Verificar firewall
gcloud compute firewall-rules list

# Testar conectividade
gcloud sql connect $INSTANCE_NAME --user=$DB_USER
```

**Erro de permissão**:
```bash
# Verificar IAM roles
gcloud projects get-iam-policy $PROJECT_ID

# Adicionar permissão se necessário
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:your-email@domain.com" \
    --role="roles/cloudsql.admin"
```

**Performance lenta**:
```sql
-- Verificar queries lentas no PostgreSQL
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

## 📝 Checklist Final

- [ ] Instância Cloud SQL criada
- [ ] Schema PostgreSQL aplicado
- [ ] Secrets configurados
- [ ] Variáveis de ambiente definidas
- [ ] Deploy no Cloud Run concluído
- [ ] Testes de conectividade passando
- [ ] Monitoramento configurado
- [ ] Backup automático ativo

---

**🎉 Parabéns!** Seu Delta CFO Agent agora está rodando com Cloud SQL PostgreSQL em produção!