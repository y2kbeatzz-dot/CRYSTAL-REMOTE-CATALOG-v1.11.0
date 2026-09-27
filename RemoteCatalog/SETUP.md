# Crystal v1.11 remote search setup

Configure the world with three URLs.

## Catalog URL

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.11.0/catalog.txt`

## Creator / fallback shards

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.11.0/catalog-shards/`

## Avatar name search

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.11.0/search2/`

In Unity open:

`Crystal GUIs -> Configure Remote Catalog`

Paste all three URLs and apply them to the open Avatar Browser.

## Search behavior

For Everything / Avatar mode, Crystal takes the first two alphanumeric characters of the typed name.

Examples:

- `Shark` -> `sh`
- `Crystal` -> `cr`
- `Juice` -> `ju`

The world downloads the corresponding `search2/<prefix>.txt` provider-result shard, then filters it using the complete text typed by the player.

Creator mode continues to use the accumulated creator/fallback shard system.

## Automatic updates

GitHub Actions continues the two-character prefix crawl every two hours. Every completed prefix is published immediately into `docs/search2/`.
