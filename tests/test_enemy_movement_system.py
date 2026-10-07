from types import SimpleNamespace

from game.systems.enemy_movement import step, chase


def test_enemy_step_uses_slide_when_direct_path_is_blocked():
    enemy=SimpleNamespace(x=100.0,y=100.0,radius=10.0,d=SimpleNamespace(ai="melee"),strafe=1)
    calls=[]
    def move_actor(x,y,dx,dy,r):
        calls.append((dx,dy))
        if dy==0 and dx>0:
            return x,y
        return x+dx,y+dy
    sim=SimpleNamespace(arena=SimpleNamespace(width=500,height=500),move_actor=move_actor)
    step(enemy,sim,1,0,100,0.2)
    assert len(calls)>1
    assert enemy.x!=100.0 or enemy.y!=100.0


def test_chase_prefers_direct_line_of_sight():
    enemy=SimpleNamespace(x=100.0,y=100.0,radius=10.0,d=SimpleNamespace(ai="melee"),strafe=1)
    player=SimpleNamespace(x=200.0,y=100.0)
    moved=[]
    sim=SimpleNamespace(player=player,enemies=[enemy],arena=SimpleNamespace(line_of_sight=lambda *a:True),move_actor=lambda x,y,dx,dy,r:(moved.append((dx,dy)) or (x+dx,y+dy)))
    chase(enemy,sim,0.1,50)
    assert moved
    assert moved[0][0]>0


def test_chase_separates_from_other_enemy_without_self_reference_error():
    enemy = SimpleNamespace(x=100.0, y=100.0, radius=10.0, d=SimpleNamespace(ai="melee"), strafe=1)
    other = SimpleNamespace(x=104.0, y=100.0, radius=10.0, alive=True)
    player = SimpleNamespace(x=220.0, y=100.0)
    moved = []
    sim = SimpleNamespace(
        player=player,
        enemies=[enemy, other],
        arena=SimpleNamespace(line_of_sight=lambda *a: True),
        move_actor=lambda x, y, dx, dy, r: (moved.append((dx, dy)) or (x + dx, y + dy)),
    )
    chase(enemy, sim, 0.1, 50)
    assert moved
    assert moved[0][0] > 0


def test_flying_enemy_stays_inside_room_bounds():
    enemy=SimpleNamespace(x=495.0,y=495.0,radius=10.0,d=SimpleNamespace(ai="flying"),strafe=1)
    sim=SimpleNamespace(arena=SimpleNamespace(width=500,height=500))
    step(enemy,sim,1,1,100,1.0)
    assert 12.0 <= enemy.x <= 488.0
    assert 12.0 <= enemy.y <= 488.0

def test_defensive_cover_moves_enemy_behind_projectile_blocker():
    from game.enemies import Enemy

    class Rng:
        def random(self):
            return 0.0

    projectile = SimpleNamespace(x=20.0, y=100.0, vx=100.0, vy=0.0, damage=5.0)
    enemy = Enemy.__new__(Enemy)
    enemy.x = 100.0
    enemy.y = 100.0
    enemy.radius = 10.0
    enemy.hp = 20.0
    enemy.shield_integrity = 0.0
    enemy.shield_timer = 0.0
    enemy.shield_active = False
    enemy.dodge_cd = 10.0
    enemy.strafe = 1
    enemy.rng = Rng()
    enemy.d = SimpleNamespace(
        weapon_id=None,
        magic_user=False,
        shielded=False,
        shield_chance=0.0,
        dodge_chance=0.0,
        cover_chance=1.0,
        speed=100.0,
    )
    calls = []
    enemy._step = lambda sim, ux, uy, speed, dt: calls.append((ux, uy, speed, dt))

    sim = SimpleNamespace(
        _active_player_projectiles=[projectile],
        data=SimpleNamespace(weapons={}),
        props=[{"x": 140.0, "y": 100.0, "radius": 12.0, "kind": "crate", "broken": False}],
        emit=lambda *args: None,
    )
    assert enemy._defensive_reaction(sim, 0.1)
    assert calls
    # The target must be beyond the blocker, not at the blocker itself.
    assert calls[0][0] > 0.0
    assert calls[0][1] == 0.0
    assert calls[0][2] > enemy.d.speed
\n

def test_enemy_step_flips_strafe_when_completely_stuck():
    enemy=SimpleNamespace(x=100.0,y=100.0,radius=10.0,d=SimpleNamespace(ai="melee"),strafe=1)
    sim=SimpleNamespace(
        arena=SimpleNamespace(width=500,height=500),
        move_actor=lambda x,y,dx,dy,r:(x,y),
    )
    step(enemy,sim,1,0,100,0.2)
    assert enemy.strafe == -1
\n