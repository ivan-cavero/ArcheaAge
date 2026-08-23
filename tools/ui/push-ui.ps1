# push-ui.ps1 — one-shot UI iteration for our client-side Lua addon.
#
#   powershell -File tools\ui\push-ui.ps1 [-ClientDir <dir with game_pak>]
#
# Steps:
#   1. compiles tools/ui/addon_panel.lua -> addon_panel.alb
#      (luac5f.exe = Lua 5.1 built with LUA_NUMBER=float — REQUIRED, see README)
#   2. injects into the CLIENT game_pak:
#        - the compiled addon   -> game/scriptsbin/x2ui/loginstage/addon_panel.alb
#        - both toc.g hooks     -> .../loginstage/login/toc.g and .../world_select/toc.g
#           (idempotent: pak-put replaces existing entries)
#
# The AAEmu.Game server does NOT need restarting anymore: its ClientData.Sources
# points at game_pak_server (a copy), leaving the client pak free to modify.
# Player-side iteration = edit .lua -> run this -> reopen the game (~1 min).

param(
    [string]$ClientDir = ".client_files\ArcheAge 1.2 (r208022) for AAEmu"
)

$ErrorActionPreference = "Stop"
$root  = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # repo root
$pak   = Join-Path $ClientDir "game_pak"
$luac  = Join-Path $PSScriptRoot "luac-build\luac5f.exe"
$alb   = Join-Path $PSScriptRoot "luac-build\addon_panel.alb"

if (!(Test-Path $pak))  { throw "game_pak not found: $pak" }
if (!(Test-Path $luac)) { throw "luac5f.exe not found ($luac) - see tools/ui/README.md build step" }

# 1. compile (overrides.lua from the visual editor is prepended when present)
$src = Join-Path $PSScriptRoot "addon_panel.lua"
$ovr = Join-Path $PSScriptRoot "overrides.lua"
$probeSrc = Join-Path $PSScriptRoot "probe_dump.lua"
$alb2 = Join-Path $PSScriptRoot "luac-build\probe_dump.alb"
$combined = Join-Path $env:TEMP "ivanpanel_combined.lua"
if (Test-Path $ovr) {
    Get-Content $ovr, $src -Raw | Set-Content $combined -Encoding UTF8
    Write-Output "incluyendo overrides.lua"
    & $luac -o $alb $combined
} else {
    & $luac -o $alb $src
}
if ($LASTEXITCODE -ne 0) { throw "compile failed" }
& $luac -o $alb2 $probeSrc
if ($LASTEXITCODE -ne 0) { throw "probe compile failed" }
Write-Output ("[1/2] compiled: {0} bytes" -f (Get-Item $alb).Length)

# 2. inject (idempotent)
$pairs = @(
    @{ local = $alb;                                   entry = "game/scriptsbin/x2ui/loginstage/addon_panel.alb" },
    @{ local = $alb2;                                  entry = "game/scriptsbin/x2ui/loginstage/probe_dump.alb" },
    @{ local = Join-Path $PSScriptRoot "login_toc.g";        entry = "game/scriptsbin/x2ui/loginstage/login/toc.g" },
    @{ local = Join-Path $PSScriptRoot "world_select_toc.g"; entry = "game/scriptsbin/x2ui/loginstage/world_select/toc.g" }
)

foreach ($p in $pairs) {
    dotnet run --project (Join-Path $root "tools/pak-put") -- $pak $p.local $p.entry | Select-String -Pattern "replaced|added|VERIFIED|ERROR"
    if ($LASTEXITCODE -ne 0) { throw "pak-put failed for $($p.entry)" }
}
Write-Output "[2/2] injected. Reopen the game client to see changes."

# Debug channels after testing:
#   - Documents\ArcheAge\ArcheAge.log         (Lua errors, script load failures)
#   - <client>\ivanpanel_log.txt              (our io-based log, if io lib exists)
