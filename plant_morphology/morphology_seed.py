"""
@cross-cutting
@module plant_morphology.morphology_seed
@tags @xc:bindings

Organ + root stand-in models for sweet-basil (the aqp self-watering-pot
plant) and two perennial-roster plants (dwarf perennial pepper,
everbearing strawberry — the "kept in a pot indefinitely" cases). Mock
estimates, flagged priors. Idempotent-by-name.

dwarf-pepper-stem-organ (2026-07-15, plant-growth-sim phase 12) closes
a real gap found via direct audit: dwarf-pepper had leaf + fruit
organs but NO stem/branch axis organ — plant_skeleton.generate_
skeleton()'s canopy walk requires one to build any above-ground bones
at all (axis_organs = organs where organ in ('stem','branch')); without
it, pepper's skeleton would only ever produce root bones, no canopy,
regardless of growth data. Added as part of bringing dwarf-pepper to
full parity with basil (a second complete, comparable species — see
aquaponics/plant_seed.py's own module docstring for the full
comparison rationale).

@consumers
  - polariServer seed_pairs
@see /HOUSEHOLD_NUTRITION_PLAN.md Appendix B, /AQUAPONICS_POT_SHAPE_PLAN.md phase 12
"""

SEED_ORGAN_MODELS = [
    # sweet-basil — the pot plant.
    {'name': 'sweet-basil-leaf-organ', 'plant_name': 'sweet-basil',
     'organ': 'leaf', 'display_name': 'Basil leaf', 'shape_primitive':
     'lamina', 'length_mm': 60.0, 'width_mm': 35.0, 'thickness_mm': 1.5,
     'count': 40, 'arrangement': 'opposite', 'provenance_id': 'morph-1'},
    {'name': 'sweet-basil-stem-organ', 'plant_name': 'sweet-basil',
     'organ': 'stem', 'display_name': 'Basil stem', 'shape_primitive':
     'cylinder', 'length_mm': 250.0, 'width_mm': 8.0, 'thickness_mm':
     8.0, 'count': 6, 'arrangement': 'opposite', 'provenance_id':
     'morph-1'},
    # dwarf perennial pepper.
    {'name': 'dwarf-pepper-leaf-organ', 'plant_name': 'dwarf-pepper',
     'organ': 'leaf', 'display_name': 'Pepper leaf', 'shape_primitive':
     'ellipsoid', 'length_mm': 70.0, 'width_mm': 40.0, 'thickness_mm':
     1.8, 'count': 60, 'arrangement': 'alternate', 'provenance_id':
     'morph-1'},
    {'name': 'dwarf-pepper-stem-organ', 'plant_name': 'dwarf-pepper',
     'organ': 'stem', 'display_name': 'Pepper stem/branches',
     'shape_primitive': 'cylinder', 'length_mm': 300.0, 'width_mm': 12.0,
     'thickness_mm': 12.0, 'count': 4, 'arrangement': 'alternate',
     'provenance_id': 'plant-growth-sim phase 12'},
    {'name': 'dwarf-pepper-fruit-organ', 'plant_name': 'dwarf-pepper',
     'organ': 'fruit', 'display_name': 'Pepper fruit', 'shape_primitive':
     'cone', 'length_mm': 60.0, 'width_mm': 30.0, 'thickness_mm': 30.0,
     'count': 15, 'arrangement': 'alternate', 'provenance_id': 'morph-1'},
    # everbearing strawberry.
    {'name': 'strawberry-leaf-organ', 'plant_name': 'everbearing-strawberry',
     'organ': 'leaf', 'display_name': 'Strawberry leaf', 'shape_primitive':
     'lamina', 'length_mm': 50.0, 'width_mm': 45.0, 'thickness_mm': 1.2,
     'count': 18, 'arrangement': 'rosette', 'provenance_id': 'morph-1'},
]

SEED_ROOT_MODELS = [
    # Basil: fibrous, herb, tolerates confinement well, dwarfable, no
    # root pruning needed.
    {'name': 'sweet-basil-roots', 'plant_name': 'sweet-basil',
     'pattern': 'fibrous', 'natural_spread_radius_mm': 120.0,
     'natural_depth_mm': 200.0, 'root_ball_fraction': 0.5,
     'confinement_tolerance': 0.7, 'dwarfable': True,
     'root_prune_cadence_days': 0.0, 'indefinite_in_pot': True,
     'provenance_id': 'morph-1'},
    # Dwarf pepper: taproot-ish but dwarf variety, prunable — indefinite
    # WITH periodic root pruning.
    {'name': 'dwarf-pepper-roots', 'plant_name': 'dwarf-pepper',
     'pattern': 'taproot', 'natural_spread_radius_mm': 180.0,
     'natural_depth_mm': 300.0, 'root_ball_fraction': 0.6,
     'confinement_tolerance': 0.45, 'dwarfable': True,
     'root_prune_cadence_days': 365.0, 'indefinite_in_pot': True,
     'provenance_id': 'morph-1'},
    # Strawberry: shallow fibrous, extremely confinement tolerant.
    {'name': 'everbearing-strawberry-roots',
     'plant_name': 'everbearing-strawberry', 'pattern': 'fibrous',
     'natural_spread_radius_mm': 90.0, 'natural_depth_mm': 150.0,
     'root_ball_fraction': 0.55, 'confinement_tolerance': 0.85,
     'dwarfable': True, 'root_prune_cadence_days': 0.0,
     'indefinite_in_pot': True, 'provenance_id': 'morph-1'},
]
