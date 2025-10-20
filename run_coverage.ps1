Param(
  [string]$CovTargets = "web_ui/app.py web_ui/database.py web_ui/smart_matching_criteria.py web_ui/robust_revenue_matcher.py database_utils.py crypto_pricing.py",
  [string]$ExcludeExpr = "not app_transactions"
)

$ErrorActionPreference = 'Stop'

Write-Host "Running pytest with coverage..."

$py = 'C:\\Program Files\\Python314\\python.exe'
$args = @(
  '-m','pytest','-q'
)

# Add coverage args
foreach($t in $CovTargets.Split(' ')){
  $args += "--cov=$t"
}
$args += @('--cov-report=term-missing','--cov-report=html:htmlcov','-k', $ExcludeExpr)

& $py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Coverage HTML: htmlcov/index.html"
