"""
@module pspp.custom.sintering_structure

mtt-2 Part B sinter-3: the sintering engine WRITES the structure-layer
seam — grain-size + porosity + relative-density descriptors onto L2
ScaleStructureDefinition rows per fire checkpoint. That is exactly the
qDistribution-descriptor pattern gsp-4 already reads, so a sintered-
state "groups"/structure view comes almost free once these rows exist.

PLAN-FIRST (the knobs-and-suggestions house rule): this proposes the
structure rows a firing outcome implies; it never persists. Applying
is an explicit caller step (mirrors cure_checkpoints). A refusal names
exactly what is missing.

@consumers
  - pspp.pspp_api (/api/pspp/sinter/structure-plan)
  - pspp.sintering_structure_selftest
"""

#: L2 grain domain length band is set from the grain size itself
#: (µm -> m); the pore band is the same neighborhood.
_UM = 1e-6

_PLAN_NOTE = ('plan-first: these ScaleStructureDefinition rows are '
              'PROPOSED from the firing outcome — applying them is an '
              'explicit step, never automatic (knobs + suggestions)')


def plan_sinter_structure(state_key, relative_density, grain_size_um,
                          theoretical_density_g_cm3=None,
                          reaction_extent=1.0):
    """Propose the L2 structure rows a sintered state implies:
    a grain-domain row (grainSize + the mandatory core) and a
    pore-network row (totalPorosity = 1 − ρ). Returns
    {ok, proposedRows, note} | refusal. Nothing is persisted."""
    if not state_key:
        return {'ok': False,
                'refusal': 'no state_key — a structure row must attach '
                           'to a MaterialState',
                'suggestion': 'pass the fired state key '
                              "('<material>#<fire-checkpoint>')"}
    if relative_density is None or grain_size_um is None:
        return {'ok': False,
                'refusal': 'need both relativeDensity and grainSize '
                           'to describe the sintered microstructure',
                'suggestion': 'run pspp.custom.sintering_engine '
                              '(relative_density + grain_size) first '
                              '— each refuses without its calibration'}
    try:
        rho = float(relative_density)
        grain = float(grain_size_um)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': 'relativeDensity and grainSize must be '
                           'numbers',
                'suggestion': 'pass the engine outputs'}
    if not 0.0 < rho <= 1.0:
        return {'ok': False,
                'refusal': f'relativeDensity {rho} out of (0, 1]',
                'suggestion': 'relative density is a fraction of '
                              'theoretical'}
    if grain <= 0:
        return {'ok': False,
                'refusal': f'grainSize {grain} must be positive',
                'suggestion': 'grain size in µm'}
    porosity = 1.0 - rho
    # Bulk density only when the theoretical density is supplied — no
    # invented value (absence is honest; the descriptor is omitted).
    grain_core = {
        'totalPorosity': round(porosity, 6),
        'reactionExtent': float(reaction_extent),
        'moistureState': 'dry-fired',
        'phaseFractions': {},  # unknown here — an honest empty core
    }
    if theoretical_density_g_cm3 is not None:
        try:
            grain_core['bulkDensity'] = round(
                float(theoretical_density_g_cm3) * rho, 6)
        except (TypeError, ValueError):
            pass
    grain_row = {
        'name': f'{state_key}@L2-grain-domain',
        'state_key': state_key,
        'scale_level': 2,
        'domain_type': 'grain-domain',
        'characteristic_length_min_m': round(grain * _UM * 0.5, 12),
        'characteristic_length_max_m': round(grain * _UM * 2.0, 12),
        'representation_type': 'descriptor-summary',
        'descriptors_json': {
            **grain_core,
            'grainSize': round(grain, 4),
            'relativeDensity': round(rho, 6),
        },
        'status': 'defined',
        'notes': 'grain-domain microstructure from the sintering '
                 'engine (MSC ρ + mean-field grain size)',
    }
    pore_row = {
        'name': f'{state_key}@L2-pore-network',
        'state_key': state_key,
        'scale_level': 2,
        'domain_type': 'capillary-pore',
        'characteristic_length_min_m': round(grain * _UM * 0.05, 12),
        'characteristic_length_max_m': round(grain * _UM * 0.5, 12),
        'representation_type': 'descriptor-summary',
        'descriptors_json': {
            'totalPorosity': round(porosity, 6),
            'reactionExtent': float(reaction_extent),
            'moistureState': 'dry-fired',
            'phaseFractions': {},
        },
        'status': 'defined',
        'notes': 'residual pore network from densification '
                 '(porosity = 1 − relative density)',
    }
    return {
        'ok': True,
        'stateKey': state_key,
        'relativeDensity': round(rho, 6),
        'grainSizeUm': round(grain, 4),
        'totalPorosity': round(porosity, 6),
        'proposedRows': [grain_row, pore_row],
        'note': _PLAN_NOTE,
    }
