# Crystal Remote Avatar Catalog v1.8

Automatic remote catalog backend for the Crystal VRChat Avatar Browser.

## Live catalog URL

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog.txt`

## How it updates

GitHub Actions runs `.github/workflows/update-avatar-catalog.yml` every 6 hours. The updater crawls supported public avatar indexes, merges exact `avtr_` IDs, and writes `docs/catalog.txt`.

## VRChat world setup

In Unity open `Crystal GUIs -> Configure Remote Catalog` and use:

`https://y2kbeatzz-dot.github.io/CRYSTAL-REMOTE-CATALOG-v1.8/catalog.txt`

Enable **Prefer remote** and **Load when world starts**.

The world still keeps its bundled local catalog as a fallback if the remote catalog cannot be downloaded.

## VRCNDb

VRCNDb remains optional. Do not copy VRCNext's private build secret. Only configure the `CRYSTAL_VRCNDB_KEY` Actions secret if the VRCNDb operator gives you an authorized key.
