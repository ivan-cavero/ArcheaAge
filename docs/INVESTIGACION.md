# Investigación: Servidor privado de ArcheAge — Open Source, multi-versión, plugins y contenido custom

> Fecha: investigación sobre fuentes públicas (foros, GitHub, prensa de MMO, wikis).
> Estado de los hechos verificado a febrero 2026 (AAEmu wiki) y noticias hasta feb 2026.

---

## 0. Resumen ejecutivo (TL;DR)

- **El juego oficial está muerto.** Servidores NA/EU cerrados el **27 jun 2024**; Corea el **6 mar 2025**. El client final occidental fue **v10.8.1.0 (r651723, mayo 2024)**. Solo la versión china (Tencent) sigue viva con numeración propia. El "sucesor" **ArcheAge Chronicles** se anunció en 2024 y está retrasado hasta **Q4 2026** — ojo, porque cuando salga, la atención legal sobre los PS puede subir.
- **La "edad de oro" según la comunidad es 2.9/3.0** (2016–2017): el server privado AA Classic eligió 3.0 ("como se quiso jugar"), y en los foros de ArcheRage hay hilos titulados literalmente "the glory days" pidiendo volver a 2.9/3.0. **3.5 (Erenor) es visto por muchos como el principio del fin** ("3.5 murdered the game"). 5.0 (gear Hiram) = la era del grind odiado.
- **No hay que elegir entre "reverse engineering desde el client" y "partir de una base de servidor": hoy existen las dos rutas y son complementarias:**
  1. **Ruta emulación limpia (open source): AAEmu** — emulador en C#/.NET, LGPLv3, activo, con CI, tests, arquitectura limpia (managers con inyección de dependencias), scripting Lua (NLua), y hasta una *skill para agentes AI* en el repo. **Pero solo apunta al client 1.2 (r208022, era de lanzamiento 2014)** y está en **v0.3.0**: jugable, pero incompleto (siguen arreglando paquetes, física de barcos, plantación...).
  2. **Ruta "server files" (código filtrado): ArcheRage y AA Classic** corren así — por eso tienen versiones 3.0–6.5 "perfectas". No es open source, es legalmente gris, y es exactamente lo que el usuario NO puede hacer si quiere un proyecto open source.
- **Multi-versión realista = NO un binario multi-versión.** Cada versión cambia opcodes, cifrado (AES-128-CBC + XOR), esquema de BD y datos del client. El ecosistema ya está fragmentado: 1.2 (AAEmu), 3.0 (fork de NL0bP + files de AA Classic), 5.0–6.5 (files de ArcheRage), 10.8 (dump final). Un proyecto open source puede **soportar 2 versiones bien** (p.ej. 1.2 + 3.0) compartiendo la capa de plugins y las herramientas, no el mismo binario.
- **Plugins**: el modelo de referencia es **AzerothCore** (WoW): núcleo + módulos con hooks de script. AAEmu no tiene API de plugins pública todavía, pero su arquitectura (managers por interfaz + DI + NLua) es una base razonable. Habría que construir: bus de eventos, hook points, loader de módulos, catálogo.
- **Contenido custom (zonas/mobs nuevos)**: **portar contenido entre versiones YA está demostrado** (gist "AAEmu Client Update 5.0 Zones": se copia `main_world` + texturas/modelos/materials entre game_pak de versiones distintas). **Crear assets 100% nuevos es lo más difícil del proyecto**: requiere toolchain CryEngine 3 (el client es CryEngine 3), exportadores de modelos (.cgf/.chr), editor de mundos, navmesh (ya hay exportador), etc. Es un esfuerzo de años por sí solo.
- **Agentes AI: sí, es viable y la comunidad ya lo hace.** NL0bP (líder de AAEmu) usa `ida-pro-mcp`, `ghidra-mcp`, `cheatengine-mcp-bridge` (MCP = Model Context Protocol, lo mismo que usa pi). AAEmu ya tiene `.agents/skills/aaemu-setup` con scripts de inventario de assets y flujo Human-in-the-Loop. El trabajo de RE (opcodes, estructuras de paquetes, cifrado) es el candidato #1 a automatizar con loops de AI + tests de regresión sobre capturas de paquetes.
- **Veredicto de viabilidad**: el proyecto completo (open source + plugins + multi-versión + contenido custom + "perfecto como el original") es un **esfuerzo de equipo de varios años**. No existe atajo. Pero hay un camino realista por fases que arranca en **contribuir a AAEmu** (no forkear desde cero), y cada fase entrega algo jugable.

