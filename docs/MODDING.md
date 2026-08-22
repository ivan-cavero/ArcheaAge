# Modding del cliente ArcheAge 1.2 — estado y plan

> Todo lo aprendido en la primera sesión real de ingeniería inversa del cliente.
> Objetivo final: **cualquier versión extraíble/editable al 100%** — idiomas,
> textos, UI, assets — con organización multiversión y, a futuro, editor de mundo.

## 1. Formato del game_pak (AAPack)

- FAT + cabecera cifrados con **AES-128-CBC, XLGamesKey**
  `32 1F 2A EE AA 58 4A B4 9A 6C 9E 09 D5 9E 9C 6F` (está en el propio código).
- Entradas: `AAPakFileInfo { name(260), offset, size, sizeDuplicate, paddingSize,
  md5, dummy1(flags?), createTime, modifyTime }`.
- `ExportFileAsStream` = **crudo**: NO descomprime NI descifra.
  - Ficheros de texto (lua/xml/cfg/alb...) se extraen tal cual ✓
  - Algunas entradas van **cifradas** (p.ej. `game/db/compact.sqlite3` sale como
    bytes aleatorios). AES-CBC con XLGamesKey + IV key16/zeros **no** descifra →
    o va comprimido antes, o usa IV derivado, o el repack BROC re-claveó el pak
    (`SetCustomKey` existe justo para eso).
- **Siguiente paso concreto**: comparar `dummy1` entre una entrada conocida-en-claro
  (client.cfg) y la cifrada (compact.sqlite3). Si difiere → es el flag de cifrado →
  aplicar `EncryptStreamAESWithIV` en export/import.

## 2. Herramientas construidas (tools/)

| Tool | Qué hace |
|---|---|
| `pak-scan` | listar/extraer entradas (FAT descifrada OK: 218.066 entradas) |
| `pak-put` | reemplazar/añadir fichero dentro del pak + verificación MD5. Requiere cliente cerrado (pak bloqueado en juego) |
| `client-sync` | extraer todo lo editable (7.652 ficheros, 453 MB) a un árbol git-friendly |
| `mega-get.py` | descargar ficheros públicos de MEGA (API v1; formato nuevo sin URL directa pendiente) |

Flujo completo: `client-sync extract → editar (git diff visible) → pak-put / overlay → Play`.

## 3. Mecanismos de modificación (por preferencia)

1. **Overlay suelto** 🧪 *en prueba*: si el cliente prefiere ficheros sueltos de
   `game\` sobre los del pak, los content packs son "soltar carpetas" — cero
   riesgo de corrupción. Test actual: `game\config\client.cfg` con FOV modificado.
2. **pak-put** ✅ herramienta lista (falta validar escritura con juego cerrado).
   Riesgo: escritura in-place sobre 23 GB → conservar SIEMPRE el zip original
   como restauración.
3. **RE del cifrado por entrada** 🔍 para las que lo lleven (db del cliente).

## 4. Hallazgos del cliente BROC (r208022)

- Stub `archeage.exe`: carga `x2game.dll` (o `-dev` si existe `%s/devmode.cfg`),
  escribe layout base en `C:\ArcheAge\{Documents,Working,manifest}` y tiene
  rutas absolutas cocidas → resuelto con **junction `C:\AAEMU`** (el launcher
  ahora la crea automáticamente vía manifest `requiresPath`).
- `-lang en_us` **obligatorio**: sin él cae al locale kr y salta el popup
  *"Failed to load commands!"* (crysystem.dll) durante la init del login UI.
- Con ticket de auth válido (memoria compartida `archeage_auth_ticket_map`,
  RC4+XML, handles en `-handle`) el cliente **se salta su login roto** →
  implementado en nuestro launcher (`auth_ticket.rs`).
- Crash actual: **char-select** (tras seleccionar server, muere antes de pedir
  la lista de personajes; el mismo flujo funciona vía AAEmu-Launcher oficial).
  Traza ProcMon capturada, análisis pendiente de exportación CSV.

## 5. Textos / traducción

- Los textos del juego viven en el sqlite del CLIENTE:
  `game/db/compact.sqlite3` (dentro del pak, cifrado — ver §1).
- El SERVIDOR ya usa un compact.sqlite3 en claro (r208088) con el mismo esquema:
  fuente perfecta para traducir y entregar al cliente como overlay/pak-put.
- Pendiente: confirmar que el cliente acepta la BD en claro en esa ruta.

## 6. Organización multiversión

```
.client_files/
├── clients/<ver>/          # instalación jugable (bin32, game_pak...)
│   ├── 1.2/                # hoy
│   └── <futura>/           # 3.0, 6.0...
├── client-src/<ver>/       # fuente extraída + git LOCAL por versión
│   └── 1.2/                # 7.652 ficheros, baseline commit hecho
└── <original .zip/.7z>     # restauración última
```

El launcher ya es multiversión (manifests por versión); cada manifest declara
`requiresPath`, verify entries y patches[] propios.

## 7. Visión editor de mundo

Los NPCs/spawns/items viven SERVER-side (MySQL aaemu_game + templates del
compact). Un "editor dentro del juego" v1 = comandos GM existentes del fork +
UI propia después; el cliente solo necesitaría assets nuevos si añadimos
visuales que no existen ya. El bloqueo real del contenido nuevo masivo sigue
siendo la cadena herramientas-pak (§1-§3).
