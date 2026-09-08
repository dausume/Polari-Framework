"""@module pspp.objects.material_processes._shared — what the material_processes row classes share (constants, seeds, helpers); split from material_processes_basis.py (sap-2c)."""
import json

EXECUTION_EFFECTS = ('TRANSFORMATIVE', 'OBSERVATIONAL')
ENERGY_DEPOSITION_MODELS = (
    'conventional-heating', 'microwave', 'rf', 'joule', 'laser',
)
_PROC_PROVENANCE = ('pspp-4 process vocabulary (PSPP_MATERIALS_PLAN '
                    '§2 + Ch.8.2-8.6 review 2026-07-18)')
SEED_PROCESS_DEFINITIONS = [
    # comminution / preparation
    {'name': 'grinding', 'process_type': 'comminution',
     'description': 'Particle-size reduction of a precursor powder.'},
    {'name': 'sieving', 'process_type': 'comminution',
     'description': 'Size classification — narrows the PSD.'},
    {'name': 'mixing', 'process_type': 'mixing',
     'description': 'Combine components into one state (recipes are '
                    'INPUT CONSTRAINTS of this process — invariant '
                    'I7).'},
    {'name': 'vacuum-degassing', 'process_type': 'mixing',
     'description': 'Remove entrained air from a slurry.'},
    # shaping
    {'name': 'casting', 'process_type': 'shaping',
     'description': 'Pour/compact into a mold.'},
    {'name': 'extrusion', 'process_type': 'shaping',
     'description': 'Force through a die (print/extrude routes).'},
    # heating family — one concept, five deposition models (F8:
    # kinetics differ, chemistry does not).
    {'name': 'heating-conventional', 'process_type': 'heating',
     'energy_deposition_model': 'conventional-heating',
     'description': 'Oven/furnace heating — boundary conduction.'},
    {'name': 'heating-microwave', 'process_type': 'heating',
     'energy_deposition_model': 'microwave',
     'description': 'Volumetric dielectric heating.'},
    {'name': 'heating-rf', 'process_type': 'heating',
     'energy_deposition_model': 'rf',
     'description': 'Radio-frequency volumetric heating.'},
    {'name': 'heating-joule', 'process_type': 'heating',
     'energy_deposition_model': 'joule',
     'description': 'Direct resistive heating.'},
    {'name': 'heating-laser', 'process_type': 'heating',
     'energy_deposition_model': 'laser',
     'description': 'Localized surface energy deposition (BLCNC '
                    'lineage).'},
    {'name': 'cooling', 'process_type': 'heating',
     'description': 'Controlled heat removal.'},
    # cure / chemistry drivers
    {'name': 'sealed-cure', 'process_type': 'curing',
     'material_family': 'geopolymer',
     'description': 'Cure with water retained (sealed) — the water '
                    'boundary condition is part of the process, not '
                    'the material.'},
    {'name': 'open-cure', 'process_type': 'curing',
     'material_family': 'geopolymer',
     'description': 'Cure with evaporation allowed.'},
    {'name': 'drying', 'process_type': 'dehydration',
     'description': 'Free-water removal.'},
    {'name': 'dehydroxylation', 'process_type': 'dehydration',
     'material_family': 'geopolymer',
     'description': 'Bound-OH removal at temperature (pp.168-169 '
                    'Al-coordination changes initiate later reaction '
                    'pathways — data pending).'},
    {'name': 'hydration', 'process_type': 'hydration',
     'description': 'Water uptake into the structure.'},
    {'name': 'carbonation', 'process_type': 'exposure',
     'description': 'CO2 reaction — a durability branch edge.'},
    {'name': 'weathering', 'process_type': 'exposure',
     'description': 'Combined outdoor exposure over time.'},
    # phase evolution (F10: crystallization is a PROCESS)
    {'name': 'annealing', 'process_type': 'phase-evolution',
     'description': 'Thermal hold enabling structural relaxation.'},
    {'name': 'nucleation', 'process_type': 'phase-evolution',
     'description': 'Crystal nuclei form in the amorphous matrix — '
                    'never `phase = X` by assignment.'},
    {'name': 'crystal-growth', 'process_type': 'phase-evolution',
     'description': 'Nuclei grow into crystalline domains (e.g. '
                    'amorphous → kalsilite → leucite with '
                    'temperature).'},
    # the one OBSERVATIONAL seed — the I2 contrast case.
    {'name': 'characterization', 'process_type': 'observation',
     'execution_effect': 'OBSERVATIONAL',
     'description': 'Measure without transforming (XRD, NMR, SEM, '
                    'mechanical test at nondestructive load) — '
                    'attaches claims, NEVER creates a state.'},
]
for _row in SEED_PROCESS_DEFINITIONS:
    _row.setdefault('execution_effect', 'TRANSFORMATIVE')
    _row.setdefault('material_family', 'general')
    _row.setdefault('energy_deposition_model', '')
    _row.setdefault('provenance_id', _PROC_PROVENANCE)
