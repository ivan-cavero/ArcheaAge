"""List a public MEGA folder tree (names + sizes + handles) — no account needed.

Keys are decrypted level-by-level from the share key (each child key is
encrypted with its parent's node key). Usage: python mega-ls2.py <folder_url>
"""
import json
import re
import sys

import requests

from mega.crypto import a32_to_base64, base64_to_a32, base64_url_decode, decrypt_attr, decrypt_key


def parse_folder_url(url):
    m = re.search(r"mega\.[^/]+/folder/([0-z_\-]+)#([0-z_\-]+)", url)
    if not m:
        m = re.search(r"mega\.[^/]+/#F!([0-z_\-]+)[!#]([0-z_\-]+)", url)
    return (m.group(1), m.group(2)) if m else (None, None)


def get_nodes(root_folder):
    data = [{"a": "f", "c": 1, "ca": 1, "r": 1}]
    r = requests.post(
        "https://g.api.mega.co.nz/cs",
        params={"id": 0, "n": root_folder},
        data=json.dumps(data),
        timeout=30,
    )
    return r.json()[0]["f"]


def main(url):
    root_share, share_key_b64 = parse_folder_url(url)
    if not root_share:
        print("No se pudo parsear la URL")
        return
    nodes = get_nodes(root_share)
    by_handle = {n["h"]: n for n in nodes}

    # encuentra la raíz real: el nodo cuyo padre no está en el conjunto
    handles = set(by_handle)
    top = next((n for n in nodes if n.get("p") not in handles), None)
    if top is None:
        print("Sin raíz"); return

    # la share key de la URL descifra TODOS los nodos del árbol (verificado:
    # AAFree, sus hijos y nietos descifran con la misma clave).
    share_key = base64_to_a32(share_key_b64)
    node_keys = {}
    for n in nodes:
        try:
            nk = decrypt_key(base64_to_a32(n["k"].split(":", 1)[1]), share_key)
            if n["t"] == 0:  # archivo: clave de atributos
                nk = (nk[0] ^ nk[4], nk[1] ^ nk[5], nk[2] ^ nk[6], nk[3] ^ nk[7])
            node_keys[n["h"]] = nk
        except Exception:
            node_keys[n["h"]] = None

    def name_of(n):
        if n["h"] not in node_keys or node_keys[n["h"]] is None or "a" not in n:
            return "(sin nombre)"
        try:
            attrs = decrypt_attr(base64_url_decode(n["a"]), node_keys[n["h"]])
            return attrs.get("n", "(sin nombre)") if isinstance(attrs, dict) else "(sin nombre)"
        except Exception:
            return "(sin nombre)"

    def render(parent, depth):
        out = []
        for n in nodes:
            if n.get("p") != parent:
                continue
            nm = name_of(n)
            size = f"  ({n['s']/1073741824:.2f} GB)" if n.get("t") == 0 and n.get("s") else ""
            out.append(f"{'  '*depth}{nm}{size}   [id={n['h']}]")
            if n.get("t") == 1:
                out.extend(render(n["h"], depth + 1))
        return out

    print(f"Total nodos: {len(nodes)}\n")
    lines = render(top["h"], 0)
    print("\n".join(lines) if lines else "(vacío)")


if __name__ == "__main__":
    main(sys.argv[1])
