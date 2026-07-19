import pygame

from . import config, fx, sprites


class Bolt:
    """Player magic projectile — pierces everything it touches."""

    def __init__(self, x, y, facing):
        self.x, self.y = x, y
        self.vx = config.MAGIC_SPEED * facing
        self.life = 1.3
        self.hit_ids = set()
        self.dmg = config.MAGIC_DMG

    def update(self, dt, px):
        self.x += self.vx * dt
        self.life -= dt
        px.add(self.x, self.y, -self.vx * 0.1, 0, 0.25, (84, 222, 200), 1)

    def draw(self, surf):
        pygame.draw.circle(surf, (84, 222, 200), (int(self.x), int(self.y)), 3)
        pygame.draw.circle(surf, (200, 255, 240), (int(self.x), int(self.y)), 1)

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 3, int(self.y) - 3, 6, 6)


class Player:
    W = 10
    H = 20
    CROUCH_H = 13

    def __init__(self, world):
        self.world = world
        self.x = 18.0
        self.y = float(world.ground_y - self.H)
        self.vx = 0.0
        self.vy = 0.0
        self.hp = config.PLAYER_HP
        self.facing = 1
        self.on_ground = True
        self.jumps_left = config.PLAYER_MAX_JUMPS
        self.crouching = False
        self.attack_t = -1.0          # time since swing started; <0 = not swinging
        self.attack_cd = 0.0
        self.attack_id = 0
        self.dash_t = -1.0            # time since dash started; <0 = not dashing
        self.dash_cd = 0.0
        self.dash_hits = set()        # enemy ids already damaged by this dash
        self.magic_cd = 0.0
        self.mana = config.MAGIC_MAX
        self.iframes = 0.0
        self.drop_t = 0.0             # dropping through a platform
        self.anim_t = 0.0
        self.alive = True

    # ------------------------------------------------------------------ input
    def try_jump(self, px):
        if self.crouching and self.on_ground and self._on_platform():
            self.drop_t = 0.22        # crouch+jump = drop through platform
            self.on_ground = False
            self.vy = 30.0
            return
        if self.jumps_left > 0:
            self.vy = -config.PLAYER_JUMP_V
            self.jumps_left -= 1
            self.on_ground = False
            if self.jumps_left == 0:  # double-jump poof
                fx.magic_burst(px, self.x + self.W / 2, self.y + self.H, n=6)

    def try_attack(self, px):
        if self.attack_cd <= 0:
            self.attack_cd = config.ATTACK_COOLDOWN
            self.attack_t = 0.0
            self.attack_id += 1
            fx.slash_arc(px, self.x + self.W / 2 + 6 * self.facing,
                         self.y + 9, self.facing)

    def try_dash(self, px):
        if self.dash_cd <= 0 and not self.crouching:
            self.dash_cd = config.DASH_COOLDOWN
            self.dash_t = 0.0
            self.dash_hits = set()
            # brief invulnerability: dashing through a crowd is the point
            self.iframes = max(self.iframes, config.DASH_TIME + 0.05)
            fx.slash_arc(px, self.x + self.W / 2, self.y + 10, self.facing)
            return True
        return False

    @property
    def dashing(self):
        return 0.0 <= self.dash_t <= config.DASH_TIME

    def try_magic(self, magic_unlocked, px):
        if (magic_unlocked and self.magic_cd <= 0
                and self.mana >= config.MAGIC_COST):
            self.magic_cd = config.MAGIC_COOLDOWN
            self.mana -= config.MAGIC_COST
            fx.magic_burst(px, self.x + self.W / 2 + 8 * self.facing,
                           self.y + 8, n=6)
            return Bolt(self.x + self.W / 2 + 8 * self.facing, self.y + 8,
                        self.facing)
        return None

    # ---------------------------------------------------------------- physics
    @property
    def hitbox(self):
        h = self.CROUCH_H if self.crouching else self.H
        return pygame.Rect(int(self.x), int(self.y + self.H - h), self.W, h)

    def _on_platform(self):
        below = pygame.Rect(int(self.x), int(self.y + self.H), self.W, 2)
        return any(below.colliderect(p) for p in self.world.solid_platforms())

    def update(self, dt, keys, px):
        self.anim_t += dt
        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.magic_cd = max(0.0, self.magic_cd - dt)
        self.mana = min(config.MAGIC_MAX, self.mana + config.MAGIC_REGEN * dt)
        self.iframes = max(0.0, self.iframes - dt)
        self.drop_t = max(0.0, self.drop_t - dt)
        if self.attack_t >= 0:
            self.attack_t += dt
            if self.attack_t > self.attack_duration:
                self.attack_t = -1.0
        if self.dash_t >= 0:
            self.dash_t += dt
            if self.dash_t > config.DASH_TIME:
                self.dash_t = -1.0

        self.crouching = keys[pygame.K_s] and self.on_ground and not self.dashing
        speed = config.PLAYER_CROUCH_SPEED if self.crouching else config.PLAYER_SPEED
        move = 0
        if keys[pygame.K_a]:
            move -= 1
        if keys[pygame.K_d]:
            move += 1
        if move and not self.dashing:
            self.facing = move
        self.vx = move * speed

        prev_bottom = self.y + self.H
        if self.dashing:
            self.vx = self.facing * config.DASH_SPEED
            self.vy = 0.0                       # dash cuts straight, no gravity
            px.add(self.x + self.W / 2 - self.facing * 4,
                   self.y + 6 + (self.anim_t * 90) % 10,
                   -self.facing * 50, 0, 0.22, (200, 225, 245), 1)
        else:
            self.vy += config.GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        # keep inside the revealed world
        max_x = self.world.reveal_x - self.W
        self.x = max(0.0, min(self.x, max_x))

        # land on ground
        if self.y + self.H >= self.world.ground_y:
            self.y = float(self.world.ground_y - self.H)
            self.vy = 0.0
            self.on_ground = True
            self.jumps_left = config.PLAYER_MAX_JUMPS
        elif self.vy >= 0 and self.drop_t <= 0:
            # one-way platforms: land only when falling onto the top
            landed = False
            for p in self.world.solid_platforms():
                if (prev_bottom <= p.top + 1 and self.y + self.H >= p.top and
                        self.x + self.W > p.left and self.x < p.right):
                    self.y = float(p.top - self.H)
                    self.vy = 0.0
                    landed = True
                    break
            self.on_ground = landed
            if landed:
                self.jumps_left = config.PLAYER_MAX_JUMPS
        else:
            self.on_ground = False

    def take_hit(self, dmg, src_x, px):
        if self.iframes > 0 or not self.alive:
            return False
        self.hp -= dmg
        self.iframes = config.PLAYER_IFRAMES
        self.vy = min(self.vy, -60.0)
        fx.burst(px, self.x + self.W / 2, self.y + 8,
                 [(220, 60, 50), (160, 40, 40)], n=8, speed=50, life=0.4)
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return True

    @property
    def attack_hitbox(self):
        if not (config.ATTACK_ACTIVE[0] <= self.attack_t <= config.ATTACK_ACTIVE[1]):
            return None
        y = int(self.y + (10 if self.crouching else 4))
        # cover the whole body plus a bit behind: point-blank enemies get hit too
        back = 4
        w = self.W + back + config.ATTACK_RANGE
        if self.facing > 0:
            return pygame.Rect(int(self.x - back), y, w, 13)
        return pygame.Rect(int(self.x + self.W + back - w), y, w, 13)

    @property
    def attack_duration(self):
        return 0.25 if sprites.PACK else 0.2

    # ---------------------------------------------------------------- drawing
    def _frames(self):
        if self.crouching:
            return sprites.get("player_crouch"), 0.0, 3
        if not self.on_ground:
            return sprites.get("player_jump"), 0.0, 3
        if abs(self.vx) > 1:
            return sprites.get("player_run"), 7.0, 1
        return sprites.get("player_idle"), 1.6, 1

    def draw(self, surf):
        if (self.iframes > 0 and int(self.iframes * 14) % 2 == 0
                and self.alive and not self.dashing):
            return                                       # hit blink
        if sprites.PACK:
            self._draw_pack(surf)
            return
        frames, fps, dy = self._frames()
        idx = int(self.anim_t * fps) % len(frames) if fps else 0
        body = frames[idx]
        if self.facing < 0:
            body = sprites.flipped(body)
        bx = int(self.x) - 3
        by = int(self.y + self.H) - body.get_height() + dy
        surf.blit(body, (bx, by))
        self._draw_sword(surf)

    def _draw_pack(self, surf):
        """GothicVania hero: weapon is IN the frames, real attack animation."""
        if self.dashing:
            frames, idx = sprites.get("player_attack"), 2   # mid-thrust pose
        elif self.attack_t >= 0:
            frames = sprites.get("player_attack")
            idx = min(len(frames) - 1,
                      int(self.attack_t / self.attack_duration * len(frames)))
        elif self.iframes > config.PLAYER_IFRAMES - 0.25:
            frames, idx = sprites.get("player_hurt"), 0
        elif self.crouching:
            frames, idx = sprites.get("player_crouch"), 0
        elif not self.on_ground:
            frames = sprites.get("player_jump")
            idx = (0 if self.vy < -60 else 1 if self.vy < 0
                   else 2 if self.vy < 60 else 3)
        elif abs(self.vx) > 1:
            frames = sprites.get("player_run")
            idx = int(self.anim_t * 12) % len(frames)
        else:
            frames = sprites.get("player_idle")
            idx = int(self.anim_t * 6) % len(frames)
        img = frames[idx]
        if self.facing < 0:
            img = sprites.flipped(img)
        # frames are canvas-centered with feet on the bottom row
        bx = int(self.x + self.W / 2) - img.get_width() // 2
        by = int(self.y + self.H) - img.get_height()
        surf.blit(img, (bx, by))

    def _draw_sword(self, surf):
        sword = sprites.get("sword")[0]
        cx = int(self.x) + self.W // 2
        if 0 <= self.attack_t <= 0.08:                   # windup: raised behind
            s = pygame.transform.rotate(sword, -80 * self.facing)
            surf.blit(s, (cx - self.facing * 2 - s.get_width() // 2,
                          int(self.y) - 8))
        elif self.attack_t > 0.08:                       # swing: thrust forward
            s = sword if self.facing > 0 else sprites.flipped(sword)
            x = cx + (2 if self.facing > 0 else -2 - s.get_width())
            surf.blit(s, (x, int(self.y) + 7))
        else:                                            # at rest: blade down
            s = pygame.transform.rotate(sword, 80 * self.facing)
            x = cx + (5 if self.facing > 0 else -5 - s.get_width())
            surf.blit(s, (x, int(self.y) + 8))
