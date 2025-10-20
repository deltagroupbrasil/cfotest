@echo off
echo ===============================================
echo    🚀 MIGRAÇÃO CLOUD SQL - DELTA CFO AGENT
echo ===============================================
echo.

REM Reautenticar Google Cloud
echo 1. Reautenticando Google Cloud...
gcloud auth login

REM Definir projeto
echo 2. Configurando projeto...
gcloud config set project aicfo-473816

REM Executar migração automatizada
echo 3. Iniciando migração (responda as perguntas)...
echo.
echo Sugerido:
echo   - Região: us-central1 (enter para padrão)
echo   - Instância: delta-cfo-db (enter para padrão)
echo   - Database: delta_cfo (enter para padrão)
echo   - Usuário: delta_user (enter para padrão)
echo   - Serviço: delta-cfo-agent (enter para padrão)
echo.
bash scripts/setup_cloud_sql.sh

echo.
echo ===============================================
echo ✅ MIGRAÇÃO CONCLUÍDA!
echo ===============================================
pause