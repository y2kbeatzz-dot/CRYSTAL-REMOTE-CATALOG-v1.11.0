# Automatic remote catalog setup

This lets your uploaded VRChat world receive newer avatar catalog data without reopening Unity.

## 1. Put this pack in a GitHub repository

The included GitHub Actions workflow runs the crawler automatically every 6 hours.

The crawler writes:

`docs/catalog.txt`

The workflow commits updates back to the repository.

## 2. Enable GitHub Pages

In the GitHub repository:

Settings -> Pages

Choose:

- Deploy from a branch
- Branch: `main`
- Folder: `/docs`

Your catalog URL will look like:

`https://USERNAME.github.io/REPOSITORY/catalog.txt`

## 3. Optional VRCNDb

Do not copy VRCNext's private build secret.

Only add this repository secret if the VRCNDb operator has given you an authorized key:

`CRYSTAL_VRCNDB_KEY`

Without it, the updater simply uses AvtrDB / Avtr.icu.

## 4. Configure the VRChat browser once

In Unity:

`Crystal GUIs -> Configure Remote Catalog`

Paste the GitHub Pages `catalog.txt` URL.

Recommended:

- Prefer remote: ON
- Load when world starts: ON
- Refresh while instance is open: optional
- Refresh interval: 1800 seconds or higher

Press:

`APPLY TO OPEN AVATAR BROWSERS`

Upload the world once.

After that, GitHub Actions can update `catalog.txt` without a Unity/world rebuild.

The world still contains its bundled `AvatarDatabase.txt` fallback in case the remote catalog cannot be downloaded.
