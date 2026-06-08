param(
    [switch]$Execute
)

## Определяем корень репозитория (на уровень выше папки scripts)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$root = Split-Path -Parent $scriptDir
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$archive = Join-Path $root "archive\cleanup_$timestamp"

function Show-Action($action, $path) {
    Write-Host "[ACTION] $action -> $path"
}

# Files and patterns to archive
# Явные пути для переносимых файлов
$filesToMove = @(
    "$root\.env",
    "$root\.env.bak",
    "$root\.env.clean",
    "$root\backend\.env"
)

# DBs in data/
# DBs в data/ (если есть)
if (Test-Path "$root\data") {
    $dbs = Get-ChildItem -Path "$root\data" -Filter "*.db" -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
} else { $dbs = @() }

# Directories to remove
# Каталоги для удаления
$dirsToRemove = @(
    "$root\frontend\dist",
    "$root\frontend\node_modules",
    "$root\venv",
    "$root\.pytest_cache",
    "$root\.vs",
    "$root\.superdesign",
    "$root\.kilo",
    "$root\.kilocode",
    "$root\backend\__pycache__"
)

# Files to delete (pyc)
$pycFiles = Get-ChildItem -Path $root -Recurse -Include "*.pyc" -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }

Write-Host "Cleanup script (dry-run). Use -Execute to perform actions."
Write-Host "Archive target: $archive"
Write-Host "Found DB files:"
$dbs | ForEach-Object { Write-Host "  $_" }

if (-not $Execute) {
    Write-Host "\nDry-run mode: no changes will be made. Rerun with -Execute to apply."
}

if ($Execute) {
    New-Item -Path $archive -ItemType Directory -Force | Out-Null

    foreach ($f in $filesToMove) {
        if (Test-Path $f) {
            Show-Action "Move" $f
            Move-Item -Path $f -Destination $archive -Force
        }
    }

    foreach ($db in $dbs) {
        Show-Action "Move" $db
        Move-Item -Path $db -Destination $archive -Force
    }

    foreach ($d in $dirsToRemove) {
        if (Test-Path $d) {
            Show-Action "RemoveDir" $d
            Remove-Item -Path $d -Recurse -Force
        }
    }

    foreach ($p in $pycFiles) {
        Show-Action "RemoveFile" $p
        Remove-Item -Path $p -Force
    }

    Write-Host "Cleanup complete. Archive created at: $archive"
} else {
    Write-Host "Planned moves:"
    foreach ($f in $filesToMove) { if (Test-Path $f) { Write-Host "  Move: $f -> $archive" } }
    foreach ($db in $dbs) { Write-Host "  Move: $db -> $archive" }
    Write-Host "Planned removals:"
    foreach ($d in $dirsToRemove) { if (Test-Path $d) { Write-Host "  RemoveDir: $d" } }
    foreach ($p in $pycFiles) { Write-Host "  RemoveFile: $p" }
}
