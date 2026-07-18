"""Global tuning. All gameplay coordinates are in *internal* pixels; the internal
surface is scaled up SCALE x to the window so the art stays chunky and crisp."""

SCALE = 2

# Set by init() once the real screen size is known.
VIEW_W = 960
VIEW_H = 150

STRIP_FRACTION = 0.28   # window height as fraction of work-area height

GROUND_H = 14           # ground thickness (internal px) — thin, sky gets the room
GRAVITY = 620.0

FPS = 60

# --- player ---
PLAYER_SPEED = 105.0
PLAYER_CROUCH_SPEED = 40.0
PLAYER_JUMP_V = 232.0
PLAYER_MAX_JUMPS = 2
PLAYER_HP = 100
PLAYER_IFRAMES = 0.6
ATTACK_COOLDOWN = 0.34
ATTACK_ACTIVE = (0.02, 0.22)   # window within the swing when the hitbox is live
ATTACK_RANGE = 21              # hitbox width in front of player
ATTACK_DMG = 1
MAGIC_UNLOCK_PCT = 40.0
MAGIC_COOLDOWN = 0.85
MAGIC_DMG = 2
MAGIC_SPEED = 175.0
DASH_SPEED = 315.0             # SPACE: forward dash attack
DASH_TIME = 0.2
DASH_COOLDOWN = 0.9
DASH_DMG = 1

# --- progress engine ---
PROGRESS_START = 10.0
PROGRESS_CAP = 95.0            # never pass this until the Stop hook fires
MIN_RUN_SECONDS = 8.0          # ultra-short prompts still get a full build-up

# --- enemies: hp (sword hits to kill), contact damage, walk speed ---
ENEMY_KINDS = {
    "bare":   dict(hp=1, dmg=1, speed=34.0, ranged=False),
    "sword":  dict(hp=2, dmg=2, speed=29.0, ranged=False),
    "archer": dict(hp=2, dmg=2, speed=24.0, ranged=True, proj="arrow", range=95.0, shoot_cd=2.3),
    "mage":   dict(hp=3, dmg=4, speed=20.0, ranged=True, proj="orb",   range=115.0, shoot_cd=2.9),
}
ENEMY_HIT_COOLDOWN = 0.9       # per-enemy: min seconds between contact hits on player
SPAWN_INTERVAL_MAX = 3.6       # seconds between spawns at 10%
SPAWN_INTERVAL_MIN = 0.95      # at 100%
SPAWN_RAMP_SECONDS = 20.0      # after a respawn, spawn rate eases back up over this long
MAX_ENEMIES_MIN = 3
MAX_ENEMIES_MAX = 12

# --- claude npc ---
SHIELD_RADIUS = 46.0
NPC_SPEED = 55.0
NPC_KILL_RADIUS = 14.0

DOOR_W = 20
DOOR_H = 34


def init(screen_w, screen_h):
    global VIEW_W, VIEW_H
    VIEW_W = screen_w // SCALE
    VIEW_H = screen_h // SCALE
