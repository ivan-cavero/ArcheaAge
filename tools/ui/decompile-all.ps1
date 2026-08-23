# decompile-all.ps1 — batch decompiles EVERY .alb in game_pak to readable Lua.
# Output: tools/ui/src/  (mirrors the pak structure, .alb -> .lua)
#
# This gives you THE ENTIRE GAME UI AS CODE. Edit any file, then run
# tools\ui\rebuild.ps1 to compile+inject back into the pak.

param([string]$ClientDir = ".client_files\ArcheAge 1.2 (r208022) for AAEmu")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pak = Join-Path $ClientDir "game_pak"
$jar = Join-Path $PSScriptRoot "unluac.jar"
$srcDir = Join-Path $env:TEMP "all_alb"
$outDir = "$root\tools\ui\src"

# 1. extract every .alb
Write-Output "extracting all .alb files..."
dotnet run --project (Join-Path $root "tools/pak-scan") -- $pak $srcDir ".alb" --no-print

$albs = Get-ChildItem $srcDir -Recurse -Filter "*.alb"
Write-Output ("found {0} .alb files" -f $albs.Count)

# 2. decompile each
New-Item -ItemType Directory -Force $outDir | Out-Null
$ok = 0; $fail = 0; $i = 0
foreach ($a in $albs) {
    $i++
    $rel = $a.FullName.Substring($srcDir.Length + 1).Replace("\", "/")
    $out = Join-Path $outDir ($rel -replace "\.alb$", ".lua")
    New-Item -ItemType Directory -Force (Split-Path $out) | Out-Null

    & java -jar $jar -o $out $a.FullName 2>$null
    if ($LASTEXITCODE -eq 0 -and (Test-Path $out)) { $ok++ } else { $fail++ }

    if ($i % 100 -eq 0) { Write-Output "  $i/$($albs.Count)..." }
}
Write-Output ("done: ok={0} fail={1}" -f $ok, $fail)
