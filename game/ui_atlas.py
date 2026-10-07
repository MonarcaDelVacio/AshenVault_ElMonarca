"""Ashen Vault UI atlas integration.

The atlas is a real sprite sheet: every reusable UI element is addressed by an
explicit source rectangle. The source artwork has a pure black background, so
black is treated as transparent when sprites are extracted.

This module deliberately avoids guessing from connected components. The atlas
contains touching/overlapping decorative pixels, so explicit regions are much
more reliable and preserve the authored artwork.
"""
from pathlib import Path
import math
import pygame

ROOT = Path(__file__).resolve().parent.parent
ATLAS_PATH = ROOT / "assets" / "ui" / "AshenVault_UI_Atlas.png"


class UIAtlas:
    # Coordinates are in the 1536x1128 source atlas.
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
        "hud_usar": (480, 505, 243, 63),
        "hud_recargar": (485, 577, 232, 45),
        "hud_interactuar": (485, 632, 232, 45),
        "hud_recoger": (486, 686, 231, 45),

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
        "frame_blue": (943, 1028, 128, 33),
        "frame_gold": (1089, 1030, 128, 32),
        "frame_gray": (1235, 1031, 126, 32),
        "frame_red": (1379, 1031, 125, 32),

        # HUD status icons.
        "icon_health": (1106, 510, 56, 48),
        "icon_shield": (1167, 509, 61, 48),
        "icon_energy": (1231, 510, 57, 48),
        "icon_poison": (1298, 510, 51, 46),
        "icon_fire": (1358, 509, 57, 48),
        "icon_freeze": (1418, 509, 44, 48),
        "icon_skull": (1468, 509, 46, 49),
        "icon_potion": (783, 510, 63, 57),
        "icon_medkit": (858, 510, 63, 57),
        "icon_key": (933, 509, 58, 58),
        "icon_chest": (1000, 510, 58, 57),
        "icon_refresh": (783, 577, 63, 59),
        "icon_purple_shield": (857, 577, 68, 61),
        "icon_white_skull": (925, 577, 64, 61),
        "icon_debuff": (1368, 588, 44, 42),
        "icon_buff": (1418, 587, 43, 43),
        "icon_star": (1468, 587, 46, 43),
        "icon_left": (790, 646, 55, 29),
        "icon_right": (860, 647, 51, 28),
        "icon_target": (926, 646, 53, 29),
        "icon_star_small": (993, 648, 51, 27),
        "icon_pin": (790, 670, 54, 60),
        "icon_exclamation": (861, 694, 49, 36),
        "icon_question": (928, 670, 51, 60),
        "icon_heart_small": (993, 670, 51, 60),

        # Five authored empty equipment slots.
        "equipment_slot": (1377, 627, 27, 47),

        # Full status bars: icon + authored bar frame.
        "bar_health": (1106, 558, 225, 51),
        "bar_shield": (1107, 611, 224, 45),
        "bar_energy": (1108, 665, 224, 42),

        # Inner bar-only portions for compact bars (bosses, etc.).
        "track_health": (1147, 566, 151, 22),
        "track_shield": (1148, 625, 150, 20),
        "track_energy": (1149, 676, 150, 21),
    }

    BUTTONS = {
        "jugar": "menu_jugar",
        "iniciar run": "menu_jugar",
        "mejoras": "menu_mejoras",
        "mejoras pausa": "pause_mejoras",
        "personajes": "menu_personajes",
        "configuracion": "menu_configuracion",
        "salir": "menu_salir",
        "armas": "up_armas",
        "habilidades": "up_habilidades",
        "modificadores": "up_modificadores",
        "volver": "up_volver",
        "volver al menu": "up_volver",
        "volver al menú": "up_volver",
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
        "reiniciar run": "restart",
        "reiniciar": "restart",
        "salir al menu": "pause_abandonar",
        "salir al menú": "pause_abandonar",
        "configuracion": "menu_configuracion",
        "configuración": "menu_configuracion",
        "configuracion pausa": "pause_configuracion",
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
                # El atlas puede conservar el mismo layout aunque su PNG haya cambiado de
                # compresion/resolucion. Validamos las regiones individualmente en _crop().
                self.available = self.atlas.get_width() >= 1536 and self.atlas.get_height() >= 1024
        except (pygame.error, OSError, ValueError):
            self.atlas = None
            self.available = False

    def _crop(self, name):
        if not self.available or name not in self.regions:
            return None
        if name in self.cache:
            return self.cache[name]
        try:
            base_rect = pygame.Rect(self.regions[name]).clip(self.atlas.get_rect())
            hud_exact_names = {
                key for key in self.regions
                if (key.startswith("icon_") or key.startswith("bar_")
                    or key.startswith("track_") or key == "equipment_slot"
                    or key.startswith("hud_") or key.startswith("frame_") or key.startswith("pause_"))
            }
            if name in hud_exact_names:
                rect = base_rect
            elif name in set(self.BUTTONS.values()):
                margin = 28
                search = base_rect.inflate(margin * 2, margin * 2).clip(self.atlas.get_rect())
                probe = self.atlas.subsurface(search).copy()
                mask = pygame.mask.from_surface(probe, 8)
                candidates = []
                for component in mask.connected_components(minimum=6):
                    boxes = component.get_bounding_rects()
                    if not boxes:
                        continue
                    bbox = boxes[0].copy()
                    for part in boxes[1:]:
                        bbox.union_ip(part)
                    if bbox.width < 20 or bbox.height < 12:
                        continue
                    cx = search.x + bbox.centerx
                    cy = search.y + bbox.centery
                    distance = math.hypot(cx - base_rect.centerx, cy - base_rect.centery)
                    area = bbox.width * bbox.height
                    score = area / (1.0 + distance * 1.8)
                    candidates.append((score, bbox.move(search.x, search.y)))
                rect = base_rect
                if candidates:
                    _, detected = max(candidates, key=lambda item: item[0])
                    expected_ratio = base_rect.width / max(1, base_rect.height)
                    detected_ratio = detected.width / max(1, detected.height)
                    if (abs(detected_ratio - expected_ratio) / max(1.0, expected_ratio) < 0.45
                            and detected.width >= base_rect.width * 0.45
                            and detected.height >= base_rect.height * 0.45):
                        rect = detected.clip(self.atlas.get_rect())
            else:
                rect = base_rect

            image = self.atlas.subsurface(rect).copy()
            if name not in hud_exact_names:
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
        # El modelo nunca cambia de escala al pasar el cursor: el resaltado se
        # dibuja alrededor de exactamente la misma silueta que está en pantalla.
        # Así el borde de selección no puede separarse de las esquinas del PNG.
        sprite = self._fit(image, base_rect.size)
        dst = sprite.get_rect(center=base_rect.center)
        screen.blit(sprite, dst)
        if selected:
            mask = pygame.mask.from_surface(sprite, 8)
            outline = mask.outline()
            if outline:
                glow = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
                pygame.draw.lines(glow, (120, 225, 255, 235), True, outline, width=2)
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
        }.get(kind, "bar_health")
        track_key = {
            "health": "track_health",
            "hp": "track_health",
            "shield": "track_shield",
            "energy": "track_energy",
        }.get(kind, "track_health")

        target = pygame.Rect(*map(int, rect))
        if target.height <= 15:
            image = self._crop(track_key)
            source_key = track_key
        else:
            image = self._crop(full_key)
            source_key = full_key
        if image is None:
            return False

        # Todas las barras del HUD utilizan exactamente el mismo rectángulo de
        # destino. El atlas contiene marcos con alturas originales diferentes,
        # por lo que aquí se normalizan a un tamaño común en pantalla.
        rendered_rect = target.copy()
        if image.get_size() != rendered_rect.size:
            image = pygame.transform.smoothscale(image, rendered_rect.size)
        screen.blit(image, rendered_rect)

        ratio = max(0.0, min(1.0, float(ratio)))

        # La geometría del track sigue saliendo de REGIONS. Sus offsets se
        # transforman independientemente en X/Y hacia el tamaño común.
        if source_key == full_key:
            full_rect = pygame.Rect(self.regions[full_key])
            track_rect = pygame.Rect(self.regions[track_key])
            sx = (track_rect.x - full_rect.x) / max(1, full_rect.width)
            sy = (track_rect.y - full_rect.y) / max(1, full_rect.height)
            sw = track_rect.width / max(1, full_rect.width)
            sh = track_rect.height / max(1, full_rect.height)
        else:
            sx, sy, sw, sh = 0.0, 0.0, 1.0, 1.0

        tx = rendered_rect.x + round(rendered_rect.width * sx)
        ty = rendered_rect.y + round(rendered_rect.height * sy)
        tw = max(1, round(rendered_rect.width * sw))
        th = max(1, round(rendered_rect.height * sh))
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

    def draw_icon_cooldown(self, screen, center, size=24, kind="health", ratio=0.0):
        """Dibuja el icono y limita el sombreado de cooldown a su propia silueta."""
        if not self.available:
            return False
        key = {
            "health": "icon_health", "shield": "icon_shield", "energy": "icon_energy",
            "lightning": "icon_energy", "poison": "icon_poison", "fire": "icon_fire",
            "freeze": "icon_freeze", "skull": "icon_skull", "heal": "icon_medkit",
            "medkit": "icon_medkit", "key": "icon_key", "shop": "icon_key",
            "chest": "icon_chest", "refresh": "icon_refresh", "purple_shield": "icon_purple_shield",
            "target": "icon_target", "buff": "icon_buff",
        }.get(str(kind).lower())
        image = self._crop(key) if key else None
        if image is None:
            return False
        sprite = self._fit(image, (size, size))
        dst = sprite.get_rect(center=center)
        screen.blit(sprite, dst)
        ratio = max(0.0, min(1.0, float(ratio)))
        if ratio > 0.0:
            mask = pygame.mask.from_surface(sprite, 8)
            cover_h = int(sprite.get_height() * ratio)
            overlay = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
            pygame.draw.rect(overlay, (8, 10, 18, 150),
                             (0, 0, sprite.get_width(), cover_h))
            alpha = mask.to_surface(setcolor=(255,255,255,255), unsetcolor=(0,0,0,0))
            overlay.blit(alpha, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(overlay, dst.topleft)
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
