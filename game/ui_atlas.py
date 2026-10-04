"""Ashen Vault UI atlas integration.

The atlas is a real sprite sheet: every reusable UI element is addressed by an
explicit source rectangle. The source artwork has a pure black background, so
black is treated as transparent when sprites are extracted.

This module deliberately avoids guessing from connected components. The atlas
contains touching/overlapping decorative pixels, so explicit regions are much
more reliable and preserve the authored artwork.
"""
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent.parent
ATLAS_PATH = ROOT / "assets" / "ui" / "AshenVault_UI_Atlas.png"


class UIAtlas:
    # Coordinates are in the 1536x1024 source atlas.
    REGIONS = {
        # Main menu
        "menu_jugar": (21, 63, 274, 66),
        "menu_mejoras": (21, 138, 273, 65),
        "menu_personajes": (21, 212, 273, 66),
        "menu_configuracion": (21, 287, 273, 67),
        "menu_salir": (21, 362, 274, 66),

        # Upgrade menu
        "up_mejoras": (336, 64, 269, 60),
        "up_armas": (336, 131, 269, 59),
        "up_habilidades": (336, 197, 269, 59),
        "up_modificadores": (336, 263, 269, 60),
        "up_volver": (336, 331, 269, 59),

        # Settings menu
        "settings_sonido": (653, 63, 237, 49),
        "settings_musica": (653, 115, 237, 49),
        "settings_graficos": (652, 166, 238, 50),
        "settings_controles": (653, 218, 237, 49),
        "settings_idioma": (652, 269, 238, 51),
        "settings_restablecer": (653, 321, 237, 49),
        "settings_volver": (653, 374, 237, 48),

        # Character menu
        "char_seleccionar": (952, 64, 253, 56),
        "char_mejoras": (952, 126, 252, 53),
        "char_equipo": (952, 186, 253, 55),
        "char_estadisticas": (952, 246, 253, 55),
        "char_historia": (952, 306, 253, 55),
        "char_volver": (952, 367, 253, 54),

        # Pause
        "pause_reanudar": (1254, 64, 258, 71),
        "pause_mejoras": (1254, 146, 258, 71),
        "pause_configuracion": (1254, 227, 258, 71),
        "pause_abandonar": (1254, 308, 258, 71),

        # Generic menu/panel actions
        "accept": (21, 496, 208, 49),
        "restart": (252, 496, 196, 50),
        "cancel": (22, 552, 207, 49),
        "select": (252, 551, 196, 50),
        "confirm": (21, 606, 208, 49),
        "delete": (252, 606, 196, 49),
        "apply": (22, 660, 207, 49),
        "close": (252, 660, 196, 49),

        # In-game HUD actions
        "hud_usar": (484, 497, 238, 52),
        "hud_recargar": (484, 553, 238, 50),
        "hud_interactuar": (484, 607, 238, 51),
        "hud_recoger": (484, 661, 238, 51),

        # Inventory/equipment
        "inv_objetos": (21, 781, 194, 43),
        "inv_soltar": (235, 781, 159, 42),
        "inv_armas": (21, 826, 194, 44),
        "inv_usar": (236, 826, 158, 43),
        "inv_equipo": (21, 872, 194, 44),
        "inv_equipar": (236, 873, 158, 42),
        "inv_consumibles": (21, 920, 194, 42),
        "inv_desequipar": (235, 920, 159, 42),

        # Dialogue/events
        "dialog_continuar": (438, 784, 225, 43),
        "dialog_omitir": (438, 829, 226, 42),
        "dialog_siguiente": (438, 874, 226, 42),
        "dialog_anterior": (438, 920, 226, 42),

        # Missions/map
        "mission_misiones": (738, 786, 208, 42),
        "mission_mapa": (738, 829, 208, 42),
        "mission_objetivo": (738, 874, 208, 42),
        "mission_volver": (738, 920, 208, 41),

        # Windows / panels
        "window_minimizar": (1010, 786, 208, 41),
        "window_maximizar": (1010, 832, 208, 41),
        "window_cerrar": (1010, 875, 208, 41),
        "window_opciones": (1010, 920, 208, 41),

        # Special actions
        "special_guardar": (1277, 787, 223, 43),
        "special_cargar": (1277, 832, 223, 43),
        "special_logros": (1277, 877, 223, 42),
        "special_creditos": (1277, 922, 223, 41),

        # Neutral scalable frames at the bottom of the atlas.
        "frame_blue": (951, 976, 123, 30),
        "frame_gold": (1096, 977, 124, 30),
        "frame_gray": (1241, 978, 123, 30),
        "frame_red": (1385, 978, 122, 30),

        # HUD status icons.
        "icon_health": (1111, 489, 48, 45),
        "icon_shield": (1176, 489, 48, 45),
        "icon_energy": (1240, 489, 47, 45),
        "icon_poison": (1302, 489, 46, 45),
        "icon_fire": (1363, 489, 47, 45),
        "icon_freeze": (1420, 489, 46, 45),
        "icon_skull": (1474, 489, 46, 45),
        "icon_potion": (787, 489, 59, 55),
        "icon_medkit": (862, 489, 57, 56),
        "icon_key": (934, 489, 56, 55),
        "icon_chest": (1004, 489, 55, 55),
        "icon_refresh": (787, 557, 59, 56),
        "icon_purple_shield": (862, 557, 57, 57),
        "icon_white_skull": (934, 557, 56, 56),
        "icon_debuff": (1371, 567, 40, 46),
        "icon_buff": (1421, 567, 41, 46),
        "icon_star": (1473, 567, 41, 46),
        "icon_left": (794, 627, 51, 41),
        "icon_right": (863, 627, 49, 41),
        "icon_target": (931, 627, 48, 41),
        "icon_star_small": (997, 627, 48, 41),
        "icon_pin": (797, 677, 45, 42),
        "icon_exclamation": (866, 677, 44, 42),
        "icon_question": (933, 677, 43, 42),
        "icon_heart_small": (1000, 677, 43, 42),

        # Five authored empty equipment slots.
        "equipment_slot": (1377, 627, 27, 47),

        # Full status bars: icon + authored bar frame.
        "bar_health": (1111, 550, 221, 43),
        "bar_shield": (1111, 593, 221, 31),
        "bar_energy": (1111, 624, 221, 43),
        "bar_mana": (1111, 668, 221, 41),

        # Inner bar-only portions for compact bars (bosses, etc.).
        "track_health": (1147, 558, 151, 22),
        "track_shield": (1148, 595, 150, 20),
        "track_energy": (1148, 634, 150, 21),
        "track_mana": (1149, 678, 147, 22),
    }

    BUTTONS = {
        "jugar": "menu_jugar",
        "mejoras": "menu_mejoras",
        "personajes": "menu_personajes",
        "configuracion": "menu_configuracion",
        "salir": "menu_salir",
        "armas": "up_armas",
        "habilidades": "up_habilidades",
        "modificadores": "up_modificadores",
        "volver": "up_volver",
        "sonido": "settings_sonido",
        "musica": "settings_musica",
        "graficos": "settings_graficos",
        "controles": "settings_controles",
        "idioma": "settings_idioma",
        "restablecer": "settings_restablecer",
        "seleccionar": "char_seleccionar",
        "equipo": "char_equipo",
        "estadisticas": "char_estadisticas",
        "historia": "char_historia",
        "reanudar": "pause_reanudar",
        "continuar": "pause_reanudar",
        "reiniciar run": "restart",
        "reiniciar": "restart",
        "salir al menu": "pause_abandonar",
        "salir al menú": "pause_abandonar",
        "configuracion": "settings_graficos",
        "configuración": "settings_graficos",
        "volumen efectos": "settings_sonido",
        "volumen musica": "settings_musica",
        "volumen música": "settings_musica",
        "abandonar": "pause_abandonar",
        "aceptar": "accept",
        "reiniciar": "restart",
        "cancelar": "cancel",
        "confirmar": "confirm",
        "eliminar": "delete",
        "aplicar": "apply",
        "cerrar": "close",
        "usar": "hud_usar",
        "recargar": "hud_recargar",
        "interactuar": "hud_interactuar",
        "recoger": "hud_recoger",
        "objetos": "inv_objetos",
        "soltar": "inv_soltar",
        "equipar": "inv_equipar",
        "desequipar": "inv_desequipar",
        "consumibles": "inv_consumibles",
        "continuar": "dialog_continuar",
        "omitir": "dialog_omitir",
        "siguiente": "dialog_siguiente",
        "anterior": "dialog_anterior",
        "misiones": "mission_misiones",
        "mapa": "mission_mapa",
        "objetivo": "mission_objetivo",
        "minimizar": "window_minimizar",
        "maximizar": "window_maximizar",
        "más opciones": "window_opciones",
        "mas opciones": "window_opciones",
        "guardar": "special_guardar",
        "cargar": "special_cargar",
        "logros": "special_logros",
        "créditos": "special_creditos",
        "creditos": "special_creditos",
    }

    def __init__(self):
        self.atlas = None
        self.cache = {}
        self.available = False
        self.regions = {}
        try:
            if ATLAS_PATH.is_file():
                self.atlas = pygame.image.load(str(ATLAS_PATH)).convert_alpha()
                # Convert the atlas' black matte into real transparency so
                # cropped sprites retain only their visible silhouette.
                self.atlas.set_colorkey((0, 0, 0))
                self.atlas = self.atlas.copy()
                self.atlas.set_colorkey(None)
                rgb = pygame.surfarray.pixels3d(self.atlas)
                alpha = pygame.surfarray.pixels_alpha(self.atlas)
                black_pixels = (rgb[:, :, 0] == 0) & (rgb[:, :, 1] == 0) & (rgb[:, :, 2] == 0)
                alpha[black_pixels] = 0
                del rgb, alpha
                self.regions = dict(self.REGIONS)
                self.available = self.atlas.get_width() == 1536 and self.atlas.get_height() == 1024
        except (pygame.error, OSError, ValueError):
            self.atlas = None
            self.available = False

    def _crop(self, name):
        if not self.available or name not in self.regions:
            return None
        if name in self.cache:
            return self.cache[name]
        try:
            rect = pygame.Rect(self.regions[name]).clip(self.atlas.get_rect())
            image = self.atlas.subsurface(rect).copy()
            visible = image.get_bounding_rect(min_alpha=8)
            if visible.width and visible.height:
                image = image.subsurface(visible).copy()
            self.cache[name] = image
            return image
        except (pygame.error, ValueError):
            return None

    @staticmethod
    def _fit(image, size):
        if image is None:
            return None
        tw, th = max(1, int(size[0])), max(1, int(size[1]))
        iw, ih = image.get_size()
        scale = min(tw / max(1, iw), th / max(1, ih))
        nw, nh = max(1, round(iw * scale)), max(1, round(ih * scale))
        if (nw, nh) == (iw, ih):
            return image
        return pygame.transform.smoothscale(image, (nw, nh))

    def _blit_fit(self, screen, image, rect):
        sprite = self._fit(image, rect.size)
        if sprite is None:
            return False
        screen.blit(sprite, sprite.get_rect(center=rect.center))
        return True

    def _nine_slice(self, image, size, border=8):
        if image is None:
            return None
        tw, th = max(1, int(size[0])), max(1, int(size[1]))
        iw, ih = image.get_size()
        b = max(2, min(int(border), iw // 2, ih // 2, tw // 2, th // 2))
        if tw < b * 2 or th < b * 2:
            return self._fit(image, (tw, th))
        out = pygame.Surface((tw, th), pygame.SRCALPHA)
        pieces = (
            (pygame.Rect(0, 0, b, b), pygame.Rect(0, 0, b, b)),
            (pygame.Rect(b, 0, iw - 2*b, b), pygame.Rect(b, 0, tw - 2*b, b)),
            (pygame.Rect(iw-b, 0, b, b), pygame.Rect(tw-b, 0, b, b)),
            (pygame.Rect(0, b, b, ih - 2*b), pygame.Rect(0, b, b, th - 2*b)),
            (pygame.Rect(b, b, iw - 2*b, ih - 2*b), pygame.Rect(b, b, tw - 2*b, th - 2*b)),
            (pygame.Rect(iw-b, b, b, ih - 2*b), pygame.Rect(tw-b, b, b, th - 2*b)),
            (pygame.Rect(0, ih-b, b, b), pygame.Rect(0, th-b, b, b)),
            (pygame.Rect(b, ih-b, iw - 2*b, b), pygame.Rect(b, th-b, tw - 2*b, b)),
            (pygame.Rect(iw-b, ih-b, b, b), pygame.Rect(tw-b, th-b, b, b)),
        )
        for src, dst in pieces:
            part = image.subsurface(src)
            if part.get_size() != dst.size:
                part = pygame.transform.smoothscale(part, dst.size)
            out.blit(part, dst)
        return out

    def draw_button(self, screen, rect, label, selected=False, destructive=False):
        """Draw an authored button including its embedded icon/text.

        Returns True only when the atlas contains the complete button artwork.
        The caller must not draw the label again in that case.
        """
        if not self.available:
            return False
        key = self.BUTTONS.get(str(label).strip().lower())
        if key is None:
            return False
        if destructive and str(label).strip().lower() == "cerrar":
            key = "window_cerrar"
        image = self._crop(key)
        if image is None:
            return False
        target = pygame.Rect(*map(int, rect))
        base_rect = pygame.Rect(*map(int, rect))
        if selected:
            target = base_rect.inflate(max(4, base_rect.width // 14), max(4, base_rect.height // 10))
        sprite = pygame.transform.smoothscale(image, target.size)
        dst = sprite.get_rect(center=base_rect.center)
        screen.blit(sprite, dst)
        if selected:
            mask = pygame.mask.from_surface(sprite, 8)
            outline = mask.outline()
            if outline:
                glow = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
                pygame.draw.polygon(glow, (120, 225, 255, 210), outline, width=2)
                screen.blit(glow, dst.topleft)
        return True

    def draw_panel(self, screen, rect, border=8, variant="blue"):
        if not self.available:
            return False
        key = {
            "blue": "frame_blue",
            "gold": "frame_gold",
            "gray": "frame_gray",
            "red": "frame_red",
        }.get(str(variant).lower(), "frame_blue")
        image = self._crop(key)
        if image is None:
            return False
        out = self._nine_slice(image, rect.size, border=border)
        if out is None:
            return False
        screen.blit(out, rect.topleft)
        return True

    def draw_bar(self, screen, rect, ratio=1.0, kind="health"):
        if not self.available:
            return False
        kind = str(kind).lower()
        full_key = {
            "health": "bar_health",
            "hp": "bar_health",
            "shield": "bar_shield",
            "energy": "bar_energy",
            "mana": "bar_mana",
        }.get(kind, "bar_health")
        track_key = {
            "health": "track_health",
            "hp": "track_health",
            "shield": "track_shield",
            "energy": "track_energy",
            "mana": "track_mana",
        }.get(kind, "track_health")

        target = pygame.Rect(*map(int, rect))
        if target.height <= 15:
            image = self._crop(track_key)
        else:
            image = self._crop(full_key)
        if image is None:
            return False
        # Draw the authored frame unchanged. Only the colored fill track is
        # masked by the current value; the heart/shield/lightning and frame stay put.
        self._blit_fit(screen, image, target)
        ratio = max(0.0, min(1.0, float(ratio)))
        # Track coordinates measured within each authored full-bar sprite.
        track = {
            "health": (36/221, 8/43, 151/221, 22/43),
            "hp": (36/221, 8/43, 151/221, 22/43),
            "shield": (37/221, 2/31, 150/221, 20/31),
            "energy": (37/221, 10/43, 150/221, 21/43),
            "mana": (38/221, 10/41, 147/221, 22/41),
        }.get(kind, (36/221, 8/43, 151/221, 22/43))
        tx = target.x + round(target.width * track[0])
        ty = target.y + round(target.height * track[1])
        tw = round(target.width * track[2])
        th = max(1, round(target.height * track[3]))
        remaining_x = tx + round(tw * ratio)
        if ratio < 1.0 and remaining_x < tx + tw:
            cover = pygame.Surface((tx + tw - remaining_x, th), pygame.SRCALPHA)
            cover.fill((3, 6, 12, 205))
            screen.blit(cover, (remaining_x, ty))
        return True

    def draw_slot(self, screen, rect, selected=False):
        if not self.available:
            return False
        target = pygame.Rect(*map(int, rect))
        # The atlas' equipment glyph is narrow/vertical, not a square slot frame.
        # Use a neutral scalable frame so each inventory cell is actually square.
        image = self._crop("frame_gold" if selected else "frame_gray")
        if image is None:
            return False
        out = self._nine_slice(image, target.size, border=max(3, min(7, target.width // 5)))
        if out is None:
            return False
        screen.blit(out, target.topleft)
        return True

    def draw_icon(self, screen, center, size=24, kind="health"):
        if not self.available:
            return False
        key = {
            "health": "icon_health",
            "heart": "icon_health",
            "shield": "icon_shield",
            "energy": "icon_energy",
            "lightning": "icon_energy",
            "poison": "icon_poison",
            "fire": "icon_fire",
            "freeze": "icon_freeze",
            "skull": "icon_skull",
            "potion": "icon_potion",
            "heal": "icon_medkit",
            "medkit": "icon_medkit",
            "key": "icon_key",
            "shop": "icon_key",
            "chest": "icon_chest",
            "refresh": "icon_refresh",
            "purple_shield": "icon_purple_shield",
            "white_skull": "icon_white_skull",
            "debuff": "icon_debuff",
            "buff": "icon_buff",
            "star": "icon_star",
            "left": "icon_left",
            "right": "icon_right",
            "target": "icon_target",
            "pin": "icon_pin",
            "exclamation": "icon_exclamation",
            "question": "icon_question",
        }.get(str(kind).lower())
        if key is None:
            return False
        image = self._crop(key)
        if image is None:
            return False
        sprite = self._fit(image, (size, size))
        screen.blit(sprite, sprite.get_rect(center=(int(center[0]), int(center[1]))))
        return True

    def has(self, name):
        return bool(self.available and name in self.regions)
