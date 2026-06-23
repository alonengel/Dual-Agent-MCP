# Launch serve-combined and run a networked match against it on localhost.
# Mirrors the cloud tunnel topology (one port, path-routed) without a public URL.
#
# Usage:  powershell -File scripts/run_local_cloud.ps1
# Requires: uv installed; run from the project root.

$ErrorActionPreference = "Stop"

if (-not $env:COPTHIEF_MCP_TOKEN) { $env:COPTHIEF_MCP_TOKEN = "local-dev-token" }
if (-not $env:COPTHIEF_LLM_PROVIDER) { $env:COPTHIEF_LLM_PROVIDER = "mock" }
$env:COPTHIEF_COP_URL = "http://127.0.0.1:8080/cop/mcp"
$env:COPTHIEF_THIEF_URL = "http://127.0.0.1:8080/thief/mcp"

Write-Host "Starting combined MCP server on :8080 (/cop/mcp, /thief/mcp)..."
$srv = Start-Process -FilePath "uv" -ArgumentList "run", "copthief", "serve-combined" `
    -PassThru -NoNewWindow

try {
    Write-Host "Waiting for server to come up..."
    Start-Sleep -Seconds 5
    Write-Host "Running networked match..."
    uv run copthief netplay --seed 7
}
finally {
    Write-Host "Stopping server..."
    # `uv run` spawns a child that actually binds :8080; kill the listener too so the
    # port is freed (stopping the uv parent alone can leave the child orphaned).
    $listeners = @(Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($procId in $listeners) {
        if ($procId -and $procId -ne 0) { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue }
    }
    if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue }
}
