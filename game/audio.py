"""Procedurally synthesized audio, no assets needed.

The music loop is an ORIGINAL bouncy minor-key chiptune in the spirit of
playful-spooky Halloween tunes (plinky xylophone 'bones', staccato bass,
ghostly organ pads). WAVs are synthesized once and cached in APP_DIR/audio.
Everything degrades to silent no-ops if the mixer can't start."""
import array
import math
import os
import random
import wave

import pygame

from . import paths

SR = 22050
_VER = "v2"

# note frequencies
D2, E2, A2, B2 = 73.42, 82.41, 110.0, 123.47
E3, G3, A3, B3 = 164.81, 196.0, 220.0, 246.94
C4, D4, E4, F4s, G4, A4, B4 = 261.63, 293.66, 329.63, 369.99, 392.0, 440.0, 493.88
C5, D5, E5, D5s = 523.25, 587.33, 659.25, 622.25


def _mix(buf, samples, at):
    at = int(at)
    for i, s in enumerate(samples):
        j = at + i
        if 0 <= j < len(buf):
            buf[j] += s


def _tone(freq, dur, wave_kind="sine", vol=0.5, decay=4.0, harm=0.0):
    n = int(dur * SR)
    out = []
    ph = 0.0
    step = freq / SR
    for i in range(n):
        t = i / n
        env = math.exp(-decay * t)
        ph += step
        x = ph % 1.0
        if wave_kind == "square":
            v = 0.7 if x < 0.5 else -0.7
        elif wave_kind == "tri":
            v = 4 * abs(x - 0.5) - 1
        elif wave_kind == "noise":
            v = random.uniform(-1, 1)
        else:
            v = math.sin(math.tau * x)
            if harm:
                v += harm * math.sin(3 * math.tau * x) * math.exp(-8 * t)
        out.append(v * env * vol)
    return out


def _pluck(freq, dur=0.22, vol=0.55):
    """Xylophone-ish bone plink: bright sine + fast-decaying 3rd harmonic."""
    return _tone(freq, dur, "sine", vol, decay=9.0, harm=0.6)


def _sweep(f0, f1, dur, wave_kind="sine", vol=0.4, decay=3.0):
    n = int(dur * SR)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / n
        f = f0 + (f1 - f0) * t
        ph += f / SR
        env = math.exp(-decay * t)
        x = ph % 1.0
        v = math.sin(math.tau * x) if wave_kind == "sine" else (
            0.6 if x < 0.5 else -0.6)
        out.append(v * env * vol)
    return out


def _rattle(hits=3, vol=0.3):
    out = []
    for h in range(hits):
        out += _tone(random.uniform(2000, 3200), 0.03, "noise", vol, decay=6)
        out += [0.0] * int(0.025 * SR)
    return out


def _write(path, buf):
    pcm = array.array("h", (max(-32000, min(32000, int(s * 32000))) for s in buf))
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())


def _synth_music():
    """Original bouncy graveyard bop: swung eighths, plinky xylophone-bone
    lead, walking staccato bass, offbeat organ stabs and rattling bones —
    the 'Spooky Scary Skeletons' FEEL without its melody."""
    bpm = 150
    beat = 60.0 / bpm
    swing = 0.58                       # offbeats land late: the bounce
    bars = 8
    total = bars * 4 * beat
    buf = [0.0] * int(total * SR)

    def put(samples, bar, e8):         # e8: eighth index 0..7 within the bar
        q, off = divmod(e8, 2)
        _mix(buf, samples, (bar * 4 + q + (swing if off else 0)) * beat * SR)

    R = None
    melody = [
        [E5, R, B4, R, G4, R, B4, R],
        [E5, R, B4, R, G4, B4, A4, G4],
        [F4s, R, A4, R, D5, R, A4, R],
        [D5, C5, B4, A4, G4, R, F4s, R],
        [E5, R, B4, R, G4, R, B4, R],
        [C5, R, E5, R, A4, R, C5, R],
        [B4, A4, G4, F4s, G4, A4, B4, C5],
        [B4, R, E4, R, R, R, R, R],
    ]
    for bar, notes in enumerate(melody):
        for i, f in enumerate(notes):
            if f:
                put(_pluck(f, 0.19, 0.5), bar, i)
    # walking staccato bass on the quarters
    roots = [E2, E2, D2 * 2, B2, E2, A2, B2, E2]
    for bar, root in enumerate(roots):
        for q, f in enumerate((root, root, root * 1.5, root)):
            put(_tone(f, 0.13, "square", 0.22, decay=7), bar, q * 2)
    # oom-PAH: soft organ stabs on the swung offbeats
    chords = {0: (E3, G3, B3), 1: (E3, G3, B3), 2: (D4 / 2, F4s / 2, A3),
              3: (B2 * 2, D4, F4s), 4: (E3, G3, B3), 5: (A3, C4, E4),
              6: (B2 * 2, D4, F4s), 7: (E3, G3, B3)}
    for bar, chord in chords.items():
        for e8 in (1, 3, 5, 7):
            for f in chord:
                put(_tone(f, 0.09, "tri", 0.05, decay=5), bar, e8)
    # bone-rattle ticks on quarters + rolls at phrase ends
    for bar in range(bars):
        for q in (1, 3):
            put(_tone(random.uniform(2400, 3000), 0.03, "noise", 0.07, decay=8),
                bar, q * 2)
    for bar in (3, 7):
        put(_rattle(5, 0.2), bar, 6)
    return buf


