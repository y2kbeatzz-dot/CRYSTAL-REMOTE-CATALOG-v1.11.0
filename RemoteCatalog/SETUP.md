# Crystal v1.9 automatic catalog

The automatic backend now uses Prismic's current public bulk avatar databases as its primary source.

Configure the world with:

Catalog URL:
`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog.txt`

Full Search Shards:
`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog-shards/`

The small catalog.txt is used for startup/fallback browsing.

When a player searches an avatar or creator name, Crystal downloads only the relevant full-search shard instead of trying to download the entire multi-million-avatar database at once.

The workflow rebuilds from Prismic every 6 hours.

Prismic provides:
- main/PC avatar metadata;
- Quest/Android compatibility database;
- iOS compatibility database.

AvtrDB v3 support is implemented using the current VRCX-format endpoint but stays optional because provider anti-abuse requirements can change.

VRCNDb remains optional and requires an authorized key from its operator.
