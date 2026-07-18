"""The Claude-skeleton: emerges from a sky portal when Claude Code needs the
user (permission request / waiting), fights its way to the player, casts a
protective shield dome, and shows the actual hook message in a dialogue cloud.
It leaves the way it came once hook activity resumes."""
import math
import random

import pygame

from . import config, fx, sprites

ORANGE = (217, 119, 87)


class ClaudeNPC:
    W = 10
    H = 15

    def __init__(self, message, world, player_x, px):
        if sprites.PACK:
            self.W, self.H = 12, 19
        self.message = message or "Claude needs your attention."
        lo = 40
        hi = max(lo + 1, world.reveal_x - 60)
        self.portal_x = random.uniform(lo, hi)
        self.portal_y = 16
        self.platform = pygame.Rect(int(self.portal_x) - 18, 30, 36, 5)
        self.plat_surf = self._render_platform()
        self.x = self.portal_x - self.W / 2
        self.y = float(self.portal_y)
        self.vy = 0.0
        self.state = "emerge"        # emerge > drop > seek > cast > present > return > ascend > gone
        self.state_t = 0.0
        self.approach_side = 0       # fixed on entering seek so it can't flip-flop
        self.facing = 1
        self.anim_t = 0.0
        self.kill_cd = 0.0
        self.shield_active = False
        self.shield_center = (0.0, 0.0)
        self.shield_radius = 0.0
        self.dialogue_open = False
        self.resolved = False
        fx.magic_burst(px, self.portal_x, self.portal_y + 8, n=16)

    def _render_platform(self):
        s = pygame.Surface((36, 5), pygame.SRCALPHA)
        s.fill((80, 60, 100))
        pygame.draw.line(s, ORANGE, (0, 0), (36, 0))
        return s

    @property
    def gone(self):
        return self.state == "gone"

    @property
    def present(self):
        return self.state == "present"

    def set_message(self, message):
        self.message = message or self.message
        self.resolved = False

    def resolve(self):
        """Hook activity resumed — pack up and leave."""
        if self.state in ("return", "ascend", "gone"):
            return
        self.resolved = True
        self.dialogue_open = False
        self.shield_active = False
        self.state = "return"
        self.state_t = 0.0

    def update(self, dt, game):
        self.state_t += dt
        self.anim_t += dt
        self.kill_cd = max(0.0, self.kill_cd - dt)
        px = game.px
        ground_top = game.world.ground_y - self.H
        if self.state in ("emerge", "ascend") or random.random() < dt * 8:
            fx.portal_swirl(px, self.portal_x, self.portal_y)

        if self.state == "emerge":
            if self.state_t > 0.7:
                self.state, self.state_t = "drop", 0.0
        elif self.state == "drop":
            self.vy = min(self.vy + 300 * dt, 55.0)      # slow magical glide
            self.y += self.vy * dt
            if random.random() < dt * 20:
                px.add(self.x + self.W / 2, self.y + self.H,
                       random.uniform(-8, 8), -10, 0.4, ORANGE, 1)
            if self.y >= ground_top:
                self.y = float(ground_top)
                self.vy = 0.0
                self.state, self.state_t = "seek", 0.0
        elif self.state == "seek":
            if self.approach_side == 0:
                self.approach_side = -1 if self.x < game.player.x else 1
            if self.approach_side < 0:
                target = game.player.x - self.W - 5
            else:
                target = game.player.x + game.player.W + 5
            dx = target - self.x
            self.facing = 1 if dx > 0 else -1
            if abs(dx) > 3:
                self.x += self.facing * config.NPC_SPEED * dt
            else:
                self.state, self.state_t = "cast", 0.0
                self.shield_center = (game.player.x + game.player.W / 2,
                                      float(game.world.ground_y))
            self._slay_path(game)
        elif self.state == "cast":
            self.shield_active = True
            self.shield_radius = config.SHIELD_RADIUS * min(1.0, self.state_t / 0.6)
            if self.state_t <= 0.6 and random.random() < dt * 40:
                a = random.uniform(math.pi, math.tau)
                cx, cy = self.shield_center
                px.add(cx + math.cos(a) * self.shield_radius,
                       cy + math.sin(a) * self.shield_radius,
                       0, -6, 0.4, (120, 210, 255), 1)
            if self.state_t > 0.6:
                self.shield_radius = config.SHIELD_RADIUS
                self.state, self.state_t = "present", 0.0
        elif self.state == "present":
            self.facing = 1 if game.player.x > self.x else -1
            self.y = ground_top + math.sin(self.anim_t * 3) * 1.5
            self._slay_path(game)
        elif self.state == "return":
            dx = self.portal_x - self.W / 2 - self.x
            self.facing = 1 if dx > 0 else -1
            if abs(dx) > 3:
                self.x += self.facing * config.NPC_SPEED * dt
                self._slay_path(game)
            else:
                self.state, self.state_t = "ascend", 0.0
        elif self.state == "ascend":
            self.y -= 60 * dt
            px.add(self.x + self.W / 2, self.y + self.H,
                   random.uniform(-6, 6), 15, 0.4, ORANGE, 1)
            if self.y <= self.portal_y:
                self.state = "gone"
                fx.magic_burst(px, self.portal_x, self.portal_y + 8, n=18)

    def _slay_path(self, game):
        """Cut down skeletons in the way, naturally and instantly."""
        if self.kill_cd > 0:
            return
        cx, cy = self.x + self.W / 2, self.y + self.H / 2
        for e in game.enemies:
            if e.dead or e.dying or e.state == "rise":
                continue
            if math.hypot(e.x + e.W / 2 - cx, e.y + e.H / 2 - cy) < config.NPC_KILL_RADIUS:
                if e.take_hit(99, game.px):
                    game.on_npc_kill(e)
                fx.slash_arc(game.px, cx + 6 * self.facing, cy, self.facing)
                self.kill_cd = 0.15
                break

    # ---------------------------------------------------------------- drawing
    def draw(self, surf):
        if self.state != "gone":
            self._draw_portal(surf)
        if self.state in ("emerge", "gone"):
            return
        surf.blit(self.plat_surf, self.platform.topleft)
        # spectral glow around the messenger
        glow = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(glow, (110, 220, 255, 40), (15, 15), 14)
        surf.blit(glow, (int(self.x + self.W / 2) - 15, int(self.y) - 4))
        frames = sprites.get("skel_claude")
        img = frames[int(self.anim_t * 8) % len(frames)]
        if self.facing < 0:
            img = sprites.flipped(img)
        surf.blit(img, (int(self.x + self.W / 2) - img.get_width() // 2,
                        int(self.y + self.H) - img.get_height()))

    def _draw_portal(self, surf):
        """Swirling void vortex, purple into cyan into black."""
        x, y = int(self.portal_x), int(self.portal_y)
        wob = math.sin(self.anim_t * 5) * 1.5
        pygame.draw.ellipse(surf, (60, 40, 90), (x - 11, y - 14 + wob, 22, 28))
        pygame.draw.ellipse(surf, (150, 90, 220), (x - 9, y - 12 + wob, 18, 24), 2)
        a = self.anim_t * 4
        for i in range(3):                       # rotating swirl arms
            ang = a + i * 2.09
            sx = x + math.cos(ang) * 5
            sy = y + math.sin(ang) * 8
            pygame.draw.circle(surf, (110, 200, 255), (int(sx), int(sy)), 1)
        pygame.draw.ellipse(surf, (28, 16, 46), (x - 5, y - 8, 10, 16))
        pygame.draw.ellipse(surf, (14, 8, 24), (x - 3, y - 5, 6, 10))

    def draw_shield(self, surf):
        if not self.shield_active or self.shield_radius < 2:
            return
        cx, cy = int(self.shield_center[0]), int(self.shield_center[1])
        r = int(self.shield_radius)
        dome = pygame.Surface((r * 2 + 4, r + 2), pygame.SRCALPHA)
        pygame.draw.circle(dome, (100, 200, 255, 20), (r + 2, r + 2), r)
        pygame.draw.circle(dome, (140, 230, 255, 80), (r + 2, r + 2), r, 2)
        pygame.draw.circle(dome, (217, 119, 87, 50), (r + 2, r + 2), r - 3, 1)
        surf.blit(dome, (cx - r - 2, cy - r - 2))

    def shimmer(self, px):
        if self.shield_active and random.random() < 0.5:
            a = random.uniform(math.pi, math.tau)
            cx, cy = self.shield_center
            px.add(cx + math.cos(a) * self.shield_radius,
                   cy + math.sin(a) * self.shield_radius,
                   0, random.uniform(-4, 4), 0.3,
                   random.choice([(140, 230, 255), (217, 119, 87)]), 1)
