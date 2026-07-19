import math
import random

import pygame

from . import config, fx, sprites

_next_id = [0]


class Projectile:
    def __init__(self, x, y, vx, vy, kind, dmg):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.kind = kind              # arrow (fast dart) | orb (slow heavy)
        self.dmg = dmg
        self.life = 3.0
        self.reflected = False        # sword-parried: now it hunts enemies

    def reflect(self):
        self.reflected = True
        self.vx = -self.vx * 1.25
        self.vy = -self.vy * 0.3      # flatten the arc, send it back hard
        self.life = 3.0

    def update(self, dt, px, player):
        if self.kind == "arrow":
            self.vy += 60.0 * dt
        elif not self.reflected:       # orbs drift toward the player until parried
            ty = player.y + 8 - self.y
            self.vy += max(-30, min(30, ty)) * dt * 1.2
        if self.kind == "orb" and random.random() < dt * 30:
            color = (255, 200, 120) if self.reflected else (150, 90, 220)
            px.add(self.x, self.y, random.uniform(-6, 6),
                   random.uniform(-6, 6), 0.3, color, 1)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surf):
        if self.kind == "arrow":
            if sprites.PACK:           # spectral dart thrown by a ghost
                tail = (int(self.x - self.vx * 0.04), int(self.y - self.vy * 0.04))
                pygame.draw.line(surf, (110, 220, 210), tail,
                                 (int(self.x), int(self.y)), 2)
                pygame.draw.circle(surf, (220, 255, 250),
                                   (int(self.x), int(self.y)), 1)
            else:
                img = sprites.get("arrow")[0]
                if self.vx < 0:
                    img = sprites.flipped(img)
                surf.blit(img, (int(self.x) - 3, int(self.y) - 1))
        else:
            body = (255, 190, 100) if self.reflected else (150, 90, 220)
            core = (255, 240, 200) if self.reflected else (220, 180, 255)
            pygame.draw.circle(surf, body, (int(self.x), int(self.y)), 3)
            pygame.draw.circle(surf, core, (int(self.x), int(self.y)), 1)

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 3, int(self.y) - 3, 6, 6)


