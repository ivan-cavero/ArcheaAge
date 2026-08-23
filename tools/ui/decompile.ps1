# decompile.ps1 — batch-decompiles every .alb of a module set into readable
# Lua sources using unluac (tools/ui/unluac.jar).
#
#   powershell -File tools\ui\decompile.ps1 [-Module "loginstage"] [-ClientDir <dir>]
#
# Output: tools/ui/decompiled/<module-path>.lua  (gitignored: derived from
# game files; used as reference/documentation, never redistributed).

param(
    [string]$Module = "loginstage",
    [string]$ClientDir = ".client_files\ArcheAge 1.2 (r208022) for AAEmu"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pak = Join-Path $ClientDir "game_pak"
$jar = Join-Path $PSScriptRoot "unluac.jar"
$srcDir = Join-Path $env:TEMP "studio_src_alb"
$outDir = Join-Path $PSScriptRoot "decompiled"

New-Item -ItemType Directory -Force $outDir | Out-Null

# 1. extract every .alb of the module subtree
dotnet run --project (Join-Path $root "tools/pak-scan") -- $pak $srcDir ("scriptsbin/x2ui/" + $Module) | Out-Null

# 2. decompile each (skip failures individually)
$albs = Get-ChildItem $srcDir -Recurse -Filter "*.alb"
$ok = 0; $fail = 0
foreach ($a in $albs) {
    $rel = $a.FullName.Substring($srcDir.Length + 1).Replace("\", "/")   # scriptsbin/x2ui/...
    $out = Join-Path $outDir ($rel -replace "\.alb$", ".lua")
    New-Item -ItemType Directory -Force (Split-Path $out) | Out-Null
    & java -jar $jar -o $out $a.FullName 2>$null
    if ($LASTEXITCODE -eq 0 -and (Test-Path $out)) { $ok++ } else { $fail++ }
}
Write-Output "decompiled ok=$ok fail=$fail -> $outDir"
