# 🚀 ATUALIZAR CLOUD RUN MANUALMENTE - Via Console Web

## 🎯 **Situação Atual**
- ✅ **Serviço funcionando**: `https://deltacfoagent-620026562181.southamerica-east1.run.app/`
- ✅ **Secrets configurados**: `db_password_sa` + `ANTHROPIC_API_KEY`
- ✅ **Código atualizado**: PostgreSQL support implementado
- ❌ **Problema**: gcloud CLI corrompido, precisa atualização manual

---

## 📋 **PASSO A PASSO - Console Web**

### **1. Acesse o Cloud Run Console**
```
https://console.cloud.google.com/run/detail/southamerica-east1/deltacfoagent/edit?project=aicfo-473816
```

### **2. Clique em "EDIT & DEPLOY NEW REVISION"**

### **3. Na aba "CONTAINER" - Configure:**

#### **Container Image URL:**
```
gcr.io/aicfo-473816/deltacfoagent:latest
```

#### **Environment Variables:**
```
DB_TYPE = postgresql
DB_HOST = 34.39.143.82
DB_PORT = 5432
DB_NAME = delta_cfo
DB_USER = delta_user
DB_SOCKET_PATH = /cloudsql/aicfo-473816:southamerica-east1:delta-cfo-db
FLASK_ENV = production
```

#### **Secrets as Environment Variables:**
```
DB_PASSWORD = db_password_sa:latest
ANTHROPIC_API_KEY = ANTHROPIC_API_KEY:latest
```

### **4. Na aba "CONNECTIONS"**
#### **Cloud SQL Connections:**
```
aicfo-473816:southamerica-east1:delta-cfo-db
```

### **5. Na aba "SECURITY"**
#### **Service Account:**
```
Compute Engine default service account
```

### **6. DEPLOY**
- Clique em "DEPLOY"
- Aguarde 5-10 minutos

---

## 🔧 **ALTERNATIVA: Via Cloud Build (Mais Fácil)**

### **1. Acesse Cloud Build Console**
```
https://console.cloud.google.com/cloud-build/builds?project=aicfo-473816
```

### **2. Clique "RUN TRIGGER" ou "SUBMIT BUILD"**

### **3. Use o repositório:**
```
Source: Delta-Compute/DeltaCFOAgent
Branch: main
Dockerfile: Dockerfile.cloudsql
```

### **4. Build Configuration:**
```yaml
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-f', 'Dockerfile.cloudsql', '-t', 'gcr.io/$PROJECT_ID/deltacfoagent:$BUILD_ID', '.']
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', 'gcr.io/$PROJECT_ID/deltacfoagent:$BUILD_ID']
- name: 'gcr.io/cloud-builders/gcloud'
  args:
  - 'run'
  - 'deploy'
  - 'deltacfoagent'
  - '--image'
  - 'gcr.io/$PROJECT_ID/deltacfoagent:$BUILD_ID'
  - '--region'
  - 'southamerica-east1'
  - '--platform'
  - 'managed'
```

---

## 🎯 **RESULTADO ESPERADO**

Após o deploy, teste:

### **1. Health Check (novo endpoint):**
```bash
curl https://deltacfoagent-620026562181.southamerica-east1.run.app/health
```

**Deve retornar:**
```json
{
  "status": "healthy",
  "database": "PostgreSQL",
  "timestamp": "2024-XX-XX...",
  "version": "2.0"
}
```

### **2. Dashboard:**
```
https://deltacfoagent-620026562181.southamerica-east1.run.app/
```

**Deve carregar normalmente com PostgreSQL funcionando!**

---

## ⚡ **QUAL MÉTODO PREFERE?**

1. **Manual via Console** - Mais controle
2. **Cloud Build** - Mais automático

**Ambos vão funcionar!** 🚀