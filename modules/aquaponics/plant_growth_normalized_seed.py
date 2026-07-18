"""
@cross-cutting
@module aquaponics.plant_growth_normalized_seed
@tags @xc:bindings

Demo plantings (plant-growth-sim phase 1/7, 2026-07-15): sweet-basil
in demo-herb-pot — reuses REAL rows from every module this feature
spans (aquaponics.plant_seed's sweet-basil PlantDefinition/PlantPart,
plant_morphology.morphology_seed's matching RootSystemModel/
OrganModel rows, aquaponics.pot_seed's demo-herb-pot,
aquaponics.pot_system_seed's two bound systems) rather than inventing
fixture-only data, so live verification exercises the real
cross-module path.

THREE plantings, sharing the pot/plant/geometry but bound to three
real contrasting PotSystemDefinition rows: aqp-6's own healthy-vs-
sealed pair (phase 7's per-part stress-equation path needs a real
system_name to compute anything, and having both lets a live check
compare a healthy and a degraded planting side by side), plus phase
10's water-batched system (a controlled, cycling Fe-stress window
instead of a static water source).

@consumers
  - polariServer seed_pairs
@see /AQUAPONICS_POT_SHAPE_PLAN.md phases 6-7, 10
"""

SEED_POT_PLANTINGS = [
    {
        'name': 'demo-herb-pot-basil-1',
        'pot_name': 'demo-herb-pot',
        'plant_name': 'sweet-basil',
        'planted_at': '2026-07-01T00:00:00+00:00',
        # phase 7 — bound to the REAL healthy ventilated-tent system
        # (aquaponics.pot_system_seed.SEED_POT_SYSTEMS), so
        # advance_growth's default (no explicit factor) path has a
        # real system to auto-compute per-part stress factors from.
        'system_name': 'basil-aquaponic-tent',
        # Fixed, not random-at-seed-time — reproducible across every
        # backend restart (Date.now()-at-seed-time would silently
        # reseed a DIFFERENT skeleton on every boot, defeating the
        # whole "same pot -> same plant" point).
        'random_seed': 8241,
        # Explicit even though it matches PotPlanting.__init__'s own
        # default — selftests build SimpleNamespace(**row) directly,
        # bypassing the constructor entirely, so an omitted key here
        # is a missing attribute, not a silently-applied default.
        'part_growth_json': '{}',
        'condition': 'healthy',
        'last_advanced_at': '',
        'provenance_id': '',
        'notes': 'plant-growth-sim phase 1/7 demo — real sweet-basil '
                 'RootSystemModel/OrganModel rows, planted in the '
                 'real demo-herb-pot, bound to the healthy ventilated-'
                 'tent system.',
    },
    {
        'name': 'demo-herb-pot-basil-sealed',
        'pot_name': 'demo-herb-pot',
        'plant_name': 'sweet-basil',
        'planted_at': '2026-07-01T00:00:00+00:00',
        # Same pot/plant/geometry, bound to the REAL sealed-chamber
        # system instead — a real, honest (not contrived) contrast
        # case for the stress-equation path (see
        # aquaponics.plant_stress_seed's own docstring for exactly
        # which stress types actually differ between the two).
        'system_name': 'basil-aquaponic-sealed',
        'random_seed': 5127,
        'part_growth_json': '{}',
        'condition': 'healthy',
        'last_advanced_at': '',
        'provenance_id': '',
        'notes': 'plant-growth-sim phase 7 demo — same pot/plant as '
                 'demo-herb-pot-basil-1, bound to the degraded sealed-'
                 'chamber system for a real stress-equation contrast.',
    },
    {
        'name': 'demo-herb-pot-basil-batched',
        'pot_name': 'demo-herb-pot',
        'plant_name': 'sweet-basil',
        'planted_at': '2026-07-01T00:00:00+00:00',
        # phase 10 — bound to the water-BATCHED system: the active
        # water source cycles (4 days rich, 1 day deliberately Fe-
        # deficient, repeating) instead of one static binding.
        'system_name': 'basil-water-batched',
        'random_seed': 3910,
        'part_growth_json': '{}',
        'condition': 'healthy',
        'last_advanced_at': '',
        'provenance_id': '',
        'notes': 'plant-growth-sim phase 10 demo — same pot/plant as '
                 'the other two, bound to the water-batched system for '
                 'a real nutrient-source-cycling demonstration.',
    },
    {
        'name': 'demo-herb-pot-pepper-1',
        'pot_name': 'demo-herb-pot',
        'plant_name': 'dwarf-pepper',
        # SAME planted_at as demo-herb-pot-basil-1 — a fair, same-
        # starting-point comparison between the two species.
        'planted_at': '2026-07-01T00:00:00+00:00',
        'system_name': 'dwarf-pepper-tent',
        'random_seed': 6284,
        'part_growth_json': '{}',
        'condition': 'healthy',
        'last_advanced_at': '',
        'provenance_id': '',
        'notes': 'plant-growth-sim phase 12 demo — the second full-'
                 'parity species, same pot/atmosphere/water/light as '
                 'demo-herb-pot-basil-1 for a real, isolated species '
                 'comparison.',
    },
]
