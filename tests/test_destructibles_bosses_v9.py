import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_all_melee_enemies_have_melee_weapon_assets():
    enemies=json.loads((ROOT/'data'/'enemies.json').read_text(encoding='utf-8'))
    weapons=json.loads((ROOT/'data'/'weapons.json').read_text(encoding='utf-8'))
    melee=[e for e in enemies.values() if e.get('ai') in ('melee','charger')]
    assert melee
    integrated=[e for e in melee if e.get('visual_has_weapon')]
    armed=[e for e in melee if not e.get('visual_has_weapon')]
    assert integrated
    assert all(e.get('weapon_id') in weapons for e in armed)
    assert all(weapons[e['weapon_id']].get('class')=='melee' for e in armed)
    assert all(weapons[e['weapon_id']].get('weapon_sprite') for e in armed)


def test_bosses_have_distinct_styles_and_summon_mixed_minions():
    bosses=json.loads((ROOT/'data'/'bosses.json').read_text(encoding='utf-8'))
    styles={b.get('boss_style') for b in bosses.values()}
    assert {'commander','summoner','tank','mage','colossus','regent'} <= styles
    for boss in bosses.values():
        for phase in boss['phases']:
            assert {'grunt','runner','gunner','spreader'} <= set(phase.get('summon_ids',[]))
            assert phase.get('summon_count',0)>=2


def test_new_enemy_variants_have_valid_weapon_assignments():
    enemies=json.loads((ROOT/'data'/'enemies.json').read_text(encoding='utf-8'))
    weapons=json.loads((ROOT/'data'/'weapons.json').read_text(encoding='utf-8'))
    assert enemies['shield_guard']['shielded'] is True
    assert enemies['mini_colossus']['ai']=='charger'
    assert enemies['blade_stalker']['speed']>=120
    assert all(e['weapon_id'] in weapons for e in enemies.values() if e.get('weapon_id'))
