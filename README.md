# Crystal Remote Avatar Catalog v1.11.0

Automatic remote backend for the Crystal VRChat Avatar Browser.

## Live URLs

Startup catalog:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog.txt`

Creator/fallback shards:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog-shards/`

Direct avatar-name search:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/search2/`

## Current automatic providers

- AvtrDB v3
- avtr.zip
- VRCDB
- PAW
- NSVR
- VRCWB
- optional VRCNDb with an authorized key

## Direct name search

The automatic crawler still walks the two-character discovery space:

`aa -> ab -> ac -> ... -> zz`

but v1.11 writes each completed prefix immediately to:

`docs/search2/<prefix>.txt`

Examples:

- `Shark` -> `search2/sh.txt`
- `Crystal` -> `search2/cr.txt`
- `Juice` -> `search2/ju.txt`

The VRChat world downloads the corresponding remote prefix shard when the player searches an avatar name, then filters that shard using the full text typed.

This means avatar-name search is no longer limited to the small startup catalog already loaded in the world.

## Other outputs

The updater also maintains:

- `docs/catalog-master.txt`
- `docs/catalog.txt`
- `docs/catalog-shards/*.txt`
- `docs/catalog-state.json`

The state file preserves the current discovery prefix. Providers that rate-limit or repeatedly fail are isolated for that run.

## Unity setup

In **Crystal GUIs -> Configure Remote Catalog**, set:

Catalog URL:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog.txt`

Creator/Fallback Shards:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog-shards/`

Avatar Name Search:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/search2/`

Then enable **Prefer remote** and **Load when world starts**.

Crystal v1.11 uses the SEARCH button / VRChat keyboard submit to pull the matching two-character remote avatar-name shard.

## Limits

The system can only return avatars known to at least one configured public metadata provider. It cannot guarantee private, deleted, never-indexed, or otherwise unavailable avatars.