def _synth_sfx():
    return {
        "swing": _sweep(900, 300, 0.09, "sine", 0.25, 8)
                 + _tone(2400, 0.05, "noise", 0.12, decay=10),
        "bones": _pluck(D5s, 0.1, 0.4) + _pluck(A4, 0.1, 0.35)
                 + _pluck(E4, 0.14, 0.35) + _rattle(4, 0.25),
        "hurt": _tone(110, 0.15, "square", 0.4, decay=7),
        "magic": _sweep(300, 1200, 0.22, "sine", 0.3, 3),
        "portal": _sweep(600, 80, 0.5, "sine", 0.35, 2)
                  + _pluck(B4, 0.2, 0.2) + _pluck(D5s, 0.2, 0.2),
        "shield": _sweep(200, 800, 0.5, "sine", 0.22, 1.5)
                  + _tone(800, 0.3, "tri", 0.15, decay=2),
        "door": _pluck(E3, 0.7, 0.5) + _pluck(G3, 0.7, 0.45)
                + _pluck(B3, 0.9, 0.45),
        "rise": _tone(70, 0.3, "noise", 0.18, decay=3)
                + _rattle(2, 0.15),
        "jump": _sweep(300, 500, 0.08, "square", 0.12, 4),
        "win": _pluck(E4, 0.18, 0.4) + _pluck(G4, 0.18, 0.4)
               + _pluck(B4, 0.18, 0.4) + _pluck(E4 * 2, 0.5, 0.5),
        "lose": _pluck(B3, 0.3, 0.45) + _pluck(A3, 0.3, 0.45)
                + _pluck(E3, 0.8, 0.5) + _rattle(5, 0.2),
        "unlock": _sweep(400, 1600, 0.35, "sine", 0.3, 2) + _pluck(B4, 0.3, 0.35),
        "dash": _sweep(520, 140, 0.13, "sine", 0.32, 6)
                + _tone(1800, 0.06, "noise", 0.14, decay=9),
        "deflect": _tone(1650, 0.16, "sine", 0.3, decay=10, harm=0.8)
                   + _tone(2600, 0.04, "noise", 0.1, decay=12),
    }


class Audio:
    def __init__(self):
        self.ok = False
        self.muted = False
        self.sounds = {}
        self.music = None
        # drop your own track named music.mp3 / .ogg / .wav either next to the
        # assets (repo) or in %LOCALAPPDATA%\GraveWait (installed) and it plays
        # on loop instead of the synthesized tune
        self.music_file = None
        for d in (paths.APP_DIR, os.path.join(paths.resource_dir(), "assets")):
            for ext in (".mp3", ".ogg", ".wav"):
                p = os.path.join(d, "music" + ext)
                if os.path.exists(p):
                    self.music_file = p
                    break
            if self.music_file:
                break
        try:
            pygame.mixer.init(SR, -16, 1, 512)
        except pygame.error:
            return
        adir = os.path.join(paths.APP_DIR, "audio")
        os.makedirs(adir, exist_ok=True)
        for f in os.listdir(adir):                 # drop stale versions
            if not f.startswith(_VER + "_"):
                try:
                    os.remove(os.path.join(adir, f))
                except OSError:
                    pass
        music_path = os.path.join(adir, f"{_VER}_music.wav")
        try:
            if not os.path.exists(music_path):
                _write(music_path, _synth_music())
            for name, samples in _synth_sfx().items():
                p = os.path.join(adir, f"{_VER}_{name}.wav")
                if not os.path.exists(p):
                    _write(p, samples)
                self.sounds[name] = pygame.mixer.Sound(p)
            self.music = pygame.mixer.Sound(music_path)
            self.ok = True
        except (OSError, pygame.error):
            self.ok = False

    def start_music(self):
        if not self.ok or self.muted:
            return
        if self.music_file:
            try:
                pygame.mixer.music.load(self.music_file)
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(loops=-1, fade_ms=800)
                return
            except pygame.error:
                pass                          # unreadable file: fall back
        self.music.set_volume(0.35)
        self.music.play(loops=-1, fade_ms=800)

    def sfx(self, name, vol=1.0):
        if self.ok and not self.muted and name in self.sounds:
            s = self.sounds[name]
            s.set_volume(min(1.0, vol))
            s.play()

    def toggle_mute(self):
        self.muted = not self.muted
        if not self.ok:
            return
        if self.muted:
            pygame.mixer.stop()
            pygame.mixer.music.stop()
        else:
            self.start_music()
