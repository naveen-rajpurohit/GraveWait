"""GraveWait — a graveyard side-scroller that doubles as a Claude Code loading
screen. Launched (detached) by hooks/emit_event.py on every prompt; reads hook
events from an append-only log and turns them into world-building progress."""
import atexit
import os
import random
import sys
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import win32api
import win32con
import win32gui

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import (audio, claude_npc, config, demo, enemies, events, fx, paths,
                  player, progress, save, sprites, ui, world)

TITLE, PLAY, DEAD, WIN = range(4)
QUIT_HOLD_SECONDS = 1.2


def acquire_lock(notify=False):
    paths.ensure_dirs()
    try:
        pid = int(open(paths.LOCK_FILE).read().strip())
        if pid != os.getpid() and _pid_alive(pid):
            if notify:                       # user double-clicked the shortcut
                _msgbox("GraveWait is already running along the bottom of "
                        "your screen.")
            sys.exit(0)                      # another instance owns the strip
    except (OSError, ValueError):
        pass
    with open(paths.LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    atexit.register(_release_lock)


def _msgbox(text, title="GraveWait"):
    import ctypes
    try:
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)
    except Exception:
        print(text)


def _release_lock():
    try:
        os.remove(paths.LOCK_FILE)
    except OSError:
        pass


def _pid_alive(pid):
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)    # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    ok = k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return bool(ok) and code.value == 259    # STILL_ACTIVE


def make_window():
    """Borderless strip along the bottom of the work area, always on top,
    and — crucially — without stealing keyboard focus from the terminal."""
    prev = win32gui.GetForegroundWindow()
    try:
        l, t, r, b = win32api.SystemParametersInfo(win32con.SPI_GETWORKAREA)
    except Exception:
        l, t = 0, 0
        r = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        b = win32api.GetSystemMetrics(win32con.SM_CYSCREEN) - 48
    w = (r - l) - (r - l) % config.SCALE
    h = int((b - t) * config.STRIP_FRACTION)
    h -= h % config.SCALE
    os.environ["SDL_VIDEO_WINDOW_POS"] = f"{l},{b - h}"
    screen = pygame.display.set_mode((w, h), pygame.NOFRAME)
    pygame.display.set_caption("GraveWait")
    try:
        hwnd = pygame.display.get_wm_info()["window"]
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE |
                              win32con.SWP_NOACTIVATE)
        if prev:
            win32gui.SetForegroundWindow(prev)
    except Exception:
        pass                                  # focus-return is best-effort
    return screen, w, h


