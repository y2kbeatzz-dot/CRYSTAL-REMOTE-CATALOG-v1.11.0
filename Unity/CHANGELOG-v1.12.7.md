# Crystal GUI v1.12.7

## AvtrDB backend-only architecture

- Unity no longer calls AvtrDB directly.
- Editor windows label AvtrDB as **REMOTE BACKEND ONLY**.
- The in-world source chip is shown as `AvtrDB*`.
- `AvtrDB*` indicates a result supplied by the remote backend.
- Local crawling continues with providers that work directly from Unity.
- Remote multi-provider data is served from:
  - https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.11.0/catalog.txt
  - https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.11.0/catalog-shards/
  - https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.11.0/search2/

This avoids direct Unity-side AvtrDB HTTP 403/520 failures while preserving AvtrDB as a backend source when available.