class Enemy:
    W = 11                            # default; per-kind below

    def __init__(self, kind, x, platform=None, ground_y=0):
        info = config.ENEMY_KINDS[kind]
        _next_id[0] += 1
        self.id = _next_id[0]
        self.kind = kind
        self.floats = sprites.PACK and info["ranged"]      # pack ghosts hover
        self.W, self.H = (12, 20) if self.floats else (11, 18)
        if not sprites.PACK:
            self.W, self.H = 10, 15
        self.hp = info["hp"]
        self.dmg = info["dmg"]
        self.speed = info["speed"] * random.uniform(0.85, 1.15)
        self.ranged = info["ranged"]
        self.range = info.get("range", 0)
        self.shoot_cd_max = info.get("shoot_cd", 0)
        self.platform = platform      # rect or None (= ground)
        self.x = float(x)
        self.base_y = platform.top if platform else ground_y
        # low enough that a standing bolt clips them and jump+bolt is a clean hit
        self.hover_off = 10 if platform is None else 8
        if self.floats:
            self.y = float(self.base_y - self.hover_off - self.H)
        else:
            self.y = float(self.base_y - self.H)
        self.state = "rise"           # rise > walk > windup ... dying
        self.state_t = 0.0
        self.vy = 0.0                 # walkers fall off platform edges
        self.rise_dur = 0.5 if self.floats else 0.7
        self.facing = -1
        self.anim_t = random.uniform(0, 10)
        self.shoot_cd = random.uniform(0.6, 1.6)
        self.hit_cd = 0.0             # min gap between contact hits on player
        self.last_hit_attack = -1     # player swing id that already hit us
        self.flash = 0.0
        self.stun = 0.0               # frozen after surviving a hit
        self.dying = False
        self.dead = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    def update(self, dt, game):
        self.anim_t += dt
        self.state_t += dt
        self.hit_cd = max(0.0, self.hit_cd - dt)
        self.flash = max(0.0, self.flash - dt)
        self.stun = max(0.0, self.stun - dt)
        if self.dying:
            if self.floats:
                self.y -= 8 * dt
            if self.state_t >= (0.45 if sprites.PACK else 0.05):
                self.dead = True
            return
        player = game.player
        dx = (player.x + player.W / 2) - (self.x + self.W / 2)
        self.facing = 1 if dx > 0 else -1
        if self.state == "rise":
            if not self.floats and random.random() < dt * 20:
                fx.dirt_burst(game.px, self.x + self.W / 2, self.base_y)
            if self.floats and random.random() < dt * 25:
                game.px.add(self.x + self.W / 2, self.y + self.H / 2,
                            random.uniform(-10, 10), random.uniform(-10, 10),
                            0.4, (110, 220, 210), 1)
            if self.state_t >= self.rise_dur:
                self.state = "walk"
            return
        if self.stun > 0:              # frozen by the blow: no moving, no hitting
            return
        if self.state == "windup":
            if self.state_t >= 0.4:
                self.state = "walk"
                self._fire(game)
            return
        # move toward the player (ranged types hold at range)
        if not (self.ranged and abs(dx) < self.range * 0.8):
            nx = self.x + self.facing * self.speed * dt
            self.x = max(0.0, min(nx, game.world.reveal_x - self.W))
        if self.floats:                # ghostly bob
            self.y = (self.base_y - self.hover_off - self.H
                      + math.sin(self.anim_t * 2.2) * 3)
        else:
            # walked past the edge? step off and hunt on foot (never jumps up)
            if self.platform is not None:
                cx_ = self.x + self.W / 2
                if cx_ < self.platform.left or cx_ > self.platform.right:
                    self.platform = None
                else:
                    self.y = float(self.platform.top - self.H)
            if self.platform is None:
                ground_top = game.world.ground_y - self.H
                if self.y < ground_top:
                    self.vy = min(self.vy + 620.0 * dt, 260.0)
                    self.y += self.vy * dt
                if self.y >= ground_top:
                    if self.vy > 60:
                        fx.dirt_burst(game.px, self.x + self.W / 2,
                                      game.world.ground_y)
                    self.y = float(ground_top)
                    self.vy = 0.0
                    self.base_y = game.world.ground_y
        # shield keeps monsters out
        npc = game.npc
        if npc and npc.shield_active:
            cx, cy = npc.shield_center
            ex, ey = self.x + self.W / 2, self.y + self.H
            d = math.hypot(ex - cx, ey - cy)
            if d < npc.shield_radius:
                k = (npc.shield_radius + 1) / max(d, 0.001)
                self.x = cx + (ex - cx) * k - self.W / 2
                self.x = max(0.0, min(self.x, game.world.reveal_x - self.W))
        # ranged attack
        if self.ranged and abs(dx) < self.range and self.shoot_cd <= 0:
            self.state = "windup"
            self.state_t = 0.0
            self.shoot_cd = self.shoot_cd_max * random.uniform(0.85, 1.2)
            return
        self.shoot_cd = max(0.0, self.shoot_cd - dt)

    def _fire(self, game):
        player = game.player
        sx = self.x + (self.W if self.facing > 0 else 0)
        sy = self.y + 5
        # aim at the player's upper chest so crouching genuinely dodges darts
        ty = player.y + (4 if not player.crouching else 8)
        tx = player.x + player.W / 2
        if self.kind == "archer":
            d = max(abs(tx - sx), 1)
            t = d / 130.0
            vx = (tx - sx) / t
            vy = (ty - sy) / t - 30.0 * t
            game.projectiles.append(Projectile(sx, sy, vx, vy, "arrow", self.dmg))
        else:
            ang = math.atan2(ty - sy, tx - sx)
            game.projectiles.append(
                Projectile(sx, sy, math.cos(ang) * 62, math.sin(ang) * 62,
                           "orb", self.dmg))
            fx.magic_burst(game.px, sx, sy, n=5)

    def take_hit(self, dmg, px):
        """Returns True when this hit kills (caller scores it). Survivors are
        briefly stunned so landing the first hit is always safe."""
        if self.dying:
            return False
        self.hp -= dmg
        self.flash = 0.1
        if self.hp > 0:
            self.stun = 0.28
            self.flash = 0.28          # stay white while frozen
            if self.state == "windup":
                self.state = "walk"    # a hit interrupts the shot
        if self.hp <= 0:
            self.dying = True
            self.state_t = 0.0
            if not sprites.PACK:
                fx.bone_burst(px, self.x + self.W / 2, self.y + self.H / 2)
            elif self.floats:
                fx.magic_burst(px, self.x + self.W / 2, self.y + self.H / 2, n=8)
            return True
        return False

    # ---------------------------------------------------------------- drawing
    def draw(self, surf, ground_clip_y):
        if sprites.PACK:
            self._draw_pack(surf)
        else:
            self._draw_procedural(surf)

    def _anchor_blit(self, surf, img, bottom=None, alpha=None):
        if self.facing < 0:
            img = sprites.flipped(img)
        if alpha is not None:
            img = img.copy()
            img.set_alpha(alpha)
        surf.blit(img, (int(self.x + self.W / 2) - img.get_width() // 2,
                        int(bottom if bottom is not None else self.y + self.H)
                        - img.get_height()))

    def _draw_pack(self, surf):
        if self.dying:
            if self.floats:
                frames = sprites.get("skel_" + self.kind)
                img = frames[int(self.anim_t * 8) % len(frames)]
                self._anchor_blit(surf, img,
                                  alpha=max(0, 255 - int(self.state_t / 0.45 * 255)))
            else:
                frames = sprites.get("enemy_death")
                idx = min(len(frames) - 1, int(self.state_t / 0.45 * len(frames)))
                self._anchor_blit(surf, frames[idx], bottom=self.base_y
                                  if self.platform is None else self.y + self.H)
            return
        if self.state == "rise":
            if self.floats:
                frames = sprites.get("skel_" + self.kind)
                img = frames[int(self.anim_t * 8) % len(frames)]
                self._anchor_blit(surf, img,
                                  alpha=int(255 * self.state_t / self.rise_dur))
            else:
                frames = sprites.get(f"skel_{self.kind}_rise")
                idx = min(len(frames) - 1,
                          int(self.state_t / self.rise_dur * len(frames)))
                self._anchor_blit(surf, frames[idx], bottom=self.base_y)
            return
        frames = sprites.get("skel_" + self.kind)
        img = frames[int(self.anim_t * (8 if self.floats else 10)) % len(frames)]
        if self.flash > 0 or (self.state == "windup" and
                              int(self.state_t * 16) % 2 == 0):
            img = sprites.white(img)
        self._anchor_blit(surf, img)

    def _draw_procedural(self, surf):
        frames = sprites.get("skel_" + self.kind)
        if self.state == "rise":
            frac = min(1.0, self.state_t / self.rise_dur)
            img = frames[0]
            h = int(img.get_height() * frac)
            if h <= 0:
                return
            src = img.subsurface((0, 0, img.get_width(), h))
            surf.blit(src, (int(self.x) - 1, self.base_y - h))
            return
        img = frames[2] if self.state == "windup" else \
            frames[int(self.anim_t * 6) % 2]
        if self.flash > 0:
            img = sprites.white(img)
        if self.facing < 0:
            img = sprites.flipped(img)
        surf.blit(img, (int(self.x) - 1, int(self.y)))


