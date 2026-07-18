# Asset credits

## GothicVania Cemetery Pack — by Ansimuz (Luis Zuno)
- Source: https://opengameart.org/content/gothicvania-cemetery-pack (also on itch.io: https://ansimuz.itch.io/gothicvania-cemetery)
- License: **CC0 / public domain** — "free to use on whatever you want, personal or commercial. Credit is not required but appreciated."
- Used for: hero animations, skeleton + clothed-skeleton walk/rise, enemy death, ghost + haloed ghost, gravestones/statue/bushes/trees props, moon/mountains/graveyard parallax layers.
- Files live in `assets/pack/` (curated, half of the original pack; grab the full zip from the links above).
- The Claude-skeleton NPC is the pack's skeleton, tinted orange at load time.

## Everything else
- All other sprites, tiles, backgrounds are procedurally generated in `game/sprites.py` / `game/world.py` (they also serve as fallback if `assets/pack/` is deleted).
- All audio is synthesized at first launch by `game/audio.py` — original composition, inspired by the playful-spooky vibe of "Spooky Scary Skeletons" (Andrew Gold, 1996) without reproducing its melody.
