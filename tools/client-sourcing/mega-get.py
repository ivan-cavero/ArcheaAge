"""Download a file from a public MEGA file link (no account needed).

MEGA public file link format:  https://mega.nz/file/<HANDLE>#<KEY>

Uses the public API (g.api.mega.co.nz) + AES (pycryptodome) to fetch the
temporary download URL and decrypt the content in streaming chunks.

Usage: python mega-get.py <file_url> <output_path>
"""
import base64
import json
import os
import sys
import urllib.request

from Crypto.Cipher import AES

CHUNK = 1 << 20


def b64url_decode(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def api_request(payload):
    req = urllib.request.Request(
        "https://g.api.mega.co.nz/cs?id=0&domain=meganz",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def parse_file_link(url):
    """Returns (handle, key_a32, key_bytes) from a /file/H#K link."""
    parts = url.split("/file/")[1].split("/")[0]
    handle, _, key = parts.partition("#")
    if not key:
        sys.exit("ERROR: link has no key (#key)")
    import struct

    # MEGA file keys are 8 big-endian u32 words: [0..3] ^ [4..7] -> AES-128 key
    k = struct.unpack(">8I", b64url_decode(key))
    key_bytes = struct.pack(">4I", *(k[i] ^ k[i + 4] for i in range(4)))
    return handle, list(k), key_bytes


def fetch(handle):
    resp = api_request([{"a": "g", "p": handle}])
    d = resp[0]
    if isinstance(d, int):
        sys.exit(f"ERROR: API returned {d} (link invalid or removed)")
    return d["g"], d["s"]


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: python mega-get.py <file_url> <output_path>")
    url, out_path = sys.argv[1:3]
    handle, key_a32, key_bytes = parse_file_link(url)
    dl_url, size = fetch(handle)
    print(f"downloading {size/1048576:.1f} MB ...")

    iv = struct_pack_iv(key_a32)
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    done = 0
    pending = b""
    with urllib.request.urlopen(dl_url, timeout=120) as r, open(out_path, "wb") as f:
        while True:
            chunk = r.read(CHUNK)
            if not chunk:
                break
            # CBC needs 16-byte blocks: keep a tail across reads
            data = pending + chunk
            cut = len(data) - len(data) % 16
            pending = data[cut:]
            f.write(cipher.decrypt(data[:cut]))
            done += len(chunk)
            if done % (16 * CHUNK) < CHUNK:
                print(f"  {done/1048576:.0f}/{size/1048576:.0f} MB", flush=True)
        if pending:
            f.write(cipher.decrypt(pending))

    actual = os.path.getsize(out_path)
    if actual < size:
        os.remove(out_path)
        sys.exit(f"ERROR: short file ({actual} < {size})")
    print(f"OK: {out_path} ({actual} bytes)")


def struct_pack_iv(key_a32):
    import struct

    return struct.pack(">QQ", ((key_a32[4] << 32) | key_a32[5]), 0)


if __name__ == "__main__":
    main()
