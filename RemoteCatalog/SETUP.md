# Crystal v1.9.5 remote catalog setup

The automatic backend uses the current VRCX-compatible provider set:

- AvtrDB v3
- avtr.zip
- VRCDB
- PAW
- NSVR
- VRCWB
- optional VRCNDb

## Configure the world once

Catalog URL:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog.txt`

Full Search Shards:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog-shards/`

In Unity:

`Crystal GUIs -> Configure Remote Catalog`

Enable:

- Prefer remote
- Load when world starts
- Full remote sharded search

Then apply it to the open Avatar Browser and upload the world.

## Automatic updates

GitHub Actions runs every 2 hours.

The updater processes 24 discovery prefixes each run and stores its resume point in:

`docs/catalog-state.json`

If providers are rate-limited or fail repeatedly, they are isolated for that run. If every provider fails for a prefix, that prefix is kept for the next run instead of being skipped.

## Search

Crystal v1.9.2 searches remote name/creator shards from:

`docs/catalog-shards/`

The SEARCH ALL button and VRChat keyboard Done/Enter both go through the same delayed Udon search event so TMP input has time to commit the typed text.


## Local Unity crawler

In Unity open:

`Crystal GUIs -> Build / Update Broad Catalog`

Leave:

`Run continuously until complete`

enabled if you want one click to continue from the current saved seed through the whole seed list.

Use:

`STOP AFTER CURRENT SEED`

to stop safely without losing the resume position.
