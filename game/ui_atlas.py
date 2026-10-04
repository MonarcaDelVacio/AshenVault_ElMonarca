"""Ashen Vault UI atlas integration.

The atlas is treated as a reusable UI skin. Button frames keep their authored
coordinates, while HUD frames/bars/slots are discovered from the transparent
atlas at runtime so the game does not depend on a second set of hand-authored
PNG files. Every draw method has a procedural fallback.
"""
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent.parent
ATLAS_PATH = ROOT / "assets" / "ui" / "AshenVault_UI_Atlas.png"


class UIAtlas:
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
        self.components = []
        self.panel_candidates = []
        self.bar_candidates = []
        self.slot_candidates = []
        self.icon_candidates = []
        self.available = False
        try:
            if ATLAS_PATH.is_file():
                self.atlas = pygame.image.load(str(ATLAS_PATH)).convert_alpha()
                for name, rect in self.FRAME_RECTS.items():
                    if rect.right <= self.atlas.get_width() and rect.bottom <= self.atlas.get_height():
                        self.frames[name] = self.atlas.subsurface(rect).copy()
                self._discover_components()
                self.available = bool(self.frames or self.components)
        except (pygame.error, OSError, ValueError):
            self.atlas = None
            self.frames.clear()
            self.components.clear()
            self.available = False

    def _discover_components(self):
        if self.atlas is None:
            return
        try:
            mask = pygame.mask.from_surface(self.atlas)
            components = mask.connected_components()
            for component in components:
                rect = component.get_bounding_rect()
                if rect.width < 6 or rect.height < 4:
                    continue
                area = component.count()
                if area < 40:
                    continue
                self.components.append((rect.copy(), area))
        except (AttributeError, TypeError, pygame.error):
            return

        for rect, area in self.components:
            aspect = rect.width / max(1, rect.height)
            if rect.width >= 150 and rect.height >= 55:
                self.panel_candidates.append((rect, area))
            elif rect.width >= 70 and rect.height <= 34 and aspect >= 2.2:
                self.bar_candidates.append((rect, area))
            elif 26 <= rect.width <= 110 and 26 <= rect.height <= 110 and 0.70 <= aspect <= 1.45:
                self.slot_candidates.append((rect, area))
            elif rect.width <= 80 and rect.height <= 80:
                self.icon_candidates.append((rect, area))

        button_rects = list(self.FRAME_RECTS.values())
        self.panel_candidates = [x for x in self.panel_candidates if not any(x[0].colliderect(r) for r in button_rects)]
        self.bar_candidates = [x for x in self.bar_candidates if not any(x[0].colliderect(r) for r in button_rects)]
        self.slot_candidates = [x for x in self.slot_candidates if not any(x[0].colliderect(r) for r in button_rects)]

    def _crop(self, rect):
        if self.atlas is None or rect is None:
            return None
        key = ("crop", rect.x, rect.y, rect.w, rect.h)
        image = self.cache.get(key)
        if image is None:
            try:
                image = self.atlas.subsurface(rect).copy()
            except (pygame.error, ValueError):
                return None
            self.cache[key] = image
        return image

    @staticmethod
    def _stretch(image, size):
        if image is None:
            return None
        w, h = max(1, int(size[0])), max(1, int(size[1]))
        return pygame.transform.smoothscale(image, (w, h))

    def _best(self, candidates, target_w, target_h):
        if not candidates:
            return None
        target_aspect = max(0.05, target_w / max(1, target_h))
        def score(item):
            rect, area = item
            aspect = rect.width / max(1, rect.height)
            aspect_error = abs(aspect - target_aspect)
            size_error = abs((rect.width * rect.height) - (target_w * target_h)) / max(1, target_w * target_h)
            return aspect_error * 5.0 + size_error * 0.35
        return min(candidates, key=score)[0]

    def _nine_slice(self, image, size, border=8):
        if image is None:
            return None
        tw, th = max(1, int(size[0])), max(1, int(size[1]))
        iw, ih = image.get_size()
        b = max(2, min(border, iw // 2, ih // 2, tw // 2, th // 2))
        if tw < b * 2 or th < b * 2:
            return self._stretch(image, (tw, th))
        out = pygame.Surface((tw, th), pygame.SRCALPHA)
        src_rects = (
            (pygame.Rect(0, 0, b, b), pygame.Rect(0, 0, b, b)),
            (pygame.Rect(b, 0, iw - b * 2, b), pygame.Rect(b, 0, tw - b * 2, b)),
            (pygame.Rect(iw - b, 0, b, b), pygame.Rect(tw - b, 0, b, b)),
            (pygame.Rect(0, b, b, ih - b * 2), pygame.Rect(0, b, b, th - b * 2)),
            (pygame.Rect(b, b, iw - b * 2, ih - b * 2), pygame.Rect(b, b, tw - b * 2, th - b * 2)),
            (pygame.Rect(iw - b, b, b, ih - b * 2), pygame.Rect(tw - b, b, b, th - b * 2)),
            (pygame.Rect(0, ih - b, b, b), pygame.Rect(0, th - b, b, b)),
            (pygame.Rect(b, ih - b, iw - b * 2, b), pygame.Rect(b, th - b, tw - b * 2, b)),
            (pygame.Rect(iw - b, ih - b, b, b), pygame.Rect(tw - b, th - b, b, b)),
        )
        for src, dst in src_rects:
            piece = image.subsurface(src)
            if piece.get_size() != dst.size:
                piece = pygame.transform.smoothscale(piece, dst.size)
            out.blit(piece, dst)
        return out

    def _variant(self, label, selected=False, destructive=False):
        text = str(label).lower()
        if destructive or any(k in text for k in ("salir", "abandonar", "eliminar", "cerrar", "cancelar")):
            return "red"
        if selected or any(k in text for k in ("mejora", "mejorar", "equipar", "aceptar")):
            return "gold"
        return "blue" if selected else "gray"

    def draw_button(self, screen, rect, label, selected=False, destructive=False):
        if not self.available:
            return False
        x, y, w, h = map(int, rect)
        if w <= 0 or h <= 0:
            return False
        variant = self._variant(label, selected, destructive)
        key = ("button", variant, w, h)
        image = self.cache.get(key)
        if image is None:
            frame = self.frames.get(variant) or self.frames.get("gray")
            if frame is None:
                return False
            image = self._stretch(frame, (w, h))
            self.cache[key] = image
        screen.blit(image, (x, y))
        return True

    def draw_panel(self, screen, rect, border=8):
        if not self.available or not self.panel_candidates:
            return False
        image = self._nine_slice(self._crop(self._best(self.panel_candidates, rect.width, rect.height)), rect.size, border=border)
        if image is None:
            return False
        screen.blit(image, rect.topleft)
        return True

    def draw_bar(self, screen, rect, ratio=1.0):
        if not self.available or not self.bar_candidates:
            return False
        image = self._stretch(self._crop(self._best(self.bar_candidates, rect.width, rect.height)), rect.size)
        if image is None:
            return False
        screen.blit(image, rect.topleft)
        ratio = max(0.0, min(1.0, float(ratio)))
        if ratio < 1.0:
            cover = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(cover, (4, 6, 11, 175), (int(rect.width * ratio), 0, rect.width, rect.height))
            screen.blit(cover, rect.topleft)
        return True

    def draw_slot(self, screen, rect, selected=False):
        if not self.available or not self.slot_candidates:
            return False
        image = self._stretch(self._crop(self._best(self.slot_candidates, rect.width, rect.height)), rect.size)
        if image is None:
            return False
        screen.blit(image, rect.topleft)
        if selected:
            pygame.draw.rect(screen, (255, 219, 133), rect.inflate(3, 3), 1, border_radius=4)
        return True

    def draw_icon(self, screen, center, size=24):
        if not self.available or not self.icon_candidates:
            return False
        image = self._stretch(self._crop(self._best(self.icon_candidates, size, size)), (size, size))
        if image is None:
            return False
        screen.blit(image, image.get_rect(center=(int(center[0]), int(center[1]))))
        return True
