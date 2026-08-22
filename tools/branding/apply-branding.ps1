# apply-branding.ps1 — replaces the login-stage "made by" page inside an
# ArcheAge client game_pak with our own branding (whole-file swap via pak-put,
# so there is no length limit and the original stays recoverable from the
# distribution archives in .clients/).
#
# Usage:
#   powershell -File tools\branding\apply-branding.ps1 -ClientDir "<dir with game_pak>" `
#              [-Line1 "ArcheaAge"] [-Line2 "Edited by Ivan Cavero"]
#
# Re-run any time to change the text; re-apply to a fresh client copy before
# re-archiving it for distribution (tools/client-sourcing/rearchive-clients.sh).

param(
    [Parameter(Mandatory = $true)][string]$ClientDir,
    [string]$Line1 = "ArcheaAge",
    [string]$Line2 = "Edited by Ivan Cavero"
)

$ErrorActionPreference = "Stop"

$pak = Join-Path $ClientDir "game_pak"
if (!(Test-Path $pak)) { throw "game_pak not found: $pak" }
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$html = @"
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>made</title>
<style>
  html, body { margin: 0; padding: 0; background: transparent; overflow: hidden; }
  #brand {
    position: absolute; left: 0; right: 0; bottom: 28px; text-align: center;
    font-family: "Trebuchet MS", Verdana, sans-serif; color: #cfe3ff;
    text-shadow: 0 0 6px rgba(80, 140, 255, 0.9), 0 1px 2px #000;
  }
  #brand .l1 { font-size: 22px; font-weight: bold; letter-spacing: 5px; }
  #brand .l2 { font-size: 13px; letter-spacing: 2px; margin-top: 7px; color: #9fb8d8; }
</style>
</head>
<body valign="middle" leftmargin="0" topmargin="0">
<div id="brand">
  <div class="l1">$Line1</div>
  <div class="l2">$Line2</div>
</div>
</body>
</html>
"@

$tmp = Join-Path ([IO.Path]::GetTempPath()) "aa-branding"
New-Item -ItemType Directory -Force $tmp | Out-Null
$dst = Join-Path $tmp "made_branded.html"
[IO.File]::WriteAllText($dst, $html, [Text.UTF8Encoding]::new($false))

foreach ($entry in @(
    "game/ui/login_stage/html/made_en.html",
    "game/ui/login_stage/html/made_kr.html"
)) {
    dotnet run --project (Join-Path $PSScriptRoot "..\pak-put") -- $pak $dst $entry
    if ($LASTEXITCODE -ne 0) { throw "pak-put failed for $entry" }
}

Write-Output "branding applied: '$Line1' / '$Line2'"
Write-Output "restore path: re-extract game_pak from the original archive in .clients/"
