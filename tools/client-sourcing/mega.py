"""Unified MEGA public-link CLI — ls and get (no account needed).

Requires: pycryptodome (pip install pycryptodome). Standard library only
otherwise — no requests, no mega package.

Examples:
  python mega.py ls  https://mega.nz/folder/HASH#KEY
  python mega.py get https://mega.nz/file/HASH#KEY   output.bin
"""
import argparse
import base64
import json
import os
import re
import struct
import sys
import urllib.parse
import urllib.request

from Crypto.Cipher import AES

CHUNK = 1 << 20  # 1 MB read buffer


# ── crypto helpers ──────────────────────────────────────────────────────

def b64url_decode(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def aes_ecb_decrypt(data, key):
    return AES.new(key, AES.MODE_ECB).decrypt(data)


def aes_cbc_decrypt(data, key, iv):
    return AES.new(key, AES.MODE_CBC, iv).decrypt(data)


# ── MEGA API transport ──────────────────────────────────────────────────

def _safe_urlopen(url_or_req, timeout=30):
    """Open *url_or_req* only if the resolved scheme is https."""
    raw_url = url_or_req if isinstance(url_or_req, str) else url_or_req.full_url
    if not raw_url.startswith("https://"):
        sys.exit(f"ERROR: refusing non-https URL: {raw_url}")
    return urllib.request.urlopen(url_or_req, timeout=timeout)  # nosec B310


def _api_post(payload, timeout=30):
    req = urllib.request.Request(
        "https://g.api.mega.co.nz/cs?id=0&domain=meganz",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with _safe_urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


# ── link parsers ────────────────────────────────────────────────────────

# Both /folder/<handle>#<key> and /#F!<handle>!<key>
_FOLDER_RE = re.compile(r"mega\.[^/]+/folder/([0-z_\-]+)#([0-z_\-]+)")
_FOLD_RE = re.compile(r"mega\.[^/]+/#F!([0-z_\-]+)[!#]([0-z_\-]+)")
_FILE_RE = re.compile(r"mega\.[^/]+/file/([0-z_\-]+)#([0-z_\-]+)")


def parse_folder_link(url):
    """Parse a MEGA *folder* URL → (handle_b64, share_key_b64).

    Supports both ``/folder/H#K`` and legacy ``/#F!H!K`` formats.
    Either value may be ``None`` when the URL does not match.
    """
    m = _FOLDER_RE.search(url)
    if not m:
        m = _FOLD_RE.search(url)
    return (m.group(1), m.group(2)) if m else (None, None)


def parse_file_link(url):
    """Parse a MEGA *file* URL → (handle, key_a32_list, aes_key_bytes)."""
    m = _FILE_RE.search(url)
    if not m:
        sys.exit("ERROR: could not parse file link — expected /file/<HANDLE>#<KEY>")
    handle, _, key_b64 = m.group(1), None, m.group(2)
    k = struct.unpack(">8I", b64url_decode(key_b64))
    key_bytes = struct.pack(">4I", *(k[i] ^ k[i + 4] for i in range(4)))
    return handle, list(k), key_bytes


# ── ls implementation ──────────────────────────────────────────────────

def _find_root(nodes):
    """Return the real root node (parent not in the set of known handles)."""
    handles = {n["h"] for n in nodes}
    return next((n for n in nodes if n.get("p") not in handles), None)


def _get_folder_nodes(root_handle):
    """Fetch the raw node list for a shared folder."""
    resp = _api_post([{"a": "f", "c": 1, "r": 1, "ca": 1, "g": 1, "p": root_handle}])
    return resp[0]["f"] if resp and isinstance(resp[0], dict) else []


def _decrypt_node_name(raw_node, master_key):
    """Decrypt a single node's name using the *mega-ls.py* master-key approach."""
    k0 = raw_node.get("k", [""])[0]
    if ":" not in k0:
        return None
    enc = b64url_decode(k0.split(":", 1)[1])
    node_key = aes_ecb_decrypt(enc, master_key) if len(enc) == 32 else enc
    if "a" not in raw_node:
        return None
    try:
        dec = aes_cbc_decrypt(
            b64url_decode(raw_node["a"]), node_key[:16], node_key[16:32]
        )
        return json.loads(dec.rstrip(b"\x00").decode("utf-8", "replace")).get("n", "")
    except Exception:
        return None


def _render_tree(node_map, parent, depth=0):
    """Yield indented lines for every child of *parent*."""
    for n in node_map.values():
        if n["p"] != parent:
            continue
        size = (
            f" ({n['size']/1073741824:.2f} GB)"
            if n["type"] == "file" and n["size"]
            else ""
        )
        tag = " [folder]" if n["type"] == "folder" else ""
        yield f"{'  ' * depth}{n['name'] or n['h']}{size}{tag}  [{n['h']}]"
        if n["type"] == "folder":
            yield from _render_tree(node_map, n["h"], depth + 1)


def cmd_ls(args):
    """List a public MEGA folder tree (names + sizes + handles)."""
    url = args.url
    root_handle, share_key_b64 = parse_folder_link(url)
    if not root_handle:
        sys.exit("ERROR: could not parse folder link — expected /folder/<HANDLE>#<KEY>")
    if not share_key_b64:
        sys.exit("ERROR: link has no key (#key)")

    nodes = _get_folder_nodes(root_handle)

    # Master key: the share key XOR'd with itself via ECB (mega-ls.py approach).
    share_key = b64url_decode(share_key_b64)
    master = aes_ecb_decrypt(share_key, share_key)

    # Build a handle → metadata map.
    node_map = {}
    for n in nodes:
        h = n["h"]
        node_map[h] = {
            "h": h,
            "p": n.get("p"),
            "name": _decrypt_node_name(n, master),
            "size": n.get("s", 0),
            "type": "folder" if n.get("t") == 1 else "file",
        }

    # Use the robust root-finding from mega-ls2 (parent not in handle set).
    root = _find_root(nodes)
    if root is None:
        sys.exit("ERROR: no root node found in response")

    root_h = root["h"]
    # Ensure the root itself appears first with its decrypted name.
    root_entry = node_map.get(root_h)
    if root_entry and root_entry["name"] is None:
        root_entry["name"] = _decrypt_node_name(root, master)

    print(f"Total nodes: {len(nodes)}\n")
    for line in _render_tree(node_map, root_h):
        print(line)


# ── get implementation ─────────────────────────────────────────────────

def cmd_get(args):
    """Download a file from a public MEGA file link (no account needed)."""
    url = args.url
    out_path = args.output

    handle, key_a32, key_bytes = parse_file_link(url)

    resp = _api_post([{"a": "g", "p": handle}], timeout=60)
    d = resp[0]
    if isinstance(d, int):
        sys.exit(f"ERROR: API returned {d} (link invalid or removed)")
    dl_url, size = d["g"], d["s"]
    iv = struct.pack(">QQ", ((key_a32[4] << 32) | key_a32[5]), 0)
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)

    print(f"downloading {size / 1048576:.1f} MB ...")

    done = 0
    pending = b""
    with _safe_urlopen(dl_url, timeout=120) as r, open(out_path, "wb") as f:
        while True:
            chunk = r.read(CHUNK)
            if not chunk:
                break
            data = pending + chunk
            cut = len(data) - len(data) % 16
            pending = data[cut:]
            f.write(cipher.decrypt(data[:cut]))
            done += len(chunk)
            if done % (16 * CHUNK) < CHUNK:
                print(f"  {done / 1048576:.0f}/{size / 1048576:.0f} MB", flush=True)
        if pending:
            f.write(cipher.decrypt(pending))

    actual = os.path.getsize(out_path)
    if actual < size:
        os.remove(out_path)
        sys.exit(f"ERROR: short file ({actual} < {size})")
    print(f"OK: {out_path} ({actual} bytes)")


# ── CLI entry point ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Unified MEGA public-link CLI — ls and get (no account needed)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ls = sub.add_parser(
        "ls",
        help="List a public MEGA folder tree (names + sizes + handles).",
    )
    p_ls.add_argument("url", help="MEGA folder URL (https://mega.nz/folder/<H>#<K>)")
    p_ls.set_defaults(func=cmd_ls)

    p_get = sub.add_parser(
        "get",
        help="Download a file from a public MEGA file link.",
    )
    p_get.add_argument("url", help="MEGA file URL (https://mega.nz/file/<H>#<K>)")
    p_get.add_argument("output", help="Local output path")
    p_get.set_defaults(func=cmd_get)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