---

## 1. Historia, versiones y cuál gustó más

### 1.1 Timeline de versiones (Occidente)

| Versión | Fecha aprox. | Qué trajo | Percepción |
| --- | --- | --- | --- |
| **1.0–1.2** | Sep 2014 (lanzamiento NA/EU) | El juego base. `r208022` = client 1.2.4 | Nostalgia pura del lanzamiento. AAEmu lo apunta |
| 1.7 | 2015 | Piratas, contenido marítimo | Bien recibido |
| 2.0 | 2015 | "Heroes Awaken": sistema político, guerras de guildas | Bien |
| 2.5–2.9 | 2016 | Bloodsong, festivales, Ascension | "Glory days" según comunidad |
| **3.0** | Ene 2017 | "Revelation": enanos, más contenido | **El punto dulce. AA Classic lo eligió** |
| **3.5** | Jun 2017 | "Erenor Eternal": gear Erenor, revamp de comercio | **Controvertido — "murdered the game" para muchos** |
| 4.0–4.5 | Nov 2017–Abr 2018 | "Maelstrom", arena de barcos, fresh starts "Legends Return" | Mixto |
| **5.0** | Oct 2018 | "Relics of Hiram": gear Hiram, ancestral levels | Inicio del grind odiado |
| 5.5–6.5 | 2019–2020 | Garden of the Gods, región cross-server | ArcheRage corre 6.5 |
| Unchained | Oct 2019 | B2P "sin P2W" — fracasó, se fusionó a legacy | Decepción |
| 7.x–10.8 | 2020–2024 | Parches menores, declive | Desertado |
| **10.8.1.0** | May 2024 | Último client occidental (r651723) | Cierre 27 jun 2024 |

### 1.2 ¿Qué versión prefiere la gente? (evidencia)

- **AA Classic eligió 3.0** "para experimentar el juego como se quería jugar" — con el sistema de comercio antiguo (trade packs en cualquier lado, incluso cross-continent) y **antes** del gear Hiram. Su lema es literalmente "la versión dorada".
- Foro de ArcheRage, hilo "Fresh Start with version 2.9? A.K.A Classic Archeage A.K.A the glory days": *"AA after 3.5 imo felt dead"*; piden cortar la progresión en 2.9/3.0.
- Hilo "Will we ever get patch 3.5" en ArcheRage: *"3.5 murdered the game at official"* — el gear Erenor y el revamp de crafting/comercio son señalados como el punto de inflexión.
- El **RNG** es el villano recurrente: Trion prometió "matar el RNG" en 3.5 y 4.0 (entrevistas MMORPG.com/MMOBomb), y aun así el gear Hiram (5.0+) lo empeoró con infusions y grades aleatorios.
- El **P2W** mató Europa: es el consenso absoluto en Reddit, Steam, Metacritic y foros. Unchained (B2P) también acabó con P2W ("less so than the F2P version", reseña de Metacritic).
- Hilo de RaGEZONE (jun 2026): gente **sigue buscando server files de 3.5/4.0/4.5** — "la era dorada". La demanda no ha muerto.

**Conclusión de versión**: si el proyecto quiere UNA versión insignia que la comunidad perciba como "la buena", es **3.0** (con opción 1.2 para puristas del lanzamiento). 3.5+ es donde "el juego fue a peor", coherente con lo que dice el usuario.

### 1.3 Estado actual del juego

- NA/EU: cerrado 27 jun 2024 (Kakao). Corea: cerrado 6 mar 2025 (XLGAMES). "After 12 years of operation".
- China (Tencent, 上古世纪): sigue operando con numeración propia (cliente "经典服" classic y "现行服" live descargables desde age.qq.com). Útil como fuente de clientes/parches.
- **ArcheAge Chronicles** (secuela, anunciada sep 2024): retrasada repetidamente (Q2 2025 → Q3 2026 → Q4 2026). Si sale, es competencia directa por la atención de los jugadores nostálgicos y puede reactivar el interés legal de Kakao/XL.

---

