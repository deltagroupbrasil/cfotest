# 🚀 Scripts Automatizados - Delta CFO Agent

Scripts para setup automatizado do **Cloud SQL (PostgreSQL)** no Google Cloud Platform.

## 📋 Scripts Disponíveis

| Script | Descrição | Plataforma |
|--------|-----------|------------|
| `setup_cloud_sql.sh` | Setup completo automatizado | Linux/Mac/WSL |
| `setup_cloud_sql.bat` | Wrapper para Windows | Windows |
| `validate_setup.sh` | Validação do setup | Linux/Mac/WSL |
| `cleanup.sh` | Limpeza de recursos | Linux/Mac/WSL |

## 🚀 Execução Rápida

### Windows:
```cmd
# Execute como administrador
scripts\setup_cloud_sql.bat
```

### Linux/Mac/WSL:
```bash
# Dar permissão de execução
chmod +x scripts/*.sh

# Executar setup
./scripts/setup_cloud_sql.sh
```

### Google Cloud Shell (Recomendado):
```bash
# No Cloud Shell (já tem tudo configurado)
./scripts/setup_cloud_sql.sh
```

## 📋 Pré-requisitos

✅ **Obrigatório:**
- Google Cloud CLI instalado e autenticado
- Projeto GCP criado
- Billing habilitado no projeto
- ANTHROPIC_API_KEY válida

✅ **Para Windows:**
- Git Bash OU WSL instalado
- PowerShell como administrador

## 🔧 O que o script faz automaticamente:

1. ✅ **Configuração inicial** - Detecta projeto atual ou solicita configuração
2. ✅ **Habilita APIs** - Cloud SQL, Cloud Run, Secret Manager, Cloud Build
3. ✅ **Cria instância Cloud SQL** - PostgreSQL 15, tier f1-micro
4. ✅ **Configura database** - Cria database e usuário da aplicação
5. ✅ **Gera senha segura** - 25 caracteres aleatórios
6. ✅ **Configura secrets** - Armazena credenciais no Secret Manager
7. ✅ **Aplica schema** - Cria tabelas PostgreSQL otimizadas
8. ✅ **Configura permissões** - IAM roles para Cloud Run
9. ✅ **Deploy automático** - Build e deploy no Cloud Run
10. ✅ **Validação** - Testa todos os endpoints

## 🎯 Configuração Padrão

```bash
REGION="us-central1"
INSTANCE_NAME="delta-cfo-db"
DB_NAME="delta_cfo"
DB_USER="delta_user"
SERVICE_NAME="delta-cfo-agent"
TIER="db-f1-micro"  # ~$7/mês
STORAGE="10GB SSD"   # ~$1.70/mês
```

## 📊 Após o Setup

### Testar aplicação:
```bash
# Validar setup completo
./scripts/validate_setup.sh

# Teste manual
curl https://YOUR_SERVICE_URL/api/stats
```

### URLs importantes:
- **Aplicação**: `https://SERVICE_NAME-HASH-REGION-run.app`
- **Console Cloud SQL**: `https://console.cloud.google.com/sql/instances`
- **Cloud Run**: `https://console.cloud.google.com/run`

### Monitoramento:
```bash
# Logs em tempo real
gcloud logs tail --project=YOUR_PROJECT_ID

# Status da instância
gcloud sql instances describe delta-cfo-db

# Métricas de custo
gcloud billing budgets list
```

## 🆘 Troubleshooting

### Erro de autenticação:
```bash
gcloud auth login
gcloud auth list
gcloud config set project YOUR_PROJECT_ID
```

### Erro de permissões:
```bash
# Verificar roles
gcloud projects get-iam-policy YOUR_PROJECT_ID

# Adicionar permissão de admin (se necessário)
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="user:your-email@domain.com" \
    --role="roles/owner"
```

### Instância não responde:
```bash
# Verificar status
gcloud sql instances describe delta-cfo-db

# Reiniciar se necessário
gcloud sql instances restart delta-cfo-db
```

### Deploy falhou:
```bash
# Verificar logs do Cloud Build
gcloud builds list --limit=5

# Fazer deploy manual
gcloud run deploy delta-cfo-agent --source .
```

### Limpar recursos (se necessário):
```bash
./scripts/cleanup.sh
```

## 💰 Custos Estimados

| Recurso | Configuração | Custo/mês |
|---------|--------------|-----------|
| Cloud SQL | db-f1-micro | $7-15 |
| Storage | 10GB SSD | $1.70 |
| Cloud Run | Pay-per-use | $0-5 |
| **Total** | | **$10-25** |

## 🔒 Segurança

✅ **Implementado:**
- Passwords geradas automaticamente (25 chars)
- Secrets no Secret Manager
- Conexões SSL/TLS
- IAM roles mínimos
- Non-root containers

## 📞 Suporte

**Problemas comuns:**
- Verificar se billing está ativo
- Confirmar que APIs estão habilitadas
- Verificar quotas do projeto
- Testar conectividade de rede

**Logs úteis:**
```bash
# Erro durante setup
gcloud builds log --project=YOUR_PROJECT_ID

# Erro em runtime
gcloud logs read --project=YOUR_PROJECT_ID --limit=50
```