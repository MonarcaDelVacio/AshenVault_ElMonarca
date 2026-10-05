"""Efectos sintetizados y musica ambiental/batallas.

La musica se carga desde assets/music/. Para maxima compatibilidad con pygame-ce
se recomienda OGG Vorbis. El sistema tambien prueba MP3/WAV/FLAC y deja M4A como
ultimo intento, aunque M4A no forma parte de los formatos oficialmente listados
por pygame-ce.
"""
import array
import math
import random
from pathlib import Path

RATE = 22050
MUSIC_DIR = Path(__file__).resolve().parent.parent / "assets" / "music"

MUSIC_TRACKS = {
    "menu": "MenuPrincipal",
    "default": "MusicaDefault no batlle",
    "battle": "Batallas (Sin Jefes)",
    "boss": "BossFight",
}
MUSIC_EXTENSIONS = (".ogg", ".mp3", ".wav", ".flac", ".m4a")


def _tone(freq, dur, vol=0.4, sweep=0.0, noise=0.0, decay=4.0):
    n = int(RATE * dur)
    buf = array.array("h")
    ph = 0.0
    for i in range(n):
        t = i / n
        f = max(20.0, freq + sweep * t)
        ph += 2 * math.pi * f / RATE
        s = math.sin(ph) * (1 - noise) + random.uniform(-1, 1) * noise
        buf.append(int(s * vol * math.exp(-decay * t) * 32767))
    return buf


RECIPES = {
    "shoot": dict(freq=700, dur=0.09, sweep=-450, noise=0.15, vol=0.28),
    "enemy_shoot": dict(freq=300, dur=0.12, sweep=-150, noise=0.3, vol=0.22),
    "enemy_hit": dict(freq=220, dur=0.06, noise=0.6, vol=0.25),
    "enemy_die": dict(freq=180, dur=0.25, sweep=-120, noise=0.7, vol=0.35, decay=3),
    "player_hit": dict(freq=130, dur=0.3, sweep=-80, noise=0.5, vol=0.5, decay=3),
    "player_die": dict(freq=200, dur=0.9, sweep=-170, noise=0.3, vol=0.5, decay=2),
    "reload_start": dict(freq=400, dur=0.07, sweep=200, vol=0.2),
    "reload_done": dict(freq=800, dur=0.08, sweep=300, vol=0.25),
    "coin": dict(freq=1200, dur=0.08, sweep=500, vol=0.2),
    "dash": dict(freq=500, dur=0.14, sweep=-300, noise=0.5, vol=0.25),
    "no_energy": dict(freq=160, dur=0.08, vol=0.25),
    "swing": dict(freq=260, dur=0.1, sweep=-100, noise=0.5, vol=0.2),
    "ui": dict(freq=600, dur=0.05, vol=0.2),
    "wall_hit": dict(freq=350, dur=0.04, noise=0.7, vol=0.12),
    "spawn": dict(freq=250, dur=0.2, sweep=300, vol=0.12),
    "room_enter": dict(freq=420, dur=0.08, sweep=180, vol=0.16),
    "room_clear": dict(freq=760, dur=0.12, sweep=420, vol=0.2),
    "boss_spawn": dict(freq=95, dur=0.5, sweep=-25, noise=0.25, vol=0.34, decay=2.2),
    "boss_phase": dict(freq=180, dur=0.3, sweep=360, noise=0.15, vol=0.28, decay=2.5),
    "victory_portal": dict(freq=900, dur=0.45, sweep=500, vol=0.22, decay=2.0),
    "victory": dict(freq=1100, dur=0.65, sweep=700, vol=0.3, decay=1.8),
    "shop_purchase": dict(freq=850, dur=0.12, sweep=250, vol=0.2),
    "item_pickup": dict(freq=620, dur=0.1, sweep=500, vol=0.2),
    "weapon_pickup": dict(freq=700, dur=0.14, sweep=600, vol=0.22),
    "weapon_switch": dict(freq=500, dur=0.05, sweep=180, vol=0.12),
    "ability_heal": dict(freq=520, dur=0.22, sweep=600, vol=0.2),
    "heal_pickup": dict(freq=560, dur=0.24, sweep=820, vol=0.24, decay=2.8),
    "energy_pickup": dict(freq=980, dur=0.16, sweep=420, vol=0.22, decay=3.2),
    "ability_shield": dict(freq=360, dur=0.25, sweep=900, vol=0.2),
    "ability_burst": dict(freq=120, dur=0.3, sweep=450, noise=0.2, vol=0.3, decay=2.8),
    "ability_haste": dict(freq=700, dur=0.2, sweep=500, vol=0.18),
    "ability_freeze": dict(freq=900, dur=0.25, sweep=-500, vol=0.2),
    "ability_drone": dict(freq=480, dur=0.2, sweep=350, vol=0.18),
}


