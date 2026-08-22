# install-ui-addon.ps1 — injects our Lua UI addon into a client game_pak.
#
#   powershell -File tools\ui\install-ui-addon.ps1 -ClientDir "<dir with game_pak>"
#
# What it does:
#   1. packs tools/ui/addon_panel.lua  -> game/scriptsbin/x2ui/addon_panel.lua
#   2. packs tools/ui/login_toc.g      -> game/scriptsbin/x2ui/loginstage/login/toc.g
#      (original toc + one appended line: ../addon_panel.lua)
#
# The addon ships as plain Lua SOURCE: if the loader falls back to .lua when
# the .alb is missing, this runs without any compile step (fast iteration).
# If it doesn't fall back, nothing breaks — the line is simply ignored/error-
# contained and we switch to the compiled-bytecode route.
# Restore: re-extract game_pak from the original archives in .clients/.

param(
    [Parameter(Mandatory = $true)][string]$ClientDir
)

$ErrorActionPreference = "Stop"
$pak = Join-Path $ClientDir "game_pak"
if (!(Test-Path $pak)) { throw "game_pak not found: $pak" }

$pairs = @(
    @{ local = Join-Path $PSScriptRoot "addon_panel.lua"; entry = "game/scriptsbin/x2ui/addon_panel.lua" },
    @{ local = Join-Path $PSScriptRoot "login_toc.g";     entry = "game/scriptsbin/x2ui/loginstage/login/toc.g" }
)

foreach ($p in $pairs) {
    dotnet run --project (Join-Path $PSScriptRoot "..\pak-put") -- $pak $p.local $p.entry
    if ($LASTEXITCODE -ne 0) { throw "pak-put failed for $($p.entry)" }
}
Write-Output "UI addon installed."
