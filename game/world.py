"""The graveyard strip: pre-rendered spooky background + ground, gravestone
props, sky platforms, the exit door, and the left-to-right magical reveal."""
import math
import random

import pygame

from . import config, fx, sprites

PROP_CHOICES = [
    ("grave1", 4), ("grave2", 3), ("grave3", 3), ("grave4", 3),
    ("statue", 1), ("bush_large", 2), ("bush_small", 2),
    ("dead_bush", 2), ("fence", 2), ("lantern", 1), ("skull_pile", 2),
]


class World:
    def __init__(self, seed=None):
        rng = random.Random(seed)
        W, H = config.VIEW_W, config.VIEW_H
        self.ground_y = H - config.GROUND_H
        self.reveal_x = W * config.PROGRESS_START / 100.0
        self.t = 0.0
        self.platforms = self._gen_platforms(rng)
        self.props = self._gen_props(rng)
        self.bg = self._render_bg(rng)
        self.ground = self._render_ground(rng)
        self.fog = self._render_fog(rng)
        self.door_rect = pygame.Rect(W - config.DOOR_W - 5,
                                     self.ground_y - config.DOOR_H,
                                     config.DOOR_W, config.DOOR_H)
        self.door_open = False

    # ------------------------------------------------------------- generation
    def _gen_platforms(self, rng):
        """Varied heights with a guarantee: every platform is landable either
        straight off the ground (double jump ~86px) or by hopping up from the
        platform it stacks on (step <=52px, horizontal offset <=40px)."""
        W = config.VIEW_W
        n = rng.randint(4, 6)
        plats = []
        slot = W * 0.82 / n
        for i in range(n):
            w = rng.randint(38, 64)
            if plats and rng.random() < 0.45:
                prev = plats[-1]["rect"]        # stacked tier: hop up from prev
                x = int(min(max(8, prev.centerx + rng.randint(-40, 40) - w // 2),
                            W - w - 30))
                y = max(44, prev.top - rng.randint(28, 52))
            else:                               # ground tier
                x = int(W * 0.09 + i * slot + rng.uniform(0, max(1.0, slot - w)))
                y = self.ground_y - rng.randint(58, 80)
            surf = self._render_platform(rng, w)
            plats.append({"rect": pygame.Rect(x, y, w, 5), "shown": False,
                          "surf": surf})
        return plats

    def _render_platform(self, rng, w):
        """Floating stone island: grassy top, rocky body, craggy bottom."""
        h = 13
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        body = pygame.Rect(0, 2, w, 6)
        pygame.draw.rect(s, (104, 100, 118), body, border_radius=2)
        for _ in range(w // 3):                     # rock texture
            s.set_at((rng.randint(1, w - 2), rng.randint(3, 7)),
                     rng.choice([(82, 78, 96), (126, 122, 140)]))
        for x in range(0, w, 6):                    # craggy hanging chunks
            r = rng.randint(2, 4)
            pygame.draw.circle(s, (88, 84, 102),
                               (min(w - 3, x + 3), 8), r)
        for x in range(w):                          # grass lip
            g = rng.choice([(52, 96, 50), (68, 116, 58), (44, 82, 46)])
            s.set_at((x, 2), g)
            if rng.random() < 0.5:
                s.set_at((x, 1), g)
            if rng.random() < 0.15:
                s.set_at((x, 0), (80, 130, 66))
        return s

    def _gen_props(self, rng):
        names = [(n, w) for n, w in PROP_CHOICES if sprites.has(n)]
        props = []
        x = 14.0
        while x < config.VIEW_W - 40:
            name = rng.choices([n for n, _ in names],
                               [w for _, w in names])[0]
            surf = sprites.get(name)[0]
            props.append({"name": name, "surf": surf,
                          "x": int(x), "y": self.ground_y - surf.get_height() + 2,
                          "shown": False})
            x += rng.uniform(34, 85)
        return props

    def _render_bg(self, rng):
        if sprites.PACK:
            bg = self._render_bg_pack(rng)
            if bg is not None:
                return bg
        return self._render_bg_procedural(rng)

    def _render_bg_pack(self, rng):
        """Procedural sky (one moon, no tiling artifacts) + GothicVania
        mountains, dead trees and graveyard silhouettes, plus lurking eyes."""
        W, H = config.VIEW_W, config.VIEW_H
        mountains = sprites.load_layer_half("mountains.png")
        graveyard = sprites.load_layer_half("graveyard.png")
        if graveyard is None:
            return None
        bg = pygame.Surface((W, H))
        top, bot = (10, 8, 22), (44, 22, 52)
        for y in range(H):
            k = y / H
            bg.fill((int(top[0] + (bot[0] - top[0]) * k),
                     int(top[1] + (bot[1] - top[1]) * k),
                     int(top[2] + (bot[2] - top[2]) * k)), (0, y, W, 1))
        for _ in range(W // 10):
            bg.set_at((rng.randint(0, W - 1), rng.randint(0, int(H * 0.5))),
                      rng.choice([(190, 190, 215), (140, 140, 170),
                                  (220, 220, 240)]))
        mx, my, mr = int(W * 0.84), int(H * 0.24), 14
        glow = pygame.Surface((mr * 6, mr * 6), pygame.SRCALPHA)
        for gr, ga in ((mr * 3, 16), (mr * 2, 26), (int(mr * 1.4), 34)):
            pygame.draw.circle(glow, (235, 215, 190, ga), (mr * 3, mr * 3), gr)
        bg.blit(glow, (mx - mr * 3, my - mr * 3))
        pygame.draw.circle(bg, (238, 230, 208), (mx, my), mr)
        for _ in range(5):
            a, d = rng.uniform(0, math.tau), rng.uniform(0, mr * 0.6)
            pygame.draw.circle(bg, (212, 204, 182),
                               (int(mx + math.cos(a) * d),
                                int(my + math.sin(a) * d)), rng.randint(1, 3))
        if mountains is not None:
            for x in range(0, W, mountains.get_width()):
                bg.blit(mountains, (x, self.ground_y - mountains.get_height() + 14))
        for name in ("bg_tree1", "bg_tree2", "bg_tree3"):
            if not sprites.has(name):
                continue
            tree = sprites.get(name)[0]
            for _ in range(2):
                tx = rng.randint(-20, W - 30)
                dark = tree.copy()
                dark.fill((110, 100, 135), special_flags=pygame.BLEND_RGB_MULT)
                bg.blit(dark, (tx, self.ground_y - tree.get_height() + 4))
        if graveyard is not None:
            for x in range(0, W, graveyard.get_width()):
                bg.blit(graveyard, (x, self.ground_y - graveyard.get_height() + 4))
        # lurking eyes: pairs of dots that pulse in draw_bg
        self.eyes = [(rng.randint(10, W - 10),
                      rng.randint(max(6, self.ground_y - 75), self.ground_y - 30),
                      rng.uniform(0, math.tau), rng.uniform(0.5, 1.4))
                     for _ in range(W // 130)]
        return bg

    def _render_bg_procedural(self, rng):
        W, H = config.VIEW_W, config.VIEW_H
        self.eyes = [(rng.randint(10, W - 10),
                      rng.randint(max(6, self.ground_y - 70), self.ground_y - 28),
                      rng.uniform(0, math.tau), rng.uniform(0.5, 1.4))
                     for _ in range(W // 160)]
        bg = pygame.Surface((W, H))
        top, bot = (8, 8, 18), (28, 18, 46)
        for y in range(H):
            k = y / H
            bg.fill((int(top[0] + (bot[0] - top[0]) * k),
                     int(top[1] + (bot[1] - top[1]) * k),
                     int(top[2] + (bot[2] - top[2]) * k)),
                    (0, y, W, 1))
        for _ in range(W // 12):                       # stars
            x, y = rng.randint(0, W - 1), rng.randint(0, int(H * 0.55))
            c = rng.choice([(190, 190, 215), (140, 140, 170), (220, 220, 240)])
            bg.set_at((x, y), c)
        # moon + glow
        mx, my, mr = int(W * 0.84), int(H * 0.28), 13
        glow = pygame.Surface((mr * 6, mr * 6), pygame.SRCALPHA)
        for gr, ga in ((mr * 3, 14), (mr * 2, 22), (int(mr * 1.4), 30)):
            pygame.draw.circle(glow, (225, 220, 190, ga), (mr * 3, mr * 3), gr)
        bg.blit(glow, (mx - mr * 3, my - mr * 3))
        pygame.draw.circle(bg, (232, 228, 205), (mx, my), mr)
        for _ in range(5):
            a, d = rng.uniform(0, math.tau), rng.uniform(0, mr * 0.6)
            pygame.draw.circle(bg, (206, 200, 176),
                               (int(mx + math.cos(a) * d), int(my + math.sin(a) * d)),
                               rng.randint(1, 3))
        # far ridge
        ridge = []
        y = self.ground_y - 34
        for x in range(0, W + 16, 16):
            y = max(self.ground_y - 52, min(self.ground_y - 18,
                    y + rng.randint(-7, 7)))
            ridge.append((x, y))
        pygame.draw.polygon(bg, (18, 16, 34),
                            [(0, H)] + ridge + [(W + 16, H)])
        # crooked tree silhouettes
        x = rng.randint(6, 30)
        while x < W:
            self._tree(bg, rng, x, self.ground_y, rng.randint(32, 62))
            x += rng.randint(30, 58)
        # near shrub silhouettes
        for _ in range(W // 26):
            bx = rng.randint(0, W - 1)
            br = rng.randint(2, 6)
            pygame.draw.circle(bg, (25, 21, 40), (bx, self.ground_y - 1), br)
        return bg

    def _tree(self, bg, rng, x, base_y, height):
        c = (13, 11, 24)
        y, cx = base_y, float(x)
        step = 6
        for _ in range(height // step):
            nx = cx + rng.uniform(-2.2, 2.2)
            pygame.draw.line(bg, c, (int(cx), y), (int(nx), y - step), 2)
            if rng.random() < 0.5 and y < base_y - 14:
                bx = rng.choice((-1, 1)) * rng.randint(6, 14)
                pygame.draw.line(bg, c, (int(nx), y - step),
                                 (int(nx + bx), y - step - rng.randint(2, 8)), 1)
            cx, y = nx, y - step

    def _render_ground(self, rng):
        W, GH = config.VIEW_W, config.GROUND_H
        g = pygame.Surface((W, GH))
        x = 0
        while x < W:                                   # grass/sand/dirt patches
            seg = rng.randint(24, 64)
            kind = rng.choices(["grass", "sand", "dirt"], [5, 3, 2])[0]
            for px_ in range(x, min(x + seg, W)):
                if kind == "grass":
                    c1, c2 = (44, 74, 42), (58, 90, 48)
                elif kind == "sand":
                    c1, c2 = (150, 132, 88), (168, 150, 104)
                else:
                    c1, c2 = (86, 64, 44), (100, 76, 52)
                g.set_at((px_, 0), rng.choice((c1, c2)))
                g.set_at((px_, 1), rng.choice((c1, c2)))
                if kind == "grass" and rng.random() < 0.12:
                    g.set_at((px_, 0), (30, 56, 32))
            x += seg
        for y in range(2, GH):                         # dirt body
            k = (y - 2) / (GH - 2)
            c = (int(52 - 16 * k), int(40 - 12 * k), int(30 - 8 * k))
            g.fill(c, (0, y, W, 1))
        for _ in range(W // 3):                        # pebbles, roots, bones
            px_, py_ = rng.randint(0, W - 1), rng.randint(3, GH - 1)
            r = rng.random()
            if r < 0.5:
                g.set_at((px_, py_), (70, 60, 52))
            elif r < 0.85:
                g.set_at((px_, py_), (34, 26, 20))
            else:
                g.set_at((px_, py_), (180, 174, 158))
        return g

    def _render_fog(self, rng):
        W = config.VIEW_W
        f = pygame.Surface((W * 2, 26), pygame.SRCALPHA)
        for _ in range(W // 8):
            x, y = rng.randint(0, W * 2), rng.randint(4, 22)
            rw, rh = rng.randint(16, 60), rng.randint(3, 7)
            a = rng.randint(6, 13)
            pygame.draw.ellipse(f, (195, 198, 218, a), (x, y, rw, rh))
        return f

    # ---------------------------------------------------------------- runtime
    def update(self, dt, progress_pct, px):
        self.t += dt
        W = config.VIEW_W
        target = W * progress_pct / 100.0
        self.reveal_x += (target - self.reveal_x) * min(1.0, dt * 2.5)
        if self.reveal_x < W - 2:
            for _ in range(2):
                fx.curtain(px, self.reveal_x)
        for p in self.props:
            if not p["shown"] and p["x"] + p["surf"].get_width() * 0.5 < self.reveal_x:
                p["shown"] = True
                fx.materialize(px, p["x"] + p["surf"].get_width() // 2,
                               self.ground_y, p["surf"].get_height())
        for pl in self.platforms:
            if not pl["shown"] and pl["rect"].right < self.reveal_x:
                pl["shown"] = True
                fx.materialize(px, pl["rect"].centerx, pl["rect"].bottom + 4, 8)
        # ambient: lantern flickers and stray wisps
        if random.random() < dt * 2.0:
            shown_lanterns = [p for p in self.props
                              if p["shown"] and p["name"] == "lantern"]
            if shown_lanterns:
                p = random.choice(shown_lanterns)
                px.add(p["x"] + 2, p["y"] + 3, random.uniform(-3, 3), -8,
                       0.5, (242, 222, 132), 1)
        if random.random() < dt * 0.5:
            px.add(random.uniform(10, max(11, self.reveal_x - 10)),
                   random.uniform(20, self.ground_y - 6),
                   random.uniform(-6, 6), random.uniform(-4, -1),
                   random.uniform(1.5, 3.0), (84, 222, 200), 1, 0.0, False)

    def regen_platforms(self):
        """Fresh sky layout each time the player rises again; platforms inside
        the already-revealed region appear instantly, the rest materialize as
        the frontier reaches them."""
        self.platforms = self._gen_platforms(random.Random())
        for pl in self.platforms:
            pl["shown"] = pl["rect"].right < self.reveal_x
        return [pl for pl in self.platforms if pl["shown"]]

    def solid_platforms(self):
        return [p["rect"] for p in self.platforms if p["shown"]]

    # ---------------------------------------------------------------- drawing
    def draw_bg(self, surf):
        surf.blit(self.bg, (0, 0))
        for ex, ey, phase, speed in self.eyes:          # blinking watchers
            k = 0.5 + 0.5 * math.sin(self.t * speed + phase)
            if k < 0.35:
                continue
            c = (int(60 * k), int(220 * k), int(190 * k))
            surf.set_at((ex, ey), c)
            surf.set_at((ex + 3, ey), c)
        off = int(self.t * 7) % config.VIEW_W
        surf.blit(self.fog, (-off, self.ground_y - 30))
        surf.blit(self.fog, (config.VIEW_W - off, self.ground_y - 30))

    def draw_world(self, surf):
        surf.blit(self.ground, (0, self.ground_y))
        for p in self.props:
            if p["shown"]:
                surf.blit(p["surf"], (p["x"], p["y"]))
        for pl in self.platforms:
            if pl["shown"]:
                surf.blit(pl["surf"], pl["rect"].topleft)
        self._draw_door(surf)

    def _draw_door(self, surf):
        r = self.door_rect
        if self.reveal_x < r.left - 4:
            return
        pygame.draw.rect(surf, (34, 28, 46), r.inflate(6, 4).move(0, 2))
        if self.door_open:
            pulse = 0.75 + 0.25 * math.sin(self.t * 4)
            inner = (int(240 * pulse), int(200 * pulse), int(120 * pulse))
            pygame.draw.rect(surf, inner, r)
            pygame.draw.rect(surf, (255, 240, 190),
                             (r.x + 3, r.y + 4, r.w - 6, r.h - 4), 1)
        else:
            pygame.draw.rect(surf, (52, 38, 26), r)
            for i in range(1, 4):
                pygame.draw.line(surf, (38, 28, 20),
                                 (r.x + i * r.w // 4, r.y),
                                 (r.x + i * r.w // 4, r.bottom))
        pygame.draw.rect(surf, (90, 84, 100), r.inflate(4, 2).move(0, 1), 2)
        pygame.draw.circle(surf, (90, 84, 100), (r.centerx, r.y - 1), r.w // 2 + 2,
                           2, draw_top_left=True, draw_top_right=True)

    def draw_front(self, surf):
        off = int(self.t * 11) % config.VIEW_W
        surf.blit(self.fog, (-off - 30, self.ground_y - 14))
        surf.blit(self.fog, (config.VIEW_W - off - 30, self.ground_y - 14))

    def draw_dark(self, surf):
        """Right of the frontier the world is unbuilt: a ghostly blue limbo
        where faint shapes wait to materialize."""
        W, H = config.VIEW_W, config.VIEW_H
        rx = int(self.reveal_x)
        if rx >= W:
            return
        fade = 22
        ghost = (8, 10, 26)
        veil = pygame.Surface((min(fade, W - rx), H), pygame.SRCALPHA)
        for i in range(veil.get_width()):
            veil.fill((*ghost, int(234 * (i + 1) / fade)), (i, 0, 1, H))
        surf.blit(veil, (rx, 0))
        if rx + fade < W:
            body = pygame.Surface((W - rx - fade, H), pygame.SRCALPHA)
            body.fill((*ghost, 234))
            surf.blit(body, (rx + fade, 0))
        # stray spirit motes drifting in the unbuilt zone
        if random.random() < 0.3:
            mx = random.randint(min(rx + 4, W - 1), W - 1)
            my = random.randint(4, H - 4)
            surf.set_at((mx, my), (90, 140, 200))
