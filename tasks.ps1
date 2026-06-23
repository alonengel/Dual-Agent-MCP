# Simple task runner wrapping the common uv commands.
# Usage:  powershell -File tasks.ps1 <task>   (or: pwsh -File tasks.ps1 <task>)
#   setup | lint | fmt | test | cov | selfplay | demo | serve-cop | serve-thief
#   serve-combined | cloud | cloudplay | tunnel | netplay | notebook | all
param([Parameter(Position = 0)][string]$Task = "all")

$ErrorActionPreference = "Stop"

function Resolve-Cloudflared {
    $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "$env:ProgramFiles\Cloudflare\cloudflared\cloudflared.exe",
        "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe",
        "$env:ProgramFiles\cloudflared\cloudflared.exe",
        "$env:LOCALAPPDATA\Microsoft\WinGet\Links\cloudflared.exe"
    )
    foreach ($path in $candidates) {
        if ($path -and (Test-Path $path)) { return $path }
    }
    return $null
}

function Stop-PortListener {
    param([int]$Port = 8080)
    $pids = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($procId in $pids) {
        if ($procId -and $procId -ne 0) {
            Write-Host "Stopping stale listener on :$Port (PID $procId)..."
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

function Wait-PortReady {
    param([int]$Port = 8080, [int]$Seconds = 15)
    for ($i = 0; $i -lt $Seconds; $i++) {
        if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

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
        $cloudflared = Resolve-Cloudflared
        if (-not $cloudflared) {
            Write-Host "cloudflared not found on PATH."
            Write-Host "Install: winget install Cloudflare.cloudflared"
            Write-Host "Then add to PATH or restart the terminal."
            exit 1
        }
        Write-Host "Using cloudflared: $cloudflared"
        Stop-PortListener -Port 8080
        Start-Sleep -Seconds 1
        Write-Host "Starting combined MCP server on :8080..."
        $srv = Start-Process -FilePath "uv" -ArgumentList "run", "copthief", "serve-combined" `
            -PassThru -NoNewWindow
        if (-not (Wait-PortReady -Port 8080)) {
            Write-Host "ERROR: MCP server did not bind to :8080 (port still busy?)"
            Stop-PortListener -Port 8080
            if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
            exit 1
        }
        Write-Host "MCP server ready on http://127.0.0.1:8080"
        try {
            Write-Host "Cloudflare quick tunnel (Ctrl+C stops tunnel + server)..."
            & $cloudflared tunnel --url http://localhost:8080
        } finally {
            Stop-PortListener -Port 8080
            if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
        }
    }
    "tunnel" {
        # Fixed-URL named tunnel (e.g. https://mcp.alon.website). One-time setup first:
        # cloudflared tunnel login / create copthief / route dns + ~/.cloudflared/config.yml.
        if (-not $env:COPTHIEF_MCP_TOKEN) {
            Write-Host "Set COPTHIEF_MCP_TOKEN first (the same token the client/partner uses)."
            exit 1
        }
        $cloudflared = Resolve-Cloudflared
        if (-not $cloudflared) { Write-Host "cloudflared not found."; exit 1 }
        Stop-PortListener -Port 8080
        Start-Sleep -Seconds 1
        Write-Host "Starting combined MCP server on :8080..."
        $srv = Start-Process -FilePath "uv" -ArgumentList "run", "copthief", "serve-combined" `
            -PassThru -NoNewWindow
        if (-not (Wait-PortReady -Port 8080)) {
            Write-Host "ERROR: MCP server did not bind to :8080"
            if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
            exit 1
        }
        Write-Host "Server ready; starting named tunnel 'copthief' (Ctrl+C stops both)..."
        try {
            & $cloudflared tunnel run copthief
        } finally {
            Stop-PortListener -Port 8080
            if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
        }
    }
    "netplay"        { uv run copthief netplay --seed 7 }
    "cloudplay" {
        # Automated public self-game: server + tunnel + netplay + teardown, one command.
        if (-not $env:COPTHIEF_MCP_TOKEN) { $env:COPTHIEF_MCP_TOKEN = "local-dev-token" }
        $cloudflared = Resolve-Cloudflared
        if (-not $cloudflared) {
            Write-Host "cloudflared not found. Install: winget install Cloudflare.cloudflared"
            exit 1
        }
        Stop-PortListener -Port 8080
        Start-Sleep -Seconds 1
        New-Item -ItemType Directory -Force -Path "logs" | Out-Null
        $log = "logs/cloudflared_quick.log"
        if (Test-Path $log) { Remove-Item $log -Force }
        Write-Host "Starting combined MCP server on :8080..."
        $srv = Start-Process -FilePath "uv" -ArgumentList "run", "copthief", "serve-combined" `
            -PassThru -NoNewWindow
        $tun = $null
        try {
            if (-not (Wait-PortReady -Port 8080)) {
                Write-Host "ERROR: MCP server did not bind to :8080"; exit 1
            }
            Write-Host "Starting Cloudflare quick tunnel..."
            $tun = Start-Process -FilePath $cloudflared -PassThru -NoNewWindow `
                -ArgumentList "tunnel", "--url", "http://localhost:8080", "--logfile", $log
            $url = $null
            for ($i = 0; $i -lt 30; $i++) {
                Start-Sleep -Seconds 1
                if (Test-Path $log) {
                    $hit = Select-String -Path $log -ErrorAction SilentlyContinue `
                        -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -First 1
                    if ($hit) { $url = $hit.Matches[0].Value; break }
                }
            }
            if (-not $url) { Write-Host "ERROR: no tunnel URL captured"; exit 1 }
            Write-Host "Tunnel: $url"
            $env:COPTHIEF_COP_URL = "$url/cop/mcp"
            $env:COPTHIEF_THIEF_URL = "$url/thief/mcp"
            Start-Sleep -Seconds 4   # allow the edge to become reachable
            uv run copthief netplay --seed 7
        } finally {
            if ($tun -and -not $tun.HasExited) { Stop-Process -Id $tun.Id -Force }
            Stop-PortListener -Port 8080
            if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
        }
    }
    "notebook"       { uv run jupyter lab }
    "all"            { uv run ruff check .; uv run pytest --cov }
    default          { Write-Host "Unknown task '$Task'. See header for options."; exit 1 }
}
