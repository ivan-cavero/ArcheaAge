# rebuild.ps1 — compiles modified .lua files and injects them into game_pak.
#
# Usage:
#   powershell -File tools\ui\rebuild.ps1                    # recompile all
#   powershell -File tools\ui\rebuild.ps1 -File "path.lua"   # single file
#
# Flow: edit tools/ui/src/**/*.lua -> rebuild.ps1 -> reopen the game.
# The compiled .alb replaces the original entry in game_pak (pak-put).

param(
    [string]$File,
    [string]$ClientDir = ".client_files\ArcheAge 1.2 (r208022) for AAEmu"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pak = Join-Path $ClientDir "game_pak"
$luac = Join-Path $PSScriptRoot "luac-build\luac5f.exe"
$srcDir = Join-Path $PSScriptRoot ".." | Join-Path -ChildPath "src"
$srcDir = [IO.Path]::GetFullPath($srcDir)

if (!(Test-Path $luac)) { throw "luac5f.exe not found: $luac" }

# unlock pak if server is running
Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" |
    Where-Object { $_.CommandLine -match 'AAEmu\.Game\.dll' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Output "Game stopped for injection" }
Start-Sleep -Seconds 2

if ($File) {
    # single file mode
    $rel = [IO.Path]::GetFullPath($File).Substring($srcDir.Length + 1).Replace("\","/")
    $albEntry = $rel -replace "\.lua$", ".alb"
    $tmpAlb = Join-Path $env:TEMP "rebuild_tmp.alb"

    & $luac -o $tmpAlb $File
    if ($LASTEXITCODE -ne 0) { throw "compile failed: $File" }

    dotnet run --project (Join-Path $root "tools/pak-put") -- $pak $tmpAlb $albEntry
    Write-Output "injected: $albEntry"
} else {
    # batch: find .lua newer than their .alb counterpart in pak
    $changed = Get-ChildItem $srcDir -Recurse -Filter "*.lua" | Where-Object {
        $rel = $_.FullName.Substring($srcDir.Length + 1).Replace("\","/")
        $albPath = Join-Path $env:TEMP ("rebuild_" + $rel.Replace("/","\"))
        if (!(Test-Path $albPath) -or $_.LastWriteTime -gt (Get-Item $albPath).LastWriteTime) { $_ }
    }
    Write-Output ("{0} files to compile" -f $changed.Count)

    foreach ($f in $changed) {
        $rel = $f.FullName.Substring($srcDir.Length + 1).Replace("\","/")
        $albEntry = $rel -replace "\.lua$", ".alb"
        $tmpAlb = Join-Path $env:TEMP ("rebuild_" + [IO.Path]::GetFileName($f.Name) + ".alb")

        & $luac -o $tmpAlb $f.FullName
        if ($LASTEXITCODE -ne 0) { Write-Output "SKIP (compile error): $rel"; continue }

        dotnet run --project (Join-Path $root "tools/pak-put") -- $pak $tmpAlb $albEntry | Select-String "VERIFIED|added|replaced|relocated|ERROR"
    }
    Write-Output "batch done."
}
