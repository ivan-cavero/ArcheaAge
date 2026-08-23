# Plan de reorganización — ArcheaAge

> Estado: propuesta (2026-08). Objetivo: que el repo sea gestionable, rápido,
> sin duplicados, y que siente la base para el editor 3D (mapa, modelos, UI,
> elementos del juego) tipo game engine.
>
> Relacionado: [ARQUITECTURA.md](ARQUITECTURA.md) (qué es cada cosa),
> [MODDING.md](MODDING.md) (ingeniería inversa del cliente),
> [ADR](ADR/) (decisiones).

---

## 1. Diagnóstico (verificado en el repo)

### Lo que ya está bien

- `.gitignore` bien pensado: `.client_files/`, `.server_files/`, `.clients/`, `target/` y `node_modules/` fuera de git.
- `docs/` con ADRs, arquitectura, investigación — hay disciplina documental.
- La pipeline de UI modding (`tools/ui`) está documentada y funciona end-to-end (decompile → edit → push → game).
- El estudio (`apps/studio`) ya es una app Tauri funcional con inyección de overrides verificada.

### Problemas concretos

| # | Dolor | Causa raíz | Dónde |
| --- | ------- | ----------- | ------- |
| P1 | **Mismo árbol de scripts en 2 sitios** | `tools/src` y `tools/ui/src` son copias **byte-idénticas** (966 ficheros, 0 diferencias) | `tools/src/` |
| P2 | **Dos editores de UI** | `tools/ui/editor/` (experimento temprano) y `apps/studio/` (el producto actual) conviven | `tools/ui/editor/` |
| P3 | **3 scripts MEGA que hacen lo mismo** | `mega-get.py`, `mega-ls.py`, `mega-ls2.py`: mismo dominio, enfoques distintos | `tools/client-sourcing/` |
| P4 | **3 proyectos C# para pak** | `pak-grep`, `pak-put`, `pak-scan`: 239 líneas totales repartidas en 3 csproj + 3 árboles bin/obj | `tools/pak-*` |
| P5 | **10 GB en `apps/`** | 7.1 GB `launcher/src-tauri/target` + 3 GB `studio/src-tauri/target` (artefactos de build). Ya ignorados por git, pero comen disco local | local |
| P6 | **Rutas hardcodeadas** | `apps/studio/src-tauri/src/lib.rs` resuelve el repo por "profundidad de exe" (4 niveles arriba) | `apps/studio` |
| P7 | **`sync-tree.ps1` existe porque hay 2 árboles** | síntoma de P1: se sincronizan a mano dos copias en vez de tener una canónica | `tools/ui/` |
| P8 | **CI no cubre studio ni tools** | solo .NET + cargo check del launcher | `.github/workflows/ci.yml` |
| P9 | **`clients` locales gigantes** | `.clients/` (~158 GB) y `.client_files/` (cliente extraído) sin documentar cómo regenerarlos | local |
| P10 | **Referencia sin documentar** | `.reference/AAEmu-Launcher` (clon de referencia) sin README que diga qué es | `.reference/` |

### Sobre "portar a CryEngine" (importante, honesto)

El cliente de ArcheAge 1.2 **ya es CryEngine 3** — el juego original se construyó sobre CE3.
"Portar a CryEngine" no aplica: el `.exe` está compilado, no hay código del motor que migrar.
Lo que sí es real y es el camino:

1. **Editar los datos que el cliente ya lee** (game_pak: UI, textos, modelos, mundo) → esto es modding, ya lo hacéis.
2. **Construir un editor propio** que manipule esos datos y los inyecte en el cliente. El editor **no reemplaza el motor** del juego; el juego sigue siendo el cliente.
3. Un cliente desde cero (reimplementar CE3 o usar otro motor) sería reescribir el juego: años de trabajo, no recomendado.

El plan de abajo asume el punto 2 con ambición total (el "sueño completo"): UI → assets → visor de mundo → editor de mundo → elementos de juego.

---

## 2. Estructura objetivo

```text
apps/                  # productos (ejecutables que usa gente)
├── launcher/          # jugador: versión, servidores, descarga, lanza el cliente
├── registry/          # metaserver (C# — CONGELADO, solo fixes; el futuro es servers/go)
└── studio/            # EL editor (hoy UI; crecerá a assets → mundo → juego)

servers/
├── aaemu/             # submódulo AAEmu fork (producción M1-M2)
└── go/                # rewrite por slices (ADR-001)

tools/                 # utilidades de desarrollo — UN solo proyecto por dominio
├── pak/               # CLI único: grep + put + scan (+ librería para el editor)
├── ui/                # pipeline de modding UI: decompile, push, overrides
│   └── src/           # ÚNICA copia canónica de scripts decompilados
├── client-sourcing/   # mega.py (uno) + rearchive
├── branding/          # scripts de branding/textos
└── db/                # dbtext.py

sdk/  plugins/  content/  db/  docs/  scripts/
```

