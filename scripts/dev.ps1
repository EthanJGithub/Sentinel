# Sentinel — start the demoable stack locally WITHOUT Docker (Windows).
# Starts the MCP tool server, the Python agent (FastAPI), and the React console
# in separate windows. The agent uses the local catalog JSON + keyword RAG when
# Postgres / the C# service aren't running, so this is enough for the full demo.
#
#   ./scripts/dev.ps1                 # heuristic models ($0)
#   $env:ANTHROPIC_API_KEY="..."; $env:OPENAI_API_KEY="..."; $env:PROVIDER_MODE="demo"; ./scripts/dev.ps1
#
# Console: http://localhost:5173   Agent: http://localhost:8000   MCP: http://localhost:7100

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venv = "D:\sentinel-data\venvs\agent\Scripts\python.exe"

Write-Host "Seeding catalog..." -ForegroundColor Cyan
& python "$root\data\scripts\generate_catalog.py"

if (-not (Test-Path $venv)) {
  Write-Host "Creating agent venv on D:..." -ForegroundColor Cyan
  python -m venv D:\sentinel-data\venvs\agent
  & $venv -m pip install -q -r "$root\services\agent-python\requirements.txt"
}

Write-Host "Starting MCP tool server (:7100)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$root\services\mcp-tools-ts'; npm run http"

Write-Host "Starting Python agent (:8000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$root\services\agent-python'; `$env:MCP_URL='http://localhost:7100'; & '$venv' -m uvicorn app.main:app --port 8000"

Write-Host "Starting React console (:5173)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$root\web\console-ts'; npm run dev"

Write-Host "`nAll services launching. Open http://localhost:5173" -ForegroundColor Cyan
