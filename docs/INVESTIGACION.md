# Research: ArcheAge private server — Open Source, multi-version, plugins and custom content

> Date: research over public sources (forums, GitHub, MMO press, wikis).
> Facts verified as of February 2026 (AAEmu wiki) and news up to Feb 2026.

---

## 0. Executive summary (TL;DR)

- **The official game is dead.** NA/EU servers closed on **Jun 27, 2024**; Korea on **Mar 6, 2025**. The final western client was **v10.8.1.0 (r651723, May 2024)**. Only the Chinese version (Tencent) is still alive with its own numbering. The "successor" **ArcheAge Chronicles** was announced in 2024 and is delayed until **Q4 2026** — watch out: when it launches, legal attention on private servers may rise.
- **The community's "golden age" is 2.9/3.0** (2016–2017): the AA Classic private server chose 3.0 ("as it was meant to be played"), and ArcheRage forums have threads literally titled "the glory days" asking to go back to 2.9/3.0. **3.5 (Erenor) is seen by many as the beginning of the end** ("3.5 murdered the game"). 5.0 (Hiram gear) = the hated grind era.
- **No need to choose between "reverse engineering from the client" and "starting from a server base": both routes exist today and are complementary:**
  1. **Clean emulation route (open source): AAEmu** — C#/.NET emulator, LGPLv3, active, with CI, tests, clean architecture (managers with dependency injection), Lua scripting (NLua), and even a *skill for AI agents* in the repo. **But it only targets client 1.2 (r208022, 2014 launch era)** and is at **v0.3.0**: playable, but incomplete (still fixing packets, boat physics, farming...).
  2. **"Server files" route (leaked code): ArcheRage and AA Classic** run this way — that's why they have "perfect" 3.0–6.5 versions. It's not open source, it's legally grey, and it's exactly what the user CANNOT do if they want an open source project.
- **Realistic multi-version = NOT a multi-version binary.** Each version changes opcodes, encryption (AES-128-CBC + XOR), DB schema and client data. The ecosystem is already fragmented: 1.2 (AAEmu), 3.0 (NL0bP fork + AA Classic files), 5.0–6.5 (ArcheRage files), 10.8 (final dump). An open source project can **support 2 versions well** (e.g. 1.2 + 3.0) sharing the plugin layer and tools, not the same binary.
- **Plugins**: the reference model is **AzerothCore** (WoW): core + modules with script hooks. AAEmu has no public plugin API yet, but its architecture (interface-based managers + DI + NLua) is a reasonable base. We'd have to build: event bus, hook points, module loader, catalog.
- **Custom content (new zones/mobs)**: **porting content between versions is already proven** (gist "AAEmu Client Update 5.0 Zones": copy `main_world` + textures/models/materials between game_paks of different versions). **Creating 100% new assets is the hardest part of the project**: it requires a CryEngine 3 toolchain (the client is CryEngine 3), model exporters (.cgf/.chr), a world editor, navmesh (an exporter already exists), etc. It's a multi-year effort on its own.
- **AI agents: yes, viable, and the community already does it.** NL0bP (AAEmu lead) uses `ida-pro-mcp`, `ghidra-mcp`, `cheatengine-mcp-bridge` (MCP = Model Context Protocol, the same thing pi uses). AAEmu already has `.agents/skills/aaemu-setup` with asset inventory scripts and a Human-in-the-Loop flow. RE work (opcodes, packet structures, encryption) is the #1 candidate for automation with AI loops + regression tests over packet captures.
- **Viability verdict**: the full project (open source + plugins + multi-version + custom content + "perfect like the original") is a **multi-year team effort**. There's no shortcut. But there's a realistic phased path that starts with **contributing to AAEmu** (not forking from scratch), and each phase delivers something playable.

---

## 1. History, versions, and which one people liked most

### 1.1 Version timeline (West)

