# build.ps1 - Windows equivalent of `make all` and `make test`.
# Usage:
#   .\build.ps1          run the full build, then the unit tests
#   .\build.ps1 -NoTest  run the build only
# Stops at the first step that fails.

param([switch]$NoTest)

$env:PYTHONUTF8 = "1"
Set-Location $PSScriptRoot

$steps = @(
    @("tools/fetch_frmr.py"),
    @("tools/check_environment.py"),
    @("tools/check_scope_changes.py"),
    @("tools/build_registry.py", "c"),
    @("tools/run_validators.py"),
    @("tools/check_evidence.py"),
    @("tools/build_mas.py"),
    @("tools/build_policies.py"),
    @("tools/build_docs.py"),
    @("tools/build_trust_center.py")
)

foreach ($step in $steps) {
    Write-Host "==> python $($step -join ' ')" -ForegroundColor Cyan
    & python @step
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $($step[0]) (exit code $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

if (-not $NoTest) {
    Write-Host "==> unit tests" -ForegroundColor Cyan
    & python -m unittest discover -s tests -t .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: unit tests" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "Build complete." -ForegroundColor Green
