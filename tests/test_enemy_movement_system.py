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
