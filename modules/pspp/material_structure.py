"""
@module pspp.material_structure

The STRUCTURE layer (plan pspp-3) — what processing writes and what
property-prediction engines read. Structure attaches to a
MaterialState (not to the bare material: a slurry and its cured solid
have different structures), per scale level, with L2 allowed MULTIPLE
domain rows (gel domains, capillary pores, reaction rims, fiber
interphases, microcrack networks — ChatGPT convergence: sub-domains
inside L2, never new top-level scales).

Mandatory core is exactly FIVE descriptors (bulk_density,
phase_fractions, total_porosity, moisture_state, reaction_extent —
reaction_extent continuous in [0,1], the Ch.5-8 aging/pot-life
insight). Everything else is optional and honestly absent; ENGINES
declare what they need via require_descriptors and get an
evidence-bearing refusal pointing at the exact missing knob.

Q-species (Figs 5.5/5.6, pp.84-85) are structural MOTIFS, not
complete structures — a qDistribution descriptor summarizes them;
the underlying network graph (when an L3 representation exists) is
never replaced by the summary.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.state_resolution (structure rows key by state)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

#: The 5-descriptor mandatory core (ChatGPT convergence: "otherwise
#: users spend months entering fields nobody reads").
MANDATORY_DESCRIPTORS = (
    'bulkDensity', 'phaseFractions', 'totalPorosity', 'moistureState',
    'reactionExtent',
)

#: L2 sub-domain vocabulary (navigation, extensible via rows' free
#: domain_type — these are the book-grounded starters).
L2_DOMAIN_TYPES = (
    'gel-domain', 'capillary-pore', 'reaction-rim',
    'dissolution-front', 'fiber-interphase', 'microcrack-network',
    'grain-domain', 'phase-morphology',
)


class ScaleStructureDefinition(treeObject):
    """One state's structure AT one scale level (and, at L2, one
    domain). The coherent owner of a state's structure is the set of
    rows sharing its state_key — same satellite idiom as scale
    definitions, so cross-scale transfer lineage (pspp-5) can cite
    individual rows."""

    @treeObjectInit
    def __init__(
        self,
        # Unique: '<state_key>@L<level>[-<domain>]'
        # ('metakaolin-gp#cured-solid@L2-capillary-pore').
        name: str = '',
        # MaterialState key this structure describes.
        state_key: str = '',
        scale_level: int = 0,
        # '' except (typically) L2 — one of L2_DOMAIN_TYPES or a new
        # coined type; multiple domain rows per state+level are the
        # DESIGN, not an anomaly.
        domain_type: str = '',
        # The length range this row speaks for (honesty about what
        # 'porosity' means HERE — invariant I8).
        characteristic_length_min_m: float = 0.0,
        characteristic_length_max_m: float = 0.0,
        # 'descriptor-summary' | 'field-ref' | 'network-graph-ref' |
        # 'particle-config-ref' — what representation backs this row.
        representation_type: str = 'descriptor-summary',
        # WHERE a non-summary representation lives (class + ref), like
        # MaterialScaleDefinition's definition home.
        representation_class: str = '',
        representation_ref: str = '',
        # The descriptors themselves (JSON dict). Mandatory core keys
        # per MANDATORY_DESCRIPTORS; absence of the rest is honest.
        descriptors_json: str = '{}',
        # 'defined' | 'partial' | 'planned' (gates treat planned as
        # absent — same status vocabulary as scale definitions).
        status: str = 'partial',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.state_key = state_key
        self.scale_level = scale_level
        self.domain_type = domain_type
        self.characteristic_length_min_m = characteristic_length_min_m
        self.characteristic_length_max_m = characteristic_length_max_m
        self.representation_type = representation_type
        self.representation_class = representation_class
        self.representation_ref = representation_ref
        self.descriptors_json = descriptors_json
        self.status = status
        self.provenance_id = provenance_id
        self.notes = notes


def _rows(manager, table='ScaleStructureDefinition'):
    rows = (getattr(manager, 'objectTables', None) or {}).get(table, {})
    return list(rows.values()) if isinstance(rows, dict) else list(rows)


def structure_rows_for_state(manager, subject_state_key):
    return [r for r in _rows(manager)
            if getattr(r, 'state_key', '') == subject_state_key]


def descriptors_for_state(manager, subject_state_key, scale_level=None,
                          domain_type=None):
    """Merged {descriptor: {value, sourceRow, scaleLevel, domainType}}
    over one state's usable structure rows ('planned' is absent)."""
    merged = {}
    for r in structure_rows_for_state(manager, subject_state_key):
        if getattr(r, 'status', 'partial') == 'planned':
            continue
        if scale_level is not None and \
                getattr(r, 'scale_level', 0) != scale_level:
            continue
        if domain_type is not None and \
                getattr(r, 'domain_type', '') != domain_type:
            continue
        try:
            descriptors = json.loads(
                getattr(r, 'descriptors_json', '') or '{}')
        except Exception:
            descriptors = {}
        for key, value in descriptors.items():
            merged[key] = {
                'value': value,
                'sourceRow': getattr(r, 'name', ''),
                'scaleLevel': getattr(r, 'scale_level', 0),
                'domainType': getattr(r, 'domain_type', ''),
            }
    return merged


def structure_profile(manager, subject_state_key):
    """One state's structure at a glance: per-level rows, mandatory-
    core coverage, honest gaps."""
    rows = structure_rows_for_state(manager, subject_state_key)
    have = descriptors_for_state(manager, subject_state_key)
    return {
        'stateKey': subject_state_key,
        'rows': [{'name': getattr(r, 'name', ''),
                  'scaleLevel': getattr(r, 'scale_level', 0),
                  'domainType': getattr(r, 'domain_type', ''),
                  'status': getattr(r, 'status', 'partial')}
                 for r in rows],
        'mandatoryCore': {d: (d in have)
                          for d in MANDATORY_DESCRIPTORS},
        'descriptorsPresent': sorted(have),
    }


def require_descriptors(manager, subject_state_key, needed,
                        scale_level=None):
    """The structure gate (sibling of scale_presence.require_scale_
    levels): an engine declares what it reads; the refusal names the
    exact missing descriptor and the row to put it on."""
    have = descriptors_for_state(manager, subject_state_key,
                                 scale_level=scale_level)
    missing = [d for d in needed if d not in have]
    if not missing:
        return {'ok': True,
                'descriptors': {d: have[d] for d in needed}}
    where = (f'a ScaleStructureDefinition row for '
             f'{subject_state_key!r}'
             + (f' at L{scale_level}' if scale_level is not None
                else ''))
    return {
        'ok': False,
        'refusal': f'state {subject_state_key!r} is missing '
                   f'structure descriptors {missing}',
        'missing': missing,
        'suggestion': f'add {missing} to descriptors_json on {where} '
                      "(status 'defined' or 'partial' — 'planned' "
                      'counts as absent), with evidence for how each '
                      'value is known',
    }
