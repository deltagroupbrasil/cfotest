@echo off
setlocal

set TESTDIR=DeltaCFOAgent\tests
echo Running unit tests from: %TESTDIR%

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  echo Using Windows launcher: py
  py -3 -m unittest discover -s %TESTDIR% -p "test_*.py" -v
  exit /b %ERRORLEVEL%
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
  for /f "delims=" %%P in ('where python') do echo Using python: %%P & goto :runpy
)

echo ERROR: Python not found via 'py' or 'python'. Ensure Python 3.9+ is installed and on PATH.
exit /b 1

:runpy
python -m unittest discover -s %TESTDIR% -p "test_*.py" -v
exit /b %ERRORLEVEL%

