"""Dibujado con pygame. Solo lee el estado de la simulación; no la modifica."""
import math
import random
import pygame
from pathlib import Path
from .world import TILE, FLOOR, WALL, PILLAR, SECRET, TORCH_PILLAR, bonfire_positions
from .ui_atlas import UIAtlas

VIEW_W, VIEW_H = 960, 540


class Renderer:
    def __init__(self, data):
        self.data = data
        # Tipografía incluida con el juego para mantener el mismo aspecto en todos los equipos.
        font_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"
        try:
            self.menu_font = pygame.font.Font(str(font_dir / "Lato-Bold.ttf"), 17)
            self.menu_small = pygame.font.Font(str(font_dir / "Lato-Regular.ttf"), 15)
            self.menu_title = pygame.font.Font(str(font_dir / "Lato-Black.ttf"), 43)
        except (pygame.error, OSError):
            self.menu_font = pygame.font.SysFont("arial", 17, bold=True)
            self.menu_small = pygame.font.SysFont("arial", 15)
            self.menu_title = pygame.font.SysFont("arial", 43, bold=True)
        self.font = pygame.font.SysFont("consolas,dejavusansmono,arial", 16, bold=True)
        self.big = pygame.font.SysFont("consolas,dejavusansmono,arial", 44, bold=True)
        self.small = pygame.font.SysFont("consolas,dejavusansmono,arial", 13)
        skull_path = pygame.font.match_font("segoeuisymbol") or pygame.font.match_font("seguisym") or pygame.font.match_font("arial")
        try:
            self.skull_font = pygame.font.Font(skull_path, 18) if skull_path else self.menu_font
        except (pygame.error, OSError):
            self.skull_font = self.menu_font
        self._bg_cache = None
        self._bg_key = None
        self._merchant_intro_room = None
        self._merchant_intro_start = 0.0
        self._decor_light_cache = {}
        self._decoration_collider_cache = {}
        self._decoration_mask_cache = {}
        self._circle_mask_cache = {}
        self._merchant_room_seen = set()
        self._confusion_star_cache = {}
        self._fit_cache = {}
        self._player_flip_cache = {}
        self._weapon_rotation_cache = {}
        self._rotation_cache = {}
        # Cachés de sprites de enemigos. Se inicializan aquí porque el render puede
        # necesitarlas desde el primer frame de una partida.
        self._enemy_frame_cache = {}
        self._enemy_flash_cache = {}
        self._light_surface_cache = {}
        self._hazard_surface_cache = {}
        self._ambient_surface = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        self._ambient_surface.fill((6, 9, 20, 66))
        self._shadow_layer = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        self._lights_surface = pygame.Surface((VIEW_W, VIEW_H))
        self._player_light_surface = pygame.Surface((VIEW_W, VIEW_H))
        self._pillar_positions_cache = {}
        # Caché por frame para evitar recalcular iluminación y sombras para cada actor.
        self._actor_light_cache = {}
        self._shadow_frame = 0
        self._shadow_refresh_interval = 2
        self._last_shadow_room_key = None
        self.chest_images = {}
        self.chest_type_images = {}
        self.decoration_images = {}
        self.decoration_frames = {}
        self.npc_frames = {}
        self.merchant_variants = []
        self.drone_frames = []
        self.special_effect_frames = {}
        self.weapon_variant_frames = {}
        # Animaciones de movimiento de los seis personajes jugables. Cada spritesheet
        # contiene 8 fotogramas en una tira horizontal. Los fotogramas se normalizan
        # al tamaño de render del jugador para conservar la escala del juego y evitar
        # desplazamientos causados por el espacio transparente de los PNG.
        self.player_walk_frames = {}
        # Overlay WEBP de la habilidad Bastion de Kael. Se carga de forma opcional
        # para que la ausencia del recurso nunca impida iniciar el juego.
        self.ability_shield_image = None
        self.dash_icon = None
        self.shield_icon = None
        self.key_bindings = {"dash": "space", "ability": "q"}
        self.ui_atlas = UIAtlas()
        # Los iconos del HUD son opcionales para que el juego arranque antes de que
        # el usuario añada sus PNG/WebP a assets/icons/.
        icon_dir = Path(__file__).resolve().parent.parent / "assets" / "icons"
        character_dir = Path(__file__).resolve().parent.parent / "assets" / "characters"
        for attr, path in (
            ("shield_icon", icon_dir / "Escudo.png"),
            ("dash_icon", icon_dir / "dash.png"),
        ):
            try:
                if path.is_file():
                    setattr(self, attr, pygame.image.load(str(path)).convert_alpha())
            except (pygame.error, OSError, ValueError):
                setattr(self, attr, None)
        ability_path = icon_dir / "habilidadescudo.webp"
        if not ability_path.is_file():
            ability_path = character_dir / "habilidadescudo.webp"
        try:
            if ability_path.is_file():
                self.ability_shield_image = pygame.image.load(str(ability_path)).convert_alpha()
        except (pygame.error, OSError, ValueError):
            self.ability_shield_image = None
        # Sprites de los personajes jugables. El archivo de cada personaje tiene
        # ocho fotogramas de 192 px de ancho. Se recorta el contenido transparente
        # y se ajusta a 48x52, que es el tamaño visual que ya utilizaba el jugador.
        player_sprite_files = {
            "soldier": "kael_sprite.png",
            "medic": "iria_sprite.png",
            "vanguard": "rook_sprite.png",
            "pyromancer": "veyra_sprite.png",
            "striker": "nox_sprite.png",
            "engineer": "mira_sprite.png",
        }
        for character_id, filename in player_sprite_files.items():
            character_path = character_dir / filename
            frames = []
            if not character_path.is_file():
                continue
            try:
                sheet = pygame.image.load(str(character_path)).convert_alpha()
                frame_w = sheet.get_width() // 8
                if frame_w <= 0:
                    continue
                for frame_index in range(8):
                    source = pygame.Surface((frame_w, sheet.get_height()), pygame.SRCALPHA)
                    source.blit(
                        sheet,
                        (0, 0),
                        pygame.Rect(frame_index * frame_w, 0, frame_w, sheet.get_height()),
                    )
                    # Ignorar residuos alpha casi transparentes de los bordes.
                    bbox = source.get_bounding_rect(min_alpha=20)
                    if bbox.width <= 0 or bbox.height <= 0:
                        continue
                    cropped = source.subsurface(bbox).copy()
                    scale = min(48 / cropped.get_width(), 52 / cropped.get_height())
                    target_size = (
                        max(1, round(cropped.get_width() * scale)),
                        max(1, round(cropped.get_height() * scale)),
                    )
                    sprite = pygame.transform.scale(cropped, target_size)
                    normalized = pygame.Surface((48, 52), pygame.SRCALPHA)
                    normalized.blit(
                        sprite,
                        (
                            (48 - target_size[0]) // 2,
                            52 - target_size[1],
                        ),
                    )
                    frames.append(normalized)
            except (pygame.error, OSError, ValueError):
                frames = []
            if frames:
                self.player_walk_frames[character_id] = frames
        self.asset_root = Path(__file__).resolve().parent.parent / "assets"
        # Sprites de cajas y barriles destructibles. Coloca los PNG en assets/props/.
        # Si falta alguno o no puede cargarse, el renderizado usa el dibujo provisional.
        self.prop_images = {}
        # Modelo dedicado de cargador: no existe un PNG de munición entre los
        # assets actuales, así que se construye una pequeña silueta pixel-art
        # transparente con la misma paleta del juego.
        self.ammo_magazine_image = pygame.Surface((24,30), pygame.SRCALPHA)
        pygame.draw.rect(self.ammo_magazine_image,(18,22,29,255),(4,1,16,28),border_radius=3)
        pygame.draw.rect(self.ammo_magazine_image,(62,70,84,255),(6,3,12,23),border_radius=2)
        pygame.draw.rect(self.ammo_magazine_image,(95,104,118,255),(8,4,8,21))
        for yy in (6,11,16,21):
            pygame.draw.rect(self.ammo_magazine_image,(214,169,70,255),(9,yy,6,2))
            pygame.draw.rect(self.ammo_magazine_image,(245,211,118,255),(10,yy,4,1))
        pygame.draw.rect(self.ammo_magazine_image,(15,19,25,255),(5,25,14,4))
        prop_dir = self.asset_root / "props"
        prop_files = {
            "crate": "caja.png",
            "crate_broken": "cajarota.png",
            "fire": "barriligneo.png",
            "poison": "barrilveneno.png",
            "electric": "barrilelectrico.png",
            "barrel_broken": "barrilroto.png",
        }
        for key, filename in prop_files.items():
            path = prop_dir / filename
            if path.is_file():
                try: