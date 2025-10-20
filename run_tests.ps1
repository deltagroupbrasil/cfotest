Param(
  [string]$TestDir = "DeltaCFOAgent/tests"
)

Write-Host "Running unit tests from: $TestDir"

function Run-WithPy {
  try {
    $py = Get-Command py -ErrorAction Stop
    Write-Host "Using Windows launcher: $($py.Source)"
    py -3 -m unittest discover -s $TestDir -p 'test_*.py' -v
    return $LASTEXITCODE
  } catch {
    return 9001
  }
}

function Run-WithPython {
  try {
    $python = Get-Command python -ErrorAction Stop
    Write-Host "Using python: $($python.Source)"
    python -m unittest discover -s $TestDir -p 'test_*.py' -v
    return $LASTEXITCODE
  } catch {
    return 9002
  }
}

$code = Run-WithPy
if ($code -eq 0) { exit 0 }

$code = Run-WithPython
if ($code -eq 0) { exit 0 }

Write-Host "ERROR: Python not found via 'py' or 'python'. Ensure Python 3.9+ is installed and on PATH."
exit 1

