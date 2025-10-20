@echo off
setlocal enabledelayedexpansion
echo ===============================================
echo   🚀 SETUP COMPLETO - CLOUD SQL + CLOUD RUN
echo ===============================================
echo.
echo Este script vai:
echo   1. ✅ Configurar secrets no Secret Manager
echo   2. ✅ Fazer deploy para Cloud Run com PostgreSQL
echo   3. ✅ Testar conectividade end-to-end
echo.

REM Configurações
set PROJECT_ID=aicfo-473816
set REGION=southamerica-east1
set SERVICE_NAME=deltacfoagent
set SQL_INSTANCE=delta-cfo-db

echo ===============================================
echo   📋 PASSO 1: CONFIGURAR SECRETS
echo ===============================================

echo Criando secrets no Secret Manager...

REM Criar secret para senha do banco de dados
echo Configurando DB_PASSWORD...
echo x2mNABXYS3ArMOteGSLbRQD5d | gcloud secrets create db_password_sa --data-file=- --project=%PROJECT_ID% || echo "Secret db_password_sa já existe"

REM Criar secret para ANTHROPIC_API_KEY (usar variável de ambiente ou prompt)
echo Configurando ANTHROPIC_API_KEY...
if defined ANTHROPIC_API_KEY (
    echo Usando ANTHROPIC_API_KEY da variável de ambiente...
    echo %ANTHROPIC_API_KEY% | gcloud secrets create ANTHROPIC_API_KEY --data-file=- --project=%PROJECT_ID% || echo "Secret ANTHROPIC_API_KEY já existe"
) else (
    echo ⚠️  IMPORTANTE: Configurando ANTHROPIC_API_KEY...
    set /p USER_API_KEY="Digite sua ANTHROPIC_API_KEY: "
    echo !USER_API_KEY! | gcloud secrets create ANTHROPIC_API_KEY --data-file=- --project=%PROJECT_ID% || echo "Secret ANTHROPIC_API_KEY já existe"
)

echo ✅ Secrets configurados!

echo ===============================================
echo   🚀 PASSO 2: DEPLOY PARA CLOUD RUN
echo ===============================================

echo Fazendo deploy para Cloud Run...
gcloud run deploy %SERVICE_NAME% ^
  --source . ^
  --dockerfile Dockerfile.cloudsql ^
  --platform managed ^
  --region %REGION% ^
  --allow-unauthenticated ^
  --memory 2Gi ^
  --cpu 2 ^
  --port 8080 ^
  --timeout 300 ^
  --max-instances 100 ^
  --set-env-vars="DB_TYPE=postgresql,DB_HOST=34.39.143.82,DB_PORT=5432,DB_NAME=delta_cfo,DB_USER=delta_user,DB_SOCKET_PATH=/cloudsql/%PROJECT_ID%:%REGION%:%SQL_INSTANCE%,FLASK_ENV=production" ^
  --set-cloudsql-instances="%PROJECT_ID%:%REGION%:%SQL_INSTANCE%" ^
  --set-secrets="DB_PASSWORD=db_password_sa:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest" ^
  --project=%PROJECT_ID%

if errorlevel 1 (
    echo ❌ Deploy falhou!
    pause
    exit /b 1
)

echo ✅ Deploy concluído!

echo ===============================================
echo   🔍 PASSO 3: TESTAR CONECTIVIDADE
echo ===============================================

echo Obtendo URL do serviço...
for /f %%i in ('gcloud run services describe %SERVICE_NAME% --platform managed --region %REGION% --project=%PROJECT_ID% --format="value(status.url)"') do set SERVICE_URL=%%i

echo.
echo 🌐 URL do seu aplicativo: %SERVICE_URL%
echo.

echo Testando health check...
curl -s %SERVICE_URL%/health

echo.
echo Testando dashboard...
curl -s -I %SERVICE_URL%/ | findstr "HTTP"

echo.
echo ===============================================
echo   ✅ SETUP COMPLETO!
echo ===============================================
echo.
echo 🌐 Aplicativo: %SERVICE_URL%
echo 🏥 Health Check: %SERVICE_URL%/health
echo 📊 Dashboard: %SERVICE_URL%/
echo.
echo 📋 Para atualizar sua ANTHROPIC_API_KEY:
echo echo "SUA_NOVA_CHAVE" ^| gcloud secrets versions add ANTHROPIC_API_KEY --data-file=- --project=%PROJECT_ID%
echo.
echo 🗄️  Para conectar ao Cloud SQL diretamente:
echo gcloud sql connect %SQL_INSTANCE% --user=delta_user --project=%PROJECT_ID%
echo.
pause