# Aquaponics (`aquaponics`)

Self-watering pots, FEM hydraulics, vermicompost, per-part plant growth.

**Kind:** polari-app · **agent tier:** member · **requires:** plant_morphology, scoring

## Objects

`AquaponicsAtmosphereAPI`, `AquaponicsCompostAPI`, `AquaponicsHydraulicsAPI`, `AquaponicsLightFieldAPI`, `AquaponicsMediaAPI`, `AquaponicsPlantAPI`, `AquaponicsPlantGrowthNormalizedAPI`, `AquaponicsPlantGrowthSimplifiedAPI`, `AquaponicsPotAPI`, `AquaponicsSystemAPI`, `AquaponicsWaterBatchAPI`, `AquaponicsWaterLevelAPI`, `AtmosphereDefinition`, `CompostBinDefinition`, `CompostLoopDefinition`, `LightSourceDefinition`, `LightSpectrumDefinition`, `NutrientProfile`, `NutrientSpecies`, `PlantDefinition`, `PlantGrowthModel`, `PlantPart`, `PotDefinition`, `PotHole`, `PotPlanting`, `PotSystemDefinition`, `SoilDefinition`, `StressResponseCurve`, `VermicompostProfile`, `WaterBatchSchedule`, `WaterDefinition`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `atmosphere_basis.py`, `growth_media_basis.py`, `light_basis.py`, `plant_basis.py`, `plant_growth_basis.py`, `plant_growth_normalized_basis.py`, `plant_stress_basis.py`, `pot_basis.py`, `pot_system_basis.py`, `vermicompost_basis.py`, `water_batch_basis.py`
- **api** — `atmosphere_api.py`, `hydraulics_api.py`, `light_field_api.py`, `media_api.py`, `plant_api.py`, `plant_growth_normalized_api.py`, `plant_growth_simplified_api.py`, `pot_api.py`, `pot_system_api.py`, `vermicompost_api.py`, `water_batch_api.py`, `water_level_api.py`
- **seed** — `atmosphere_seed.py`, `light_seed.py`, `media_seed.py`, `plant_growth_normalized_seed.py`, `plant_growth_seed.py`, `plant_seed.py`, `plant_stress_seed.py`, `pot_materials_seed.py`, `pot_seed.py`, `pot_system_seed.py`, `vermicompost_seed.py`, `water_batch_seed.py`
- **page** — `aquaponics_page.py`
- **custom** — `custom/atmosphere_analysis.py`, `custom/hydraulics.py`, `custom/light_field.py`, `custom/media_analysis.py`, `custom/nutrient_uptake.py`, `custom/plant_analysis.py`, `custom/plant_growth_simplified.py`, `custom/plant_skeleton.py`, `custom/pot_geometry.py`, `custom/vermicompost_analysis.py`, `custom/water_level.py`
- **selftests** — `aquaponics_pages_selftest.py`, `atmosphere_selftest.py`, `growth_media_selftest.py`, `hydraulics_selftest.py`, `light_field_selftest.py`, `plant_growth_normalized_selftest.py`, `plant_growth_simplified_selftest.py`, `plant_selftest.py`, `plant_species_comparison_selftest.py`, `plant_stress_selftest.py`, `plant_transport_selftest.py`, `pot_selftest.py`, `system_selftest.py`, `vermicompost_selftest.py`, `water_batch_selftest.py`, `water_level_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Pages

- `aquaponics.aquaponics_page:SEED_AQUAPONICS_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest aquaponics        # in the running backend
PYTHONPATH=.:modules python3 -m aquaponics.aquaponics_pages_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform aquaponics`
