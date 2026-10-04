"""Buffs temporales de estatuas: solo existen durante la run actual."""

STATUE_BUFFS = {
    "statue_goddess": {
        "name": "Bendición de la Guardiana",
        "title": "Piel de mármol",
        "kind": "defense",
        "description": "Reduce el daño que recibes durante esta partida.",
        "base": 0.12,
        "per_difficulty": 0.025,
    },
    "statue_knight": {
        "name": "Juramento del Caballero",
        "title": "Filo cercano",
        "kind": "melee",
        "description": "Aumenta el daño de las armas cuerpo a cuerpo.",
        "base": 0.18,
        "per_difficulty": 0.035,
    },
    "statue_archer": {
        "name": "Ojo del Arquero",
        "title": "Puntería eterna",
        "kind": "ranged",
        "description": "Aumenta el daño de las armas a distancia y mágicas.",
        "base": 0.15,
        "per_difficulty": 0.03,
    },
    "statue_mage": {
        "name": "Pacto del Sabio",
        "title": "Dominio arcano",
        "kind": "ability",
        "description": "Hace más efectivas las habilidades del personaje.",
        "base": 0.18,
        "per_difficulty": 0.035,
    },
    "statue_assassin": {
        "name": "Marca del Asesino",
        "title": "Paso letal",
        "kind": "critical",
        "description": "Aumenta la probabilidad de crítico y el daño crítico.",
        "base": 0.05,
        "per_difficulty": 0.01,
    },
}

STATUE_COST_BASE = 18
STATUE_COST_STEP = 7

def statue_cost(difficulty):
    return STATUE_COST_BASE + max(0, int(difficulty)-1) * STATUE_COST_STEP

def statue_offer(kind, difficulty):
    definition = STATUE_BUFFS[kind]
    difficulty = max(1, int(difficulty))
    value = definition["base"] + definition["per_difficulty"] * (difficulty - 1)
    return {
        "kind": kind, "name": definition["name"], "title": definition["title"],
        "description": definition["description"], "value": value,
        "cost": statue_cost(difficulty), "difficulty": difficulty,
    }
