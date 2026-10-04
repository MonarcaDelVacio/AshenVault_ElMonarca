# Ashen Vault — v8

Roguelike 2D original para PC, construido con Python + pygame-ce. Esta versión amplía la base v7 y corrige las piezas que todavía estaban incompletas: contenido por bioma, secretos destruibles, invocadores, rarezas funcionales, arsenal, fases de jefe, reproducibilidad y empaquetado.

## Contenido actual

- 6 biomas:
  - Ruinas Antiguas
  - Bosque Umbrío
  - Mazmorra Profunda
  - Laboratorio Helix
  - Falla Ígnea
  - Núcleo del Vacío
- 6 jefes, uno por bioma.
- 3 fases por jefe con patrones de ataque diferentes.
- 27 tipos de enemigos.
- Pools de enemigos específicos por bioma.
- 58 armas originales.
- 5 niveles de rareza.
- La rareza modifica daño, cadencia, cargador y/o velocidad de proyectil; además se muestra su efecto en el Arsenal.
- Armas cuerpo a cuerpo con hitbox y arco; pueden interceptar proyectiles únicamente durante la ventana activa del golpe.
- Cofres comunes, raros y legendarios.
- Salas especiales, tiendas, eventos, curación y mini-jefes.
- Sinergias y objetos pasivos.
- Habilidades de personajes.
- Guardado y progresión permanente.
- Música, efectos de sonido, partículas, telegráficos, números de daño y screenshake.

## Correcciones principales de esta versión

### Salas secretas
Las salas secretas son un tipo de habitación independiente dentro de la generación procedural. Al entrar se resuelven como una sala especial y entregan una recompensa de calidad superior. Las antiguas paredes secretas destructibles ya no forman parte del sistema actual.

### Invocadores
El enemigo Tejedor ahora invoca unidades reales durante el combate, con límite de invocaciones activas para evitar crecimiento descontrolado.

### Enemigos por bioma
El generador ya no utiliza indiscriminadamente todos los enemigos. Cada bioma tiene su propio pool de encuentros y todos los identificadores están validados al cargar los datos.

### Arsenal
El juego contiene 58 armas originales distribuidas entre pistolas, subfusiles, rifles, precisión, ametralladoras, lanzadores, magia, especiales, experimentales y melee.

### Rarezas
Las rarezas ya no sólo modifican precios. Las armas reciben modificadores estadísticos según su rareza y muestran el efecto correspondiente en el menú Arsenal.

### Jefes
Las fases ahora pueden cambiar el patrón de proyectiles, incluyendo abanicos, ráfagas, círculos y espirales. Algunos jefes también empiezan a invocar enemigos durante fases avanzadas.

### Reproducibilidad
La simulación utiliza el RNG asociado a la semilla de la run para generación, IA y disparos. Esto permite reproducir el comportamiento de una run con la misma semilla.

### Pooling
Además del object pooling de proyectiles, los enemigos normales derrotados se reutilizan mediante un pool interno para reducir creación y destrucción repetida de objetos.

### Cofres
Los cofres se redujeron visualmente de 128×128 a 44×44 píxeles. Con habitaciones de tiles de 32×32, ocupan aproximadamente 1,38 tiles: poco más de un cuadro, en lugar de dominar la sala.


### Economía y botín

- Las cajas destructibles tienen un 25% de probabilidad total de soltar una recompensa: 12% curación, 8% energía y 5% monedas.
- Los enemigos normales dejan monedas de forma aleatoria; la probabilidad y la cantidad potencial aumentan con su valor de recompensa/dificultad.
- Los jefes y mini-jefes siempre dejan la cantidad de monedas definida para ellos.
- Los esbirros invocados no sueltan monedas ni botín.

## Decoración y NPCs

La generación procedural incluye decoración contextual y determinista: vegetación y rocas en el Bosque Umbrío, estatuas y fuentes en salas especiales, mobiliario y comerciante en tiendas, y decoración más sobria en mazmorras y salas de jefe. Los objetos físicos tienen huella de colisión y reservan espacio durante la generación. El render utiliza profundidad por eje Y: lo que está más arriba queda detrás y lo que está más abajo queda delante.

El comerciante usa sus animaciones de reposo y proximidad, y una mascota decorativa acompaña la tienda sin convertirse en una entidad de combate. Jugador, enemigos y NPC se ordenan con la misma profundidad por Y para que puedan pasar delante o detrás de la decoración.

## Estatuas y bendiciones temporales

