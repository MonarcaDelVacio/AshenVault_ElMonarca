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