#!/usr/bin/env python3
"""
Crystal Avatar Catalog updater v1.9.1

Automatic providers:
  AvtrDB v3
  avtr.zip
  VRCDB
  PAW
  NSVR
  VRCWB

Optional:
  VRCNDb with an authorized key

Outputs:
  docs/catalog-master.txt
  docs/catalog.txt
  docs/catalog-shards/*.txt
  docs/catalog-state.json
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MASTER = DOCS / "catalog-master.txt"
HOT = DOCS / "catalog.txt"
STATE = DOCS / "catalog-state.json"
SHARDS = DOCS / "catalog-shards"

UA = "CrystalVRChatCatalogUpdater/1.9.2"

MAX_ROWS = int(os.getenv("CRYSTAL_MAX_ROWS", "350000"))
SEEDS_PER_RUN = int(os.getenv("CRYSTAL_SEEDS_PER_RUN", "32"))
RESULTS_PER_QUERY = int(os.getenv("CRYSTAL_RESULTS_PER_QUERY", "750"))
DELAY = float(os.getenv("CRYSTAL_DELAY_SECONDS", "0.8"))
HOT_ROWS = int(os.getenv("CRYSTAL_HOT_ROWS", "12000"))

VRCN_KEY = os.getenv("CRYSTAL_VRCNDB_KEY", "").strip()
VRCX_ID = os.getenv("CRYSTAL_VRCX_ID", "").strip()

AVTR_ID = re.compile(r"^avtr_[0-9a-fA-F-]{36}$")
SHARD_KEYS = list("abcdefghijklmnopqrstuvwxyz0123456789") + ["_"]

PROVIDERS = [
    ("AvtrDB", "https://api.avtrdb.com/v3/avatar/search/vrcx"),
    ("avtr.zip", "https://vrcx.avtr.zip"),
    ("VRCDB", "https://vrcx.vrcdb.com/avatars/Avatar/VRCX"),
    ("PAW", "https://paw-api.amelia.fun/vrcx_search"),
    ("NSVR", "https://avtr.nekosunevr.co.uk/vrcx_search"),
    ("VRCWB", "https://avatar.worldbalancer.com/vrcx_search.php"),
]


class ProviderBlocked(Exception):
    pass


def clean(value):
    return (
        str(value or "")
        .replace("|", " ")
        .replace("\n", " ")
        .replace("\r", " ")
        .strip()
    )


def request_json(url, headers=None, timeout=30):
    headers = dict(headers or {})
    headers.setdefault("User-Agent", UA)
    headers.setdefault("Accept", "application/json")
    headers.setdefault("Referer", "https://vrcx.app")

    if VRCX_ID:
        headers.setdefault("VRCX-ID", VRCX_ID)

    delays = (0, 5, 15)

    for attempt, wait in enumerate(delays):
        if wait:
            time.sleep(wait)

        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8", "replace")
                return json.loads(raw)

        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                if attempt < len(delays) - 1:
                    continue
                raise ProviderBlocked("HTTP 429")

            if exc.code == 403:
                raise ProviderBlocked("HTTP 403")

            if 500 <= exc.code < 600 and attempt < len(delays) - 1:
                continue

            raise


def normalize_platform(obj):
    values = []

    for key in (
        "platform",
        "platforms",
        "supportedPlatforms",
        "supported_platforms",
        "platformCodes",
        "platform_codes",
    ):
        if obj.get(key) is not None:
            values.append(obj.get(key))

    for key in ("unityPackages", "unity_packages", "packages", "builds"):
        value = obj.get(key)

        if isinstance(value, list):
            for item in value:
                if not isinstance(item, dict):
                    continue

                for pkey in (
                    "platform",
                    "platforms",
                    "supportedPlatforms",
                    "supported_platforms",
                ):
                    if item.get(pkey) is not None:
                        values.append(item.get(pkey))

    tokens = []

    def unpack(value):
        if isinstance(value, str):
            tokens.extend(
                x for x in re.split(r"[\s,;+|/]+", value.lower())
                if x
            )
        elif isinstance(value, list):
            for item in value:
                unpack(item)
        elif isinstance(value, dict):
            for key, enabled in value.items():
                if enabled:
                    unpack(key)

    for value in values:
        unpack(value)

    t = set(tokens)

    pc = bool(t & {
        "w", "pc", "windows", "standalonewindows",
        "standalone_windows", "win"
    })
    android = bool(t & {
        "a", "android", "quest", "standaloneandroid",
        "standalone_android"
    })
    ios = bool(t & {"i", "ios"})

    if pc and android and ios:
        return "PC+Android+iOS"
    if pc and android:
        return "PC+Android"
    if pc and ios:
        return "PC+iOS"
    if android and ios:
        return "Android+iOS"
    if pc:
        return "PC"
    if android:
        return "Android"
    if ios:
        return "iOS"
    return "Unknown"


def merge_platform(a, b):
    joined = (clean(a) + "+" + clean(b)).lower()

    pc = "pc" in joined or "windows" in joined
    android = "android" in joined or "quest" in joined
    ios = "ios" in joined

    if pc and android and ios:
        return "PC+Android+iOS"
    if pc and android:
        return "PC+Android"
    if pc and ios:
        return "PC+iOS"
    if android and ios:
        return "Android+iOS"
    if pc:
        return "PC"
    if android:
        return "Android"
    if ios:
        return "iOS"
    return "Unknown"


def normalize_result(obj, source):
    if not isinstance(obj, dict):
        return None

    avatar_id = (
        obj.get("id")
        or obj.get("Id")
        or obj.get("avatarId")
        or obj.get("avatar_id")
        or obj.get("vrc_id")
        or ""
    )

    name = (
        obj.get("name")
        or obj.get("Name")
        or obj.get("avatarName")
        or ""
    )

    author_name = (
        obj.get("authorName")
        or obj.get("AuthorName")
        or obj.get("author_name")
        or obj.get("creatorName")
        or ""
    )

    author_id = (
        obj.get("authorId")
        or obj.get("AuthorId")
        or obj.get("author_id")
        or obj.get("creatorId")
        or ""
    )

    image = (
        obj.get("thumbnailImageUrl")
        or obj.get("imageUrl")
        or obj.get("image_url")
        or ""
    )

    avatar_id = clean(avatar_id)
    name = clean(name)

    if not AVTR_ID.match(avatar_id) or not name:
        return None

    return {
        "name": name,
        "creator": clean(author_name) or "Unknown Creator",
        "creator_id": clean(author_id),
        "id": avatar_id,
        "source": source,
        "platform": normalize_platform(obj),
        "image": clean(image),
    }


def row_line(row):
    return "|".join([
        clean(row.get("name")),
        clean(row.get("creator")),
        clean(row.get("creator_id")),
        clean(row.get("id")),
        clean(row.get("source")),
        clean(row.get("platform") or "Unknown"),
        clean(row.get("image")),
    ])


def parse_row(line):
    parts = line.rstrip("\n").split("|")

    if len(parts) < 5:
        return None

    row = {
        "name": parts[0],
        "creator": parts[1],
        "creator_id": parts[2],
        "id": parts[3],
        "source": parts[4],
        "platform": parts[5] if len(parts) > 5 else "Unknown",
        "image": parts[6] if len(parts) > 6 else "",
    }

    if not AVTR_ID.match(clean(row["id"])):
        return None

    return row


def load_master():
    rows = {}

    if MASTER.exists():
        source = MASTER
    elif HOT.exists():
        source = HOT
    else:
        return rows

    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#"):
            continue

        row = parse_row(line)

        if row:
            rows[row["id"]] = row

    return rows


def merge_row(rows, incoming):
    aid = incoming["id"]
    current = rows.get(aid)

    if current is None:
        if len(rows) >= MAX_ROWS:
            return False

        rows[aid] = incoming
        return True

    if incoming.get("name"):
        current["name"] = incoming["name"]

    if incoming.get("creator") and incoming["creator"] != "Unknown Creator":
        current["creator"] = incoming["creator"]

    if incoming.get("creator_id"):
        current["creator_id"] = incoming["creator_id"]

    if incoming.get("image"):
        current["image"] = incoming["image"]

    current["platform"] = merge_platform(
        current.get("platform", "Unknown"),
        incoming.get("platform", "Unknown"),
    )

    sources = set(
        x for x in clean(current.get("source")).split("+")
        if x
    )
    sources.add(incoming["source"])
    current["source"] = "+".join(sorted(sources))

    return False


def query_provider(label, base_url, seed):
    query = urllib.parse.urlencode({
        "search": seed,
        "n": RESULTS_PER_QUERY,
    })

    payload = request_json(base_url + "?" + query)

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("results", "avatars", "data", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]

    return []


def query_vrcndb(seed):
    if not VRCN_KEY:
        return []

    query = urllib.parse.urlencode({
        "limit": min(RESULTS_PER_QUERY, 500),
        "page": 1,
        "q": seed,
    })

    path_query = "/api/search.php?" + query
    url = "https://db.vrcnext.com" + path_query

    ts = str(int(time.time()))
    nonce = secrets.token_hex(8)

    canonical = "\n".join([
        ts,
        nonce,
        "GET",
        path_query,
        UA,
    ])

    sig = hmac.new(
        VRCN_KEY.encode(),
        canonical.encode(),
        hashlib.sha256,
    ).hexdigest()

    payload = request_json(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
            "X-VRCN-Ts": ts,
            "X-VRCN-Nonce": nonce,
            "X-VRCN-Sig": sig,
        },
    )

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        return payload.get("results", [])

    return []


def build_seeds():
    seeds = [
        a + b
        for a in "abcdefghijklmnopqrstuvwxyz"
        for b in "abcdefghijklmnopqrstuvwxyz"
    ]
    seeds += [f"{n:02d}" for n in range(100)]
    seeds += [
        "vr", "vrc", "avatar", "quest", "android",
        "pc", "furry", "anime", "robot", "cat", "fox",
    ]
    return seeds


def load_state(total):
    if not STATE.exists():
        return {"index": 0, "total": total}

    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"index": 0, "total": total}

    if state.get("total") != total:
        return {"index": 0, "total": total}

    return state


def shard_key(value):
    value = clean(value).lower()

    for ch in value:
        if "a" <= ch <= "z" or "0" <= ch <= "9":
            return ch

    return "_"


def write_outputs(rows, state):
    DOCS.mkdir(parents=True, exist_ok=True)

    ordered = sorted(
        rows.values(),
        key=lambda row: (
            clean(row.get("name")).casefold(),
            clean(row.get("id")),
        ),
    )

    master_lines = [
        "# Crystal avatar master catalog",
        "# Avatar Name|Creator Name|Creator ID|Avatar ID|Source|Platform|Image",
    ]
    master_lines.extend(row_line(row) for row in ordered)

    MASTER.write_text(
        "\n".join(master_lines) + "\n",
        encoding="utf-8",
    )

    if len(ordered) <= HOT_ROWS:
        hot = ordered
    else:
        step = len(ordered) / float(HOT_ROWS)
        hot = [
            ordered[min(len(ordered) - 1, int(i * step))]
            for i in range(HOT_ROWS)
        ]

    hot_lines = [
        "# Crystal remote avatar hot catalog",
        "# Avatar Name|Creator Name|Creator ID|Avatar ID|Source|Platform|Image",
    ]
    hot_lines.extend(row_line(row) for row in hot)

    HOT.write_text(
        "\n".join(hot_lines) + "\n",
        encoding="utf-8",
    )

    temp = DOCS / "catalog-shards.tmp"

    if temp.exists():
        shutil.rmtree(temp)

    temp.mkdir(parents=True, exist_ok=True)

    handles = {}

    def fh(key):
        if key not in handles:
            handle = (temp / f"{key}.txt").open(
                "w",
                encoding="utf-8",
                newline="\n",
            )
            handle.write("# Crystal full search shard\n")
            handle.write(
                "# Avatar Name|Creator Name|Creator ID|Avatar ID|Source|Platform|Image\n"
            )
            handles[key] = handle

        return handles[key]

    for row in ordered:
        keys = {
            shard_key(row.get("name")),
            shard_key(row.get("creator")),
        }

        line = row_line(row) + "\n"

        for key in keys:
            fh(key).write(line)

    for handle in handles.values():
        handle.close()

    for key in SHARD_KEYS:
        path = temp / f"{key}.txt"

        if not path.exists():
            path.write_text(
                "# Crystal full search shard\n"
                "# Avatar Name|Creator Name|Creator ID|Avatar ID|Source|Platform|Image\n",
                encoding="utf-8",
            )

    (temp / "index.txt").write_text(
        "\n".join([
            "# Crystal catalog shard index",
            f"rows={len(ordered)}",
            f"seed_index={state['index']}",
            f"seed_total={state['total']}",
            "keys=" + ",".join(SHARD_KEYS),
            "",
        ]),
        encoding="utf-8",
    )

    if SHARDS.exists():
        shutil.rmtree(SHARDS)

    temp.rename(SHARDS)

    STATE.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8",
    )


def main():
    rows = load_master()
    seeds = build_seeds()
    state = load_state(len(seeds))
    index = int(state.get("index", 0)) % len(seeds)

    blocked = set()
    failure_counts = {}
    added = 0
    processed = 0

    print(
        "Starting rows:",
        len(rows),
        "seed:",
        f"{index + 1}/{len(seeds)}",
    )

    for _ in range(SEEDS_PER_RUN):
        seed = seeds[index]
        print("seed", seed)

        any_provider_responded = False

        for label, url in PROVIDERS:
            if label in blocked:
                continue

            try:
                items = query_provider(label, url, seed)
                any_provider_responded = True

            except ProviderBlocked as exc:
                print(label, "blocked for this run:", exc)
                blocked.add(label)
                continue

            except Exception as exc:
                failure_counts[label] = failure_counts.get(label, 0) + 1
                print(
                    label,
                    "failed:",
                    exc,
                    "(failure",
                    failure_counts[label],
                    ")"
                )

                if failure_counts[label] >= 2:
                    print(
                        label,
                        "disabled for the rest of this run after repeated failures."
                    )
                    blocked.add(label)

                continue

            print(label, "items", len(items))

            for item in items:
                row = normalize_result(item, label)

                if row and merge_row(rows, row):
                    added += 1

            time.sleep(DELAY)

        if VRCN_KEY and "VRCNDb" not in blocked:
            try:
                items = query_vrcndb(seed)
                any_provider_responded = True

                for item in items:
                    row = normalize_result(item, "VRCNDb")

                    if row and merge_row(rows, row):
                        added += 1

            except ProviderBlocked as exc:
                print("VRCNDb blocked for this run:", exc)
                blocked.add("VRCNDb")

            except Exception as exc:
                print("VRCNDb failed:", exc)

        if not any_provider_responded:
            print(
                "No provider completed seed",
                seed,
                "- keeping it as the resume point."
            )
            break

        index = (index + 1) % len(seeds)
        processed += 1

        if len(rows) >= MAX_ROWS:
            print("Catalog row cap reached:", MAX_ROWS)
            break

    state = {
        "version": "1.9.2",
        "index": index,
        "total": len(seeds),
        "last_seed": seeds[index - 1] if processed else seeds[index],
        "rows": len(rows),
        "added_this_run": added,
        "processed_this_run": processed,
        "blocked_providers": sorted(blocked),
        "updated_unix": int(time.time()),
    }

    write_outputs(rows, state)

    print(
        "Done. rows=",
        len(rows),
        "added=",
        added,
        "next seed=",
        f"{index + 1}/{len(seeds)}",
    )


if __name__ == "__main__":
    main()