Las salas secretas pueden contener una estatua central de uno de cinco tipos: Guardiana, Caballero, Arquero, Sabio o Asesino. Las estatuas son puntos físicos de interés y miden aproximadamente tres veces la altura del personaje jugable.

Al acercarse y pulsar **E**, se abre un menú que pausa la simulación. Cada estatua puede utilizarse una sola vez por partida, cobra monedas y ofrece una bendición temporal. Las variantes escalan con la dificultad de la dungeon: defensa, daño cuerpo a cuerpo, daño a distancia, efectividad de habilidades o crítico. Los buffs viven únicamente en la run actual y no se guardan al terminarla.

## Superficies de suelo

Los nuevos suelos opcionales se colocan directamente en `assets/floors/`: `Superficie_arena.png`, `Superficie_hierba.png`, `Superficie_ladrillos.png`, `Superficie_ladrillosdepiedra.png`, `Superficie_madera.png`, `Superficie_roca.png` y `Superficie_rocanegra.png`. El juego selecciona la superficie de forma determinista según el bioma y el tipo de sala. Si alguno no está presente, se utilizan los suelos antiguos automáticamente.

## Nuevas entidades y efectos

Los nuevos modelos de `assets/enemies/` sustituyen visualmente a varios enemigos existentes sin dibujar simultáneamente el modelo legacy ni su arma visual. Se respetan sus animaciones de movimiento, ataque y muerte cuando están disponibles. Los proyectiles especiales de limo, fantasma y demonios también pueden utilizar sus hojas propias.

Los nuevos efectos incluyen proyectiles tipo flecha, tornado de suelo, explosiones de fuego/agua, gran explosión y rayo descendente. Se usan como telegráficos y efectos de impacto de patrones de jefe, manteniendo límites de cantidad para evitar acumulación excesiva de efectos.

## Cofres

Los cofres funcionales utilizan variantes visuales según la recompensa: verde para comunes, morado para raros/objetos, dorado para legendarios y rojo para armas. Los estados abierto/cerrado se mantienen separados y la interacción sigue siendo la misma.

## Personaje Kael

El sprite sheet de caminar se encuentra en `assets/characters/kael_walk.png` (8 frames de 64×64, fondo transparente). El renderizador lo carga automáticamente y mantiene el arma dibujada por encima del personaje. La dirección visual cambia según el movimiento horizontal.

La habilidad Bastion de Kael puede usar una superposición de escudo de energía en `assets/icons/habilidadescudo.webp`. Las versiones antiguas podían usar `assets/characters/habilidadescudo.webp`; esa copia duplicada ya no se incluye. Si el archivo no está presente o no se puede cargar, el juego sigue funcionando sin el recurso visual.

### Dependencias
Se eliminó OpenCV de las dependencias. El fondo WebM del menú y la cinemática inicial utilizan PyAV/FFmpeg. NumPy es necesaria para convertir los frames de video a RGB y ahora se instala automáticamente.

### Cinemática inicial
Al iniciar el juego aparece primero el splash independiente de AshenVault durante 3 segundos. Después se abre la ventana principal y se reproduce `assets/intro/intro.mp4`. La reproducción usa PyAV directamente, sin VLC ni reproductores externos. El audio del MP4 se prepara en segundo plano y el reloj del video espera a que la pista esté lista para evitar desincronización.

`run.bat` ejecuta una comprobación previa que verifica PyAV, NumPy, la pista de video/audio y la decodificación real del primer frame. Si la comprobación falla, el juego no arranca silenciosamente al menú.

Para saltar la cinemática: **ESC**, **ENTER** o **ESPACIO**.

## Controles

- WASD: movimiento
- Mouse: apuntar
- Click izquierdo: disparar
- Espacio: dash
- Q: habilidad
- R: recargar
- E: interactuar / comprar / recoger
- TAB: cambiar arma
- ESC: pausa / volver

Los controles principales pueden reasignarse desde Configuración.

## Ejecución

Recomendado en Windows:

```text
run.bat
```

O manualmente:

```bash
pip install -r requirements.txt
python main.py
```

## Crear ejecutable

En Windows:

```text
build_exe.bat
```

El script genera `dist\AshenVault.exe` con PyInstaller e incluye `data`, `assets` y PyAV.

## Mantenimiento y verificación

