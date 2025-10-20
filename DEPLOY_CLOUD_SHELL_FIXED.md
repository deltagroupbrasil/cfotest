# ⚡ DEPLOY CLOUD SHELL - COMANDOS CORRIGIDOS

## 🎯 **Problema Identificado**
- ❌ `--dockerfile` não existe no gcloud run deploy
- ✅ **Soluções alternativas** disponíveis

---

## 🚀 **OPÇÃO 1: Build + Deploy (Mais Confiável)**

```bash
# 1. Clone o repositório
git clone https://github.com/Delta-Compute/DeltaCFOAgent
cd DeltaCFOAgent

# 2. Build com Cloud Build usando nosso cloudbuild.yaml
gcloud builds submit --config cloudbuild.yaml --project=aicfo-473816

# 3. Deploy já será feito automaticamente pelo cloudbuild.yaml!
```

---

## 🚀 **OPÇÃO 2: Build Manual + Deploy**

```bash
# 1. Clone
git clone https://github.com/Delta-Compute/DeltaCFOAgent
cd DeltaCFOAgent

# 2. Build da imagem manualmente
gcloud builds submit --tag gcr.io/aicfo-473816/deltacfoagent:latest --project=aicfo-473816

# 3. Deploy da imagem
gcloud run deploy deltacfoagent \
  --image gcr.io/aicfo-473816/deltacfoagent:latest \
  --platform managed \
  --region southamerica-east1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --port 8080 \
  --timeout 300 \
  --max-instances 100 \
  --set-env-vars="DB_TYPE=postgresql,DB_HOST=34.39.143.82,DB_PORT=5432,DB_NAME=delta_cfo,DB_USER=delta_user,DB_SOCKET_PATH=/cloudsql/aicfo-473816:southamerica-east1:delta-cfo-db,FLASK_ENV=production" \
  --set-cloudsql-instances="aicfo-473816:southamerica-east1:delta-cfo-db" \
  --set-secrets="DB_PASSWORD=db_password_sa:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest" \
  --project=aicfo-473816
```

---

## 🚀 **OPÇÃO 3: Deploy Direto com Source (Simples)**

```bash
# 1. Clone
git clone https://github.com/Delta-Compute/DeltaCFOAgent
cd DeltaCFOAgent

# 2. Renomear Dockerfile (para usar o correto)
cp Dockerfile.cloudsql Dockerfile

# 3. Deploy direto do source
gcloud run deploy deltacfoagent \
  --source . \
  --platform managed \
  --region southamerica-east1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --port 8080 \
  --timeout 300 \
  --max-instances 100 \
  --set-env-vars="DB_TYPE=postgresql,DB_HOST=34.39.143.82,DB_PORT=5432,DB_NAME=delta_cfo,DB_USER=delta_user,DB_SOCKET_PATH=/cloudsql/aicfo-473816:southamerica-east1:delta-cfo-db,FLASK_ENV=production" \
  --set-cloudsql-instances="aicfo-473816:southamerica-east1:delta-cfo-db" \
  --set-secrets="DB_PASSWORD=db_password_sa:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest" \
  --project=aicfo-473816
```

---

## 🎯 **RECOMENDAÇÃO**

**Use a OPÇÃO 1** - É a mais confiável porque:
- ✅ Usa o `cloudbuild.yaml` que já está configurado
- ✅ Build + Deploy automático
- ✅ Menos chance de erro

---

## 🧪 **TESTE APÓS DEPLOY**

```bash
# Obter URL do serviço
SERVICE_URL=$(gcloud run services describe deltacfoagent --region southamerica-east1 --project=aicfo-473816 --format="value(status.url)")

# Testar health check
curl $SERVICE_URL/health

# Deve retornar: {"status": "healthy", "database": "PostgreSQL"}
```

---

**Execute a OPÇÃO 1 no Cloud Shell. É a mais simples!** ⚡