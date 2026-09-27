# Crystal GUI v1.12.2

Unity-side AvtrDB compatibility update.

- Uses `https://api.avtrdb.com/v3/avatar/search/vrcx`.
- Sends `Referer: https://vrcx.app`.
- Generates and reuses a persistent local `VRCX-ID` UUID through Unity EditorPrefs.
- Parses the current v3 VRCX response fields: `Id`, `Name`, `AuthorName`, and `AuthorId`.
- Removes the obsolete `vrc_id` response assumption.
- Keeps the current GUI, filters, remote catalog/search shards, creator search, and platform badges.
- Existing `AvatarDatabase.txt` and saved crawl position can be retained.
