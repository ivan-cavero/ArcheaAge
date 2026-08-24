# apps/landing — Arcadia (landing web)

Landing bilingüe (ES/EN) del proyecto **Arcadia**, la plataforma ArcheAge
open source del monorepo. Construida con **Astro 6** (estático, cero JS por
defecto) y el mismo lenguaje visual que el launcher
(`apps/launcher/src/styles/base.css`).

## Quick start

```bash
cd apps/landing
bun install        # o npm install
bun run dev        # http://localhost:4321
bun run build      # salida estática en dist/
bun run preview    # sirve dist/ localmente
```

## Rutas

| Ruta  | Idioma                 |
|-------|------------------------|
| `/`   | Español (por defecto)  |
| `/en/`| English                |

## Estructura

```text
apps/landing
├── Dockerfile          # build multi-etapa con Bun 1.4 + sirve con Bun
├── serve.ts            # servidor estático mínimo para producción (Bun)
├── astro.config.mjs    # site URL, sitemap, output estático
├── package.json        # astro ^6.x
├── .dockerignore       # contexto de build limpio
├── public/
│   ├── images/         # assets compartidos con el launcher
│   └── favicon.svg
└── src/
    ├── i18n/
    │   ├── es.ts       # diccionario español (referencia de tipos)
    │   └── en.ts       # traducción inglés (misma forma, tipada)
    ├── layouts/BaseLayout.astro
    ├── components/     # Nav, Hero, Stats, Servers, Features, World,
    │                    #   Compare, Portal, Benchmarks, Roadmap, CTA, Footer
    ├── styles/global.css
    └── pages/
        ├── index.astro    # ES
        └── en/index.astro # EN
```

## Cómo editar contenido

Todo el texto vive en `src/i18n/es.ts` (y su traducción `en.ts`). Cambia una
frase ahí y recompila. El `type Dict` derivado de `es` garantiza que `en`
mantiene la misma forma (el checker falla si difieren).

## Integraciones futuras

- **Widget de estado en vivo**: conectar el hero al Registry
  (`GET /versions/{v}/servers`) a través de un Server Island / Live Content
  Collection de Astro, manteniendo el resto de la página estática.
- **Portal web** (perfiles, leaderboards, equipamiento): rutas dinámicas
  bajo `/portal/` cuando el Registry lo exponga.

## Deploy (Docker / Dokploy)

Despliegue listo para **Dokploy sin nginx**: la imagen final es solo Bun,
que sirve el sitio estático.

- `Dockerfile` — build multi-etapa con **Bun 1.4** (`oven/bun:1.4-alpine`):
  instala dependencias con lockfile, buildea el sitio y sirve `dist/` con el
  propio Bun (`serve.ts`) como usuario no-root.
- `serve.ts` — servidor estático mínimo de Bun: `Content-Type` correcto,
  cache inmutable de `/_astro/`, cache 30 días de imágenes, fallback SPA y
  security headers; previene path traversal; puerto desde `PORT` (8080).
- `.dockerignore` — contexto de build limpio (excluye `node_modules`,
  `dist`, `.astro`, `.git`).

### Despliegue en Dokploy

1. Crea una nueva **Application** en Dokploy apuntando a este repo
   (subcarpeta `apps/landing`).
2. En el build, usa el **Dockerfile** (Dokploy lo detecta y lo ejecuta; el
   contenedor expone el puerto 8080).
3. En **Domains**, añade tu **dominio custom** — Dokploy genera el
   certificado HTTPS automáticamente y enruta al puerto 8080 del contenedor.
4. Opcional: variables de entorno (`PORT`, `TZ`).

### Local (sin compose)

```bash
cd apps/landing
podman build -t arcadia-landing .      # o docker build -t arcadia-landing .
podman run -p 8080:8080 arcadia-landing
curl -I http://localhost:8080/         # 200 OK + cabeceras de caché/seguridad
```

> Nota: en el build con Bun/Alpine, `sharp` (optimización de imágenes de
> Astro) se instala desde sus binarios musl; si algún host diera problemas,
> cambia la base del build a `oven/bun:1.4` (glibc) y recompila.

## Nota legal

No se distribuyen activos del juego: las imágenes de `public/` son branding
propio del monorepo. Ver el disclaimer del README raíz.