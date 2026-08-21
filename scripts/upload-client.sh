#!/usr/bin/env bash
# ArcheaAge — sube un cliente a S3/HTTP y genera su manifest.
#
# Uso:
#   bash scripts/upload-client.sh <version> <carpeta-cliente> <login-type> [--bucket s3://mi-bucket/archeaage]
#
# Ejemplo:
#   bash scripts/upload-client.sh 1.2 "F:/descargas/Trion_1.2_client" trino_1_2 \
#       --bucket s3://mi-bucket/archeaage
#
# Qué hace:
#   1. Sube la carpeta del cliente a S3 (aws s3 sync; o usa --http-base para un
#      servidor HTTP cualquiera).
#   2. Calcula SHA256 de cada archivo y genera content/manifests/<version>.json
#      con URLs https:// (el launcher ya descarga vía https con resume).
#   3. Imprime el bloque JSON para añadir la versión a apps/registry/appsettings.json.
#
# Requisitos: aws cli configurado (o valores --bucket/--http-base), python3.
set -euo pipefail

VERSION="${1:?uso: upload-client.sh <version> <carpeta> <login-type> [--bucket ...] [--http-base ...]}"
CLIENT_DIR="${2:?carpeta del cliente requerida}"
LOGIN_TYPE="${3:?login-type requerido (trino_1_2|trino_3_5|trino_6_0|trino_7_0|kakao_8_0|mailru_1_0|xlworld_1_0)}"
shift 3
BUCKET="s3://archeaage-dist/archeaage"
HTTP_BASE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --bucket) BUCKET="$2"; shift 2 ;;
    --http-base) HTTP_BASE="$2"; shift 2 ;;
    *) echo "opción desconocida: $1"; exit 1 ;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/content/manifests/$VERSION.json"
[ -d "$CLIENT_DIR" ] || { echo "ERROR: no existe $CLIENT_DIR"; exit 1; }

echo "[upload] version=$VERSION login=$LOGIN_TYPE"
echo "[upload] subiendo a $BUCKET/$VERSION/ …"
aws s3 sync "$CLIENT_DIR" "$BUCKET/$VERSION/" --no-progress || {
  echo "ERROR: aws s3 sync falló (¿aws cli configurado?)."
  echo "Sugerencia: exporta AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION"
  exit 1
}

echo "[upload] generando manifest…"
python - "$VERSION" "$LOGIN_TYPE" "$CLIENT_DIR" "$HTTP_BASE" "$BUCKET" "$MANIFEST" <<'PY'
import hashlib, json, os, sys

version, login_type, client_dir, http_base, bucket, manifest_path = sys.argv[1:7]

files = []
for root, _dirs, names in os.walk(client_dir):
    for n in sorted(names):
        p = os.path.join(root, n)
        rel = os.path.relpath(p, client_dir).replace("\\", "/")
        size = os.path.getsize(p)
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if http_base:
            url = f"{http_base.rstrip('/')}/{version}/{rel}"
        else:
            url = f"https://{bucket.removeprefix('s3://').rstrip('/')}/{version}/{rel}"
        files.append({
            "name": rel,
            "kind": "direct",
            "url": url,
            "size": size,
            "sha256": h.hexdigest(),
        })

# detección de lo que verificar (ajústalo por versión si difiere)
verify = []
for probe in ["game_pak", "bin32/archeage.exe", "bin64/archeage.exe", "launch_game.exe", "compact.sqlite3"]:
    p = os.path.join(client_dir, probe)
    if os.path.exists(p) and os.path.isfile(p):
        verify.append({"path": probe, "minSize": os.path.getsize(p)})

manifest = {
    "version": version,
    "client": f"custom {version}",
    "files": files,
    "extract": {"archive": "", "tool": "7z"},
    "verify": verify,
    "login": {"protocol": login_type},
    "patches": [],
    "contentPacks": [],
}
os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)
print(f"[upload] manifest escrito: content/manifests/{version}.json")
print(f"[upload] {len(files)} archivos · {sum(fs['size'] for fs in files)/1073741824:.2f} GB")
print()
print("Añade al apps/registry/appsettings.json (Tokens + Versions):")
print(json.dumps({"Tokens": {version: "dev-secret"},
                  "Versions": [{"Id": version, "Name": f"ArcheAge {version}"}]}, indent=2))
PY