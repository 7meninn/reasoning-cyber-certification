param(
    [int]$Port = 8501,
    [switch]$Background
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$Python = Join-Path $VenvPath "Scripts\python.exe"
$Requirements = Join-Path $ProjectRoot "requirements.txt"
$App = Join-Path $ProjectRoot "app\streamlit_app.py"

if (-not (Test-Path $Python)) {
    python -m venv $VenvPath
}

& $Python -m pip install --disable-pip-version-check --no-input -r $Requirements

if ($Background) {
    $ArgumentList = "-m streamlit run `"$App`" --server.port $Port --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false"
    Start-Process `
        -FilePath $Python `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden
    Write-Host "Demo running at http://127.0.0.1:$Port"
} else {
    & $Python -m streamlit run $App --server.port $Port --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
}
