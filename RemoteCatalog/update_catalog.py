#!/usr/bin/env python3
"""
Crystal Avatar Catalog updater v1.9

Primary source:
  Prismic's current public PAS database files:
    pasavtrdb.txt      (main/PC metadata)
    pasavtrdb_qst.txt  (Quest/Android compatibility)
    pasavtrdb_ios.txt  (iOS compatibility)

Supplementary sources are optional:
  AvtrDB v3 / VRCX provider format
  Avtr.icu
  VRCNDb (authorized key only)

Outputs:
  docs/catalog.txt                small "hot" fallback catalog
  docs/catalog-shards/a.txt ...   full Prismic search shards
  docs/catalog-shards/index.txt   shard metadata
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import struct
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "catalog.txt"
STATE = DOCS / "catalog-state.json"
SHARDS = DOCS / "catalog-shards"

UA = "CrystalVRChatCatalogUpdater/1.9.0"
HOT_ROWS = int(os.getenv("CRYSTAL_HOT_ROWS", "12000"))
USE_PRISMIC = os.getenv("CRYSTAL_ENABLE_PRISMIC", "1") != "0"
USE_AVTRDB = os.getenv("CRYSTAL_ENABLE_AVTRDB", "0") != "0"
USE_ICU = os.getenv("CRYSTAL_ENABLE_AVTRICU", "0") != "0"
VRCN_KEY = os.getenv("CRYSTAL_VRCNDB_KEY", "").strip()

PRISMIC_PRIMARY = [
    "https://gist.githubusercontent.com/Mwr247/a80c1f9060fc4fd46a8f00d589c47c5a/raw/pasavtrdb.txt",
    "https://gist.githubusercontent.com/Mwr247/a80c1f9060fc4fd46a8f00d589c47c5a/raw/pasavtrdb_qst.txt",
    "https://gist.githubusercontent.com/Mwr247/a80c1f9060fc4fd46a8f00d589c47c5a/raw/pasavtrdb_ios.txt",
]
PRISMIC_BACKUP = [
    "https://prismic.net/vrc/pasavtrdb.txt",
    "https://prismic.net/vrc/pasavtrdb_qst.txt",
    "https://prismic.net/vrc/pasavtrdb_ios.txt",
]

STATIC_BYTES = bytes([
    208, 29, 107, 36, 251, 69, 122, 14,
    67, 204, 171, 246, 106, 38, 183, 224
])

AVTR_ID = re.compile(r"^avtr_[0-9a-fA-F-]{36}$")
SHARD_KEYS = list("abcdefghijklmnopqrstuvwxyz0123456789") + ["_"]


def clean(value):
    return (
        str(value or "")
        .replace("|", " ")
        .replace("\n", " ")
        .replace("\r", " ")
        .strip()
    )


def request_bytes(url, timeout=90):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "*/*"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def request_json(url, headers=None, timeout=30):
    req = urllib.request.Request(
        url,
        headers=headers or {"User-Agent": UA, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def download_with_fallback(index):
    errors = []
    for url in (PRISMIC_PRIMARY[index], PRISMIC_BACKUP[index]):
        try:
            print("Downloading", url)
            return request_bytes(url)
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("Prismic download failed: " + " | ".join(errors))


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def remaining(self):
        return len(self.data) - self.pos

    def read(self, count):
        end = self.pos + count
        if end > len(self.data):
            raise ValueError("read beyond end of PAS data")
        out = self.data[self.pos:end]
        self.pos = end
        return out

    def byte(self):
        return self.read(1)[0]

    def int24(self):
        b = self.read(3)
        return (b[0] << 16) | (b[1] << 8) | b[2]

    def int32_array(self, count):
        raw = self.read(count * 4)
        return struct.unpack("<" + ("i" * count), raw)


def decode_avatar_id(block, iv):
    crypt = bytearray(block)

    for i in range(len(crypt) - 1, -1, -1):
        prev = len(crypt) - 1 if i == 0 else i - 1
        crypt[i] = crypt[i] ^ crypt[prev] ^ iv[i]

    for i, value in enumerate(crypt):
        crypt[i] = ((value >> 4) | ((value << 4) & 0xFF)) & 0xFF

    hex_string = "".join(f"{b:02x}" for b in reversed(crypt))

    return (
        "avtr_"
        + hex_string[0:8] + "-"
        + hex_string[8:12] + "-"
        + hex_string[12:16] + "-"
        + hex_string[16:20] + "-"
        + hex_string[20:32]
    )


def dynamic_key(random_bytes):
    return bytes(a ^ b for a, b in zip(random_bytes, STATIC_BYTES))


def parse_aux_database(data):
    r = Reader(data)

    if r.read(3) != b"PAS":
        raise ValueError("PAS header not found")

    r.read(2 + 3 + 3 + 2)
    file_avatars = r.int24()
    r.read(3 + 1)

    key = dynamic_key(r.read(16))
    avatar_ids = r.read(file_avatars * 16)

    ids = set()

    for i in range(file_avatars):
        ids.add(decode_avatar_id(
            avatar_ids[i * 16:(i + 1) * 16],
            key
        ))

    return ids


def parse_main_database(data, quest_ids, ios_ids):
    r = Reader(data)

    if r.read(3) != b"PAS":
        raise ValueError("PAS header not found")

    r.read(2)
    avatar_count = r.int24()
    author_count = r.int24()

    date_arr = r.read(2)
    date_num = (((date_arr[0] << 8) + date_arr[1]) >> 3)
    year = (date_num >> 9) + 16
    month = (date_num >> 5) & 15
    day = date_num & 31
    last_update = f"20{year:02d}-{month:02d}-{day:02d}"

    file_avatars = r.int24()
    r.int24()
    r.byte()

    key = dynamic_key(r.read(16))
    avatar_id_bytes = r.read(file_avatars * 16)

    r.int32_array(file_avatars)
    author_ids = r.int32_array(file_avatars)

    strings = r.read(r.remaining()).decode("utf-8", "replace")
    parts = strings.split("\n", 1)

    if len(parts) < 2:
        raise ValueError("Malformed Prismic string block")

    author_names = [s[::-1] for s in parts[0].split("\r")]
    avatar_lines = parts[1].split("\r")

    if len(avatar_lines) < file_avatars:
        raise ValueError("Prismic avatar list shorter than expected")

    def iterator():
        for i in range(file_avatars):
            avatar_id = decode_avatar_id(
                avatar_id_bytes[i * 16:(i + 1) * 16],
                key,
            )

            fields = avatar_lines[i].split("\t")
            name = fields[0][::-1] if fields else ""

            author_index = author_ids[i] & 524287
            author = (
                author_names[author_index]
                if author_index < len(author_names)
                else "Unknown"
            )

            android = avatar_id in quest_ids
            ios = avatar_id in ios_ids

            if android and ios:
                platform = "PC+Android+iOS"
            elif android:
                platform = "PC+Android"
            elif ios:
                platform = "PC+iOS"
            else:
                platform = "PC"

            yield {
                "id": avatar_id,
                "name": name,
                "creator": author,
                "creator_id": "",
                "source": "Prismic",
                "platform": platform,
            }

    return {
        "avatar_count": avatar_count,
        "author_count": author_count,
        "file_avatars": file_avatars,
        "last_update": last_update,
        "entries": iterator(),
    }


def shard_key(value):
    value = clean(value).lower()
    for ch in value:
        if "a" <= ch <= "z" or "0" <= ch <= "9":
            return ch
    return "_"


def row_line(row):
    return "|".join([
        clean(row.get("name")),
        clean(row.get("creator")),
        clean(row.get("creator_id")),
        clean(row.get("id")),
        clean(row.get("source")),
        clean(row.get("platform") or "Unknown"),
    ])


def save_hot(rows):
    DOCS.mkdir(parents=True, exist_ok=True)

    unique = {}
    for row in rows:
        aid = clean(row.get("id"))
        if AVTR_ID.match(aid):
            unique[aid] = row

    ordered = sorted(
        unique.values(),
        key=lambda r: (
            clean(r.get("name")).casefold(),
            clean(r.get("id")),
        ),
    )

    lines = [
        "# Crystal remote avatar hot catalog",
        "# Avatar Name|Creator Name|Creator ID|Avatar ID|Source|Platform",
    ]
    lines.extend(row_line(row) for row in ordered)

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def rebuild_prismic():
    main = download_with_fallback(0)
    quest = download_with_fallback(1)
    ios = download_with_fallback(2)

    print("Parsing Quest/Android IDs...")
    quest_ids = parse_aux_database(quest)

    print("Parsing iOS IDs...")
    ios_ids = parse_aux_database(ios)

    print("Parsing main Prismic database...")
    parsed = parse_main_database(main, quest_ids, ios_ids)

    temp = DOCS / "catalog-shards.tmp"

    if temp.exists():
        shutil.rmtree(temp)

    temp.mkdir(parents=True, exist_ok=True)

    handles = {}

    def handle_for(key):
        if key not in handles:
            p = temp / f"{key}.txt"
            fh = p.open("w", encoding="utf-8", newline="\n")
            fh.write("# Crystal full avatar search shard\n")
            fh.write("# Avatar Name|Creator Name|Creator ID|Avatar ID|Source|Platform\n")
            handles[key] = fh
        return handles[key]

    hot = []
    total = parsed["file_avatars"]
    stride = max(1, total // max(1, HOT_ROWS))
    written = 0

    for index, row in enumerate(parsed["entries"]):
        aid = clean(row["id"])

        if not AVTR_ID.match(aid) or not clean(row["name"]):
            continue

        keys = {
            shard_key(row["name"]),
            shard_key(row["creator"]),
        }

        line = row_line(row) + "\n"

        for key in keys:
            handle_for(key).write(line)

        if len(hot) < HOT_ROWS and index % stride == 0:
            hot.append(row)

        written += 1

        if written % 100000 == 0:
            print("Prismic rows processed:", written)

    for fh in handles.values():
        fh.close()

    for key in SHARD_KEYS:
        p = temp / f"{key}.txt"
        if not p.exists():
            p.write_text(
                "# Crystal full avatar search shard\n"
                "# Avatar Name|Creator Name|Creator ID|Avatar ID|Source|Platform\n",
                encoding="utf-8",
            )

    (temp / "index.txt").write_text(
        "\n".join([
            "# Crystal search shard index",
            "source=Prismic",
            f"avatars={written}",
            f"authors={parsed['author_count']}",
            f"prismic_last_update={parsed['last_update']}",
            "keys=" + ",".join(SHARD_KEYS),
            "",
        ]),
        encoding="utf-8",
    )

    if SHARDS.exists():
        shutil.rmtree(SHARDS)

    temp.rename(SHARDS)
    save_hot(hot)

    print("Prismic complete:", written, "avatars; hot catalog:", len(hot))


def avtrdb_v3(seed, limit=500):
    query = urllib.parse.urlencode({"search": seed, "n": limit})
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Referer": "https://vrcx.app",
    }
    crystal_id = os.getenv("CRYSTAL_VRCX_ID", "").strip()
    if crystal_id:
        headers["VRCX-ID"] = crystal_id
    return request_json(
        "https://api.avtrdb.com/v3/avatar/search/vrcx?" + query,
        headers,
    )


def avtricu(seed, limit=100):
    query = urllib.parse.urlencode({
        "search": seed,
        "limit": limit,
        "offset": 0,
    })
    return request_json(
        "https://avtr.icu/search?" + query,
        {
            "User-Agent": UA,
            "Accept": "application/json",
            "Referer": "https://avtr.icu/",
        },
    )


def vrcndb(seed, limit=100):
    if not VRCN_KEY:
        return []

    query = urllib.parse.urlencode({"limit": limit, "page": 1, "q": seed})
    path_query = "/api/search.php?" + query
    url = "https://db.vrcnext.com" + path_query

    ts = str(int(time.time()))
    nonce = secrets.token_hex(8)
    canonical = "\n".join([ts, nonce, "GET", path_query, UA])
    sig = hmac.new(
        VRCN_KEY.encode(),
        canonical.encode(),
        hashlib.sha256,
    ).hexdigest()

    return request_json(
        url,
        {
            "User-Agent": UA,
            "Accept": "application/json",
            "X-VRCN-Ts": ts,
            "X-VRCN-Nonce": nonce,
            "X-VRCN-Sig": sig,
        },
    )


def main():
    DOCS.mkdir(parents=True, exist_ok=True)

    if USE_PRISMIC:
        rebuild_prismic()
    else:
        print("Prismic disabled; existing catalog left unchanged.")

    print(
        "Optional providers:",
        "AvtrDBv3=" + str(USE_AVTRDB),
        "Avtr.icu=" + str(USE_ICU),
        "VRCNDb=" + str(bool(VRCN_KEY)),
    )

    STATE.write_text(
        json.dumps({
            "version": "1.9.0",
            "updated_unix": int(time.time()),
            "prismic": USE_PRISMIC,
            "avtrdb_v3": USE_AVTRDB,
            "avtr_icu": USE_ICU,
            "vrcndb": bool(VRCN_KEY),
        }, indent=2),
        encoding="utf-8",
    )

    print("Catalog update complete.")


if __name__ == "__main__":
    main()
