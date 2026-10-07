from types import SimpleNamespace

from game.systems import enemy_combat


def test_enemy_melee_attack_damages_player_and_emits_slash():
    player = SimpleNamespace(
        x=120.0, y=100.0, radius=10.0,
        hp=20.0, alive=True,
        take_damage=lambda damage, angle: True,
        set_status=lambda *args: None,
    )
    enemy = SimpleNamespace(
        x=100.0, y=100.0, facing=0.0, cooldown=0.0,
        d=SimpleNamespace(
            ai="melee", cooldown=1.0, hit_radius=45.0, damage=5.0,
            color=(1, 2, 3), damage_type="physical",
        ),
        is_boss=False, is_miniboss=False,
    )
    events=[]
    sim=SimpleNamespace(
        player=player, props=[],
        emit=lambda *event: events.append(event),
        on_player_hit=lambda *args: events.append(("player_hit",)+args),
        _break_prop=lambda *args: None,
    )

    enemy_combat.attack(enemy, sim, 20.0)

    assert enemy.cooldown == 1.0
    assert any(event[0] == "melee_swing" for event in events)
    assert any(event[0] == "player_hit" for event in events)


def test_enemy_ranged_attack_uses_weapon_projectile_visual_and_pattern():
    calls=[]
    enemy = SimpleNamespace(
        x=100.0, y=100.0, facing=0.0, cooldown=0.0,
        d=SimpleNamespace(
            ai="ranged", cooldown=1.5, pellets=3, fan_angle=30.0,
            projectile_speed=500.0, damage=8.0, projectile_radius=4.0,
            damage_type="physical", color=(9, 8, 7), projectile_pattern="fan",
            weapon_id="bow", projectile_visual_scale=1.0,
        ),
        is_boss=False, is_miniboss=False,
    )
    weapon = SimpleNamespace(projectile_sprite="assets/projectiles/test.png", projectile_speed=800.0, damage_type="physical", color=(1,2,3), explosive=False)
    sim = SimpleNamespace(
        data=SimpleNamespace(weapons={"bow": weapon}),
        spawn_projectile=lambda *args: calls.append(args),
        emit=lambda *args: None,
        time=0.0,
    )

    enemy_combat.attack(enemy, sim, 200.0)

    assert enemy.cooldown == 1.5
    assert len(calls) == 3
    assert all(call[0] == 1 for call in calls)
    assert all(call[13] == "assets/projectiles/test.png" for call in calls)