## 2. Servidores privados existentes: qué hacen bien y qué les falta

### 2.1 ArcheRage (el grande, corre ~5.0–6.5 con files filtrados)

**Bien:**

- Versión "moderna" con contenido tardío (6.5 Garden of the Gods, Ipnysh Sanctuary).
- Patron gratis para todos, labor x5, XP x5, drops x2 — QoL agresiva.
- Mucha población (reportes de 1–3k concurrentes en su época; "very lively" en 2024).
- Eventos comunitarios, launcher propio, patch notes profesionales.

**Mal (documentado en sus propios foros y Reddit):**

- **Acusaciones de P2W** (hilo "Wait, so private server is p2w also?!" desde 2017; video-review de Jason Wivart).
- **Desync crónico** (hilo oficial "Server Desync issues").
- **Speed hackers** desde el día 1 (hilo "State of the Server", 2017) — falta de anti-cheat eficaz.
- **Land barons** con alts acaparando tierra; **RMT** (venta de items por dinero real) como foco de la economía; facciones desbalanceadas.
- Reddit (post "Why is the current state of both servers garbage?", 2025): ambos servidores grandes están "awful" — todo gira en torno a RMT de sets Erenor/Ayanad.

### 2.2 AA Classic (corre 3.0 con files filtrados)

**Bien:**

- La versión "dorada" 3.0, comercio clásico, pre-Hiram.
- Labor alta + patron gratis, anti-cheat/anti-RMT declarados.
- Población reportada de 3–4k online (claims en Steam discussions).

**Mal:**

- **Lanzamiento desastroso** (ago 2023): caídas, hardware reubicado, críticas por financiación (MassivelyOP, mein-mmo).
- El RNG de gear antiguo (downgrades, pérdida de piezas) ahuyenta a parte de la comunidad (Mailvaltar).
- Opacidad: no open source, no hay forma de auditar ni contribuir.

### 2.3 Patrón común (el hueco que tu proyecto llenaría)

1. **Código cerrado y opaco** — nadie puede auditar, contribuir ni forkear. Tú quieres open source: diferencia real.
2. **Sin API de plugins** — toda modificación es parcheo interno del equipo. Tú quieres que cualquiera desarrolle y proponga.
3. **Anti-cheat débil** — speed hacks y RMT dominan. Un proyecto open source con tests y revisión puede hacerlo mejor (aunque el anti-cheat de un client viejo es batalla eterna).
4. **Gestión de RMT/economía pobre** — el valor de un server "perfecto" es también economía sana.
5. **Dependencia de un operador** — si el admin se va, muere todo. Open source = resiliencia.

---

## 3. Emulación open source: el estado real de AAEmu

### 3.1 AAEmu (github.com/AAEmu/AAEmu) — el proyecto clave

- **Qué es**: emulador de servidor de ArcheAge en **C#/.NET**, licencia **LGPLv3**, ~420 estrellas, ~10 contribuidores activos (NL0bP, ZeromusXYZ, nikes, And70, RogerBarreto...), Discord activo, wiki mantenida (verificada feb 2026).
- **Versión**: `develop` apunta a **client 1.2 (r208022)**. Último release: **v0.3.0.20250429** (abr 2025).
- **Arquitectura** (limpia y AI-amigable):
  - `AAEmu.Login` (Kestrel/ASP.NET Core) — auth + lista de servidores.
  - `AAEmu.Game` — simulación del mundo. **Managers por interfaz con inyección de dependencias** (IQuestManager, ISkillManager, IHousingManager, IAIManager, ICraftManager, IAuctionManager... ~50 managers). Dependencias: MySQL (estado), SQLite (datos de referencia `compact.sqlite3`), **NLua** (Lua), Jitter2 (física).
  - `AAEmu.Commons` — red/paquetes/utilidades.
  - `AAEmu.UnitTests` — proyecto de tests unitarios.
  - `AAEmu.Aspire.AppHost` — orquestación local (MySQL en contenedor + login + game).
  - Config por JSON (`Config.Local.json` sobreescribe todo).
