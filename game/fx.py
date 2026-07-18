"""Tiny particle system + canned emitters for all the spooky-magical effects."""
import math
import random

import pygame

from . import config


class Particles:
    __slots__ = ("ps",)

    def __init__(self):
        self.ps = []

    def add(self, x, y, vx, vy, life, color, size=1, grav=0.0, glow=False):
        self.ps.append([x, y, vx, vy, life, life, color, size, grav, glow])

    def update(self, dt):
        alive = []
        for p in self.ps:
            p[4] -= dt
            if p[4] <= 0:
                continue
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += p[8] * dt
            alive.append(p)
        self.ps = alive

    def draw(self, surf):
        for x, y, _vx, _vy, life, life0, color, size, _g, glow in self.ps:
            k = max(0.0, min(1.0, life / life0))
            c = (int(color[0] * k), int(color[1] * k), int(color[2] * k))
            ix, iy = int(x), int(y)
            if glow and size > 1:
                pygame.draw.circle(surf, c, (ix, iy), size)
            elif size <= 1:
                if 0 <= ix < config.VIEW_W and 0 <= iy < config.VIEW_H:
                    surf.set_at((ix, iy), c)
            else:
                pygame.draw.rect(surf, c, (ix, iy, size, size))


MAGIC_COLORS = [(150, 90, 220), (90, 220, 200), (200, 140, 255), (120, 240, 180)]
BONE_COLORS = [(222, 218, 200), (168, 162, 148), (120, 116, 104)]
DIRT_COLORS = [(74, 56, 40), (96, 76, 50), (56, 44, 34)]
EMBER_COLORS = [(217, 119, 87), (240, 170, 90), (255, 210, 120)]


def burst(px, x, y, colors, n=12, speed=60, life=0.5, grav=140.0, size=1):
    for _ in range(n):
        a = random.uniform(0, math.tau)
        s = random.uniform(0.3, 1.0) * speed
        px.add(x, y, math.cos(a) * s, math.sin(a) * s - speed * 0.3,
               random.uniform(0.5, 1.2) * life, random.choice(colors), size, grav)


def bone_burst(px, x, y):
    burst(px, x, y, BONE_COLORS, n=16, speed=75, life=0.6, grav=220.0)


def dirt_burst(px, x, y):
    burst(px, x, y, DIRT_COLORS, n=10, speed=45, life=0.45, grav=260.0)


def magic_burst(px, x, y, n=14):
    burst(px, x, y, MAGIC_COLORS, n=n, speed=55, life=0.7, grav=-15.0)


def materialize(px, x, y, h):
    """Sparkles when a piece of the world builds itself in."""
    for _ in range(10):
        px.add(x + random.uniform(-4, 4), y - random.uniform(0, h),
               random.uniform(-8, 8), random.uniform(-24, -6),
               random.uniform(0.4, 0.9), random.choice(MAGIC_COLORS), 1, -10.0)


def curtain(px, x):
    """Continuous shimmer along the world-build frontier."""
    y = random.uniform(4, config.VIEW_H - 4)
    px.add(x + random.uniform(-2, 2), y, random.uniform(-14, -4),
           random.uniform(-10, 10), random.uniform(0.4, 1.1),
           random.choice(MAGIC_COLORS), 1, 0.0)


def portal_swirl(px, x, y, r=10):
    a = random.uniform(0, math.tau)
    px.add(x + math.cos(a) * r, y + math.sin(a) * r * 0.6,
           -math.cos(a) * 18, -math.sin(a) * 12,
           random.uniform(0.3, 0.7),
           random.choice([(217, 119, 87), (150, 90, 220), (255, 200, 150)]), 1)


def slash_arc(px, x, y, facing):
    for i in range(7):
        a = -1.1 + i * 0.36
        px.add(x + math.cos(a) * 12 * facing, y + math.sin(a) * 10,
               facing * 40, math.sin(a) * 20, 0.14, (230, 235, 245), 1)
