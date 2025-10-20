@echo off
setlocal

set PY=C:\Program Files\Python314\python.exe
set COVTARGETS=web_ui/app.py web_ui/database.py web_ui/smart_matching_criteria.py web_ui/robust_revenue_matcher.py database_utils.py crypto_pricing.py
set EXCLUDE=not app_transactions

echo Running pytest with coverage...
"%PY%" -m pytest -q --cov=web_ui/app.py --cov=web_ui/database.py --cov=web_ui/smart_matching_criteria.py --cov=web_ui/robust_revenue_matcher.py --cov=database_utils.py --cov=crypto_pricing.py --cov-report=term-missing --cov-report=html:htmlcov -k "%EXCLUDE%"
set ERR=%ERRORLEVEL%
if %ERR% NEQ 0 exit /b %ERR%

echo Coverage HTML: htmlcov\index.html
exit /b 0
