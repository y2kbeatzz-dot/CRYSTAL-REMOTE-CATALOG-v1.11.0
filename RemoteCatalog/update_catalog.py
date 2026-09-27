#!/usr/bin/env python3
"""
Crystal Avatar Catalog updater.

Runs outside Unity. Intended for GitHub Actions or a normal PC scheduler.

Environment variables:
  CRYSTAL_MAX_PAGES          pages per seed/provider (default 3)
  CRYSTAL_DELAY_SECONDS      delay between requests (default 0.8)
  CRYSTAL_ENABLE_AVTRICU     1/0 (default 1)
  CRYSTAL_ENABLE_AVTRDB      1/0 (default 1)
  CRYSTAL_VRCNDB_KEY         optional authorized VRCNDb key
"""

import json
import os
import random
import re
import time
import hmac
import hashlib
import secrets
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "catalog.txt"
STATE = ROOT / "docs" / "catalog-state.json"

MAX_PAGES = int(os.getenv("CRYSTAL_MAX_PAGES", "3"))
DELAY = float(os.getenv("CRYSTAL_DELAY_SECONDS", "0.8"))
USE_DB = os.getenv("CRYSTAL_ENABLE_AVTRDB", "1") != "0"
USE_ICU = os.getenv("CRYSTAL_ENABLE_AVTRICU", "1") != "0"
VRCN_KEY = os.getenv("CRYSTAL_VRCNDB_KEY", "").strip()
UA = "CrystalVRChatCatalogUpdater/1.8.0"

AVTR_ID = re.compile(r"^avtr_[0-9a-fA-F-]{36}$")

def clean(value):
    return str(value or "").replace("|", " ").replace("\n", " ").replace("\r", " ").strip()

def request_json(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def avtrdb(seed, page, limit=100):
    q = urllib.parse.urlencode({
        "query": seed,
        "limit": limit,
        "page": page,
    })
    obj = request_json(
        "https://api.avtrdb.com/v2/avatar/search?" + q,
        {"User-Agent": UA, "Accept": "application/json"},
    )
    if isinstance(obj, dict):
        return obj.get("avatars", [])
    return obj if isinstance(obj, list) else []

def avtricu(seed, page, limit=100):
    q = urllib.parse.urlencode({
        "search": seed,
        "limit": limit,
        "offset": page * limit,
    })
    obj = request_json(
        "https://avtr.icu/search?" + q,
        {
            "User-Agent": UA,
            "Accept": "application/json",
            "Referer": "https://avtr.icu/",
        },
    )
    return obj if isinstance(obj, list) else []

def vrcn(seed, page, limit=100):
    if not VRCN_KEY:
        return []
    q = urllib.parse.urlencode({
        "limit": limit,
        "page": page + 1,
        "q": seed,
    })
    path_query = "/api/search.php?" + q
    url = "https://db.vrcnext.com" + path_query

    ts = str(int(time.time()))
    nonce = secrets.token_hex(8)
    canonical = "\n".join([ts, nonce, "GET", path_query, UA])
    sig = hmac.new(
        VRCN_KEY.encode(),
        canonical.encode(),
        hashlib.sha256,
    ).hexdigest()

    obj = request_json(
        url,
        {
            "User-Agent": UA,
            "Accept": "application/json",
            "X-VRCN-Ts": ts,
            "X-VRCN-Nonce": nonce,
            "X-VRCN-Sig": sig,
        },
    )
    if isinstance(obj, dict):
        return obj.get("results", [])
    return []

def normalize_avtrdb(a):
    author = a.get("author") or {}
    return {
        "id": a.get("vrc_id") or a.get("id") or "",
        "name": a.get("name") or "",
        "creator": author.get("name") or a.get("authorName") or "",
        "creator_id": author.get("id") or a.get("authorId") or "",
        "source": "AvtrDB",
    }

def normalize_icu(a):
    return {
        "id": a.get("id") or "",
        "name": a.get("name") or "",
        "creator": a.get("authorName") or "",
        "creator_id": a.get("authorId") or "",
        "source": "Avtr.icu",
    }

def normalize_vrcn(a):
    return {
        "id": a.get("id") or "",
        "name": a.get("name") or "",
        "creator": a.get("author_name") or "",
        "creator_id": a.get("author_id") or "",
        "source": "VRCNDb",
    }

def merge_row(rows, row):
    aid = clean(row.get("id"))
    if not AVTR_ID.match(aid):
        return False
    name = clean(row.get("name"))
    if not name:
        return False

    cur = rows.get(aid)
    if cur is None:
        rows[aid] = {
            "id": aid,
            "name": name,
            "creator": clean(row.get("creator")) or "Unknown Creator",
            "creator_id": clean(row.get("creator_id")),
            "source": clean(row.get("source")),
        }
        return True

    # Metadata belongs to the exact same avatar ID.
    cur["name"] = name or cur["name"]
    creator = clean(row.get("creator"))
    creator_id = clean(row.get("creator_id"))
    if creator:
        cur["creator"] = creator
    if creator_id:
        cur["creator_id"] = creator_id

    source = clean(row.get("source"))
    sources = set(filter(None, cur["source"].split("+")))
    if source:
        sources.add(source)
    cur["source"] = "+".join(sorted(sources))
    return False

def load_rows():
    rows = {}
    if not OUT.exists():
        return rows
    for line in OUT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = line.split("|")
        if len(p) < 5:
            continue
        merge_row(rows, {
            "name": p[0],
            "creator": p[1],
            "creator_id": p[2],
            "id": p[3],
            "source": p[4],
        })
    return rows

def save(rows):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Crystal remote avatar catalog",
        "# Avatar Name|Creator Name|Creator ID|Avatar ID|Source",
    ]
    for aid in sorted(rows):
        r = rows[aid]
        lines.append("|".join([
            clean(r["name"]),
            clean(r["creator"]),
            clean(r["creator_id"]),
            clean(r["id"]),
            clean(r["source"]),
        ]))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

