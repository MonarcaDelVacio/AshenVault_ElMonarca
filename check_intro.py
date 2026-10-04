"""Comprobación previa de la cinemática para run.bat/build_exe.bat."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
VIDEO = ROOT / "assets" / "intro" / "intro.mp4"


def main():
    print("[INTRO] Comprobando dependencias y archivo de video...")
    try:
        import numpy as np  # noqa: F401
        print("[OK] NumPy disponible:", np.__version__)
    except Exception as exc:
        print("[ERROR] NumPy no está disponible:", exc)
        return 1
    try:
        import av
        print("[OK] PyAV:", av.__version__)
    except Exception as exc:
        print("[ERROR] PyAV no está disponible:", exc)
        return 1
    if not VIDEO.is_file():
        print("[ERROR] No existe:", VIDEO)
        return 1
    try:
        container = av.open(str(VIDEO), mode="r")
        try:
            video = next((s for s in container.streams if s.type == "video"), None)
            audio = next((s for s in container.streams if s.type == "audio"), None)
            if video is None:
                print("[ERROR] intro.mp4 no contiene pista de video.")
                return 1
            print(f"[OK] Video: {video.codec_context.width}x{video.codec_context.height}")
            print("[OK] Audio:", "sí" if audio is not None else "no")
            video_decode_index = next(i for i, s in enumerate(container.streams.video) if s is video)
            frame = next(container.decode(video=video_decode_index), None)
            if frame is None:
                print("[ERROR] PyAV abrió el MP4 pero no pudo decodificar el primer frame.")
                return 1
            arr = frame.to_ndarray(format="rgb24")
            if arr.ndim != 3 or arr.shape[2] != 3:
                print("[ERROR] El primer frame no pudo convertirse a RGB.")
                return 1
            print("[OK] Primer frame de video decodificado correctamente.")

            # Importante: container.decode(video=...) y decode(audio=...)
            # reciben el indice DENTRO de su tipo de stream, no el indice global
            # de container.streams. Esto evita el IndexError que aparecia cuando
            # el MP4 tenia audio antes del video (audio=0, video=1).
            if audio is not None:
                audio_decode_index = next(i for i, s in enumerate(container.streams.audio) if s is audio)
                audio_frame = next(container.decode(audio=audio_decode_index), None)
                if audio_frame is None:
                    print("[ERROR] PyAV encontro la pista de audio pero no pudo decodificarla.")
                    return 1
                print("[OK] Primer frame de audio decodificado correctamente.")
        finally:
            container.close()
    except Exception as exc:
        print("[ERROR] No se pudo abrir/decodificar intro.mp4:")
        print("       ", repr(exc))
        return 1
    print("[OK] Intro lista para reproducirse.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
