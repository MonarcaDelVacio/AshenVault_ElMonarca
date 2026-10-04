Sprites individuales para paredes, esquinas y columnas del escenario.

Coloca estos PNG en esta carpeta (assets/walls/):
  paredinferior.png
  paredsuperior.png
  paredlateralizquierda.png
  paredlateralderecha.png
  esquinainferiorderecha.png
  esquinainferiorizquierda.png
  esquinasuperiorderecha.png
  esquinasuperiorizquierda.png
  columna.png                 (pilar interior indestructible)
  columnaconantorcha.png      (columna decorativa con luz)

El juego también busca columna.png y columnaconantorcha.png en assets/props/
por compatibilidad, pero si están en assets/walls/ se usan primero.

El juego adapta paredinferior.png a 32x32 (un bloque de alto) y las otras
piezas de pared a 32x64 (dos bloques de alto). Todas ocupan una sola casilla
lógica en el suelo. Las piezas altas se alinean por la base con su casilla
sólida: la parte superior es altura visual, mientras que la colisión queda en
el bloque inferior. Las piezas se seleccionan según la posición del suelo y
se dibujan por delante del jugador cuando este pasa por detrás del muro.
Se recomienda conservar la transparencia.

Si falta alguna textura de pared, se usa el dibujo de respaldo o los atlas
anteriores wall2.png y cobbles2.png, si están presentes.
