"""Pure UI state constants shared by the application shell.

This module deliberately contains no pygame dependency. It centralizes the
state identifiers and menu/configuration definitions so main.py remains the
presentation/state-machine facade.
"""

INTRO, MENU, PLAY, PAUSE, MAP, DEAD, VICTORY, SCORE, SETTINGS, CHAR_SELECT, HUB, STATUE = (
    "intro", "menu", "play", "pause", "map", "dead", "victory", "score",
    "settings", "char_select", "hub", "statue"
)

MENU_ITEMS = ["Jugar", "Configuracion", "Salir"]
PAUSE_ITEMS = ["Continuar", "Configuracion", "Reiniciar run", "Salir al menu"]
SETTINGS_ITEMS = [
    "Volumen efectos", "Volumen musica", "Sensibilidad mouse",
    "Mover arriba", "Mover abajo", "Mover izquierda", "Mover derecha",
    "Dash", "Habilidad", "Recargar", "Pausa", "Minimapa",
    "Pantalla completa", "Restablecer", "Volver",
]
SETTING_KEYS = {
    "Mover arriba": "up",
    "Mover abajo": "down",
    "Mover izquierda": "left",
    "Mover derecha": "right",
    "Dash": "dash",
    "Habilidad": "ability",
    "Recargar": "reload",
    "Pausa": "pause",
    "Minimapa": "map",
}
HUB_ITEMS = ["Iniciar run", "Personajes", "Mejoras", "Volver al menu"]
