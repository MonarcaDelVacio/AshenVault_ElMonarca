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
        self.chest_images = {}
        self.chest_type_images = {}
        self.decoration_images = {}
        self.decoration_frames = {}
        self.npc_frames = {}
        self.special_effect_frames = {}
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
        # Coloca suelo1.png ... suelo11.png en assets/floors/ y wall2.png/cobbles2.png en assets/walls/.
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
        self.wall_top_images = {}
        self.wall_fill_images = {}
        # Sprites individuales para los ocho segmentos del perímetro de la sala.
        # La pared inferior es baja (32x32); los demás segmentos tienen 32x64.
        # Todas conservan una huella de colisión de una casilla.
        self.wall_piece_images = {}
        wall_piece_files = (
            "paredinferior.png", "paredsuperior.png",
            "paredlateralizquierda.png", "paredlateralderecha.png",
            "esquinainferiorderecha.png", "esquinainferiorizquierda.png",
            "esquinasuperiorderecha.png", "esquinasuperiorizquierda.png",
        )
        wall_dir = self.asset_root / "walls"
        for filename in wall_piece_files:
            path = wall_dir / filename
            if path.is_file():
                try:
                    image = pygame.image.load(str(path)).convert_alpha()
                    if image.get_width() > 0 and image.get_height() > 0:
                        piece_key = filename.removesuffix(".png")
                        target_size = (TILE, TILE) if piece_key == "paredinferior" else (TILE, TILE * 2)
                        self.wall_piece_images[piece_key] = pygame.transform.smoothscale(image, target_size)
                except (pygame.error, OSError, ValueError):
                    pass

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

        def make_atlas_background_transparent(surface, background_rgb, tolerance=4):
            """Quita el fondo gris uniforme de los atlas sin borrar sus texturas."""
            keyed = surface.copy()
            br, bg, bb = background_rgb
            for yy in range(keyed.get_height()):
                for xx in range(keyed.get_width()):
                    rr, gg, bl, aa = keyed.get_at((xx, yy))
                    if (abs(rr - br) <= tolerance and abs(gg - bg) <= tolerance
                            and abs(bl - bb) <= tolerance):
                        keyed.set_at((xx, yy), (rr, gg, bl, 0))
            return keyed

        wall_atlas_path = wall_dir / "wall2.png"
        if wall_atlas_path.is_file():
            try:
                atlas = pygame.image.load(str(wall_atlas_path)).convert_alpha()
                # wall2.png usa gris claro (RGB 184,184,184) como fondo vacío.
                atlas = make_atlas_background_transparent(atlas, (184, 184, 184), 5)
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
                atlas = make_atlas_background_transparent(atlas, (166, 166, 166), 5)
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
        for name, filename in {
            "merchant_idle":"merchant_idle.png", "merchant_near":"merchant_near.png",
        }.items():
            path = npc_dir / filename
            if path.is_file():
                frames = self._load_sheet_frames(path)
                if frames: self.npc_frames[name] = frames

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
            "ogro": {"idle":"Ogro/ogro_ataquedesendente.png","walk":"Ogro/ogro_ataquedesendente.png","attack":"Ogro/ogro_ataquedesendente.png","attack_heavy":"Ogro/ogro_ataquedesendentepesado.png"},
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

    @staticmethod
    def _alpha_runs(values):
        runs=[]; start=None
        for i, active in enumerate(values):
            if active and start is None: start=i
            elif not active and start is not None:
                runs.append((start,i-1)); start=None
        if start is not None: runs.append((start,len(values)-1))
        return runs

    def _load_sheet_frames(self, path):
        try:
            image = pygame.image.load(str(path)).convert_alpha()
            # Las fuentes son tiras de 3 frames muy próximos entre sí.
            # La detección por alpha puede unirlos en un solo componente, por lo
            # que aquí usamos las tres celdas horizontales explícitas.
            if path.name in ("fountain_active.png", "fountain_inactive.png"):
                if image.get_width() % 3 != 0:
                    return []
                frame_w = image.get_width() // 3
                return [
                    image.subsurface(pygame.Rect(i * frame_w, 0, frame_w, image.get_height())).copy()
                    for i in range(3)
                ]

            # El ataque del Minotauro Gigante es una cuadrícula 3x3 real.
            # Sus celdas tienen fondo/transparencia suficiente para que la detección
            # automática pueda confundir las 9 poses con una sola imagen o recortarlas
            # de forma irregular. Para este asset usamos siempre las nueve celdas.
            if path.name == "MinotauroGigante_ataque.png" and image.get_width() % 3 == 0 and image.get_height() % 3 == 0:
                cell_w = image.get_width() // 3
                cell_h = image.get_height() // 3
                return [
                    image.subsurface(pygame.Rect(col * cell_w, row * cell_h, cell_w, cell_h)).copy()
                    for row in range(3) for col in range(3)
                ]
            alpha = pygame.surfarray.array_alpha(image)
            cols = self._alpha_runs(alpha.max(axis=1) > 8)
            rows = self._alpha_runs(alpha.max(axis=0) > 8)
            frames=[]
            for y0,y1 in rows:
                for x0,x1 in cols:
                    rect=pygame.Rect(x0,y0,x1-x0+1,y1-y0+1)
                    if rect.width < 2 or rect.height < 2: continue
                    frames.append(image.subsurface(rect).copy())
            return frames or [image]
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
        # Supplied enemy/boss art is intentionally much larger than the old
        # placeholder bodies. The smallest supplied actor is at least as tall
        # as the 48x52 player sprite, while larger radius values naturally grow.
        base_target=max(56.0, float(e.radius)*4.2)
        target=base_target*float(getattr(e.d,"sprite_scale",1.0)) / 4.0
        if getattr(e,"is_boss",False):
            target=max(128.0, target)
        elif getattr(e,"is_miniboss",False):
            target=max(82.0, target)
        w,h=frame.get_size(); scale=target/max(1,w,h)
        frame=pygame.transform.smoothscale(frame,(max(1,int(w*scale)),max(1,int(h*scale))))
        if math.cos(e.facing)<0:
            frame=pygame.transform.flip(frame,True,False)
        if e.flash>0:
            frame=frame.copy()
            mask=pygame.mask.from_surface(frame,threshold=8)
            flash=mask.to_surface(setcolor=(255,255,255,175),unsetcolor=(0,0,0,0))
            frame.blit(flash,(0,0),special_flags=pygame.BLEND_RGBA_ADD)
        elif light_level < 0.98:
            frame=frame.copy(); frame.fill((max(1,int(255*light_level)),)*3+(255,),special_flags=pygame.BLEND_RGBA_MULT)
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
        w,h=frame.get_size(); scale=float(size)/max(1,w,h)
        frame=pygame.transform.smoothscale(frame,(max(1,int(w*scale)),max(1,int(h*scale))))
        if math.cos(facing)<0: frame=pygame.transform.flip(frame,True,False)
        frame=frame.copy(); frame.set_alpha(max(0,int(255*(1-elapsed/max_life))))
        screen.blit(frame,frame.get_rect(center=(int(x+ox),int(y+oy))))

    def _draw_projectile_sheet(self, screen, frames, pr, ox, oy, size):
        if not frames: return
        idx=int(pr.age*len(frames)/0.42)%len(frames)
        frame=frames[idx]
        w,h=frame.get_size(); scale=float(size)/max(1,w,h)
        frame=pygame.transform.smoothscale(frame,(max(1,int(w*scale)),max(1,int(h*scale))))
        angle=math.degrees(math.atan2(pr.vy,pr.vx))
        frame=pygame.transform.rotate(frame,-angle)
        screen.blit(frame,frame.get_rect(center=(int(pr.x+ox),int(pr.y+oy))))

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

    @staticmethod
    def _fit_effect_frame(image, size):
        if image is None:
            return None
        w, h = image.get_size()
        scale = min(float(size) / max(1, w, h), 1.0 if size <= max(w, h) else float(size) / max(1, w, h))
        # Los efectos pueden necesitar crecer respecto al PNG original; nunca deformamos.
        scale = float(size) / max(1, w, h)
        return pygame.transform.smoothscale(image, (max(1, int(w * scale)), max(1, int(h * scale))))

    def _draw_combat_sprite_animation(self, screen, frames, elapsed, x, y, size, angle=None, alpha=255, loop=False, duration=0.24):
        if not frames:
            return
        frame_index = int(max(0.0, elapsed) * len(frames) / max(0.001, duration))
        if loop:
            frame_index %= len(frames)
        else:
            frame_index = min(len(frames) - 1, frame_index)
        frame = frames[frame_index]
        frame = self._fit_effect_frame(frame, size)
        if frame is None:
            return
        if angle is not None:
            frame = pygame.transform.rotate(frame, -math.degrees(angle))
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

    @staticmethod
    def _fit_image(image, max_dimension):
        if image is None:
            return None
        bbox=image.get_bounding_rect(min_alpha=8)
        if bbox.width and bbox.height:
            image=image.subsurface(bbox).copy()
        w,h=image.get_size()
        scale=min(max_dimension/max(w,h),1.0)
        size=(max(1,int(w*scale)),max(1,int(h*scale)))
        return pygame.transform.smoothscale(image,size)

    @staticmethod
    def _melee_grip_anchor(weapon_def):
        path=str(getattr(weapon_def,"weapon_sprite","")).lower()
        if "guadana" in path: return (0.20,0.82)
        if "martillo" in path: return (0.19,0.78)
        if "hacha" in path: return (0.18,0.78)
        if "lanza" in path: return (0.17,0.78)
        if "espada" in path: return (0.18,0.79)
        return (0.18,0.78)

    def _rotate_weapon_from_grip(self, image, weapon_def, rotation):
        image=self._fit_image(image,self._weapon_max_dimension(getattr(weapon_def,"class","pistol")))
        if image is None: return None
        gx,gy=self._melee_grip_anchor(weapon_def)
        grip=(image.get_width()*gx,image.get_height()*gy)
        pad=max(image.get_width(),image.get_height())+12
        canvas=pygame.Surface((image.get_width()+pad*2,image.get_height()+pad*2),pygame.SRCALPHA)
        canvas.blit(image,(pad+image.get_width()/2-grip[0],pad+image.get_height()/2-grip[1]))
        rotated=pygame.transform.rotozoom(canvas,rotation,1.0)
        bbox=rotated.get_bounding_rect(min_alpha=8)
        return rotated.subsurface(bbox).copy() if bbox.width and bbox.height else rotated

    @staticmethod
    def _weapon_max_dimension(weapon_class):
        return {
            "pistol": 29, "smg": 32, "shotgun": 34, "rifle": 38,
            "precision": 42, "machinegun": 39, "launcher": 37,
            "magic": 35, "special": 38, "experimental": 34, "melee": 37,
        }.get(weapon_class, 32)

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

    @staticmethod
    def _wall_piece_key(arena, tx, ty):
        """Identifica bordes y esquinas exteriores a partir de dónde está el suelo."""
        def is_floor(x, y):
            return 0 <= x < arena.cols and 0 <= y < arena.rows and arena.grid[y][x] == FLOOR

        north, east = is_floor(tx, ty - 1), is_floor(tx + 1, ty)
        south, west = is_floor(tx, ty + 1), is_floor(tx - 1, ty)
        nw, ne = is_floor(tx - 1, ty - 1), is_floor(tx + 1, ty - 1)
        sw, se = is_floor(tx - 1, ty + 1), is_floor(tx + 1, ty + 1)

        # Las esquinas se detectan por el suelo diagonal, aunque las casillas
        # cardinales contiguas sean también pared.
        if not (north or east or south or west):
            if se:
                return "esquinasuperiorizquierda"
            if sw:
                return "esquinasuperiorderecha"
            if ne:
                return "esquinainferiorizquierda"
            if nw:
                return "esquinainferiorderecha"
        if south:
            return "paredsuperior"
        if north:
            return "paredinferior"
        if east:
            return "paredlateralizquierda"
        if west:
            return "paredlateralderecha"
        return None

    def _background(self, arena):
        key = (arena.biome, arena.room_id, arena.cols, arena.rows, str(arena.grid), getattr(arena, "floor_surface", None))
        if self._bg_key == key:
            return self._bg_cache
        b = self.data.biomes[arena.biome]
        surf = pygame.Surface((arena.width, arena.height + 10), pygame.SRCALPHA)
        # Cada sala tiene una única superficie de suelo. La textura elegida se
        # repite dentro de la sala, pero jamás se mezclan dos superficies.
        floor_name = getattr(arena, "floor_surface", None)
        floor_img = self.named_floor_images.get(floor_name) if floor_name else None
        if floor_img is None:
            fallback_by_biome = {
                "ruins": 10, "forest": 5, "dungeon": 9,
                "laboratory": 2, "volcanic": 7, "final": 11,
            }
            floor_img = self.floor_images.get(fallback_by_biome.get(arena.biome, 1))
        # Las texturas de piedra cambian con el bioma cuando están disponibles.
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
                    piece_key = self._wall_piece_key(arena, tx, ty)
                    piece = self.wall_piece_images.get(piece_key) if piece_key else None
                    if piece is None:
                        if wall_fill is not None:
                            surf.blit(wall_fill, r)
                        else:
                            pygame.draw.rect(surf, b["wall"], r)
                        # Compatibilidad con los atlas antiguos cuando no hay sprite individual.
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
        # Dibuja las paredes altas en una segunda pasada para que el suelo no tape
        # la mitad que sobresale de la casilla. Las paredes superiores crecen hacia
        # abajo dentro de la sala; las inferiores y laterales se apoyan por la base.
        for ty, row in enumerate(arena.grid):
            for tx, tile in enumerate(row):
                if tile != WALL:
                    continue
                piece_key = self._wall_piece_key(arena, tx, ty)
                piece = self.wall_piece_images.get(piece_key) if piece_key else None
                if piece is None:
                    continue
                # Todas las piezas altas se anclan por la base a su casilla sólida.
                # Así, la mitad superior es solo altura visual y la colisión queda
                # en el bloque inferior, donde el personaje no debe atravesar el muro.
                dest = (tx * TILE, (ty + 1) * TILE - piece.get_height())
                surf.blit(piece, dest)

        # Las columnas interiores usan columna.png. Se dibujan en el fondo y se
        # vuelven a dibujar por delante de los actores que estén detrás de ellas.
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
        """Oculta a los actores detrás de las paredes y columnas altas.

        La posición lógica/collider sigue siendo una sola casilla; solo el arte
        sobresale verticalmente. La pared inferior conserva su altura de un tile.
        """
        player_y = sim.player.y
        for ty, row in enumerate(arena.grid):
            for tx, tile in enumerate(row):
                if tile in (PILLAR, TORCH_PILLAR):
                    pillar_image = self.torch_column_image if tile == TORCH_PILLAR else self.column_image
                    if pillar_image is not None:
                        base_y = (ty + 1) * TILE
                        if player_y < base_y:
                            rect = pillar_image.get_rect(
                                midbottom=(int(tx * TILE + TILE // 2 + ox), int(base_y + oy)))
                            screen.blit(pillar_image, rect)
                elif tile == WALL:
                    piece_key = self._wall_piece_key(arena, tx, ty)
                    piece = self.wall_piece_images.get(piece_key) if piece_key else None
                    if piece is None:
                        continue
                    dest_y = (ty + 1) * TILE - piece.get_height()
                    base_y = dest_y + piece.get_height()
                    if player_y < base_y:
                        screen.blit(piece, (int(tx * TILE + ox), int(dest_y + oy)))

    def _draw_dynamic_shadows(self, screen, arena, sim, ox, oy):
        """Sombras suaves de pilares y objetos, proyectadas desde las luces activas.

        Las paredes de borde (WALL) delimitan la sala y no proyectan sombras. Solo
        los pilares interiores y los objetos elevados generan sombras sobre el suelo.
        """
        px, py = sim.player.x, sim.player.y
        decor_lights = self._room_decor_lights(arena)
        sources = [(px, py, 190, 1.0)]
        sources.extend((light["x"], light["y"], light["radius"], 0.42) for light in decor_lights)

        for source_x, source_y, source_radius, source_strength in sources:
            layer = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)

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
                rect = pygame.Rect(int(sx - width / 2), int(sy - height / 2), width, height)
                corners = [(rect.left, rect.top), (rect.right, rect.top),
                           (rect.right, rect.bottom), (rect.left, rect.bottom)]
                # La sombra se proyecta en dirección opuesta a la fuente de luz.
                far_edge = sorted(corners, key=lambda point: point[0] * dx + point[1] * dy, reverse=True)[:2]
                ex, ey = dx * length, dy * length
                a, b = far_edge
                shadow_alpha = max(12, min(100, int(alpha * source_strength)))
                pygame.draw.polygon(layer, (0, 0, 0, shadow_alpha),
                                    [a, b, (int(b[0] + ex), int(b[1] + ey)),
                                     (int(a[0] + ex), int(a[1] + ey))])
                base = pygame.Rect(0, 0, max(18, int(width * 1.05)), max(8, int(height * 0.48)))
                base.center = (int(sx + dx * 7), int(sy + dy * 10))
                pygame.draw.ellipse(layer, (0, 0, 0, min(110, shadow_alpha + 18)), base)

            # Solo los pilares interiores proyectan sombras arquitectónicas.
            for ty, row in enumerate(arena.grid):
                for tx, tile in enumerate(row):
                    if tile not in (PILLAR, TORCH_PILLAR):
                        continue
                    wx, wy = tx * TILE + TILE / 2, ty * TILE + TILE / 2
                    sx, sy = wx + ox, wy + oy
                    if sx < -TILE or sy < -TILE or sx > VIEW_W + TILE or sy > VIEW_H + TILE:
                        continue
                    cast_shadow(wx, wy, TILE - 3, TILE - 3, 58, 72)

            chest = getattr(sim, "chest", None)
            if chest is not None:
                cast_shadow(chest.x, chest.y, 42, 30, 28, 58 if not chest.is_open else 32)
            for prop in getattr(sim, "props", []):
                if not prop.get("broken"):
                    size = 30 if prop.get("kind") == "crate" else 42
                    cast_shadow(prop["x"], prop["y"], size, size, 30, 56)

            # Los enemigos proyectan sombras sobre el suelo desde las fuentes cercanas.
            for enemy in getattr(sim, "enemies", []):
                if enemy.alive and getattr(enemy, "spawn_delay", 0) <= 0:
                    cast_shadow(enemy.x, enemy.y, max(14, enemy.radius * 1.6),
                                max(12, enemy.radius), 18, 42)

            screen.blit(layer, (0, 0))

    def _room_decor_lights(self, arena):
        """Luces de antorchas ancladas a pilares sólidos y hogueras decorativas."""
        key = (getattr(arena, "room_id", None), arena.cols, arena.rows, arena.biome, str(arena.grid))
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
        """Estimación barata de luz directa con oclusión por muros y pilares."""
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
        return max(0.28, min(1.0, level))

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
        pygame.draw.ellipse(screen,(12,14,20,120),(x-13,y+8,x+13-(x-13),9))
        frames=self.enemy_sprites.get("drone",{})
        frames=frames.get("idle") or frames.get("run") or frames.get("walk") or next(iter(frames.values()),[])
        if frames:
            frame=frames[int(t*8.0)%len(frames)]
            frame=self._fit_image(frame,42)
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
            enemy_rotated = pygame.transform.rotate(enemy_weapon, rotation)
            enemy_pos = (int(x + math.cos(e.facing) * (e.radius + 3)), int(y + math.sin(e.facing) * (e.radius + 3)))
            screen.blit(enemy_rotated, enemy_rotated.get_rect(center=enemy_pos))
        shield_ratio = getattr(e, "shield_integrity", 0.0) / max(1.0, getattr(e.d, "shield_durability", 48.0))
        if (getattr(e.d, "shielded", False) and shield_ratio > 0) or getattr(e, "shield_active", False):
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
        if e.hp < e.max_hp:
            w = 24
            pygame.draw.rect(screen, (40, 0, 0), (x - w // 2, y - e.radius - 9, w, 4))
            pygame.draw.rect(screen, (230, 60, 60), (x - w // 2, y - e.radius - 9, int(w * max(0, e.hp) / e.max_hp), 4))

    def _draw_player_actor(self, screen, p, ox, oy, t):
        x, y = int(p.x + ox), int(p.y + oy)
        shield_ability_active = getattr(p, "ability_shield_fx", 0.0) > 0
        pygame.draw.ellipse(screen, (0, 0, 0), (x - p.radius + 2, y + p.radius - 3, p.radius * 2, max(4, p.radius // 2)))
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
            sprite = character_frames[frame_index]
            if p.facing_x < 0:
                sprite = pygame.transform.flip(sprite, True, False)
            bbox=sprite.get_bounding_rect(min_alpha=8)
            if bbox.width and bbox.height:
                sprite=sprite.subsurface(bbox).copy()
            flash_kind=None
            flash_alpha=0
            if getattr(p,"hurt_flash",0.0)>0:
                flash_kind=(255,55,55); flash_alpha=int(185*min(1.0,p.hurt_flash/.25))
            elif getattr(p,"heal_flash",0.0)>0:
                flash_kind=(80,255,105); flash_alpha=int(175*min(1.0,p.heal_flash/.26))
            elif getattr(p,"energy_flash",0.0)>0:
                flash_kind=(255,225,55); flash_alpha=int(175*min(1.0,p.energy_flash/.26))
            if flash_kind:
                # BLEND_RGBA_ADD sobre una superficie completa puede levantar el
                # alpha de píxeles transparentes. La máscara de alpha garantiza que
                # el parpadeo quede estrictamente dentro del contorno del PNG.
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
            shield_overlay = pygame.transform.smoothscale(self.ability_shield_image, (52, 52))
            pulse = 0.5 + 0.5 * math.sin(t * 18.0)
            shield_overlay.set_alpha(int(95 + 85 * pulse))
            screen.blit(shield_overlay, shield_overlay.get_rect(center=(x, y)))
        # Arma equipada: sprite individual rotado hacia el cursor, siempre sobre el personaje.
        kick = max(0.0, 1 - p.since_shot * 12) * 3
        ax, ay = math.cos(p.aim), math.sin(p.aim)
        weapon_def = p.weapon.d
        weapon_id = getattr(weapon_def, "id", "")
        weapon_image = self.weapon_scaled_images.get(weapon_id)
        if weapon_image is not None:
            weapon_class = getattr(weapon_def, "class", "")
            sprite_path = str(getattr(weapon_def, "weapon_sprite", "")).lower()
            is_melee_asset = weapon_class == "melee" or "/melee/" in sprite_path
            base_angle = 35.0 if is_melee_asset and "lanza" in sprite_path else (-35.0 if is_melee_asset else {"magic": -32, "special": -25}.get(weapon_class, 0))
            if math.cos(p.aim) < 0:
                weapon_image = pygame.transform.flip(weapon_image, True, False)
                rotation = base_angle + 180 - math.degrees(p.aim)
            else:
                rotation = base_angle - math.degrees(p.aim)
            hand_offset = (p.radius + 1 - kick) if is_melee_asset else (p.radius - 1 - kick)
            rotated = self._rotate_weapon_from_grip(weapon_image, weapon_def, rotation) if is_melee_asset else pygame.transform.rotate(weapon_image, rotation)
            center = (int(x + ax * hand_offset), int(y + ay * hand_offset))
            screen.blit(rotated, rotated.get_rect(center=center))
        else:
            x0, y0 = x + ax * (p.radius - 2 - kick), y + ay * (p.radius - 2 - kick)
            x1, y1 = x + ax * (p.radius + 12 - kick), y + ay * (p.radius + 12 - kick)
            pygame.draw.line(screen, (30, 30, 36), (x0, y0), (x1, y1), 6)
            pygame.draw.line(screen, weapon_def.color, (x0, y0), (x1, y1), 3)
        charge_max = float(getattr(weapon_def, "charge_max", 0) or 0)
        charge_time = float(getattr(p.weapon, "charge_time", 0) or 0)
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
            draw_img = pygame.transform.smoothscale(img, (44, 44))
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

    def decoration_overlap(self, deco, x, y, radius):
        """Prueba la colisión real contra los píxeles opacos del modelo."""
        kind=str(deco.get("kind",""))
        variant=int(deco.get("variant",0))
        key=(kind,variant)
        cached=self._decoration_mask_cache.get(key)
        if cached is None:
            image=self.decoration_images.get(kind)
            frames=self.decoration_frames.get(kind)
            if frames:
                image=frames[0]
            if image is None and kind in ("bush","rock"):
                image=self.decoration_images.get(f"{kind}_{variant%6+1}")
            if image is None:
                return False
            max_size={
                "fountain_active":104,"fountain_inactive":104,"fountain_small":68,"well_empty":104,
                "bench_large":92,"bench_small":66,"barrel_large":62,"signpost":70,"crate_stack":76,
                "crate_pair":68,"table":72,"counter":84,"wood_chest_decor":68,
                "statue_goddess":640,"statue_archer":640,"statue_assassin":640,
                "statue_knight":640,"statue_mage":640,"bush":56,"rock":58,
            }.get(kind,56)
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
        variant=int(deco.get("variant",0))
        key=(kind,variant)
        if key in self._decoration_collider_cache:
            rx,ry,ox,oy=self._decoration_collider_cache[key]
        else:
            image=self.decoration_images.get(kind)
            if image is None and kind in ("bush","rock"):
                image=self.decoration_images.get(f"{kind}_{variant%6+1}")
            if image is None:
                return None
            bbox=image.get_bounding_rect(min_alpha=8)
            if not bbox.width or not bbox.height:
                return None
            max_size={
                "fountain_active":104,"fountain_inactive":104,"fountain_small":68,"well_empty":104,
                "bench_large":92,"bench_small":66,"barrel_large":62,"signpost":70,"crate_stack":76,
                "crate_pair":68,"table":72,"counter":84,"wood_chest_decor":68,
                "statue_goddess":640,"statue_archer":640,"statue_assassin":640,"statue_knight":640,"statue_mage":640,
                "bush":56,"rock":58,
            }.get(kind,56)
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
        image=self.decoration_images.get(kind)
        if image is None and kind in ("bush","rock"):
            image=self.decoration_images.get(f"{kind}_{int(deco.get("variant",0))%6+1}")
        if image is None:
            return
        base_y=float(deco.get("y",0))*TILE+TILE
        x=float(deco.get("x",0))*TILE+TILE/2+ox
        y=base_y+oy
        max_size={
            "fountain_active":104,"fountain_inactive":104,"fountain_small":68,
            "well_empty":104,"bench_large":92,"bench_small":66,"barrel_large":62,
            "signpost":70,"crate_stack":76,"crate_pair":68,"table":72,"counter":84,
            "wood_chest_decor":68,
            "statue_goddess":510,"statue_archer":510,"statue_assassin":510,
            "statue_knight":510,"statue_mage":510,
            "bush":56,"rock":58,
        }.get(kind,56)
        frames = self.decoration_frames.get(kind)
        if frames:
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
        ambient = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        ambient.fill((6, 9, 20, 66))
        screen.blit(ambient, (0, 0))

        # Iluminación dinámica 2D económica: luces radiales aditivas se calculan en
        # coordenadas de pantalla y se dibujan detrás de los actores y objetos.
        decor_lights = self._room_decor_lights(arena)
        lights = pygame.Surface((VIEW_W, VIEW_H))
        lights.fill((0, 0, 0))
        player_light = pygame.Surface((VIEW_W, VIEW_H))
        player_light.fill((0, 0, 0))
        def add_light(target, world_x, world_y, radius, color, strength=1.0):
            lx, ly = int(world_x + ox), int(world_y + oy)
            if lx < -radius or ly < -radius or lx > VIEW_W + radius or ly > VIEW_H + radius:
                return
            # Gradiente radial con muchos anillos de baja intensidad y caída suave.
            for i in range(24, 0, -1):
                ring = i / 24.0
                rr = max(1, int(radius * ring))
                falloff = (1.0 - ring) ** 1.55
                factor = (0.008 + falloff * 0.205) * strength
                tint = tuple(min(255, int(channel * factor)) for channel in color)
                pygame.draw.circle(target, tint, (lx, ly), rr)
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
            merchant_idle=self.npc_frames.get("merchant_idle", [])
            merchant_near=self.npc_frames.get("merchant_near", [])
            near = math.hypot(p.x-arena.width/2,p.y-arena.height/2)<155
            actors.append((arena.height/2-48, "merchant", {
                "idle": merchant_idle,
                "near": merchant_near,
                "near_active": near,
                "intro_start": self._merchant_intro_start,
            }))
            # La animación de entrada (capa -> se la quita) solo ocurre una vez por sala.
        actors.sort(key=lambda item:item[0])
        for actor_y,kind,obj in actors:
            if kind=="player": self._draw_player_actor(screen,obj,ox,oy,t)
            elif kind=="enemy": self._draw_enemy_actor(screen,obj,arena,sim,ox,oy,decor_lights,t)
            elif kind=="drone": self._draw_drone_actor(screen,obj,ox,oy,t)
            elif kind=="merchant":
                intro=obj["idle"]; elapsed=max(0.0,t-float(obj.get("intro_start",t)))
                if intro and elapsed < 0.72:
                    # Los cuatro primeros frames contienen la capa; los siguientes
                    # muestran cómo el comerciante queda listo para atender.
                    idx=min(len(intro)-1,int(elapsed*7.0))
                    frame=intro[idx]
                else:
                    frames=obj["near"] if obj.get("near_active") and obj.get("near") else obj["idle"]
                    if frames:
                        start=4 if len(frames)>4 else 0
                        frame=frames[start + (int(t*7.0) % max(1,len(frames)-start))]
                    else:
                        frame=None
                if frame is not None:
                    frame=self._fit_image(frame,70)
                    screen.blit(frame,frame.get_rect(midbottom=(int(arena.width/2+ox),int(arena.height/2-48+oy))))
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
        # Puertas arquitectónicas: los umbrales bloqueados tienen una reja visible;
        # al despejar la sala desaparece la barrera y aparece una flecha blanca grande.
        # Las columnas de los laterales forman el marco usando los mismos sprites.
        for d in arena.doors.values():
            x,y=d.x*TILE+int(ox),d.y*TILE+int(oy)
            cx,cy=x+TILE//2,y+TILE//2
            horizontal=d.side in ("N","S")
            frame=self.column_image
            if frame is not None and horizontal:
                # En accesos norte/sur, los postes se apoyan en el suelo interior:
                # no flotan en el centro del tile de puerta.
                narrow=pygame.transform.smoothscale(frame,(8,44))
                base_y = y + TILE * 2 if d.side == "N" else y
                for frame_x in (x,x+TILE-8):
                    screen.blit(narrow,narrow.get_rect(midbottom=(frame_x+4,base_y)))
            elif frame is not None:
                # Para los accesos laterales se reutiliza la piedra como dintel,
                # con la pieza girada y anclada al lado interior del umbral.
                lintel=pygame.transform.smoothscale(pygame.transform.rotate(frame,90),(32,8))
                left = x if d.side == "W" else x
                for fy in (y,y+TILE-8):
                    screen.blit(lintel,(left,fy))
            if not d.open:
                pygame.draw.rect(screen,(24,22,29),(x+3,y+3,TILE-6,TILE-6),border_radius=3)
                pygame.draw.rect(screen,(130,55,58),(x+3,y+3,TILE-6,TILE-6),2,border_radius=3)
                if horizontal:
                    for bx in (x+8,x+16,x+24):
                        pygame.draw.line(screen,(150,135,125),(bx,y+5),(bx,y+TILE-5),3)
                    pygame.draw.line(screen,(190,80,70),(x+4,cy),(x+TILE-4,cy),3)
                else:
                    for by in (y+8,y+16,y+24):
                        pygame.draw.line(screen,(150,135,125),(x+5,by),(x+TILE-5,by),3)
                    pygame.draw.line(screen,(190,80,70),(cx,y+4),(cx,y+TILE-4),3)
            else:
                # Flecha blanca con contorno oscuro, orientada hacia la sala siguiente.
                if d.side=="N": points=[(cx,cy-15),(cx-12,cy+1),(cx-5,cy+1),(cx-5,cy+11),(cx+5,cy+11),(cx+5,cy+1),(cx+12,cy+1)]
                elif d.side=="S": points=[(cx,cy+15),(cx-12,cy-1),(cx-5,cy-1),(cx-5,cy-11),(cx+5,cy-11),(cx+5,cy-1),(cx+12,cy-1)]
                elif d.side=="W": points=[(cx-15,cy),(cx+1,cy-12),(cx+1,cy-5),(cx+11,cy-5),(cx+11,cy+5),(cx+1,cy+5),(cx+1,cy+12)]
                else: points=[(cx+15,cy),(cx-1,cy-12),(cx-1,cy-5),(cx-11,cy-5),(cx-11,cy+5),(cx-1,cy+5),(cx-1,cy+12)]
                pygame.draw.polygon(screen,(22,24,30),points)
                inner=[]
                for px,py in points:
                    inner.append((cx+(px-cx)*0.82,cy+(py-cy)*0.82))
                pygame.draw.polygon(screen,(250,250,255),inner)
        # Cofres y props ya fueron dibujados dentro de la pasada de profundidad
        # compartida con actores y decoraciones. Aquí solo queda el prompt del cofre,
        # que es UI y por eso debe permanecer por encima de todo.
        chest = getattr(sim, "chest", None)
        if chest is not None and not chest.is_open and math.hypot(chest.x - sim.player.x, chest.y - sim.player.y) < 72:
            self.text(screen, "E  ABRIR COFRE", (chest.x + ox, chest.y + 30), (255, 235, 150), self.small, True)

        for h in getattr(sim,"hazards",[]):
            alpha=max(30,min(100,int(100*h["life"]/5.0)))
            layer=pygame.Surface((int(h["radius"]*2),int(h["radius"]*2)),pygame.SRCALPHA)
            pygame.draw.circle(layer,(*h["color"],alpha),(layer.get_width()//2,layer.get_height()//2),int(h["radius"]))
            pygame.draw.circle(layer,(*h["color"],min(170,alpha+50)),(layer.get_width()//2,layer.get_height()//2),int(h["radius"]),3)
            screen.blit(layer,(int(h["x"]+ox-h["radius"]),int(h["y"]+oy-h["radius"])))
        for wave in getattr(sim,"wave_attacks",[]):
            pygame.draw.circle(screen,wave.get("color",(255,120,50)),(int(wave["x"]+ox),int(wave["y"]+oy)),int(wave["radius"]),4)

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
            self.text(screen, str(offer.name)[:12], (px, py + 37), col, self.small, center=True)

        # Rayos láser persistentes: finos al inicio, crecen entre 1 y 3 s,
        # siguen el apuntado del propietario y terminan en la primera colisión.
        for laser in getattr(sim, "lasers", []):
            owner=laser.get("owner"); angle=float(laser.get("angle",0.0))
            if owner is None: continue
            length,point,_=sim._laser_hit_target(laser,0.0)
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
                icon = self.weapon_scaled_images.get(getattr(it, "weapon_id", ""))
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
            # Los proyectiles de fuego usan la animacion ignea generica y siempre
            # se orientan siguiendo su trayectoria, tanto para jugador como enemigos.
            if pr.dtype == "fire" and self.ignite_projectile_frames:
                angle = math.atan2(pr.vy, pr.vx) if not pr.stuck else pr.stuck_angle
                self._draw_combat_sprite_animation(
                    screen, self.ignite_projectile_frames, pr.age,
                    pr.x + ox, pr.y + oy, max(18.0, pr.radius * 5.5 * getattr(pr, "visual_scale", 1.0)),
                    angle=angle,
                    alpha=max(0, int(255 * min(1.0, pr.life / 0.08))) if pr.stuck else 255,
                    loop=True, duration=0.30
                )
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
                    correction = 45.0 if "assets/weapons/melee/lanza" in sprite_path else 0.0
                    scaled = pygame.transform.rotate(scaled, correction - angle)
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
            cell=min(18,max(10,int(min(190/cols,92/rows))))
            width,height=max(200, cols*cell+36),rows*cell+36
            x,y=VIEW_W-width-10,42
            content_x = (width - cols*cell)//2
            content_y = 10
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
            if getattr(room,"portal_room",False):
                if self.portal_frames:
                    img=pygame.transform.smoothscale(self.portal_frames[0],(ms,ms)); panel.blit(img,img.get_rect(center=(cx,cy)))
                else:
                    pts=[(cx,cy-ms//2),(cx+ms//2,cy),(cx,cy+ms//2),(cx-ms//2,cy)]; pygame.draw.polygon(panel,(100,220,255),pts); pygame.draw.polygon(panel,(205,245,255),pts,1)
            elif room.room_type=="boss":
                self.ui_atlas.draw_icon(panel, (cx, cy), size=max(14, ms + 4), kind="skull")
            elif room.room_type=="shop":
                self.ui_atlas.draw_icon(panel, (cx, cy), size=max(14, ms + 4), kind="key")
            elif room.room_type=="treasure":
                self.ui_atlas.draw_icon(panel, (cx, cy), size=max(14, ms + 4), kind="chest")
            elif room.room_type=="healing":
                self.ui_atlas.draw_icon(panel, (cx, cy), size=max(14, ms + 4), kind="heal")
            elif room.room_type in ("elite", "miniboss"):
                self.ui_atlas.draw_icon(panel, (cx, cy), size=max(14, ms + 4), kind="white_skull")
            elif room.room_type=="challenge":
                self.ui_atlas.draw_icon(panel, (cx, cy), size=max(14, ms + 4), kind="target")
            elif room.room_type=="event":
                self.ui_atlas.draw_icon(panel, (cx, cy), size=max(14, ms + 4), kind="exclamation")
            elif room.room_type=="secret":
                self.ui_atlas.draw_icon(panel, (cx, cy), size=max(14, ms + 4), kind="pin")
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

        # Solo monedas en la esquina superior derecha.
        coins_label = "DUNGEON %d   MONEDAS  %d" % (getattr(sim,"difficulty",1), p.coins)
        self.text(screen, coins_label, (VIEW_W - 12, 14), (255, 225, 135), self.font, right=True)
        if getattr(sim, "statue_buffs", None):
            buff_labels={"defense":"DEF","melee":"MEL","ranged":"DIST","ability":"HAB","critical":"CRIT"}
            labels="  ".join(buff_labels.get(b.get("kind"),"BUFF") for b in sim.statue_buffs)
            self.text(screen, "ESTATUAS  " + labels, (VIEW_W - 12, 34), (125, 225, 205), self.small, right=True)
        self.draw_minimap(screen, sim, large=False)

        # Barra de jefe: centrada y reducida para no invadir los indicadores laterales.
        bosses = [e for e in sim.enemies if getattr(e, "is_boss", False) and e.alive]
        if bosses:
            boss = bosses[0]
            bw, bh = 500, 38
            bx, by = (VIEW_W - bw) // 2, 10
            boss_rect = pygame.Rect(bx, by, bw, bh)
            panel(boss_rect, fill=(17, 15, 22, 238), border=(104, 73, 78))
            title = str(boss.d.name).upper()
            self.text(screen, title[:34], (bx + 11, by + 4), (242, 231, 226), self.small)
            phase = max(1, min(3, int(getattr(boss, "phase", 1))))
            phase_color = {1: (211, 92, 84), 2: (231, 133, 65), 3: (240, 184, 83)}[phase]
            self.text(screen, "FASE %d/3" % phase, (bx + bw - 62, by + 4), phase_color, self.small)
            track = pygame.Rect(bx + 10, by + 22, bw - 20, 9)
            hp_ratio = max(0.0, min(1.0, boss.hp / max(1.0, boss.max_hp)))
            if not self.ui_atlas.draw_bar(screen, track, hp_ratio):
                pygame.draw.rect(screen, (6, 7, 12), track, border_radius=4)
                fill_w = int((track.width - 2) * hp_ratio)
                if fill_w > 0:
                    fill = pygame.Rect(track.x + 1, track.y + 1, fill_w, track.height - 2)
                    pygame.draw.rect(screen, (157, 43, 58), fill, border_radius=3)
                    pygame.draw.line(screen, (236, 105, 102), (fill.x + 2, fill.y + 1), (max(fill.x + 2, fill.right - 2), fill.y + 1), 1)
            for mark in (1 / 3, 2 / 3):
                mx = track.x + int(track.width * mark)
                pygame.draw.line(screen, (29, 22, 29), (mx, track.y + 1), (mx, track.bottom - 1), 2)

        # Panel inferior: arma y munición a la izquierda; habilidades a la derecha.
        w = p.weapon
        weapon_rect = pygame.Rect(22, VIEW_H - 74, 218, 64)
        panel(weapon_rect, fill=(15, 17, 25, 218), border=(64, 70, 86))
        hud_weapon = self._fit_image(self.weapon_scaled_images.get(getattr(w.d, "id", "")), 28)
        if hud_weapon is not None:
            screen.blit(hud_weapon, hud_weapon.get_rect(topleft=(62, VIEW_H - 61)))
            self.text(screen, w.d.name, (102, VIEW_H - 61), (240, 241, 246), self.small)
        else:
            self.text(screen, w.d.name, (62, VIEW_H - 61), (240, 241, 246), self.small)
        is_melee = getattr(w.d, "class", "") == "melee"
        if is_melee:
            ammo_text = "USOS  %d/%d" % (w.ammo, w.d.magazine)
            ammo_color = (255, 120, 120) if w.ammo <= 3 else (210, 218, 230)
        elif w.reloading:
            ammo_text, ammo_color = "RECARGANDO", (240, 200, 90)
        else:
            ammo_text = "MUNICIÓN  %d/%d" % (w.ammo, w.d.magazine)
            ammo_color = (255, 120, 120) if w.ammo <= 3 else (210, 218, 230)

        # Munición y estado de recarga quedan en una sola línea limpia. La barra
        # de progreso fue eliminada para evitar ruido visual en el panel.
        ammo_pos = (62, VIEW_H - 34)
        self.text(screen, ammo_text, ammo_pos, ammo_color, self.small)

        # Solo cuando el cargador está completamente vacío mostramos el icono de
        # recarga, pegado a la munición y dentro del mismo panel.
        if not is_melee and not w.reloading and w.ammo <= 0:
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
            selected = occupied and p.inventory[slot_index] is p.weapon
            fill = (28, 26, 32, 225) if occupied else (12, 15, 22, 170)
            border = (255, 203, 105) if selected else ((86, 145, 168) if occupied else (54, 61, 75))
            if not self.ui_atlas.draw_slot(screen, rect, selected):
                panel(rect, fill=fill, border=border)
            if occupied:
                weapon_state = p.inventory[slot_index]
                icon = self._fit_image(self.weapon_scaled_images.get(getattr(weapon_state.d, "id", "")), 31)
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

