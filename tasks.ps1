# Simple task runner wrapping the common uv commands.
# Usage:  powershell -File tasks.ps1 <task>   (or: pwsh -File tasks.ps1 <task>)
#   setup | lint | fmt | test | cov | selfplay | demo | serve-cop | serve-thief | netplay | notebook | all
param([Parameter(Position = 0)][string]$Task = "all")

$ErrorActionPreference = "Stop"

switch ($Task) {
    "setup"      { uv sync }
    "lint"       { uv run ruff check . }
    "fmt"        { uv run ruff check --fix . }
    "test"       { uv run pytest -q }
    "cov"        { uv run pytest --cov }
    "selfplay"   { uv run copthief selfplay --gui }
    "demo"       { uv run python scripts/capture_demo.py --seed 7 }
    "serve-cop"  { uv run copthief serve --role cop }
    "serve-thief"{ uv run copthief serve --role thief }
    "netplay"    { uv run copthief netplay --seed 7 }
    "notebook"   { uv run jupyter lab }
    "all"        { uv run ruff check .; uv run pytest --cov }
    default      { Write-Host "Unknown task '$Task'. See header for options."; exit 1 }
}
