"""Ashen Vault - roguelike de acción 2D. Ejecutar: python main.py"""
import sys
from pathlib import Path
import pygame

from game.data import GameData
from game.save import SaveData, DEFAULT
from game.audio import Audio
from game.fx import Fx
from game.render import Renderer, VIEW_W, VIEW_H
from game.menu_visuals import MenuVisuals
from game.ui_atlas import UIAtlas
from game.intro import IntroPlayer
from game.sim import Sim, Input

INTRO, MENU, PLAY, PAUSE, MAP, DEAD, VICTORY, SETTINGS, CHAR_SELECT, HUB, STATUE = "intro", "menu", "play", "pause", "map", "dead", "victory", "settings", "char_select", "hub", "statue"
MENU_ITEMS = ["Jugar", "Configuracion", "Salir"]
PAUSE_ITEMS = ["Continuar", "Configuracion", "Reiniciar run", "Salir al menu"]
SETTINGS_ITEMS = ["Volumen efectos", "Volumen musica", "Sensibilidad mouse", "Mover arriba", "Mover abajo", "Mover izquierda", "Mover derecha", "Dash", "Habilidad", "Recargar", "Pausa", "Minimapa", "Pantalla completa", "Restablecer", "Volver"]
SETTING_KEYS = {"Mover arriba":"up", "Mover abajo":"down", "Mover izquierda":"left", "Mover derecha":"right", "Dash":"dash", "Habilidad":"ability", "Recargar":"reload", "Pausa":"pause", "Minimapa":"map"}
HUB_ITEMS = ["Iniciar run", "Personajes", "Mejoras", "Volver al menu"]


