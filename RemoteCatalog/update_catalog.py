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
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "catalog.txt"
STATE = ROOT / "docs" / "catalog-state.json"

MAX_PAGES = int(os.getenv("CRYSTAL_MAX_PAGES", "3"))
DELAY = float(os.getenv("CRYSTAL_DELAY_SECONDS", "0.8"))
USE_DB = os.getenv("CRYSTAL_ENABLE_AVTRDB", "1") != "0"
USE_ICU = os.getenv("CRYSTAL_ENABLE_AVTRICU", "1") != "0"
VRCN_KEY = os.getenv("CRYSTAL_VRCNDB_KEY", "").strip()
UA = "CrystalVRChatCatalogUpdater/1.8.3"

AVTR_ID = re.compile(r"^avtr_[0-9a-fA-F-]{36}$")

class ProviderRateLimited(Exception):
    pass

class ProviderForbidden(Exception):
    pass

def clean(value):
    return str(value or "").replace("|", " ").replace("\n", " ").replace("\r", " ").strip()

def request_json(url, headers=None, timeout=25):
    headers = headers or {}
    delays = [0, 8, 20]

    for attempt, delay in enumerate(delays):
        if delay:
            time.sleep(delay)

        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))

        except urllib.error.HTTPError as e:
            if e.code == 429:
                if attempt < len(delays) - 1:
                    continue
                raise ProviderRateLimited("HTTP 429 Too Many Requests")

            if e.code == 403:
                raise ProviderForbidden("HTTP 403 Forbidden")

            if 500 <= e.code < 600 and attempt < len(delays) - 1:
                continue

            raise

    raise RuntimeError("request failed after retries")

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


def platform_from_avatar(a):
    values = []

    for key in (
        "platforms",
        "platform",
        "supportedPlatforms",
        "supported_platforms",
        "platformCodes",
        "platform_codes",
    ):
        if key in a and a.get(key) is not None:
            values.append(a.get(key))

    if a.get("hasPc") or a.get("has_pc") or a.get("pc"):
        values.append("pc")
    if a.get("hasAndroid") or a.get("has_android") or a.get("android"):
        values.append("android")
    if a.get("hasIos") or a.get("has_ios") or a.get("ios"):
        values.append("ios")

    for key in ("unityPackages", "unity_packages", "packages", "builds"):
        obj = a.get(key)
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    for k in ("platform", "platforms", "supportedPlatforms"):
                        if item.get(k) is not None:
                            values.append(item.get(k))

    flattened = []

    def add_value(v):
        if isinstance(v, str):
            flattened.extend(re.split(r"[\\s,;+|/]+", v.lower()))
        elif isinstance(v, list):
            for x in v:
                add_value(x)
        elif isinstance(v, dict):
            for k, enabled in v.items():
                if enabled:
                    add_value(k)

    for v in values:
        add_value(v)

    tokens = set(x for x in flattened if x)

    pc = bool(tokens & {
        "w", "pc", "windows", "standalonewindows",
        "standalone_windows", "win"
    })
    android = bool(tokens & {
        "a", "android", "quest", "standaloneandroid",
        "standalone_android"
    })
    ios = bool(tokens & {"i", "ios"})

    if pc and android:
        return "PC+Android"
    if pc:
        return "PC"
    if android:
        return "Android"
    if ios:
        return "iOS"
    return "Unknown"

def merge_platform(a, b):
    vals = {clean(a), clean(b)} - {"", "Unknown"}

    pc = any("PC" in v or "Windows" in v for v in vals)
    android = any("Android" in v or "Quest" in v for v in vals)
    ios = any("iOS" in v for v in vals)

    if pc and android:
        return "PC+Android"
    if pc:
        return "PC"
    if android:
        return "Android"
    if ios:
        return "iOS"
    return "Unknown"

def normalize_avtrdb(a):
    author = a.get("author") or {}
    return {
        "id": a.get("vrc_id") or a.get("id") or "",
        "name": a.get("name") or "",
        "creator": author.get("name") or a.get("authorName") or "",
        "creator_id": author.get("id") or a.get("authorId") or "",
        "source": "AvtrDB",
        "platform": platform_from_avatar(a),
    }

def normalize_icu(a):
    return {
        "id": a.get("id") or "",
        "name": a.get("name") or "",
        "creator": a.get("authorName") or "",
        "creator_id": a.get("authorId") or "",
        "source": "Avtr.icu",
        "platform": platform_from_avatar(a),
    }

def normalize_vrcn(a):
    return {
        "id": a.get("id") or "",
        "name": a.get("name") or "",
        "creator": a.get("author_name") or "",
        "creator_id": a.get("author_id") or "",
        "source": "VRCNDb",
        "platform": platform_from_avatar(a),
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
            "platform": clean(row.get("platform")) or "Unknown",
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
    cur["platform"] = merge_platform(
        cur.get("platform", "Unknown"),
        row.get("platform", "Unknown"),
    )
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
            "platform": p[5] if len(p) >= 6 else "Unknown",
        })
    return rows

def save(rows):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Crystal remote avatar catalog",
        "# Avatar Name|Creator Name|Creator ID|Avatar ID|Source|Platform",
    ]
    ordered = sorted(
        rows.values(),
        key=lambda r: (clean(r.get("name")).casefold(), r.get("id", "")),
    )
    for r in ordered:
        lines.append("|".join([
            clean(r["name"]),
            clean(r["creator"]),
            clean(r["creator_id"]),
            clean(r["id"]),
            clean(r["source"]),
            clean(r.get("platform", "Unknown")),
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

    # Process a rotating batch every scheduled run; provider blocks stop the run cleanly.
    batch = int(os.getenv("CRYSTAL_SEEDS_PER_RUN", "8"))

    print(f"Starting with {len(rows)} avatars; seed {idx+1}/{len(seeds)}")

    blocked_for_run = set()

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

        seed_had_response = False

        for provider_name, func, mapper in providers:
            if provider_name in blocked_for_run:
                continue

            provider_responded = False

            for page in range(MAX_PAGES):
                try:
                    items = func(seed, page)
                    provider_responded = True
                    seed_had_response = True

                except ProviderRateLimited as e:
                    print(provider_name, "rate limited:", e, "- stopping this provider for this run")
                    blocked_for_run.add(provider_name)
                    break

                except ProviderForbidden as e:
                    print(provider_name, "forbidden:", e, "- stopping this provider for this run")
                    blocked_for_run.add(provider_name)
                    break

                except Exception as e:
                    print(provider_name, "failed:", e)
                    break

                if not items:
                    break

                for a in items:
                    merge_row(rows, mapper(a))

                print(provider_name, "page", page + 1, "items", len(items))
                time.sleep(DELAY)

        if seed_had_response:
            idx = (idx + 1) % len(seeds)
        else:
            print("No provider completed this seed; keeping", seed, "for the next run.")

        save(rows)
        save_state(idx, len(seeds))

        if not seed_had_response:
            break

    print("saved", len(rows), "unique avatars to", OUT)

if __name__ == "__main__":
    main()
