"""Pure validation helpers for AshenVault's JSON data graph.

The validator checks cross-file references without importing pygame or constructing
runtime entities. It is intentionally stricter than JSON parsing while avoiding
gameplay-specific balance rules.
"""


def _ref_errors(container_name, container, known, field):
    errors = []
    for ident, raw in container.items():
        value = raw.get(field)
        if value is not None and value not in known:
            errors.append(f"{container_name} {ident}: referencia desconocida {field}={value}")
    return errors


def _require_mapping(data, name, errors, *, allow_empty=False):
    value = data.get(name)
    if not isinstance(value, dict):
        errors.append(f"{name}: debe ser un objeto JSON")
        return {}
    if not allow_empty and not value:
        errors.append(f"{name}: conjunto vacío")
    return value


def _require_id_map(container_name, container, errors):
    for ident, raw in container.items():
        if not isinstance(ident, str) or not ident:
            errors.append(f"{container_name}: identificador inválido")
        if not isinstance(raw, dict):
            errors.append(f"{container_name} {ident}: entrada debe ser un objeto JSON")


def _require_non_negative_number(container_name, ident, raw, field, errors):
    value = raw.get(field)
    if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0):
        errors.append(f"{container_name} {ident}: {field} inválido")


def validate_data_graph(data):
    """Return deterministic validation errors for the loaded JSON graph.

    Phase 11 validation covers the complete declarative data graph. It checks
    structure and cross-file references, but deliberately does not enforce
    gameplay balance values.
    """
    errors = []

    weapons = _require_mapping(data, "weapons", errors)
    enemies = _require_mapping(data, "enemies", errors)
    characters = _require_mapping(data, "characters", errors)
    bosses = _require_mapping(data, "bosses", errors)
    biomes = _require_mapping(data, "biomes", errors)
    enemy_variants = data.get("enemy_variants", {})
    if not isinstance(enemy_variants, dict):
        errors.append("enemy_variants: debe ser un objeto JSON")
        enemy_variants = {}
    biome_bosses = _require_mapping(data, "biome_bosses", errors)
    arenas = _require_mapping(data, "arenas", errors, allow_empty=True)
    rooms = _require_mapping(data, "rooms", errors, allow_empty=True)
    chests = _require_mapping(data, "chests", errors, allow_empty=True)
    items = _require_mapping(data, "items", errors, allow_empty=True)
    modifiers = _require_mapping(data, "modifiers", errors, allow_empty=True)
    synergies = _require_mapping(data, "synergies", errors, allow_empty=True)
    shops = data.get("shops")
    if not isinstance(shops, dict):
        errors.append("shops: debe ser un objeto JSON")
        shops = {}

    for name, container in (
        ("weapons", weapons), ("enemies", enemies), ("characters", characters),
        ("bosses", bosses), ("biomes", biomes),
        ("arenas", arenas), ("rooms", rooms), ("chests", chests),
        ("items", items), ("modifiers", modifiers), ("synergies", synergies),
    ):
        _require_id_map(name, container, errors)

    errors.extend(_ref_errors("personaje", characters, weapons, "start_weapon"))
    errors.extend(_ref_errors("enemigo", enemies, weapons, "weapon_id"))

    for ident, raw in enemies.items():
        if not isinstance(raw, dict):
            continue
        sprite_set = raw.get("sprite_set")
        if sprite_set is not None and not isinstance(sprite_set, str):
            errors.append(f"enemigo {ident}: sprite_set inválido")
        if sprite_set is None:
            errors.append(f"enemigo {ident}: falta sprite_set")
        summon_ids = raw.get("summon_ids", [])
        if summon_ids is not None and not isinstance(summon_ids, list):
            errors.append(f"enemigo {ident}: summon_ids inválido")
        for target in summon_ids or []:
            if target not in enemies:
                errors.append(f"enemigo {ident}: referencia desconocida summon_ids={target}")

    for ident, raw in bosses.items():
        if not isinstance(raw, dict):
            continue
        sprite_set = raw.get("sprite_set")
        if not isinstance(sprite_set, str) or not sprite_set:
            errors.append(f"jefe {ident}: falta sprite_set")
        summon_ids = raw.get("summon_ids", [])
        if summon_ids is not None and not isinstance(summon_ids, list):
            errors.append(f"jefe {ident}: summon_ids inválido")
        for target in summon_ids or []:
            if target not in enemies:
                errors.append(f"jefe {ident}: referencia desconocida summon_ids={target}")
        phases = raw.get("phases", [])
        if phases is not None and not isinstance(phases, list):
            errors.append(f"jefe {ident}: phases inválido")
            phases = []
        for phase_index, phase in enumerate(phases):
            if not isinstance(phase, dict):
                errors.append(f"jefe {ident}: fase {phase_index} inválida")
                continue
            phase_summons = phase.get("summon_ids", [])
            if phase_summons is not None and not isinstance(phase_summons, list):
                errors.append(f"jefe {ident}: fase {phase_index} summon_ids inválido")
                phase_summons = []
            for target in phase_summons or []:
                if target not in enemies:
                    errors.append(
                        f"jefe {ident}: fase {phase_index} referencia desconocida summon_ids={target}"
                    )

    if enemy_variants:
        families = enemy_variants.get("families")
        if not isinstance(families, dict):
            errors.append("enemy_variants: families inválido")
        else:
            for family_id, variants in families.items():
                if not isinstance(variants, list):
                    errors.append(f"enemy_variants {family_id}: familia inválida")
                    continue
                seen = set()
                for index, variant in enumerate(variants):
                    if not isinstance(variant, dict):
                        errors.append(f"enemy_variants {family_id}[{index}]: entrada inválida")
                        continue
                    variant_id = variant.get("id")
                    if not isinstance(variant_id, str) or not variant_id:
                        errors.append(f"enemy_variants {family_id}[{index}]: falta id")
                    elif variant_id in seen:
                        errors.append(f"enemy_variants {family_id}: id duplicado {variant_id}")
                    seen.add(variant_id)
                    for field in ("damage_mult", "hp_mult", "speed_mult", "projectile_speed_mult", "projectile_visual_scale", "explosion_radius"):
                        _require_non_negative_number("enemy_variants", f"{family_id}[{index}]", variant, field, errors)
                    asset = variant.get("projectile_asset_sheet")
                    if asset is not None and (not isinstance(asset, str) or not asset):
                        errors.append(f"enemy_variants {family_id}[{index}]: projectile_asset_sheet inválido")

    for biome_id, biome in biomes.items():
        if not isinstance(biome, dict):
            continue
        pool = biome.get("enemy_pool", [])
        if not isinstance(pool, list):
            errors.append(f"bioma {biome_id}: enemy_pool inválido")
            continue
        for enemy_id in pool:
            if enemy_id not in enemies:
                errors.append(f"bioma {biome_id}: enemigo desconocido enemy_pool={enemy_id}")

    for biome_id, boss_id in biome_bosses.items():
        if biome_id not in biomes:
            errors.append(f"biome_bosses: bioma desconocido {biome_id}")
        if boss_id not in bosses:
            errors.append(f"biome_bosses: jefe desconocido {biome_id}:{boss_id}")

    for arena_id, arena in arenas.items():
        if not isinstance(arena, dict):
            continue
        biome = arena.get("biome")
        if biome is not None and biome not in biomes:
            errors.append(f"arena {arena_id}: bioma desconocido {biome}")
        for field in ("cols", "rows"):
            value = arena.get(field)
            if value is not None and (not isinstance(value, int) or value < 1):
                errors.append(f"arena {arena_id}: {field} inválido")

    for room_id, room in rooms.items():
        if not isinstance(room, dict):
            continue
        budget = room.get("enemy_budget")
        if budget is not None and (not isinstance(budget, (int, float)) or isinstance(budget, bool) or budget < 0):
            errors.append(f"sala {room_id}: enemy_budget inválido")

    for chest_id, chest in chests.items():
        if not isinstance(chest, dict):
            continue
        if not isinstance(chest.get("rarity"), str) or not chest.get("rarity"):
            errors.append(f"cofre {chest_id}: falta rarity")
        _require_non_negative_number("cofre", chest_id, chest, "key_cost", errors)

    for container_name, container in (("item", items), ("modifier", modifiers)):
        for ident, raw in container.items():
            if not isinstance(raw, dict):
                continue
            effects = raw.get("effects")
            if effects is not None and not isinstance(effects, dict):
                errors.append(f"{container_name} {ident}: effects inválido")

    known_upgrades = set(items) | set(modifiers)
    for ident, raw in synergies.items():
        if not isinstance(raw, dict):
            continue
        requires = raw.get("requires", [])
        if not isinstance(requires, list):
            errors.append(f"sinergia {ident}: requires inválido")
            continue
        for requirement in requires:
            if requirement not in known_upgrades:
                errors.append(f"sinergia {ident}: requisito desconocido requires={requirement}")
        effects = raw.get("effects")
        if effects is not None and not isinstance(effects, dict):
            errors.append(f"sinergia {ident}: effects inválido")

    if "weapon_prices" in shops and not isinstance(shops["weapon_prices"], dict):
        errors.append("shops: weapon_prices inválido")
    if "items" in shops:
        if not isinstance(shops["items"], list):
            errors.append("shops: items inválido")
        else:
            for index, item in enumerate(shops["items"]):
                if not isinstance(item, dict):
                    errors.append(f"shops: item {index} inválido")
                    continue
                _require_non_negative_number("shop", index, item, "price", errors)
                _require_non_negative_number("shop", index, item, "amount", errors)
    if "slots" in shops and (not isinstance(shops["slots"], int) or shops["slots"] < 1):
        errors.append("shops: slots inválido")

    for ident, raw in characters.items():
        if not isinstance(raw, dict):
            continue
        ability = raw.get("ability")
        if ability is not None and not isinstance(ability, dict):
            errors.append(f"personaje {ident}: ability inválida")
        dash = raw.get("dash")
        if dash is not None and not isinstance(dash, dict):
            errors.append(f"personaje {ident}: dash inválido")

    for ident, raw in weapons.items():
        if not isinstance(raw, dict):
            continue
        weapon_class = raw.get("class")
        if not isinstance(weapon_class, str) or not weapon_class:
            errors.append(f"arma {ident}: falta class")
        if weapon_class != "melee" and not raw.get("projectile_sprite"):
            errors.append(f"arma {ident}: falta projectile_sprite")
        _require_non_negative_number("arma", ident, raw, "magazine", errors)
        _require_non_negative_number("arma", ident, raw, "fire_interval", errors)
        if isinstance(raw.get("magazine"), (int, float)) and raw.get("magazine", 1) < 1:
            errors.append(f"arma {ident}: magazine inválido")

    return errors
