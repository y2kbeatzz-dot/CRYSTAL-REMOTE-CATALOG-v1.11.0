# Crystal Remote Avatar Catalog v1.9.1

Automatic remote catalog backend for the Crystal VRChat Avatar Browser.

## Live URLs

Startup/fallback catalog:

\`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog.txt\`

Full search shards:

\`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog-shards/\`

## Current provider set

The automatic updater uses currently documented VRCX-compatible providers:

- AvtrDB v3
- avtr.zip
- VRCDB
- PAW
- NSVR
- VRCWB

VRCNDb is optional and requires an authorized key.

The old Prismic PAS URLs returned HTTP 404 during live verification, so the automatic backend no longer depends on them.

## Coverage

The crawler walks two-letter prefixes and saves its resume position. If every provider fails for one prefix, that prefix is kept for the next run rather than silently skipped.

## Search shards

After every successful update the accumulated catalog is rebuilt into first-character search shards so the VRChat world can search a much larger remote set without downloading the whole master file at once.

## Schedule

GitHub Actions refreshes the provider catalog every two hours.
