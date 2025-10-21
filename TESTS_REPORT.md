# Relatório de Testes – DeltaCFOAgent

Este documento consolida todos os testes criados, como executá‑los, resultados atuais, soluções para problemas comuns e próximos passos sugeridos.

## Visão Geral
- Back‑end: testes unitários e de integração com `pytest` (SQLite como DB de integração quando aplicável).
- Front‑end: testes unitários de JS com Jest + jsdom para `web_ui/static/script.js`.
- E2E: testes com Playwright (navegador real) cobrindo fluxo do usuário na UI até API e (quando aplicável) DB.
- CI: GitHub Actions executa `pytest` + cobertura, Jest + cobertura e Playwright E2E.

## Testes Criados

### Back‑end (Python)
- `tests/test_database_utils.py`: conexões SQLite, CRUD, transações em lote, integrity check, vacuum, remoção de lockfiles, singleton.
- `tests/test_web_ui_database_sqlite.py`: `execute_query/many`, transação commit/rollback, batch, retry com erro transitório, `health_check`.
- `tests/test_web_ui_database_health.py`: caminho saudável vs. inesperado (status `unhealthy` com mensagem de erro); imports externos stubados.
- `tests/test_smart_matching_criteria.py`: pontuações de valor/data/vendor/entity/pattern; limites (2/5/10/15%); sanity e confiança; avaliação completa.
- `tests/test_robust_revenue_matcher_helpers.py`: chunking, dicionários de resultado (sucesso/erro), explicações, enrich com DB stubado.
- `tests/test_crypto_pricing_sqlite.py`: inserção de preços estáveis e fallback de 7 dias (SQLite).
- `tests/test_crypto_pricing_contract.py`: contrato para Binance (stub em `requests.get` → URL/params + inserts em lote) e USDC fixo.
- `tests/test_reporting_api.py`: endpoints de DRE (inclui validações de datas inválidas e payload); shape da resposta.
- `tests/test_reporting_api_branches.py`: cobertura de ramos (datas MM/DD/YYYY, `include_details=True`, erro do DB → 500, DB vazio → totais zero).
- `tests/test_reporting_income_statement_integration.py`: integração SQLite – semente de `transactions`, chamada de `/api/reports/income-statement/simple`, valida totais e chaves.
- `tests/test_web_ui_app_stats.py`: `/api/stats` (monkeypatch dos cálculos para shape determinístico).
- `tests/test_web_ui_app_transactions.py`: filtros (entidade, tipo, needs_review, min/max, keyword, source) com fixture `pandas`.

### HTML (renderização via Flask)
- `tests/test_web_ui_app_templates.py`: renderização de `/`, `/dashboard`, `/revenue`; verifica elementos básicos (nav/header/botões/form/filters), `cache_buster` e assets estáticos (200).

### Front‑end (Jest + jsdom)
- `web_ui/__tests__/script.test.js`: 
  - `buildFilterQuery`, `clearFilters`, `renderTransactionTable` (estado vazio e linhas, classes positivo/negativo), `updateTableInfo` (contagens), `formatCurrency/formatDate`, `loadTransactions` (stub de `fetch`).

### E2E (Playwright – navegador real)
- `tests-e2e/dashboard.e2e.spec.ts`: fluxo CSV (app simples) – aplica/limpa filtros, `needsReview`, valida linhas.
- `tests-e2e/dashboard_filters_advanced.e2e.spec.ts`: filtros de data, `keyword`, combinações e estado vazio.
- `tests-e2e/appdb_integration.e2e.spec.ts`: integração com DB (app_db) – semente SQLite, start do `web_ui.app_db` (5002), tabela exibe linha “E2E Seed Row” e filtro por entidade mantém linha.

## Como Executar

### Python (unit/integration)
```
cd DeltaCFOAgent
python -m pytest -q
# Verboso
python -m pytest -ra -vv
```

### Cobertura (alvos principais)
```
python -m pytest -q \
  --cov=web_ui/app.py \
  --cov=web_ui/database.py \
  --cov=web_ui/smart_matching_criteria.py \
  --cov=web_ui/robust_revenue_matcher.py \
  --cov=database_utils.py \
  --cov=crypto_pricing.py \
  --cov-report=term-missing --cov-report=html:htmlcov \
  -k "not app_transactions"
# Abra: DeltaCFOAgent/htmlcov/index.html
```

### Front‑end (Jest)
```
cd DeltaCFOAgent
npm install
npm run test
```

### E2E (Playwright)
```
cd DeltaCFOAgent
npm install
npx playwright install
# App simples (CSV)
# Windows PS:
$env:FLASK_APP='web_ui.app'; python -m flask run --port 5001 --no-reload
# Outro terminal:
npm run test:e2e
```
Para testar `app_db` localmente, inicie `web_ui.app_db` em outra porta (ex.: 5002) e semeie o SQLite conforme exemplo no CI.

## CI (GitHub Actions)
- Execução em `main` (push/PR):
  - Python: `pytest` + cobertura (limiar `--cov-fail-under=80` nos módulos alvo).
  - HTML: BeautifulSoup instalado (testes de template ativos).
  - Front‑end: Jest + jsdom com limiares (branches ≥70%, lines/functions ≥80%).
  - E2E: Playwright – sobe `web_ui.app` (5001) com CSV e `web_ui.app_db` (5002) com SQLite semeado; executa specs E2E.

## Resultados Atuais
- Local (Python): todos os testes passam; alguns HTML podem ser `skipped` sem `bs4` local (no CI roda com bs4).
- CI: executa toda a suíte (Python + Jest + E2E) e publica artefatos de cobertura. Limiar de backend está em 80% (meta: 85%).

## Problemas Comuns e Soluções
- bs4 ausente localmente → instale `beautifulsoup4` ou rode apenas no CI.
- Dependências externas (psycopg2, dotenv, reportlab etc.) → testes usam *stubs* locais para manter isolamento e evitar rede.
- Playwright local → `npx playwright install` (primeira vez) e garantir que o Flask está rodando na porta correta.
- CSV faltando para `web_ui.app` → criar `MASTER_TRANSACTIONS.csv` com cabeçalho e linhas (vide CI).
- Permissões de script no Windows (PowerShell) → executar com `-ExecutionPolicy Bypass` se necessário.

## Próximos Passos Sugeridos
- Cobertura Back‑end → 85%:
  - Ampliar testes de ramos em `web_ui/reporting_api.py` (agregações por categoria/entidade, junção com invoices, caminhos de erro adicionais) e do `robust_revenue_matcher` (batches, retries, persistência).
  - Elevar `--cov-fail-under` no CI para 85% após próxima rodada.
- E2E CRUD (app_db):
  - Adicionar fluxo de criação/edição de transação via UI e validar persistência (UI → API → DB → UI).
- Testes de performance (rápidos; <2s por teste quando possível) e *markers* para cenários mais lentos.
- Documentar *fixtures* e dados de exemplo em `tests/fixtures/` (se necessário) para facilitar manutenção.

---
Última atualização: <!-- UPDATED_BY_CI_OR_DEV -->
