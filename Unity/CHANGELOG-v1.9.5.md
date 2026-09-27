# Crystal Avatar Browser v1.9.5

## Continuous crawler fix

- `Run continuously until complete` now truly ignores the normal per-run seed cap.
- Normal batch mode still uses `Seeds this run`.
- Resume state is saved after every seed.
- `STOP AFTER CURRENT SEED` preserves progress.
- The crawler continues through the two-letter discovery sequence (`aa ... zz`) automatically instead of requiring another click after each batch.
- Fixed missing continuous-mode state declarations from the first v1.9.4 draft.

## Remote backend

The GitHub-hosted remote backend remains separate and continues updating on its scheduled workflow.
