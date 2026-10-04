import os,sys,tempfile,unittest,math
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.data import GameData
from game.sim import Sim, Input
from game.save import SaveData

class Phase5Adjustments(unittest.TestCase):
    def test_rooms_only_show_real_connections_as_doors(self):
        from game.world import Dungeon
        for seed in range(25):
            dungeon=Dungeon(seed); room_ids=set(dungeon.rooms)
            for rid,room in dungeon.rooms.items():
                expected=set()
                if (rid[0],rid[1]-1) in room_ids: expected.add('N')
                if (rid[0],rid[1]+1) in room_ids: expected.add('S')
                if (rid[0]-1,rid[1]) in room_ids: expected.add('W')
                if (rid[0]+1,rid[1]) in room_ids: expected.add('E')
                self.assertEqual(set(room.arena.doors),expected)

    def test_melee_weapons_have_real_hitboxes_and_common_no_energy(self):
        from game.enemies import Enemy
        from game.weapons import WeaponState
        d=GameData(); s=Sim(d,'soldier',seed=8); p=s.player
        p.weapon=WeaponState(d.weapons['iron_sabre']); s.enemies=[]
        e=Enemy(d.enemies['grunt'],p.x+45,p.y); e.spawn_delay=0; s.enemies.append(e)
        inp=Input(); inp.aim_x=p.x+100; inp.aim_y=p.y; inp.fire_pressed=True
        s.update(inp,0.016)
        self.assertLess(e.hp,e.max_hp); self.assertEqual(p.energy,p.max_energy)

    def test_melee_only_blocks_projectiles_during_an_active_swing(self):
        from game.weapons import WeaponState
        d=GameData(); s=Sim(d,'soldier',seed=9); p=s.player
        p.weapon=WeaponState(d.weapons['iron_sabre']); p.aim=0

        # Apuntar al proyectil sin atacar ya no lo elimina.
        pr=s.spawn_projectile(1,p.x+25,p.y,math.pi,100,5,3,1,(255,80,80),'physical')
        s._update_projectiles(0.12)
        self.assertTrue(pr.active); self.assertEqual(p.hp,p.max_hp)

        # Un golpe cuerpo a cuerpo activo sí puede interceptarlo.
        p.hp=p.max_hp; p.shield=p.max_shield; p.melee_attack_timer=0.12
        pr=s.spawn_projectile(1,p.x+45,p.y,math.pi,100,5,3,1,(255,80,80),'physical')
        s._update_projectiles(0.05)
        self.assertFalse(pr.active); self.assertEqual(p.hp,p.max_hp)

    def test_ability_key_and_separate_audio_settings(self):
        with tempfile.TemporaryDirectory() as td:
            path=os.path.join(td,'save.json'); s=SaveData(path)
            self.assertEqual(s.data['settings']['keys']['ability'],'q')
            self.assertIn('effects_volume',s.data['settings']); self.assertIn('music_volume',s.data['settings'])
            s.data['settings']['effects_volume']=0.2; s.data['settings']['music_volume']=0.8; s.save(); s2=SaveData(path)
            self.assertEqual(s2.data['settings']['effects_volume'],0.2); self.assertEqual(s2.data['settings']['music_volume'],0.8)

if __name__=='__main__': unittest.main()
