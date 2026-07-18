# GraveWait

A spooky graveyard side-scroller that doubles as a **loading screen for Claude Code**.

Every time you send a prompt, a borderless strip appears along the bottom of your
screen: a graveyard world that builds itself left-to-right as your prompt runs.
Fight the skeletons that claw out of the ground while you wait. When Claude needs
a permission, a ghostly messenger descends from a portal, shields you, and shows
the request. When the prompt finishes, a door opens on the far right — escape
through it to bank a win, or stay and fight.

No Claude? The installer can put a desktop shortcut that runs a standalone
**4-minute demo** with a simulated prompt instead.

## Install (Windows)

Grab **GraveWaitSetup.exe** from the
[Releases](../../releases) page and run it. The setup wizard lets you:

- read and accept the terms,
- pick the install folder,
- **Attach to Claude Code** — adds the launch-on-prompt hooks to your
  `~/.claude/settings.json` (original file backed up; removed on uninstall),
- create a **desktop shortcut** for the standalone 4-minute demo.

No Python required — the installer ships self-contained executables.

## Run from source

```
pip install -r requirements.txt
python install_hooks.py         # attach to Claude Code (remove: --uninstall)
python main.py --demo           # or: standalone 4-minute demo, no Claude
python tools\fake_prompt.py     # dev: simulate a ~2 min prompt lifecycle
```

## Controls

| Key | Action |
|-----|--------|
| A / D | move |
| W | jump / double-jump (crouch+W drops through platforms) |
| SPACE | forward dash attack (brief invulnerability, hits everything you pass) |
| S | crouch (dodges darts) |
| L | sword (also parries frontal projectiles back at enemies) |
| P | magic bolt (unlocks at 40% progress; cancels enemy shots mid-air) |
| ENTER | talk to the messenger / exit the door |
| M | mute |
| hold Q | quit |

## Rules

- The world reveal IS the progress bar (semi-real: it creeps with Claude's tool
  activity, stalls when Claude is quiet, and completes only when the prompt does).
- 100 HP, no healing, no pausing. Die and you lose your score — press SPACE to
  rise again at the same world progress, with a freshly rearranged sky.
- Skeleton tiers appear as the world grows: bare (1 hit), clothed (2), ghost (2),
  haloed ghost (3). Spawns get faster and denser toward 100%.
- Exiting the open door counts a win. High score and wins persist in
  `%LOCALAPPDATA%\GraveWait\save.json`.

## Music

The soundtrack is a synthesized original in a playful-spooky style. To use your
own track instead, drop it as `music.mp3` / `.ogg` / `.wav` either in
`assets/` (running from source) or in `%LOCALAPPDATA%\GraveWait` (installed) —
it will loop in place of the built-in tune.

## Building the installer

```
pip install -r requirements.txt pyinstaller
pyinstaller gravewait.spec --noconfirm      # dist/GraveWait/ (two exes)
ISCC installer\gravewait.iss                # installer/Output/GraveWaitSetup.exe
```

The GitHub Actions workflow (`.github/workflows/build-installer.yml`) does the
same automatically and attaches the setup exe to the release whenever you push
a `v*` tag.

## Layout

- `main.py` — window (bottom strip, always-on-top, never steals focus), scenes,
  combat; also the CLI for `--demo`, `--install-hooks`, `--uninstall-hooks`
- `game/` — world, player, enemies, claude_npc, progress, events, demo, fx, ui,
  audio, save
- `hooks/emit_event.py` — Claude Code hook handler; appends to
  `%LOCALAPPDATA%\GraveWait\events.jsonl` and launches the game
  (ships as `gravewait-hook.exe` in the packaged build)
- `install_hooks.py` — global hook installer / `--uninstall`
- `tools/fake_prompt.py` — dev-only prompt-lifecycle simulator
- `installer/` — Inno Setup script, EULA, icon
- `assets/pack/` — GothicVania Cemetery art (CC0, see `ASSETS.md`); delete the
  folder and the game falls back to built-in procedural pixel art

## Credits

Art: [GothicVania Cemetery](https://opengameart.org/content/gothicvania-cemetery-pack)
by Ansimuz (CC0). Everything else: see `ASSETS.md`. MIT licensed. Not affiliated
with Anthropic.
