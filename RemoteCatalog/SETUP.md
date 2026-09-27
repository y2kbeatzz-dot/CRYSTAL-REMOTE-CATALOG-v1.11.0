# Crystal v1.9.1 automatic catalog

The automatic backend uses current VRCX-compatible providers rather than the retired Prismic PAS download URLs.

Automatic providers:
- AvtrDB v3
- avtr.zip
- VRCDB
- PAW
- NSVR
- VRCWB

Optional:
- VRCNDb with an authorized key
- Prismic rows can still appear if you manually import a current Prismic export, but the old public PAS URLs now return 404 and are not used automatically.

Configure the world once with:

Catalog URL:
\`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog.txt\`

Full Search Shards:
\`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog-shards/\`

The updater resumes its two-letter discovery position and does not skip a seed when every provider fails.

The SEARCH ALL button and VRChat keyboard Done/Enter both use the same delayed Udon search path.
