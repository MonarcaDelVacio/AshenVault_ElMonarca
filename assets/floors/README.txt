ASHENVAULT - SUPERFICIES DE SUELO

Coloca estos PNG directamente en esta carpeta (assets/floors/):

Superficie_arena.png
Superficie_hierba.png
Superficie_ladrillos.png
Superficie_ladrillosdepiedra.png
Superficie_madera.png
Superficie_roca.png
Superficie_rocanegra.png

Son opcionales. Si alguno falta, el juego utiliza automáticamente los suelos
anteriores (suelo1.png ... suelo11.png). No es necesario cambiar nombres ni
convertir los PNG.

El juego selecciona la superficie por ambiente de la sala:
- bosque: hierba / madera / roca
- ruinas: ladrillos de piedra / roca / ladrillos
- mazmorra: roca / roca negra / ladrillos de piedra
- laboratorio: ladrillos / roca
- volcánico: roca negra / roca / ladrillos
- final: roca negra / ladrillos de piedra / roca

La selección es determinista por sala para evitar cambios visuales aleatorios
al volver a entrar.