class Game:
    def __init__(self, screen, w, h, demo_mode=False):
        self.screen = screen
        self.win_size = (w, h)
        config.init(w, h)
        sprites.build()
        sprites.load_pack()
        ui.init()
        self.frame = pygame.Surface((config.VIEW_W, config.VIEW_H))
        self.audio = audio.Audio()
        self.save = save.Save()
        self.tail = demo.DemoDriver() if demo_mode else events.EventTail()
        self.px = fx.Particles()
        self.progress = progress.Progress()
        self.world = world.World(seed=random.random())
        self.player = player.Player(self.world)
        self.enemies = []
        self.projectiles = []
        self.bolts = []
        self.npc = None
        self.spawner = enemies.Spawner()
        self.scene = TITLE
        self.session = ""
        self.mode = self.save.mode          # easy | hard, picked on the title
        self.score = 0
        self.last_score = 0
        self.quest = ""
        self.status_text = "waiting for a prompt..."
        self.last_tool = ""
        self.last_tool_t = 0.0
        self.toasts = []
        self.quit_requested = False
        self.q_held = 0.0
        self.poll_timer = 0.0
        self.door_announced = False
        self.exited_this_run = False
        self.audio.start_music()

    # -------------------------------------------------------------- hook events
    def route_events(self, now):
        for ev in self.tail.poll():
            sid = ev.get("session_id", "")
            kind = ev.get("event")
            if kind == "prompt_start":
                self.session = sid
                self.new_run(ev.get("prompt", ""), now)
                continue
            if sid and self.session and sid != self.session:
                continue                     # a different Claude session's noise
            if kind == "tool_done":
                self.progress.on_tool(now)
                self.last_tool = ev.get("tool", "")
                self.last_tool_t = now
                if self.npc:
                    self.npc.resolve()
            elif kind == "notification":
                self.on_notification(ev.get("message", ""))
            elif kind == "stop":
                self.progress.on_stop(now)
                if self.npc:
                    self.npc.resolve()

    def new_run(self, prompt, now):
        if self.score > 0:
            self.save.bank_score(self.score)
        self.score = 0
        self.progress.start_run(now)
        self.world = world.World(seed=random.random())
        self.enemies = []
        self.projectiles = []
        self.bolts = []
        self.npc = None
        self.spawner = enemies.Spawner()
        self.spawner.reset_ramp(now)
        self.door_announced = False
        self.exited_this_run = False
        self.quest = (prompt or "").replace("\n", " ").strip()[:70]
        self.toast("A NEW TASK BEGINS...", now, ui.ORANGE)
        keep_playing = self.scene == PLAY and self.player.alive
        self.player = player.Player(self.world)
        if not keep_playing:
            self.scene = TITLE

    def on_notification(self, message, now=None):
        now = now or time.time()
        if self.npc and not self.npc.gone:
            self.npc.set_message(message)
        else:
            self.npc = claude_npc.ClaudeNPC(message, self.world,
                                            self.player.x, self.px)
            self.audio.sfx("portal")
        self.toast("CLAUDE NEEDS YOU!", now, ui.ORANGE)

    def toast(self, msg, now, color=ui.INK):
        self.toasts = [t for t in self.toasts if t[1] > now][-2:]
        self.toasts.append((msg, now + 2.5, color))

    # ------------------------------------------------------------------- input
    def handle_key(self, key, now):
        if self.scene == TITLE and key in (pygame.K_a, pygame.K_d,
                                           pygame.K_LEFT, pygame.K_RIGHT):
            self.mode = "hard" if self.mode == "easy" else "easy"
            self.save.mode = self.mode
            self.save.write()
            self.audio.sfx("jump", 0.4)
        elif self.scene == TITLE and key == pygame.K_SPACE:
            self.scene = PLAY
            self.spawner.reset_ramp(now)
            self.audio.sfx("jump")
        elif self.scene == PLAY:
            if key == pygame.K_w:
                self.player.try_jump(self.px)
                self.audio.sfx("jump", 0.5)
            elif key == pygame.K_SPACE:
                if self.player.try_dash(self.px):
                    self.audio.sfx("dash")
            elif key == pygame.K_l:
                self.player.try_attack(self.px)
                self.audio.sfx("swing")
            elif key == pygame.K_p:
                bolt = self.player.try_magic(self.magic_unlocked, self.px)
                if bolt:
                    self.bolts.append(bolt)
                    self.audio.sfx("magic")
            elif key == pygame.K_RETURN:
                self.interact()
        elif self.scene == DEAD and key == pygame.K_SPACE:
            self.respawn(now)
        elif self.scene == WIN and key == pygame.K_SPACE:
            self.scene = PLAY
        if key == pygame.K_m:
            self.audio.toggle_mute()
            self.toast("MUTED" if self.audio.muted else "SOUND ON", now, ui.DIM)

    def interact(self):
        if (self.npc and self.npc.present and
                abs(self.npc.x - self.player.x) < 40):
            self.npc.dialogue_open = not self.npc.dialogue_open
        else:
            self.try_exit_door()

    def try_exit_door(self):
        if (self.world.door_open and
                self.player.hitbox.colliderect(self.world.door_rect.inflate(8, 4))):
            if not self.exited_this_run:
                self.exited_this_run = True
                self.save.wins += 1
                self.save.bank_score(self.score)
            self.scene = WIN
            self.audio.sfx("win")

    def respawn(self, now):
        self.last_score = self.score
        self.score = 0
        self.player = player.Player(self.world)
        self.enemies = []
        self.projectiles = []
        self.bolts = []
        # the graveyard rearranges its sky while you were dead
        for pl in self.world.regen_platforms():
            fx.materialize(self.px, pl["rect"].centerx, pl["rect"].bottom + 4, 8)
        self.spawner.reset_ramp(now)
        self.scene = PLAY

    @property
    def magic_unlocked(self):
        return self.progress.value >= config.MAGIC_UNLOCK_PCT

    # ------------------------------------------------------------------ update
    def update(self, dt, now):
        # long-press Q to quit: a stray tap next to W must not kill the run
        if pygame.key.get_pressed()[pygame.K_q]:
            self.q_held += dt
            if self.q_held >= QUIT_HOLD_SECONDS:
                self.quit_requested = True
        else:
            self.q_held = 0.0
        self.poll_timer -= dt
        if self.poll_timer <= 0:
            self.poll_timer = 0.15
            self.route_events(now)

        was_locked = not self.magic_unlocked
        self.progress.update(dt, now)
        if was_locked and self.magic_unlocked and self.progress.status != "idle":
            self.toast("MAGIC UNLOCKED (P)", now, (84, 222, 200))
            self.audio.sfx("unlock")
        self.world.update(dt, self.progress.value, self.px)
        if self.progress.done and not self.door_announced:
            self.door_announced = True
            self.world.door_open = True
            self.toast("THE WAY OUT HAS OPENED!", now, ui.GOLD)
            self.audio.sfx("door")
            fx.magic_burst(self.px, self.world.door_rect.centerx,
                           self.world.door_rect.centery, n=20)
        self.px.update(dt)
        if self.npc:
            self.npc.update(dt, self)
            self.npc.shimmer(self.px)
            if self.npc.gone:
                self.npc = None
        self.update_status(now)
        if self.scene != PLAY:
            return

        self.player.update(dt, pygame.key.get_pressed(), self.px)
        self.spawner.update(dt, now, self)

        for e in self.enemies:
            prev_state = e.state
            e.update(dt, self)
            if prev_state == "rise" and e.state == "walk":
                self.audio.sfx("rise", 0.4)
        self.combat()
        self.enemies = [e for e in self.enemies if not e.dead]

        for pr in self.projectiles:
            pr.update(dt, self.px, self.player)
        for b in self.bolts:
            b.update(dt, self.px)
        self.projectiles = [p for p in self.projectiles if self.keep_proj(p)]
        self.bolts = [b for b in self.bolts
                      if b.life > 0 and 0 < b.x < config.VIEW_W]

        if not self.player.alive:
            self.last_score = self.score
            self.save.bank_score(self.score)
            self.score = 0
            self.scene = DEAD
            self.audio.sfx("lose")

    def keep_proj(self, p):
        if p.life <= 0 or not (0 < p.x < config.VIEW_W):
            return False
        if p.y > self.world.ground_y - 1:
            fx.dirt_burst(self.px, p.x, self.world.ground_y)
            return False
        if self.npc and self.npc.shield_active and not p.reflected:
            cx, cy = self.npc.shield_center
            if ((p.x - cx) ** 2 + (p.y - cy) ** 2 <
                    self.npc.shield_radius ** 2):
                fx.magic_burst(self.px, p.x, p.y, n=5)
                return False
        return True

    def combat(self):
        hb = self.player.attack_hitbox
        dashing = self.player.dashing
        for e in self.enemies:
            if e.dead or e.dying or e.state == "rise":
                continue
            if hb and e.last_hit_attack != self.player.attack_id \
                    and hb.colliderect(e.rect):
                e.last_hit_attack = self.player.attack_id
                if e.take_hit(config.ATTACK_DMG, self.px):
                    self.on_kill(e)
                continue
            if dashing and e.id not in self.player.dash_hits \
                    and e.rect.colliderect(self.player.hitbox.inflate(6, 0)):
                self.player.dash_hits.add(e.id)
                if e.take_hit(config.DASH_DMG, self.px):
                    self.on_kill(e)
                continue
            if e.hit_cd <= 0 and e.stun <= 0 \
                    and e.rect.colliderect(self.player.hitbox):
                if self.player.take_hit(e.dmg, e.x, self.px):
                    e.hit_cd = config.ENEMY_HIT_COOLDOWN
                    self.audio.sfx("hurt")
        for b in self.bolts:
            for e in self.enemies:
                if e.dead or e.dying or e.state == "rise" or e.id in b.hit_ids:
                    continue
                if b.rect.colliderect(e.rect):
                    b.hit_ids.add(e.id)
                    if e.take_hit(b.dmg, self.px):
                        self.on_kill(e)
        # the parry box is taller than the sword's damage box (dive-bombing
        # shots are deflectable) but only guards the player's FRONT — anything
        # hitting the back lands, swing or no swing
        parry = None
        if hb:
            pl = self.player
            pw = pl.W // 2 + config.ATTACK_RANGE + 4
            px0 = (int(pl.x + pl.W / 2) if pl.facing > 0
                   else int(pl.x + pl.W / 2) - pw)
            parry = pygame.Rect(px0, int(pl.y) - 8, pw, pl.H + 14)
        for p in self.projectiles:
            # a well-timed swing bats a frontal shot right back at them
            if (not p.reflected and parry and parry.colliderect(p.rect)
                    and p.vx * self.player.facing <= 20):
                p.reflect()
                fx.burst(self.px, p.x, p.y, [(255, 220, 150), (230, 235, 245)],
                         n=6, speed=45, life=0.3)
                self.audio.sfx("deflect")
                continue
            # magic against magic: mutual annihilation
            if not p.reflected:
                for b in self.bolts:
                    if b.life > 0 and b.rect.colliderect(p.rect):
                        p.life = 0
                        b.life = 0
                        fx.magic_burst(self.px, p.x, p.y, n=10)
                        self.audio.sfx("deflect", 0.6)
                        break
                if p.life <= 0:
                    continue
            if p.reflected:
                for e in self.enemies:
                    if e.dead or e.dying or e.state == "rise":
                        continue
                    if p.rect.colliderect(e.rect):
                        p.life = 0
                        if e.take_hit(p.dmg, self.px):
                            self.on_kill(e)
                        break
            elif p.rect.colliderect(self.player.hitbox):
                if self.player.take_hit(p.dmg, p.x - p.vx, self.px):
                    p.life = 0
                    self.audio.sfx("hurt")

    def on_kill(self, e):
        self.score += 1
        self.save.total_kills += 1
        self.audio.sfx("bones", 0.7)

    def on_npc_kill(self, e):
        """Claude's kills are freebies — they still count for the player."""
        self.on_kill(e)

    def update_status(self, now):
        st = self.progress.status
        if self.npc and not self.npc.resolved and st != "done":
            self.status_text = "claude needs you - find the ghostly messenger"
        elif st == "idle":
            self.status_text = "waiting for a prompt..."
        elif st == "running":
            if now - self.last_tool_t < 4.0 and self.last_tool:
                self.status_text = f"claude used {self.last_tool}"
            else:
                self.status_text = "claude is thinking..."
        elif st == "finishing":
            self.status_text = "wrapping up..."
        else:
            self.status_text = "task complete - the door is open"

    # -------------------------------------------------------------------- draw
    def draw(self, now):
        f = self.frame
        self.world.draw_bg(f)
        self.world.draw_world(f)
        if self.world.door_open:
            ui.door_hint(f, self.world, now)
        for e in self.enemies:
            e.draw(f, self.world.ground_y)
        if self.npc:
            self.npc.draw(f)
        if self.scene in (PLAY, WIN):
            self.player.draw(f)
        for pr in self.projectiles:
            pr.draw(f)
        for b in self.bolts:
            b.draw(f)
        if self.npc:
            self.npc.draw_shield(f)
        self.px.draw(f)
        self.world.draw_front(f)
        self.world.draw_dark(f)
        ui.hud(f, self)
        ui.toasts(f, self, now)
        if self.npc and self.npc.present and not self.npc.dialogue_open:
            ui.npc_hint(f, self.npc, now)
        if self.npc and self.npc.dialogue_open:
            ui.dialogue_cloud(f, self.npc)
        if self.scene == TITLE:
            ui.title_overlay(f, self, now)
            ui.controls_hint(f)          # controls only on the start screen
        elif self.scene == DEAD:
            ui.dead_overlay(f, self, now)
        elif self.scene == WIN:
            ui.win_overlay(f, self, now)
        ui.quit_bar(f, self.q_held / QUIT_HOLD_SECONDS)
        f.fill((86, 76, 110), (0, 0, config.VIEW_W, 1))            # thin frame
        f.fill((86, 76, 110), (0, config.VIEW_H - 1, config.VIEW_W, 1))
        pygame.transform.scale(f, self.win_size, self.screen)
        pygame.display.flip()


