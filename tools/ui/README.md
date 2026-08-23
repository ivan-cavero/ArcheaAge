# tools/ui — client UI modding (aa_ui addon)

How we add **custom Lua UI** (panels, moved elements, new behavior) to the
ArcheAge 1.2 client, and everything learned on the way. Status: **working** —
`addon_panel.lua` renders a branded info panel on the login-stage screens.

## The pipeline at a glance

```text
tools/ui/decompile.py all                 extract+decompile every .alb -> tools/ui/src/
tools/ui/addon_panel.lua                    edit this (plain Lua 5.1)
        │  luac5f.exe -o addon_panel.alb    compile (Lua 5.1, LUA_NUMBER=float!)
        ▼
tools/ui/push.py                          inject into CLIENT game_pak (pak-put)
        ▼
reopen the game (~40 s)                     panel renders on login/server-select
```

Debug channels after running the game:

| Channel | Path | What you get |
| --- | --- | --- |
| Client log | `Documents\ArcheAge\ArcheAge.log` (+ `LogBackups\`) | **Lua errors, script load failures** — read this first |
| Our io log | `<client>\aa_ui_log.txt` | whatever the addon writes via `L()` (only if the `io` lib exists in that state) |

## One-time setup

### 1. Build the compiler (`luac5f.exe`)

The client's Lua VM uses **32-bit floats** (`sizeof(lua_Number)=4`, verified in
the `.alb` headers), so stock Lua binaries produce rejected bytecode. Build it
once with any i686 GCC/Clang (llvm-mingw works):

```powershell
# get Lua 5.1.5 source, then:
cd lua-5.1.5/src
i686-w64-mingw32-gcc -O2 -o ..\luac5f.exe `
  lapi.c lcode.c ldebug.c ldo.c ldump.c lfunc.c lgc.c llex.c lmem.c `
  lobject.c lopcodes.c lparser.c lstate.c lstring.c ltable.c ltm.c `
  lundump.c lvm.c lzio.c lauxlib.c lbaselib.c ldblib.c liolib.c `
  lmathlib.c loslib.c lstrlib.c ltablib.c loadlib.c linit.c luac.c print.c
```

…and patch `luaconf.h` so the float sticks (stock file redefines it without a
guard): change line ~505 `#define LUA_NUMBER double` → `float`.

Sanity check: compiling anything must yield the header
`1B 4C 75 61 51 00 01 04 04 04 04 00` — byte-identical to every `.alb`
shipped in game_pak. We also verified against a known pair: compiling
`game/scripts/globalui/loading/loading.lua` matches its shipped
`loading.alb` through header+instructions+constants (differences are only
debug/line-info payload).

### 2. Hook the module tocs (already injected; idempotent)

`push.py` installs these every run:

- `loginstage/login/toc.g` and `loginstage/world_select/toc.g`: original
  contents + one appended line `../addon_panel.lua`.
- `loginstage/addon_panel.alb`: our compiled chunk.

⚠️ Path resolution gotcha that cost us hours: a toc entry `../foo.lua`
resolves **relative to the module folder**, e.g.
`scriptsbin/x2ui/loginstage/foo.alb` (NOT `scriptsbin/x2ui/foo.alb`). If the
path is wrong the client logs
`[Lua Error] Failed to load script file ...` in `ArcheAge.log`.

### 3. Decouple the server from the client pak

AAEmu.Game holds `ClientData.Sources` open, which locks `game_pak`. Point it
at a copy instead (done here):

```powershell
Copy-Item <client>\game_pak <client>\game_pak_server
# servers/aaemu/AAEmu.Game/Config.Local.json -> Sources = [<...>\game_pak_server]
```

Result: injecting UI never requires stopping the server; iteration is just
*edit → push → reopen client*.

## What else was discovered (and where each thing lives)

| Thing | Location / mechanism |
| --- | --- |
| Credits page ("ArcheaAge") | pak entry `game/ui/login_stage/html/made_en.html` — plain HTML rendered by Awesomium; whole-file swap via `tools/pak-put` (see `tools/branding/apply_branding.py`) |
| Visible UI strings ("Select Server", hints…) | NOT in the pak — they live in **`compact.sqlite3`**, table `localized_texts` (`tbl_name='ui_texts'`). Edit with `tools/db/dbtext.py` |
| Script loading mode | cvar `lua_use_binary` in cryscriptsystem.dll: `1` = `scriptsbin/*.alb`, `0` = `scripts/*.lua`. Only ~252 of 1035 modules have sources → binary mode is effectively mandatory |
| Native addon system | crysystem.dll mounts `/game`, `/USER`, `/addon`; scans `addon/<name>/toc.g`; per-account enable list in `Documents\ArcheAge\USER\Data\account\addon_list.g` (Lua-source `.g` format). Not yet needed — our toc hook already runs earlier |
| User folder | `Documents\ArcheAge\` (= `/USER` mount): `system.cfg`, `ArcheAge.log`, screenshots, shader cache, account data |
| Repacked-client junk | distributions ship `bin32/debug.log` from the packer's machine (references `C:\AAEMU`) — launcher deletes it post-extract |

## Restore / unhook

Everything is reversible from the original distribution archives kept in
`.clients/`: re-extract `game_pak` (and `compact.sqlite3`) over the patched
copies. The loose `addon\`, `bin32\addon\`, `USER\addon\` probe folders can be
deleted freely.

## Roadmap (the "engine-like editor" idea)

1. **Widget-tree dumper**: walk each screen's windows/children from our addon
   and dump names+anchors to the log → a live DOM-inspector of the UI.
2. **Override table**: addon reads a declarative layout file
   (window name → anchor/offset/color/text) so moving or restyling an element
   is editing one line — no recompile.
3. **Visual editor**: small web app rendering the dumped tree as draggable
   boxes over a screenshot, exporting the override file.
4. **Textures/backgrounds**: same pak pipeline — extract `.dds` with
   `pak-scan`, edit, `pak-put` back.
