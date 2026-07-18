"""HUD, overlays, toasts, and the Claude dialogue cloud. Fonts render at
internal resolution and get chunky when the frame is scaled up — intended."""
import math

import pygame

from . import config

F_SMALL = F_MED = F_BIG = F_HUGE = None

INK = (235, 230, 218)
DIM = (150, 145, 160)
ORANGE = (217, 119, 87)
RED = (220, 60, 50)
GOLD = (242, 222, 132)


def init():
    global F_SMALL, F_MED, F_BIG, F_HUGE
    F_SMALL = pygame.font.SysFont("consolas", 10)
    F_MED = pygame.font.SysFont("consolas", 12, bold=True)
    F_BIG = pygame.font.SysFont("consolas", 18, bold=True)
    F_HUGE = pygame.font.SysFont("consolas", 26, bold=True)


def text(surf, s, pos, color=INK, font=None, anchor="topleft", shadow=True):
    font = font or F_SMALL
    img = font.render(s, False, color)
    r = img.get_rect(**{anchor: pos})
    if shadow:
        sh = font.render(s, False, (10, 8, 16))
        surf.blit(sh, r.move(1, 1))
    surf.blit(img, r)
    return r


def wrap(s, font, max_w):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.size(t)[0] <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _sword_bar(surf, x, y, length, pct):
    """Progress meter shaped like a sword lying on its side, filling with gold."""
    blade_h = 5
    tip = 8
    # crossguard + grip at the left
    pygame.draw.rect(surf, (150, 120, 52), (x, y - 2, 2, blade_h + 4))
    pygame.draw.rect(surf, (94, 66, 40), (x - 7, y + 1, 7, 3))
    pygame.draw.circle(surf, (150, 120, 52), (x - 8, y + 2), 2)
    # blade outline
    bx = x + 3
    bw = length - tip
    pygame.draw.rect(surf, (44, 42, 58), (bx, y, bw, blade_h))
    pygame.draw.polygon(surf, (44, 42, 58),
                        [(bx + bw, y), (bx + bw + tip, y + blade_h // 2),
                         (bx + bw, y + blade_h - 1)])
    # golden fill by progress
    fill = int((length - 1) * max(0.0, min(1.0, pct / 100.0)))
    if fill > 0:
        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(bx, y - 1, fill, blade_h + 2))
        pygame.draw.rect(surf, (222, 178, 84), (bx, y, bw, blade_h))
        pygame.draw.polygon(surf, (222, 178, 84),
                            [(bx + bw, y), (bx + bw + tip, y + blade_h // 2),
                             (bx + bw, y + blade_h - 1)])
        pygame.draw.line(surf, (255, 224, 150), (bx, y + 1),
                         (bx + min(fill, bw), y + 1))
        surf.set_clip(clip)
    pygame.draw.rect(surf, (120, 116, 138), (bx, y, bw, blade_h), 1)


def hud(surf, game):
    W = config.VIEW_W
    hp = max(0, game.player.hp)
    text(surf, f"HEALTH: {hp}/{config.PLAYER_HP}", (6, 4), INK, F_MED)
    pygame.draw.rect(surf, (26, 20, 30), (6, 17, 82, 8))
    pygame.draw.rect(surf, RED, (7, 18, int(80 * hp / config.PLAYER_HP), 6))
    pygame.draw.rect(surf, (110, 104, 122), (6, 17, 82, 8), 1)
    text(surf, f"SCORE: {game.score}", (6, 28), INK, F_MED)
    # right column: records + current mode
    text(surf, f"BEST {game.save.high_score}", (W - 6, 5), DIM, F_SMALL,
         anchor="topright")
    text(surf, f"WINS {game.save.wins}", (W - 6, 16), DIM, F_SMALL,
         anchor="topright")
    if game.mode == "hard":
        text(surf, "HARD", (W - 6, 27), (222, 84, 70), F_SMALL,
             anchor="topright")
    else:
        text(surf, "EASY", (W - 6, 27), (110, 165, 110), F_SMALL,
             anchor="topright")
    # center: sword progress bar + status
    pct = game.progress.value
    text(surf, f"PROGRESS: {pct:.0f}%", (W // 2, 4), GOLD, F_MED, anchor="midtop")
    _sword_bar(surf, W // 2 - 60, 19, 120, pct)
    text(surf, game.status_text, (W // 2, 28), DIM, F_SMALL, anchor="midtop")
    if game.quest:
        text(surf, game.quest, (W // 2, 39), (110, 105, 125), F_SMALL,
             anchor="midtop")
    if not game.magic_unlocked and game.progress.status != "idle":
        text(surf, "magic @40%", (6, 40), (100, 90, 130), F_SMALL)


def toasts(surf, game, now):
    y = 44
    for msg, t_end, color in game.toasts:
        k = max(0.0, min(1.0, t_end - now))
        c = (int(color[0] * k + 10), int(color[1] * k + 8), int(color[2] * k + 16))
        text(surf, msg, (config.VIEW_W // 2, y), c, F_MED, anchor="midtop")
        y += 14


def _dim(surf, alpha=150, color=(0, 0, 0)):
    d = pygame.Surface((config.VIEW_W, config.VIEW_H), pygame.SRCALPHA)
    d.fill((*color, alpha))
    surf.blit(d, (0, 0))


def _blink(now):
    return math.sin(now * 4) > -0.3


def title_overlay(surf, game, now):
    _dim(surf, 120)
    cx = config.VIEW_W // 2
    cy = config.VIEW_H // 2
    text(surf, "G R A V E W A I T", (cx, cy - 32), ORANGE, F_HUGE, anchor="center")
    if _blink(now):
        text(surf, "PRESS SPACE TO START", (cx, cy - 2), INK, F_BIG, anchor="center")
    # mode selector, toggled with A/D
    easy_c = GOLD if game.mode == "easy" else DIM
    hard_c = GOLD if game.mode == "hard" else DIM
    text(surf, "MODE:", (cx - 52, cy + 16), DIM, F_MED, anchor="center")
    text(surf, ("> EASY <" if game.mode == "easy" else "EASY"),
         (cx - 8, cy + 16), easy_c, F_MED, anchor="center")
    text(surf, ("> HARD <" if game.mode == "hard" else "HARD"),
         (cx + 52, cy + 16), hard_c, F_MED, anchor="center")
    text(surf, "A/D changes mode", (cx, cy + 30), (96, 90, 110), F_SMALL,
         anchor="center")
    text(surf, f"wins {game.save.wins}   best {game.save.high_score}",
         (cx, cy + 42), DIM, F_SMALL, anchor="center")


def controls_hint(surf):
    """Tiny always-on reminder along the bottom: helps, never shouts."""
    text(surf,
         "A/D move  W jump2  SPACE dash  S crouch  L sword  P magic  "
         "ENTER talk  M mute  Q(hold) quit",
         (4, config.VIEW_H - 10), (96, 90, 110), F_SMALL, shadow=False)


def dead_overlay(surf, game, now):
    _dim(surf, 140, (40, 0, 0))
    cx = config.VIEW_W // 2
    cy = config.VIEW_H // 2
    text(surf, "YOU LOSE", (cx, cy - 26), RED, F_HUGE, anchor="center")
    text(surf, f"skulls {game.last_score}    high score {game.save.high_score}",
         (cx, cy + 2), INK, F_MED, anchor="center")
    if _blink(now):
        text(surf, "PRESS SPACE TO RISE AGAIN", (cx, cy + 22), INK, F_BIG,
             anchor="center")


def win_overlay(surf, game, now):
    _dim(surf, 140, (10, 20, 10))
    cx = config.VIEW_W // 2
    cy = config.VIEW_H // 2
    text(surf, "YOU ESCAPED", (cx, cy - 30), GOLD, F_HUGE, anchor="center")
    text(surf, f"skulls {game.score}    high score {game.save.high_score}",
         (cx, cy - 4), INK, F_MED, anchor="center")
    text(surf, f"wins {game.save.wins}", (cx, cy + 12), ORANGE, F_MED,
         anchor="center")
    if _blink(now):
        text(surf, "SPACE: keep fighting    hold Q: leave", (cx, cy + 30),
             DIM, F_MED, anchor="center")


def dialogue_cloud(surf, npc):
    W = config.VIEW_W
    max_w = int(W * 0.52)
    pad = 8
    cloud_bg = (240, 240, 244)
    lines = wrap(npc.message, F_SMALL, max_w - pad * 2)
    lines = lines[:7] + (["..."] if len(lines) > 7 else [])
    lh = F_SMALL.get_height()
    bw = max([F_SMALL.size(l)[0] for l in lines] + [140]) + pad * 2
    bh = lh * len(lines) + pad * 2 + 24
    bx = int(min(max(8, npc.x - bw / 2), W - bw - 8))
    by = 9
    # fluffy cloud: puffs of overlapping circles around the body
    for cx in range(bx, bx + bw + 1, 12):
        pygame.draw.circle(surf, cloud_bg, (cx, by + 2), 8)
        pygame.draw.circle(surf, cloud_bg, (min(cx + 6, bx + bw), by + bh - 2), 8)
    for cy in range(by + 4, by + bh - 3, 10):
        pygame.draw.circle(surf, cloud_bg, (bx, cy), 7)
        pygame.draw.circle(surf, cloud_bg, (bx + bw, cy), 7)
    pygame.draw.rect(surf, cloud_bg, (bx, by, bw, bh), border_radius=6)
    # trailing puffs toward the messenger
    tx = int(max(bx + 12, min(npc.x + npc.W / 2, bx + bw - 12)))
    pygame.draw.circle(surf, cloud_bg, (tx, by + bh + 7), 5)
    pygame.draw.circle(surf, cloud_bg, (tx - 3, by + bh + 13), 3)
    text(surf, "PERMISSION REQUESTED:", (bx + bw // 2, by + 2), (150, 60, 30),
         F_SMALL, anchor="midtop", shadow=False)
    y = by + 14
    for l in lines:
        img = F_SMALL.render(l, False, (36, 34, 40))
        surf.blit(img, (img.get_rect(midtop=(bx + bw // 2, y))))
        y += lh
    text(surf, "[ANSWER IN TERMINAL - ENTER CLOSES]",
         (bx + bw // 2, by + bh - 12), (110, 105, 115), F_SMALL,
         anchor="midtop", shadow=False)


def quit_bar(surf, frac):
    if frac <= 0:
        return
    W = config.VIEW_W
    pygame.draw.rect(surf, (26, 20, 30), (W - 66, config.VIEW_H - 12, 60, 6))
    pygame.draw.rect(surf, RED, (W - 65, config.VIEW_H - 11,
                                 int(58 * min(1.0, frac)), 4))
    text(surf, "quitting...", (W - 66, config.VIEW_H - 22), DIM, F_SMALL)


def npc_hint(surf, npc, now):
    if _blink(now):
        text(surf, "ENTER", (int(npc.x + npc.W / 2), int(npc.y) - 10), ORANGE,
             F_SMALL, anchor="midbottom")


def door_hint(surf, world, now):
    if _blink(now):
        r = world.door_rect
        text(surf, "ENTER", (r.centerx, r.y - 4), GOLD, F_SMALL,
             anchor="midbottom")