Principio rector: **una copia canónica por cosa**. Si algo necesita dos árboles,
el segundo se *genera* (nunca se commitea ni se sincroniza a mano).

---

## 3. Fase 0 — Quick wins (1-2 días, bajo riesgo)

| Acción | Comando / detalle | Criterio de fin |
| --- | --- | --- |
| Borrar el árbol duplicado | `rm -rf tools/src` (idéntico a `tools/ui/src`) | `git status` limpio; `tools/ui/src` intacto |
| Borrar el editor predecesor | `rm -rf tools/ui/editor` (reemplazado por `apps/studio`) | studio sigue funcionando (background, tree, overrides) |
| Unificar scripts MEGA | Consolidar en `tools/client-sourcing/mega.py` con subcomandos `ls` / `ls2` / `get`; borrar los 3 originales | `python mega.py ls <url>` funciona |
| Gitignore del estudio | Añadir `apps/studio/src-tauri/gen/` a `.gitignore` (target ya cubierto por `apps/*/src-tauri/target/`) | `git check-ignore` lo confirma |
| Liberar 10 GB de disco | `(cd apps/launcher/src-tauri && cargo clean)` y `(cd apps/studio/src-tauri && cargo clean)` | disco liberado; `cargo build` sigue funcionando |
| Documentar `.reference/` | Añadir `docs/ADR/` nota o README en `.reference/` explicando qué es el clon y si se necesita | cualquiera sabe si puede borrarlo |

**Regla para esta fase**: nada que borre rompe un build. Si algo rompe, se revierte en un commit.

---

## 4. Fase 1 — Consolidación (1-2 semanas)

1. **Pak como librería + un CLI** (`tools/pak`)
   - Fusionar `pak-grep` + `pak-put` + `pak-scan` (239 líneas) en un proyecto `tools/pak` con subcomandos.
   - Exponer el lector/escritor de pak como **librería** reutilizable: el editor 3D la necesitará para leer assets.
   - Criterio: `pak scan`, `pak grep`, `pak put` hacen lo de antes; la librería tiene tests de ida y vuelta (put → scan → extraer = original).

2. **Un solo hogar para el editor de UI** — `apps/studio`
   - `tools/ui/` se queda solo con la pipeline (decompile.ps1, push-ui.ps1, overrides, src canónico).
   - Studio consume los datos generados (`tools/ui/decompiled`, `overrides.lua`) — nunca duplica árboles.
   - Quitar rutas hardcodeadas de `lib.rs`: una sola resolución de repo-root (variable de entorno `ARCHEAAGE_ROOT` con fallback documentado) en vez de "4 niveles arriba del exe".
   - Criterio: `git grep` de rutas con profundidad = 0; studio funciona instalado Y en dev.

