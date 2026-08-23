# sync-tree.ps1 — copies the freshly generated game UI tree from
# Documents\ArcheAge into the Studio's static frontend so it auto-loads,
# then validates it is parseable JSON.
#
# Regeneration flow (per client version):
#   1. tools\ui\push-ui.ps1            (injects probe_dump.alb)
#   2. Play until server-select, close
#   3. powershell tools\ui\sync-tree.ps1
#   4. commit apps/studio/ui/game_ui_tree.json

$src = Join-Path $env:USERPROFILE "Documents\ArcheAge\game_ui_tree.json"
$dst = Join-Path $PSScriptRoot "..\studio\ui\game_ui_tree.json"

if (!(Test-Path $src)) { Write-Error "tree not found: $src (run one in-game pass with the probe injected)"; exit 1 }

Copy-Item $src $dst -Force

try {
    $null = Get-Content $dst -Raw | ConvertFrom-Json
    $nodes = ([regex]::Matches((Get-Content $dst -Raw), '"path"')).Count
    Write-Output ("synced + valid JSON · {0} nodes -> {1}" -f $nodes, $dst)
} catch {
    Write-Error "copied file is not valid JSON: $_"
    exit 1
}
