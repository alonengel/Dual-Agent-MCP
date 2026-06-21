# Launch both MCP servers over HTTP and run a networked match against them.
# Mirrors the "self-game in the cloud" topology, but entirely on localhost.
#
# Usage:  pwsh -File scripts/run_local_cloud.ps1
# Requires: uv installed; run from the project root.

$ErrorActionPreference = "Stop"

# A shared token guards every MCP tool call; the orchestrator must use the same one.
if (-not $env:COPTHIEF_MCP_TOKEN) { $env:COPTHIEF_MCP_TOKEN = "local-dev-token" }
if (-not $env:COPTHIEF_LLM_PROVIDER) { $env:COPTHIEF_LLM_PROVIDER = "mock" }

Write-Host "Starting cop and thief MCP servers (HTTP)..."
$cop = Start-Process -FilePath "uv" -ArgumentList "run", "copthief", "serve", "--role", "cop" -PassThru -NoNewWindow
$thief = Start-Process -FilePath "uv" -ArgumentList "run", "copthief", "serve", "--role", "thief" -PassThru -NoNewWindow

try {
    Write-Host "Waiting for servers to come up..."
    Start-Sleep -Seconds 6
    Write-Host "Running networked match..."
    uv run copthief netplay --seed 7
}
finally {
    Write-Host "Stopping servers..."
    if ($cop -and -not $cop.HasExited) { Stop-Process -Id $cop.Id -Force }
    if ($thief -and -not $thief.HasExited) { Stop-Process -Id $thief.Id -Force }
}
