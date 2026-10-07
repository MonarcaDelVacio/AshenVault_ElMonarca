"""Pure validation helpers for AshenVault's JSON data graph.

The validator checks cross-file references without importing pygame or constructing
runtime entities.  It is intentionally stricter than JSON parsing while avoiding
gameplay-specific balance rules.
"""

def _ref_errors(container_name, container, known, field):
    errors = []
    for ident, raw in container.items():
        value = raw.get(field)
        if value is not None and value not in known:
            errors.append(f"{container_name} {ident}: referencia desconocida {field}={value}")
    return errors


def validate_data_graph(data):
    """Return deterministic validation errors for the loaded JSON graph."""
    errors = []
    weapons = data.get("weapons", {})
    enemies = data.get("enemies", {})
    characters = data.get("characters", {})
    bosses = data.get("bosses", {})
    biomes = data.get("biomes", {})
    biome_bosses = data.get("biome_bosses", {})

    if not weapons:
        errors.append("weapons: conjunto vacío")
    if not characters:
        errors.append("characters: conjunto vacío")
    if not enemies:
        errors.append("enemies: conjunto vacío")
    if not bosses:
        errors.append("bosses: conjunto vacío")

    errors.extend(_ref_errors("personaje", characters, weapons, "start_weapon"))
    errors.extend(_ref_errors("enemigo", enemies, weapons, "weapon_id"))

    for ident, raw in enemies.items():
        if raw.get("sprite_set") is not None and not isinstance(raw.get("sprite_set"), str):
            errors.append(f"enemigo {ident}: sprite_set inválido")
        for field in ("summon_ids",):
            for target in raw.get(field, []) or []:
                if target not in enemies:
                    errors.append(f"enemigo {ident}: referencia desconocida {field}={target}")

    for ident, raw in bosses.items():
        sprite_set = raw.get("sprite_set")
        if not isinstance(sprite_set, str) or not sprite_set:
            errors.append(f"jefe {ident}: falta sprite_set")
        for target in raw.get("summon_ids", []) or []:
            if target not in enemies:
                errors.append(f"jefe {ident}: referencia desconocida summon_ids={target}")
        for phase_index, phase in enumerate(raw.get("phases", []) or []):
            for target in phase.get("summon_ids", []) or []:
                if target not in enemies:
                    errors.append(
                        f"jefe {ident}: fase {phase_index} referencia desconocida summon_ids={target}"
                    )

    for biome_id, biome in biomes.items():
        for enemy_id in biome.get("enemy_pool", []) or []:
            if enemy_id not in enemies:
                errors.append(f"bioma {biome_id}: enemigo desconocido enemy_pool={enemy_id}")

    for biome_id, boss_id in biome_bosses.items():
        if biome_id not in biomes:
            errors.append(f"biome_bosses: bioma desconocido {biome_id}")
        if boss_id not in bosses:
            errors.append(f"biome_bosses: jefe desconocido {biome_id}:{boss_id}")

    for ident, raw in weapons.items():
        weapon_class = raw.get("class")
        if not isinstance(weapon_class, str) or not weapon_class:
            errors.append(f"arma {ident}: falta class")
        if weapon_class != "melee" and not raw.get("projectile_sprite"):
            errors.append(f"arma {ident}: falta projectile_sprite")
        if raw.get("magazine", 1) < 1:
            errors.append(f"arma {ident}: magazine inválido")
        if raw.get("fire_interval", 0) < 0:
            errors.append(f"arma {ident}: fire_interval inválido")

    return errors
