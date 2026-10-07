"""Registro centralizado de assets para AshenVault.

Fase 2 introduce un registro en modo compatibilidad: no decide todavía cómo
se renderiza un asset ni sustituye los loaders existentes. Su responsabilidad
es dar a cada recurso una identidad estable y conservar su procedencia,
región de spritesheet y metadatos geométricos.

El registro no importa pygame para poder validarse en tests sin inicializar el
subsistema gráfico.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


RectTuple = tuple[int, int, int, int]
PointTuple = tuple[float, float]


@dataclass(frozen=True)
class AssetRecord:
    """Metadatos estables de un recurso o frame."""

    asset_id: str
    category: str
    source_file: str | None = None
    frame_index: int | None = None
    source_rect: RectTuple | None = None
    alpha_bounds: RectTuple | None = None
    visual_bounds: RectTuple | None = None
    collision_bounds: RectTuple | None = None
    pivot: PointTuple | None = None
    anchor: PointTuple | None = None
    scale: float = 1.0
    variant: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    handle: Any = field(default=None, compare=False, repr=False)


class AssetRegistry:
    """Índice determinista de assets con soporte para migración gradual."""

    def __init__(self) -> None:
        self._records: dict[str, AssetRecord] = {}

    def register(self, record: AssetRecord, *, replace: bool = False) -> AssetRecord:
        if not record.asset_id:
            raise ValueError("asset_id no puede estar vacío")
        existing = self._records.get(record.asset_id)
        if existing is not None and not replace:
            if existing != record:
                raise ValueError(f"Asset duplicado con metadatos distintos: {record.asset_id}")
            return existing
        self._records[record.asset_id] = record
        return record

    def register_simple(
        self,
        asset_id: str,
        category: str,
        *,
        source_file: str | None = None,
        frame_index: int | None = None,
        source_rect: RectTuple | None = None,
        variant: str | None = None,
        scale: float = 1.0,
        handle: Any = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AssetRecord:
        return self.register(
            AssetRecord(
                asset_id=asset_id,
                category=category,
                source_file=source_file,
                frame_index=frame_index,
                source_rect=source_rect,
                variant=variant,
                scale=float(scale),
                metadata=dict(metadata or {}),
                handle=handle,
            )
        )

    def register_runtime_frame(
        self,
        asset_id: str,
        category: str,
        *,
        source_file: str,
        frame_index: int,
        source_rect: RectTuple,
        alpha_bounds: RectTuple | None = None,
        visual_bounds: RectTuple | None = None,
        collision_bounds: RectTuple | None = None,
        pivot: PointTuple | None = None,
        anchor: PointTuple | None = None,
        scale: float = 1.0,
        variant: str | None = None,
        handle: Any = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AssetRecord:
        """Registra un frame ya cargado sin cambiar el loader que lo produjo."""
        return self.register(
            AssetRecord(
                asset_id=asset_id,
                category=category,
                source_file=source_file,
                frame_index=frame_index,
                source_rect=source_rect,
                alpha_bounds=alpha_bounds,
                visual_bounds=visual_bounds,
                collision_bounds=collision_bounds,
                pivot=pivot,
                anchor=anchor,
                scale=float(scale),
                variant=variant,
                metadata=dict(metadata or {}),
                handle=handle,
            )
        )

    def resolve(self, asset_id: str) -> AssetRecord | None:
        return self._records.get(asset_id)

    def require(self, asset_id: str) -> AssetRecord:
        record = self.resolve(asset_id)
        if record is None:
            raise KeyError(f"Asset no registrado: {asset_id}")
        return record

    def records(self) -> tuple[AssetRecord, ...]:
        return tuple(self._records.values())

    def ids(self) -> tuple[str, ...]:
        return tuple(self._records)

    def by_category(self, category: str) -> tuple[AssetRecord, ...]:
        return tuple(r for r in self._records.values() if r.category == category)

    def validate_unique_source_regions(self) -> list[str]:
        """Detecta dos IDs que apuntan a la misma región física de un atlas."""
        seen: dict[tuple[str, RectTuple], str] = {}
        errors: list[str] = []
        for record in self._records.values():
            if not record.source_file or record.source_rect is None:
                continue
            key = (record.source_file, record.source_rect)
            previous = seen.get(key)
            if previous is not None and previous != record.asset_id:
                errors.append(
                    f"{previous} y {record.asset_id} comparten región "
                    f"{record.source_file}:{record.source_rect}"
                )
            else:
                seen[key] = record.asset_id
        return errors

    def validate_required(self, asset_ids: Iterable[str]) -> list[str]:
        return [asset_id for asset_id in asset_ids if asset_id not in self._records]

    @classmethod
    def from_game_data(cls, data: Any) -> "AssetRegistry":
        """Construye el inventario declarativo sin cargar superficies de pygame."""
        registry = cls()

        for wid, weapon in getattr(data, "weapons", {}).items():
            sprite = getattr(weapon, "weapon_sprite", None)
            sheet = getattr(weapon, "weapon_sprite_sheet", None)
            index = getattr(weapon, "weapon_sprite_index", None)
            if sprite:
                registry.register_simple(
                    f"weapon:{wid}",
                    "weapon",
                    source_file=str(sprite),
                    frame_index=index if isinstance(index, int) else None,
                )
            elif sheet:
                registry.register_simple(
                    f"weapon:{wid}",
                    "weapon",
                    source_file=str(sheet),
                    frame_index=index if isinstance(index, int) else None,
                    metadata={"sheet_key": str(sheet)},
                )

            projectile = getattr(weapon, "projectile_sprite", None)
            if projectile:
                registry.register_simple(
                    f"weapon-projectile:{wid}",
                    "projectile",
                    source_file=str(projectile),
                    metadata={"reference": str(projectile)},
                )

        for eid, enemy in getattr(data, "enemies", {}).items():
            registry.register_simple(
                f"enemy:{eid}",
                "enemy",
                source_file=getattr(enemy, "sprite_set", None),
                metadata={
                    "sprite_set": getattr(enemy, "sprite_set", None),
                    "sprite_scale": getattr(enemy, "sprite_scale", 1.0),
                },
            )
            projectile_asset = getattr(enemy, "projectile_asset_sheet", None)
            if projectile_asset:
                registry.register_simple(
                    f"enemy-projectile:{eid}",
                    "projectile",
                    source_file=str(projectile_asset),
                    metadata={"reference": str(projectile_asset)},
                )

        for bid, boss in getattr(data, "bosses", {}).items():
            registry.register_simple(
                f"boss:{bid}",
                "boss",
                source_file=getattr(boss, "sprite_set", None),
                metadata={
                    "sprite_set": getattr(boss, "sprite_set", None),
                    "sprite_scale": getattr(boss, "sprite_scale", 1.0),
                },
            )

        for cid, character in getattr(data, "characters", {}).items():
            registry.register_simple(
                f"character:{cid}",
                "character",
                metadata={"start_weapon": getattr(character, "start_weapon", None)},
            )

        return registry