def music_context(sim):
    """Devuelve la pista adecuada para el estado actual de una partida.

    Se considera batalla activa cuando hay enemigos vivos en la sala. Los jefes
    y mini-jefes usan la pista de jefe; cualquier otra batalla usa la pista normal.
    Una sala despejada, tienda, evento, curacion, tesoro, etc. usa la musica default.
    """
    if sim is None:
        return "menu"
    enemies = getattr(sim, "enemies", ())
    if enemies:
        if any(getattr(e, "is_boss", False) for e in enemies):
            return "boss"
        if any(getattr(e, "is_miniboss", False) for e in enemies):
            return "boss"
        return "battle"
    return "default"


class Audio:
    def __init__(self, effects_volume=0.6, music_volume=0.6, music_dir=None):
        self.ok = False
        self.effects_volume = effects_volume
        self.music_volume = music_volume
        self.sounds = {}
        self.last = {}
        self.music_dir = Path(music_dir) if music_dir else MUSIC_DIR
        self.music_track = None
        self.music_file = None
        self.music_unavailable = set()
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(RATE, -16, 1, 512)
            for name, r in RECIPES.items():
                snd = pygame.mixer.Sound(buffer=_tone(**r).tobytes())
                self.sounds[name] = snd
            self.ok = True
            self.set_effects_volume(effects_volume)
            self.set_music_volume(music_volume)
        except Exception:
            self.ok = False  # sin audio disponible: el juego sigue funcionando

    def set_effects_volume(self, v):
        self.effects_volume = max(0.0, min(1.0, v))
        for s in self.sounds.values():
            s.set_volume(self.effects_volume)

    def set_music_volume(self, v):
        self.music_volume = max(0.0, min(1.0, v))
        if self.ok:
            try:
                import pygame
                pygame.mixer.music.set_volume(self.music_volume)
            except Exception:
                pass

    def set_volume(self, v):
        self.set_effects_volume(v)

    def _find_music_file(self, track):
        stem = MUSIC_TRACKS.get(track)
        if not stem:
            return None
        for ext in MUSIC_EXTENSIONS:
            p = self.music_dir / (stem + ext)
            if p.is_file():
                return p
        return None

    def play_music(self, track, fade_ms=120):
        """Cambia de pista y la deja en bucle hasta que cambia el contexto."""
        # No bloqueamos permanentemente una pista tras un fallo transitorio.
        # Esto permite recuperarla si el archivo aparece, si el mixer se
        # inicializa correctamente o si se cambia la configuración de audio.
        if not self.ok or track == self.music_track:
            return False
        try:
            import pygame
            path = self._find_music_file(track)
            if path is None:
                pygame.mixer.music.stop()
                self.music_track = None
                self.music_file = None
                self.music_unavailable.discard(track)
                return False
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1, fade_ms=max(0, int(fade_ms)))
            self.music_track = track
            self.music_file = path
            self.music_unavailable.discard(track)
            return True
        except Exception:
            # Un formato no soportado (por ejemplo M4A en algunos builds) no
            # debe cerrar el juego ni impedir que sigan funcionando los efectos.
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            self.music_track = None
            self.music_file = None
            self.music_unavailable.discard(track)
            return False

    def stop_music(self):
        if self.ok:
            try:
                import pygame
                pygame.mixer.music.stop()
            except Exception:
                pass
        self.music_track = None
        self.music_file = None

    def sync_music(self, state, sim=None):
        """Aplica la musica correspondiente al estado visual del juego."""
        if state == "play":
            self.play_music(music_context(sim))
        elif state in {"menu", "pause", "settings", "hub", "char_select", "dead", "victory"}:
            self.play_music("menu")
        else:
            self.stop_music()

    def play(self, name, now=0.0):
        s = self.sounds.get(name)
        if s and now - self.last.get(name, -1) > 0.03:  # evita saturar el mezclador
            self.last[name] = now
            s.play()
