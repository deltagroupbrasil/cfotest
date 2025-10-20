# ⚡ DEPLOY VIA CLOUD SHELL - Mais Fácil!

## 🎯 **Por que Cloud Shell?**
- ✅ **Não depende** do gcloud CLI local (que está corrompido)
- ✅ **Já autenticado** automaticamente
- ✅ **Todas as ferramentas** disponíveis
- ✅ **Acesso direto** ao projeto

---

## 🚀 **PASSO A PASSO SIMPLES**

### **1. Abrir Cloud Shell**
```
https://console.cloud.google.com/home/dashboard?cloudshell=true&project=aicfo-473816
```

### **2. Executar estes comandos:**

```bash
# 1. Clone o repositório
git clone https://github.com/Delta-Compute/DeltaCFOAgent
cd DeltaCFOAgent

# 2. Verificar se secrets existem
gcloud secrets list --project=aicfo-473816

# 3. Fazer deploy direto
gcloud run deploy deltacfoagent \
  --source . \
  --dockerfile Dockerfile.cloudsql \
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

# 4. Testar após deploy
curl $(gcloud run services describe deltacfoagent --region southamerica-east1 --project=aicfo-473816 --format="value(status.url)")/health
```

---

## 🎯 **RESULTADO ESPERADO**

```json
{
  "status": "healthy",
  "database": "PostgreSQL",
  "timestamp": "...",
  "version": "2.0"
}
```

**Isso significa que PostgreSQL está funcionando!** 🎉

---

## 📋 **INSTRUÇÕES ALTERNATIVAS**

Se preferir interface gráfica, use:
1. **Cloud Console** → `UPDATE_CLOUD_RUN_MANUAL.md`
2. **Cloud Build** → Trigger automático do GitHub

**Qual prefere? Cloud Shell é o mais rápido!** ⚡