| Version | Approx. date | What it brought | Perception |
| --- | --- | --- | --- |
| **1.0–1.2** | Sep 2014 (NA/EU launch) | The base game. `r208022` = client 1.2.4 | Pure launch nostalgia. AAEmu targets it |
| 1.7 | 2015 | Pirates, sea content | Well received |
| 2.0 | 2015 | "Heroes Awaken": political system, guild wars | Good |
| 2.5–2.9 | 2016 | Bloodsong, festivals, Ascension | "Glory days" per the community |
| **3.0** | Jan 2017 | "Revelation": dwarves, more content | **The sweet spot. AA Classic chose it** |
| **3.5** | Jun 2017 | "Erenor Eternal": Erenor gear, trade revamp | **Controversial — "murdered the game" for many** |
| 4.0–4.5 | Nov 2017–Apr 2018 | "Maelstrom", boat arena, "Legends Return" fresh starts | Mixed |
| **5.0** | Oct 2018 | "Relics of Hiram": Hiram gear, ancestral levels | Start of the hated grind |
| 5.5–6.5 | 2019–2020 | Garden of the Gods, cross-server region | ArcheRage runs 6.5 |
| Unchained | Oct 2019 | B2P "without P2W" — failed, merged into legacy | Disappointment |
| 7.x–10.8 | 2020–2024 | Minor patches, decline | Deserted |
| **10.8.1.0** | May 2024 | Last western client (r651723) | Closure Jun 27, 2024 |

### 1.2 Which version do people prefer? (evidence)

- **AA Classic chose 3.0** "to experience the game as it was meant to be played" — with the old trade system (trade packs anywhere, even cross-continent) and **before** Hiram gear. Its motto is literally "the golden version".
- ArcheRage forum, thread "Fresh Start with version 2.9? A.K.A Classic Archeage A.K.A the glory days": *"AA after 3.5 imo felt dead"*; they ask to cut progression at 2.9/3.0.
- Thread "Will we ever get patch 3.5" on ArcheRage: *"3.5 murdered the game at official"* — Erenor gear and the crafting/trade revamp are pointed at as the turning point.
- **RNG** is the recurring villain: Trion promised to "kill the RNG" in 3.5 and 4.0 (MMORPG.com/MMOBomb interviews), and yet Hiram gear (5.0+) made it worse with random infusions and grades.
- **P2W** killed Europe: it's the absolute consensus on Reddit, Steam, Metacritic and forums. Unchained (B2P) also ended up P2W ("less so than the F2P version", Metacritic review).
- RaGEZONE thread (Jun 2026): people **still look for 3.5/4.0/4.5 server files** — "the golden era". The demand hasn't died.

**Version conclusion**: if the project wants ONE flagship version that the community perceives as "the good one", it's **3.0** (with 1.2 as an option for launch purists). 3.5+ is where "the game went downhill", consistent with what the user says.

### 1.3 Current state of the game

- NA/EU: closed Jun 27, 2024 (Kakao). Korea: closed Mar 6, 2025 (XLGAMES). "After 12 years of operation".
- China (Tencent, 上古世纪): still operating with its own numbering (classic "经典服" and live "现行服" clients downloadable from age.qq.com). Useful as a source of clients/patches.
- **ArcheAge Chronicles** (sequel, announced Sep 2024): repeatedly delayed (Q2 2025 → Q3 2026 → Q4 2026). If it ships, it's direct competition for nostalgic players' attention and may revive Kakao/XL's legal interest.

---

## 2. Existing private servers: what they do well and what they lack

### 2.1 ArcheRage (the big one, runs ~5.0–6.5 with leaked files)

**Good:**

- "Modern" version with late content (6.5 Garden of the Gods, Ipnysh Sanctuary).
- Free patron for everyone, labor x5, XP x5, drops x2 — aggressive QoL.
- Lots of population (reports of 1–3k concurrent at its peak; "very lively" in 2024).
- Community events, own launcher, professional patch notes.

**Bad (documented in their own forums and Reddit):**

- **P2W accusations** (thread "Wait, so private server is p2w also?!" since 2017; Jason Wivart video review).
- **Chronic desync** (official thread "Server Desync issues").
- **Speed hackers** since day 1 (thread "State of the Server", 2017) — lack of effective anti-cheat.
- **Land barons** hoarding land with alts; **RMT** (selling items for real money) as an economic focus; unbalanced factions.
- Reddit (post "Why is the current state of both servers garbage?", 2025): both big servers are "awful" — everything revolves around RMT of Erenor/Ayanad sets.

