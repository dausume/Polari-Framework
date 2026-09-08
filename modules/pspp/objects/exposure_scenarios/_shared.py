"""@module pspp.objects.exposure_scenarios._shared — what the exposure_scenarios row classes share (constants, seeds, helpers); split from exposure_scenarios_basis.py (sap-2c)."""
import json

_PROV = 'pspp-9 exposure vocabulary (PSPP_MATERIALS_PLAN §2)'
SEED_EXPOSURE_SCENARIOS = [
    {'name': 'indoor-ambient', 'display_name': 'Indoor ambient',
     'environment_json': json.dumps(
         {'temperature_c': 22, 'relative_humidity': 0.45,
          'water_contact': 'none'})},
    {'name': 'outdoor', 'display_name': 'Outdoor weathering',
     'environment_json': json.dumps(
         {'temperature_c': [-10, 40], 'relative_humidity': [0.2, 1.0],
          'water_contact': 'humid', 'uv': True,
          'thermal_cycling': True})},
    {'name': 'hydroponic', 'display_name': 'Hydroponic / aquaponic',
     'description': 'Continuously wet growing systems (the pot '
                    'world) — water transport dominates.',
     'environment_json': json.dumps(
         {'temperature_c': [15, 30], 'water_contact': 'flowing',
          'nutrient_solution': True})},
    {'name': 'marine', 'display_name': 'Marine immersion',
     'environment_json': json.dumps(
         {'water_contact': 'immersed', 'chloride': True})},
    {'name': 'acid', 'display_name': 'Acid exposure',
     'environment_json': json.dumps(
         {'water_contact': 'immersed', 'ph': 2})},
    {'name': 'freeze-thaw', 'display_name': 'Freeze-thaw cycling',
     'environment_json': json.dumps(
         {'temperature_c': [-20, 20], 'water_contact': 'humid',
          'thermal_cycling': True})},
    {'name': 'fire', 'display_name': 'Fire / high temperature',
     'environment_json': json.dumps(
         {'temperature_c': [20, 1000], 'water_contact': 'none'})},
]
for _row in SEED_EXPOSURE_SCENARIOS:
    _row.setdefault('description', '')
    _row.setdefault('provenance_id', _PROV)
def exposure_index(manager):
    rows = (getattr(manager, 'objectTables', None) or {}).get(
        'ExposureScenario', {})
    rows = list(rows.values()) if isinstance(rows, dict) else list(rows)
    if not rows:
        rows = [type('R', (), dict(r))() for r in
                SEED_EXPOSURE_SCENARIOS]
    out = {}
    for r in rows:
        try:
            environment = json.loads(
                getattr(r, 'environment_json', '') or '{}')
        except Exception:
            environment = {}
        out[getattr(r, 'name', '')] = {
            'name': getattr(r, 'name', ''),
            'displayName': getattr(r, 'display_name', ''),
            'environment': environment,
        }
    return out
