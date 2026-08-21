"""List a public MEGA folder tree (names + sizes + direct file links).

MEGA public folder link format:  https://mega.nz/folder/<HANDLE>#<KEY>
Nested:                          .../folder/<HANDLE>#<KEY>/folder/<SUBHANDLE>

Uses the public API (g.api.mega.co.nz) + AES (pycryptodome) to decrypt the
encrypted node metadata — no account needed.

Usage: python mega-ls.py <folder_url> [--sub <subhandle>]
"""
import base64
import json
import sys
import urllib.request

from Crypto.Cipher import AES


def b64url_decode(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def b64url_encode(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def aes_ecb_decrypt(data, key):
    return AES.new(key, AES.MODE_ECB).decrypt(data)


def aes_cbc_decrypt(data, key, iv):
    return AES.new(key, AES.MODE_CBC, iv).decrypt(data)


def api_request(payload):
    req = urllib.request.Request(
        "https://g.api.mega.co.nz/cs?id=0&domain=meganz",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def parse_folder_link(url):
    """Returns (top_handle, share_key_bytes) from a /folder/H#K link."""
    parts = url.split("/folder/")[1].split("/")[0]
    handle, _, key = parts.partition("#")
    return handle, b64url_decode(key) if key else None


def list_tree(handle, share_key):
    """Fetch the folder tree and decrypt names. Returns {handle: node}."""
    resp = api_request([{"a": "f", "c": 1, "r": 1, "ca": 1, "g": 1, "p": handle}])
    nodes = resp[0]["f"] if resp and isinstance(resp[0], dict) else []

    # master key for the shared subtree: aes_ecb_decrypt(share_key, share_key)
    master = aes_ecb_decrypt(share_key, share_key)
    out = {}
    for n in nodes:
        h = n["h"]
        # first key entry is the per-user encrypted key
        k0 = n.get("k", [""])[0]
        node_key = None
        if ":" in k0:
            enc = b64url_decode(k0.split(":", 1)[1])
            node_key = aes_ecb_decrypt(enc, master) if len(enc) == 32 else enc
        name = ""
        if node_key and "a" in n:
            try:
                raw = b64url_decode(n["a"])
                # MEGA: attributes are AES-CBC with key=node_key[0:16], iv=node_key[16:32]
                dec = aes_cbc_decrypt(raw, node_key[:16], node_key[16:32])
                name = json.loads(dec.rstrip(b"\x00").decode("utf-8", "replace")).get("n", "")
            except Exception:
                name = "<encrypted>"
        out[h] = {
            "h": h,
            "p": n.get("p"),
            "name": name,
            "size": n.get("s", 0),
            "type": "folder" if n.get("t") == 1 else "file",
        }
    return out


def render(nodes, root_handle, depth=0, prefix=""):
    lines = []
    for h, n in nodes.items():
        if n["p"] != root_handle:
            continue
        size = f" ({n['size']/1073741824:.2f} GB)" if n["type"] == "file" and n["size"] else ""
        lines.append(f"{prefix}{n['name'] or h}{size}  [{h}]")
        if n["type"] == "folder":
            lines.extend(render(nodes, h, depth + 1, prefix + "  "))
    return lines


if __name__ == "__main__":
    url = sys.argv[1]
    handle, key = parse_folder_link(url)
    if not key:
        print("ERROR: el enlace no tiene clave (#key)")
        sys.exit(1)
    nodes = list_tree(handle, key)
    print(f"Total nodos: {len(nodes)}\n")
    for line in render(nodes, handle):
        print(line)
