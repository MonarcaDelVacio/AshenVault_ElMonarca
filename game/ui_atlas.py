"""Ashen Vault UI atlas integration.

Loads the generated UI atlas when present and exposes reusable button frames.
The game keeps a procedural fallback so missing art never prevents startup.
"""
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent.parent
ATLAS_PATH = ROOT / "assets" / "ui" / "AshenVault_UI_Atlas.png"

class UIAtlas:
    # Empty button frames located on the atlas bottom row.
    FRAME_RECTS = {
        "blue": pygame.Rect(953, 975, 118, 34),
        "gold": pygame.Rect(1095, 975, 122, 34),
        "gray": pygame.Rect(1242, 975, 123, 34),
        "red": pygame.Rect(1383, 975, 124, 34),
    }

    def __init__(self):
        self.atlas = None
        self.frames = {}
        self.cache = {}
        self.available = False
        try:
            if ATLAS_PATH.is_file():
                self.atlas = pygame.image.load(str(ATLAS_PATH)).convert_alpha()
                for name, rect in self.FRAME_RECTS.items():
                    self.frames[name] = self.atlas.subsurface(rect).copy()
                self.available = bool(self.frames)
        except (pygame.error, OSError, ValueError):
            self.atlas = None
            self.frames.clear()
            self.available = False

    def _variant(self, label, selected=False, destructive=False):
        text = str(label).lower()
        if destructive or any(k in text for k in ("salir", "abandonar", "eliminar", "cerrar", "cancelar")):
            return "red"
        if selected or any(k in text for k in ("mejora", "mejorar", "equipar", "aceptar")):
            return "gold"
        return "blue" if selected else "gray"

    def draw_button(self, screen, rect, label, selected=False, destructive=False):
        """Draw a stretched atlas frame. Returns True when atlas art was used."""
        if not self.available:
            return False
        x, y, w, h = map(int, rect)
        if w <= 0 or h <= 0:
            return False
        variant = self._variant(label, selected, destructive)
        key = (variant, w, h)
        image = self.cache.get(key)
        if image is None:
            frame = self.frames.get(variant) or self.frames.get("gray")
            if frame is None:
                return False
            image = pygame.transform.smoothscale(frame, (w, h))
            self.cache[key] = image
        screen.blit(image, (x, y))
        return True
