"""
@module pspp.scale_transfers_basis

Scale transfers as FIRST-CLASS rows (plan pspp-5) — the promotion of
MaterialScaleDefinition's weak derived_from/derivation_method lineage
into citable objects: WHAT moved between which scales of which
states, by which method, under which assumptions, valid where. This
is how Polari proves a material is valid at some scales and not
others (ChatGPT convergence: transfers produce CLAIMS, not values).

Wax is the retrofit proof: the live paraffin lineage (L0 measured →
L1 FEM homogenization 'wax-thermal-continuum' → L4 DFT
'paraffin-quantum-energy') re-expressed as rows WITHOUT changing wax
behavior — the rows cite the same models the msim already runs.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - future pspp transfer-execution (ENGINE_REGISTRY + simulation
    gate, like scale_execution)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from pspp.claims_basis import canonical_subject

TRANSFER_STATUSES = ('declared', 'executed', 'validated')


class ScaleTransferDefinition(treeObject):
    """One cross-scale information transfer between material states."""

    @treeObjectInit
    def __init__(
        self,
        # Unique: '<source_state>@L<a>-><target_state>@L<b>[-variant]'.
        name: str = '',
        source_state_key: str = '',
        source_scale: int = 0,
        target_state_key: str = '',
        target_scale: int = 0,
        # HOW: a registered engine key ('fem.effective-conductivity'),
        # a model ref ('model:wax-thermal-continuum'), or an
        # EvidenceMethod identifier for non-engine transfers
        # ('rules-of-mixtures') — validate_transfer names the options.
        transfer_method: str = '',
        # What the transfer moves (descriptor/property names, JSON).
        transported_json: str = '[]',
        assumptions_json: str = '[]',
        validity_json: str = '{}',
        uncertainty_json: str = '',
        # 'declared' | 'executed' | 'validated'
        status: str = 'declared',
        validation_evidence_json: str = '[]',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.source_state_key = source_state_key
        self.source_scale = source_scale
        self.target_state_key = target_state_key
        self.target_scale = target_scale
        self.transfer_method = transfer_method
        self.transported_json = transported_json
        self.assumptions_json = assumptions_json
        self.validity_json = validity_json
        self.uncertainty_json = uncertainty_json
        self.status = status
        self.validation_evidence_json = validation_evidence_json
        self.provenance_id = provenance_id
        self.notes = notes


def _known_methods():
    """Engine keys + model: refs + evidence identifiers a transfer
    may name. Engine registry import is soft — validation still
    works on instances without the msci engines present."""
    methods = set()
    try:
        from materialsScience.scale_execution import ENGINE_REGISTRY
        methods |= set(ENGINE_REGISTRY)
    except Exception:
        pass
    from pspp.evidence_methods_basis import EVIDENCE_METHOD_VOCAB
    methods |= set(EVIDENCE_METHOD_VOCAB)
    return methods


def validate_transfer(row):
    """Evidence-bearing verdict for one transfer row (or dict)."""
    get = (row.get if isinstance(row, dict)
           else lambda k, d='': getattr(row, k, d))
    problems = []
    for key in ('source_state_key', 'target_state_key'):
        if '#' not in str(get(key, '')):
            problems.append(f"{key} must be a state key "
                            "('<material>#<state>')")
    for key in ('source_scale', 'target_scale'):
        if not 0 <= int(get(key, -1)) <= 4:
            problems.append(f'{key} must be a scale level 0-4')
    method = str(get('transfer_method', ''))
    known = _known_methods()
    if not method:
        problems.append('transfer_method is empty')
    elif not method.startswith('model:') and method not in known:
        problems.append(
            f'unknown transfer_method {method!r} — use a registered '
            f'engine key, an EvidenceMethod identifier, or '
            f"'model:<EngineModelDefinition name>'")
    if get('status', 'declared') not in TRANSFER_STATUSES:
        problems.append(f'status must be one of {TRANSFER_STATUSES}')
    if problems:
        return {'ok': False, 'refusal': '; '.join(problems),
                'suggestion': 'fix the named fields on the '
                              'ScaleTransferDefinition row'}
    return {'ok': True, 'name': get('name', '')}


def transfers_for_state(manager, state_key):
    """All transfers touching one state, summarized — the lineage a
    detail page draws (arrows between scale levels with citations)."""
    rows = (getattr(manager, 'objectTables', None) or {}).get(
        'ScaleTransferDefinition', {})
    rows = rows.values() if isinstance(rows, dict) else rows
    out = []
    for r in rows:
        if state_key not in (getattr(r, 'source_state_key', ''),
                             getattr(r, 'target_state_key', '')):
            continue
        def loads(attr, fallback):
            try:
                return json.loads(getattr(r, attr, '') or fallback)
            except Exception:
                return json.loads(fallback)
        out.append({
            'name': getattr(r, 'name', ''),
            'from': {'state': getattr(r, 'source_state_key', ''),
                     'level': getattr(r, 'source_scale', 0)},
            'to': {'state': getattr(r, 'target_state_key', ''),
                   'level': getattr(r, 'target_scale', 0)},
            'method': getattr(r, 'transfer_method', ''),
            'transported': loads('transported_json', '[]'),
            'assumptions': loads('assumptions_json', '[]'),
            'status': getattr(r, 'status', 'declared'),
        })
    return out


_WAX_PROVENANCE = ('pspp-5 wax retrofit — cites the LIVE msim models '
                   '(wax_multiscale_seed); behavior unchanged, '
                   'lineage promoted to rows')

#: The existing wax lineage as transfer rows (canonical states —
#: pre-pspp wax rows all resolve through '#as-defined', invariant I1).
_PW = canonical_subject('paraffin-wax')
SEED_SCALE_TRANSFERS = [
    {
        'name': f'{_PW}@L0->{_PW}@L1-thermal',
        'source_state_key': _PW, 'source_scale': 0,
        'target_state_key': _PW, 'target_scale': 1,
        'transfer_method': 'model:wax-thermal-continuum',
        'transported_json': json.dumps(
            ['thermalConductivity', 'effectiveK']),
        'assumptions_json': json.dumps(
            ['isotropic matrix', 'inputs object-bound to live L0 '
             'material rows (msim stage 2)']),
        'validity_json': json.dumps(
            {'note': 'solid wax below melt onset'}),
        'status': 'executed',
        'provenance_id': _WAX_PROVENANCE,
    },
    {
        'name': f'{_PW}@L0->{_PW}@L4-quantum',
        'source_state_key': _PW, 'source_scale': 0,
        'target_state_key': _PW, 'target_scale': 4,
        'transfer_method': 'model:paraffin-quantum-energy',
        'transported_json': json.dumps(['totalEnergy']),
        'assumptions_json': json.dumps(
            ['fragment-vs-real-material caveat (DFT fragment)']),
        'validity_json': json.dumps(
            {'note': 'molecular fragment, not bulk'}),
        'status': 'executed',
        'provenance_id': _WAX_PROVENANCE,
    },
]
