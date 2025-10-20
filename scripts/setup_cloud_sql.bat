@echo off
REM ===============================================
REM Delta CFO Agent - Cloud SQL Setup for Windows
REM ===============================================

echo.
echo ===============================================
echo 🚀 Delta CFO Agent - Cloud SQL Setup
echo ===============================================
echo.

REM Check if running in Git Bash or WSL
where bash >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Bash nao encontrado!
    echo.
    echo Opcoes para executar o setup:
    echo   1. Instale Git Bash: https://git-scm.com/download/win
    echo   2. Use WSL: wsl --install
    echo   3. Use Google Cloud Shell: https://shell.cloud.google.com
    echo.
    pause
    exit /b 1
)

REM Check if gcloud is installed
gcloud --version >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Google Cloud CLI nao encontrado!
    echo.
    echo Instale o Google Cloud CLI:
    echo https://cloud.google.com/sdk/docs/install
    echo.
    echo Depois execute:
    echo   gcloud auth login
    echo   gcloud config set project SEU_PROJECT_ID
    echo.
    pause
    exit /b 1
)

echo ✅ Dependencias OK
echo.
echo 🔄 Executando script bash de setup...
echo.

REM Execute the bash script
bash scripts/setup_cloud_sql.sh

if %errorlevel% neq 0 (
    echo.
    echo ❌ Setup falhou!
    echo Verifique os logs acima para mais detalhes
    pause
    exit /b 1
)

echo.
echo ✅ Setup concluido com sucesso!
echo.
echo 🔍 Para validar o setup, execute:
echo   bash scripts/validate_setup.sh
echo.
pause