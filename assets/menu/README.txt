ASSETS DEL MENU PRINCIPAL

Coloca aqui estos dos archivos con estos nombres exactos:

FondoMenuPrincipal.webm
AshenVault.png

FondoMenuPrincipal.webm
- Se reproduce en bucle como fondo de todas las pantallas del menu (principal, hub, personajes, arsenal, mejoras, estadisticas y configuracion).
- Se adapta al tamaño de la ventana y se recorta al centro sin deformarse.
- El audio del WebM NO se utiliza; la musica del menu sigue siendo MenuPrincipal.
- WebM recomendado: VP8 o VP9, 16:9, 1920x1080 o 1280x720.

AshenVault.png
- Se coloca sobre el video.
- Se recomienda PNG con transparencia (canal alpha).

DEPENDENCIA
- El reproductor usa PyAV/FFmpeg para decodificar el WebM.
- run.bat comprueba e instala automaticamente requirements.txt si faltan pygame o PyAV.
- build_exe.bat incluye assets y PyAV al crear el ejecutable.

El juego puede arrancar aunque los archivos del menu aun no esten presentes: en ese caso se utiliza un fondo oscuro de respaldo.

El menu de pausa es una excepcion: conserva el fondo del mundo de juego con su overlay de pausa.