def _loads(row, attr, fallback):
    try:
        return json.loads(getattr(row, attr, None)
                          or (row.get(attr) if isinstance(row, dict)
                              else None) or fallback)
    except Exception:
        return json.loads(fallback)
def validate_execution(definition, execution):
    """Enforce invariant I2 on one (definition, execution) pair:
    TRANSFORMATIVE must name output states; OBSERVATIONAL must not."""
    get_def = (definition.get if isinstance(definition, dict)
               else lambda k, d='': getattr(definition, k, d))
    effect = get_def('execution_effect', '')
    if effect not in EXECUTION_EFFECTS:
        return {'ok': False,
                'refusal': f'definition declares no valid '
                           f'execution_effect ({effect!r})',
                'suggestion': f'set one of {EXECUTION_EFFECTS} on the '
                              'MaterialProcessDefinition row — the '
                              'discriminator is declared, never '
                              'inferred (invariant I2)'}
    outputs = _loads(execution, 'output_state_ids_json', '[]')
    if effect == 'OBSERVATIONAL' and outputs:
        return {'ok': False,
                'refusal': 'OBSERVATIONAL execution names output '
                           f'states {outputs} — observations attach '
                           'claims, never create states',
                'suggestion': 'either clear output_state_ids_json or '
                              'redeclare the definition TRANSFORMATIVE '
                              'if the material genuinely changes'}
    if effect == 'TRANSFORMATIVE' and not outputs:
        return {'ok': False,
                'refusal': 'TRANSFORMATIVE execution names no output '
                           'states',
                'suggestion': 'name the child MaterialState key(s) it '
                              'produces (they may start with unknown '
                              'structure — that is honest)',
                }
    return {'ok': True, 'effect': effect, 'outputs': outputs}
def admissible_schedule(definition, schedule, thermal_profiles=None):
    """Thermal admissibility: when a definition constrains itself to a
    component set's no-volatiles window, every schedule hold must sit
    inside that window. Reuses materialsScience.thermal_windows."""
    get_def = (definition.get if isinstance(definition, dict)
               else lambda k, d='': getattr(definition, k, d))
    raw = get_def('accepted_input_constraints_json', '{}') or '{}'
    try:
        constraints = (raw if isinstance(raw, dict)
                       else json.loads(raw))
    except Exception:
        constraints = {}
    components = constraints.get('thermal_window_components') or []
    if not components:
        return {'ok': True,
                'note': 'no thermal constraint declared on this '
                        'process definition'}
    from materialsScience.thermal_windows import processing_window
    if thermal_profiles is None:
        from materialsScience.thermal_windows import (
            SEED_THERMAL_PROFILES, profiles_from_rows,
        )
        thermal_profiles = profiles_from_rows(SEED_THERMAL_PROFILES)
    window = processing_window(components, thermal_profiles)
    if not window.get('ok'):
        return {'ok': False,
                'refusal': 'no open processing window for '
                           f'{components}',
                'window': window,
                'suggestion': 'change the component set or fix the '
                              'missing ThermalProcessingProfile rows '
                              f"({window.get('missingProfiles', [])})"}
    lo, hi = window['windowC']
    holds = [s.get('holdC') for s in (schedule or [])
             if isinstance(s, dict) and 'holdC' in s]
    bad = [t for t in holds if not (lo <= t <= hi)]
    if bad:
        return {'ok': False,
                'refusal': f'schedule holds {bad} exit the '
                           f'no-volatiles window [{lo}, {hi}] of '
                           f'{components}',
                'window': window,
                'suggestion': 'lower the hold temperature(s) or '
                              'reformulate — the offending component '
                              f"is {window.get('limitedBy', '?')}"}
    return {'ok': True, 'window': window, 'holdsC': holds}
