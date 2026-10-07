from types import SimpleNamespace

from game.abilities import use_ability


def test_bastion_initializes_front_shield_integrity():
    player = SimpleNamespace(
        ability_cd=0.0, alive=True, ability={"kind":"shield", "amount":4, "cooldown":9, "invuln":0.8},
        c=SimpleNamespace(ability={"kind":"shield", "amount":4, "cooldown":9, "invuln":0.8}),
        statue_ability_mult=1.0, max_shield=10.0, shield=0.0,
        invuln=0.0, ability_shield_fx=0.0, ability_shield_hp=0.0,
        x=10.0, y=20.0, status_timers={},
        set_status=lambda *args: None,
    )
    sim = SimpleNamespace(player=player, stats={"abilities":0}, emit=lambda *args: None)
    assert use_ability(sim) is True
    assert player.ability_shield_hp == 4.0
    assert player.ability_shield_fx > 0
    assert sim.stats["abilities"] == 1
