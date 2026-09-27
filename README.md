# Crystal Remote Avatar Catalog v1.9

Automatic remote catalog backend for the Crystal VRChat Avatar Browser.

## Live URLs

Startup/fallback catalog:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog.txt`

Full search shards:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog-shards/`

## Primary source

The automatic updater now uses Prismic's current public PAS database files as the bulk source:

- main/PC metadata
- Quest/Android compatibility
- iOS compatibility

The old alphabet crawler is no longer the main discovery system. The bulk database is processed directly.

## Search shards

The full Prismic dataset is split into small first-character shards so a VRChat world does not need to download one massive multi-million-row text file.

Avatar-name and creator-name initials both feed the shards, so the in-world browser can search by either.

## Optional providers

AvtrDB v3 support uses the current VRCX provider endpoint:

`https://api.avtrdb.com/v3/avatar/search/vrcx`

It is optional because rate-limit and anti-abuse requirements can change.

VRCNDb is optional and requires an authorized key.

VRCDB is not scraped because its current public documentation does not publish a supported external API contract.

## Schedule

GitHub Actions refreshes the Prismic-derived catalog every 6 hours.
