# 📊 Delta CFO Analytics Service

Microserviço dedicado para análises avançadas e business intelligence do sistema Delta CFO Agent.

## 🎯 Funcionalidades

### 📈 Análises Disponíveis
- **Monthly Summary**: Resumo mensal de transações por entidade
- **Entity Breakdown**: Análise detalhada por entidade de negócio
- **Category Analysis**: Análise de gastos por categoria
- **Dashboard Data**: Dados consolidados para dashboards

### 🔗 API Endpoints

#### Base URL
```
https://delta-analytics-service-xxxx-uc.a.run.app
```

#### Endpoints Disponíveis

1. **Health Check**
   ```
   GET /
   ```
   - Status do serviço

2. **Monthly Summary**
   ```
   GET /api/analytics/monthly-summary?months=12
   ```
   - Parâmetros: `months` (1-24, default: 12)
   - Resumo mensal de transações

3. **Entity Breakdown**
   ```
   GET /api/analytics/entities
   ```
   - Análise por entidade de negócio

4. **Category Analysis**
   ```
   GET /api/analytics/categories
   ```
   - Top 50 categorias por volume

5. **Dashboard Data**
   ```
   GET /api/analytics/dashboard
   ```
   - Dados consolidados para dashboard

6. **Service Status**
   ```
   GET /api/analytics/status
   ```
   - Status do serviço e conectividade

## 🚀 Deploy Local

### Pré-requisitos
- Python 3.11+
- Database SQLite do sistema principal

### Instalação
```bash
cd services/analytics_service
pip install -r requirements.txt
python app.py
```

### Teste Local
```bash
curl http://localhost:8080/api/analytics/status
```

## ☁️ Deploy Google Cloud Run

### Deploy Automático via GitHub
1. Faça commit das alterações no branch `main`
2. GitHub Actions deployta automaticamente
3. Acesse o serviço na URL fornecida

### Deploy Manual
```bash
gcloud run deploy delta-analytics-service \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

## 📊 Exemplos de Uso

### 1. Obter Resumo Mensal
```bash
curl "https://your-service-url/api/analytics/monthly-summary?months=6"
```

### 2. Análise por Entidades
```bash
curl "https://your-service-url/api/analytics/entities"
```

### 3. Dashboard Completo
```bash
curl "https://your-service-url/api/analytics/dashboard"
```

## 🔧 Configuração

### Variáveis de Ambiente
- `PORT`: Porta do serviço (default: 8080)
- `DATABASE_PATH`: Caminho para o database SQLite
- `DEBUG`: Modo debug (true/false)

### Database
O serviço utiliza o mesmo database SQLite do sistema principal:
- Tabela: `transactions`
- Colunas: `date`, `description`, `amount`, `entity`, `category`

## 🏗️ Arquitetura

```
Analytics Service
├── app.py              # Flask application
├── Dockerfile          # Container configuration
├── requirements.txt    # Python dependencies
├── cloudbuild.yaml    # GCP build configuration
└── README.md          # This file
```

### Classes Principais

#### `AnalyticsEngine`
- `get_monthly_summary()`: Análise mensal
- `get_entity_breakdown()`: Breakdown por entidade
- `get_category_analysis()`: Análise de categorias
- `get_db_connection()`: Conexão com database

## 📈 Performance

### Benchmarks
- **Response Time**: < 500ms para queries típicas
- **Memory Usage**: ~200MB base, peak ~500MB
- **Database**: Otimizado para reads com índices
- **Concurrency**: Suporte a múltiplas requisições

### Limits
- **Memory**: 1Gi (configurável)
- **CPU**: 1 vCPU (configurável)
- **Timeout**: 300s
- **Max Instances**: 5 (auto-scaling)

## 🔍 Monitoring

### Health Checks
```bash
# Service health
curl https://your-url/

# Database connectivity
curl https://your-url/api/analytics/status
```

### Logs
```bash
# View logs
gcloud run services logs tail delta-analytics-service --region us-central1
```

### Métricas no Cloud Console
- Request count
- Response latency
- Error rate
- Memory/CPU usage

## 🛠️ Desenvolvimento

### Estrutura do Código
```python
# Flask app with analytics endpoints
app = Flask(__name__)

# Analytics engine class
class AnalyticsEngine:
    def get_monthly_summary(self, months=12):
        # SQL query for monthly data

    def get_entity_breakdown(self):
        # Analysis by business entity
```

### Adicionando Novos Endpoints
1. Criar método na `AnalyticsEngine`
2. Adicionar route no Flask app
3. Atualizar documentação
4. Testar localmente
5. Deploy via GitHub Actions

## 🔒 Segurança

### Considerações
- ✅ HTTPS automático (Cloud Run)
- ✅ Container isolado
- ✅ Read-only database access
- ⚠️ No authentication (público)
- ⚠️ Rate limiting não implementado

### Próximos Passos de Segurança
1. Implementar autenticação JWT
2. Rate limiting por IP
3. Validação de inputs
4. CORS configuration

## 🚨 Troubleshooting

### Problemas Comuns

1. **Database não encontrado**
   ```
   Error: Database connection failed
   ```
   - Verificar `DATABASE_PATH`
   - Confirmar se database existe no container

2. **Memory limit exceeded**
   ```
   Error: Container killed (OOM)
   ```
   - Aumentar memory limit no Cloud Run

3. **Query timeout**
   ```
   Error: Query execution timeout
   ```
   - Otimizar queries SQL
   - Adicionar índices no database

4. **Cold start lento**
   - Configurar min-instances > 0
   - Otimizar imports Python

### Debug Local
```bash
# Enable debug mode
export DEBUG=true
python app.py

# Check database
sqlite3 path/to/database.db ".tables"
```

## 📚 Documentação Relacionada

- [Delta CFO Agent - Main Project](../../README.md)
- [Deployment Guide](../../DEPLOYMENT_GUIDE.md)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 🤝 Contribuição

1. Fork o repositório
2. Crie feature branch
3. Teste localmente
4. Submeta Pull Request
5. Aguarde review e deploy automático

---

**Criado em**: 2024-10-02
**Versão**: 1.0.0
**Autor**: Delta CFO Team