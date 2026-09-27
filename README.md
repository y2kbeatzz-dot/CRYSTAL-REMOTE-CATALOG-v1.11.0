# Crystal Remote Avatar Catalog v1.9.2

Automatic remote backend for the Crystal VRChat Avatar Browser.

## Live URLs

Catalog:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog.txt`

Full search shards:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog-shards/`

## Current automatic providers

- AvtrDB v3
- avtr.zip
- VRCDB
- PAW
- NSVR
- VRCWB
- optional VRCNDb when an authorized key is configured

The retired Prismic PAS download URLs are not used automatically.

## What the updater does

The scheduled workflow:

- resumes its discovery prefix instead of restarting;
- merges avatars by exact `avtr_` ID;
- stores avatar name, creator, source, platform and image URL when supplied;
- creates `docs/catalog-master.txt`;
- creates a smaller startup `docs/catalog.txt`;
- rebuilds `docs/catalog-shards/*.txt` for in-world full search;
- isolates providers that return 403/429 or repeatedly fail;
- preserves the current seed when every provider fails, instead of skipping alphabet ranges.

The workflow currently processes 24 discovery prefixes every 2 hours.

## Unity / VRChat setup

In Unity use:

`Crystal GUIs -> Configure Remote Catalog`

Set:

Catalog URL:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog.txt`

Full Search Shards:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog-shards/`

Then enable **Prefer remote** and **Load when world starts**.

Crystal v1.9.2 uses the delayed `SearchPressed -> CommitSearchPressed` flow for the SEARCH ALL button and VRChat keyboard submit.

## Optional secrets

`CRYSTAL_VRCNDB_KEY` — only use an authorized key supplied by the VRCNDb operator.

`CRYSTAL_VRCX_ID` — optional VRCX-style provider header if you have a valid value to use.

Do not copy private keys from other projects.