3. **Política de doble stack (C# / Go)** — documentar en un ADR
   - `apps/registry` (C#): congelado, solo fixes de seguridad. `servers/go/registry`: el desarrollo nuevo.
   - Regla: **no** se añade funcionalidad nueva a C#; si se necesita, se hace en Go.

4. **CI que cubre lo que es código**
   - Añadir job para `apps/studio` (cargo check + build del front, sin Tauri Linux deps si molesta — al menos cargo check).
   - Añadir job para `tools/pak` (dotnet build + tests).
   - Criterio: el CI falla si se rompe studio o pak.

5. **README con el árbol real**
   - Actualizar el bloque `Structure` del README a la estructura objetivo.
   - Criterio: `find . -maxdepth 2` de un nuevo miembro coincide con el README.

---

## 5. Fase 2 — El editor 3D (roadmap "sueño completo")

El editor vive en **`apps/studio`**, que deja de ser "UI Studio" para ser **ArcheaAge Editor**.
Stack: **Tauri (ya existe) + three.js/WebGPU en el webview** — reutiliza el 100% de la
infra actual; no se añade un motor nativo nuevo hasta que three.js demuestre ser el cuello
de botella (solo ocurriría con mundos enormes en edición).

Cada hito tiene **criterio de salida** medible. No se pasa al siguiente sin cerrarlo.

### Hito A — Editor de UI (en curso, cerrarlo primero)

- Consolidar (Fase 1) y pulir: árbol de pantallas, inspector de widgets, preview con texturas reales, overrides → juego.
- **Salida**: editar un widget y verlo en el cliente en < 1 minuto, sin tocar código a mano.

### Hito B — Navegador de assets del juego ("usar elementos del juego")

- Sobre la librería pak (Fase 1): navegador de archivos del game_pak con vista previa:
  - DDS (texturas, iconos de items) — ya hay pipeline DDS en `tools/ui`.
  - Modelos (Granny `.gr2`), animaciones (`.caf`), materiales.
  - Audio, textos (ya hay `find_texts.py`), layouts.
- Búsqueda por nombre/tipo; "arrastrar al editor" empieza aquí.
- **Salida**: abrir `game_pak`, buscar un icono de item o un modelo, verlo, y colocarlo en un canvas del editor.

### Hito C — Visor de mundo 3D

- Extraer datos de mundo del cliente (ver `MODDING.md` — hay que investigar formatos de nivel/terreno; es el punto técnicamente más arriesgado).
- Viewport 3D (three.js) con navegación tipo editor (orbit/pan/zoom), capas, selección.
- Cargar: terreno, agua, objetos estáticos, spawns (los spawns viven en SQL del server — AAEmu).
- **Salida**: cargar un mapa del cliente y navegarlo en el editor a ~30 FPS.

### Hito D — Editor de mundo

- Colocar/mover/rotar/borrar objetos y spawns; editar terreno si el formato lo permite (heightmap).
- Export a dos destinos: **patches al cliente** (content packs) y **SQL del server** (spawns AAEmu).
- **Salida**: colocar un NPC o un objeto en el editor, exportar, y verlo en el juego corriendo.

### Hito E — Elementos de juego (items, NPCs, quests)

- Editor de datos de juego (tablas SQL + definiciones de client): items, NPCs, drops, quests.
- Reutiliza el navegador de assets (iconos, modelos) para vincular datos ↔ assets visuales.
- **Salida**: crear un item nuevo con icono y modelo, dropearlo en el mundo desde el editor, recogerlo en el juego.

### Hito F — Content packs (lo que ya sueña el README)

- El editor exporta "content packs" versionados (deltas sobre el cliente) que el launcher descarga e inyecta.
- **Salida**: editar UI + mundo + items en el editor → publicar un pack → otro jugador lo recibe por el launcher.

**Riesgos honestos de esta fase**:

- El formato de mundo del cliente 1.2 puede exigir RE profunda (semanas) — Hito C es el punto de mayor incertidumbre; por eso va después de B, que construye el músculo de pak/formatos.
- Editar terreno del cliente es el sub-problema más difícil; si el formato no coopera, el editor de terreno se limita a altura/luz o se deja a herramientas de la comunidad.
- Tiempo: A es días; B-C semanas; D-E meses; F meses+. Es un proyecto de motor, se construye por capas.

---

## 6. Normas de casa (a partir de ahora)

1. **Una copia canónica por cosa.** Si necesitas dos árboles, el segundo se genera en build, nunca se commitea. Prohibido `sync-tree` de copias idénticas.
2. **Borrar > mover > documentar.** Si algo no se usa, se borra; si se duda, se documenta y se borra en la siguiente fase.
3. **Todo cambio estructural = ADR.** Estructura de carpetas, stacks, formatos: 5 líneas en `docs/ADR/`.
4. **Nada de C# nuevo en registry** — el futuro es Go (ADR-001).
5. **El editor no duplica herramientas** — usa `tools/` como librería (pak, decompile, DDS), no como copia.
6. **CI cubre todo lo que es código**: studio, pak, registry, launcher, sdk, plugins.
7. **Los datos locales nunca entran en git**: `.clients/`, `.client_files/`, `.server_files/` (ya en `.gitignore`; mantener).
8. **El README siempre describe la realidad** — actualizarlo en el mismo PR que cambia la estructura.

---

## 7. Orden de ejecución sugerido

```text
Fase 0 (días)      → despeja el desorden visible, libera disco, riesgo mínimo
Fase 1 (1-2 sem)   → estructura estable, CI cubre todo, pak como librería
Hito A (días)      → cierra el editor de UI como producto real
Hito B (semanas)   → navegador de assets: el "usar elementos del juego"
Hito C (semanas)   → visor de mundo 3D (máxima incertidumbre técnica)
Hito D-E-F (meses) → editor de mundo → elementos → content packs
```

**Hoy mismo (30 min)**: los quick wins de la Fase 0. Todo lo demás se planifica en fases.