### 2.2 AA Classic (runs 3.0 with leaked files)

**Good:**

- The "golden" 3.0 version, classic trade, pre-Hiram.
- High labor + free patron, declared anti-cheat/anti-RMT.
- Reported population of 3–4k online (claims on Steam discussions).

**Bad:**

- **Disastrous launch** (Aug 2023): outages, relocated hardware, funding criticism (MassivelyOP, mein-mmo).
- Old gear RNG (downgrades, piece loss) scares part of the community (Mailvaltar).
- Opacity: not open source, no way to audit or contribute.

### 2.3 Common pattern (the gap your project would fill)

1. **Closed, opaque code** — nobody can audit, contribute or fork. You want open source: a real difference.
2. **No plugin API** — every modification is internal team patching. You want anyone to develop and propose.
3. **Weak anti-cheat** — speed hacks and RMT dominate. An open source project with tests and review can do better (though anti-cheat for an old client is an eternal battle).
4. **Poor RMT/economy management** — the value of a "perfect" server is also a healthy economy.
5. **Single-operator dependency** — if the admin leaves, everything dies. Open source = resilience.

---

## 3. Open source emulation: the real state of AAEmu

### 3.1 AAEmu (github.com/AAEmu/AAEmu) — the key project

- **What it is**: ArcheAge server emulator in **C#/.NET**, **LGPLv3** license, ~420 stars, ~10 active contributors (NL0bP, ZeromusXYZ, nikes, And70, RogerBarreto...), active Discord, maintained wiki (verified Feb 2026).
- **Version**: `develop` targets **client 1.2 (r208022)**. Latest release: **v0.3.0.20250429** (Apr 2025).
- **Architecture** (clean and AI-friendly):
  - `AAEmu.Login` (Kestrel/ASP.NET Core) — auth + server list.
  - `AAEmu.Game` — world simulation. **Interface-based managers with dependency injection** (IQuestManager, ISkillManager, IHousingManager, IAIManager, ICraftManager, IAuctionManager... ~50 managers). Dependencies: MySQL (state), SQLite (reference data `compact.sqlite3`), **NLua** (Lua), Jitter2 (physics).
  - `AAEmu.Commons` — network/packets/utilities.
  - `AAEmu.UnitTests` — unit test project.
  - `AAEmu.Aspire.AppHost` — local orchestration (MySQL in a container + login + game).
  - JSON config (`Config.Local.json` overrides everything).
- **CI/quality**: GitHub Actions (dotnetcore CI, **CodeQL**, Sonar, stale, wiki-sync), Coveralls coverage.
- **Real maturity**: v0.3.0 = playable (login, create character, enter world, basic quests/doodads/NPCs, farming, boats in progress) but **incomplete**: the release notes are packet fixes, data (doodads/npcs), boat physics, loot, respawns. The long road (full combat, AI, instances, raids, 2.0 political system, full trade) is 80% of the work.
- **Key fun fact**: the repo already has **`.agents/skills/aaemu-setup`** — a skill for AI agents with asset inventory scripts (PowerShell + Bash), Human-in-the-Loop flow for multi-GB downloads, config templates and troubleshooting. **The community is already preparing the repo for agents.**
- **Declared legal state**: "not affiliated with XLGames... nor associated". LGPLv3 on the emulator code (not on the client or the data).

### 3.2 Other projects

