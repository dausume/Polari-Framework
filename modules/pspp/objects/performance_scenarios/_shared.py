"""@module pspp.objects.performance_scenarios._shared — what the performance_scenarios row classes share (constants, seeds, helpers); split from performance_scenarios_basis.py (sap-2c)."""
from pspp.exposure_scenarios_basis import exposure_index
import json
from pspp.material_structure_basis import require_descriptors

def _claim(state_key, prop, value, method, assumptions, source):
    return {'subject': state_key, 'property': prop, 'value': value,
            'evidenceMethod': method, 'assumptions': assumptions,
            'source': source}
def _elastic_bounds(manager, state_key, exposure, params):
    gate = require_descriptors(
        manager, state_key,
        ('bulkDensity', 'phaseFractions', 'totalPorosity'))
    if not gate['ok']:
        return gate
    phases = params.get('phases') or []
    if not (len(phases) >= 2
            and all('modulus_gpa' in p and 'volume_fraction' in p
                    for p in phases)):
        return {'ok': False,
                'refusal': 'elastic-bounds needs scenario parameters '
                           "phases=[{name, modulus_gpa, "
                           'volume_fraction}, ...] (2+)',
                'suggestion': 'declare the constituent moduli on the '
                              'scenario row — bounds math is '
                              'rules-of-mixtures over DECLARED '
                              'constituents, never guessed'}
    from materialsScience.formulation_math import mixture_bounds
    values = [p['modulus_gpa'] for p in phases]
    fractions = [p['volume_fraction'] for p in phases]
    bounds = mixture_bounds(values, fractions)
    porosity = gate['descriptors']['totalPorosity']['value']
    assumptions = [
        'Voigt/Reuss/Hill BOUNDS over declared constituents — '
        'idealized estimates, not measurements',
        f'porosity {porosity} NOT applied: the porosity->stiffness '
        'knockdown is a named gap until a cited relation loads '
        '(invariant I5)',
        f"exposure '{exposure['name']}' effects on modulus unmodeled",
    ]
    return {'ok': True, 'claims': [
        _claim(state_key, 'elasticModulusVoigtUpper',
               bounds['voigt'], 'rules-of-mixtures', assumptions,
               'formulation_math.mixture_bounds'),
        _claim(state_key, 'elasticModulusReussLower',
               bounds['reuss'], 'rules-of-mixtures', assumptions,
               'formulation_math.mixture_bounds'),
        _claim(state_key, 'elasticModulusHill',
               bounds['value'], 'rules-of-mixtures', assumptions,
               'formulation_math.mixture_bounds'),
    ]}
def _water_transport(manager, state_key, exposure, params):
    contact = exposure['environment'].get('water_contact', 'none')
    if contact == 'none':
        return {'ok': True, 'claims': [], 'note':
                f"exposure '{exposure['name']}' has no water contact "
                '— nothing to transport'}
    gate = require_descriptors(
        manager, state_key, ('openPorosity', 'connectedPorosity'))
    if not gate['ok']:
        return gate
    descriptors = gate['descriptors']
    claims = [
        _claim(state_key, 'connectedPorosity',
               descriptors['connectedPorosity']['value'], 'measured',
               ['connected porosity governs transport far more than '
                'total porosity (plan §2.2)'],
               descriptors['connectedPorosity']['sourceRow']),
    ]
    permeability = require_descriptors(
        manager, state_key, ('hydraulicPermeability',))
    if permeability['ok']:
        k = permeability['descriptors']['hydraulicPermeability']
        claims.append(_claim(
            state_key, 'hydraulicPermeability', k['value'],
            'measured',
            [f"under '{exposure['name']}' ({contact}) — field solves "
             'available via the live Darcy engine '
             '(materialsScience.engines.darcy_engine)'],
            k['sourceRow']))
        return {'ok': True, 'claims': claims}
    return {'ok': True, 'claims': claims, 'note':
            'hydraulicPermeability absent — quantitative flux needs '
            'that descriptor (or a Darcy solve); the refusal-shaped '
            'gap: ' + permeability['refusal']}
PERFORMANCE_ENGINES = {
    'elastic-bounds': _elastic_bounds,
    'water-transport': _water_transport,
}
def run_performance_scenario(manager, scenario):
    """Run one scenario (row or dict) → claims + honest notes."""
    get = (scenario.get if isinstance(scenario, dict)
           else lambda k, d='': getattr(scenario, k, d))
    engineKey = get('performance_engine', '')
    engine = PERFORMANCE_ENGINES.get(engineKey)
    if engine is None:
        return {'ok': False,
                'refusal': f'unknown performance engine {engineKey!r}',
                'suggestion': f'one of {sorted(PERFORMANCE_ENGINES)} '
                              '— degradation engines (carbonation, '
                              'efflorescence, oxidation…) are named '
                              'gaps awaiting cited models'}
    exposures = exposure_index(manager)
    exposure = exposures.get(get('exposure_scenario', ''))
    if exposure is None:
        return {'ok': False,
                'refusal': f'unknown exposure '
                           f'{get("exposure_scenario", "")!r}',
                'suggestion': f'one of {sorted(exposures)}'}
    try:
        params = json.loads(get('parameters_json', '{}') or '{}') \
            if not isinstance(get('parameters_json', {}), dict) \
            else get('parameters_json')
    except Exception:
        params = {}
    result = engine(manager, get('initial_state_key', ''), exposure,
                    params)
    if result.get('ok'):
        result['scenario'] = get('name', '')
        result['exposure'] = exposure['name']
        result['engine'] = engineKey
    return result