- Suite completa: **181/181 tests OK** en el entorno de desarrollo.
- `py_compile`: OK.
- Validación de contenido: armas, enemigos, biomas, jefes y referencias de sprites/proyectiles.
- Validación de pools de enemigos por bioma e invocaciones.
- Validación de progresión, portales entre dungeons y minimapa.
- Validación de loot y monedas por sala.
- Los drops se corrigen a posiciones seguras dentro de la sala.
- Se eliminaron caches de Python/pruebas y no se incluyen artefactos generados en el paquete fuente.
- La compilación Windows/PyInstaller debe verificarse en Windows.

## Estructura

```text
ashenvault/
├── assets/
├── data/
│   ├── weapons.json
│   ├── enemies.json
│   ├── biomes.json
│   ├── bosses.json
│   └── ...
├── game/
│   ├── abilities.py
│   ├── audio.py
│   ├── bosses.py
│   ├── chests.py
│   ├── data.py
│   ├── enemies.py
│   ├── gen.py
│   ├── items.py
│   ├── menu_visuals.py
│   ├── player.py
│   ├── projectiles.py
│   ├── render.py
│   ├── save.py
│   ├── sim.py
│   ├── weapons.py
│   └── world.py
├── tests/
├── main.py
├── requirements.txt
├── run.bat
├── install_dependencies.bat
└── build_exe.bat
```

## Retratos de selección de personaje

Para mostrar los retratos en el menú **Personajes**, coloca tus archivos PNG en:

`assets/characters/portraits/`

Usa estos nombres exactos: `Kael.png`, `Iria.png`, `Rook.png`, `Veyra.png`, `Nox.png` y `Mira.png`.
Los PNG pueden tener fondo transparente; el juego los adapta al recuadro automáticamente.
Si todavía no copiaste alguno, el juego seguirá funcionando y mostrará el marco vacío.

Los menús se pueden navegar tanto con teclado como con mouse. En Configuración, haz clic sobre
la barra para ajustar el volumen, o sobre una fila de controles para reasignar la tecla.


## Sprites de armas, proyectiles y consumibles

- Los sprites de las 58 armas están en `assets/weapons/`, separados por categoría.
- Cada definición de `data/weapons.json` incluye `weapon_sprite`; las armas a distancia también incluyen `projectile_sprite`.
- Las armas equipadas giran hacia el cursor y se dibujan por encima del personaje; los sprites originales se mantienen orientados hacia la derecha como referencia.
- Los proyectiles del jugador usan el sprite asignado a su arma. Los proyectiles de enemigos usan una variante visual según su tipo de daño.
- Las armas recogibles y las ofertas de armas en la tienda muestran su miniatura.
- `assets/misc/healing.png` y `assets/misc/energy.png` se utilizan en las ofertas de cura y batería de energía de la tienda.
- Los proyectiles y sprites se cargan desde PNG con transparencia; no requieren conversión adicional.

## Ajustes recientes de armas

- Los sprites de las armas se espejan horizontalmente al apuntar hacia la izquierda para mantener la empuñadura y la boca del arma en la orientación correcta.
- `Escopeta Zarza` usa el sprite `rifle1.png` y dispara 7 perdigones con dispersión; `Rifle de Espinas` usa `rifle6.png` para no reutilizar el sprite de escopeta.
- `Lanza del Vigía`, `Lanza Lunar` y `Arco Lumen` se cargan manteniendo el clic izquierdo, hasta un máximo de 3 segundos. Al soltar, lanzan un proyectil cuyo daño, velocidad y alcance escalan con la carga.
- Las armas de la categoría lanzador detonan al impactar y dañan enemigos cercanos en un radio aproximado de 3×3 casillas. Los impactos usan la animación de explosión integrada cuando corresponde.

## Sprites de cajas y barriles

Las cajas destructibles se escalan a 32×32 y bloquean el movimiento mientras están intactas.
Se generan en grupos cortos de 2–3 cajas para crear obstáculos rompibles. Las puertas se
desbloquean al limpiar la sala; al acercarse a una puerta abierta se cambia de sala
automáticamente, con una flecha blanca que indica la salida.

Para usar los PNG personalizados de objetos destructibles, colócalos en `assets/props/` con estos nombres exactos (respeta la ortografía):

- `caja.png` — caja intacta.
- `cajarota.png` — caja rota, visible mientras se desvanece.
- `barriligneo.png` — barril ígneo intacto.
- `barrilveneno.png` — barril venenoso intacto.
- `barrilelectrico.png` — barril eléctrico intacto.
- `barrilroto.png` — barril roto, visible mientras se desvanece.

Los sprites se escalan automáticamente a 48 × 48 píxeles (1,5 casillas del juego). Si falta un archivo o no se puede cargar, el juego dibuja un gráfico provisional para ese objeto. No hace falta modificar el código ni instalar nada adicional.