class Spawner:
    def __init__(self):
        self.cooldown = 2.0
        self.ramp_start = 0.0

    def reset_ramp(self, now):
        self.ramp_start = now

    def update(self, dt, now, game):
        hard = game.mode == "hard"
        pct = game.progress.value
        difficulty = max(0.0, min(1.0, (pct - 10.0) / 90.0))
        ramp_secs = config.SPAWN_RAMP_SECONDS * (config.HARD_RAMP_MULT
                                                 if hard else 1.0)
        ramp_t = (now - self.ramp_start) / ramp_secs
        ramp = 3.0 - 2.0 * max(0.0, min(1.0, ramp_t))          # 3x..1x interval
        interval = (config.SPAWN_INTERVAL_MAX +
                    (config.SPAWN_INTERVAL_MIN - config.SPAWN_INTERVAL_MAX)
                    * difficulty) * ramp
        cap = round(config.MAX_ENEMIES_MIN +
                    (config.MAX_ENEMIES_MAX - config.MAX_ENEMIES_MIN) * difficulty)
        if hard:
            interval *= config.HARD_SPAWN_MULT
            cap += config.HARD_EXTRA_ENEMIES
        self.cooldown -= dt
        alive = sum(1 for e in game.enemies if not e.dying)
        if self.cooldown > 0 or alive >= cap:
            return
        self.cooldown = interval * random.uniform(0.7, 1.3)
        kind = self._pick_kind(pct + (config.HARD_TIER_SHIFT if hard else 0.0))
        spot = self._pick_spot(game, kind)
        if spot is None:
            return
        x, plat = spot
        e = Enemy(kind, x, plat, game.world.ground_y)
        if hard:
            e.speed *= config.HARD_SPEED_MULT
        game.enemies.append(e)

    def _pick_kind(self, pct):
        # the graveyard mostly coughs up bare bones; ranged stays the seasoning
        kinds, weights = ["bare"], [6.0]
        if pct >= 25:
            kinds.append("sword")
            weights.append(2.0 + pct / 50.0)
        if pct >= 45:
            kinds.append("archer")
            weights.append(0.9 + pct / 120.0)
        if pct >= 70:
            kinds.append("mage")
            weights.append(0.7 + pct / 120.0)
        return random.choices(kinds, weights)[0]

    def _pick_spot(self, game, kind):
        world, player = game.world, game.player
        plats = world.solid_platforms()
        for _ in range(8):
            use_plat = plats and random.random() < (0.6 if kind in ("archer", "mage")
                                                    else 0.15)
            if use_plat:
                p = random.choice(plats)
                x = random.uniform(p.left, max(p.left + 1, p.right - 12))
                plat = p
            else:
                if world.reveal_x < 50:
                    return None
                x = random.uniform(15, world.reveal_x - 27)
                plat = None
            if abs(x - player.x) < 42:
                continue
            npc = game.npc
            if npc and npc.shield_active:
                cx = npc.shield_center[0]
                if abs(x - cx) < npc.shield_radius + 10:
                    continue
            return x, plat
        return None
