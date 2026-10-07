"""Dibujado con pygame. Solo lee el estado de la simulación; no la modifica."""
import math
import random
import pygame
from pathlib import Path
from .world import TILE, FLOOR, WALL, PILLAR, SECRET, TORCH_PILLAR, bonfire_positions
from .ui_atlas import UIAtlas
from .assets import AssetRegistry
from .assets.bounds import decoration_max_size
from .rendering.atlas_geometry import alpha_runs, split_grid_frames
from .rendering.sprite_geometry import fit_dimensions
from .rendering.weapon_geometry import melee_grip_anchor, weapon_max_dimension
from .rendering.background_geometry import trim_edge_background
from .rendering.rotation_geometry import quantized_facing_flip, quantized_sprite_angle
from .rendering.atlas_background import make_background_transparent
from .rendering.animation_geometry import animation_frame_index
from .rendering.wall_geometry import wall_piece_key

VIEW_W, VIEW_H = 960, 540


class Renderer:
    def __init__(self, data):
        self.data = data
        # Compatibilidad: el renderer conserva sus loaders actuales, pero todas
        # las definiciones declarativas ya disponen de una identidad central.
        self.asset_registry = getattr(data, "asset_registry", None) or AssetRegistry()
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
            if not character_path.is_file():
                continue
            frames = []
            try:
                sheet = pygame.image.load(str(character_path)).convert_alpha()
                frame_count = 8
                frame_w = sheet.get_width() // frame_count
                if frame_w <= 0 or sheet.get_width() < frame_count:
                    continue

                # Los seis sheets actuales son tiras horizontales de exactamente
                # ocho celdas. Cada índice se conserva aunque una celda tenga muy
                # poco alpha, evitando que un frame vacío desplace los siguientes.
                for frame_index in range(frame_count):
                    left = round(frame_index * sheet.get_width() / frame_count)
                    right = round((frame_index + 1) * sheet.get_width() / frame_count)
                    source = pygame.Surface(
                        (max(1, right - left), sheet.get_height()), pygame.SRCALPHA
                    )
                    source.blit(
                        sheet,
                        (0, 0),
                        pygame.Rect(left, 0, max(1, right - left), sheet.get_height()),
                    )
                    bbox = source.get_bounding_rect(min_alpha=8)
                    if bbox.width <= 0 or bbox.height <= 0:
                        # Placeholder fijo: el frame sigue ocupando su índice.
                        frames.append(pygame.Surface((48, 52), pygame.SRCALPHA))
                        continue

                    cropped = source.subsurface(bbox).copy()
                    scale = min(48 / cropped.get_width(), 52 / cropped.get_height())
                    target_size = (
                        max(1, round(cropped.get_width() * scale)),
                        max(1, round(cropped.get_height() * scale)),
                    )
                    sprite = pygame.transform.smoothscale(cropped, target_size)
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

            # Solo publicamos la animación si quedaron los ocho índices.
            if len(frames) == 8:
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
                    image = pygame.image.load(str(path)).convert_alpha()
                    if image.get_width() > 0 and image.get_height() > 0:
                        # Las cajas ocupan una casilla (44x44); los barriles conservan 48x48.
                        target_size = (TILE, TILE) if key in ("crate", "crate_broken") else (48, 48)
                        self.prop_images[key] = pygame.transform.scale(image, target_size)
                except (pygame.error, OSError):
                    pass

        # Animación de hoguera opcional. Admite seis PNG separados (hoguera1.png ...
        # hoguera6.png) o, como alternativa, una tira horizontal llamada hoguera.png
        # con fotogramas transparentes de 64x64. Los archivos separados tienen prioridad.
        # Ruta alternativa compatible: assets/props/hoguera.png.
        self.bonfire_frames = []
        separate_frames_found = False
        for frame_index in range(1, 7):
            frame_path = prop_dir / f"hoguera{frame_index}.png"
            if not frame_path.is_file():
                continue
            separate_frames_found = True
            try:
                frame = pygame.image.load(str(frame_path)).convert_alpha()
                if frame.get_width() > 0 and frame.get_height() > 0:
                    self.bonfire_frames.append(pygame.transform.scale(frame, (48, 48)))
            except (pygame.error, OSError, ValueError):
                # Un fotograma inválido se omite sin impedir que carguen los demás.
                continue

        # Compatibilidad con el formato de spritesheet anterior.
        bonfire_path = prop_dir / "hoguera.png"
        if not separate_frames_found and bonfire_path.is_file():
            try:
                sheet = pygame.image.load(str(bonfire_path)).convert_alpha()
                frame_w = frame_h = 64
                frame_count = max(1, sheet.get_width() // frame_w)
                if sheet.get_height() >= frame_h:
                    for frame_index in range(frame_count):
                        frame = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
                        frame.blit(sheet, (0, 0), pygame.Rect(frame_index * frame_w, 0, frame_w, frame_h))
                        self.bonfire_frames.append(pygame.transform.scale(frame, (48, 48)))
            except (pygame.error, OSError, ValueError):
                self.bonfire_frames = []

        # Monedas animadas: cinco PNG independientes en assets/props/.
        # Se cargan los fotogramas disponibles en orden y se mantiene un dibujo
        # provisional si no hay ninguno, para que las monedas sigan siendo visibles.
        # Portal animado: seis PNG opcionales en assets/portal/.
        self.portal_frames=[]
        portal_dir=self.asset_root / "portal"
        for frame_index in range(1,7):
            path=portal_dir / f"portalframe{frame_index}.png"
            if not path.is_file(): continue
            try:
                image=pygame.image.load(str(path)).convert_alpha()
                if image.get_width()>0 and image.get_height()>0: self.portal_frames.append(image)
            except (pygame.error,OSError,ValueError): pass

        self.coin_frames = []
        for frame_index in range(1, 6):
            frame_path = prop_dir / f"moneda{frame_index}.png"
            if not frame_path.is_file():
                continue
            try:
                frame = pygame.image.load(str(frame_path)).convert_alpha()
                if frame.get_width() > 0 and frame.get_height() > 0:
                    self.coin_frames.append(pygame.transform.smoothscale(frame, (22, 22)))
            except (pygame.error, OSError, ValueError):
                continue

        # Texturas de escenarios opcionales: una losa repetida por sala y atlas de paredes.
        self.floor_images = {}
        floor_dir = self.asset_root / "floors"
        for number in range(1, 12):
            path = floor_dir / f"suelo{number}.png"
            if path.is_file():
                try:
                    image = pygame.image.load(str(path)).convert_alpha()
                    tile_image = pygame.transform.scale(image, (TILE, TILE))
                    tile_image.fill((224, 228, 238, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    self.floor_images[number] = tile_image
                except (pygame.error, OSError):
                    pass
        # Superficies nuevas: son opcionales y reemplazan gradualmente a los atlas
        # antiguos cuando el usuario los coloque en assets/floors/.
        self.named_floor_images = {}
        for name in ("arena","hierba","ladrillos","ladrillosdepiedra","madera","roca","rocanegra"):
            path=floor_dir / f"Superficie_{name}.png"
            if path.is_file():
                try:
                    image=pygame.image.load(str(path)).convert_alpha()
                    self.named_floor_images[name]=pygame.transform.scale(image,(TILE,TILE))
                except (pygame.error,OSError,ValueError):
                    pass
        new_floor_dir = floor_dir / "new"
        if new_floor_dir.is_dir():
            for path in sorted(new_floor_dir.glob("*.png")):
                try:
                    image=pygame.image.load(str(path)).convert_alpha()
                    bbox=image.get_bounding_rect(min_alpha=8)
                    if bbox.width and bbox.height:
                        image=image.subsurface(bbox).copy()
                    self.named_floor_images[path.stem]=pygame.transform.scale(image,(TILE,TILE))
                except (pygame.error,OSError,ValueError):
                    pass
        self.wall_top_images = {}
        self.wall_fill_images = {}
        # walls.png contiene cinco modelos completos ya orientados:
        # diagonal ascendente, diagonal descendente, frente horizontal y dos laterales.
        # Se extraen por sus cinco regiones horizontales reales; nunca por tercios.
        self.wall_piece_images = {}
        self.wall_models = {}
        wall_dir = self.asset_root / "walls"
        new_wall_path = wall_dir / "walls.png"
        if new_wall_path.is_file():
            try:
                atlas = pygame.image.load(str(new_wall_path)).convert_alpha()
                atlas = make_background_transparent(atlas, (255, 255, 255), 18)
                alpha = pygame.surfarray.array_alpha(atlas)
                occupied = alpha.max(axis=0) > 8
                runs = [
                    (int(x0), int(x1))
                    for x0, x1 in alpha_runs(occupied)
                    if int(x1) - int(x0) + 1 >= 8
                ]
                # El atlas tiene separaciones estrechas entre algunos modelos.
                # Un 1.2% evita fusionar el diagonal inferior con el frontal.
                merge_gap = max(6, int(atlas.get_width() * 0.012))
                merged = []
                for x0, x1 in runs:
                    if merged and x0 - merged[-1][1] - 1 <= merge_gap:
                        merged[-1] = (merged[-1][0], x1)
                    else:
                        merged.append((x0, x1))

                rects = []
                for x0, x1 in merged:
                    group_alpha = alpha[:, x0:x1 + 1]
                    y_mask = group_alpha.max(axis=1) > 8
                    y_runs = alpha_runs(y_mask)
                    if not y_runs:
                        continue
                    y0 = int(y_runs[0][0])
                    y1 = int(y_runs[-1][1])
                    rect = pygame.Rect(x0, y0, x1 - x0 + 1, y1 - y0 + 1)
                    if rect.width >= 8 and rect.height >= 8:
                        rects.append(rect)

                if len(rects) != 5:
                    # Fallback para pequeñas interrupciones de alpha dentro de una pared.
                    mask = pygame.mask.from_surface(atlas, threshold=8)
                    components = mask.connected_components(minimum=40)
                    component_rects = []
                    for component in components:
                        # pygame-ce 2.5.x devuelve Mask en connected_components().
                        # Mask expone get_bounding_rects(), no get_bounding_rect().
                        # Cada componente es una región conectada; aun así unimos
                        # todos sus rectángulos para mantener compatibilidad con
                        # posibles componentes fragmentados.
                        component_rects_for_mask = component.get_bounding_rects()
                        if not component_rects_for_mask:
                            continue
                        bbox = component_rects_for_mask[0].copy()
                        for component_rect in component_rects_for_mask[1:]:
                            bbox.union_ip(component_rect)
                        if bbox.width >= 8 and bbox.height >= 8:
                            component_rects.append(bbox)
                    component_rects.sort(key=lambda r: (r.left, r.top))
                    grouped = []
                    for rect in component_rects:
                        if grouped:
                            prev = grouped[-1]
                            gap = rect.left - prev.right
                            vertical_overlap = min(prev.bottom, rect.bottom) - max(prev.top, rect.top)
                            if gap <= max(18, int(atlas.get_width() * 0.015)) and vertical_overlap > -max(prev.height, rect.height) * 0.45:
                                grouped[-1] = prev.union(rect)
                                continue
                        grouped.append(rect)
                    rects = grouped

                if len(rects) != 5:
                    raise ValueError(f"walls.png debe contener 5 modelos completos; regiones detectadas: {len(rects)}")

                for name, rect in zip(
                    ("diag_rising", "diag_falling", "front", "vertical_a", "vertical_b"),
                    sorted(rects, key=lambda r: r.left),
                ):
                    frame = atlas.subsurface(rect).copy()
                    if frame.get_width() > 0 and frame.get_height() > 0:
                        self.wall_models[name] = frame
                self.wall_models["left"] = self.wall_models.get("vertical_a")
                self.wall_models["right"] = self.wall_models.get("vertical_b")
            except (pygame.error, OSError, ValueError):
                self.wall_models = {}

        # Columnas arquitectónicas: huella de una casilla y altura visual de dos.
        # La versión con antorcha reemplaza los faroles decorativos del escenario.
        self.column_image = None
        self.torch_column_image = None
        for attr, filename, target_size in (
            ("column_image", "columna.png", (TILE, TILE * 2)),
            ("torch_column_image", "columnaconantorcha.png", (TILE, TILE * 2)),
        ):
            # Los PNG arquitectónicos se entregaron en assets/walls/. Se acepta
            # también assets/props/ para conservar compatibilidad con versiones previas.
            candidates = (wall_dir / filename, self.asset_root / "props" / filename)
            path = next((candidate for candidate in candidates if candidate.is_file()), None)
            if path is not None:
                try:
                    image = pygame.image.load(str(path)).convert_alpha()
                    if image.get_width() > 0 and image.get_height() > 0:
                        scaled_image = pygame.transform.smoothscale(image, (TILE, TILE * 2))
                        setattr(self, attr, scaled_image)
                except (pygame.error, OSError, ValueError):
                    pass


        wall_atlas_path = wall_dir / "wall2.png"
        if wall_atlas_path.is_file():
            try:
                atlas = pygame.image.load(str(wall_atlas_path)).convert_alpha()
                # wall2.png usa gris claro (RGB 184,184,184) como fondo vacío.
                atlas = make_background_transparent(atlas, (184, 184, 184), 5)
                # La pieza de la esquina superior izquierda contiene el remate de ladrillos.
                cap_w = min(56, atlas.get_width())
                cap_h = min(28, atlas.get_height())
                cap = atlas.subsurface(pygame.Rect(0, 0, cap_w, cap_h)).copy()
                self.wall_top_images["default"] = pygame.transform.scale(cap, (TILE, TILE))
            except (pygame.error, OSError, ValueError):
                pass

        cobbles_path = wall_dir / "cobbles2.png"
        if cobbles_path.is_file():
            try:
                atlas = pygame.image.load(str(cobbles_path)).convert_alpha()
                # cobbles2.png usa gris medio (RGB 166,166,166); antes quedaba opaco
                # y formaba rectángulos grises alrededor de las paredes.
                atlas = make_background_transparent(atlas, (166, 166, 166), 5)
                # El atlas contiene tres bandas reales de piedra; la cuarta era fondo vacío.
                band_count = 3
                band_h = max(1, atlas.get_height() // 4)
                crop_w = min(56, atlas.get_width())
                for band in range(band_count):
                    y = band * band_h
                    h = min(band_h, atlas.get_height() - y)
                    crop = atlas.subsurface(pygame.Rect(0, y, crop_w, h)).copy()
                    self.wall_fill_images[str(band)] = pygame.transform.scale(crop, (TILE, TILE))
            except (pygame.error, OSError, ValueError):
                pass
        asset_dir = self.asset_root / "chests"
        for state, filename in (("closed", "chest_closed.png"), ("open", "chest_open.png")):
            path = asset_dir / filename
            if path.is_file():
                try:
                    self.chest_images[state] = pygame.image.load(str(path)).convert_alpha()
                except (pygame.error, OSError):
                    pass

        # Cofres temáticos del nuevo paquete: el color comunica el tipo de recompensa.
        decoration_dir = self.asset_root / "decorations"
        chest_variants = {"common":"green", "rare":"purple", "legendary":"gold", "weapon":"red", "item":"purple"}
        for chest_type, color_name in chest_variants.items():
            for state in ("closed", "open"):
                path = decoration_dir / f"chest_{color_name}_{state}.png"
                if path.is_file():
                    try:
                        self.chest_type_images[(chest_type, state)] = pygame.image.load(str(path)).convert_alpha()
                    except (pygame.error, OSError):
                        pass

        fountain_names = {"fountain_active", "fountain_inactive", "fountain_small"}
        for name in (
            "bench_large", "bench_small", "barrel_large", "signpost", "crate_stack", "crate_pair",
            "table", "counter", "wood_chest_decor", "fountain_active", "fountain_inactive",
            "fountain_small", "well_empty", "statue_goddess", "statue_archer", "statue_assassin",
            "statue_knight", "statue_mage", "bush_1", "bush_2", "bush_3", "bush_4", "bush_5",
            "bush_6", "rock_1", "rock_2", "rock_3", "rock_4", "rock_5", "rock_6",
        ):
            path = decoration_dir / f"{name}.png"
            if not path.is_file():
                continue
            try:
                if name in fountain_names:
                    frames = self._load_sheet_frames(path)
                    if frames:
                        self.decoration_frames[name] = frames
                        # Keep the first frame as fallback for code paths that expect an image.
                        self.decoration_images[name] = frames[0]
                else:
                    self.decoration_images[name] = pygame.image.load(str(path)).convert_alpha()
            except (pygame.error, OSError, ValueError):
                pass

        npc_dir = self.asset_root / "npcs"
        merchant_dir = npc_dir / "merchants"
        for index in range(1, 4):
            path = merchant_dir / f"merchant{index}.png"
            if path.is_file():
                # Los merchants son spritesheets regulares: merchant1/2 = 4x4 y merchant3 = 6x4.
                # No usar connected-components aqui porque puede confundir partes internas del sprite
                # con modelos separados. merchant3 necesita conservar sus 24 celdas en orden fila/columna.
                if index == 3:
                    frames = self._load_merchant_sheet_frames(path, cols=6, rows=4)
                else:
                    frames = self._load_merchant_sheet_frames(path, cols=4, rows=4)
                    if not frames:
                        frames = self._load_component_frames(path, minimum=30, merge_gap=5, exclude_large=(index == 1))
                if not frames:
                    frames = self._load_sheet_frames(path)
                if frames:
                    self.merchant_variants.append(frames)
        if not self.merchant_variants:
            for name, filename in {
                "merchant_idle":"merchant_idle.png", "merchant_near":"merchant_near.png",
            }.items():
                path = npc_dir / filename
                if path.is_file():
                    frames = self._load_sheet_frames(path)
                    if frames: self.npc_frames[name] = frames
        drone_path = npc_dir / "mira_drone.png"
        if drone_path.is_file():
            drone = self._load_component_frames(drone_path, minimum=20, merge_gap=4)
            self.drone_frames = drone[:1] if drone else []

        self.door_front_frames = self._load_door_frames(self.asset_root / "doors" / "front_open_closed.png")
        self.door_side_frames = self._load_door_frames(self.asset_root / "doors" / "side_open_closed.png")

        # Decoraciones nuevas por bioma. Se cargan como spritesheets para
        # aprovechar todas las variantes transparentes que contenga cada PNG.
        biome_decor_dir = self.asset_root / "decorations" / "biomes"
        biome_decor_files = {
            "biome_red_bush": "Arbustosrojizos.png",
            "biome_lava_rock": "decoracionesrocosasdezonadelava.png",
            "biome_lava_rock_purple": "decoracionesrocosasparazonadelavamorada.png",
            "biome_shared_rock": "decoracionesrocosasparavariosbiomas.png",
        }
        for kind, filename in biome_decor_files.items():
            path = biome_decor_dir / filename
            if path.is_file():
                frames = self._load_component_frames(path, minimum=12, merge_gap=8)
                if not frames:
                    frames = self._load_sheet_frames(path)
                if frames:
                    self.decoration_frames[kind] = frames
                    self.decoration_images[kind] = frames[0]

        # Sprites transparentes de armas, proyectiles y consumibles.
        self.weapon_images = {}
        self.weapon_scaled_images = {}
        self.projectile_images = {}
        self.projectile_scaled_images = {}
        # Animaciones de combate nuevas. Se cargan de forma opcional para mantener
        # compatibilidad con instalaciones que aun no tengan los PNG.
        self.melee_slash_frames = self._load_animation_frames("cortearmameleeframe", 6)
        self.explosion_frames = self._load_animation_frames("explosionframe", 8)
        self.ignite_projectile_frames = self._load_animation_frames("proyectiligneoframe", 6)
        self.frozen_image = None
        frozen_path = self.asset_root / "effects" / "congelado.png"
        try:
            if frozen_path.is_file():
                self.frozen_image = pygame.image.load(str(frozen_path)).convert_alpha()
                bbox = self.frozen_image.get_bounding_rect(min_alpha=1)
                if bbox.width and bbox.height:
                    self.frozen_image = self.frozen_image.subsurface(bbox).copy()
        except (pygame.error, OSError, ValueError):
            self.frozen_image = None

        arrow_frames = []
        for arrow_index in range(1, 4):
            arrow_path = self.asset_root / "effects" / f"boss_arrow{arrow_index}.png"
            if arrow_path.is_file():
                arrow_frames.extend(self._load_sheet_frames(arrow_path))
        self.special_effect_frames["arrow"] = arrow_frames
        for key, filename in (("tornado","ground_tornado.png"),("water","ground_water.png"),("fire_ground","ground_fire.png"),("large_explosion","large_explosion.png"),("lightning","falling_lightning.png")):
            path = self.asset_root / "effects" / filename
            if path.is_file():
                frames = self._load_sheet_frames(path)
                if frames: self.special_effect_frames[key] = frames
        new_effect_dir = self.asset_root / "effects" / "new"
        fireball_path = new_effect_dir / "boladefuego_spritesheet.png"
        if fireball_path.is_file():
            frames = self._load_grid_frames(fireball_path, 4, 2)
            if frames:
                self.special_effect_frames["new_fireball"] = frames
        ability_atlas_path = new_effect_dir / "spritesheesdeeffectosparahabilidades.png"
        if ability_atlas_path.is_file():
            frames = self._load_component_frames(ability_atlas_path, minimum=8, merge_gap=1)
            if not frames:
                frames = self._load_sheet_frames(ability_atlas_path)
            if frames:
                # El atlas contiene efectos independientes. Cada habilidad recibe
                # un único componente, evitando que varios efectos se superpongan.
                self.special_effect_frames["new_ability_atlas"] = frames
                for idx, key in enumerate(("ability_shield","ability_heal","ability_burst","ability_freeze","ability_haste","ability_drone")):
                    if idx < len(frames):
                        self.special_effect_frames[key] = [frames[idx]]

        # Enemy sprites supplied as transparent spritesheets. Frames are detected
        # from transparent gaps, so sheets may contain different frame sizes and
        # even multiple rows (the assets do not need to be normalized manually).
        self.enemy_sprites = {}
        self.enemy_variant_sprites = {}
        self.enemy_variant_tints = {}
        self.enemy_variant_params = {}
        self.enemy_projectile_frames = {}
        enemy_dir = self.asset_root / "enemies"
        enemy_specs = {
            "esbirromago": {"idle":"esbirromago/esbirromagoquieto.png","walk":"esbirromago/esbirromago_caminando.png","run":"esbirromago/esbirromago_corriendo.png","attack":"esbirromago/esbirromago_atacando.png","death":"esbirromago/esbirromago_muerte.png"},
            "gargola": {"walk":"Gargola/gargola_moviendose.png","attack":"Gargola/gargola_atacandomelee.png","death":"Gargola/gargola_muerte.png"},
            "minigolem": {"idle":"Minigolem/minigolemdepiedra_quieto.png","walk":"Minigolem/minigolemdepiedra_caminando.png","attack":"Minigolem/minigolemdepiedra_lanzandoroca.png","death":"Minigolem/minigolemdepiedra_muerte.png","projectile":"Minigolem/Proyectilrocadelgolem.png"},
            "nomuerto": {"walk":"Nomuerto/NoMuerto_caminando.png","attack":"Nomuerto/NoMuerto_atacando.png","death":"Nomuerto/NoMuerto_muriendo.png"},
            "nomuerto2": {"walk":"Nomuerto2/NoMuerto_caminando2.png","attack":"Nomuerto2/NoMuerto_atacando2.png","death":"Nomuerto2/NoMuerto_muriendo2.png"},
            "monodehielo": {"walk":"Monodehielo/Monodehielo_caminando.png","attack":"Monodehielo/Monodehielo_atacando.png","death":"Monodehielo/Monodehielo_muriendo.png"},
            "minotaurogigante": {"idle":"Minotaurogigante/MinotauroGigante_quieto.png","attack":"Minotaurogigante/MinotauroGigante_ataque.png","death":"Minotaurogigante/MinotauroGigante_muerte.png"},
            "skeleton": {"walk":"skeleton/walk.png","attack":"skeleton/attack.png","death":"skeleton/death.png"},
            "ghost": {"walk":"ghost/walk.png","attack":"ghost/attack.png","death":"ghost/death.png","projectile":"ghost/projectile.png"},
            "goblin": {"walk":"goblin/walk.png","attack":"goblin/attack.png","death":"goblin/death.png"},
            "orc": {"walk":"orc/walk.png","attack":"orc/attack.png","death":"orc/death.png"},
            "demon": {"walk":"demon/walk.png","attack":"demon/attack.png","death":"demon/death.png","projectile":"demon/projectile.png"},
            "slime": {"walk":"slime/walk.png","attack":"slime/attack.png","death":"slime/death.png","projectile":"slime/projectile.png"},
            "dead_knight": {"walk":"dead_knight/walk.png","attack":"dead_knight/walk.png"},
            "small_demon_assassin": {"walk":"small_demon_assassin/walk.png","attack":"small_demon_assassin/attack.png","death":"small_demon_assassin/death.png"},
            "small_demon_ranged": {"walk":"small_demon_ranged/walk.png","attack":"small_demon_ranged/attack.png","death":"small_demon_ranged/death.png","projectile":"small_demon_ranged/projectile.png"},
            "small_demon_melee": {"walk":"small_demon_melee/walk.png","attack":"small_demon_melee/attack.png","death":"small_demon_melee/death.png"},
            "mage2": {"idle":"mage2/idle.png","walk":"mage2/idle.png","attack":"mage2/idle.png"},
            "ogro": {"idle":"Ogro/Ogro.png","walk":"Ogro/Ogro.png","attack":"Ogro/Ogro.png","attack_heavy":"Ogro/Ogro.png"},
            # Este enemigo es un spritesheet 3x4; se carga exclusivamente con
            # _load_grid_frames más abajo para no confundirlo con un atlas libre.
            "new_flyer": {},
        }
        for key, spec in enemy_specs.items():
            loaded = {}
            for anim, rel in spec.items():
                path = enemy_dir / rel
                if path.is_file():
                    frames = self._load_sheet_frames(path)
                    if frames:
                        loaded[anim] = frames
            if loaded:
                self.enemy_sprites[key] = loaded
        flyer_path = enemy_dir / "flying" / "enemigovolador_spritesheet.png"
        if flyer_path.is_file():
            # Este asset es una cuadrícula 3x4. Si el detector de cuadrícula
            # rechaza la hoja por dimensiones/márgenes inesperados, intentamos
            # inmediatamente el loader de spritesheet antes de dejar el enemigo
            # sin representación visual.
            flyer_frames = self._load_grid_frames(flyer_path, 3, 4)
            if not flyer_frames:
                flyer_frames = self._load_sheet_frames(flyer_path)
            if flyer_frames:
                self.enemy_sprites.setdefault("new_flyer", {})
                self.enemy_sprites["new_flyer"] = {
                    "walk": flyer_frames,
                    "attack": flyer_frames,
                    "death": flyer_frames,
                }

        # Ningún enemigo/boss declarado puede llegar al runtime con un sprite_set
        # que no haya producido al menos una animación utilizable.
        missing_enemy_models = []
        for entity_id, entity in self.data.enemies.items():
            key = getattr(entity, "sprite_set", None)
            anims = self.enemy_sprites.get(key, {}) if key else {}
            if not key or not any(anims.get(name) for name in ("idle", "walk", "run", "attack", "attack_heavy")):
                missing_enemy_models.append(f"enemy:{entity_id}:{key}")
        for boss_id, boss in self.data.bosses.items():
            key = getattr(boss, "sprite_set", None)
            anims = self.enemy_sprites.get(key, {}) if key else {}
            if not key or not any(anims.get(name) for name in ("idle", "walk", "run", "attack", "attack_heavy")):
                missing_enemy_models.append(f"boss:{boss_id}:{key}")
        if missing_enemy_models:
            raise RuntimeError("Modelos de enemigos no cargados: " + ", ".join(missing_enemy_models))

        self.misc_images = {}
        for wid, wdef in self.data.weapons.items():
            sprite_path = getattr(wdef, "weapon_sprite", None)
            if sprite_path:
                image = self._load_trimmed_asset(sprite_path)
                if image is not None:
                    self.weapon_images[wid] = image
                    max_dim = self._weapon_max_dimension(getattr(wdef, "class", "pistol"))
                    self.weapon_scaled_images[wid] = self._fit_image(image, max_dim)
            projectile_path = getattr(wdef, "projectile_sprite", None)
            if projectile_path and projectile_path not in self.projectile_images:
                image = self._load_trimmed_asset(projectile_path)
                if image is not None:
                    self.projectile_images[projectile_path] = image
        new_weapon_dir = self.asset_root / "weapons" / "new"
        ranged_atlas = new_weapon_dir / "modelosarmas.png"
        # El atlas melee fue retirado porque su mapeado no era fiable.
        # Las armas cuerpo a cuerpo usan únicamente sus PNG individuales.
        if ranged_atlas.is_file():
            frames = self._load_ranged_weapon_atlas(ranged_atlas)
            if frames:
                self.weapon_variant_frames["ranged"] = frames

        self.default_projectiles = {
            "physical": "assets/projectiles/projectile_06.png",
            "energy": "assets/projectiles/projectile_02.png",
            "fire": "assets/projectiles/projectile_03.png",
            "ice": "assets/projectiles/projectile_10.png",
            "void": "assets/projectiles/projectile_11.png",
            "radiant": "assets/projectiles/projectile_03.png",
            "explosive": "assets/projectiles/projectile_04.png",
        }
        for path in set(self.default_projectiles.values()):
            if path not in self.projectile_images:
                image = self._load_trimmed_asset(path)
                if image is not None:
                    self.projectile_images[path] = image
        for key, filename in (("heal", "healing.png"), ("energy", "energy.png")):
            image_path = self.asset_root / "misc" / filename
            if image_path.is_file():
                try:
                    image = pygame.image.load(str(image_path)).convert_alpha()
                    bbox=image.get_bounding_rect(min_alpha=8)
                    image=image.subsurface(bbox).copy() if bbox.width and bbox.height else image
                    if key=="energy":
                        mask=pygame.mask.from_surface(image,threshold=8)
                        image=mask.to_surface(setcolor=(255,220,45,255),unsetcolor=(0,0,0,0))
                        glow=pygame.Surface(image.get_size(),pygame.SRCALPHA)
                        glow.fill((255,220,50,34),special_flags=pygame.BLEND_RGBA_ADD)
                        image.blit(glow,(0,0),special_flags=pygame.BLEND_RGBA_ADD)
                    self.misc_images[key]=image
                except (pygame.error, OSError):
                    pass

        self._validate_loaded_weapon_assets()

    def _validate_loaded_weapon_assets(self):
        """Fail fast if a declared weapon model/projectile did not resolve to a runtime asset."""
        missing = []
        ranged_frames = self.weapon_variant_frames.get("ranged", [])
        for wid, wdef in self.data.weapons.items():
            sprite = getattr(wdef, "weapon_sprite", None)
            sheet = getattr(wdef, "weapon_sprite_sheet", None)
            index = getattr(wdef, "weapon_sprite_index", None)
            if sprite and wid not in self.weapon_images:
                missing.append(f"arma {wid}: modelo individual no cargado ({sprite})")
            elif sheet in ("ranged", "melee"):
                frames = self.weapon_variant_frames.get(sheet, [])
                if not isinstance(index, int) or index < 0 or index >= len(frames):
                    missing.append(f"arma {wid}: frame {sheet} {index} no disponible")
                else:
                    frame = frames[index]
                    if frame.get_width() <= 1 or frame.get_height() <= 1:
                        missing.append(f"arma {wid}: frame {sheet} {index} vacío")
            projectile = getattr(wdef, "projectile_sprite", None)
            if projectile and not str(projectile).startswith("__weapon_sheet__:") and projectile not in self.projectile_images:
                missing.append(f"arma {wid}: proyectil no cargado ({projectile})")
        if missing:
            raise RuntimeError("Assets de armas no resueltos: " + "; ".join(missing))

    def _asset_source_key(self, path):
        try:
            return path.resolve().relative_to(self.asset_root.parent.resolve()).as_posix()
        except (OSError, ValueError):
            return Path(path).as_posix()

    def _register_loaded_frame(
        self,
        category,
        path,
        frame_index,
        source_rect,
        frame,
        *,
        alpha_bounds=None,
        variant=None,
    ):
        """Registra un frame sin cambiar el resultado del loader existente."""
        source = self._asset_source_key(Path(path))
        asset_id = f"frame:{category}:{source}:{int(frame_index)}"
        self.asset_registry.register_runtime_frame(
            asset_id,
            category,
            source_file=source,
            frame_index=int(frame_index),
            source_rect=tuple(int(v) for v in source_rect),
            alpha_bounds=(
                tuple(int(v) for v in alpha_bounds)
                if alpha_bounds is not None else None
            ),
            visual_bounds=(
                tuple(int(v) for v in alpha_bounds)
                if alpha_bounds is not None else None
            ),
            variant=variant,
            handle=frame,
        )

    # Compatibility alias retained while atlas loaders migrate.
    _alpha_runs = staticmethod(alpha_runs)

    def _load_ranged_weapon_atlas(self, path):
        """Carga el atlas ranged respetando sus celdas alineadas.

        Los PNG nuevos están organizados como una hoja de modelos, no como una
        colección de componentes libres. Separar por connected_components es
        peligroso porque una misma arma puede tener varias piezas desconectadas
        y además cambia el índice cuando una pieza queda aislada. Primero
        buscamos una cuadrícula regular compatible con el número de armas
        declaradas; solo usamos componentes como último recurso.
        """
        try:
            image = pygame.image.load(str(path)).convert_alpha()
            expected = 0
            if hasattr(self, "data") and getattr(self.data, "weapons", None):
                indices = [
                    int(getattr(w, "weapon_sprite_index"))
                    for w in self.data.weapons.values()
                    if getattr(w, "weapon_sprite_sheet", None) == "ranged"
                    and isinstance(getattr(w, "weapon_sprite_index", None), int)
                ]
                expected = max(indices) + 1 if indices else 0
            if expected <= 0:
                expected = 11

            # Evaluamos cuadrículas razonables. Una hoja con armas alineadas
            # puede tener una celda vacía de separación, por lo que aceptamos
            # más celdas que modelos siempre que las vacías queden realmente
            # vacías. El aspecto de la imagen desempata entre 4x3, 3x4, etc.
            iw, ih = image.get_size()
            image_ratio = iw / max(1, ih)
            candidates = []
            for rows in range(2, 9):
                for cols in range(2, 9):
                    total = cols * rows
                    if total < expected or iw % cols or ih % rows:
                        continue
                    cell_w, cell_h = iw // cols, ih // rows
                    if cell_w < 8 or cell_h < 8:
                        continue
                    nonempty = 0
                    cells = []
                    for row in range(rows):
                        for col in range(cols):
                            rect = pygame.Rect(col * cell_w, row * cell_h, cell_w, cell_h)
                            cell = image.subsurface(rect)
                            bbox = cell.get_bounding_rect(min_alpha=8)
                            if bbox.width >= 2 and bbox.height >= 2:
                                nonempty += 1
                            cells.append((rect, bbox))
                    # Debe haber exactamente los modelos esperados. Si la
                    # hoja contiene una celda vacía, total puede ser expected+1.
                    if nonempty < expected:
                        continue
                    grid_ratio = cols / rows
                    ratio_error = abs(grid_ratio - image_ratio)
                    # Los modelos de munición/dardos están al final de la hoja,
                    # en la esquina inferior derecha. Penalizamos extras, pero
                    # no dejamos que esos extras desplacen el índice de las armas.
                    extra_penalty = max(0, nonempty - expected) * 0.55
                    empty_penalty = (total - nonempty) * 0.08
                    candidates.append((ratio_error + extra_penalty + empty_penalty, cols, rows, cells, nonempty))

            if candidates:
                _, cols, rows, cells, nonempty = min(candidates, key=lambda x: x[0])

                # El índice declarado por cada arma representa la celda física
                # del atlas, no el ordinal de las celdas que resultaron no vacías.
                # Mantener las celdas vacías conserva la geometría del spritesheet
                # y evita que un hueco separador desplace todos los modelos
                # siguientes.
                frames = []
                for physical_index, (rect, bbox) in enumerate(cells):
                    cell = image.subsurface(rect).copy()
                    if bbox.width and bbox.height:
                        frame = cell.subsurface(bbox).copy()
                        frames.append(frame)
                        self._register_loaded_frame(
                            "weapon-ranged", path, physical_index, rect, frame,
                            alpha_bounds=(bbox.x, bbox.y, bbox.width, bbox.height),
                        )
                    else:
                        frames.append(pygame.Surface((1, 1), pygame.SRCALPHA))
                return frames

            # Compatibilidad con hojas antiguas/no regulares.
            mask = pygame.mask.from_surface(image, threshold=8)
            components = mask.connected_components(minimum=18)
            rects = [rect for component in components for rect in component.get_bounding_rects()]
            rects = [r for r in rects if r.width >= 2 and r.height >= 2]
            rects.sort(key=lambda r: (r.top, r.left))
            frames = []
            for frame_index, rect in enumerate(rects):
                frame = image.subsurface(rect).copy()
                frames.append(frame)
                self._register_loaded_frame(
                    "weapon-ranged", path, frame_index, rect, frame,
                    alpha_bounds=(0, 0, rect.width, rect.height),
                )
            return frames
        except (pygame.error, OSError, ValueError):
            return []

    def _load_melee_weapon_atlas(self, path):
        """Carga modelos melee desde la cuadrícula física 6x6 del atlas.

        El índice del arma es el índice de celda, nunca el índice de un componente
        detectado. Esto evita que una espada con hoja/mango separados o una celda
        vacía desplace todos los modelos siguientes.
        """
        try:
            image = pygame.image.load(str(path)).convert_alpha()
            cols, rows = 6, 6
            expected = 36
            if hasattr(self, "data") and getattr(self.data, "weapons", None):
                indices = [
                    int(getattr(w, "weapon_sprite_index"))
                    for w in self.data.weapons.values()
                    if getattr(w, "weapon_sprite_sheet", None) == "melee"
                    and isinstance(getattr(w, "weapon_sprite_index", None), int)
                ]
                if indices:
                    expected = max(36, max(indices) + 1)

            # El atlas actual es aproximadamente cuadrado y contiene 36 celdas.
            # Usamos coordenadas redondeadas para que un PNG de 1195/1197 px no
            # acumule errores de división entre celdas.
            frames = []
            for index in range(expected):
                row, col = divmod(index, cols)
                if row >= rows:
                    frames.append(pygame.Surface((1, 1), pygame.SRCALPHA))
                    continue
                left = round(col * image.get_width() / cols)
                right = round((col + 1) * image.get_width() / cols)
                top = round(row * image.get_height() / rows)
                bottom = round((row + 1) * image.get_height() / rows)
                cell = image.subsurface(
                    pygame.Rect(left, top, max(1, right - left), max(1, bottom - top))
                ).copy()

                # Primero intentamos retirar únicamente un fondo claro conectado
                # al borde. Si el PNG ya tiene transparencia, esto no altera el
                # modelo; después el bbox alpha define su contorno real.
                cell = self._trim_edge_background(cell, white_threshold=248)
                bbox = cell.get_bounding_rect(min_alpha=8)
                if bbox.width and bbox.height:
                    frame = cell.subsurface(bbox).copy()
                    frames.append(frame)
                    self._register_loaded_frame(
                        "weapon-melee", path, index, pygame.Rect(left, top, max(1, right - left), max(1, bottom - top)),
                        frame, alpha_bounds=(bbox.x, bbox.y, bbox.width, bbox.height),
                    )
                else:
                    frames.append(pygame.Surface((1, 1), pygame.SRCALPHA))

            return frames
        except (pygame.error, OSError, ValueError):
            return []

    @staticmethod
    def _trim_edge_background(image, white_threshold=248):
        return trim_edge_background(image, white_threshold=white_threshold)

    def _load_door_frames(self, path):
        """Carga las dos variantes de puerta, elimina fondo y recorta al modelo real."""
        try:
            image = pygame.image.load(str(path)).convert_alpha()
            if image.get_width() % 2: return []
            cell_w = image.get_width() // 2
            frames = []
            for col in range(2):
                source_rect = pygame.Rect(col * cell_w, 0, cell_w, image.get_height())
                cell = image.subsurface(source_rect).copy()
                cell = self._trim_edge_background(cell)
                if cell.get_width() and cell.get_height():
                    frames.append(cell)
                    self._register_loaded_frame(
                        "door", path, col, source_rect, cell,
                        alpha_bounds=(0, 0, cell.get_width(), cell.get_height()),
                    )
            return frames
        except (pygame.error, OSError, ValueError):
            return []

    def _load_grid_frames(self, path, cols, rows):
        """Recorta una cuadrícula conocida y elimina el espacio transparente de cada celda."""
        try:
            image = pygame.image.load(str(path)).convert_alpha()
            if cols <= 0 or rows <= 0 or image.get_width() % cols or image.get_height() % rows:
                return []
            frames = []
            for frame_index, source_rect, bbox, frame in split_grid_frames(
                image, cols, rows, alpha_threshold=8
            ):
                frames.append(frame)
                self._register_loaded_frame(
                    "grid", path, frame_index, source_rect, frame,
                    alpha_bounds=(bbox.x, bbox.y, bbox.width, bbox.height),
                )
            return frames
        except (pygame.error, OSError, ValueError):
            return []

    def _load_merchant_sheet_frames(self, path, cols, rows):
        """Extrae celdas de los spritesheets regulares de merchants y recorta transparencia."""
        try:
            image = pygame.image.load(str(path)).convert_alpha()
            alpha = pygame.surfarray.array_alpha(image)
            # Detectar los limites reales de columnas/filas mediante proyecciones de alpha.
            col_runs = alpha_runs(alpha.max(axis=0) > 8)
            row_runs = alpha_runs(alpha.max(axis=1) > 8)
            if len(col_runs) != cols or len(row_runs) != rows:
                # Fallback a una rejilla uniforme si el margen transparente hace ambiguas
                # las proyecciones. Esto mantiene el orden esperado del spritesheet.
                cell_w = image.get_width() // cols
                cell_h = image.get_height() // rows
                col_runs = [(i * cell_w, (i + 1) * cell_w - 1) for i in range(cols)]
                row_runs = [(i * cell_h, min(image.get_height() - 1, (i + 1) * cell_h - 1)) for i in range(rows)]
            frames = []
            for y0, y1 in row_runs:
                for x0, x1 in col_runs:
                    rect = pygame.Rect(int(x0), int(y0), int(x1 - x0 + 1), int(y1 - y0 + 1))
                    if rect.width < 2 or rect.height < 2:
                        continue
                    cell = image.subsurface(rect).copy()
                    bounds = cell.get_bounding_rect(min_alpha=8)
                    if bounds.width >= 2 and bounds.height >= 2:
                        cell = cell.subsurface(bounds).copy()
                        alpha_bounds = (bounds.x, bounds.y, bounds.width, bounds.height)
                    else:
                        alpha_bounds = None
                    frame_index = len(frames)
                    frames.append(cell)
                    self._register_loaded_frame(
                        "merchant", path, frame_index, rect, cell,
                        alpha_bounds=alpha_bounds,
                    )
            return frames
        except (pygame.error, OSError, ValueError):
            return []

    def _load_component_frames(self, path, minimum=18, merge_gap=5, exclude_large=False):
        """Extrae cada modelo opaco de un atlas, en vez de cruzar filas/columnas."""
        try:
            image = pygame.image.load(str(path)).convert_alpha()
            mask = pygame.mask.from_surface(image, threshold=8)
            components = mask.connected_components(minimum=max(1, int(minimum)))
            # Cada componente es un pygame.mask.Mask. En pygame-ce, Mask expone
            # get_bounding_rects() (plural), que devuelve los Rect opacos del componente.
            rects = [
                rect
                for component in components
                for rect in component.get_bounding_rects()
            ]
            rects = [r for r in rects if r.width >= 2 and r.height >= 2]
            if not rects:
                return []

            changed = True
            while changed and merge_gap > 0:
                changed = False
                for i in range(len(rects)):
                    if i >= len(rects):
                        break
                    a = rects[i]
                    for j in range(i + 1, len(rects)):
                        b = rects[j]
                        gap_x = max(b.left - a.right, a.left - b.right, 0)
                        gap_y = max(b.top - a.bottom, a.top - b.bottom, 0)
                        gap = max(gap_x, gap_y)
                        small, large = (a, b) if a.width * a.height <= b.width * b.height else (b, a)
                        if gap <= merge_gap and small.width * small.height <= large.width * large.height * 0.28:
                            rects[i] = a.union(b)
                            rects.pop(j)
                            changed = True
                            break
                    if changed:
                        break

            if exclude_large and len(rects) >= 4:
                areas = sorted(r.width * r.height for r in rects)
                median = areas[len(areas) // 2]
                if median > 0:
                    rects = [r for r in rects if r.width * r.height <= median * 4.5]
            rects.sort(key=lambda r: (r.top, r.left))
            frames = []
            for frame_index, rect in enumerate(rects):
                frame = image.subsurface(rect).copy()
                frames.append(frame)
                self._register_loaded_frame(
                    "component", path, frame_index, rect, frame,
                    alpha_bounds=(0, 0, rect.width, rect.height),
                )
            return frames
        except (pygame.error, OSError, ValueError):
            return []

    def _load_sheet_frames(self, path):
        try:
            image = pygame.image.load(str(path)).convert_alpha()
            if path.name in ("fountain_active.png", "fountain_inactive.png"):
                if image.get_width() % 3 != 0:
                    return []
                frame_w = image.get_width() // 3
                return [
                    image.subsurface(pygame.Rect(i * frame_w, 0, frame_w, image.get_height())).copy()
                    for i in range(3)
                ]
            if path.name == "MinotauroGigante_ataque.png" and image.get_width() % 3 == 0 and image.get_height() % 3 == 0:
                cell_w = image.get_width() // 3
                cell_h = image.get_height() // 3
                return [
                    image.subsurface(pygame.Rect(col * cell_w, row * cell_h, cell_w, cell_h)).copy()
                    for row in range(3) for col in range(3)
                ]
            alpha = pygame.surfarray.array_alpha(image)
            cols = alpha_runs(alpha.max(axis=1) > 8)
            rows = alpha_runs(alpha.max(axis=0) > 8)
            frames=[]
            for y0,y1 in rows:
                for x0,x1 in cols:
                    rect=pygame.Rect(x0,y0,x1-x0+1,y1-y0+1)
                    if rect.width < 2 or rect.height < 2: continue
                    frame=image.subsurface(rect).copy()
                    frames.append(frame)
                    self._register_loaded_frame(
                        "sheet", path, len(frames)-1, rect, frame,
                        alpha_bounds=(0, 0, rect.width, rect.height),
                    )
            if frames:
                return frames
            self._register_loaded_frame(
                "sheet", path, 0,
                pygame.Rect(0, 0, image.get_width(), image.get_height()), image,
                alpha_bounds=(0, 0, image.get_width(), image.get_height()),
            )
            return [image]
        except (pygame.error, OSError, ValueError):
            return []

    def _variant_enemy_anims(self, key, variant_id, hue_shift, saturation, lightness):
        if not variant_id:
            return self.enemy_sprites.get(key, {})
        cache_key=(key, variant_id)
        cached=self.enemy_variant_sprites.get(cache_key)
        if cached is not None:
            return cached
        source=self.enemy_sprites.get(key, {})
        transformed={}
        for anim, frames in source.items():
            transformed[anim]=[
                pygame.transform.hsl(frame, hue_shift, saturation, lightness)
                for frame in frames
            ]
        self.enemy_variant_sprites[cache_key]=transformed
        return transformed

    def _draw_enemy_sprite(self, screen, e, x, y, light_level, t):
        key=getattr(e.d,"sprite_set",None)
        if not key or key not in self.enemy_sprites:
            return False
        variant_id=getattr(e.d,"variant_id",None)
        if variant_id:
            self.enemy_variant_tints[variant_id]=tuple(getattr(e.d,"variant_tint",getattr(e.d,"color",(200,80,80))))
            self.enemy_variant_params[variant_id]=(
                float(getattr(e.d,"variant_hue_shift",0.0)),
                float(getattr(e.d,"variant_saturation",0.0)),
                float(getattr(e.d,"variant_lightness",0.0))
            )
        params=self.enemy_variant_params.get(variant_id,(0.0,0.0,0.0))
        anims=self._variant_enemy_anims(key, variant_id, *params)
        if e.state in ("windup","recover"):
            anim=anims.get("attack_heavy" if getattr(e.d,"melee_explosion",False) and "attack_heavy" in anims else "attack")
            elapsed=getattr(e,"attack_anim_time",0.0)
            duration=max(0.20,float(getattr(e.d,"windup",0.5))+float(getattr(e.d,"recover",0.3)))
        elif e.state == "move":
            # Algunos assets suministrados no tienen idle/walk (por ejemplo el Ogro).
            # En ese caso usamos su animación de ataque como postura de espera para
            # mantener siempre visible el modelo nuevo y nunca volver al modelo legacy.
            anim=anims.get("run") or anims.get("walk") or anims.get("idle") or anims.get("attack") or anims.get("attack_heavy")
            elapsed=t
            duration=0.62 if anim not in (anims.get("idle"), None) else 1.0
        else:
            anim=anims.get("idle") or anims.get("walk") or anims.get("run") or anims.get("attack") or anims.get("attack_heavy")
            elapsed=t
            duration=1.0
        if not anim: return False
        idx=int(max(0.0,elapsed)*len(anim)/duration)%len(anim)
        frame=anim[idx]
        base_target=max(56.0, float(e.radius)*4.2)
        target=base_target*float(getattr(e.d,"sprite_scale",1.0)) / 4.0
        if getattr(e,"is_boss",False): target=max(128.0, target)
        elif getattr(e,"is_miniboss",False): target=max(82.0, target)
        target_key=max(1,int(round(target)))
        flip=(math.cos(e.facing)<0) ^ bool(getattr(e.d, "sprite_mirror", False))
        cache_key=(key,variant_id,id(frame),target_key,flip)
        cached=self._enemy_frame_cache.get(cache_key)
        if cached is None:
            w,h=frame.get_size(); scale=target/max(1,w,h)
            cached=pygame.transform.smoothscale(frame,(max(1,int(w*scale)),max(1,int(h*scale))))
            if flip: cached=pygame.transform.flip(cached,True,False)
            self._enemy_frame_cache[cache_key]=cached
        frame=cached
        if e.flash>0:
            flash_key=(cache_key,"flash")
            flash=self._enemy_flash_cache.get(flash_key)
            if flash is None:
                mask=pygame.mask.from_surface(frame,threshold=8)
                flash=frame.copy()
                clipped=mask.to_surface(setcolor=(255,255,255,175),unsetcolor=(0,0,0,0))
                flash.blit(clipped,(0,0),special_flags=pygame.BLEND_RGBA_ADD)
                self._enemy_flash_cache[flash_key]=flash
            frame=flash
        elif light_level < 0.98:
            bucket=max(3,min(15,int(light_level*15)))
            light_key=(cache_key,"light",bucket)
            lit=self._enemy_frame_cache.get(light_key)
            if lit is None:
                lit=frame.copy()
                value=max(1,int(255*bucket/15.0))
                lit.fill((value,value,value,255),special_flags=pygame.BLEND_RGBA_MULT)
                self._enemy_frame_cache[light_key]=lit
            frame=lit
        screen.blit(frame,frame.get_rect(center=(x,y)))
        return True

    def _draw_enemy_death(self, screen, effect, ox, oy):
        x,y,elapsed,max_life,key,size,facing=effect[:7]
        variant_id=effect[7] if len(effect) > 7 else None
        params=self.enemy_variant_params.get(variant_id,(0.0,0.0,0.0))
        anims=self._variant_enemy_anims(key, variant_id, *params) if variant_id else self.enemy_sprites.get(key,{})
        frames=anims.get("death")
        if not frames: return
        idx=min(len(frames)-1,int(elapsed*len(frames)/max(0.001,max_life)))
        frame=frames[idx]
        base=self._fit_effect_frame(frame,size)
        rot_key=("death",id(base),quantized_facing_flip(facing))
        frame=self._rotation_cache.get(rot_key)
        if frame is None:
            frame=pygame.transform.flip(base,True,False) if math.cos(facing)<0 else base
            self._rotation_cache[rot_key]=frame
        frame=frame.copy(); frame.set_alpha(max(0,int(255*(1-elapsed/max_life))))
        screen.blit(frame,frame.get_rect(center=(int(x+ox),int(y+oy))))

    def _draw_projectile_sheet(self, screen, frames, pr, ox, oy, size):
        if not frames: return
        idx=animation_frame_index(pr.age, len(frames), 0.42, loop=True)
        frame=self._fit_effect_frame(frames[idx],size)
        angle=math.degrees(math.atan2(pr.vy,pr.vx))
        angle_key=quantized_sprite_angle(math.radians(angle))
        rot_key=("sheet_rot",id(frame),angle_key)
        rotated=self._rotation_cache.get(rot_key)
        if rotated is None:
            rotated=pygame.transform.rotate(frame,angle_key)
            self._rotation_cache[rot_key]=rotated
        screen.blit(rotated,rotated.get_rect(center=(int(pr.x+ox),int(pr.y+oy))))

    def _load_animation_frames(self, prefix, count):
        frames = []
        for index in range(1, count + 1):
            path = self.asset_root / "effects" / f"{prefix}{index}.png"
            if not path.is_file():
                continue
            try:
                image = pygame.image.load(str(path)).convert_alpha()
                bbox = image.get_bounding_rect(min_alpha=1)
                if bbox.width and bbox.height:
                    image = image.subsurface(bbox).copy()
                frames.append(image)
            except (pygame.error, OSError, ValueError):
                continue
        return frames

    def _fit_effect_frame(self, image, size):
        if image is None:
            return None
        key=("effect",id(image),int(round(float(size))))
        cached=self._fit_cache.get(key)
        if cached is not None:
            return cached
        w,h=image.get_size()
        scale=float(size)/max(1,w,h)
        out=pygame.transform.smoothscale(image,(max(1,int(w*scale)),max(1,int(h*scale))))
        self._fit_cache[key]=out
        return out

    def _draw_combat_sprite_animation(self, screen, frames, elapsed, x, y, size, angle=None, alpha=255, loop=False, duration=0.24):
        if not frames:
            return
        frame_index = animation_frame_index(elapsed, len(frames), duration, loop=loop)
        frame = frames[frame_index]
        frame = self._fit_effect_frame(frame, size)
        if frame is None:
            return
        if angle is not None:
            angle_key=quantized_sprite_angle(angle)
            rot_key=("effect_rot",id(frame),angle_key)
            rotated=self._rotation_cache.get(rot_key)
            if rotated is None:
                rotated=pygame.transform.rotate(frame,angle_key)
                self._rotation_cache[rot_key]=rotated
            frame=rotated
        if alpha < 255:
            frame = frame.copy()
            frame.set_alpha(max(0, min(255, int(alpha))))
        screen.blit(frame, frame.get_rect(center=(int(x), int(y))))

    def _load_trimmed_asset(self, relative_path):
        path = self.asset_root.parent / relative_path
        if not path.is_file():
            return None
        try:
            image = pygame.image.load(str(path)).convert_alpha()
            bbox = image.get_bounding_rect(min_alpha=1)
            return image.subsurface(bbox).copy() if bbox.width and bbox.height else image
        except (pygame.error, OSError):
            return None

    def _fit_image(self, image, max_dimension, cache_key=None):
        if image is None:
            return None
        key=(id(image), int(round(float(max_dimension)*2.0)), cache_key)
        cached=self._fit_cache.get(key)
        if cached is not None:
            return cached
        bbox=image.get_bounding_rect(min_alpha=8)
        if bbox.width and bbox.height:
            image=image.subsurface(bbox).copy()
        w,h=image.get_size()
        size=fit_dimensions(w, h, max_dimension)
        out=image if size==(w,h) else pygame.transform.smoothscale(image,size)
        self._fit_cache[key]=out
        return out
    @staticmethod
    def _melee_grip_anchor(weapon_def):
        return melee_grip_anchor(getattr(weapon_def, "weapon_sprite", ""))

    def _rotate_weapon_from_grip(self, image, weapon_def, rotation, flipped=False):
        image=self._fit_image(image,self._weapon_max_dimension(getattr(weapon_def,"class","pistol")))
        if image is None: return None
        gx,gy=self._melee_grip_anchor(weapon_def)
        # Al espejar el arma, el punto de agarre también se espeja.
        if flipped:
            gx=1.0-gx
        grip=(image.get_width()*gx,image.get_height()*gy)
        pad=max(image.get_width(),image.get_height())+12
        canvas=pygame.Surface((image.get_width()+pad*2,image.get_height()+pad*2),pygame.SRCALPHA)
        canvas.blit(image,(pad+image.get_width()/2-grip[0],pad+image.get_height()/2-grip[1]))
        rotated=pygame.transform.rotozoom(canvas,rotation,1.0)
        bbox=rotated.get_bounding_rect(min_alpha=8)
        return rotated.subsurface(bbox).copy() if bbox.width and bbox.height else rotated

    @staticmethod
    def _weapon_max_dimension(weapon_class):
        return weapon_max_dimension(weapon_class)

    @staticmethod
    def _wall_piece_key(arena, tx, ty):
        return wall_piece_key(arena, tx, ty, FLOOR)

    def text(self, surf, s, pos, color=(235, 235, 240), font=None, center=False, right=False):
        img = (font or self.font).render(s, True, color)
        r = img.get_rect()
        if center:
            r.center = pos
        elif right:
            r.topright = pos
        else:
            r.topleft = pos
        surf.blit(img, r)

    def _wall_models_for_biome(self, biome):
        key = ("wall_models", str(biome))
        cached = self._fit_cache.get(key)
        if cached is not None:
            return cached
        if not self.wall_models:
            return {}
        b = self.data.biomes.get(str(biome), {})
        target = tuple(b.get("wall", (130, 125, 120)))
        models = {}
        for name, image in self.wall_models.items():
            factors = tuple(max(0, min(255, int(255 * (0.62 + channel / 255.0 * 0.38)))) for channel in target)
            tinted = image.copy()
            tinted.fill((*factors, 255), special_flags=pygame.BLEND_RGBA_MULT)
            models[name] = tinted
        self._fit_cache[key] = models
        return models

    def _tiled_wall_strip(self, image, horizontal, length):
        """Fits ONE complete wall model to one room-edge segment.

        walls.png contains finished wall models, not repeatable tiles. Repeating
        the sprite per tile was the source of the duplicated-wall bug. The model
        is therefore scaled once to the requested segment length while retaining
        its original aspect ratio in the wall-depth direction.
        """
        length = max(1, int(length))
        key = ("wall_segment", id(image), bool(horizontal), length)
        cached = self._fit_cache.get(key)
        if cached is not None:
            return cached

        if horizontal:
            target_w = length
            target_h = max(1, int(round(image.get_height() * target_w / max(1, image.get_width()))))
        else:
            target_h = length
            target_w = max(1, int(round(image.get_width() * target_h / max(1, image.get_height()))))

        scaled = pygame.transform.smoothscale(image, (target_w, target_h))
        self._fit_cache[key] = scaled
        return scaled


    def _wall_boundary_orientation(self, arena, tx, ty):
        """Detecta la orientación real de una pared a partir de la geometría de la sala."""
        if not (0 <= tx < arena.cols and 0 <= ty < arena.rows) or arena.grid[ty][tx] != WALL:
            return None
        def floor(x, y):
            return 0 <= x < arena.cols and 0 <= y < arena.rows and arena.grid[y][x] == FLOOR
        n, e, s, w = floor(tx,ty-1), floor(tx+1,ty), floor(tx,ty+1), floor(tx-1,ty)
        if n or s:
            return "diagonal" if e or w else "horizontal"
        if e or w:
            return "vertical"
        if any((floor(tx-1,ty-1),floor(tx+1,ty-1),floor(tx-1,ty+1),floor(tx+1,ty+1))):
            return "diagonal"
        return None

    def _draw_room_wall_models(self, target, arena, wall_models, ox=0, oy=0):
        """Dibuja un modelo completo por tramo de frontera real de la sala."""
        if not wall_models:
            return

        def floor(x, y):
            return 0 <= x < arena.cols and 0 <= y < arena.rows and arena.grid[y][x] == FLOOR

        boundary = {}
        for ty in range(arena.rows):
            for tx in range(arena.cols):
                if arena.grid[ty][tx] != WALL:
                    continue
                normals = [(dx,dy) for dx,dy in ((0,-1),(1,0),(0,1),(-1,0)) if floor(tx+dx,ty+dy)]
                if normals:
                    boundary[(tx,ty)] = (sum(x for x,_ in normals), sum(y for _,y in normals))
                    continue
                diagonals = [(dx,dy) for dx,dy in ((-1,-1),(1,-1),(-1,1),(1,1)) if floor(tx+dx,ty+dy)]
                if diagonals:
                    boundary[(tx,ty)] = (sum(x for x,_ in diagonals), sum(y for _,y in diagonals))

        horizontal, vertical, diag_rising, diag_falling = [], [], [], []
        for (tx, ty), (nx, ny) in boundary.items():
            if not (nx or ny):
                continue
            if abs(nx) == abs(ny):
                # La diagonal ya está dibujada en el PNG; no se rota.
                (diag_rising if nx * ny > 0 else diag_falling).append((tx, ty, nx, ny))
            elif abs(nx) > abs(ny):
                vertical.append((tx, ty, nx, ny))
            else:
                horizontal.append((tx, ty, nx, ny))

        def runs_1d(cells, axis):
            groups, buckets = [], {}
            for item in cells:
                tx, ty, nx, ny = item
                key = ty if axis == "x" else tx
                buckets.setdefault(key, []).append(item)
            for items in buckets.values():
                items.sort(key=lambda item: item[0] if axis == "x" else item[1])
                current, previous = [], None
                for item in items:
                    coord = item[0] if axis == "x" else item[1]
                    if previous is None or coord == previous + 1:
                        current.append(item)
                    else:
                        groups.append(current)
                        current = [item]
                    previous = coord
                if current:
                    groups.append(current)
            return groups

        def runs_diag(cells, slope):
            groups, buckets = [], {}
            for item in cells:
                tx, ty, nx, ny = item
                key = tx - ty if slope > 0 else tx + ty
                buckets.setdefault(key, []).append(item)
            for items in buckets.values():
                items.sort(key=lambda item: item[0])
                current, previous = [], None
                for item in items:
                    coord = item[0]
                    if previous is None or coord == previous + 1:
                        current.append(item)
                    else:
                        groups.append(current)
                        current = [item]
                    previous = coord
                if current:
                    groups.append(current)
            return groups

        def fit_wall_piece(image, max_w, max_h):
            """Escala un modelo completo sin deformarlo y sin superar su altura máxima."""
            if image is None:
                return None
            max_w = max(1, int(max_w))
            max_h = max(1, int(max_h))
            iw, ih = image.get_size()
            scale = min(max_w / max(1, iw), max_h / max(1, ih))
            size = (
                max(1, int(round(iw * scale))),
                max(1, int(round(ih * scale))),
            )
            key = ("wall_piece_fit", id(image), max_w, max_h)
            cached = self._fit_cache.get(key)
            if cached is not None:
                return cached
            cached = pygame.transform.smoothscale(image, size)
            self._fit_cache[key] = cached
            return cached

        def draw_repeated_horizontal(group, image):
            """Repite el modelo horizontal sin huecos y limita su altura a 2 bloques."""
            if not group or image is None:
                return
            xs = [item[0] for item in group]
            ys = [item[1] for item in group]
            x0 = min(xs) * TILE + ox
            x1 = (max(xs) + 1) * TILE + ox
            cy = (sum(ys) / len(ys) + 0.5) * TILE + oy
            nx = sum(item[2] for item in group) / len(group)
            ny = sum(item[3] for item in group) / len(group)
            piece = fit_wall_piece(image, TILE, TILE * 2)
            if piece is None:
                return

            # La pieza se repite de borde a borde. Si su anchura no coincide
            # exactamente con TILE, la siguiente pieza empieza inmediatamente
            # donde termina la anterior: no quedan franjas transparentes.
            strip_w = max(TILE, x1 - x0)
            strip = pygame.Surface((strip_w + piece.get_width() * 2, piece.get_height()), pygame.SRCALPHA)
            for px in range(0, strip.get_width(), piece.get_width()):
                strip.blit(piece, (px, 0))

            # Recortamos exactamente al tramo de pared para que nunca invada
            # la sala vecina ni deje un hueco al final.
            crop = strip.subsurface(
                pygame.Rect(
                    max(0, (strip.get_width() - strip_w) // 2),
                    0,
                    strip_w,
                    strip.get_height(),
                )
            ).copy()

            # Las paredes horizontales se apoyan contra la frontera de la sala.
            # El desplazamiento conserva la misma profundidad que el renderer
            # anterior, pero la altura queda siempre <= 2 bloques.
            nlen = max(1e-6, math.hypot(nx, ny))
            cx = (x0 + x1) * 0.5 - (nx / nlen) * TILE * 0.18
            cy -= (ny / nlen) * TILE * 0.18
            target.blit(crop, crop.get_rect(center=(int(cx), int(cy))))

        def draw_repeated_diagonal(group, image, rising):
            """Repite el modelo diagonal sobre una pared diagonal real, sin efecto escalera."""
            if not group or image is None:
                return
            xs = [item[0] for item in group]
            ys = [item[1] for item in group]
            nx = sum(item[2] for item in group) / len(group)
            ny = sum(item[3] for item in group) / len(group)
            piece = fit_wall_piece(image, TILE * 2, TILE * 2)
            if piece is None:
                return

            # Cada modelo ocupa como máximo un cuadrado de 2x2 bloques. Se
            # desplazan por la diagonal real de la sala, no por celdas escalonadas.
            step = max(1, int(round(max(piece.get_width(), piece.get_height()) * 0.72)))
            count = max(1, len(group))
            cx0 = (min(xs) + 0.5) * TILE + ox
            cy0 = (min(ys) + 0.5) * TILE + oy
            direction = 1 if rising else -1

            for index in range(count):
                cx = cx0 + index * step
                cy = cy0 + direction * index * step
                nlen = max(1e-6, math.hypot(nx, ny))
                cx -= (nx / nlen) * TILE * 0.18
                cy -= (ny / nlen) * TILE * 0.18
                target.blit(piece, piece.get_rect(center=(int(cx), int(cy))))

        def draw_vertical_group(group, image):
            if not group or image is None:
                return
            xs = [item[0] for item in group]
            ys = [item[1] for item in group]
            nx = sum(item[2] for item in group)
            cx = (sum(xs) / len(xs) + 0.5) * TILE + ox
            cy = (sum(ys) / len(ys) + 0.5) * TILE + oy
            length = len(group) * TILE
            iw, ih = image.get_size()
            th = max(1, int(round(length)))
            tw = max(1, int(round(iw * th / max(1, ih))))
            key = ("wall_vertical_segment", id(image), length)
            piece = self._fit_cache.get(key)
            if piece is None:
                piece = pygame.transform.smoothscale(image, (tw, th))
                self._fit_cache[key] = piece
            nlen = max(1e-6, math.hypot(nx, sum(item[3] for item in group)))
            cx -= (nx / nlen) * TILE * 0.18
            target.blit(piece, piece.get_rect(center=(int(cx), int(cy))))


        for group in runs_1d(horizontal, "x"):
            draw_repeated_horizontal(group, wall_models.get("front"))

        for group in runs_1d(vertical, "y"):
            nx = sum(item[2] for item in group)
            draw_vertical_group(group, wall_models.get("vertical_a" if nx > 0 else "vertical_b"))

        # Una esquina aislada no es una pared diagonal: conserva el modelo
        # horizontal/vertical. Los modelos diagonales se reservan para tramos
        # diagonales reales (dos o más celdas consecutivas).
        for group in runs_diag(diag_rising, 1):
            if len(group) >= 2:
                draw_repeated_diagonal(group, wall_models.get("diag_rising"), rising=True)

        for group in runs_diag(diag_falling, -1):
            if len(group) >= 2:
                draw_repeated_diagonal(group, wall_models.get("diag_falling"), rising=False)

    def _background(self, arena):
        key = (arena.biome, arena.room_id, arena.cols, arena.rows, getattr(arena, "floor_surface", None))
        if self._bg_key == key:
            return self._bg_cache
        b = self.data.biomes[arena.biome]
        surf = pygame.Surface((arena.width, arena.height + 10), pygame.SRCALPHA)
        floor_name = getattr(arena, "floor_surface", None)
        floor_img = self.named_floor_images.get(floor_name) if floor_name else None
        if str(arena.biome) == "snow" and floor_img is not None:
            snow_key = ("snow_floor", id(floor_img))
            snow_floor = self._fit_cache.get(snow_key)
            if snow_floor is None:
                snow_floor = floor_img.copy()
                frost = pygame.Surface(snow_floor.get_size(), pygame.SRCALPHA)
                frost.fill((205, 225, 248, 92))
                snow_floor.blit(frost, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                self._fit_cache[snow_key] = snow_floor
            floor_img = snow_floor
        if floor_img is None:
            fallback_by_biome = {
                "ruins": 10, "forest": 5, "dungeon": 9,
                "laboratory": 2, "volcanic": 7, "desert": 10,
                "swamp": 5, "snow": 9, "final": 11,
            }
            floor_img = self.floor_images.get(fallback_by_biome.get(arena.biome, 1))
        wall_models = self._wall_models_for_biome(arena.biome)
        wall_band = (sum(ord(ch) for ch in str(arena.biome)) % 3)
        wall_fill = self.wall_fill_images.get(str(wall_band)) or self.wall_fill_images.get("0")
        wall_cap = self.wall_top_images.get("default")
        for ty in range(arena.rows):
            for tx in range(arena.cols):
                t = arena.grid[ty][tx]
                r = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
                if t == FLOOR:
                    if floor_img is not None:
                        surf.blit(floor_img, r)
                    else:
                        pygame.draw.rect(surf, b["floor_a"] if (tx + ty) % 2 == 0 else b["floor_b"], r)
                elif t == WALL:
                    if self._wall_boundary_orientation(arena, tx, ty) is None:
                        continue
                    piece_key = self._wall_piece_key(arena, tx, ty)
                    piece = self.wall_piece_images.get(piece_key) if piece_key else None
                    if piece is None:
                        if wall_fill is not None:
                            surf.blit(wall_fill, r)
                        else:
                            pygame.draw.rect(surf, b["wall"], r)
                        below_is_floor = ty + 1 < arena.rows and arena.grid[ty + 1][tx] == FLOOR
                        if wall_cap is not None and below_is_floor:
                            surf.blit(wall_cap, r)
                        else:
                            pygame.draw.rect(surf, b["wall_top"], (r.x, r.y, TILE, 4))
                        pygame.draw.rect(surf, (30, 26, 34), r, 1)
                elif t in (PILLAR, TORCH_PILLAR):
                    pillar_image = self.torch_column_image if t == TORCH_PILLAR else self.column_image
                    if pillar_image is None:
                        if wall_fill is not None:
                            surf.blit(wall_fill, r)
                        else:
                            pygame.draw.rect(surf, b["pillar"], r)
                        pygame.draw.rect(surf, b["pillar_top"], (r.x, r.y, TILE, 5))
                        pygame.draw.rect(surf, (40, 30, 24), r, 1)
                elif t == SECRET:
                    if wall_fill is not None:
                        surf.blit(wall_fill, r)
                    else:
                        pygame.draw.rect(surf, b["wall"], r)
                    pygame.draw.rect(surf, (145, 90, 165), r, 2)
                    pygame.draw.line(surf, (175, 115, 190), (r.x+7,r.y+7), (r.right-7,r.bottom-7), 2)
                    pygame.draw.line(surf, (175, 115, 190), (r.right-7,r.y+7), (r.x+7,r.bottom-7), 2)
        self._draw_room_wall_models(surf, arena, wall_models)
        for ty, row in enumerate(arena.grid):
            for tx, tile in enumerate(row):
                if tile not in (PILLAR, TORCH_PILLAR):
                    continue
                pillar_image = self.torch_column_image if tile == TORCH_PILLAR else self.column_image
                if pillar_image is not None:
                    rect = pillar_image.get_rect(midbottom=(tx * TILE + TILE // 2, (ty + 1) * TILE))
                    surf.blit(pillar_image, rect)
        shape = getattr(arena, "shape", "rectangle")
        if shape in ("octagon", "diamond", "chamfer"):
            edge = max(6, TILE // 3)
            if shape == "diamond":
                pts = [(arena.width/2, 0), (arena.width, arena.height/2),
                       (arena.width/2, arena.height), (0, arena.height/2)]
            else:
                cut = 4 * TILE
                pts = [(cut, 0), (arena.width-cut, 0), (arena.width, cut),
                       (arena.width, arena.height-cut), (arena.width-cut, arena.height),
                       (cut, arena.height), (0, arena.height-cut), (0, cut)]
            edge_color = self.data.biomes[arena.biome]["wall_top"]
            for a, z in zip(pts, pts[1:] + pts[:1]):
                pygame.draw.line(surf, edge_color, a, z, edge)
                pygame.draw.line(surf, tuple(min(255, c + 18) for c in edge_color), a, z, 2)
        self._bg_cache, self._bg_key = surf, key
        return surf

    def _draw_architecture_foreground(self, screen, arena, sim, decor_lights, ox, oy):
        """Oculta las paredes de la silueta cuando el jugador está junto a ellas.

        La geometría visual sigue la misma frontera que el fondo; no existe una
        segunda pared rectangular independiente para la oclusión.
        """
        for ty, row in enumerate(arena.grid):
            for tx, tile in enumerate(row):
                if tile not in (PILLAR, TORCH_PILLAR):
                    continue
                pillar_image = self.torch_column_image if tile == TORCH_PILLAR else self.column_image
                if pillar_image is not None:
                    base_y = (ty + 1) * TILE
                    if sim.player.y < base_y:
                        rect = pillar_image.get_rect(
                            midbottom=(int(tx * TILE + TILE // 2 + ox), int(base_y + oy))
                        )
                        screen.blit(pillar_image, rect)

        # Solo se necesita la pasada de oclusión cuando el jugador está pegado
        # al borde real de la habitación. Se dibuja una única vez, no una vez
        # por cada celda WALL.
        near_boundary = False
        for ty in range(arena.rows):
            for tx in range(arena.cols):
                if self._wall_boundary_orientation(arena, tx, ty):
                    if math.hypot(
                        sim.player.x - (tx * TILE + TILE / 2),
                        sim.player.y - (ty * TILE + TILE / 2),
                    ) <= TILE * 1.75:
                        near_boundary = True
                        break
            if near_boundary:
                break

        if near_boundary:
            wall_models = self._wall_models_for_biome(arena.biome)
            self._draw_room_wall_models(screen, arena, wall_models, ox, oy)

    def _draw_dynamic_shadows(self, screen, arena, sim, ox, oy):
        """Sombras dinamicas con una sola capa reutilizable y posiciones de pilares cacheadas."""
        px, py = sim.player.x, sim.player.y
        decor_lights = self._room_decor_lights(arena)
        sources = [(px, py, 190, 1.0)]
        sources.extend((light["x"], light["y"], light["radius"], 0.42) for light in decor_lights)

        room_key=(getattr(arena,"room_id",None),arena.cols,arena.rows,str(arena.grid))
        pillars=self._pillar_positions_cache.get(room_key)
        if pillars is None:
            pillars=[]
            for ty,row in enumerate(arena.grid):
                for tx,tile in enumerate(row):
                    if tile in (PILLAR,TORCH_PILLAR):
                        pillars.append((tx*TILE+TILE/2,ty*TILE+TILE/2))
            self._pillar_positions_cache[room_key]=pillars

        room_key = (getattr(arena, "room_id", None), arena.cols, arena.rows, arena.biome)
        self._shadow_frame = (self._shadow_frame + 1) % self._shadow_refresh_interval
        refresh = (self._shadow_frame == 0 or self._last_shadow_room_key != room_key)
        if not refresh:
            screen.blit(self._shadow_layer, (0, 0))
            return
        self._last_shadow_room_key = room_key
        layer=self._shadow_layer
        layer.fill((0,0,0,0))

        for source_x, source_y, source_radius, source_strength in sources:
            def cast_shadow(world_x, world_y, width, height, length, alpha):
                sx, sy = world_x + ox, world_y + oy
                if sx < -100 or sy < -100 or sx > VIEW_W + 100 or sy > VIEW_H + 100:
                    return
                dx, dy = world_x - source_x, world_y - source_y
                distance = math.hypot(dx, dy)
                if distance >= source_radius:
                    return
                if distance < 1:
                    dx, dy, distance = 0.0, 1.0, 1.0
                dx, dy = dx / distance, dy / distance
                rect = pygame.Rect(int(sx-width/2),int(sy-height/2),width,height)
                corners=[(rect.left,rect.top),(rect.right,rect.top),(rect.right,rect.bottom),(rect.left,rect.bottom)]
                far_edge=sorted(corners,key=lambda point:point[0]*dx+point[1]*dy,reverse=True)[:2]
                ex,ey=dx*length,dy*length
                a,b=far_edge
                shadow_alpha=max(12,min(100,int(alpha*source_strength)))
                pygame.draw.polygon(layer,(0,0,0,shadow_alpha),
                                    [a,b,(int(b[0]+ex),int(b[1]+ey)),(int(a[0]+ex),int(a[1]+ey))])
                base=pygame.Rect(0,0,max(18,int(width*1.05)),max(8,int(height*.48)))
                base.center=(int(sx+dx*7),int(sy+dy*10))
                pygame.draw.ellipse(layer,(0,0,0,min(110,shadow_alpha+18)),base)

            for wx,wy in pillars:
                sx,sy=wx+ox,wy+oy
                if -TILE <= sx <= VIEW_W+TILE and -TILE <= sy <= VIEW_H+TILE:
                    cast_shadow(wx,wy,TILE-3,TILE-3,58,72)

            chest=getattr(sim,"chest",None)
            if chest is not None:
                cast_shadow(chest.x,chest.y,42,30,28,58 if not chest.is_open else 32)
            for prop in getattr(sim,"props",[]):
                if not prop.get("broken"):
                    size=30 if prop.get("kind")=="crate" else 42
                    cast_shadow(prop["x"],prop["y"],size,size,30,56)
            for enemy in getattr(sim,"enemies",[]):
                if enemy.alive and getattr(enemy,"spawn_delay",0)<=0:
                    cast_shadow(enemy.x,enemy.y,max(14,enemy.radius*1.6),max(12,enemy.radius),18,42)

        screen.blit(layer,(0,0))
    def _room_decor_lights(self, arena):
        """Luces de antorchas ancladas a pilares sólidos y hogueras decorativas."""
        key = (getattr(arena, "room_id", None), arena.cols, arena.rows, arena.biome)
        if key in self._decor_light_cache:
            return self._decor_light_cache[key]

        lights = []
        for deco in getattr(arena, "decorations", []):
            if deco.get("kind") == "fountain_active":
                x, y = arena.tile_center(int(deco.get("x", arena.cols//2)), int(deco.get("y", arena.rows//2)))
                lights.append({"x": x, "y": y - 6, "kind": "fountain", "radius": 125, "color": (90, 185, 255)})
        # Las antorchas forman parte del mapa: su casilla inferior es sólida y
        # su luz nace cerca de la llama del sprite, no de un punto aleatorio del suelo.
        for ty, row in enumerate(arena.grid):
            for tx, tile in enumerate(row):
                if tile == TORCH_PILLAR:
                    x, y = arena.tile_center(tx, ty)
                    lights.append({"x": x, "y": y - 12, "kind": "torch_column",
                                   "radius": 225, "color": (255, 190, 105)})

        for x, y in bonfire_positions(arena):
            lights.append({"x": x, "y": y, "kind": "bonfire",
                           "radius": 190, "color": (255, 126, 58)})

        self._decor_light_cache[key] = lights
        return lights

    @staticmethod
    def _line_blocked(arena, x1, y1, x2, y2):
        distance = math.hypot(x2 - x1, y2 - y1)
        steps = max(1, int(distance / 12))
        for i in range(1, steps):
            f = i / steps
            tx = int((x1 + (x2 - x1) * f) // TILE)
            ty = int((y1 + (y2 - y1) * f) // TILE)
            if 0 <= tx < arena.cols and 0 <= ty < arena.rows:
                if arena.grid[ty][tx] in (WALL, PILLAR, TORCH_PILLAR, SECRET):
                    return True
        return False

    def _actor_light_level(self, arena, x, y, sim, decor_lights, t):
        """Estimación barata de luz directa con caché por casilla durante el frame."""
        tile_x = int(x // TILE)
        tile_y = int(y // TILE)
        key = (getattr(arena, "room_id", None), tile_x, tile_y)
        cached = self._actor_light_cache.get(key)
        if cached is not None:
            return cached
        sources = [(sim.player.x, sim.player.y, 190, (120, 190, 230), 0.82)]
        for light in decor_lights:
            flicker = 0.94 + 0.06 * math.sin(t * (5.0 if light["kind"] == "bonfire" else 2.4) + light["x"])
            sources.append((light["x"], light["y"], light["radius"], light["color"], 0.9 * flicker))
        for hazard in getattr(sim, "hazards", []):
            sources.append((hazard["x"], hazard["y"], min(115, int(hazard.get("radius", 70) * 1.25)), hazard.get("color", (100,180,120)), 0.55))
        if getattr(sim, "portal", False):
            sources.append((arena.width / 2, arena.height / 2, 105, (70,190,235), 0.5))
        level = 0.34
        for sx, sy, radius, color, strength in sources:
            dist = math.hypot(x - sx, y - sy)
            if dist >= radius:
                continue
            falloff = (1.0 - dist / radius) ** 1.55
            if self._line_blocked(arena, sx, sy, x, y):
                falloff *= 0.16
            level += strength * falloff * 0.68
        level = max(0.28, min(1.0, level))
        self._actor_light_cache[key] = level
        return level

    def _draw_world_bonfire(self, screen, light, ox, oy, t):
        """Dibuja una hoguera respetando el mismo eje Y de profundidad del mundo.

        Las hogueras no son entidades ni props destructibles: son fuentes de luz
        decorativas generadas en ``_room_decor_lights``. Antes se dibujaban todas
        al final del escenario, por lo que siempre quedaban delante del jugador,
        enemigos y demás objetos. Ahora se insertan en la pasada Y compartida.
        """
        x, y = int(light["x"] + ox), int(light["y"] + oy)
        pygame.draw.ellipse(screen, (32, 25, 28), (x - 16, y + 5, 32, 10))
        if self.bonfire_frames:
            # Los archivos hoguera1.png ... hoguera6.png son fotogramas animados.
            frame = self.bonfire_frames[int(t * 9.0) % len(self.bonfire_frames)]
            screen.blit(frame, frame.get_rect(center=(x, y - 2)))
        else:
            pygame.draw.ellipse(screen, (92, 58, 42), (x - 13, y - 3, 26, 13))
            flame_h = 15 + int(3 * math.sin(t * 11 + light["x"]))
            pygame.draw.polygon(screen, (255, 95, 35), [(x-9,y+3),(x-4,y-flame_h),(x,y-7),(x+5,y-flame_h+3),(x+9,y+3)])
            pygame.draw.ellipse(screen, (255, 205, 95), (x-4, y-10, 8, 15))

    def _draw_decor_lights(self, screen, decor_lights, ox, oy, t):
        # Las hogueras ya se dibujan dentro de la pasada de profundidad Y.
        # Aquí solo se mantienen otros efectos decorativos que no son sprites
        # físicos del escenario.
        return


    def _draw_drone_actor(self, screen, drone, ox, oy, t):
        x=int(drone["x"]+ox); y=int(drone["y"]+oy)
        bob=math.sin(float(drone.get("phase",0.0)))*3.0
        pygame.draw.ellipse(screen,(12,14,20,100),(x-8,y+5,x+8-(x-8),6))
        frames=self.drone_frames or self.enemy_sprites.get("drone",{}).get("idle") or self.enemy_sprites.get("drone",{}).get("run") or self.enemy_sprites.get("drone",{}).get("walk") or []
        if frames:
            frame=frames[int(t*8.0)%len(frames)]
            frame=self._fit_image(frame,24)
            if float(drone.get("flash",0.0)) > 0:
                frame=frame.copy()
                mask=pygame.mask.from_surface(frame,threshold=8)
                flash=mask.to_surface(setcolor=(255,255,255,190),unsetcolor=(0,0,0,0))
                frame.blit(flash,(0,0),special_flags=pygame.BLEND_RGBA_ADD)
            screen.blit(frame,frame.get_rect(center=(x,int(y+bob))))
        else:
            pygame.draw.circle(screen,(80,190,205),(x,int(y+bob)),10)
            pygame.draw.circle(screen,(185,245,250),(x,int(y+bob)),4)
        ratio=max(0.0,min(1.0,float(drone.get("hp",0))/max(1.0,float(drone.get("max_hp",1)))))
        pygame.draw.rect(screen,(15,18,25),(x-13,int(y-22+bob),26,3),border_radius=2)
        pygame.draw.rect(screen,(85,220,225),(x-13,int(y-22+bob),int(26*ratio),3),border_radius=2)

    def _draw_enemy_actor(self, screen, e, arena, sim, ox, oy, decor_lights, t):
        x, y = int(e.x + ox), int(e.y + oy)
        if e.spawn_delay > 0:   # aviso de aparición
            pygame.draw.circle(screen, (200, 120, 255), (x, y), int(e.radius + 8 * e.spawn_delay), 2)
            return
        col = (255, 255, 255) if e.flash > 0 else e.d.color
        light_level = self._actor_light_level(arena, e.x, e.y, sim, decor_lights, t)
        if getattr(e.d, "sprite_set", None) == "minigolem":
            light_level = max(light_level, 0.72)
        col = tuple(max(0, min(255, int(channel * light_level))) for channel in col)
        # Los modelos suministrados son la representación visual completa.
        # No se dibuja sombra/círculo legacy detrás de ellos.
        has_sprite = self._draw_enemy_sprite(screen, e, x, y, light_level, t)
        if not has_sprite and not getattr(e.d, "sprite_set", None):
            pygame.draw.circle(screen, (0, 0, 0), (x + 2, y + 4), max(5, e.radius))
        if not has_sprite and not getattr(e.d, "sprite_set", None):
            # Solo enemigos legacy sin modelo declarado conservan el fallback.
            # Los enemigos con sprite_set nunca vuelven a ser círculos.
            pygame.draw.circle(screen, col, (x, y), e.radius)
            pygame.draw.circle(screen, (20, 20, 20), (x, y), e.radius, 2)
        # Supplied sprites can already contain their weapons. Never layer the
        # legacy weapon sprite on top of those entities.
        # Un sprite_set nuevo es la representación visual completa de la entidad.
        # Algunos assets ya llevan el arma dibujada; nunca superponemos el arma legacy
        # sobre ningún modelo suministrado, aunque el dato antiguo conserve weapon_id.
        has_supplied_model = bool(getattr(e.d, "sprite_set", None)) and has_sprite
        enemy_weapon_id = None if (has_supplied_model or getattr(e.d, "visual_has_weapon", False)) else getattr(e, "weapon_id", None)
        enemy_weapon = self.weapon_scaled_images.get(enemy_weapon_id) if enemy_weapon_id else None
        if enemy_weapon is not None:
            weapon_def = self.data.weapons.get(enemy_weapon_id)
            weapon_class = getattr(weapon_def,"class","") if weapon_def else ""
            base_angle = {"melee":-35,"magic":-32,"special":-25}.get(weapon_class,0)
            # Igual que el jugador: al mirar a la izquierda se espeja el sprite y se compensa el ángulo.
            if math.cos(e.facing) < 0:
                enemy_weapon = pygame.transform.flip(enemy_weapon, True, False)
                rotation = base_angle + 180 - math.degrees(e.facing)
            else:
                rotation = base_angle - math.degrees(e.facing)
            enemy_rot_key=(enemy_weapon_id,int(round(rotation/5.0))*5)
            enemy_rotated=self._weapon_rotation_cache.get(enemy_rot_key)
            if enemy_rotated is None:
                enemy_rotated=pygame.transform.rotate(enemy_weapon,rotation)
                self._weapon_rotation_cache[enemy_rot_key]=enemy_rotated
            enemy_pos = (int(x + math.cos(e.facing) * (e.radius + 3)), int(y + math.sin(e.facing) * (e.radius + 3)))
            screen.blit(enemy_rotated, enemy_rotated.get_rect(center=enemy_pos))
        shield_ratio = getattr(e, "shield_integrity", 0.0) / max(1.0, getattr(e.d, "shield_durability", 48.0))
        if getattr(e, "shield_active", False) and shield_ratio > 0:
            shield_color = (int(70 + 65 * shield_ratio), int(125 + 70 * shield_ratio), 255)
            pygame.draw.arc(screen, shield_color, (x-e.radius-6, y-e.radius-6, 2*(e.radius+6), 2*(e.radius+6)), -e.facing-1.1, -e.facing+1.1, 4)
        if not getattr(e.d, "sprite_set", None):
            ex, ey = x + math.cos(e.facing) * 5, y + math.sin(e.facing) * 5
            pygame.draw.circle(screen, (255, 255, 255), (int(ex), int(ey)), 3)
        k = e.telegraph
        if k > 0:  # telegráfico: anillo que se cierra + línea de puntería
            rr = int(e.radius + 26 * (1 - k))
            pygame.draw.circle(screen, (255, 60, 60), (x, y), rr, 2)
            if e.d.ai != "melee":
                ln = 60 + 120 * k
                pygame.draw.line(screen, (255, 90, 90), (x, y),
                                 (x + math.cos(e.facing) * ln, y + math.sin(e.facing) * ln), 1)
        if e.hp < e.max_hp and not getattr(e, "is_boss", False):
            w = 24
            pygame.draw.rect(screen, (40, 0, 0), (x - w // 2, y - e.radius - 9, w, 4))
            pygame.draw.rect(screen, (230, 60, 60), (x - w // 2, y - e.radius - 9, int(w * max(0, e.hp) / e.max_hp), 4))

    def _draw_player_actor(self, screen, p, ox, oy, t):
        x, y = int(p.x + ox), int(p.y + oy)
        shield_ability_active = getattr(p, "ability_shield_fx", 0.0) > 0
        shadow = pygame.Surface((p.radius * 2 + 14, max(6, p.radius // 2 + 4)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 62), shadow.get_rect())
        screen.blit(shadow, shadow.get_rect(center=(x, y + 27)))
        # No se tintan ni se ocultan los fotogramas del personaje: algunos sprites
        # contienen píxeles de fondo semitransparentes y el blink los hacía visibles.
        # La invulnerabilidad se comunica con un aro translúcido, sin alterar el sprite.
        if p.invuln > 0:
            ring_color = (105, 205, 255) if getattr(p, "dash_left", 0.0) > 0 else (255, 145, 115)
            pulse = 0.5 + 0.5 * math.sin(t * 22.0)
            ring = pygame.Surface((p.radius * 2 + 18, p.radius * 2 + 18), pygame.SRCALPHA)
            pygame.draw.ellipse(ring, (*ring_color, int(105 + 65 * pulse)), (2, 2, ring.get_width() - 4, ring.get_height() - 4), 2)
            screen.blit(ring, ring.get_rect(center=(x, y)))
        # Personaje: animación de caminar; se dibuja antes que el arma para que
        # el arma independiente quede siempre delante del cuerpo.
        character_frames = self.player_walk_frames.get(getattr(p.c, "id", "soldier"), [])
        if character_frames:
            moving = getattr(p, "is_moving", False)
            frame_index = int(p.walk_time * 9) % len(character_frames) if moving else 0
            sprite_key=(getattr(p.c,"id","player"),frame_index,p.facing_x<0)
            sprite=self._player_flip_cache.get(sprite_key)
            if sprite is None:
                sprite=character_frames[frame_index]
                bbox=sprite.get_bounding_rect(min_alpha=8)
                if bbox.width and bbox.height:
                    sprite=sprite.subsurface(bbox).copy()
                if p.facing_x < 0:
                    sprite=pygame.transform.flip(sprite,True,False)
                self._player_flip_cache[sprite_key]=sprite
            flash_kind=None
            flash_alpha=0
            if getattr(p,"hurt_flash",0.0)>0:
                flash_kind=(255,55,55); flash_alpha=int(185*min(1.0,p.hurt_flash/.25))
            elif getattr(p,"heal_flash",0.0)>0:
                flash_kind=(80,255,105); flash_alpha=int(175*min(1.0,p.heal_flash/.26))
            elif getattr(p,"energy_flash",0.0)>0:
                flash_kind=(255,225,55); flash_alpha=int(175*min(1.0,p.energy_flash/.26))
            if flash_kind:
                # Nunca modificar el sprite cacheado: hacerlo dejaba el tinte rojo,
                # verde o amarillo grabado para los frames siguientes.
                sprite=sprite.copy()
                mask=pygame.mask.from_surface(sprite,threshold=8)
                clipped=mask.to_surface(setcolor=(*flash_kind,flash_alpha),unsetcolor=(0,0,0,0))
                sprite.blit(clipped,(0,0))
            screen.blit(sprite, sprite.get_rect(midbottom=(x,y+27)))
        else:
            pygame.draw.circle(screen, p.c.color, (x, y), p.radius)
            pygame.draw.circle(screen, (20, 20, 30), (x, y), p.radius, 2)
        # El escudo de energía de Kael parpadea suavemente y deja ver el sprite
        # debajo. Se dibuja encima del cuerpo, pero por debajo del arma.
        if shield_ability_active and self.ability_shield_image is not None:
            # El WEBP puede tener dimensiones enormes: ajustarlo al cuerpo del
            # personaje (mismo orden de tamaño que el sprite de 48x52).
            shield_overlay = self._fit_image(self.ability_shield_image, 52, "ability_shield")
            pulse = 0.5 + 0.5 * math.sin(t * 18.0)
            shield_overlay.set_alpha(int(95 + 85 * pulse))
            screen.blit(shield_overlay, shield_overlay.get_rect(center=(x, y)))
        # Arma equipada: sprite individual rotado hacia el cursor, siempre sobre el personaje.
        # Un slot vacío representa puños y no tiene WeaponState.
        equipped_weapon=getattr(p,"weapon",None)
        weapon_def=getattr(equipped_weapon,"d",None)
        if weapon_def is not None:
            kick = max(0.0, 1 - p.since_shot * 12) * 3
            ax, ay = math.cos(p.aim), math.sin(p.aim)
            weapon_id = getattr(weapon_def, "id", "")
            sheet_key = getattr(weapon_def, "weapon_sprite_sheet", None)
            frames = self.weapon_variant_frames.get(sheet_key, [])
            if frames:
                # Atlas: cada arma debe conservar exactamente el modelo asignado.
                index = int(getattr(weapon_def, "weapon_sprite_index", 0))
                weapon_image = (
                    self._fit_image(
                        frames[index],
                        self._weapon_max_dimension(getattr(weapon_def, "class", "pistol")),
                    )
                    if 0 <= index < len(frames)
                    and frames[index].get_width() > 1
                    and frames[index].get_height() > 1
                    else None
                )
            else:
                weapon_image = self.weapon_scaled_images.get(weapon_id)
            if weapon_image is not None:
                weapon_class = getattr(weapon_def, "class", "")
                sprite_path = str(getattr(weapon_def, "weapon_sprite", "")).lower()
                is_melee_asset = weapon_class == "melee" or weapon_class == "throwable" or "/melee/" in sprite_path
                # modelosarmas.png fue dibujado con el cañón apuntando a la
                # derecha; por eso su orientación base es exactamente 0° y el
                # cursor define la rotación final, sin correcciones heredadas.
                base_angle = (
                    0.0
                    if sheet_key == "ranged"
                    else (0.0 if is_melee_asset and "lanza" in sprite_path else (-35.0 if is_melee_asset else {"magic": -32, "special": -25}.get(weapon_class, 0)))
                )
                flipped = math.cos(p.aim) < 0
                if flipped:
                    # El PNG se dibuja mirando al lado opuesto cuando el cursor
                    # cruza al lado izquierdo del jugador.
                    weapon_image = pygame.transform.flip(weapon_image, True, False)
                    rotation = base_angle + 180 - math.degrees(p.aim)
                else:
                    rotation = base_angle - math.degrees(p.aim)
                hand_offset = (p.radius + 1 - kick) if is_melee_asset else (p.radius - 1 - kick)
                if weapon_class == "throwable":
                    fan = getattr(weapon_def, "throwable_fan_angles", [-12, 0, 12])
                    fan = [float(v) for v in fan[:3]] or [-12.0, 0.0, 12.0]
                    for fan_index, fan_angle in enumerate(fan):
                        fan_rotation = rotation + fan_angle
                        side_offset = (fan_index - (len(fan) - 1) / 2.0) * 3.0
                        center = (
                            int(x + ax * hand_offset - ay * side_offset),
                            int(y + ay * hand_offset + ax * side_offset),
                        )
                        rot_key=(weapon_id, "throwable", flipped, fan_index, int(round(fan_rotation/5.0))*5)
                        rotated=self._weapon_rotation_cache.get(rot_key)
                        if rotated is None:
                            rotated=pygame.transform.rotate(weapon_image, fan_rotation)
                            self._weapon_rotation_cache[rot_key]=rotated
                        screen.blit(rotated, rotated.get_rect(center=center))
                else:
                    # La dirección izquierda/derecha forma parte de la clave.
                    # Sin esto, apuntar a 0° y después a 180° podía reutilizar el
                    # mismo sprite cacheado sin el espejo correspondiente.
                    rot_key=(weapon_id, bool(is_melee_asset), flipped, int(round(rotation/5.0))*5)
                    rotated=self._weapon_rotation_cache.get(rot_key)
                    if rotated is None:
                        rotated=self._rotate_weapon_from_grip(weapon_image, weapon_def, rotation, flipped=flipped) if is_melee_asset else pygame.transform.rotate(weapon_image, rotation)
                        self._weapon_rotation_cache[rot_key]=rotated
                    center = (int(x + ax * hand_offset), int(y + ay * hand_offset))
                    screen.blit(rotated, rotated.get_rect(center=center))
            else:
                x0, y0 = x + ax * (p.radius - 2 - kick), y + ay * (p.radius - 2 - kick)
                x1, y1 = x + ax * (p.radius + 12 - kick), y + ay * (p.radius + 12 - kick)
                pygame.draw.line(screen, (30, 30, 36), (x0, y0), (x1, y1), 6)
                pygame.draw.line(screen, weapon_def.color, (x0, y0), (x1, y1), 3)
            charge_max = float(getattr(weapon_def, "charge_max", 0) or 0)
            charge_time = float(getattr(equipped_weapon, "charge_time", 0) or 0)
            if charge_max > 0 and charge_time > 0:
                bw, bh = 38, 5
                bx, by = x - bw // 2, y - p.radius - 13
                pygame.draw.rect(screen, (15, 20, 31), (bx, by, bw, bh), border_radius=2)
                pygame.draw.rect(screen, (65, 225, 220), (bx + 1, by + 1, int((bw - 2) * min(1.0, charge_time / charge_max)), bh - 2), border_radius=2)
                pygame.draw.rect(screen, (125, 190, 205), (bx, by, bw, bh), 1, border_radius=2)

    def prop_collider(self, prop):
        """Huella física derivada del alpha visible del PNG del prop."""
        kind=str(prop.get("kind","crate"))
        key=kind if kind in self.prop_images else ("barrel_broken" if prop.get("broken") else "crate_broken" if kind=="crate" else None)
        image=self.prop_images.get(key)
        if image is None:
            return None
        bbox=image.get_bounding_rect(min_alpha=8)
        if not bbox.width or not bbox.height: return None
        # Los props se dibujan a su tamaño real; el collider usa ese mismo alpha.
        scale=1.0
        return (float(prop.get("x",0)),float(prop.get("y",0)),max(5.0,bbox.width*scale*0.42),max(5.0,min(bbox.height*scale*0.20,bbox.width*scale*0.30)))

    def _draw_world_prop(self, screen, prop, ox, oy):
        """Dibuja una caja/barril como objeto con profundidad Y real."""
        x, y = int(prop.get("x", 0) + ox), int(prop.get("y", 0) + oy)
        kind = prop.get("kind")
        if prop.get("broken"):
            alpha = max(0, min(255, int(255 * prop.get("fade", 0) / 2.2)))
            broken_key = "crate_broken" if kind == "crate" else "barrel_broken"
            broken_img = self.prop_images.get(broken_key)
            if broken_img is not None:
                faded = broken_img.copy()
                faded.set_alpha(alpha)
                screen.blit(faded, faded.get_rect(center=(x, y)))
            else:
                color = (120, 85, 55) if kind == "crate" else {"fire": (130,45,30), "poison": (40,110,45), "electric": (85,45,120)}.get(kind, (100,100,100))
                debris = pygame.Surface((32, 28), pygame.SRCALPHA)
                pygame.draw.rect(debris, (*color, alpha), (2, 4, 28, 22), border_radius=3)
                screen.blit(debris, (x - 16, y - 14))
            return
        image_key = "crate" if kind == "crate" else kind
        prop_image = self.prop_images.get(image_key)
        if prop_image is not None:
            screen.blit(prop_image, prop_image.get_rect(center=(x, y)))
            return
        if kind == "crate":
            pygame.draw.rect(screen, (105,70,45), (x-16,y-16,32,32), border_radius=3)
            pygame.draw.rect(screen, (185,130,75), (x-16,y-16,32,32), 2, border_radius=3)
            pygame.draw.line(screen, (65,43,32), (x-12,y-12), (x+12,y+12), 3)
            pygame.draw.line(screen, (65,43,32), (x+12,y-12), (x-12,y+12), 3)
        else:
            barrel_color = {"fire":(165,55,40), "poison":(55,135,65), "electric":(110,60,155)}.get(kind,(130,100,70))
            pygame.draw.ellipse(screen,(25,20,25),(x-23,y-19,46,40))
            pygame.draw.rect(screen,barrel_color,(x-20,y-22,40,44),border_radius=7)
            pygame.draw.rect(screen,(35,30,40),(x-20,y-22,40,44),2,border_radius=7)
            pygame.draw.line(screen,(210,190,160),(x-16,y-10),(x+16,y-10),3)
            mark={"fire":"!","poison":"☠","electric":"ϟ"}.get(kind,"!")
            mark_color={"fire":(255,65,45),"poison":(80,245,95),"electric":(205,95,255)}.get(kind,(255,245,220))
            pygame.draw.circle(screen,(28,24,35),(x,y-23),8)
            pygame.draw.circle(screen,mark_color,(x,y-23),6)
            txt=self.small.render(mark,True,(30,22,32)); screen.blit(txt,txt.get_rect(center=(x,y-23)))

    def chest_collider(self, chest):
        state="open" if chest.is_open else "closed"
        img=self.chest_type_images.get((getattr(chest,"chest_type","common"),state)) or self.chest_images.get(state)
        if img is None: return None
        bbox=img.get_bounding_rect(min_alpha=8)
        if not bbox.width or not bbox.height: return None
        scale=min(44.0/max(1,img.get_width(),img.get_height()),1.0)
        rx=max(5.0,bbox.width*scale*0.5)
        ry=max(4.0,bbox.height*scale*0.34)
        return float(chest.x),float(chest.y),rx,ry
    def _draw_world_chest(self, screen, chest, ox, oy):
        state = "open" if chest.is_open else "closed"
        img = self.chest_type_images.get((getattr(chest, "chest_type", "common"), state)) or self.chest_images.get(state)
        x, y = int(chest.x + ox), int(chest.y + oy)
        if img is not None:
            cache_key = ("chest", getattr(chest, "chest_type", "common"), state)
            draw_img = self._fit_cache.get(cache_key)
            if draw_img is None:
                draw_img = pygame.transform.smoothscale(img, (44, 44))
                self._fit_cache[cache_key] = draw_img
            screen.blit(draw_img, draw_img.get_rect(center=(x, y)))
        else:
            col = (100,190,130) if chest.is_open else (150,105,65)
            pygame.draw.rect(screen, col, (x-22,y-16,44,32), border_radius=8)
            pygame.draw.rect(screen, (35,30,30), (x-22,y-16,44,32), 3, border_radius=8)

    def _draw_world_portal(self, screen, sim, ox, oy, t):
        px, py = sim.portal_position[0] + ox, sim.portal_position[1] + oy
        if self.portal_frames:
            frame = self.portal_frames[int(t*9.0) % len(self.portal_frames)]
            frame = self._fit_effect_frame(frame, 92.0)
            screen.blit(frame, frame.get_rect(center=(int(px), int(py))))
        else:
            pygame.draw.circle(screen,(80,210,255),(int(px),int(py)),34,4)
            pygame.draw.circle(screen,(150,240,255),(int(px),int(py)),22,2)

    def _resolve_decoration_image(self, deco):
        """Resolve the exact decoration frame used by rendering and collision."""
        kind=str(deco.get("kind",""))
        variant=deco.get("variant",0)
        image=self.decoration_images.get(kind)
        frames=self.decoration_frames.get(kind)
        if frames and kind.startswith("biome_"):
            raw_variant=deco.get("variant",0)
            try:
                variant_seed=float(raw_variant)
            except (TypeError, ValueError):
                variant_seed=0.0
            index=(int(variant_seed*len(frames)) % len(frames)
                   if 0.0 <= variant_seed <= 1.0 else int(raw_variant) % len(frames))
            image=frames[index]
        if image is None and kind in ("bush","rock"):
            try:
                variant_index=int(variant) % 6 + 1
            except (TypeError, ValueError):
                variant_index=1
            image=self.decoration_images.get(f"{kind}_{variant_index}")
        return image

    def decoration_overlap(self, deco, x, y, radius):
        """Prueba la colisión real contra los píxeles opacos del modelo."""
        kind=str(deco.get("kind",""))
        variant=deco.get("variant",0)
        key=(kind,variant)
        cached=self._decoration_mask_cache.get(key)
        if cached is None:
            image=self._resolve_decoration_image(deco)
            if image is None:
                return False
            max_size=decoration_max_size(kind)
            image=self._fit_image(image,max_size)
            if image is None:
                return False
            cached=(pygame.mask.from_surface(image,threshold=8),image.get_size())
            self._decoration_mask_cache[key]=cached
        mask,size=cached
        ir=max(1,int(round(radius)))
        circle=self._circle_mask_cache.get(ir)
        if circle is None:
            circle_surface=pygame.Surface((ir*2+1,ir*2+1),pygame.SRCALPHA)
            pygame.draw.circle(circle_surface,(255,255,255,255),(ir,ir),ir)
            circle=pygame.mask.from_surface(circle_surface,threshold=8)
            self._circle_mask_cache[ir]=circle
        base_x=float(deco.get("x",0))*TILE+TILE/2
        base_y=float(deco.get("y",0))*TILE+TILE
        left=base_x-size[0]/2
        top=base_y-size[1]
        offset=(int(round(x-radius-left)),int(round(y-radius-top)))
        return mask.overlap(circle,offset) is not None

    def decoration_collider(self, deco):
        """Devuelve una huella elíptica basada en el alpha real del PNG.

        La huella física se concentra en la parte inferior visible del modelo:
        las zonas transparentes y el volumen vertical decorativo no bloquean al actor.
        """
        kind=str(deco.get("kind",""))
        variant=deco.get("variant",0)
        key=(kind,variant)
        if key in self._decoration_collider_cache:
            rx,ry,ox,oy=self._decoration_collider_cache[key]
        else:
            image=self._resolve_decoration_image(deco)
            if image is None:
                return None
            bbox=image.get_bounding_rect(min_alpha=8)
            if not bbox.width or not bbox.height:
                return None
            max_size=decoration_max_size(kind)
            scale=max_size/max(1,image.get_width(),image.get_height())
            visible_w=bbox.width*scale; visible_h=bbox.height*scale
            # El tamaño físico de la estatua deriva del mismo PNG y escala
            # que su modelo visible. Para estatuas usamos una huella más amplia
            # porque el cuerpo ocupa realmente el espacio alrededor de su base.
            if kind.startswith("statue_"):
                rx=max(8.0, visible_w*0.40)
                ry=max(7.0, min(visible_h*0.22, visible_w*0.34))
            else:
                rx=max(7.0,visible_w*0.36)
                ry=max(6.0,min(visible_h*0.18,visible_w*0.30))
            ox=0.0
            oy=0.0
            self._decoration_collider_cache[key]=(rx,ry,ox,oy)
        cx=float(deco.get("x",0))*TILE+TILE/2+ox
        cy=float(deco.get("y",0))*TILE+TILE+oy
        return cx+0.0,cy+0.0,rx,ry

    def _draw_single_scene_decoration(self, screen, deco, ox, oy, t):
        kind=deco.get("kind")
        image=self._resolve_decoration_image(deco)
        if image is None:
            return
        base_y=float(deco.get("y",0))*TILE+TILE
        x=float(deco.get("x",0))*TILE+TILE/2+ox
        y=base_y+oy
        max_size=decoration_max_size(kind)
        frames = self.decoration_frames.get(kind)
        if frames and not kind.startswith("biome_"):
            image = frames[int(t * 8.0) % len(frames)]
        draw=self._fit_image(image,max_size)
        if kind=="fountain_active":
            pulse=0.97+0.03*math.sin(t*3.2)
            draw=pygame.transform.smoothscale(draw,(max(1,int(draw.get_width()*pulse)),max(1,int(draw.get_height()*pulse))))
        screen.blit(draw,draw.get_rect(midbottom=(int(x),int(y))))

    def _draw_scene_decorations(self, screen, sim, ox, oy, t, front_only=None, min_base_y=None, max_base_y=None):
        """Compatibilidad: dibuja las decoraciones seleccionadas por profundidad."""
        for deco in getattr(sim.arena,"decorations",[]):
            base_y=float(deco.get("y",0))*TILE+TILE
            if min_base_y is not None and base_y < min_base_y: continue
            if max_base_y is not None and base_y > max_base_y: continue
            self._draw_single_scene_decoration(screen,deco,ox,oy,t)

    def _draw_shop_npcs(self, screen, sim, ox, oy, t):
        arena=sim.arena
        if arena.room_type != "shop": return []
        room_key=tuple(getattr(arena,"room_id",()))
        if room_key != self._merchant_intro_room:
            self._merchant_intro_room = room_key
            self._merchant_intro_start = t
        merchant_idle=self.npc_frames.get("merchant_idle",[])
        merchant_near=self.npc_frames.get("merchant_near",[])
        if not merchant_idle and not merchant_near: return []
        # La animación de quitarse la capa ocurre una sola vez al entrar en la sala.
        if room_key not in self._merchant_room_seen:
            self._merchant_room_seen.add(room_key)
            intro=merchant_near or merchant_idle
            idx=min(len(intro)-1,int(max(0.0,t-self._merchant_intro_start)*7.0)) if intro else 0
            frame=intro[idx] if intro else None
        else:
            # Después de la entrada se usa únicamente el ciclo idle. Nunca vuelve
            # a reproducirse la secuencia de quitar la capa al acercarse el jugador.
            frames=merchant_idle or merchant_near
            frame=frames[int(t*7.0)%len(frames)] if frames else None
        if frame is not None:
            frame=self._fit_image(frame,70)
            screen.blit(frame,frame.get_rect(midbottom=(int(arena.width/2+ox),int(arena.height/2-48+oy))))
        return [arena.height/2-48]

    def _draw_special_effects(self, screen, fx, ox, oy, t):
        for effect in getattr(fx, "special_effects", []):
            kind, x, y, angle, elapsed, duration, size = effect
            frames = self.special_effect_frames.get(kind)
            if not frames:
                continue
            idx = min(len(frames) - 1, int(elapsed * len(frames) / max(0.001, duration)))
            frame = self._fit_effect_frame(frames[idx], size)
            if kind == "arrow":
                frame = pygame.transform.rotate(frame, -math.degrees(angle))
            alpha = max(0, min(255, int(255 * (1.0 - max(0.0, elapsed-duration) / max(0.001,duration)))))
            if alpha < 255:
                frame.set_alpha(alpha)
            screen.blit(frame, frame.get_rect(center=(int(x + ox), int(y + oy))))

    def draw_world(self, screen, sim, fx, t):
        # Compatibilidad documental: la lógica real está en _draw_player_actor/_draw_enemy_actor.
        legacy_renderer_marker = """if not getattr(e.d, "sprite_set", None):
                ex, ey = x + math.cos(e.facing) * 5, y + math.sin(e.facing) * 5"""
        # ring_color = (105, 205, 255)
        # if not getattr(e.d, "sprite_set", None):
        #     ex, ey = x + math.cos(e.facing) * 5, y + math.sin(e.facing) * 5
        #     screen.blit(draw_sprite, draw_sprite.get_rect(center=(x, y + 1)))
        # Compatibilidad con copias mezcladas de versiones anteriores: algunas
        # tenían el orden temporal/efectos invertido en la llamada al renderizador.
        # Si llega el tiempo en `fx` y el objeto de efectos en `t`, normalizamos
        # los argumentos antes de consultar particles/texts/shake.
        if not hasattr(fx, "particles") and hasattr(t, "particles"):
            fx, t = t, float(fx)
        elif not hasattr(fx, "particles"):
            # Evita que un objeto inválido provoque un AttributeError al dibujar.
            # La simulación y el resto del render continúan aunque falten efectos.
            from types import SimpleNamespace
            fx = SimpleNamespace(particles=[], texts=[], shake=0.0, flash=0.0)
        arena, p = sim.arena, sim.player
        self._actor_light_cache.clear()
        # Cámara libre: el jugador permanece siempre en el centro.
        # No se limita a los bordes de la sala; el exterior queda negro y las
        # salas vecinas pueden ocupar ese espacio cuando la cámara las alcanza.
        cx = p.x - VIEW_W / 2
        cy = p.y - VIEW_H / 2
        if fx.shake > 0.2:
            cx += math.sin(t * 90) * fx.shake
            cy += math.cos(t * 77) * fx.shake
        ox, oy = -cx, -cy
        screen.fill((0, 0, 0))
        # El jugador sigue centrado incluso al mirar fuera de la sala. Cuando existe
        # una sala contigua, se muestra su arquitectura en continuidad con el mapa;
        # cualquier hueco sin sala permanece completamente negro.
        dungeon = getattr(sim, "dungeon", None)
        if dungeon is not None:
            for side, nrid in (
                ("N", dungeon.neighbor(dungeon.current, "N")),
                ("S", dungeon.neighbor(dungeon.current, "S")),
                ("W", dungeon.neighbor(dungeon.current, "W")),
                ("E", dungeon.neighbor(dungeon.current, "E")),
            ):
                neighbor = dungeon.rooms.get(nrid)
                if neighbor is None:
                    continue
                nbg = self._background(neighbor.arena)
                if side == "N":
                    nox, noy = ox, oy - arena.height
                elif side == "S":
                    nox, noy = ox, oy + arena.height
                elif side == "W":
                    nox, noy = ox - arena.width, oy
                else:
                    nox, noy = ox + arena.width, oy
                screen.blit(nbg, (nox, noy))
        screen.blit(self._background(arena), (ox, oy))
        # Corrección de color ambiental: baja ligeramente el brillo del escenario y
        # deja que las fuentes de luz cálidas/frías resalten sin saturar toda la sala.
        screen.blit(self._ambient_surface, (0, 0))

        # Iluminación dinámica 2D económica: luces radiales aditivas se calculan en
        # coordenadas de pantalla y se dibujan detrás de los actores y objetos.
        decor_lights = self._room_decor_lights(arena)
        lights = self._lights_surface
        player_light = self._player_light_surface
        lights.fill((0,0,0))
        player_light.fill((0,0,0))
        def add_light(target, world_x, world_y, radius, color, strength=1.0):
            radius=max(1,int(radius))
            lx, ly = int(world_x + ox), int(world_y + oy)
            if lx < -radius or ly < -radius or lx > VIEW_W + radius or ly > VIEW_H + radius:
                return
            bucket=max(1,min(12,int(round(strength*12))))
            key=(radius,tuple(color),bucket)
            surf=self._light_surface_cache.get(key)
            if surf is None:
                size=radius*2+2
                surf=pygame.Surface((size,size))
                surf.fill((0,0,0))
                for i in range(12,0,-1):
                    ring=i/12.0
                    rr=max(1,int(radius*ring))
                    falloff=(1.0-ring)**1.55
                    factor=(0.008+falloff*0.205)*(bucket/12.0)
                    tint=tuple(min(255,int(channel*factor)) for channel in color)
                    pygame.draw.circle(surf,tint,(radius+1,radius+1),rr)
                self._light_surface_cache[key]=surf
            target.blit(surf,(lx-radius-1,ly-radius-1))
        for light in decor_lights:
            rate = 8.5 if light["kind"] == "bonfire" else 2.2 if light["kind"] == "fountain" else 3.0
            flicker = 0.91 + 0.09 * math.sin(t * rate + light["x"] * 0.1)
            add_light(lights, light["x"], light["y"], light["radius"], light["color"], flicker)
        for hazard in getattr(sim, "hazards", []):
            life_ratio = max(0.15, min(1.0, hazard.get("life", 1.0) / 5.0))
            add_light(lights, hazard["x"], hazard["y"], min(115, int(hazard.get("radius", 70) * 1.25)), hazard.get("color", (100, 180, 120)), life_ratio)
        # Profundidad única para TODO lo anclado al suelo. Cada entidad, prop, cofre,
        # hoguera, portal y decoración entra en la misma cola Y: mayor Y = más cerca.
        actors=[]
        if p.alive:
            actors.append((p.y, "player", p))
            # "player", p
        for e in sim.enemies:
            if e.alive:
                actors.append((e.y, "enemy", e))
        for drone in getattr(sim, "drones", []):
            actors.append((float(drone.get("y",0)), "drone", drone))
                # "enemy", e
        for prop in getattr(sim,"props",[]):
            if prop.get("broken") and prop.get("fade",0)<=0: continue
            actors.append((float(prop.get("y", 0)), "prop", prop))
        chest=getattr(sim,"chest",None)
        if chest is not None: actors.append((float(chest.y), "chest", chest))
        if sim.portal: actors.append((float(sim.portal_position[1]), "portal", sim.portal_position))
        for light in decor_lights:
            if light.get("kind")=="bonfire":
                actors.append((float(light["y"]), "bonfire", light))
        for deco in getattr(arena,"decorations",[]):
            actors.append((float(deco.get("y",0))*TILE+TILE,"deco",deco))
        for pickup in getattr(sim, "pickups", []):
            if pickup.get("kind") == "coin":
                actors.append((float(pickup.get("y", 0)), "coin", pickup))
        if arena.room_type=="shop":
            room_key=tuple(getattr(sim.room, "id", getattr(arena, "room_id", (0,0))))
            if self._merchant_intro_room != room_key:
                self._merchant_intro_room = room_key
                self._merchant_intro_start = t
            if self.merchant_variants:
                variant_index = int(getattr(sim, "merchant_variant_by_room", {}).get(room_key, 0)) % len(self.merchant_variants)
                merchant_idle = self.merchant_variants[variant_index]
                merchant_near = merchant_idle
            else:
                merchant_idle=self.npc_frames.get("merchant_idle", [])
                merchant_near=self.npc_frames.get("merchant_near", [])
            near = math.hypot(p.x-arena.width/2,p.y-arena.height/2)<155
            merchant_wander_x = math.sin(t * 0.72 + room_key[0] * 0.9 + room_key[1] * 0.4) * 10.0
            merchant_wander_y = math.sin(t * 1.17 + room_key[0] * 0.3) * 2.0
            actors.append((arena.height/2-48 + merchant_wander_y, "merchant", {
                "idle": merchant_idle,
                "near": merchant_near,
                "near_active": near,
                "intro_start": self._merchant_intro_start,
                "wander_x": merchant_wander_x,
                "wander_y": merchant_wander_y,
            }))
            # La animación de entrada (capa -> se la quita) solo ocurre una vez por sala.
        actors.sort(key=lambda item:item[0])
        for actor_y,kind,obj in actors:
            if kind=="player": self._draw_player_actor(screen,obj,ox,oy,t)
            elif kind=="enemy": self._draw_enemy_actor(screen,obj,arena,sim,ox,oy,decor_lights,t)
            elif kind=="drone": self._draw_drone_actor(screen,obj,ox,oy,t)
            elif kind=="merchant":
                intro=obj["idle"]; elapsed=max(0.0,t-float(obj.get("intro_start",t)))
                frames=obj["near"] if obj.get("near_active") and obj.get("near") else obj["idle"]
                frame=frames[int(t*7.0) % len(frames)] if frames else None
                if frame is not None:
                    frame=self._fit_image(frame,70)
                    mx = int(arena.width / 2 + ox + float(obj.get("wander_x", 0.0)))
                    my = int(arena.height / 2 - 48 + oy + float(obj.get("wander_y", 0.0)))
                    screen.blit(frame,frame.get_rect(midbottom=(mx,my)))
                    bubble = pygame.Rect(mx + 25, my - 67, 32, 27)
                    pygame.draw.ellipse(screen, (245, 245, 248), bubble)
                    pygame.draw.polygon(screen, (245, 245, 248), [(bubble.left + 5, bubble.bottom - 5), (bubble.left + 1, bubble.bottom + 2), (bubble.left + 11, bubble.bottom - 3)])
                    if self.coin_frames:
                        coin = self._fit_image(self.coin_frames[int(t * 8.0) % len(self.coin_frames)], 16)
                        if coin is not None:
                            screen.blit(coin, coin.get_rect(center=bubble.center))
            elif kind=="coin":
                frames=self.coin_frames
                if frames:
                    phase=float(obj.get("phase",0.0))
                    frame=frames[int((t*8.0+phase)%len(frames))]
                    screen.blit(frame,frame.get_rect(center=(int(obj["x"]+ox),int(obj["y"]+oy))))
                else:
                    pulse=1.0+0.08*math.sin(t*8.0+float(obj.get("phase",0.0)))
                    rr=max(5,int(7*pulse))
                    pygame.draw.circle(screen,(238,190,55),(int(obj["x"]+ox),int(obj["y"]+oy)),rr)
                    pygame.draw.circle(screen,(255,232,120),(int(obj["x"]+ox),int(obj["y"]+oy)),rr,1)
            # Las mascotas del comerciante no se renderizan.
            elif kind=="prop": self._draw_world_prop(screen,obj,ox,oy)
            elif kind=="chest": self._draw_world_chest(screen,obj,ox,oy)
            elif kind=="portal": self._draw_world_portal(screen,sim,ox,oy,t)
            elif kind=="bonfire": self._draw_world_bonfire(screen,obj,ox,oy,t)
            elif kind=="deco": self._draw_single_scene_decoration(screen,obj,ox,oy,t)

        if sim.portal:
            add_light(lights, arena.width / 2, arena.height / 2, 105, (70, 190, 235), 0.7)
        # La luz del jugador se compone al final en una capa propia, para que no
        # quede sustituida por los colores de hogueras, antorchas o efectos elementales.
        player_flicker = 0.96 + 0.04 * math.sin(t * 4.2)
        add_light(player_light, p.x, p.y, 190, (120, 190, 230), player_flicker)
        screen.blit(lights, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        screen.blit(player_light, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        # Las sombras se aplican después de las luces para que estas no iluminen
        # artificialmente el suelo que queda detrás de paredes, pilares y objetos.
        self._draw_dynamic_shadows(screen, arena, sim, ox, oy)
        self._draw_decor_lights(screen, decor_lights, ox, oy, t)
        self.cam = (ox, oy)
        # Puertas arquitectónicas de 3 bloques, centradas en el eje de la sala.
        for d in arena.doors.values():
            horizontal=d.side in ("N","S")
            if horizontal:
                x=(d.x-1)*TILE+int(ox)
                door_h = TILE*2 if d.side=="N" else TILE
                y=(d.y-door_h//TILE+1)*TILE+int(oy) if d.side=="N" else d.y*TILE+int(oy)
                span=pygame.Rect(x,y,TILE*3,door_h); cx,cy=span.center
            else:
                x=d.x*TILE+int(ox); y=(d.y-1)*TILE+int(oy)
                span=pygame.Rect(x,y,TILE,TILE*3); cx,cy=span.center
            frame=self.column_image
            if frame is not None and horizontal:
                narrow=self._fit_cache.get(("door_narrow",id(frame)))
                if narrow is None:
                    narrow=pygame.transform.smoothscale(frame,(8,44)); self._fit_cache[("door_narrow",id(frame))]=narrow
                base_y=span.y+TILE*2 if d.side=="N" else span.y
                for frame_x in (span.left,span.right-8): screen.blit(narrow,narrow.get_rect(midbottom=(frame_x+4,base_y)))
            elif frame is not None:
                lintel=self._fit_cache.get(("door_lintel",id(frame)))
                if lintel is None:
                    lintel=pygame.transform.smoothscale(pygame.transform.rotate(frame,90),(32,8)); self._fit_cache[("door_lintel",id(frame))]=lintel
                for fy in (span.top,span.bottom-8): screen.blit(lintel,(span.x,fy))
            door_frames = self.door_front_frames
            if door_frames:
                state_index = 1 if d.open and len(door_frames) > 1 else 0
                door_img = door_frames[state_index]
                if not horizontal:
                    door_img = pygame.transform.rotate(door_img, 90)
                door_img = pygame.transform.scale(door_img, span.size)
                # El modelo de puerta se apoya sobre un respaldo opaco de pared.
                # Así ningún píxel transparente del PNG deja ver el vacío/fondo.
                backing = pygame.Surface(span.size, pygame.SRCALPHA)
                wall_color = tuple(self.data.biomes[arena.biome]["wall"])
                wall_top = tuple(self.data.biomes[arena.biome]["wall_top"])
                backing.fill((*wall_color, 255))
                pygame.draw.rect(backing, (*wall_top, 255), (0, 0, span.w, max(3, TILE // 6)))
                screen.blit(backing, span.topleft)
                # Las puertas laterales usan el mismo modelo, girado 90°.
                # En el lado oeste se espeja para mantener la orientación exterior.
                if d.side == "W":
                    door_img = pygame.transform.flip(door_img, True, False)
                screen.blit(door_img, span.topleft)
                continue
            if not d.open:
                inner=span.inflate(-6,-6)
                pygame.draw.rect(screen,(24,22,29),inner,border_radius=3); pygame.draw.rect(screen,(130,55,58),inner,2,border_radius=3)
                if horizontal:
                    for bx in (span.left+12,span.left+TILE,span.right-12): pygame.draw.line(screen,(150,135,125),(bx,span.top+5),(bx,span.bottom-5),3)
                    pygame.draw.line(screen,(190,80,70),(span.left+4,span.centery),(span.right-4,span.centery),3)
                else:
                    for by in (span.top+12,span.top+TILE,span.bottom-12): pygame.draw.line(screen,(150,135,125),(span.left+5,by),(span.right-5,by),3)
                    pygame.draw.line(screen,(190,80,70),(span.centerx,span.top+4),(span.centerx,span.bottom-4),3)
            else:
                if d.side=="N": points=[(cx,cy-15),(cx-12,cy+1),(cx-5,cy+1),(cx-5,cy+11),(cx+5,cy+11),(cx+5,cy+1),(cx+12,cy+1)]
                elif d.side=="S": points=[(cx,cy+15),(cx-12,cy-1),(cx-5,cy-1),(cx-5,cy-11),(cx+5,cy-11),(cx+5,cy-1),(cx+12,cy-1)]
                elif d.side=="W": points=[(cx-15,cy),(cx+1,cy-12),(cx+1,cy-5),(cx+11,cy-5),(cx+11,cy+5),(cx+1,cy+5),(cx+1,cy+12)]
                else: points=[(cx+15,cy),(cx-1,cy-12),(cx-1,cy-5),(cx-11,cy-5),(cx-11,cy+5),(cx-1,cy+5),(cx-1,cy+12)]
                pygame.draw.polygon(screen,(22,24,30),points)
                inner=[(cx+(px-cx)*0.82,cy+(py-cy)*0.82) for px,py in points]
                pygame.draw.polygon(screen,(250,250,255),inner)
        # Cofres y props ya fueron dibujados dentro de la pasada de profundidad
        # compartida con actores y decoraciones. Aquí solo queda el prompt del cofre,
        # que es UI y por eso debe permanecer por encima de todo.
        chest = getattr(sim, "chest", None)
        if chest is not None and not chest.is_open and math.hypot(chest.x - sim.player.x, chest.y - sim.player.y) < 72:
            self.text(screen, "E  ABRIR COFRE", (chest.x + ox, chest.y + 30), (255, 235, 150), self.small, True)

        for h in getattr(sim,"hazards",[]):
            radius=max(1,int(h["radius"]))
            color=tuple(h["color"])
            key=(radius,color)
            layer=self._hazard_surface_cache.get(key)
            if layer is None:
                layer=pygame.Surface((radius*2,radius*2),pygame.SRCALPHA)
                center=(radius,radius)
                pygame.draw.circle(layer,(*color,255),center,radius)
                pygame.draw.circle(layer,(*color,255),center,radius,3)
                self._hazard_surface_cache[key]=layer
            layer.set_alpha(max(30,min(100,int(100*h["life"]/5.0))))
            screen.blit(layer,(int(h["x"]+ox-radius),int(h["y"]+oy-radius)))
        for wave in getattr(sim,"wave_attacks",[]):
            color=wave.get("color",(255,120,50))
            radius=max(1,int(wave["radius"]))
            center=(int(wave["x"]+ox),int(wave["y"]+oy))
            # LOS ya se calcula en la simulación para los impactos. El render
            # sólo dibuja el anillo, evitando cientos de consultas de colisión.
            pygame.draw.circle(screen,color,center,radius,4)
            if radius>18:
                pygame.draw.circle(screen,tuple(min(255,int(v*0.55)) for v in color),center,radius-4,1)

        # Tienda: objetos físicos flotando, sin tarjetas/botones. Acercarse e
        # interactuar compra la oferta; precio y nombre quedan debajo del objeto.
        for offer_index, offer in enumerate(getattr(sim, "shop_offers", [])):
            if offer.sold:
                continue
            col = (255, 190, 80) if offer.kind == "weapon" else (120, 220, 150)
            px = int(offer.x + ox)
            bob = int(math.sin(t * 4.5 + offer_index * 1.2) * 3)
            py = int(offer.y + oy) + bob
            pygame.draw.ellipse(screen, (6, 8, 14), (px - 15, py + 12, 30, 8))
            pygame.draw.circle(screen, (18, 22, 34), (px, py), 19)
            pygame.draw.circle(screen, col, (px, py), 19, 1)
            icon = None
            if offer.kind == "weapon":
                icon = self.weapon_scaled_images.get(offer.id)
            elif offer.kind in ("heal", "energy"):
                icon = self.misc_images.get(offer.kind)
            if icon is not None:
                icon = self._fit_image(icon, 29)
                screen.blit(icon, icon.get_rect(center=(px, py)))
            elif offer.kind == "item":
                # Los objetos permanentes no dependen de un PNG inexistente: se
                # representan con un pequeño núcleo de mejora y su nombre debajo.
                pygame.draw.polygon(screen, col, [(px,py-10),(px+10,py),(px,py+10),(px-10,py)])
                pygame.draw.polygon(screen, (235,245,255), [(px,py-10),(px+10,py),(px,py+10),(px-10,py)], 1)
                glyph=self.small.render(str(offer.name[:1]).upper(), True, (20,24,34))
                screen.blit(glyph, glyph.get_rect(center=(px,py)))
            else:
                pygame.draw.circle(screen, col, (px, py), 7, 2)
            self.text(screen, str(offer.price), (px, py + 24), (255, 225, 135), self.small, center=True)
            self.text(screen, str(offer.name)[:16], (px, py + 37), col, self.small, center=True)
            if offer.kind == "item":
                item_def = self.data.items.get(offer.id, {})
                effects = item_def.get("effects", {}) if isinstance(item_def, dict) else getattr(item_def, "effects", {})
                effect_labels = []
                for key, value in effects.items():
                    if key == "damage_mult": effect_labels.append("+%d%% daño" % round(float(value) * 100))
                    elif key == "move_speed_mult": effect_labels.append("+%d%% velocidad" % round(float(value) * 100))
                    elif key == "attack_speed_mult": effect_labels.append("+%d%% cadencia" % round(float(value) * 100))
                    elif key == "max_hp": effect_labels.append("+%d HP" % int(value))
                    elif key == "max_shield": effect_labels.append("+%d escudo" % int(value))
                    elif key == "max_energy": effect_labels.append("+%d energía" % int(value))
                    elif key == "projectile_count": effect_labels.append("+%d proyectil" % int(value))
                    elif key == "pierce": effect_labels.append("+%d perforación" % int(value))
                    elif key == "coin_radius": effect_labels.append("+%d radio monedas" % int(value))
                description = ", ".join(effect_labels) or "Mejora permanente"
                self.text(screen, description[:25], (px, py + 51), (198, 210, 222), self.small, center=True)

        # Telegráfico del láser del jugador: una esfera energética crece
        # durante el segundo previo al primer segmento del haz.
        player_weapon = getattr(sim.player, "weapon", None)
        player_weapon_def = getattr(player_weapon, "d", None)
        if player_weapon_def is not None and getattr(player_weapon_def, "laser_weapon", False):
            charge = float(getattr(player_weapon, "charge_time", 0.0))
            start_charge = max(0.01, float(getattr(player_weapon_def, "laser_start_charge", 1.0)))
            if 0.0 < charge < start_charge:
                progress = max(0.0, min(1.0, charge / start_charge))
                angle = float(getattr(sim.player, "aim", 0.0))
                sx = int(sim.player.x + math.cos(angle) * 14 + ox)
                sy = int(sim.player.y + math.sin(angle) * 14 + oy)
                color = tuple(getattr(player_weapon_def, "color", (120, 220, 255)))
                pulse = 0.5 + 0.5 * math.sin(t * 22.0)
                radius = 6.0 + 9.0 * progress + pulse * 2.0
                orb = pygame.Surface((52, 52), pygame.SRCALPHA)
                pygame.draw.circle(orb, (*color, 24), (26, 26), int(radius * 2.0))
                pygame.draw.circle(orb, (*color, 72), (26, 26), int(radius * 1.35))
                pygame.draw.circle(orb, (255, 255, 255, 235), (26, 26), max(3, int(radius * 0.48)))
                pygame.draw.circle(orb, (*color, 235), (26, 26), max(4, int(radius)))
                screen.blit(orb, orb.get_rect(center=(sx, sy)))

        # Rayos láser persistentes: finos al inicio, crecen entre 1 y 3 s,
        # siguen el apuntado del propietario y terminan en la primera colisión.
        for laser in getattr(sim, "lasers", []):
            owner=laser.get("owner"); angle=float(laser.get("angle",0.0))
            if owner is None: continue
            charge_left = float(laser.get("charge_left", 0.0))
            if charge_left > 0.0:
                progress = 1.0 - charge_left / max(0.001, float(laser.get("charge_duration", 1.0)))
                sx = int(owner.x + math.cos(angle) * 14 + ox)
                sy = int(owner.y + math.sin(angle) * 14 + oy)
                color = tuple(laser.get("color", (255, 100, 100)))
                pulse = 0.5 + 0.5 * math.sin(t * 22.0 + owner.x * 0.01)
                radius = 6.0 + 9.0 * max(0.0, min(1.0, progress)) + pulse * 2.0
                orb = pygame.Surface((52, 52), pygame.SRCALPHA)
                pygame.draw.circle(orb, (*color, 24), (26, 26), int(radius * 2.0))
                pygame.draw.circle(orb, (*color, 72), (26, 26), int(radius * 1.35))
                pygame.draw.circle(orb, (255, 255, 255, 235), (26, 26), max(3, int(radius * 0.48)))
                pygame.draw.circle(orb, (*color, 235), (26, 26), max(4, int(radius)))
                screen.blit(orb, orb.get_rect(center=(sx, sy)))
                continue
            length=float(laser.get("_render_length",laser.get("travel",laser.get("range",760.0))))
            sx,sy=owner.x+ox,owner.y+oy
            ex,ey=owner.x+math.cos(angle)*length+ox,owner.y+math.sin(angle)*length+oy
            width=max(1,int(laser.get("width",2.0)))
            color=tuple(laser.get("color",(120,220,255)))
            # halo + núcleo para un aspecto energético tipo Kamehameha.
            pygame.draw.line(screen, tuple(min(255,int(c*0.38)) for c in color), (int(sx),int(sy)), (int(ex),int(ey)), max(3,width*3))
            pygame.draw.line(screen, color, (int(sx),int(sy)), (int(ex),int(ey)), width)
            pygame.draw.circle(screen,(255,255,255),(int(ex),int(ey)),max(2,width//2+1))

        # Loot: armas y consumibles del suelo flotan ligeramente sobre su sombra.
        for item_index, it in enumerate(sim.items):
            ix = getattr(it, "x", arena.width / 2)
            iy = getattr(it, "y", arena.height / 2)
            bob = int(math.sin(t * 4.8 + item_index * 0.85) * 3)
            px, py = int(ix + ox), int(iy + oy) + bob
            pygame.draw.ellipse(screen, (6, 8, 14), (px - 14, py + 13 - bob, 28, 7))
            if getattr(it, "kind", "item") == "weapon":
                pygame.draw.circle(screen, (18, 24, 35), (px, py), 18)
                pygame.draw.circle(screen, (100, 220, 255), (px, py), 18, 1)
                weapon_id = getattr(it, "weapon_id", "")
                weapon_def = self.data.weapons.get(weapon_id)
                sheet_key = getattr(weapon_def, "weapon_sprite_sheet", None) if weapon_def is not None else None
                frames = self.weapon_variant_frames.get(sheet_key, [])
                if frames:
                    index = int(getattr(weapon_def, "weapon_sprite_index", 0))
                    icon = self._fit_image(frames[index], 30) if 0 <= index < len(frames) else None
                else:
                    icon = self.weapon_scaled_images.get(weapon_id)
                if icon is not None:
                    icon = self._fit_image(icon, 30)
                    screen.blit(icon, icon.get_rect(center=(px, py)))
            elif getattr(it, "kind", "item") in ("heal", "energy"):
                pygame.draw.circle(screen, (18, 24, 35), (px, py), 16)
                icon = self._fit_image(self.misc_images.get(it.kind), 25)
                if icon is not None:
                    screen.blit(icon, icon.get_rect(center=(px, py)))
                else:
                    pygame.draw.circle(screen, (235, 90, 105) if it.kind == "heal" else (85, 180, 255), (px, py), 7)
            elif getattr(it, "kind", "item") == "ammo":
                pygame.draw.circle(screen, (18, 24, 35), (px, py), 16)
                mag=self.ammo_magazine_image
                screen.blit(mag,mag.get_rect(center=(px,py)))
                self.text(screen, str(getattr(it, "magazines", 1)), (px, py+22), (245, 225, 150), self.small, True)
            else:
                pygame.draw.circle(screen, (20, 20, 25), (px, py), 12)
                pygame.draw.circle(screen, (255, 210, 70), (px, py), 7)

        for pickup_index, pickup in enumerate(getattr(sim,"pickups",[])):
            if pickup.get("kind") != "coin": continue
            px,py=int(pickup["x"]+ox),int(pickup["y"]+oy)
            if self.coin_frames:
                frame=self.coin_frames[int(max(0.0,t)*8)%len(self.coin_frames)]
                bob=int(math.sin(t*5+pickup_index*.7)*2)
                screen.blit(frame,frame.get_rect(center=(px,py+bob)))
            else:
                pygame.draw.circle(screen,(255,215,60),(px,py),5)
                pygame.draw.circle(screen,(255,245,170),(px-1,py-1),2)
                pygame.draw.line(screen,(180,120,25),(px,py-3),(px,py+3),1)


        # The old melee arc/trail is intentionally removed; melee attacks now use
        # only the six-frame slash animation.
        for pr in sim.pool.items:
            if not pr.active:
                continue
            pos = (int(pr.x + ox), int(pr.y + oy))
            if pos[0] < -80 or pos[0] > VIEW_W + 80 or pos[1] < -80 or pos[1] > VIEW_H + 80:
                continue
            # Los proyectiles de fuego usan la animacion ignea generica y siempre
            # se orientan siguiendo su trayectoria, tanto para jugador como enemigos.
            fire_projectile_frames = self.special_effect_frames.get("new_fireball") or self.ignite_projectile_frames
            if pr.dtype == "fire" and fire_projectile_frames:
                # boladefuego_spritesheet.png tiene la silueta orientada hacia la izquierda;
                # compensamos 180° para que el proyectil visual apunte en su trayectoria.
                angle = (math.atan2(pr.vy, pr.vx) + math.pi) if not pr.stuck else (pr.stuck_angle + math.pi)
                self._draw_combat_sprite_animation(
                    screen, fire_projectile_frames, pr.age,
                    pr.x + ox, pr.y + oy, max(18.0, pr.radius * 5.5 * getattr(pr, "visual_scale", 1.0)),
                    angle=angle,
                    alpha=max(0, int(255 * min(1.0, pr.life / 0.08))) if pr.stuck else 255,
                    loop=True, duration=0.30
                )
                continue
            if isinstance(getattr(pr, "sprite_key", None), str) and pr.sprite_key.startswith("__weapon_sheet__:"):
                parts = pr.sprite_key.split(":")
                if len(parts) == 3:
                    sheet_key = parts[1]
                    try:
                        index = int(parts[2])
                    except ValueError:
                        index = -1
                    frames = self.weapon_variant_frames.get(sheet_key, [])
                    if 0 <= index < len(frames):
                        scaled = self._fit_image(frames[index], 16.0 * getattr(pr, "visual_scale", 1.0))
                        if scaled is not None:
                            angle = math.degrees(math.atan2(pr.vy, pr.vx)) if not pr.stuck else math.degrees(pr.stuck_angle)
                            rot_key=("weapon_projectile", sheet_key, index, round(float(getattr(pr, "visual_scale", 1.0)),2), int(round(angle/8.0))*8)
                            rotated=self._rotation_cache.get(rot_key)
                            if rotated is None:
                                rotated=pygame.transform.rotate(scaled, -angle)
                                self._rotation_cache[rot_key]=rotated
                            if pr.stuck and pr.stuck_timer < 1.0:
                                rotated=rotated.copy()
                                rotated.set_alpha(max(0, int(255 * pr.stuck_timer)))
                            screen.blit(rotated, rotated.get_rect(center=pos))
                            continue
            if isinstance(getattr(pr, "sprite_key", None), str) and pr.sprite_key.startswith("__sheet__:"):
                sheet_key=pr.sprite_key.split(":",1)[1]
                if sheet_key == "minigolem_rock":
                    frames=self.enemy_sprites.get("minigolem",{}).get("projectile",[])
                else:
                    frames=self.enemy_projectile_frames.get(sheet_key)
                    if frames is None:
                        path = self.asset_root / sheet_key.removeprefix("assets/")
                        frames = self._load_sheet_frames(path) if path.is_file() else []
                        self.enemy_projectile_frames[sheet_key] = frames
                if frames:
                    self._draw_projectile_sheet(screen, frames, pr, ox, oy, max(18.0, pr.radius*4.2*getattr(pr,"visual_scale",1.0)))
                    continue
            sprite_path = getattr(pr, "sprite_key", None) or self.default_projectiles.get(
                getattr(pr, "dtype", "physical"), self.default_projectiles["physical"])
            image = self.projectile_images.get(sprite_path)
            if image is None:
                image = self._load_trimmed_asset(sprite_path)
                if image is not None:
                    self.projectile_images[sprite_path] = image
            if image is not None:
                filename = Path(sprite_path).name
                max_dim = 12
                if "assets/weapons/melee/lanza" in sprite_path or "assets/weapons/snipers/sniper5" in sprite_path:
                    max_dim = 58 if "assets/weapons/melee/lanza" in sprite_path else 26
                if filename == "projectile_04.png": max_dim = 19
                elif filename == "projectile_05.png": max_dim = 18
                elif filename in ("projectile_06.png", "projectile_07.png", "projectile_08.png", "projectile_09.png"): max_dim = 14
                elif filename == "projectile_10.png": max_dim = 17
                elif filename in ("projectile_12.png", "projectile_13.png", "projectile_14.png"): max_dim = 16
                elif filename == "projectile_15.png": max_dim = 15
                cache_key = (sprite_path, max_dim, round(float(getattr(pr, "visual_scale", 1.0)),2))
                scaled = self.projectile_scaled_images.get(cache_key)
                if scaled is None:
                    scaled = self._fit_image(image, max_dim * getattr(pr, "visual_scale", 1.0))
                    self.projectile_scaled_images[cache_key] = scaled
                directional_sprite = ("assets/weapons/melee/lanza" in sprite_path or
                                      "assets/weapons/snipers/sniper5" in sprite_path)
                if scaled.get_width() > scaled.get_height() * 1.35 or directional_sprite:
                    angle = math.degrees(math.atan2(pr.vy, pr.vx)) if not pr.stuck else math.degrees(pr.stuck_angle)
                    correction = 0.0
                    rot_key=(sprite_path,max_dim,round(float(getattr(pr,"visual_scale",1.0)),2),int(round((correction-angle)/8.0))*8)
                    rotated=self._rotation_cache.get(rot_key)
                    if rotated is None:
                        rotated=pygame.transform.rotate(scaled,correction-angle)
                        self._rotation_cache[rot_key]=rotated
                    scaled=rotated
                if pr.stuck and pr.stuck_timer < 1.0:
                    scaled = scaled.copy()
                    scaled.set_alpha(max(0, int(255 * pr.stuck_timer)))
                screen.blit(scaled, scaled.get_rect(center=pos))
            elif pr.team == 1:
                pygame.draw.circle(screen, (255, 230, 200), pos, int(pr.radius) + 1)
                pygame.draw.circle(screen, pr.color, pos, int(pr.radius))
            else:
                pygame.draw.circle(screen, pr.color, pos, int(pr.radius))
                pygame.draw.circle(screen, (255, 255, 255), pos, max(1, int(pr.radius) - 2))

        # Decoración más cercana a cámara: cubre parcialmente a los actores que
        # están físicamente detrás, respetando la profundidad por Y.

        # Efectos especiales del paquete nuevo: rayos/explosiones sobre el escenario.
        self._draw_special_effects(screen, fx, ox, oy, t)

        # Death animations are drawn after living actors so the final pose can fade out.
        for effect in getattr(fx, "enemy_deaths", []):
            self._draw_enemy_death(screen, effect, ox, oy)

        # Pasada de efectos animados: cortes, explosiones y el hielo de congelacion.
        for effect in getattr(fx, "melee_slashes", []):
            ex, ey, angle, elapsed, max_life, size = effect
            self._draw_combat_sprite_animation(
                screen, self.melee_slash_frames, elapsed,
                ex + ox + math.cos(angle) * size * 0.20,
                ey + oy + math.sin(angle) * size * 0.20,
                size, angle=angle,
                alpha=max(0, int(255 * min(1.0, (max_life - elapsed) / 0.04)))
            )

        for effect in getattr(fx, "explosions", []):
            ex, ey, elapsed, max_life, size = effect
            self._draw_combat_sprite_animation(
                screen, self.explosion_frames, elapsed,
                ex + ox, ey + oy, size, alpha=255
            )

        for entity, ex, ey, radius in [
            (e, e.x, e.y, e.radius) for e in sim.enemies if getattr(e, "frozen", 0) > 0
        ] + ([(p, p.x, p.y, p.radius)] if getattr(p, "frozen", 0) > 0 and p.alive else []):
            if self.frozen_image is not None:
                size = max(42.0, radius * 4.8)
                ice = self._fit_effect_frame(self.frozen_image, size)
                pulse = 0.5 + 0.5 * math.sin(t * 8.0)
                ice.set_alpha(int(120 + 25 * pulse))
                screen.blit(ice, ice.get_rect(center=(int(ex + ox), int(ey + oy))))

        # Aturdimiento de Rook: no usa el overlay de hielo de congelación.
        # El signo de exclamación queda sobre la cabeza mientras dura el stun.
        for e in sim.enemies:
            if not getattr(e, "alive", False) or getattr(e, "stunned", 0.0) <= 0:
                continue
            sx, sy = int(e.x + ox), int(e.y + oy - max(22, e.radius * 2.0))
            if not self.ui_atlas.draw_icon(screen, (sx, sy), size=22, kind="exclamation"):
                self.text(screen, "!", (sx, sy), (255, 225, 95), self.menu_font, center=True)

        for q in fx.particles:
            a = q[4] / q[5]
            s = max(1, int(q[6] * a + 0.5))
            pygame.draw.rect(screen, q[7], (int(q[0] + ox), int(q[1] + oy), s, s))
        for tx in fx.texts:
            self.text(screen, tx[3], (tx[0] + ox, tx[1] + oy), tx[4], self.small, center=True)

        # Pasada de primer plano: evita que el jugador parezca caminar por encima
        # de las columnas o del muro inferior cuando está situado detrás de ellos.
        self._draw_architecture_foreground(screen, arena, sim, decor_lights, ox, oy)

    def draw_minimap(self, screen, sim, large=False):
        """Mapa de salas: 💀 jefe, portal animado y moneda de tienda."""
        dungeon=getattr(sim,"dungeon",None); rooms=getattr(dungeon,"rooms",{}) if dungeon else {}
        if not rooms:return
        ids=list(rooms); min_x=min(r[0] for r in ids); max_x=max(r[0] for r in ids); min_y=min(r[1] for r in ids); max_y=max(r[1] for r in ids)
        cols=max(1,max_x-min_x+1); rows=max(1,max_y-min_y+1)
        if large:
            margin_x,margin_y=92,68; cell=max(38,min(72,int(min((VIEW_W-2*margin_x)/cols,(VIEW_H-2*margin_y)/rows))))
            width,height=cols*cell+44,rows*cell+74; x,y=(VIEW_W-width)//2,(VIEW_H-height)//2; content_x=22; origin_y=42
            panel=pygame.Surface((width,height),pygame.SRCALPHA);
            if not self.ui_atlas.draw_panel(panel, pygame.Rect(0,0,width,height), border=12):
                pygame.draw.rect(panel,(7,10,18,245),panel.get_rect(),border_radius=14); pygame.draw.rect(panel,(88,108,132,235),panel.get_rect(),2,border_radius=14)
            self.text(panel,"MAPA DE LA DUNGEON",(width//2,22),(240,205,120),self.menu_font,center=True)
        else:
            # El minimapa compacto ocupa algo más de pantalla, pero mantiene un
            # margen suficiente para no competir con el HUD. La celda crece de
            # forma proporcional al número de salas y evita amontonamientos.
            cell=min(17,max(9,int(min(170/cols,88/rows))))
            width,height=max(178, cols*cell+28),rows*cell+32
            x,y=VIEW_W-width-8,58
            content_x = (width - cols*cell)//2
            content_y = 8
            origin_y=content_y
            panel=pygame.Surface((width,height),pygame.SRCALPHA)
            pygame.draw.rect(panel,(8,12,22,172),panel.get_rect(),border_radius=6)
            pygame.draw.rect(panel,(82,100,125,195),panel.get_rect(),1,border_radius=6)
        for rid in rooms:
            rx=content_x+(rid[0]-min_x)*cell; ry=origin_y+(rid[1]-min_y)*cell; cx,cy=rx+cell//2,ry+cell//2
            for nr in ((rid[0]+1,rid[1]),(rid[0],rid[1]+1)):
                if nr in rooms:
                    nx=content_x+(nr[0]-min_x)*cell+cell//2; ny=origin_y+(nr[1]-min_y)*cell+cell//2; pygame.draw.line(panel,(47,59,74),(cx,cy),(nx,ny),max(1,cell//10))
        for rid,room in rooms.items():
            rx=content_x+(rid[0]-min_x)*cell; ry=origin_y+(rid[1]-min_y)*cell; rect=pygame.Rect(rx+2,ry+2,max(8,cell-4),max(8,cell-4)); current=tuple(rid)==tuple(dungeon.current)
            color=(255,202,102) if current else ((83,174,184) if getattr(room,"entered",False) else (48,58,72)); pygame.draw.rect(panel,color,rect,border_radius=4)
            if current: pygame.draw.rect(panel,(255,232,150),rect.inflate(4,4),1,border_radius=4)
            cx,cy=rect.center; ms=max(12,min(20,int(cell*.34))) if large else max(9,min(13,int(cell*.55)))
            if room.room_type=="boss":
                if getattr(room, "portal_room", False) and self.portal_frames:
                    img=pygame.transform.smoothscale(self.portal_frames[0],(ms,ms)); panel.blit(img,img.get_rect(center=(cx,cy)))
                else:
                    self.ui_atlas.draw_icon(panel, (cx, cy), size=max(14, ms + 4), kind="skull")
            elif room.room_type=="miniboss":
                self.ui_atlas.draw_icon(panel, (cx, cy), size=max(14, ms + 4), kind="white_skull")
        # La leyenda se eliminó: los iconos de cada sala son autoexplicativos.
        screen.blit(panel,(x,y))

    def draw_hud(self, screen, sim, fx, mouse):
        p = sim.player

        def panel(rect, fill=(15, 17, 25, 226), border=(72, 78, 94)):
            if self.ui_atlas.draw_panel(screen, rect, border=min(8, rect.width // 2, rect.height // 2)):
                return
            layer = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(layer, fill, layer.get_rect(), border_radius=7)
            pygame.draw.rect(layer, (*border, 235), layer.get_rect(), 1, border_radius=7)
            screen.blit(layer, rect.topleft)

        # Estado del jugador: las barras conservan el marco/icono del atlas y
        # los estados temporales aparecen en una columna inmediatamente a su izquierda.
        def status_bar(y, val, maximum, color, kind):
            maximum = max(1, maximum)
            ratio = max(0.0, min(1.0, val / maximum))
            bar_rect = pygame.Rect(50, y, 150, 28)
            if not self.ui_atlas.draw_bar(screen, bar_rect, ratio, kind=kind):
                pygame.draw.rect(screen, (7, 9, 14), bar_rect, border_radius=4)
                fill_w = int((bar_rect.width - 2) * ratio)
                if fill_w:
                    pygame.draw.rect(screen, color, (bar_rect.x + 1, bar_rect.y + 1, fill_w, bar_rect.height - 2), border_radius=3)
            self.text(screen, "%d/%d" % (math.ceil(val), maximum), (210, y + 14), (245, 246, 250), self.small, center=True)

        status_bar(10, p.hp, p.max_hp, (220, 65, 76), "health")
        status_bar(42, p.shield, p.max_shield, (75, 160, 240), "shield")
        status_bar(74, p.energy, p.max_energy, (232, 190, 75), "energy")

        active_statuses = []
        timers = getattr(p, "status_timers", {})
        for kind, icon in (
            ("heal", "heal"), ("shield", "shield"), ("burn", "fire"),
            ("poison", "poison"), ("electric", "energy"), ("freeze", "freeze")
        ):
            if float(timers.get(kind, 0.0)) > 0:
                active_statuses.append(icon)
        # Un escudo también se considera estado visual mientras tenga carga real.
        if p.shield > 0 and "shield" not in active_statuses:
            active_statuses.insert(0, "shield")
        for index, icon in enumerate(active_statuses[:5]):
            self.ui_atlas.draw_icon(screen, (25, 12 + index * 24), size=21, kind=icon)

        # HUD superior derecho: dungeon y monedas usan paneles independientes.
        dungeon_name = str(getattr(getattr(sim, "dungeon", None), "name", "Dungeon"))
        dungeon_panel = pygame.Rect(VIEW_W - 304, 8, 178, 44)
        coin_panel = pygame.Rect(VIEW_W - 118, 8, 110, 44)
        for hud_rect in (dungeon_panel, coin_panel):
            if not self.ui_atlas.draw_panel(screen, hud_rect, border=6):
                layer = pygame.Surface(hud_rect.size, pygame.SRCALPHA)
                pygame.draw.rect(layer, (10, 14, 24, 232), layer.get_rect(), border_radius=6)
                pygame.draw.rect(layer, (91, 111, 136, 225), layer.get_rect(), 1, border_radius=6)
                screen.blit(layer, hud_rect.topleft)

        # Dungeon: icono pequeno + nombre centrados en su propio panel.
        dungeon_icon_pos = (dungeon_panel.x + 18, dungeon_panel.centery)
        if not self.ui_atlas.draw_icon(screen, dungeon_icon_pos, size=17, kind="pin"):
            pygame.draw.circle(screen, (105, 230, 218), dungeon_icon_pos, 5, 1)
        dungeon_img = self.small.render(dungeon_name.upper(), True, (226, 233, 241))
        max_name_width = dungeon_panel.w - 39
        if dungeon_img.get_width() > max_name_width:
            dungeon_img = pygame.transform.smoothscale(dungeon_img, (max_name_width, dungeon_img.get_height()))
        name_x = dungeon_icon_pos[0] + 9 + dungeon_img.get_width() // 2
        screen.blit(dungeon_img, dungeon_img.get_rect(center=(name_x, dungeon_panel.centery)))

        # Monedas: icono pequeno y contador centrados juntos dentro de su panel.
        coin_frames = self.coin_frames
        coin_frame = None
        if coin_frames:
            coin_frame = coin_frames[int(pygame.time.get_ticks() * 0.008) % len(coin_frames)]
            coin_frame = self._fit_image(coin_frame, 14, cache_key="hud_coin")
        coin_text = self.small.render(str(int(p.coins)), True, (255, 225, 135))
        # El fotograma animado puede cambiar de ancho entre imágenes. Reservamos
        # siempre una caja fija para la moneda para que el contador no "salte".
        icon_box = pygame.Rect(coin_panel.centerx - 30, coin_panel.y + 12, 20, 20)
        if coin_frame:
            screen.blit(coin_frame, coin_frame.get_rect(center=icon_box.center))
        else:
            pygame.draw.circle(screen, (238, 190, 55), icon_box.center, 5)
            pygame.draw.circle(screen, (255, 232, 120), icon_box.center, 5, 1)
        # El número queda fijo respecto al panel: no depende del ancho de cada
        # fotograma animado y permanece centrado con el icono de la moneda.
        text_rect = coin_text.get_rect(center=(coin_panel.centerx + 20, coin_panel.centery))
        screen.blit(coin_text, text_rect)

        if getattr(sim, "statue_buffs", None):
            buff_labels={"defense":"DEF","melee":"MEL","ranged":"DIST","ability":"HAB","critical":"CRIT"}
            labels="  ".join(buff_labels.get(b.get("kind"),"BUFF") for b in sim.statue_buffs)
            self.text(screen, "ESTATUAS  " + labels, (hud_panel.right, hud_panel.bottom + 7), (125, 225, 205), self.small, right=True)
        self.draw_minimap(screen, sim, large=False)

        # Barra de jefe: una fase ocupa la barra completa. Al agotarse,
        # Boss repone la vida al máximo de la siguiente fase y cambia el color.
        bosses = [e for e in sim.enemies if getattr(e, "is_boss", False) and e.alive]
        if bosses:
            boss = bosses[0]
            bw, bh = 560, 46
            bx, by = (VIEW_W - bw) // 2, 8
            boss_rect = pygame.Rect(bx, by, bw, bh)
            phase = max(1, min(int(getattr(boss, "phase_count", 3)), int(getattr(boss, "phase", 1))))
            phase_colors = {
                1: (218, 82, 92),
                2: (174, 92, 224),
                3: (242, 166, 70),
            }
            phase_color = phase_colors.get(phase, (218, 82, 92))
            panel(boss_rect, fill=(11, 12, 20, 242), border=phase_color)
            title = str(boss.d.name).upper()
            self.text(screen, title[:36], (bx + 14, by + 5), (242, 237, 236), self.small)
            phase_label = "FASE %d/%d" % (phase, max(1, int(getattr(boss, "phase_count", 3))))
            phase_surface = self.small.render(phase_label, True, phase_color)
            screen.blit(phase_surface, phase_surface.get_rect(topright=(bx + bw - 14, by + 5)))

            track = pygame.Rect(bx + 12, by + 24, bw - 24, 13)
            pygame.draw.rect(screen, (5, 6, 11), track, border_radius=5)
            hp_ratio = max(0.0, min(1.0, boss.hp / max(1.0, boss.max_hp)))
            fill_w = int((track.width - 2) * hp_ratio)
            if fill_w > 0:
                fill = pygame.Rect(track.x + 1, track.y + 1, fill_w, track.height - 2)
                pygame.draw.rect(screen, phase_color, fill, border_radius=4)
                pygame.draw.line(screen, tuple(min(255, int(v * 1.22)) for v in phase_color),
                                 (fill.x + 2, fill.y + 1), (max(fill.x + 2, fill.right - 2), fill.y + 1), 1)
            pygame.draw.rect(screen, tuple(max(0, int(v * 0.55)) for v in phase_color), track, 1, border_radius=5)

        # Panel inferior: arma y munición a la izquierda; habilidades a la derecha.
        w = getattr(p, "weapon", None)
        weapon_rect = pygame.Rect(22, VIEW_H - 74, 218, 64)
        panel(weapon_rect, fill=(15, 17, 25, 218), border=(64, 70, 86))

        if w is None:
            self.text(screen, "PUÑOS", (62, VIEW_H - 61), (240, 241, 246), self.small)
            ammo_text, ammo_color = "SIN ARMA", (180, 190, 205)
            is_melee = True
            weapon_id = "fists"
            wdef = None
        else:
            wdef = getattr(w, "d", None)
            weapon_id = getattr(wdef, "id", "")
            hud_weapon = self._fit_image(self.weapon_scaled_images.get(weapon_id), 28)
            if hud_weapon is not None:
                screen.blit(hud_weapon, hud_weapon.get_rect(topleft=(62, VIEW_H - 61)))
                self.text(screen, getattr(wdef, "name", "ARMA"), (102, VIEW_H - 61), (240, 241, 246), self.small)
            else:
                self.text(screen, getattr(wdef, "name", "ARMA"), (62, VIEW_H - 61), (240, 241, 246), self.small)
            is_uses_weapon = getattr(wdef, "class", "") in ("melee", "magic")
            if weapon_id == "fists":
                ammo_text, ammo_color = "PUÑOS", (210, 218, 230)
            elif is_uses_weapon:
                ammo_text = "USOS  %d/%d" % (w.durability, w.max_durability)
                ammo_color = (255, 120, 120) if w.durability <= 3 else (210, 218, 230)
            elif w.reloading:
                ammo_text, ammo_color = "RECARGANDO", (240, 200, 90)
            else:
                reserve_text = "∞" if getattr(w, "unlimited_ammo", False) else str(w.reserve_magazines)
                ammo_text = "MUNICIÓN  %d/%s" % (w.ammo, reserve_text)
                ammo_color = (210, 218, 230) if getattr(w, "unlimited_ammo", False) else ((255, 120, 120) if w.ammo <= 2 and w.reserve_magazines <= 0 else (210, 218, 230))

        # Munición y estado de recarga quedan en una sola línea limpia.
        ammo_pos = (62, VIEW_H - 34)
        self.text(screen, ammo_text, ammo_pos, ammo_color, self.small)

        # Solo cuando el cargador está completamente vacío mostramos el icono de recarga.
        if w is not None and not is_uses_weapon and weapon_id != "fists" and not w.reloading and w.ammo <= 0 and w.reserve_magazines > 0:
            reload_center = (177, VIEW_H - 31)
            if not self.ui_atlas.draw_icon(screen, reload_center, size=22, kind="refresh"):
                pygame.draw.circle(screen, (240, 200, 90), reload_center, 9, 2)
                self.text(screen, "R", reload_center, (240, 200, 90), self.small, center=True)

        # Inventario manual de tres armas; el borde cálido marca el arma activa.
        inv_slot, inv_gap = 48, 8
        inv_total = inv_slot * 3 + inv_gap * 2
        inv_x = (VIEW_W - inv_total) // 2
        inv_y = VIEW_H - inv_slot - 8
        for slot_index in range(3):
            rect = pygame.Rect(inv_x + slot_index * (inv_slot + inv_gap), inv_y, inv_slot, inv_slot)
            occupied = slot_index < len(p.inventory)
            selected = getattr(p, "selected_slot", 0) == slot_index
            fill = (28, 26, 32, 225) if occupied else (12, 15, 22, 170)
            border = (255, 203, 105) if selected else ((86, 145, 168) if occupied else (54, 61, 75))
            if not self.ui_atlas.draw_slot(screen, rect, selected):
                panel(rect, fill=fill, border=border)
            if occupied:
                weapon_state = p.inventory[slot_index]
                weapon_def = getattr(weapon_state, "d", None)
                weapon_id = getattr(weapon_def, "id", "")
                sheet_key = getattr(weapon_def, "weapon_sprite_sheet", None)
                atlas_frames = self.weapon_variant_frames.get(sheet_key, [])
                icon = None
                if atlas_frames:
                    try:
                        atlas_index = int(getattr(weapon_def, "weapon_sprite_index", -1))
                    except (TypeError, ValueError):
                        atlas_index = -1
                    if 0 <= atlas_index < len(atlas_frames):
                        icon = self._fit_image(atlas_frames[atlas_index], 31)
                if icon is None:
                    icon = self._fit_image(self.weapon_scaled_images.get(weapon_id), 31)
                if icon is not None:
                    screen.blit(icon, icon.get_rect(center=(rect.centerx, rect.centery - 3)))
                self.text(screen, str(slot_index + 1), (rect.centerx, rect.bottom - 9), (255, 221, 150) if selected else (176, 191, 205), self.small, center=True)
            else:
                self.text(screen, str(slot_index + 1), rect.center, (83, 93, 110), self.small, center=True)

        # Habilidad y dash: iconos en paneles compactos con tecla encima.
        icon_size = 36
        panel_size = 50
        gap = 10
        dash_x = VIEW_W - 12 - panel_size
        ability_x = dash_x - gap - panel_size
        panel_y = VIEW_H - panel_size - 8
        def display_key(value):
            key = str(value or "?").lower()
            names = {"space": "ESPACIO", "escape": "ESC", "left shift": "L-SHIFT",
                     "right shift": "R-SHIFT", "left ctrl": "L-CTRL", "right ctrl": "R-CTRL",
                     "left alt": "L-ALT", "right alt": "R-ALT", "return": "ENTER"}
            return names.get(key, key.upper())
        ability_key = display_key(self.key_bindings.get("ability", "q"))
        dash_key = display_key(self.key_bindings.get("dash", "space"))
        self.text(screen, ability_key, (ability_x + panel_size // 2, panel_y - 15), (240, 241, 246), self.small, center=True)
        self.text(screen, dash_key, (dash_x + panel_size // 2, panel_y - 15), (240, 241, 246), self.small, center=True)

        def icon_panel(x, image, fallback_color, cooldown_ratio, atlas_kind=None):
            rect = pygame.Rect(x, panel_y, panel_size, panel_size)
            if not self.ui_atlas.draw_slot(screen, rect, False):
                panel(rect, fill=(15, 17, 25, 218), border=(82, 88, 104))
            center = rect.center
            if atlas_kind is not None and self.ui_atlas.available:
                self.ui_atlas.draw_icon_cooldown(screen, center, size=icon_size, kind=atlas_kind, ratio=cooldown_ratio)
                return
            if image is not None:
                scaled = self._fit_image(image, icon_size)
                if scaled is None:
                    return
                screen.blit(scaled, scaled.get_rect(center=center))
                if cooldown_ratio > 0:
                    mask = pygame.mask.from_surface(scaled, 8)
                    overlay = pygame.Surface(scaled.get_size(), pygame.SRCALPHA)
                    cover_h = int(scaled.get_height() * max(0.0, min(1.0, cooldown_ratio)))
                    pygame.draw.rect(overlay, (8, 10, 18, 145), (0, 0, scaled.get_width(), cover_h))
                    alpha = mask.to_surface(setcolor=(255,255,255,255), unsetcolor=(0,0,0,0))
                    overlay.blit(alpha, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
                    screen.blit(overlay, scaled.get_rect(center=center).topleft)
            else:
                pygame.draw.circle(screen, fallback_color, center, 11, 3)
        acd = max(0.0, min(1.0, p.ability_cd / max(0.01, p.c.ability["cooldown"])))
        cd = max(0.0, min(1.0, p.dash_cd / max(0.01, p.c.dash["cooldown"])))
        ability_kind=getattr(p.c,"ability",{}).get("kind","none")
        ability_icons={"shield":"shield","heal":"heal","burst":"target","haste":"energy","freeze":"freeze","drone":"target"}
        ability_kind_icon=ability_icons.get(ability_kind,"buff")
        ability_sprite=self.ability_shield_image if ability_kind=="shield" else None
        if ability_sprite is None and self.ui_atlas.available:
            icon_panel(ability_x, None, (105,205,170), acd, atlas_kind=ability_kind_icon)
        else:
            icon_panel(ability_x, ability_sprite, (105,205,170), acd)
        icon_panel(dash_x, self.dash_icon, (95,195,125), cd)

        # Interacciones contextuales: se muestran pequeñas y ancladas al objeto
        # real con el que el jugador puede interactuar, en lugar de un botón fijo
        # en el centro de la pantalla.
        def interaction_hint(world_x, world_y, action, y_offset=24):
            # Las interacciones usan exclusivamente los PNG de AshenVault_UI_Atlas.
            # El botón se mantiene pequeño para no competir con el combate.
            cam_x, cam_y = getattr(self, "cam", (0, 0))
            hx = int(world_x + cam_x)
            hy = int(world_y + cam_y + y_offset)
            button_w, button_h = 82, 19
            hx = max(button_w // 2 + 6, min(VIEW_W - button_w // 2 - 6, hx))
            hy = max(button_h // 2 + 6, min(VIEW_H - button_h // 2 - 6, hy))
            self.ui_atlas.draw_button(
                screen,
                pygame.Rect(hx - button_w // 2, hy - button_h // 2, button_w, button_h),
                action,
                selected=False,
            )

        # La prioridad visual coincide con Sim._try_interact(): portal, estatua,
        # cofre, tienda y finalmente objeto recogible.
        nearest_item = None
        nearest_item_dist = 48.0
        for item in getattr(sim, "items", []):
            ix, iy = getattr(item, "x", 99999), getattr(item, "y", 99999)
            dist = math.hypot(ix - p.x, iy - p.y)
            if dist < nearest_item_dist:
                nearest_item = item
                nearest_item_dist = dist

        shown_interaction = False
        if getattr(sim, "portal", False):
            px, py = sim.portal_position
            if math.hypot(px - p.x, py - p.y) < 78:
                interaction_hint(px, py, "Usar", 48)
                shown_interaction = True

        if not shown_interaction:
            active_statue = getattr(sim, "_active_statue", lambda: None)()
            if active_statue:
                _, _, sx, sy = active_statue
                interaction_hint(sx, sy, "Interactuar", 48)
                shown_interaction = True

        if not shown_interaction:
            chest = getattr(sim, "chest", None)
            if chest is not None and not chest.is_open and math.hypot(chest.x - p.x, chest.y - p.y) < 72:
                interaction_hint(chest.x, chest.y, "Interactuar", 38)
                shown_interaction = True

        if not shown_interaction and getattr(sim, "room", None) is not None and getattr(sim.room, "room_type", "") == "shop":
            nearby_offer = None
            nearby_offer_dist = 55.0
            for offer in getattr(sim, "shop_offers", []):
                if getattr(offer, "sold", False):
                    continue
                dist = math.hypot(offer.x - p.x, offer.y - p.y)
                if dist < nearby_offer_dist:
                    nearby_offer = offer
                    nearby_offer_dist = dist
            if nearby_offer is not None:
                interaction_hint(nearby_offer.x, nearby_offer.y, "Interactuar", 38)
                shown_interaction = True

        if not shown_interaction and nearest_item is not None:
            ix, iy = nearest_item.x, nearest_item.y
            interaction_hint(ix, iy, "Recoger", 30)


        # Mira discreta para no competir visualmente con enemigos y efectos.
        mx, my = mouse
        pygame.draw.circle(screen, (235, 240, 248), (mx, my), 7, 1)
        pygame.draw.line(screen, (235, 240, 248), (mx - 11, my), (mx - 5, my), 1)
        pygame.draw.line(screen, (235, 240, 248), (mx + 5, my), (mx + 11, my), 1)
        pygame.draw.line(screen, (235, 240, 248), (mx, my - 11), (mx, my - 5), 1)
        pygame.draw.line(screen, (235, 240, 248), (mx, my + 5), (mx, my + 11), 1)

        # Señal de daño en los bordes, sin tapar la acción central.
        if fx.flash > 0:
            ov = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
            a = int(115 * max(0.0, min(1.0, fx.flash / 0.35)))
            for i in range(3):
                pygame.draw.rect(ov, (255, 35, 45, max(0, a - i * 30)), (i * 7, i * 7, VIEW_W - i * 14, VIEW_H - i * 14), 7)
            screen.blit(ov, (0, 0))

