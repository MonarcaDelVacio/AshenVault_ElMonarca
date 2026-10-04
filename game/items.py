"""Objetos temporales y aplicación centralizada de bonificaciones."""

def _apply_effects(player, effects):
    for key,val in effects.items():
        if key in ('damage_mult','crit_chance','speed','energy_regen'):
            setattr(player,key,getattr(player,key)+val if key!='damage_mult' else getattr(player,key)*(1+val))
        elif key=='max_hp': player.max_hp+=int(val); player.hp+=int(val)
        elif key=='max_shield': player.max_shield+=int(val); player.shield+=int(val)
        elif key=='max_energy': player.max_energy+=int(val); player.energy+=val
        elif key=='shield_regen_rate': player.c.shield_regen_rate += val
        elif key=='weapon_damage_mult': player.damage_mult*=1+val
        elif key=='move_speed_mult': player.speed*=1+val
        elif key=='attack_speed_mult': player.attack_speed_mult=getattr(player,'attack_speed_mult',1.0)*(1+val)
        elif key=='pierce': player.bonus_pierce=getattr(player,'bonus_pierce',0)+int(val)
        elif key=='projectile_count': player.bonus_projectiles=getattr(player,'bonus_projectiles',0)+int(val)
        elif key=='coin_radius': player.coin_radius=getattr(player,'coin_radius',0)+int(val)

def apply_item_bonuses(player, item, synergy_data=None):
    effects=item.effects if hasattr(item,'effects') else item.get('effects',{})
    _apply_effects(player,effects)
    player.items.append(item)
    if synergy_data:
        owned={getattr(x,'id',None) for x in player.items}
        for sid,sy in synergy_data.items():
            if sid in player.synergies: continue
            if set(sy.get("requires",[])).issubset(owned):
                _apply_effects(player,sy.get("effects",{}))
                player.synergies.append(sid)


def make_item(data, ident):
    raw=data[ident]
    return type('Item',(object,),{'id':ident,**raw})()