class App:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.fullscreen = True
        # Presentación independiente: una ventana sin bordes muestra el icono del juego
        # antes de crear la ventana principal. Esto imita el arranque de muchos juegos
        # comerciales y evita que el splash forme parte de la ventana de AshenVault.
        if not self._show_boot_splash():
            pygame.quit()
            raise SystemExit(0)

        pygame.display.set_caption("AshenVault")
        # Ventana física redimensionable + lienzo lógico fijo. El lienzo se escala
        # al tamaño disponible al presentar cada frame, evitando que la vista quede
        # pequeña al agrandar la ventana y conservando la proporción 16:9.
        self.window = pygame.display.set_mode((VIEW_W, VIEW_H), pygame.RESIZABLE, vsync=0)
        self.screen = pygame.Surface((VIEW_W, VIEW_H)).convert()
        self._set_window_icon()
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        self.data = GameData()
        self.save = SaveData()
        self.fullscreen = bool(self.save.data["settings"].get("fullscreen", True))
        if self.fullscreen:
            try:
                pygame.Window.from_display_module().set_fullscreen(desktop=True)
            except (pygame.error, AttributeError):
                self.fullscreen = False
                self.save.data["settings"]["fullscreen"] = False
                self.save.save()
        self.audio = Audio(self.save.data["settings"].get("effects_volume", self.save.data["settings"].get("volume",0.6)), self.save.data["settings"].get("music_volume",0.6))
        self.r = Renderer(self.data)
        # El HUD refleja también las teclas reasignadas desde Configuración.
        self.r.key_bindings = self.save.data["settings"].get("keys", {})
        self.menu_visuals = MenuVisuals((VIEW_W, VIEW_H))
        self.ui_atlas = UIAtlas()
        self.intro = IntroPlayer((VIEW_W, VIEW_H), music_volume=self.audio.music_volume)
        self.fx = Fx()
        self.inp = Input()
        self.state = INTRO if not self.intro.done else MENU
        self.sel = 0
        self.sim = None
        self.char_id = "soldier"
        self.hub_sel = 0
        self.hub_dropdown_open = False
        self.hub_dropdown_sel = 0
        self.char_sel = 0
        self.char_ids = list(self.data.characters)
        self.character_portraits = {}
        self._load_character_portraits()
        self.reward = 0
        self.info = None          # panel informativo (Personajes/Arsenal/...)
        self.back_state = MENU
        self.settings_sel = 0
        self.rebind_action = None
        self.t = 0.0
        # Transición visual de la última imagen de la intro al menú.
        self._intro_transition_surface = None
        self._intro_transition_t = 0.0
        self._intro_transition_duration = 0.85
        self.running = True
        self.large_minimap = False
        if self.state == MENU:
            self.audio.sync_music(self.state, self.sim)

    def _show_boot_splash(self):
        """Muestra el icono en una ventana independiente y sin bordes.

        La ventana se destruye antes de crear la ventana principal del juego, de modo
        que el jugador ve primero únicamente la marca de AshenVault y después la
        ventana normal que contiene la intro MP4.
        """
        duration = 3.0
        try:
            pygame.display.set_caption("AshenVault")
            flags = getattr(pygame, "NOFRAME", 0)
            splash_w, splash_h = 640, 360
            splash = pygame.display.set_mode((splash_w, splash_h), flags)
            pygame.display.set_caption("AshenVault")
            # Centrar explícitamente la ventana sin bordes cuando el backend expone
            # la posición de la ventana SDL. Si no está disponible, SDL usa su
            # comportamiento predeterminado y el splash sigue funcionando.
            try:
                desktop_w, desktop_h = pygame.display.get_desktop_sizes()[0]
                win = pygame.Window.from_display_module()
                win.position = ((desktop_w - splash_w) // 2, (desktop_h - splash_h) // 2)
            except (AttributeError, IndexError, TypeError, pygame.error):
                pass

            icon_path = Path(__file__).resolve().parent / "assets" / "icons" / "AshenVaultIcon.png"
            icon = None
            if icon_path.is_file():
                try:
                    icon = pygame.image.load(str(icon_path)).convert_alpha()
                    # Recorta el PNG al contorno real del modelo. Así el fondo
                    # negro sólo ocupa la silueta rectangular necesaria y no un
                    # margen transparente enorme alrededor del logo.
                    bbox = icon.get_bounding_rect(min_alpha=8)
                    if bbox.width > 0 and bbox.height > 0:
                        icon = icon.subsurface(bbox).copy()
                    opaque=pygame.Surface(icon.get_size()).convert()
                    opaque.fill((0,0,0))
                    opaque.blit(icon,(0,0))
                    icon=opaque
                except (pygame.error, OSError):
                    icon = None

            # Fondo negro y logo centrado, con margen para que no domine toda la pantalla.
            splash.fill((0, 0, 0))
            if icon is not None:
                iw, ih = icon.get_size()
                max_w = int(splash_w * 0.66)
                max_h = int(splash_h * 0.90)
                scale = min(max_w / max(1, iw), max_h / max(1, ih))
                if scale < 0.999:
                    icon = pygame.transform.smoothscale(
                        icon, (max(1, int(iw * scale)), max(1, int(ih * scale)))
                    )
                splash.blit(icon, icon.get_rect(center=(splash_w // 2, splash_h // 2)))
            pygame.display.flip()
            self._make_splash_transparent(splash_w, splash_h)

            clock = pygame.time.Clock()
            elapsed = 0.0
            while elapsed < duration:
                dt = clock.tick(60) / 1000.0
                elapsed += dt
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        pygame.display.quit()
                        pygame.display.init()
                        return False
                    if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                        elapsed = duration
                        break

            pygame.display.quit()
            pygame.display.init()
            return True
        except (pygame.error, OSError):
            # Si el backend no permite una ventana NOFRAME, no bloqueamos el arranque:
            # cerramos el display y continuamos con la ventana principal.
            try:
                pygame.display.quit()
                pygame.display.init()
            except pygame.error:
                pass
            return True

    def _make_splash_transparent(self, splash_w, splash_h):
        """Hace transparente el fondo negro del splash en Windows.

        Se usa color-key sobre una ventana layered: el negro se vuelve transparente
        y solo queda visible el PNG con su propio canal alpha. En otros sistemas
        simplemente se conserva el fondo negro para no comprometer el arranque.
        """
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes
            hwnd = ctypes.windll.user32.FindWindowW(None, "AshenVault")
            if not hwnd:
                return
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            LWA_COLORKEY = 0x00000001
            user32 = ctypes.windll.user32
            get_style = user32.GetWindowLongW
            set_style = user32.SetWindowLongW
            get_style.restype = wintypes.LONG
            set_style.restype = wintypes.LONG
            style = get_style(hwnd, GWL_EXSTYLE)
            set_style(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)
            user32.SetLayeredWindowAttributes(hwnd, 0x000000, 0, LWA_COLORKEY)
        except Exception:
            # Si Windows/SDL no permite color-key, el splash sigue funcionando.
            pass

    def _apply_fullscreen(self, enabled):
        """Cambia entre ventana y pantalla completa sin cambiar la resolución lógica.

        pygame-ce 2.5.x no expone FULLSCREEN_DESKTOP como una constante de
        pygame.display. Su API Window sí permite solicitar explícitamente
        fullscreen usando la resolución actual del escritorio.
        """
        enabled = bool(enabled)
        try:
            window = pygame.Window.from_display_module()
            if enabled:
                window.set_fullscreen(desktop=True)
            else:
                window.set_windowed()

            self.fullscreen = enabled
            self.save.data["settings"]["fullscreen"] = enabled
            self.save.save()
        except (pygame.error, AttributeError):
            # Si el backend no soporta la API Window, dejamos el juego en
            # ventana y no guardamos un estado de pantalla completa inválido.
            self.fullscreen = False
            self.save.data["settings"]["fullscreen"] = False
            self.save.save()

    def _reset_settings(self):
        """Restablece únicamente las preferencias configurables; conserva progreso."""
        defaults = DEFAULT["settings"]
        self.save.data["settings"] = __import__("copy").deepcopy(defaults)
        self.audio.set_effects_volume(defaults["effects_volume"])
        self.audio.set_music_volume(defaults["music_volume"])
        self._apply_fullscreen(defaults["fullscreen"])
        self.rebind_action = None
        self.save.save()

    def _set_window_icon(self):
        """Carga el icono PNG del juego para la ventana de Pygame.

        Archivo esperado:
            assets/icons/AshenVaultIcon.png

        El ICO se reserva para Windows/PyInstaller y el futuro instalador.
        """
        icon_path = Path(__file__).resolve().parent / "assets" / "icons" / "AshenVaultIcon.png"
        if not icon_path.is_file():
            return
        try:
            icon = pygame.image.load(str(icon_path)).convert_alpha()
            pygame.display.set_icon(icon)
        except (pygame.error, OSError):
            # El juego puede iniciar aunque todavía no exista el icono.
            pass

    @staticmethod
    def _remove_portrait_background(image):
        """Elimina fondos blancos/negros sólidos conectados al borde del PNG."""
        if image is None:
            return None
        out = image.convert_alpha()
        w, h = out.get_size()
        samples = [out.get_at((x, y))[:3] for x, y in ((0,0),(w-1,0),(0,h-1),(w-1,h-1))]
        avg = tuple(sum(c[i] for c in samples)//len(samples) for i in range(3))
        if min(avg) > 220:
            bg, tol = (255,255,255), 28
        elif max(avg) < 35:
            bg, tol = (0,0,0), 22
        else:
            return out
        px = pygame.PixelArray(out)
        seen = set()
        stack = []
        for x in range(w):
            stack.extend(((x,0),(x,h-1)))
        for y in range(h):
            stack.extend(((0,y),(w-1,y)))
        while stack:
            x,y = stack.pop()
            if (x,y) in seen or not (0 <= x < w and 0 <= y < h):
                continue
            rgba = out.unmap_rgb(px[x, y])
            r,g,b,a = rgba.r, rgba.g, rgba.b, rgba.a
            if a == 0:
                seen.add((x,y)); continue
            if max(abs(r-bg[0]), abs(g-bg[1]), abs(b-bg[2])) > tol:
                continue
            seen.add((x,y))
            out.set_at((x,y),(r,g,b,0))
            stack.extend(((x-1,y),(x+1,y),(x,y-1),(x,y+1)))
        del px
        return out

    def _load_character_portraits(self):
        """Carga retratos y elimina fondos sólidos que vengan incrustados en los PNG."""
        folder = Path(__file__).resolve().parent / "assets" / "characters" / "portraits"
        for filename in ("Kael.png", "Iria.png", "Rook.png", "Veyra.png", "Nox.png", "Mira.png"):
            path = folder / filename
            if path.is_file():
                try:
                    image = pygame.image.load(str(path)).convert_alpha()
                    self.character_portraits[filename[:-4].lower()] = self._remove_portrait_background(image)
                except (pygame.error, OSError):
                    pass

    def _menu_rects(self):
        if self.state == MENU and not self.info:
            return [(VIEW_W // 2 - 92, 220 + n * 57, 184, 42) for n in range(len(MENU_ITEMS))]
        if self.state == PAUSE:
            return [(VIEW_W // 2 - 105, 190 + n * 62, 210, 52) for n in range(len(PAUSE_ITEMS))]
        if self.state == HUB and not self.info:
            return []
        return []

    def handle_menu_mouse(self, pos, click=False):
        """Permite navegar y activar las opciones con el ratón."""
        if self.state == STATUE:
            accept_rect=pygame.Rect(VIEW_W//2-145,390,130,38)
            cancel_rect=pygame.Rect(VIEW_W//2+15,390,130,38)
            if click and accept_rect.collidepoint(pos):
                if self.sim.accept_statue_buff():
                    self.audio.play("ui", self.t); self.go(PLAY)
                else:
                    self.statue_message = "NO TIENES SUFICIENTES MONEDAS"
            elif click and cancel_rect.collidepoint(pos):
                self.sim.close_statue_menu(); self.go(PLAY)
            return
        if self.state == CHAR_SELECT:
            for n in range(len(self.char_ids)):
                col, row = n % 3, n // 3
                rect = pygame.Rect(20 + col * 310, 108 + row * 184, 300, 174)
                if rect.collidepoint(pos):
                    self.char_sel = n
                    if click:
                        self.char_id = self.char_ids[n]
                        self.audio.play("ui", self.t)
                        self.confirm_character_selection()
                    return
            back_rect = pygame.Rect(16, 488, 150, 34)
            upgrades_rect = pygame.Rect(VIEW_W - 166, 488, 150, 34)
            if click and back_rect.collidepoint(pos):
                self.go(HUB if self.back_state == HUB else MENU)
                return
            if click and upgrades_rect.collidepoint(pos):
                self.hub_sel = 0
                self.go(HUB)
                return
            return
        if self.state == HUB and not self.info:
            from game.save import CHARACTER_UPGRADES
            if self.hub_dropdown_open:
                dropdown=pygame.Rect(120,250,720,176)
                if dropdown.collidepoint(pos):
                    for n,cid_option in enumerate(self.char_ids):
                        col,row=n%3,n//3
                        rect=pygame.Rect(135+col*230,265+row*72,215,60)
                        if rect.collidepoint(pos):
                            self.hub_dropdown_sel=n
                            if click:
                                self.char_id=cid_option; self.hub_dropdown_open=False; self.hub_sel=0; self.audio.play("ui",self.t)
                            return
                if click:
                    self.hub_dropdown_open=False
                return
            cid=self.char_id; tree=CHARACTER_UPGRADES.get(cid,{})
            for n,kind in enumerate(tree):
                col,row=n%2,n//2
                rect=pygame.Rect(70+col*420,118+row*145,390,125)
                if rect.collidepoint(pos):
                    self.hub_sel=n+2
                    if click: self.activate_hub("UPGRADE:"+kind)
                    return
            actions=["Personajes","Volver al menu"]
            for n,item in enumerate(actions):
                rect=pygame.Rect(250+n*240,438,220,44)
                if rect.collidepoint(pos):
                    self.hub_sel=HUB_ITEMS.index(item)
                    if click: self.activate_hub(item)
                    return
            return
        if self.state == SETTINGS:
            # Las zonas clicables coinciden exactamente con los elementos dibujados.
            for idx in (0, 1):
                y = 157 + idx * 57
                bar = pygame.Rect(244, y + 17, 120, 8)
                row_rect = pygame.Rect(126, y, 266, 45)
                if row_rect.collidepoint(pos):
                    self.settings_sel = idx
                    if (click or pygame.mouse.get_pressed()[0]) and bar.collidepoint(pos):
                        field = "effects_volume" if idx == 0 else "music_volume"
                        value = round(max(0.0, min(1.0, (pos[0] - bar.x) / bar.width)), 2)
                        self.save.data["settings"][field] = value
                        if idx == 0: self.audio.set_effects_volume(value)
                        else: self.audio.set_music_volume(value)
                        self.save.save()
                    return
            sens_rect = pygame.Rect(126, 257, 266, 74)
            if sens_rect.collidepoint(pos):
                self.settings_sel = 2
                bar=pygame.Rect(145,307,228,8)
                if (click or pygame.mouse.get_pressed()[0]) and bar.collidepoint(pos):
                    v=max(0.25,min(2.0,(pos[0]-bar.x)/bar.width*1.75+0.25))
                    self.save.data["settings"]["mouse_sensitivity"]=round(v,2)
                    self.save.save()
                return
            for offset in range(9):
                idx = offset + 3
                rect = pygame.Rect(438, 153 + offset * 29, 392, 26)
                if rect.collidepoint(pos):
                    self.settings_sel = idx
                    if click:
                        self.rebind_action = SETTING_KEYS[SETTINGS_ITEMS[idx]]
                    return
            fullscreen_rect = pygame.Rect(126, 338, 266, 32)
            if fullscreen_rect.collidepoint(pos):
                self.settings_sel = 12
                if click:
                    self._apply_fullscreen(not self.save.data["settings"].get("fullscreen", False))
                return
            reset_rect = pygame.Rect(126, 383, 266, 32)
            if reset_rect.collidepoint(pos):
                self.settings_sel = 13
                if click:
                    self._reset_settings()
                return
            back = pygame.Rect(VIEW_W // 2 - 82, 462, 164, 29)
            if back.collidepoint(pos) and click:
                self.go(self.back_state)
            return
        if self.info:
            if click:
                self.info = None
            return
        rects = self._menu_rects()
        for n, rect in enumerate(rects):
            if pygame.Rect(rect).collidepoint(pos):
                if self.state == MENU: self.sel = n
                elif self.state == PAUSE: self.sel = n
                elif self.state == HUB: self.hub_sel = n
                if click:
                    self.audio.play("ui", self.t)
                    if self.state == HUB: self.activate_hub(HUB_ITEMS[n])
                    elif self.state == MENU: self.activate(MENU_ITEMS[n])
                    elif self.state == PAUSE: self.activate(PAUSE_ITEMS[n])
                return

    # ---------- teclas configurables ----------
    def key(self, action):
        name = self.save.data["settings"]["keys"][action]
        return pygame.key.key_code(name)

    def confirm_character_selection(self):
        """Confirma el personaje y continúa el flujo que abrió la selección."""
        if self.back_state == "start_run":
            self.new_run()
        else:
            self.go(HUB if self.back_state == HUB else MENU)

    def new_run(self):
        self.sim = Sim(self.data, self.char_id, meta_upgrades=self.save.data.get("upgrades", {}), character_progress=self.save.data.get("character_progress", {}).get(self.char_id, {}))
        self.sim.decoration_collider_provider = self.r
        self.fx = Fx()
        self.inp = Input()
        self.state = PLAY
        self.statue_message = ""
        pygame.event.set_grab(True)

    def go(self, state):
        self.state = state
        self.sel = 0
        pygame.event.set_grab(state == PLAY)
        self.audio.sync_music(self.state, self.sim)

    def finish_intro(self):
        """Finaliza la intro y cruza suavemente su último frame hacia el menú."""
        if self.state != INTRO:
            return

        # Conservamos exactamente lo que el jugador estaba viendo antes de
        # abandonar la cinemática. El menú se dibuja debajo y esta imagen se
        # desvanece progresivamente encima, evitando cualquier pantallazo blanco
        # o salto brusco entre escenas.
        self._intro_transition_surface = self.screen.copy()
        self._intro_transition_t = self._intro_transition_duration
        self.intro.skip()
        self.state = MENU
        self.sel = 0
        pygame.event.set_grab(False)
        self.audio.play_music("menu", fade_ms=1500)

    # ---------- entrada ----------
    def _logical_mouse_pos(self, pos=None):
        """Convierte coordenadas de la ventana física al lienzo lógico 960x540."""
        if pos is None:
            pos = pygame.mouse.get_pos()
        ww, wh = self.window.get_size()
        scale = min(ww / VIEW_W, wh / VIEW_H) if ww > 0 and wh > 0 else 1.0
        draw_w, draw_h = VIEW_W * scale, VIEW_H * scale
        left, top = (ww - draw_w) * 0.5, (wh - draw_h) * 0.5
        lx = (pos[0] - left) / max(scale, 0.001)
        ly = (pos[1] - top) / max(scale, 0.001)
        return (max(0, min(VIEW_W - 1, int(lx))), max(0, min(VIEW_H - 1, int(ly))))

    def _present(self):
        """Presenta el lienzo lógico ocupando el máximo espacio proporcional disponible."""
        self.window = pygame.display.get_surface() or self.window
        ww, wh = self.window.get_size()
        self.window.fill((0, 0, 0))
        scale = min(ww / VIEW_W, wh / VIEW_H) if ww > 0 and wh > 0 else 1.0
        size = (max(1, int(VIEW_W * scale)), max(1, int(VIEW_H * scale)))
        if size == (VIEW_W, VIEW_H):
            scaled = self.screen
        else:
            scaled = pygame.transform.smoothscale(self.screen, size)
        self.window.blit(scaled, ((ww - size[0]) // 2, (wh - size[1]) // 2))
        pygame.display.flip()

    def poll(self):
        i = self.inp
        for ev in pygame.event.get():
            if ev.type in (pygame.VIDEORESIZE, getattr(pygame, "WINDOWRESIZED", -1)) and not self.fullscreen:
                # El backend ya ajusta la superficie de display; conservamos el nuevo tamaño.
                continue
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.KEYDOWN:
                self.on_key(ev.key)
            elif ev.type == pygame.MOUSEMOTION and self.state != PLAY:
                self.handle_menu_mouse(self._logical_mouse_pos(ev.pos), click=False)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.state == PLAY:
                    i.fire_pressed = True
                else:
                    self.handle_menu_mouse(self._logical_mouse_pos(ev.pos), click=True)
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.state == PLAY:
                i.fire_released = True
            elif ev.type == pygame.WINDOWFOCUSLOST and self.state == PLAY:
                self.go(PAUSE)
        if self.state == PLAY:
            keys = pygame.key.get_pressed()
            i.move_x = float(keys[self.key("right")]) - float(keys[self.key("left")])
            i.move_y = float(keys[self.key("down")]) - float(keys[self.key("up")])
            i.fire_held = pygame.mouse.get_pressed()[0]

    def on_key(self, k):
        if self.state == INTRO:
            if k in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                self.finish_intro()
            return
        if self.state == PLAY:
            if k == self.key("pause"):
                self.go(PAUSE)
            elif k == self.key("dash"):
                self.inp.dash_pressed = True
            elif k == self.key("reload"):
                self.inp.reload_pressed = True
            elif k == self.key("map"):
                self.large_minimap = True
                self.go(MAP)
            elif k == pygame.K_e:
                self.inp.interact_pressed = True
            elif k == pygame.K_TAB:
                self.inp.switch_weapon_pressed = True
            elif k in (pygame.K_1, pygame.K_2, pygame.K_3) and self.sim:
                slot = k - pygame.K_1
                if slot < len(self.sim.player.inventory):
                    self.sim.player.weapon = self.sim.player.inventory[slot]
            elif k == self.key("ability"):
                self.inp.ability_pressed = True
            return
        items = {MENU: MENU_ITEMS, PAUSE: PAUSE_ITEMS, HUB: HUB_ITEMS}.get(self.state)
        if self.state == STATUE:
            if k in (pygame.K_ESCAPE, pygame.K_n):
                self.sim.close_statue_menu(); self.go(PLAY); return
            if k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_y):
                if self.sim.accept_statue_buff():
                    self.audio.play("ui", self.t); self.go(PLAY)
                else:
                    self.statue_message = "NO TIENES SUFICIENTES MONEDAS"
                return
            return
        if self.state == CHAR_SELECT:
            if k in (pygame.K_ESCAPE,): self.go(HUB if self.back_state==HUB else MENU); return
            if k in (pygame.K_UP, pygame.K_w): self.char_sel=(self.char_sel-1)%len(self.char_ids); return
            if k in (pygame.K_DOWN, pygame.K_s): self.char_sel=(self.char_sel+1)%len(self.char_ids); return
            if k in (pygame.K_RETURN, pygame.K_SPACE): self.char_id=self.char_ids[self.char_sel]; self.confirm_character_selection(); return
            return
        if self.state == HUB:
            if self.info:
                if k == pygame.K_ESCAPE or k in (pygame.K_RETURN, pygame.K_SPACE): self.info=None
                return
            if self.hub_dropdown_open:
                if k == pygame.K_ESCAPE:
                    self.hub_dropdown_open=False; return
                if k in (pygame.K_LEFT, pygame.K_a):
                    self.hub_dropdown_sel=(self.hub_dropdown_sel-1)%len(self.char_ids); return
                if k in (pygame.K_RIGHT, pygame.K_d):
                    self.hub_dropdown_sel=(self.hub_dropdown_sel+1)%len(self.char_ids); return
                if k in (pygame.K_UP, pygame.K_w):
                    self.hub_dropdown_sel=(self.hub_dropdown_sel-3)%len(self.char_ids); return
                if k in (pygame.K_DOWN, pygame.K_s):
                    self.hub_dropdown_sel=(self.hub_dropdown_sel+3)%len(self.char_ids); return
                if k in (pygame.K_RETURN, pygame.K_SPACE):
                    self.char_id=self.char_ids[self.hub_dropdown_sel]; self.hub_dropdown_open=False; self.hub_sel=0; self.audio.play("ui",self.t); return
                return
            if k == pygame.K_ESCAPE:
                self.go(MENU); return
            from game.save import CHARACTER_UPGRADES
            dynamic=["Iniciar run","Personajes"]+["UPGRADE:"+kind for kind in CHARACTER_UPGRADES.get(self.char_id,{})]+["Volver al menu"]
            if k in (pygame.K_UP, pygame.K_w):
                self.hub_sel=(self.hub_sel-1)%len(dynamic); return
            if k in (pygame.K_DOWN, pygame.K_s):
                self.hub_sel=(self.hub_sel+1)%len(dynamic); return
            if k in (pygame.K_RETURN, pygame.K_SPACE):
                if self.hub_sel==1:
                    self.hub_dropdown_open=True; self.hub_dropdown_sel=self.char_ids.index(self.char_id)
                else:
                    self.activate_hub(dynamic[self.hub_sel])
                return
            return
        if k == pygame.K_ESCAPE:
            if self.state == MAP:
                self.large_minimap = False
                self.go(PLAY)
            elif self.state == PAUSE:
                self.go(PLAY)
            elif self.state in (SETTINGS,) or self.info:
                self.info = None
                self.go(self.back_state)
            return
        if self.state in (DEAD, VICTORY):
            if k in (pygame.K_RETURN, pygame.K_SPACE):
                self.go(MENU)
            return
        if self.state == SETTINGS:
            if self.rebind_action:
                if k == pygame.K_ESCAPE:
                    self.rebind_action = None
                    return
                name = pygame.key.name(k)
                if name and name != "unknown":
                    self.save.set_key(self.rebind_action, name)
                    self.rebind_action = None
                    self.audio.play("ui", self.t)
                return
            if k in (pygame.K_UP, pygame.K_w):
                self.settings_sel = (self.settings_sel - 1) % len(SETTINGS_ITEMS)
                self.audio.play("ui", self.t)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.settings_sel = (self.settings_sel + 1) % len(SETTINGS_ITEMS)
                self.audio.play("ui", self.t)
            elif k in (pygame.K_LEFT, pygame.K_a) and self.settings_sel in (0,1,2):
                field="effects_volume" if self.settings_sel==0 else "music_volume"
                v=(max(0.25,self.save.data["settings"].get("mouse_sensitivity",1.0)-0.05) if self.settings_sel==2 else max(0.0,self.save.data["settings"].get(field,0.6)-0.1)); self.save.data["settings"]["mouse_sensitivity" if self.settings_sel==2 else field]=round(v,2)
                if self.settings_sel != 2:
                    if field=="effects_volume": self.audio.set_effects_volume(v)
                    else: self.audio.set_music_volume(v)
                self.save.save()
            elif k in (pygame.K_RIGHT, pygame.K_d) and self.settings_sel in (0,1,2):
                field="effects_volume" if self.settings_sel==0 else "music_volume"
                v=(min(2.0,self.save.data["settings"].get("mouse_sensitivity",1.0)+0.05) if self.settings_sel==2 else min(1.0,self.save.data["settings"].get(field,0.6)+0.1)); self.save.data["settings"]["mouse_sensitivity" if self.settings_sel==2 else field]=round(v,2)
                if self.settings_sel != 2:
                    if field=="effects_volume": self.audio.set_effects_volume(v)
                    else: self.audio.set_music_volume(v)
                self.save.save()
            elif k in (pygame.K_RETURN, pygame.K_SPACE):
                item=SETTINGS_ITEMS[self.settings_sel]
                if item == "Volver":
                    self.go(self.back_state)
                elif item == "Pantalla completa":
                    self._apply_fullscreen(not self.save.data["settings"].get("fullscreen", False))
                elif item == "Restablecer":
                    self._reset_settings()
                elif item not in ("Volumen efectos","Volumen musica","Sensibilidad mouse"):
                    self.rebind_action=SETTING_KEYS[item]
            return
        if self.info:
            self.info = None
            return
        if not items:
            return
        if k in (pygame.K_UP, pygame.K_w):
            self.sel = (self.sel - 1) % len(items)
            self.audio.play("ui", self.t)
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.sel = (self.sel + 1) % len(items)
            self.audio.play("ui", self.t)
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            self.audio.play("ui", self.t)
            self.activate(items[self.sel])

    def activate_hub(self, item):
        if item == "Iniciar run": self.new_run()
        elif item == "Personajes":
            self.hub_dropdown_open=True; self.hub_dropdown_sel=self.char_ids.index(self.char_id)
        elif item == "Mejoras":
            self.hub_sel=2
        elif item.startswith("UPGRADE:"):
            kind=item.split(":",1)[1]
            if self.save.buy_character_upgrade(self.char_id,kind): self.audio.play("ui",self.t)
        elif item == "Volver al menu": self.go(MENU)

    def activate(self, item):
        if item == "Jugar":
            self.back_state = "start_run"
            self.char_sel = self.char_ids.index(self.char_id)
            self.go(CHAR_SELECT)
        elif item == "Reiniciar run":
            self.new_run()
        elif item == "Continuar":
            self.go(PLAY)
        elif item == "Mejoras":
            self.hub_sel=2; self.go(HUB)
        elif item == "Personajes":
            self.back_state = MENU
            self.char_sel = self.char_ids.index(self.char_id)
            self.go(CHAR_SELECT)
        elif item == "Configuracion":
            self.back_state = self.state
            self.settings_sel = 0
            self.rebind_action = None
            self.go(SETTINGS)
        elif item == "Salir al menu":
            self.go(MENU)
        elif item == "Salir":
            self.running = False
        else:
            self.back_state = self.state
            self.info = item

    # ---------- bucle ----------
    def update(self, dt):
        if self.state == INTRO:
            self.intro.update(dt)
            if self.intro.done:
                self.finish_intro()
            return

        if self._intro_transition_t > 0.0:
            self._intro_transition_t = max(0.0, self._intro_transition_t - max(0.0, float(dt)))
            if self._intro_transition_t <= 0.0:
                self._intro_transition_surface = None

        # El video pertenece al sistema de menús y debe continuar animándose
        # en MENU, HUB, selección de personaje, información y configuración.
        if self.state not in (PLAY, PAUSE):
            self.menu_visuals.update(dt)
        if self.state != PLAY:
            return
        s = self.sim
        # Actualizar el apuntado antes de simular evita un frame de latencia en el disparo.
        self.inp.aim_x, self.inp.aim_y = self.world_mouse()
        s.update(self.inp, dt)       # la pausa simplemente no llama a update: todo se congela
        if s.statue_menu is not None:
            self.statue_message = ""
            self.go(STATUE)
        self.audio.sync_music(self.state, s)
        self.inp.clear_edges()
        for ev in s.events:
            self.fx.handle(ev)
            self.audio.play(ev[0], self.t)
        s.events.clear()
        self.fx.update(dt)
        if s.over:
            self.reward = self.save.record_run(s.stats, victory=s.victory, char_id=self.char_id)
            self.run_xp = getattr(self.save, "last_run_xp", s.stats.get("xp", 0))
            self.levels_gained = getattr(self.save, "last_levels_gained", 0)
            self.go(HUB)

    def world_mouse(self):
        mx, my = self._logical_mouse_pos()
        ox, oy = getattr(self.r, "cam", (0, 0))
        sensitivity=float(self.save.data["settings"].get("mouse_sensitivity",1.0)); mx=VIEW_W*0.5+(mx-VIEW_W*0.5)*sensitivity; my=VIEW_H*0.5+(my-VIEW_H*0.5)*sensitivity
        return mx - ox, my - oy

    def draw_option_card(self, rect, label, selected=False, value=None, compact=False, use_atlas=True):
        """Opción de menú usando el atlas visual generado para Ashen Vault."""
        x, y, w, h = rect
        destructive = str(label).lower() in {"salir", "salir al menu", "abandonar", "eliminar", "cancelar", "cerrar"}
        atlas_label = label
        if self.state == PAUSE:
            atlas_label = {"Configuracion": "Configuracion pausa", "Mejoras": "Mejoras pausa"}.get(str(label), label)
        used_atlas = use_atlas and self.ui_atlas.draw_button(self.screen, rect, atlas_label, selected=selected, destructive=destructive)

        if not used_atlas:
            panel = pygame.Surface((w, h), pygame.SRCALPHA)
            fill = (18, 20, 31, 224) if selected else (12, 14, 23, 190)
            pygame.draw.rect(panel, fill, (0, 0, w, h), border_radius=5)
            border = (74, 226, 220, 245) if selected else (102, 108, 130, 190)
            pygame.draw.rect(panel, border, (0, 0, w, h), 2 if selected else 1, border_radius=5)
            self.screen.blit(panel, (x, y))

        font = self.r.menu_font if selected else self.r.menu_small
        color = (244, 252, 250) if selected else (195, 205, 220)
        # Las piezas del atlas ya contienen el texto/iconografía de sus botones.
        # Solo dibujamos el texto cuando la opción no existe como sprite completo.
        if used_atlas:
            if value is not None:
                val_img = font.render(str(value), True, (93, 235, 222) if selected else (205, 210, 224))
                self.screen.blit(val_img, val_img.get_rect(midright=(x + w - 14, y + h // 2)))
        elif value is None:
            self.r.text(self.screen, label, (x + w // 2, y + h // 2), color, font, True)
        else:
            label_img = font.render(label, True, color)
            self.screen.blit(label_img, label_img.get_rect(midleft=(x + 15, y + h // 2)))
            val_img = font.render(str(value), True, (93, 235, 222) if selected else (205, 210, 224))
            self.screen.blit(val_img, val_img.get_rect(midright=(x + w - 14, y + h // 2)))

    def draw_menu_bg(self):
        """Fondo común para todas las pantallas del menú (excepto PAUSA)."""
        self.menu_visuals.draw_background(self.screen)

    def draw_list(self, title, items, sel):
        self.draw_menu_bg()
        self.r.text(self.screen, title, (VIEW_W // 2, 90), (240, 190, 80), self.r.big, True)
        for n, it in enumerate(items):
            col = (255, 235, 150) if n == sel else (170, 165, 180)
            label = ("> " + it + " <") if n == sel else it
            self.r.text(self.screen, label, (VIEW_W // 2, 190 + n * 38), col, center=True)

    def draw_info(self):
        s = self.save.data
        lines = []
        if self.info == "Personajes":
            for c in self.data.characters.values():
                tag = "DESBLOQUEADO" if c.id in s["unlocked_characters"] else "BLOQUEADO"
                lines += ["%s [%s]" % (c.name, tag), "  " + c.description,
                          "  HP %d  Escudo %d  Energia %d  Vel %d" % (c.max_hp, c.max_shield, c.max_energy, c.speed)]
        elif self.info == "Arsenal":
            for w in self.data.weapons.values():
                lines += ["%s (%s)" % (w.name, w.rarity),
                          "  Dano %s  Cadencia %.2fs  Cargador %d  Recarga %.1fs  Energia %d  Tipo %s" % (
                              w.damage, w.fire_interval, w.magazine, w.reload_time, w.energy_cost, w.damage_type),
                          "  Efecto de rareza: %s" % getattr(w, "rarity_effect", "none")]
        elif self.info == "Mejoras":
            lines = ["Moneda permanente: %d" % s["meta_currency"], "", "Tienda de mejoras permanentes disponible en el refugio."]
        else:
            st = s["stats"]
            lines = ["Partidas: %d" % st["runs"], "Enemigos derrotados: %d" % st["kills"],
                     "Mejor oleada: %d" % st["best_wave"], "Monedas recogidas: %d" % st["total_coins"]]
        self.draw_menu_bg()
        panel = pygame.Surface((820, 390), pygame.SRCALPHA)
        pygame.draw.rect(panel, (9, 12, 22, 226), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, (92, 151, 166, 210), panel.get_rect(), 1, border_radius=10)
        self.screen.blit(panel, (70, 90))
        self.r.text(self.screen, self.info.upper(), (VIEW_W // 2, 63), (240, 195, 105), self.r.menu_title, True)
        y = 112
        old_clip = self.screen.get_clip()
        self.screen.set_clip(pygame.Rect(84, 104, 792, 365))
        for line in lines[:13]:
            if not line:
                y += 8
                continue
            is_heading = not line.startswith("  ")
            font = self.r.menu_font if is_heading else self.r.menu_small
            color = (103, 229, 220) if is_heading else (211, 220, 232)
            # Ajusta cada línea larga al ancho útil del panel, sin desbordes.
            available = 770
            words = line.split()
            wrapped, current = [], ""
            for word in words:
                candidate = (current + " " + word).strip()
                if font.size(candidate)[0] > available and current:
                    wrapped.append(current)
                    current = word
                else:
                    current = candidate
            if current:
                wrapped.append(current)
            for wrapped_line in wrapped:
                self.r.text(self.screen, wrapped_line, (94, y), color, font)
                y += 22 if not is_heading else 25
        self.screen.set_clip(old_clip)
        self.draw_option_card((VIEW_W // 2 - 100, 488, 200, 30), "Volver", False)

    def draw_hub(self):
        if self.info: self.draw_info(); return
        from game.save import CHARACTER_UPGRADES, xp_to_next
        self.draw_menu_bg(); s=self.save.data; cid=self.char_id; tree=CHARACTER_UPGRADES.get(cid,{})
        c=self.data.characters[cid]; prog=s["character_progress"].get(cid,{"level":1,"xp":0,"upgrades":{}}); level=prog.get("level",1); xp=prog.get("xp",0); needed=xp_to_next(level)
        self.r.text(self.screen,"MEJORAS · %s" % c.name.split(",")[0].upper(),(VIEW_W//2,42),(240,195,105),self.r.menu_title,True)
        self.r.text(self.screen,"NIVEL %d    XP %d / %d    FRAGMENTOS %d" % (level,xp,needed,s["meta_currency"]),(VIEW_W//2,78),(112,231,219),self.r.menu_font,True)
        for n,(kind,up) in enumerate(tree.items()):
            col,row=n%2,n//2; x,y,w,h=70+col*420,118+row*145,390,125; selected=self.hub_sel==n+2
            card=pygame.Rect(x,y,w,h); pygame.draw.rect(self.screen,(10,13,23,235),card,border_radius=8); pygame.draw.rect(self.screen,(74,226,220) if selected else (75,91,113),card,2 if selected else 1,border_radius=8)
            self.r.text(self.screen,up["name"].upper(),(x+w//2,y+24),(105,232,222) if selected else (214,223,235),self.r.menu_font,True)
            self.r.text(self.screen,up["description"],(x+w//2,y+52),(183,198,213),self.r.menu_small,True)
            lvl=int(prog.get("upgrades",{}).get(kind,0)); self.r.text(self.screen,"NIVEL %d / %d"%(lvl,up["max"]),(x+w//2,y+76),(232,222,190),self.r.menu_small,True)
            if lvl>=up["max"]: price="MAXIMO"; color=(124,231,173)
            else:
                cost=self.save.character_upgrade_cost(cid,kind); price="MEJORAR · %d FRAGMENTOS"%cost; color=(255,219,133) if s["meta_currency"]>=cost else (161,167,181)
            self.r.text(self.screen,price,(x+w//2,y+103),color,self.r.menu_small,True)
        for n,item in enumerate(("Personajes","Volver al menu")):
            self.draw_option_card((250+n*240,438,220,44),item,self.hub_sel==HUB_ITEMS.index(item))
        self.r.text(self.screen,"Las mejoras son exclusivas de %s y afectan sus partidas."%c.name.split(",")[0],(VIEW_W//2,518),(150,165,180),self.r.menu_small,True)
        if self.hub_dropdown_open:
            panel=pygame.Rect(120,250,720,176)
            pygame.draw.rect(self.screen,(7,10,19,248),panel,border_radius=10)
            pygame.draw.rect(self.screen,(78,220,210,230),panel,2,border_radius=10)
            self.r.text(self.screen,"SELECCIONAR PERSONAJE PARA MEJORAR",(VIEW_W//2,258),(240,205,120),self.r.menu_small,True)
            for n,cid_option in enumerate(self.char_ids):
                col,row=n%3,n//3
                rect=pygame.Rect(135+col*230,265+row*72,215,60)
                selected=n==self.hub_dropdown_sel
                pygame.draw.rect(self.screen,(19,35,43,245) if selected else (12,17,27,230),rect,border_radius=6)
                pygame.draw.rect(self.screen,(75,226,220) if selected else (72,87,108),rect,2 if selected else 1,border_radius=6)
                copt=self.data.characters[cid_option]
                self.r.text(self.screen,copt.name.split(",")[0],(rect.centerx,rect.y+22),(255,225,145) if selected else (205,216,229),self.r.menu_font,True)
                self.r.text(self.screen,"NIVEL %d"%self.save.data.get("character_progress",{}).get(cid_option,{}).get("level",1),(rect.centerx,rect.y+43),(120,220,205) if selected else (150,165,180),self.r.menu_small,True)

    def draw(self):
        scr = self.screen
        if self.state == INTRO:
            self.intro.draw(scr)
            self._present()
            return
        mouse = self._logical_mouse_pos()
        if self.state in (PLAY, PAUSE, MAP, DEAD, VICTORY, STATUE) and self.sim:
            self.r.draw_world(scr, self.sim, self.fx, self.t)
            self.r.draw_hud(scr, self.sim, self.fx, mouse)
            if self.state == MAP:
                shade=pygame.Surface((VIEW_W,VIEW_H),pygame.SRCALPHA); shade.fill((3,5,10,205)); scr.blit(shade,(0,0))
                self.r.draw_minimap(scr,self.sim,large=True)
                self.r.text(scr,"M / ESC · CERRAR MAPA",(VIEW_W//2,VIEW_H-16),(175,190,205),self.r.menu_small,True)
        if self.state == HUB:
            self.draw_hub()
        elif self.state == MENU:
            if self.info:
                self.draw_info()
            else:
                self.menu_visuals.draw(scr)
                for n, it in enumerate(MENU_ITEMS):
                    self.draw_option_card(self._menu_rects()[n], it, n == self.sel)
                self.r.text(scr, "AshenVault - By ElMonarca", (14, VIEW_H - 13), (168, 176, 190), self.r.small)
        elif self.state == STATUE:
            ov=pygame.Surface((VIEW_W,VIEW_H),pygame.SRCALPHA); ov.fill((2,5,10,185)); scr.blit(ov,(0,0))
            offer=self.sim.statue_menu or {}
            panel=pygame.Rect(VIEW_W//2-255,105,510,350)
            pygame.draw.rect(scr,(8,12,22,245),panel,border_radius=14)
            pygame.draw.rect(scr,(116,190,180,235),panel,2,border_radius=14)
            self.r.text(scr,str(offer.get("name","ESTATUA")).upper(),(VIEW_W//2,145),(240,205,120),self.r.menu_title,True)
            self.r.text(scr,str(offer.get("title","BENDICION")),(VIEW_W//2,188),(100,230,215),self.r.menu_font,True)
            desc=str(offer.get("description","")); words=desc.split(); lines=[]; cur=""
            for word in words:
                candidate=(cur+" "+word).strip()
                if self.r.menu_small.size(candidate)[0]>420 and cur:
                    lines.append(cur); cur=word
                else: cur=candidate
            if cur: lines.append(cur)
            for i,line in enumerate(lines[:4]): self.r.text(scr,line,(VIEW_W//2,225+i*22),(220,228,238),self.r.menu_small,True)
            value=float(offer.get("value",0))*100; kind=offer.get("kind")
            value_text=("-%d%% daño recibido"%round(value)) if kind=="defense" else ("+%d%% daño cuerpo a cuerpo"%round(value)) if kind=="melee" else ("+%d%% daño a distancia"%round(value)) if kind=="ranged" else ("+%d%% efectividad de habilidad"%round(value)) if kind=="ability" else ("+%d%% crítico"%round(value))
            self.r.text(scr,value_text,(VIEW_W//2,315),(255,224,135),self.r.menu_font,True)
            cost=int(offer.get("cost",0)); coins=int(self.sim.player.coins); cost_col=(110,235,175) if coins>=cost else (235,100,100)
            self.r.text(scr,"Costo: %d monedas   ·   Tienes: %d"%(cost,coins),(VIEW_W//2,348),cost_col,self.r.menu_small,True)
            self.draw_option_card((VIEW_W//2-145,390,130,38),"Aceptar",False)
            self.draw_option_card((VIEW_W//2+15,390,130,38),"Salir",False)
            self.r.text(scr,"ENTER / Y · aceptar    ESC / N · salir",(VIEW_W//2,455),(165,180,198),self.r.menu_small,True)
            if self.statue_message: self.r.text(scr,self.statue_message,(VIEW_W//2,480),(245,105,105),self.r.menu_small,True)
        elif self.state == PAUSE:
            ov = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160))
            scr.blit(ov, (0, 0))
            self.r.text(scr, "PAUSA", (VIEW_W // 2, 140), (240, 190, 80), self.r.menu_title, True)
            for n, it in enumerate(PAUSE_ITEMS):
                self.draw_option_card(self._menu_rects()[n], it, n == self.sel)
        elif self.state == DEAD:
            ov = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
            ov.fill((20, 0, 0, 190))
            scr.blit(ov, (0, 0))
            st = self.sim.stats
            self.r.text(scr, "HAS CAIDO", (VIEW_W // 2, 110), (230, 70, 70), self.r.menu_title, True)
            rows = ["Oleada alcanzada: %d" % st["waves"], "Enemigos derrotados: %d" % st["kills"],
                    "Disparos: %d" % st["shots"], "Dano recibido: %d" % st["damage_taken"],
                    "Monedas: %d" % st["coins"], "", "Recompensa permanente: +%d" % self.reward]
            for n, l in enumerate(rows):
                self.r.text(scr, l, (VIEW_W // 2, 190 + n * 28), (235, 235, 240), self.r.menu_small, True)
            self.r.text(scr, "Enter para volver al menu", (VIEW_W // 2, VIEW_H - 40), (160, 160, 175), self.r.menu_small, True)
        elif self.state == VICTORY:
            ov = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
            ov.fill((0, 30, 20, 190)); scr.blit(ov, (0, 0))
            st=self.sim.stats
            self.r.text(scr,"VICTORIA",(VIEW_W//2,110),(120,240,180),self.r.big,True)
            rows=["Salas: %d" % st["rooms"],"Enemigos derrotados: %d" % st["kills"],"Disparos: %d" % st["shots"],"Monedas: %d" % st["coins"],"Objetos: %d" % st["items"],"Recompensa permanente: +%d" % self.reward]
            for n,l in enumerate(rows):self.r.text(scr,l,(VIEW_W//2,190+n*28),(235,235,240),self.r.menu_small,True)
            self.r.text(scr,"Enter para volver al menu",(VIEW_W//2,VIEW_H-40),(160,200,175),self.r.menu_small,True)
        elif self.state == CHAR_SELECT:
            self.draw_menu_bg()
            self.r.text(scr, "SELECCION DE PERSONAJE", (VIEW_W//2, 48), (240,190,80), self.r.menu_title, True)
            for n, cid in enumerate(self.char_ids):
                c = self.data.characters[cid]
                selected = n == self.char_sel
                col, row_idx = n % 3, n // 3
                x, y = 20 + col * 310, 108 + row_idx * 184
                card = pygame.Rect(x, y, 300, 174)
                pygame.draw.rect(scr, (10, 13, 23, 225) if selected else (10, 13, 23, 195), card, border_radius=8)
                pygame.draw.rect(scr, (74, 226, 220) if selected else (86, 101, 124), card, 2 if selected else 1, border_radius=8)

                # Retrato amplio, recortado proporcionalmente y centrado en su propio panel.
                portrait = pygame.Rect(x + 10, y + 10, 82, 105)
                # El retrato conserva transparencia real; no se coloca ningún fondo
                # blanco/negro detrás del PNG.
                pygame.draw.rect(scr, (82, 143, 158) if selected else (65, 78, 99), portrait, 1, border_radius=6)
                portrait_key = {"soldier":"kael", "medic":"iria", "vanguard":"rook", "pyromancer":"veyra", "striker":"nox", "engineer":"mira"}.get(cid, cid.lower())
                image = self.character_portraits.get(portrait_key)
                if image:
                    iw, ih = image.get_size()
                    scale = min((portrait.w - 8) / max(1, iw), (portrait.h - 8) / max(1, ih))
                    thumb = pygame.transform.smoothscale(image, (max(1, int(iw * scale)), max(1, int(ih * scale))))
                    scr.blit(thumb, thumb.get_rect(center=portrait.center))
                else:
                    self.r.text(scr, "PNG", portrait.center, (104, 124, 144), self.r.menu_small, True)

                name_panel = pygame.Rect(x + 8, y + 121, 86, 25)
                pygame.draw.rect(scr, (23, 30, 44), name_panel, border_radius=4)
                pygame.draw.rect(scr, (74, 226, 220) if selected else (77, 91, 111), name_panel, 1, border_radius=4)
                name_font = self.r.menu_font if selected else self.r.menu_small
                name = c.name.split(",")[0]
                name_img = name_font.render(name, True, (255, 226, 145) if selected else (196, 207, 222))
                if name_img.get_width() > name_panel.w - 6:
                    name_img = pygame.transform.smoothscale(name_img, (name_panel.w - 6, name_img.get_height()))
                scr.blit(name_img, name_img.get_rect(center=name_panel.center))

                # Panel independiente para la descripción; el texto se ajusta al ancho disponible.
                desc_panel = pygame.Rect(x + 102, y + 10, 188, 154)
                pygame.draw.rect(scr, (7, 10, 19), desc_panel, border_radius=5)
                pygame.draw.rect(scr, (66, 82, 105), desc_panel, 1, border_radius=5)
                description = c.description
                words, lines, current = description.split(), [], ""
                desc_font = self.r.menu_small
                for word in words:
                    candidate = (current + " " + word).strip()
                    if desc_font.size(candidate)[0] > desc_panel.w - 16 and current:
                        lines.append(current); current = word
                    else:
                        current = candidate
                if current: lines.append(current)
                old_clip = scr.get_clip()
                scr.set_clip(desc_panel.inflate(-8, -8))
                for line_i, line in enumerate(lines[:7]):
                    self.r.text(scr, line, (desc_panel.x + 8, desc_panel.y + 12 + line_i * 18), (218, 226, 237) if selected else (173, 188, 204), desc_font)
                scr.set_clip(old_clip)
            c = self.data.characters[self.char_ids[self.char_sel]]
            self.ui_atlas.draw_button(scr, pygame.Rect(16, 488, 150, 34), "Volver", selected=False)
            self.ui_atlas.draw_button(scr, pygame.Rect(VIEW_W - 166, 488, 150, 34), "Mejoras", selected=False)
        elif self.state == SETTINGS:
            self.draw_menu_bg()
            self.r.text(scr, "CONFIGURACION", (VIEW_W // 2, 43), (240, 195, 105), self.r.menu_title, True)
            self.r.text(scr, "AJUSTA TU EQUIPO ANTES DE DESCENDER", (VIEW_W // 2, 78), (157, 190, 198), self.r.menu_small, True)
            settings = self.save.data["settings"]
            v = settings.get("effects_volume", 0.6)
            mv = settings.get("music_volume", 0.6)
            k = settings["keys"]
            sens = float(settings.get("mouse_sensitivity", 1.0))

            # Layout compacto: cada control ocupa su propia fila y no se superponen.
            left_rect = pygame.Rect(112, 112, 294, 330)
            right_rect = pygame.Rect(420, 112, 428, 330)
            for rect in (left_rect, right_rect):
                pygame.draw.rect(scr, (10, 13, 23, 232), rect, border_radius=9)
                pygame.draw.rect(scr, (105, 126, 151, 220), rect, 1, border_radius=9)
            self.r.text(scr, "AUDIO", (left_rect.centerx, 135), (92, 226, 218), self.r.menu_small, True)
            self.r.text(scr, "CONTROLES", (right_rect.centerx, 135), (92, 226, 218), self.r.menu_small, True)

            for idx, (label, value, atlas_label) in enumerate((( "EFECTOS", v, "Sonido"), ("MUSICA", mv, "Musica"))):
                y = 157 + idx * 57
                selected = self.settings_sel == idx
                row_rect = pygame.Rect(126, y, 266, 45)
                if selected:
                    pygame.draw.rect(scr, (20, 35, 45), row_rect, border_radius=6)
                    pygame.draw.rect(scr, (80, 223, 215), row_rect, 1, border_radius=6)
                self.ui_atlas.draw_button(scr, pygame.Rect(132, y + 7, 96, 26), atlas_label, selected=selected)
                self.r.text(scr, "%d%%" % round(value * 100), (374, y + 5), (240, 245, 247) if selected else (174, 191, 204), self.r.menu_small, True)
                bar_rect = pygame.Rect(244, y + 17, 120, 8)
                pygame.draw.rect(scr, (35, 42, 56), bar_rect, border_radius=4)
                fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, int(bar_rect.width * value), bar_rect.height)
                if fill_rect.width:
                    pygame.draw.rect(scr, (73, 221, 211) if selected else (90, 157, 164), fill_rect, border_radius=4)
                pygame.draw.rect(scr, (126, 151, 171), bar_rect, 1, border_radius=4)

            sens_rect = pygame.Rect(126, 257, 266, 74)
            self.r.text(scr, "SENSIBILIDAD MOUSE", (259, 269), (225, 232, 240), self.r.menu_small, True)
            self.r.text(scr, "%.2fx" % sens, (259, 291), (240, 245, 247), self.r.menu_small, True)
            sens_bar = pygame.Rect(145, 307, 228, 8)
            pygame.draw.rect(scr, (35, 42, 56), sens_bar, border_radius=4)
            sens_ratio = max(0.0, min(1.0, (sens - 0.25) / 1.75))
            fill = pygame.Rect(sens_bar.x, sens_bar.y, int(sens_bar.width * sens_ratio), sens_bar.height)
            if fill.width: pygame.draw.rect(scr, (90, 157, 164), fill, border_radius=4)
            pygame.draw.rect(scr, (126, 151, 171), sens_bar, 1, border_radius=4)

            fullscreen = bool(settings.get("fullscreen", False))
            fullscreen_rect = pygame.Rect(126, 338, 266, 32)
            if self.settings_sel == 12:
                pygame.draw.rect(scr, (20, 35, 45), fullscreen_rect, border_radius=6)
                pygame.draw.rect(scr, (80, 223, 215), fullscreen_rect, 1, border_radius=6)
            checkbox = pygame.Rect(139, 345, 18, 18)
            pygame.draw.rect(scr, (12, 16, 25), checkbox, border_radius=3)
            pygame.draw.rect(scr, (80, 223, 215) if self.settings_sel == 12 else (116, 132, 151), checkbox, 1, border_radius=3)
            if fullscreen:
                pygame.draw.line(scr, (105, 235, 180), (143, 330), (148, 334), 2)
                pygame.draw.line(scr, (105, 235, 180), (148, 334), (155, 325), 2)
            self.r.text(scr, "PANTALLA COMPLETA", (259, 354), (225, 232, 240), self.r.menu_small, True)

            reset_rect = pygame.Rect(126, 383, 266, 32)
            self.ui_atlas.draw_button(scr, reset_rect, "Restablecer", selected=self.settings_sel == 13)

            control_items = SETTINGS_ITEMS[3:12]
            for offset, item in enumerate(control_items):
                idx = offset + 3
                y = 153 + offset * 29
                selected = self.settings_sel == idx
                key_name = k[SETTING_KEYS[item]].upper()
                self.draw_option_card((438, y, 392, 26), item, selected, key_name, compact=True, use_atlas=False)

            self.draw_option_card((VIEW_W // 2 - 82, 462, 164, 29), "Volver", self.settings_sel == 14)
            if self.rebind_action:
                self.r.text(scr, "PULSA UNA TECLA PARA ASIGNAR · ESC CANCELA", (VIEW_W // 2, 514), (123, 238, 222), self.r.menu_small, True)
            else:
                pass
        if self.state != PLAY:
            mx, my = mouse
            pygame.draw.circle(scr, (255, 255, 255), (mx, my), 4, 1)

        # Crossfade intro -> menu: la imagen anterior desaparece mientras el
        # menú ya está animándose y la música entra con su propio fade-in.
        if self._intro_transition_surface is not None and self._intro_transition_t > 0.0:
            progress = 1.0 - (self._intro_transition_t / self._intro_transition_duration)
            alpha = max(0, min(255, int(255 * (1.0 - progress))))
            overlay = self._intro_transition_surface.copy()
            overlay.set_alpha(alpha)
            scr.blit(overlay, (0, 0))

        self._present()

    def run(self):
        while self.running:
            dt = self.clock.tick_busy_loop(120) / 1000.0
            self.t += dt
            self.poll()
            if self.state == PLAY:
                self.inp.aim_x, self.inp.aim_y = self.world_mouse()
            self.update(dt)
            self.draw()
        self.save.save()
        self.menu_visuals.close()
        self.intro.close()
        pygame.quit()


if __name__ == "__main__":
    App().run()
    sys.exit(0)