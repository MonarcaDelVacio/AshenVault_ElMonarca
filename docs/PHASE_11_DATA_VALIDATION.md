# Fase 11 — Data Validation

## Estado

Fase 11 completada a nivel de implementación y auditoría estática del repositorio.

## Cobertura

- Validación del grafo declarativo de armas, enemigos, personajes, bosses y biomas.
- Validación de arenas, rooms, chests, items, modifiers, synergies y shops.
- Validación estructural de enemy_variants.
- Detección de referencias cruzadas inexistentes.
- Detección de IDs duplicados en variantes.
- Validación de modelos declarados para enemigos y bosses.
- Validación de assets de armas y proyectiles.
- Validación de assets de proyectiles declarados por variantes.
- Validación de índices de atlas durante la carga real del renderer.
- Validaciones ejecutadas al iniciar GameData antes de comenzar una run.
- Tests de regresión para referencias rotas, contratos inválidos, tiendas, arenas y variantes.

## Restricción

La fase no modifica balance ni comportamiento de gameplay. Su objetivo es detectar datos inválidos antes de que lleguen al runtime.

## Verificación

La integración y los tests fueron revisados mediante el contenido actual del repositorio y sus diffs. El conector disponible no proporciona un ejecutor local de pytest ni existe actualmente un workflow de GitHub Actions utilizable para ejecutar la batería completa desde esta sesión; por tanto, no se afirma una ejecución completa de pytest.

## Siguiente fase

Fase 12 — Optimization.