- **NL0bP/Archeage-Server-emulator** — older fork focused on **3.0.3.0** (client 2017-03-15). The encryption work (AES-128-CBC + XOR) and opcodes were born here. Direct reference for a 3.0 line.
- **Ko0z/ArcheCore** — 1.2 emulator in **C++**, very early (no DB, just login + walking around the world). Inspired by AAEmu.
- **Melia** (NoCode-NoLife) — Tree of Savior emulator (NL0bP contributes). Reference for extensible architecture.
- **Ecosystem tools (public repos)**:
  - `ZeromusXYZ/AAEmu-Packer` — `game_pak` editor (extract/replace/add files).
  - `Ingramz/aapatcher` / forks — apply PAK patches like the official launcher.
  - `ShannonAAEmu/ArcheAge-HackShieldDecrypter` — decrypt HackShield (anti-cheat) environment.
  - `ShannonAAEmu/ArcheAge-AiExporter` — export navmesh (AI routes) from the client.
  - `NL0bP/OpcodeAndNameFinder` — find opcodes and compare packet structures between versions.
  - `alxbl/archeage` — Wireshark dissector for the protocol (Lua).
  - `menta2k/Internal-Archeage-API` — internal API (C#) over the client's Lua interface (for bots/mods/QoL; proves the client exposes Lua).
  - `Markemp/Cryengine-Converter` — CryEngine model converter (.cgf/.chr); ArcheAge chunk support (version 801) was added over time.
  - `Noviern/aagamedump` — dump of the final client 10.8.1.0 (Kakao, r651723, 2024-05-02, "Final-EU-NA").
  - `NL0bP/archeage-db-cryptor` — game data DB encryption.
  - `ZeromusXYZ/AAEmu-Launcher` — launcher pointing at your own server.

### 3.3 The protocol (what you need to understand for RE)

- Two-stage encryption: **AES-CBC-128** + **XOR** procedure (different per direction). Keys are obtained from process memory (that's why NL0bP's first releases had "bad decryption of packets — do your own encryption research").
- **Opcodes change between versions** (hence the need for OpcodeAndNameFinder and per-version diffs).
- The client is **CryEngine 3** (C++), with lots of logic in **Lua** and data in `game_pak` + `compact.sqlite3`.

---

## 4. The two routes: RE from the client or start from a base?

### 4.1 Route A — Clean emulation (AAEmu-style): RE from the client + sniffing

- **How it works**: capture packets (Wireshark), decrypt, map opcodes to structures, reimplement server logic from scratch in C#.
- **Pros**: legally the most defensible path (original code, LGPLv3, no XLGAMES code); real open source; the community and tools already exist.
- **Cons**: it's **slow** — AAEmu has taken ~7 years and is at v0.3.0 for ONE version (1.2). Reaching "perfect" (all content, AI, instances) is a multi-year team project. Each new version multiplies the work (opcodes, encryption, data).

### 4.2 Route B — Server base (leaked server files) + modification

- **How it works**: ArcheRage and AA Classic run on leaked official server code (3.0–6.5), modified by their teams.
- **Pros**: the ONLY way to have 3.0+ versions "perfect like the original" in the short term. That's why the big PSs look complete.
- **Cons**: **not open source** (the code is XLGAMES property — publishing it = near-certain DMCA), legally grey (EULA forbids RE; emulators survive on tolerance, not right), dependence on leaks circulating on RaGEZONE/Discord (3.5+ still scarce), no quality or audit guarantees.

### 4.3 Verdict

**For your goal (open source + plugins + community) Route A is the only coherent one — but NOT from scratch: on top of AAEmu.** And Route B isn't entirely discarded: leaked code and client dumps serve as **protocol and data reference** to speed up Route A (compare opcodes, structures, DB schemas). The pragmatic hybrid: **AAEmu core (1.2) + a 3.0 line based on the NL0bP fork + use of files/dumps as reference documentation**, never as published code.

**Honest expectation**: no emulator reaches 100% (AzerothCore has been going 12+ years and still has gaps). "Perfect like the original" must be redefined as "complete core loops + playable content + healthy economy", not "byte-for-byte replica".

---

## 5. Multi-version: the reality

- **Each version changes**: packet opcodes, encryption/keys, DB schema (reference SQLite + state MySQL), client data (game_pak, compact.sqlite3), client Lua.
- **The ecosystem is already fragmented by version**: 1.2 (AAEmu develop), 3.0 (NL0bP fork, AA Classic files), 5.0–6.5 (ArcheRage files), 10.8 (final dump). No emulator serves two versions.
- **Realistic design**: a **monorepo with per-version lines** (`branch 1.2`, `branch 3.0`) sharing: (a) the **plugin API** (if the plugin contract is stable, a plugin works on both), (b) the **tools** (packer, opcode finder, tests), (c) the **data layer** where compatible. The server binary is NOT shareable between versions.
- **2 versions done well > 5 versions done badly.** Recommendation: **1.2 (AAEmu, stable base) + 3.0 (the "golden age")**. 3.5+ stays out of the initial scope (it's where "the game went downhill" and where RE work is heaviest).

---

## 6. Plugins: the AzerothCore model and what to build

### 6.1 The reference model (AzerothCore, WoW 3.3.5a)

- Modular core: modules live in `modules/`, cloned as independent repos, the build compiles them against the core.
- **Script hooks** in the core (`ScriptMgr.h`): hook points executed from world startup. Modules subscribe to hooks; if a hook is missing, it's added to the core via PR.
- Module catalog + skeleton-module + boilerplates to get started.
- Result: thousands of community modules without touching the core.

### 6.2 What AAEmu has today (base)

- Interface-based managers + DI → the natural equivalent of "script hooks" is an **event bus** + **hook points** in the managers.
- **NLua** is already a dependency → Lua scripting possible for content (quests, events).
- Unit tests + CI → a plugin can ship its own tests.
- **No** public plugin API, module loader, or catalog. That's what needs to be built (and it's a bounded engineering project, not research).

### 6.3 Recommended minimal design

1. **Typed event bus** in the core (world events: `PlayerLoggedIn`, `QuestCompleted`, `ItemCrafted`, `CombatKill`...).
2. **Hook points** in the managers (subscription interfaces).
3. **Module loader** (`modules/` directory, .NET assemblies loaded at startup — trivial in .NET with `Assembly.LoadFrom`).
4. **Versioned plugin contract** (an `IAaPlugin` interface + metadata attributes) so a plugin compiles against the SDK without touching the core.
5. **Plugin SDK** as a separate NuGet package (so the community compiles plugins without cloning the server).
6. **Registry/catalog** + compatibility CI (compile all plugins against each release).

This is the project's "moat": **the first ArcheAge emulator with a community plugin economy**, like AzerothCore is for WoW.

---

## 7. Custom content: decompiling the client and adding zones/mobs

### 7.1 What the client contains and what can be touched

| Layer | Format | Existing tools | Difficulty |
| --- | --- | --- | --- |
| Data packs | `game_pak` (CryEngine files) | AAEmu-Packer, aapatcher | Low |
| Game data (items, mobs, quests, NPCs) | `compact.sqlite3` (reference SQLite) + client Lua | SQL, Lua | **Low-medium** (data-driven: adding a mob = DB row + model + AI) |
| Worlds/zones | `worlds/` (main_world, terrain) inside the pak | **Porting between versions: proven** (5.0 zones gist) | Medium |
| Models/animations | `.cgf` / `.chr` / `.caf` (CryEngine 3) | Cryengine-Converter (partial, v801 chunks) | **High** (3D toolchain: export from Blender/3ds Max with CryEngine exporters) |
| Navmesh (AI routes) | navigation files | ArcheAge-AiExporter | Medium |
| Client logic | Lua | Internal-Archeage-API (CLR injection) | Medium-high |

### 7.2 What's viable and what isn't

- **VIABLE (months)**: add new items, mobs, quests, NPCs, doodads via DB + reused existing data; **port whole zones between versions** (copy `main_world` + textures/models/materials — there's already a gist doing it with the 5.0 zone on a 1.2.4 client); economy balancing; custom events.
- **HARD (years)**: new zones with 100% original assets — requires the **CryEngine 3 Sandbox Editor** (not public), mature model exporters (ArcheAge support in Cryengine-Converter is partial), and navmesh generation for new AI.
- **Realistic shortcut**: "new content" that looks like the game is achieved by **recombining existing assets** (models, textures, music, animations already in the client) — same as modders of other CryEngine games. The "decompile the client" pipeline = extract game_pak + convert + repack, and that ALREADY exists.

### 7.3 Full client decompilation

- The client is C++ (CryEngine 3) + Lua + data. "Decompiling it fully" (to readable C#/C++) is not the right goal: it's not needed. What's needed is **understanding the data interface** (pak, sqlite, Lua) and the **network protocol** — and that's mostly documented by the community (Wireshark dissector, OpcodeAndNameFinder, dumps).
- The client **is not redistributed** (it's XLGAMES IP). The open source project distributes the server and the tools; players bring their own client (that's how AAEmu does it: HitL downloads from MEGA/Drive).

---

## 8. Viability with AI agents, loops and tests

### 8.1 What already exists (hard evidence)

- **NL0bP** (AAEmu lead) contributes to **`mrexodia/ida-pro-mcp`**, **`bethington/ghidra-mcp`**, **`miscusi-peek/cheatengine-mcp-bridge`**, **`paperclipai/paperclip`** — i.e. **the person who knows most about ArcheAge RE is already using MCP so LLMs drive IDA/Ghidra/Cheat Engine**. "AI-driven reverse engineering" isn't speculation: it's the ecosystem's current practice.
- **AAEmu already has an agent skill** (`.agents/skills/aaemu-setup`) with asset inventory, HitL and troubleshooting — designed so an agent (like pi) sets up the server end-to-end.
- **CI already exists** (dotnetcore, CodeQL, Sonar, coveralls) + `AAEmu.UnitTests`.

### 8.2 Where AI loops fit (by impact order)

1. **Protocol RE (the bottleneck)**: loop of packet capture → decryption → opcode diff between versions → C# structure generation → **packet regression tests** (replaying captures against the server). Tools: Wireshark/tshark + ida/ghidra-MCP + OpcodeAndNameFinder. An agent can do "vibe reversing" with IDA Pro MCP (already mrexodia's practice).
2. **Data**: parse `compact.sqlite3`/Lua → generate typed loaders → integrity tests (every referenced item/mob/quest exists). Data PRs (doodads/npcs fixes) are the bulk of AAEmu's current work — highly automatable.
3. **Tests**: layered suite — unit (managers), integration (login → create → enter world), **golden packet tests** (a healthy session capture = regression fixture), and world smokes (spawn, quest, craft, combat). The repo already has the base.
4. **Plugins**: CI can compile all catalog plugins against each release (compatibility matrix) + per-plugin tests.
5. **Contributor onboarding**: agent skills (like AAEmu's) for setup, for porting content between versions, for writing a plugin.

### 8.3 Recommended team/automation structure

- **Repos**: server monorepo (1.2/3.0 lines) + plugin SDK repo (NuGet) + plugin catalog + RE tools repo.
- **CI/CD**: build + unit + integration per PR; CodeQL/Sonar; compiled release publishing (AAEmu already does it).
- **AI loops**: a "RE agent" (IDA/Ghidra MCP + captures), a "data agent" (DB/Lua), a "content agent" (pak/zones), a "plugin reviewer" (blind, reviews plugin PRs). With gauntlet/loop-engineering: each loop has a bar (a test that fails if the work is wrong).
- **Test-as-bar**: "it works" always means a reproducible suite, not "I tried it by hand".

---

## 9. Recommended phased roadmap

> Guiding principle: **never start from scratch; contribute to AAEmu first, fork later.** Each phase delivers something playable.

### Phase 0 — Immersion (1–2 months)

- Set up AAEmu locally (Aspire) with the `.agents/skills/aaemu-setup` skill — it serves to learn and to validate the agent flow.
- Join the AAEmu Discord, read the wiki (Components, Developer-Notes, FAQ), review recent PRs.
- **Flagship version decision**: 1.2 (AAEmu) vs 3.0 (NL0bP fork). Recommendation: **3.0 as the goal, 1.2 as the stable base** (the 3.0 fork is older and less maintained; porting 1.2→3.0 is a project in itself).

### Phase 1 — Foundations (3–6 months)

- Contribute fixes/features to AAEmu (gain context and reputation; the current team is small and welcomes contributors).
- **Build the plugin layer**: event bus + hook points + module loader + NuGet SDK + compatibility CI. (First differentiating deliverable.)
- **Strengthen tests**: golden packet tests (capture replay), login→world integration, core system smokes.

### Phase 2 — Version line (6–12 months)

- Choose ONE extra line (3.0) and consolidate the fork: encryption, opcodes, data.
- **Content porting** pipeline between versions (5.0 zones gist as a starting point), documented and tested.
- Basic anti-cheat + economy (labor, taxes, anti-RMT) as official plugins.

### Phase 3 — Custom content and community (12–24 months)

- Content toolchain: pak editor in CI, model converter, navmesh, "how to add a mob/zone" guides.
- Plugin catalog + proposal system (PRs reviewed with mandatory tests).
- Community events, periodic fresh starts.

### Phase 4 — Scale (24+ months)

- Multi-server (sharding), web API (AAEmu already has a WIP WebApi), metrics, own launcher.
- Evaluate supporting more versions ONLY if the plugin architecture allows it without disproportionate cost.

---

## 10. Risks and warnings

1. **Legal**: emulator code (LGPLv3) is established practice since 2019, but: **never publish leaked server code or client data**; **don't monetize** (donations for hosting costs are the standard; P2W/item selling is what attracts lawsuits and kills servers); the client isn't redistributed. **ArcheAge Chronicles (Q4 2026) may revive Kakao/XL attention** on the PS ecosystem.
2. **Time**: "perfect like the original" in clean emulation = years of team work. Route B (files) gives complete versions now, but kills the open source goal. There's no way to have both in the short term.
3. **Community**: current PSs are burned by RMT/desync/hackers. The project must earn trust with transparency (open source + public tests) from day 1.
4. **Anti-cheat**: an old client without official support is an eternal battle; plan server-side detection (speed/teleport heuristics, economy) before client-side.
5. **Scope creep**: multi-version + custom content + plugins + anti-cheat + community = too much for one team. The phased roadmap exists precisely to avoid dying of ambition.

---

## 11. Conclusion

The project is **viable but it's not a sprint: it's a team marathon**. The good news is that **nothing needs to be invented from scratch**: the open source emulator (AAEmu, 1.2), the 3.0 fork, the pak/model/navmesh tools, the protocol dissector, the agent skills and the RE MCP stack all exist and are active in 2026. The real gap the project would fill is:

1. **A community plugin layer** (nobody in ArcheAge has one; AzerothCore proved the model in WoW).
2. **Transparency and tests** (the big PSs are black boxes with RMT and desync).
3. **A "golden age" version line (3.0)** maintained as an open project, not as an admin's secret.
4. **A custom content pipeline** (porting zones between versions already works; new assets are the long frontier).

How to do it with AI: **protocol RE with IDA/Ghidra-MCP in loops with golden packet tests**, **data agents for SQLite/Lua**, **CI that compiles and tests every proposed plugin**, and **onboarding skills** so anyone can contribute. The first PR you should open isn't code: it's **joining AAEmu and helping them stabilize 1.2** — because every fix you land there is infrastructure for your project.

---

## Appendix: key sources

- AAEmu repo + wiki (Components, Client, Server, FAQ, Developer-Notes, Aspire Guide): github.com/AAEmu/AAEmu
- AAEmu `.agents/skills/aaemu-setup` (SKILL.md / REFERENCE.md)
- AAEmu releases v0.3.0.20250429 (release notes)
- NL0bP: Archeage-Server-emulator (3.0.3.0), OpcodeAndNameFinder, archeage-db-cryptor; contributions to ida-pro-mcp / ghidra-mcp / cheatengine-mcp-bridge / paperclip
- ZeromusXYZ: AAEmu-Packer, AAEmu-Launcher
- ShannonAAEmu: HackShieldDecrypter, AiExporter
- alxbl/archeage (Wireshark dissector), menta2k/Internal-Archeage-API, Markemp/Cryengine-Converter, Ko0z/ArcheCore, Noviern/aagamedump
- Gist "AAEmu Client Update 5.0 Zones" (porting zones between versions)
- MassivelyOP: NA/EU closure (Jun 2024), Korea closure (Mar 2025), AA Classic launch woes, rogue servers booming, ArcheAge Chronicles delays (Q4 2026)
- Forums: ArcheRage NA (glory days 2.9/3.0, 3.5 murdered the game, desync, p2w, speed hackers), AA Classic forum, RaGEZONE (3.5+ files search), r/archeage (state of PSs)
- Mailvaltar blog (ArcheRage 2024 experience), mein-mmo (PSs after the closure), MMORPG.com/MMOBomb (3.5/4.0 RNG interviews), Fandom wiki (update timeline), age.qq.com (Chinese clients)
- AzerothCore wiki (modular structure, create a module, catalogue)