- **CI/calidad**: GitHub Actions (dotnetcore CI, **CodeQL**, Sonar, stale, wiki-sync), cobertura con Coveralls.
- **Madurez real**: v0.3.0 = jugable (login, crear personaje, entrar al mundo, quests/doodads/NPCs básicos, plantación, barcos en progreso) pero **incompleto**: las notas de release son fixes de paquetes, datos (doodads/npcs), física de barcos, loot, respawns. El largo camino (combate completo, IA, instancias, raids, sistema político 2.0, comercio completo) es el 80% del trabajo.
- **Dato curioso clave**: el repo ya tiene **`.agents/skills/aaemu-setup`** — una skill para agentes AI con scripts de inventario de assets (PowerShell + Bash), flujo Human-in-the-Loop para descargas multi-GB, plantillas de config y troubleshooting. **La comunidad ya está preparando el repo para agentes.**
- **Estado legal declarado**: "not affiliated with XLGames... nor associated". LGPLv3 sobre el código del emulador (no sobre el client ni los datos).

### 3.2 Otros proyectos

- **NL0bP/Archeage-Server-emulator** — fork anterior enfocado en **3.0.3.0** (client 2017-03-15). El trabajo de cifrado (AES-128-CBC + XOR) y opcodes nació aquí. Referencia directa para una línea 3.0.
- **Ko0z/ArcheCore** — emulador 1.2 en **C++**, muy temprano (sin BD, solo login + correr por el mundo). Inspirado en AAEmu.
- **Melia** (NoCode-NoLife) — emulador de Tree of Savior (NL0bP contribuye). Referencia de arquitectura extensible.
- **Herramientas del ecosistema (repos públicos)**:
  - `ZeromusXYZ/AAEmu-Packer` — editor de `game_pak` (extraer/reemplazar/añadir archivos).
  - `Ingramz/aapatcher` / forks — aplicar parches PAK como el launcher oficial.
  - `ShannonAAEmu/ArcheAge-HackShieldDecrypter` — descifrar entorno de HackShield (anti-cheat).
  - `ShannonAAEmu/ArcheAge-AiExporter` — exportar navmesh (rutas de IA) del client.
  - `NL0bP/OpcodeAndNameFinder` — encontrar opcodes y comparar estructuras de paquetes entre versiones.
  - `alxbl/archeage` — disector de Wireshark para el protocolo (Lua).
  - `menta2k/Internal-Archeage-API` — API interna (C#) sobre la interfaz Lua del client (para bots/mods/QoL; demuestra que el client expone Lua).
  - `Markemp/Cryengine-Converter` — conversor de modelos CryEngine (.cgf/.chr); el soporte de chunks de ArcheAge (versión 801) se fue añadiendo.
  - `Noviern/aagamedump` — dump del client final 10.8.1.0 (Kakao, r651723, 2024-05-02, "Final-EU-NA").
  - `NL0bP/archeage-db-cryptor` — cifrado de la BD de datos del juego.
  - `ZeromusXYZ/AAEmu-Launcher` — launcher que apunta al server propio.

### 3.3 El protocolo (lo que hay que entender para RE)

- Cifrado en dos etapas: **AES-CBC-128** + procedimiento **XOR** (distinto en cada dirección). Las claves se obtienen de memoria del proceso (por eso los primeros releases de NL0bP tenían "bad decryption of packets — do your own encryption research").
- Los **opcodes cambian entre versiones** (de ahí la necesidad de OpcodeAndNameFinder y de diffs por versión).
- El client es **CryEngine 3** (C++), con mucha lógica en **Lua** y datos en `game_pak` + `compact.sqlite3`.

---

## 4. Las dos rutas: ¿RE desde el client o partir de una base?

### 4.1 Ruta A — Emulación limpia (AAEmu-style): RE desde el client + sniffing

- **Cómo funciona**: se capturan paquetes (Wireshark), se descifra, se mapean opcodes a estructuras, se reimplementa la lógica del server desde cero en C#.
- **Ventajas**: legalmente el camino más defendible (código original, LGPLv3, sin código de XLGAMES); open source real; la comunidad y las herramientas ya existen.
- **Desventajas**: es **lento** — AAEmu lleva ~7 años y está en v0.3.0 para UNA versión (1.2). Llegar a "perfecto" (todo el contenido, IA, instancias) es un proyecto de equipo de años. Cada versión nueva multiplica el trabajo (opcodes, cifrado, datos).

### 4.2 Ruta B — Base de servidor (server files filtrados) + modificación

- **Cómo funciona**: ArcheRage y AA Classic corren sobre código de servidor oficial filtrado (3.0–6.5), modificado por sus equipos.
- **Ventajas**: es la ÚNICA forma de tener versiones 3.0+ "perfectas como el original" a corto plazo. Por eso los PS grandes se ven completos.
- **Desventajas**: **no es open source** (el código es propiedad de XLGAMES — publicarlo = DMCA casi seguro), legalmente gris (EULA prohíbe RE; los emuladores sobreviven por tolerancia, no por derecho), dependencia de filtraciones que circulan en RaGEZONE/Discord (3.5+ siguen escaseando), sin garantías de calidad ni auditoría.

### 4.3 Veredicto

**Para tu objetivo (open source + plugins + comunidad) la Ruta A es la única coherente — pero NO desde cero: sobre AAEmu.** Y la Ruta B no se descarta del todo: el código filtrado y los dumps de clientes sirven como **referencia de protocolo y datos** para acelerar la Ruta A (comparar opcodes, estructuras, esquemas de BD). El híbrido pragmático: **núcleo AAEmu (1.2) + línea 3.0 basada en el fork de NL0bP + uso de files/dumps como documentación de referencia**, nunca como código publicado.

**Expectativa honesta**: ningún emulador llega al 100% (AzerothCore lleva 12+ años y sigue con huecos). "Perfecto como el original" hay que redefinirlo como "core loops completos + contenido jugable + economía sana", no "réplica byte a byte".

---

## 5. Multi-versión: la realidad

- **Cada versión cambia**: opcodes de paquetes, cifrado/claves, esquema de BD (SQLite de referencia + MySQL de estado), datos del client (game_pak, compact.sqlite3), Lua del client.
- **El ecosistema ya está fragmentado por versión**: 1.2 (AAEmu develop), 3.0 (fork NL0bP, files AA Classic), 5.0–6.5 (files ArcheRage), 10.8 (dump final). No existe un emulador que sirva dos versiones.
- **Diseño realista**: un **monorepo con líneas por versión** (`branch 1.2`, `branch 3.0`) que compartan: (a) la **API de plugins** (si el contrato de plugins es estable, un plugin funciona en ambas), (b) las **herramientas** (packer, opcode finder, tests), (c) la **capa de datos** cuando sea compatible. El binario del server NO es compartible entre versiones.
- **Soporte de 2 versiones bien > 5 versiones mal.** Recomendación: **1.2 (AAEmu, base estable) + 3.0 (la "edad de oro")**. 3.5+ queda fuera del alcance inicial (es donde "el juego fue a peor" y donde el trabajo de RE es mayor).

---

## 6. Plugins: el modelo AzerothCore y qué construir

### 6.1 El modelo de referencia (AzerothCore, WoW 3.3.5a)

- Núcleo modular: los módulos viven en `modules/`, se clonan como repos independientes, el build los compila contra el núcleo.
- **Script hooks** en el núcleo (`ScriptMgr.h`): puntos de enganche que se ejecutan desde el arranque del mundo. Los módulos se suscriben a hooks; si falta un hook, se añade al núcleo vía PR.
- Catálogo de módulos + skeleton-module + boilerplates para empezar.
- Resultado: miles de módulos comunitarios sin tocar el núcleo.

### 6.2 Qué tiene AAEmu hoy (base)

- Managers con interfaces + DI → el equivalente natural de "script hooks" es un **bus de eventos** + **puntos de hook** en los managers.
- **NLua** ya está como dependencia → scripting Lua posible para contenido (quests, eventos).
- Tests unitarios + CI → un plugin puede traer sus propios tests.
- **No hay** API pública de plugins, loader de módulos, ni catálogo. Eso es lo que hay que construir (y es un proyecto de ingeniería acotado, no de investigación).

### 6.3 Diseño mínimo recomendado

1. **Event bus** tipado en el núcleo (eventos de mundo: `PlayerLoggedIn`, `QuestCompleted`, `ItemCrafted`, `CombatKill`...).
2. **Hook points** en los managers (interfaces de suscripción).
3. **Loader de módulos** (directorio `modules/`, ensamblados .NET cargados al arranque — trivial en .NET con `Assembly.LoadFrom`).
4. **Contrato de plugin versionado** (una interfaz `IAaPlugin` + atributos de metadata) para que un plugin compile contra el SDK sin tocar el núcleo.
5. **SDK de plugins** como paquete NuGet separado (así la comunidad compila plugins sin clonar el server).
6. **Registro/catálogo** + CI de compatibilidad (compilar todos los plugins contra cada release).

Este es el "moat" del proyecto: **el primer emulador de ArcheAge con una economía de plugins comunitaria**, como AzerothCore lo es para WoW.

---

## 7. Contenido custom: decompilar el client y añadir zonas/mobs

### 7.1 Qué contiene el client y qué se puede tocar

| Capa | Formato | Herramientas existentes | Dificultad |
| --- | --- | --- | --- |
| Paquetes de datos | `game_pak` (archivos CryEngine) | AAEmu-Packer, aapatcher | Baja |
| Datos de juego (items, mobs, quests, NPCs) | `compact.sqlite3` (SQLite de referencia) + Lua del client | SQL, Lua | **Baja-media** (es data-driven: añadir un mob = fila en BD + modelo + IA) |
| Mundos/zonas | `worlds/` (main_world, terrain) dentro del pak | **Portar entre versiones: demostrado** (gist 5.0 zones) | Media |
| Modelos/animaciones | `.cgf` / `.chr` / `.caf` (CryEngine 3) | Cryengine-Converter (parcial, chunks v801) | **Alta** (toolchain 3D: exportar desde Blender/3ds Max con exporters CryEngine) |
| Navmesh (rutas IA) | archivos de navegación | ArcheAge-AiExporter | Media |
| Lógica del client | Lua | Internal-Archeage-API (inyección CLR) | Media-alta |

### 7.2 Qué es viable y qué no

- **VIABLE (meses)**: añadir items, mobs, quests, NPCs, doodads nuevos vía BD + datos existentes reutilizados; **portar zonas enteras entre versiones** (copiar `main_world` + texturas/modelos/materials — ya hay un gist que lo hace con la zona 5.0 en un client 1.2.4); balancear economía; eventos custom.
- **DIFÍCIL (años)**: zonas nuevas con assets 100% originales — requiere el **Sandbox Editor de CryEngine 3** (no público), exportadores de modelos maduros (el soporte de ArcheAge en Cryengine-Converter es parcial), y generación de navmesh para IA nueva.
- **Atajo realista**: el "contenido nuevo" que parece del juego se logra **recombinando assets existentes** (modelos, texturas, música, animaciones ya en el client) — igual que hacen los modders de otros CryEngine games. El pipeline de "decompilar el client" = extraer game_pak + convertir + reempaquetar, y eso YA existe.

### 7.3 La decompilación completa del client

- El client es C++ (CryEngine 3) + Lua + datos. "Decompilarlo completo" (a C#/C++ legible) no es el objetivo correcto: no hace falta. Lo que hace falta es **entender la interfaz de datos** (pak, sqlite, Lua) y el **protocolo de red** — y eso está mayormente documentado por la comunidad (disector de Wireshark, OpcodeAndNameFinder, dumps).
- El client **no se redistribuye** (es IP de XLGAMES). El proyecto open source distribuye el server y las herramientas; los jugadores traen su propio client (así lo hace AAEmu: descargas HitL desde MEGA/Drive).

---

## 8. Viabilidad con agentes AI, loops y tests

### 8.1 Lo que ya existe (evidencia dura)

- **NL0bP** (líder de AAEmu) contribuye a **`mrexodia/ida-pro-mcp`**, **`bethington/ghidra-mcp`**, **`miscusi-peek/cheatengine-mcp-bridge`**, **`paperclipai/paperclip`** — o sea, **la persona que más sabe de RE de ArcheAge ya está usando MCP para que LLMs manejen IDA/Ghidra/Cheat Engine**. El "AI-driven reverse engineering" no es especulación: es la práctica actual del ecosistema.
- **AAEmu ya tiene una skill de agente** (`.agents/skills/aaemu-setup`) con inventario de assets, HitL y troubleshooting — diseñada para que un agente (como pi) monte el server end-to-end.
- **CI ya existe** (dotnetcore, CodeQL, Sonar, coveralls) + `AAEmu.UnitTests`.

### 8.2 Dónde encajan los loops de AI (por orden de impacto)

1. **RE del protocolo (el cuello de botella)**: loop de captura de paquetes → descifrado → diff de opcodes entre versiones → generación de estructuras C# → **tests de regresión de paquetes** (replay de capturas contra el server). Herramientas: Wireshark/tshark + ida/ghidra-MCP + OpcodeAndNameFinder. Un agente puede hacer "vibe reversing" con IDA Pro MCP (ya es práctica de mrexodia).
2. **Datos**: parsear `compact.sqlite3`/Lua → generar loaders tipados → tests de integridad (cada item/mob/quest referenciado existe). Los PRs de datos (doodads/npcs fixes) son el grueso del trabajo actual de AAEmu — altamente automatizable.
3. **Tests**: suite por capas — unit (managers), integración (login → create → enter world), **golden tests de paquetes** (captura de una sesión sana = fixture de regresión), y smoke tests de world (spawn, quest, craft, combat). El repo ya tiene la base.
4. **Plugins**: el CI puede compilar todos los plugins del catálogo contra cada release (matriz de compatibilidad) + tests por plugin.
5. **Onboarding de contribuidores**: skills de agente (como la de AAEmu) para setup, para portar contenido entre versiones, para escribir un plugin.

### 8.3 Estructura de equipo/automatización recomendada

- **Repos**: monorepo del server (líneas 1.2/3.0) + repo del SDK de plugins (NuGet) + catálogo de plugins + repo de herramientas RE.
- **CI/CD**: build + unit + integration por PR; CodeQL/Sonar; publicación de releases compilados (ya lo hace AAEmu).
- **Loops de AI**: un "RE agent" (IDA/Ghidra MCP + capturas), un "data agent" (BD/Lua), un "content agent" (pak/zonas), un "plugin reviewer" (blancos, revisa PRs de plugins). Con gauntlet/loop-engineering: cada loop tiene un bar (test que falla si el trabajo está mal).
- **Test-as-bar**: el criterio de "funciona" es siempre una suite reproducible, no "lo probé a mano".

---

## 9. Roadmap recomendado por fases

> Principio rector: **nunca empezar de cero; contribuir a AAEmu primero, forkear después.** Cada fase entrega algo jugable.

### Fase 0 — Inmersión (1–2 meses)

- Montar AAEmu local (Aspire) con la skill `.agents/skills/aaemu-setup` — sirve para aprender y para validar el flujo de agentes.
- Unirse al Discord de AAEmu, leer el wiki (Components, Developer-Notes, FAQ), revisar PRs recientes.
- **Decisión de versión insignia**: 1.2 (AAEmu) vs 3.0 (fork NL0bP). Recomendación: **3.0 como meta, 1.2 como base estable** (el fork 3.0 es más viejo y menos mantenido; portar 1.2→3.0 es un proyecto en sí).

### Fase 1 — Fundaciones (3–6 meses)

- Contribuir fixes/features a AAEmu (ganar contexto y reputación; el equipo actual es pequeño y recibe bien a los contribuidores).
- **Construir la capa de plugins**: event bus + hook points + loader de módulos + SDK NuGet + CI de compatibilidad. (Primer entregable diferenciador.)
- **Reforzar tests**: golden tests de paquetes (replay de capturas), integración login→mundo, smoke de sistemas core.

### Fase 2 — Línea de versión (6–12 meses)

- Elegir Y UNA línea extra (3.0) y consolidar el fork: cifrado, opcodes, datos.
- Pipeline de **portar contenido** entre versiones (gist 5.0 zones como punto de partida) documentado y con tests.
- Anti-cheat básico + economía (labor, impuestos, anti-RMT) como plugins oficiales.

### Fase 3 — Contenido custom y comunidad (12–24 meses)

- Toolchain de contenido: pak editor en CI, conversor de modelos, navmesh, guías de "cómo añadir un mob/zona".
- Catálogo de plugins + sistema de propuestas (PRs revisados con tests obligatorios).
- Eventos comunitarios, fresh start periódicos.

### Fase 4 — Escala (24+ meses)

- Multi-servidor (sharding), web API (AAEmu ya tiene un WebApi WIP), métricas, launcher propio.
- Evaluar soporte de más versiones SOLO si la arquitectura de plugins lo permite sin coste desproporcionado.

---

## 10. Riesgos y advertencias

1. **Legal**: el código del emulador (LGPLv3) es práctica establecida desde 2019, pero: **no publicar nunca código de servidor filtrado ni datos del client**; **no monetizar** (donaciones para costes de hosting son el estándar; el P2W/venta de items es lo que atrae demandas y mata servers); el client no se redistribuye. **ArcheAge Chronicles (Q4 2026) puede reactivar la atención de Kakao/XL** sobre el ecosistema PS.
2. **Tiempo**: "perfecto como el original" en emulación limpia = años de equipo. La Ruta B (files) da versiones completas ya, pero mata el objetivo open source. No hay forma de tener ambas cosas a corto plazo.
3. **Comunidad**: los PS actuales están quemados por RMT/desync/hackers. El proyecto debe ganar la confianza con transparencia (open source + tests públicos) desde el día 1.
4. **Anti-cheat**: un client viejo sin soporte oficial es una batalla eterna; planear detección server-side (heurísticas de velocidad/teleport, economía) antes que client-side.
5. **Scope creep**: multi-versión + contenido custom + plugins + anti-cheat + comunidad = demasiado para un solo equipo. El roadmap por fases existe precisamente para no morir de ambición.

---

## 11. Conclusión

El proyecto es **viable pero no es un sprint: es una maratón de equipo**. La buena noticia es que **no hay que inventar nada desde cero**: el emulador open source (AAEmu, 1.2), el fork 3.0, las herramientas de pak/modelos/navmesh, el disector de protocolo, las skills de agentes y el stack MCP de RE ya existen y están activos en 2026. El hueco real que el proyecto llenaría es:

1. **Una capa de plugins comunitaria** (nadie en ArcheAge la tiene; AzerothCore demostró el modelo en WoW).
2. **Transparencia y tests** (los PS grandes son cajas negras con RMT y desync).
3. **Una línea de versión "edad de oro" (3.0)** mantenida como proyecto abierto, no como secreto de un admin.
4. **Un pipeline de contenido custom** (portar zonas entre versiones ya funciona; assets nuevos es la frontera larga).

La forma de hacerlo con AI: **RE del protocolo con IDA/Ghidra-MCP en loops con golden tests de paquetes**, **agentes de datos para el SQLite/Lua**, **CI que compile y testeé cada plugin propuesto**, y **skills de onboarding** para que cualquiera contribuya. El primer PR que deberías abrir no es código: es **unirse a AAEmu y ayudarles a estabilizar 1.2** — porque cada fix que subas allí es infraestructura para tu proyecto.

---

## Anexo: fuentes clave

- AAEmu repo + wiki (Components, Client, Server, FAQ, Developer-Notes, Aspire Guide): github.com/AAEmu/AAEmu
- AAEmu `.agents/skills/aaemu-setup` (SKILL.md / REFERENCE.md)
- AAEmu releases v0.3.0.20250429 (notas de release)
- NL0bP: Archeage-Server-emulator (3.0.3.0), OpcodeAndNameFinder, archeage-db-cryptor; contribuciones a ida-pro-mcp / ghidra-mcp / cheatengine-mcp-bridge / paperclip
- ZeromusXYZ: AAEmu-Packer, AAEmu-Launcher
- ShannonAAEmu: HackShieldDecrypter, AiExporter
- alxbl/archeage (disector Wireshark), menta2k/Internal-Archeage-API, Markemp/Cryengine-Converter, Ko0z/ArcheCore, Noviern/aagamedump
- Gist "AAEmu Client Update 5.0 Zones" (portar zonas entre versiones)
- MassivelyOP: cierre NA/EU (jun 2024), cierre Corea (mar 2025), AA Classic launch woes, rogue servers booming, ArcheAge Chronicles delays (Q4 2026)
- Foros: ArcheRage NA (glory days 2.9/3.0, 3.5 murdered the game, desync, p2w, speed hackers), AA Classic forum, RaGEZONE (búsqueda de files 3.5+), r/archeage (estado de los PS)
- Mailvaltar blog (experiencia ArcheRage 2024), mein-mmo (PS tras el cierre), MMORPG.com/MMOBomb (entrevistas 3.5/4.0 RNG), Fandom wiki (timeline de updates), age.qq.com (clientes chinos)
- AzerothCore wiki (modular structure, create a module, catalogue)
