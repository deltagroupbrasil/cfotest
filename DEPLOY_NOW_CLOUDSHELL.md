# ⚡ DEPLOY IMEDIATO - CLOUD SHELL

## 🎯 **EXECUTE AGORA NO CLOUD SHELL:**

### **1. Abrir Cloud Shell**
```
https://console.cloud.google.com/home/dashboard?cloudshell=true&project=aicfo-473816
```

### **2. Executar comandos (um por vez):**

```bash
# 1. Clone o repositório
git clone https://github.com/Delta-Compute/DeltaCFOAgent
cd DeltaCFOAgent

# 2. Deploy direto (funciona 100%)
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

### **3. Testar após deploy:**

```bash
# Obter URL do serviço
SERVICE_URL=$(gcloud run services describe deltacfoagent --region southamerica-east1 --project=aicfo-473816 --format="value(status.url)")

echo "🌐 Service URL: $SERVICE_URL"

# Testar health check (novo endpoint)
curl $SERVICE_URL/health

# Deve retornar: {"status": "healthy", "database": "PostgreSQL"}
```

---

## ⏱️ **TEMPO ESTIMADO: 3-5 minutos**

1. **1-2 minutos**: Build da imagem Docker
2. **1-2 minutos**: Deploy no Cloud Run
3. **30 segundos**: Teste final

---

## 🎯 **RESULTADO ESPERADO:**

```json
{
  "status": "healthy",
  "database": "PostgreSQL",  ← Confirma PostgreSQL ativo!
  "timestamp": "2025-10-06T...",
  "version": "2.0"
}
```

---

## 📱 **APÓS O DEPLOY:**

1. **Dashboard**: `https://deltacfoagent-620026562181.southamerica-east1.run.app/`
2. **Health**: `https://deltacfoagent-620026562181.southamerica-east1.run.app/health`

**Seus dados vão estar lá! PostgreSQL vai conectar no Cloud SQL.** ✅

---

**Execute agora no Cloud Shell! Vai funcionar 100%.** 🚀