### Monedas animadas

Coloca los cinco fotogramas de la moneda en `assets/props/` con estos nombres exactos: `moneda1.png`, `moneda2.png`, `moneda3.png`, `moneda4.png` y `moneda5.png`. El juego los escala a 22×22 píxeles y los anima a 8 fotogramas por segundo, con un pequeño movimiento vertical. Si faltan los PNG, se mantiene una moneda dibujada por el juego como respaldo.

## Sprites de escenarios personalizados

El renderizador busca las texturas de escenario en `assets/floors/` y `assets/walls/` (los nombres deben respetarse):

```text
assets/
├── floors/
│   ├── suelo1.png
│   ├── suelo2.png
│   ├── suelo3.png
│   ├── suelo4.png
│   ├── suelo5.png
│   ├── suelo6.png
│   ├── suelo7.png
│   ├── suelo8.png
│   ├── suelo9.png
│   ├── suelo10.png
│   └── suelo11.png
├── walls/
│   ├── paredinferior.png
│   ├── paredsuperior.png
│   ├── paredlateralizquierda.png
│   ├── paredlateralderecha.png
│   ├── esquinainferiorderecha.png
│   ├── esquinainferiorizquierda.png
│   ├── esquinasuperiorderecha.png
│   ├── esquinasuperiorizquierda.png
│   ├── columna.png
│   ├── columnaconantorcha.png
│   ├── wall2.png (opcional, compatibilidad anterior)
│   └── cobbles2.png (opcional, compatibilidad anterior)
└── props/
```

Cada sala elige una única superficie de suelo según su ambiente y tipo. Esa superficie se repite en toda la sala; nunca se combinan dos superficies dentro de una misma sala. Los PNG nuevos se escalan a 32×32. Si falta un PNG nuevo, se usa una única textura antigua de respaldo para esa sala. Los ocho PNG de pared se colocan en `assets/walls/`: `paredinferior.png` se adapta a 32×32 (un bloque de alto), mientras que las otras paredes y esquinas se adaptan a 32×64. Todas ocupan una sola casilla en el suelo. El juego decide qué borde o esquina usar según la posición del suelo y ancla las piezas altas por su base a la casilla sólida; así la mitad superior aporta altura visual y la colisión corresponde al bloque inferior. Las dibuja en una pasada aparte para que no las tape el suelo. Los soportes interiores del techo se generan en patrones arquitectónicos simétricos en vez de posiciones aleatorias: las salas de combate tienen seis soportes y las salas especiales cuatro. Los pilares con antorcha son también casillas sólidas (`TORCH_PILLAR`): usan `columnaconantorcha.png`, bloquean el paso por la casilla inferior y emiten luz desde la llama. Los pilares normales (`PILLAR`) usan `columna.png`. Ambos PNG se buscan primero en `assets/walls/` y después en `assets/props/` por compatibilidad. Ambas columnas se adaptan a 32×64, con la base alineada a la casilla sólida inferior. La luz del jugador se compone después de las demás fuentes de luz para mantener su brillo visual por encima de las luces del escenario. Cuando el jugador pasa por detrás de un muro o columna, se dibuja una pasada de primer plano para que la estructura lo oculte parcialmente y dé sensación de altura. Los sprites individuales tienen prioridad; si faltan, el juego conserva los gráficos de respaldo y los atlas antiguos siguen siendo compatibles. Se recomienda transparencia en todos los PNG.

## Selección de personaje

La opción **Personajes** ya no aparece en el menú principal. Al elegir **Jugar**, primero se abre la selección de personaje; al confirmar, comienza la partida con el personaje elegido. La selección desde el menú de mejoras sigue disponible.


## Nuevos recursos de dungeon

Coloca los seis frames del portal en `assets/portal/`: `portalframe1.png` a `portalframe6.png`. El juego los carga de forma opcional y los anima en la sala final.

La tecla `M` abre el mapa ampliado; puede reasignarse desde Configuracion > Minimapa.

## Intro de inicio

La presentacion inicial usa `assets/intro/intro.mp4`. Al arrancar se muestra brevemente `assets/icons/AshenVaultIcon.png` centrado sobre fondo negro, despues se reproduce el MP4 y finalmente entra el menu principal con `MenuPrincipal.ogg` mediante un fundido suave. Si el MP4 no esta presente, el juego continua directamente al menu.

La intro puede saltarse con `Esc`, `Enter` o `Espacio`.
