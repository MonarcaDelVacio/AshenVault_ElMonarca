"""Reproductor de la cinemática inicial de AshenVault.

La intro se reproduce con PyAV para mantener el proyecto independiente de
reproductores externos. Si el MP4 contiene audio, se extrae a WAV temporal y
se reproduce con pygame.mixer mientras los frames de video se presentan.
"""
from pathlib import Path
import tempfile
import wave
import threading

# NumPy es necesaria para convertir los frames de PyAV a superficies de Pygame.
# Se importa explícitamente para que PyInstaller también la incluya en el EXE.
import numpy as np


class IntroPlayer:
    def __init__(self, size, video_path=None, icon_path=None, music_volume=1.0):
        self.width, self.height = size
        root = Path(__file__).resolve().parent.parent
        self.video_path = Path(video_path) if video_path else root / "assets" / "intro" / "intro.mp4"
        self.icon_path = Path(icon_path) if icon_path else root / "assets" / "icons" / "AshenVaultIcon.png"
        self.music_volume = max(0.0, min(1.0, float(music_volume)))

        self.phase = "video"
        self.elapsed = 0.0
        self.done = False
        self.available = self.video_path.is_file()
        self.video_error = None
        self.error_mode = False
        self.audio_error = None

        self.container = None
        self.video_stream = None
        self.frames = None
        self.frame = None
        self.frame_surface = None
        self.fps = 30.0
        self.video_time = 0.0
        self.frame_index = -1
        self.duration = None
        self.audio_temp_path = None
        self.has_audio = False
        self.playback_started = False
        self._closed = False
        self.audio_started = False
        self._audio_loading = False
        self._audio_ready = False
        self._audio_thread = None
        self._prepared = False

        self.icon = None
        self._load_icon()
        if self.available:
            self._open_video()
            if self.available:
                # Nunca bloqueamos el primer frame esperando la extracción de audio.
                # El video comienza inmediatamente y el WAV se prepara en segundo plano.
                self._prepare_audio()

        # Si todavía no existe el MP4, no bloqueamos el juego en la pantalla de intro.
        if not self.available:
            self.video_error = self.video_error or f"No se encontró la intro: {self.video_path}"
            # No entramos silenciosamente al menú: dejamos una pantalla de error
            # saltables para que el problema sea visible y diagnosticable.
            self.error_mode = True

    def _load_icon(self):
        try:
            import pygame
            if self.icon_path.is_file():
                self.icon = pygame.image.load(str(self.icon_path)).convert_alpha()
        except Exception:
            self.icon = None

    def _open_video(self):
        try:
            import av
            self.container = av.open(str(self.video_path), mode="r")
            self.video_stream = next((s for s in self.container.streams if s.type == "video"), None)
            self.has_audio = any(s.type == "audio" for s in self.container.streams)
            if self.video_stream is None:
                raise RuntimeError("El MP4 no contiene una pista de video")

            rate = self.video_stream.average_rate or self.video_stream.base_rate
            try:
                fps = float(rate) if rate else 30.0
            except Exception:
                fps = 30.0
            if fps != fps or fps <= 0:
                fps = 30.0
            self.fps = max(1.0, min(fps, 120.0))

            if self.video_stream.duration and self.video_stream.time_base:
                self.duration = float(self.video_stream.duration * self.video_stream.time_base)

            self._video_decode_index = next(i for i, s in enumerate(self.container.streams.video) if s is self.video_stream)
            self.frames = self.container.decode(video=self._video_decode_index)
            if not self._read_frame():
                raise RuntimeError("No se pudo leer el primer frame del MP4")
            self.video_error = None
        except Exception as exc:
            self.video_error = str(exc)
            self.available = False
            self._close_video()
            self.error_mode = True

    def _read_frame(self):
        if self.container is None or self.video_stream is None:
            return False
        try:
            av_frame = next(self.frames)
        except StopIteration:
            return False
        except Exception as exc:
            self.video_error = str(exc)
            return False
        try:
            self.frame = av_frame.to_ndarray(format="rgb24")
            self.frame_surface = None
            self.frame_index += 1
            # Algunos MP4/H.264 entregan frames sin timestamp utilizable en
            # determinadas versiones de PyAV. En ese caso usamos PTS y, como
            # último recurso, el índice del frame/FPS para mantener el reloj.
            timestamp = getattr(av_frame, "time", None)
            if timestamp is None:
                pts = getattr(av_frame, "pts", None)
                time_base = getattr(av_frame, "time_base", None) or getattr(self.video_stream, "time_base", None)
                if pts is not None and time_base is not None:
                    timestamp = float(pts * time_base)
            if timestamp is None:
                timestamp = self.frame_index / max(1.0, self.fps)
            self.video_time = float(timestamp)
            return True
        except Exception as exc:
            self.video_error = str(exc)
            return False

    @staticmethod
    def _resampled_frames(resampler, frame):
        """Normaliza las variantes de retorno de AudioResampler entre PyAV 14-16."""
        result = resampler.resample(frame)
        if result is None:
            return []
        if isinstance(result, (list, tuple)):
            return result
        return [result]

    def _extract_audio(self):
        """Extrae la pista de audio a WAV temporal para pygame.mixer.music."""
        if not self.video_path.is_file():
            return None
        container = None
        try:
            import av
            # Usa un contenedor independiente para no alterar el demuxer del video.
            container = av.open(str(self.video_path), mode="r")
            audio_stream = next((s for s in container.streams if s.type == "audio"), None)
            if audio_stream is None:
                return None

            resampler = av.audio.resampler.AudioResampler(format="s16", layout="stereo", rate=44100)
            pcm = bytearray()
            audio_decode_index = next(i for i, s in enumerate(container.streams.audio) if s is audio_stream)
            for frame in container.decode(audio=audio_decode_index):
                for out in self._resampled_frames(resampler, frame):
                    pcm.extend(out.to_ndarray().tobytes())
            for out in self._resampled_frames(resampler, None):
                pcm.extend(out.to_ndarray().tobytes())
            if not pcm:
                return None

            tmp = tempfile.NamedTemporaryFile(prefix="ashenvault_intro_", suffix=".wav", delete=False)
            tmp_path = Path(tmp.name)
            tmp.close()
            with wave.open(str(tmp_path), "wb") as wav:
                wav.setnchannels(2)
                wav.setsampwidth(2)
                wav.setframerate(44100)
                wav.writeframes(bytes(pcm))
            self.audio_temp_path = tmp_path
            return tmp_path
        except Exception as exc:
            self.audio_error = str(exc)
            return None
        finally:
            if container is not None:
                try:
                    container.close()
                except Exception:
                    pass

    def _prepare_audio(self):
        if self.audio_started or self.container is None:
            return
        self.audio_started = True
        self._audio_loading = True
        self._audio_thread = threading.Thread(target=self._extract_audio_worker, daemon=True)
        self._audio_thread.start()

    def _extract_audio_worker(self):
        audio_path = self._extract_audio()
        if audio_path is not None:
            if self._closed:
                try:
                    audio_path.unlink(missing_ok=True)
                except Exception:
                    pass
            else:
                self.audio_temp_path = audio_path
                self._audio_ready = True
        else:
            # Un fallo de extracción no debe dejar el video congelado para siempre.
            self.playback_started = True
        self._audio_loading = False

    def _start_ready_audio(self):
        if not self._audio_ready or self.audio_temp_path is None:
            return False
        try:
            import pygame
            if not pygame.mixer.get_init():
                self.audio_error = "El mezclador de audio de Pygame no está inicializado"
                return False
            pygame.mixer.music.load(str(self.audio_temp_path))
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play()
            self.playback_started = True
            return True
        except Exception as exc:
            self.audio_error = str(exc)
            # Si el audio no puede reproducirse, el video sigue; no bloqueamos
            # toda la cinemática por una pista de audio defectuosa.
            self.playback_started = True
            return False
        finally:
            self._audio_ready = False

    def start_video(self):
        if self.done or not self.available:
            return
        self.phase = "video"
        self.elapsed = 0.0
        self.video_time = 0.0
        self.frame_index = -1
        self.playback_started = False
        # Reopen so audio decoding does not disturb the video decoder state.
        try:
            self._close_video()
            self._open_video()
            if self.available:
                self._prepare_audio()
        except Exception as exc:
            self.video_error = str(exc)
            self.done = True

    def update(self, dt):
        if self.done:
            return
        if self.error_mode:
            return
        dt = max(0.0, min(float(dt), 0.1))
        if self.phase != "video":
            return

        # Si existe audio, no hacemos avanzar el reloj del video hasta tenerlo
        # listo. Así evitamos que una extracción lenta desincronice imagen y sonido.
        if self.has_audio and not self.playback_started:
            self._start_ready_audio()
            if not self.playback_started:
                return

        self.elapsed += dt

        # Presentar el frame cuyo timestamp corresponde al tiempo transcurrido.
        target = self.elapsed
        reads = 0
        while self.frame is not None and self.video_time < target and reads < 8:
            if not self._read_frame():
                self.done = True
                self._stop_audio()
                break
            reads += 1

        # La finalización se determina al agotar el decodificador, no por la
        # duración declarada en el contenedor (algunos MP4 reportan una duración
        # distinta a la pista y eso podía cortar la cinemática prematuramente).

    def draw(self, screen):
        import pygame
        screen.fill((0, 0, 0))
        if self.error_mode:
            font = pygame.font.Font(None, 30)
            small = pygame.font.Font(None, 22)
            title = font.render("No se pudo reproducir la intro", True, (235, 235, 235))
            screen.blit(title, title.get_rect(center=(self.width // 2, self.height // 2 - 42)))
            message = (self.video_error or "Error desconocido").replace("\n", " ")
            if len(message) > 110:
                message = message[:107] + "..."
            detail = small.render(message, True, (190, 190, 190))
            screen.blit(detail, detail.get_rect(center=(self.width // 2, self.height // 2)))
            hint = small.render("Pulsa ESC, ENTER o ESPACIO para continuar", True, (150, 220, 210))
            screen.blit(hint, hint.get_rect(center=(self.width // 2, self.height // 2 + 42)))
            return
        if self.frame is None:
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
        surf = self.frame_surface if (nw, nh) == (sw, sh) else pygame.transform.smoothscale(self.frame_surface, (nw, nh))
        x = (self.width - nw) // 2
        y = (self.height - nh) // 2
        screen.blit(surf, (x, y))

    def skip(self):
        self.done = True
        self._stop_audio()

    def _stop_audio(self):
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

    def _close_video(self):
        obj = self.container
        self.container = None
        self.video_stream = None
        self.frames = None
        self.frame = None
        self.frame_surface = None
        if obj is not None:
            try:
                obj.close()
            except Exception:
                pass

    def close(self):
        self._closed = True
        self._stop_audio()
        if self._audio_thread is not None and self._audio_thread.is_alive():
            self._audio_thread.join(timeout=0.75)
        self._close_video()
        if self.audio_temp_path is not None:
            try:
                self.audio_temp_path.unlink(missing_ok=True)
            except Exception:
                pass
            self.audio_temp_path = None