def main():
    if "--install-hooks" in sys.argv or "--uninstall-hooks" in sys.argv:
        import install_hooks
        try:
            if "--install-hooks" in sys.argv:
                install_hooks.install()
                _msgbox("GraveWait is attached to Claude Code.\n\nEvery prompt "
                        "you send now raises the graveyard along the bottom of "
                        "your screen. New Claude Code sessions pick it up "
                        "automatically.")
            else:
                install_hooks.uninstall()
                _msgbox("GraveWait is detached from Claude Code.")
        except Exception as exc:
            _msgbox(f"GraveWait could not update Claude Code settings:\n{exc}")
        return
    demo_mode = "--play" in sys.argv or "--demo" in sys.argv
    # true per-monitor DPI awareness: exact physical pixels, no OS blur-scaling
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    acquire_lock(notify=demo_mode)
    pygame.init()
    screen, w, h = make_window()
    game = Game(screen, w, h, demo_mode=demo_mode)
    clock = pygame.time.Clock()
    running = True
    while running:
        dt = min(clock.tick(config.FPS) / 1000.0, 0.05)
        now = time.time()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                game.handle_key(ev.key, now)
        if game.quit_requested:
            running = False
        game.update(dt, now)
        game.draw(now)
    game.save.write()
    pygame.quit()


if __name__ == "__main__":
    main()
