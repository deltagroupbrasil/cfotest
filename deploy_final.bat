@echo off
echo Executando deploy final para Cloud Run...
set CLOUDSDK_PYTHON=C:\Program Files\Python312\python.exe
cd "C:\Users\Delta Mining\Claude\DeltaCFOAgent"
gcloud run deploy delta-cfo-agent --source . --dockerfile Dockerfile.cloudsql --platform managed --region us-central1 --allow-unauthenticated --memory 1Gi --cpu 1 --port 8080 --timeout 900 --set-env-vars="DB_TYPE=postgresql,DB_HOST=34.27.251.47,DB_PORT=5432,DB_NAME=delta_cfo,DB_USER=delta_user,DB_SOCKET_PATH=/cloudsql/aicfo-473816:us-central1:delta-cfo-db,FLASK_ENV=production" --set-cloudsql-instances="aicfo-473816:us-central1:delta-cfo-db" --set-secrets="DB_PASSWORD=db_password:latest,ANTHROPIC_API_KEY=anthropic_key:latest,FLASK_SECRET_KEY=flask_secret_key:latest" --project=aicfo-473816
echo.
echo Deploy finalizado!
pause