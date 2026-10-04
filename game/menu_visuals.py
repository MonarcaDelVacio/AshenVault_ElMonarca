"""Fondo animado y logo compartidos por las pantallas normales del menú."""
from pathlib import Path

MENU_ASSET_DIR = Path(__file__).resolve().parent.parent / "assets" / "menu"
VIDEO_NAME = "FondoMenuPrincipal.webm"
LOGO_NAME = "AshenVault.png"


class MenuVisuals:
    def __init__(self, size):
        self.width, self.height = size
        self.video_path = MENU_ASSET_DIR / VIDEO_NAME
        self.logo_path = MENU_ASSET_DIR / LOGO_NAME
        self.container = None
        self.video_stream = None
        self.frames = None
        self.frame = None
        self.frame_surface = None
        self.fps = 30.0
        self.accum = 0.0
        self.video_available = False
        self.video_error = None
        self.video_backend = None
        self.logo = None
        self.logo_error = None
        self._try_open_video()
        self._try_load_logo()

    def _try_open_video(self):
        if not self.video_path.is_file():
            self.video_error = f"No existe: {self.video_path}"
            return
        try:
            import av
            container = av.open(str(self.video_path), mode="r")
            stream = next((s for s in container.streams if s.type == "video"), None)
            if stream is None:
                container.close()
                raise RuntimeError("El WebM no contiene una pista de video")
            rate = stream.average_rate or stream.base_rate
            try:
                fps = float(rate) if rate else 30.0
            except Exception:
                fps = 30.0
            if fps != fps or fps <= 0:
                fps = 30.0
            self.container = container
            self.video_stream = stream
            self.frames = container.decode(video=stream.index)
            self.fps = max(1.0, min(fps, 120.0))
            self.video_backend = "pyav"
            if not self._read_frame():
                self._close_video()
                raise RuntimeError("PyAV abrió el WebM pero no pudo leer el primer frame")
            self.video_available = True
            self.video_error = None
        except Exception as exc:
            self._close_video()
            self.video_available = False
            self.video_error = f"PyAV: {exc}"

    def _close_video(self):
        obj = self.container
        self.container = None
        self.video_stream = None
        self.frames = None
        self.video_backend = None
        if obj is not None:
            try:
                obj.close() if hasattr(obj, "close") else obj.release()
            except Exception:
                pass

    def _read_frame(self):
        if self.container is None or self.video_backend != "pyav":
            return False
        try:
            av_frame = next(self.frames)
        except StopIteration:
            try:
                self.container.seek(0, stream=self.video_stream)
                self.frames = self.container.decode(video=self.video_stream.index)
                av_frame = next(self.frames)
            except Exception:
                return False
        except Exception:
            return False
        try:
            self.frame = av_frame.to_ndarray(format="rgb24")
            self.frame_surface = None
            return True
        except Exception:
            return False

    def _try_load_logo(self):
        if not self.logo_path.is_file():
            return
        try:
            import pygame
            self.logo = pygame.image.load(str(self.logo_path)).convert_alpha()
        except Exception as exc:
            self.logo = None
            self.logo_error = str(exc)

    def update(self, dt):
        if not self.video_available:
            return
        self.accum += max(0.0, dt)
        step = 1.0 / self.fps
        reads = min(4, int(self.accum / step))
        if reads <= 0:
            return
        self.accum -= reads * step
        for _ in range(reads):
            if not self._read_frame():
                self.video_available = False
                break

    def draw_background(self, screen):
        """Dibuja solo el fondo animado, reutilizable en todos los menús normales."""
        import pygame
        if self.frame is None:
            screen.fill((12, 10, 18))
            return

        if self.frame_surface is None:
            self.frame_surface = pygame.image.frombuffer(
                self.frame.tobytes(),
                (self.frame.shape[1], self.frame.shape[0]),
                "RGB",
            ).convert()

        sw, sh = self.frame_surface.get_size()
        scale = max(self.width / max(1, sw), self.height / max(1, sh))
        nw = max(1, int(sw * scale))
        nh = max(1, int(sh * scale))
        if (nw, nh) == (sw, sh):
            surf = self.frame_surface
        else:
            surf = pygame.transform.smoothscale(self.frame_surface, (nw, nh))
        x = (self.width - nw) // 2
        y = (self.height - nh) // 2
        screen.blit(surf, (x, y))

    def draw(self, screen):
        """Dibuja fondo + logo para el menú principal."""
        import pygame
        self.draw_background(screen)
        if self.logo is not None:
            max_w = int(self.width * 0.84)
            max_h = int(self.height * 0.34)
            lw, lh = self.logo.get_size()
            scale = min(max_w / max(1, lw), max_h / max(1, lh), 1.0)
            logo = pygame.transform.smoothscale(self.logo, (int(lw * scale), int(lh * scale))) if scale < 0.999 else self.logo
            screen.blit(logo, logo.get_rect(center=(self.width // 2, int(self.height * 0.17))))

    def close(self):
        self._close_video()
