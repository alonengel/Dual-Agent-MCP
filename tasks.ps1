# Simple task runner wrapping the common uv commands.
# Usage:  powershell -File tasks.ps1 <task>   (or: pwsh -File tasks.ps1 <task>)
#   setup | lint | fmt | test | cov | selfplay | demo | serve-cop | serve-thief
#   serve-combined | cloud | netplay | notebook | all
param([Parameter(Position = 0)][string]$Task = "all")

$ErrorActionPreference = "Stop"

switch ($Task) {
    "setup"          { uv sync }
    "lint"           { uv run ruff check . }
    "fmt"            { uv run ruff check --fix . }
    "test"           { uv run pytest -q }
    "cov"            { uv run pytest --cov }
    "selfplay"       { uv run copthief selfplay --gui }
    "demo"           { uv run python scripts/capture_demo.py --seed 7 }
    "serve-cop"      { uv run copthief serve --role cop }
    "serve-thief"    { uv run copthief serve --role thief }
    "serve-combined" { uv run copthief serve-combined }
    "cloud" {
        if (-not $env:COPTHIEF_MCP_TOKEN) { $env:COPTHIEF_MCP_TOKEN = "local-dev-token" }
        Write-Host "Starting combined MCP server on :8080..."
        $srv = Start-Process -FilePath "uv" -ArgumentList "run", "copthief", "serve-combined" `
            -PassThru -NoNewWindow
        Start-Sleep -Seconds 3
        try {
            Write-Host "Cloudflare quick tunnel (Ctrl+C stops tunnel; server cleaned up)..."
            cloudflared tunnel --url http://localhost:8080
        } finally {
            if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
        }
    }
    "netplay"        { uv run copthief netplay --seed 7 }
    "notebook"       { uv run jupyter lab }
    "all"            { uv run ruff check .; uv run pytest --cov }
    default          { Write-Host "Unknown task '$Task'. See header for options."; exit 1 }
}
