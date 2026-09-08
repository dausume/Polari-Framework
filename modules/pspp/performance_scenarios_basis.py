"""
@module pspp.performance_scenarios_basis

Performance = a material STATE, in a GEOMETRY, under an EXPOSURE,
with LOADS, over TIME (plan pspp-9). Engines declare the structure
descriptors they read (require_descriptors gate) and produce CLAIMS
with evidence — v1 ships the two plan engines, both reusing existing
house math instead of inventing physics:

- elastic-bounds: Voigt/Reuss/Hill bounds via formulation_math over
  scenario-declared phase moduli — bounds, honestly labeled; the
  porosity->stiffness knockdown is a NAMED GAP until a cited
  relation loads (invariant I5).
- water-transport: reads the porosity/permeability descriptors; when
  hydraulicPermeability exists it claims it (and points at the live
  Darcy engine for field solves); missing descriptors refuse naming
  the exact knob.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from pspp.material_structure_basis import require_descriptors
from pspp.exposure_scenarios_basis import exposure_index


class MaterialPerformanceScenario(treeObject):
    """One in-service question about one material state."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # The MaterialState under test ('<material>#<state>').
        initial_state_key: str = '',
        # Part geometry reference ('' = bulk material question).
        geometry_ref: str = '',
        # ExposureScenario.name.
        exposure_scenario: str = '',
        loads_json: str = '{}',
        duration_hours: float = 0.0,
        # PERFORMANCE_ENGINES key.
        performance_engine: str = '',
        parameters_json: str = '{}',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.initial_state_key = initial_state_key
        self.geometry_ref = geometry_ref
        self.exposure_scenario = exposure_scenario
        self.loads_json = loads_json
        self.duration_hours = duration_hours
        self.performance_engine = performance_engine
        self.parameters_json = parameters_json
        self.provenance_id = provenance_id
        self.notes = notes


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