def build_seeds():
    # broad but finite; repeated scheduled runs rotate through them.
    seeds = [a+b for a in "abcdefghijklmnopqrstuvwxyz" for b in "abcdefghijklmnopqrstuvwxyz"]
    seeds += [f"{n:02d}" for n in range(100)]
    seeds += ["vr", "vrc", "avatar", "booth", "quest", "pc"]
    return seeds

def load_state(total):
    if STATE.exists():
        try:
            s = json.loads(STATE.read_text(encoding="utf-8"))
            if s.get("total") == total:
                return int(s.get("index", 0)) % total
        except Exception:
            pass
    return 0

def save_state(index, total):
    STATE.write_text(
        json.dumps({"index": index, "total": total}, indent=2),
        encoding="utf-8",
    )

def main():
    rows = load_rows()
    seeds = build_seeds()
    idx = load_state(len(seeds))

    # Do a small rotating batch every scheduled run.
    batch = int(os.getenv("CRYSTAL_SEEDS_PER_RUN", "8"))

    print(f"Starting with {len(rows)} avatars; seed {idx+1}/{len(seeds)}")

    for _ in range(batch):
        seed = seeds[idx]
        print("seed", seed)

        providers = []
        if USE_DB:
            providers.append(("AvtrDB", avtrdb, normalize_avtrdb))
        if USE_ICU:
            providers.append(("Avtr.icu", avtricu, normalize_icu))
        if VRCN_KEY:
            providers.append(("VRCNDb", vrcn, normalize_vrcn))

        for provider_name, func, mapper in providers:
            for page in range(MAX_PAGES):
                try:
                    items = func(seed, page)
                except Exception as e:
                    print(provider_name, "failed:", e)
                    break

                if not items:
                    break

                for a in items:
                    merge_row(rows, mapper(a))

                print(provider_name, "page", page + 1, "items", len(items))
                time.sleep(DELAY)

        idx = (idx + 1) % len(seeds)
        save(rows)
        save_state(idx, len(seeds))

    print("saved", len(rows), "unique avatars to", OUT)

if __name__ == "__main__":
    main()
