                    frames = self._load_sheet_frames(path)
                    if frames:
                        loaded[anim] = frames
            if loaded:
                self.enemy_sprites[key] = loaded
        flyer_path = enemy_dir / "flying" / "enemigovolador_spritesheet.png"
        if flyer_path.is_file():
            # Este asset es una cuadrícula 4x4. Si el detector de cuadrícula
            # rechaza la hoja por dimensiones/márgenes inesperados, intentamos
            # inmediatamente el loader de spritesheet antes de dejar el enemigo
            # sin representación visual.
            flyer_frames = self._load_grid_frames(flyer_path, 4, 4)
            if not flyer_frames:
                flyer_frames = self._load_sheet_frames(flyer_path)
            if flyer_frames:
                self.enemy_sprites.setdefault("new_flyer", {})
                self.enemy_sprites["new_flyer"] = {
                    "walk": flyer_frames,
                    "attack": flyer_frames,
                    "death": flyer_frames,
                }

        # Ningún enemigo/boss declarado puede llegar al runtime con un sprite_set que no haya producido al menos una animación utilizable.
        # Evita que _draw_enemy_sprite() falle silenciosamente y deje un enemigo físicamente presente pero visualmente invisible.
        missing_enemy_models = []
        for entity_id, entity in self.data.enemies.items():
            key = getattr(entity, "sprite_set", None)
            anims = self.enemy_sprites.get(key, {}) if key else {}
            if not key or not any(anims.get(name) for name in ("idle", "walk", "run", "attack", "attack_heavy")):
                missing_enemy_models.append(f"enemy:{entity_id}:{key}")
        for boss_id, boss in self.data.bosses.items():
            key = getattr(boss, "sprite_set", None)
            anims = self.enemy_sprites.get(key, {}) if key else {}
            if not key or not any(anims.get(name) for name in ("idle", "walk", "run", "attack", "attack_heavy")):
                missing_enemy_models.append(f"boss:{boss_id}:{key}")
        if missing_enemy_models:
            raise RuntimeError("Modelos de enemigos no cargados: " + ", ".join(missing_enemy_models))

        self.misc_images = {}
        for wid, wdef in self.data.weapons.items():
            sprite_path = getattr(wdef, "weapon_sprite", None)
            if sprite_path:
                image = self._load_trimmed_asset(sprite_path)
                if image is not None:
                    self.weapon_images[wid] = image
                    max_dim = self._weapon_max_dimension(getattr(wdef, "class", "pistol"))
                    self.weapon_scaled_images[wid] = self._fit_image(image, max_dim)
            projectile_path = getattr(wdef, "projectile_sprite", None)