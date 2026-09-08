"""
@module pspp.custom.structure_groups

gsp-1/gsp-4 (GEOPOLYMER_STRUCTURE_SAMPLING_PLAN): the most-likely
structural groups of a stochastic (amorphous) material, as ranked
Q-species motif fractions.

Two honest entry modes:
- REFERENCE (cation, MR): straight off the digitized Maekawa glass
  curves / the Table 5.6 glass->solution mapping via
  pspp.custom.q_distribution — bands and refusals ride along unchanged.
- STATE (material[, state]): a resolved MaterialState whose structure
  rows carry a ``qDistribution`` descriptor (fractions or percents by
  motif). No descriptor -> evidence-bearing refusal naming the exact
  knob; this NEVER guesses a distribution for a state.

Q-species are structural MOTIFS (see pspp.material_structure_basis) — these
summaries never replace an underlying network representation.

@consumers
  - pspp.pspp_api (/api/pspp/structure/groups)
  - pspp.custom.structure_sampling (target fractions for ensemble samples)
  - pspp.structure_groups_selftest
"""

from pspp.material_structure_basis import descriptors_for_state
from pspp.custom.q_distribution import (
    _Q4_ARTIFACT_CAVEAT,
    glass_to_solution_q,
    q_glass_distribution,
)
from pspp.custom.state_resolution import resolve_state

MOTIFS = ('Q0', 'Q1', 'Q2', 'Q3', 'Q4')

MOTIF_DESCRIPTIONS = {
    'Q0': 'isolated SiO4/AlO4 tetrahedron (monomer) — 0 bridging O',
    'Q1': 'chain-end tetrahedron — 1 bridging O',
    'Q2': 'chain/ring middle tetrahedron — 2 bridging O',
    'Q3': 'branching (sheet) tetrahedron — 3 bridging O',
    'Q4': 'fully cross-linked framework tetrahedron — 4 bridging O',
}

#: qDistribution descriptor values are accepted as fractions (sum~1)
#: or percents (sum~100); anything else is refused, never rescaled
#: silently past this tolerance.
_SUM_TOLERANCE = 0.15


def _normalized_fractions(values):
    """{motif: number} -> ({motif: fraction}, assumptions[]) | None.
    Accepts fraction- or percent-scaled inputs within tolerance."""
    try:
        raw = {m: float(values[m]) for m in MOTIFS if m in values}
    except (TypeError, ValueError):
        return None
    if not raw or any(v < 0 for v in raw.values()):
        return None
    total = sum(raw.values())
    if total <= 0:
        return None
    assumptions = []
    for scale, label in ((1.0, 'fractions'), (100.0, 'percents')):
        if abs(total - scale) <= _SUM_TOLERANCE * scale:
            if abs(total - scale) > 1e-9:
                assumptions.append(
                    f'{label} summed to {total:.4g}, not {scale:g} '
                    f'(digitization drift) — normalized')
            return ({m: v / total for m, v in raw.items()}, assumptions)
    return None


def _ranked_groups(fractions):
    ranked = sorted(fractions.items(), key=lambda kv: -kv[1])
    return [{'motif': motif,
             'fraction': round(fraction, 4),
             'rank': index + 1,
             'description': MOTIF_DESCRIPTIONS[motif]}
            for index, (motif, fraction) in enumerate(ranked)]


def reference_groups(cation, mr, physical_state='glass',
                     datasets=None):
    """Ranked motif fractions for a (Na|K) silicate at one MR, from
    the digitized reference curves. physical_state: glass | solution
    (solution only at the Table 5.6 listed MRs, Na only)."""
    caveats = []
    if physical_state == 'glass':
        verdict = q_glass_distribution(cation, mr, datasets=datasets)
        if not verdict.get('ok'):
            return verdict
        values, evidence = verdict['values'], verdict.get('evidence')
        band = verdict.get('band')
    elif physical_state == 'solution':
        if cation != 'Na':
            return {'ok': False,
                    'refusal': 'glass->solution mapping exists only '
                               'for the Na system (Table 5.6)',
                    'suggestion': "physicalState='glass' works for "
                                  "both Na and K"}
        verdict = glass_to_solution_q(mr, datasets=datasets)
        if not verdict.get('ok'):
            return verdict
        values, evidence = verdict['solution'], verdict.get('evidence')
        band = None
        caveats.append(_Q4_ARTIFACT_CAVEAT)
    else:
        return {'ok': False,
                'refusal': f'unknown physicalState '
                           f'{physical_state!r}',
                'suggestion': "use 'glass' or 'solution'"}
    normalized = _normalized_fractions(values)
    if normalized is None:
        return {'ok': False,
                'refusal': 'reference values did not resolve to a '
                           'usable Q0-Q4 distribution',
                'suggestion': 'inspect the DigitizedDataset row — '
                              'motif columns must be non-negative '
                              'fractions or percents'}
    fractions, assumptions = normalized
    return {
        'ok': True, 'mode': 'reference', 'cation': cation, 'MR': mr,
        'physicalState': physical_state,
        'groups': _ranked_groups(fractions),
        'caveats': caveats,
        'assumptions': assumptions + list(
            verdict.get('assumptions') or []),
        'band': band, 'evidence': evidence,
    }


def state_groups(manager, material, state=None):
    """Ranked motif fractions for one resolved MaterialState, read
    from its structure rows' qDistribution descriptor (gsp-4)."""
    resolved = resolve_state(manager, material, state)
    if not resolved.get('ok'):
        return resolved
    state_key = resolved['stateKey']
    descriptors = descriptors_for_state(manager, state_key)
    entry = descriptors.get('qDistribution')
    if entry is None:
        return {
            'ok': False, 'mode': 'state', 'stateKey': state_key,
            'refusal': f'state {state_key!r} has no qDistribution '
                       'structure descriptor',
            'suggestion': 'record one on a ScaleStructureDefinition '
                          'row for this state (descriptors_json.'
                          'qDistribution = {Q0..Q4}), or query '
                          'reference mode (cation+MR) for the '
                          'parent solution/glass',
        }
    normalized = _normalized_fractions(entry['value'])
    if normalized is None:
        return {
            'ok': False, 'mode': 'state', 'stateKey': state_key,
            'refusal': 'qDistribution descriptor present but not a '
                       'usable {Q0..Q4} distribution',
            'suggestion': f"fix descriptors_json.qDistribution on "
                          f"row {entry['sourceRow']!r} — non-negative "
                          'fractions (sum~1) or percents (sum~100)',
        }
    fractions, assumptions = normalized
    return {
        'ok': True, 'mode': 'state', 'stateKey': state_key,
        'material': material,
        'state': (resolved.get('state') or {}).get('stateName'),
        'groups': _ranked_groups(fractions),
        'caveats': [], 'assumptions': assumptions,
        'sourceRow': entry['sourceRow'],
        'scaleLevel': entry['scaleLevel'],
        'evidence': f"qDistribution descriptor on structure row "
                    f"{entry['sourceRow']!r}",
    }


def inventory_q_fractions(inventory, species=None, alias_of=None):
    """Map an inventory's quantified qn-carrying species populations
    to Q-motif fractions (shared by geopolymer stepped mode and the
    sol-gel library). alias_of: {alias: canonical} — an alias resource
    is skipped whenever its canonical is quantified (one resource
    under two names, never double-counted). Returns {ok, fractions,
    unmappedQuantified, presentUnquantified, aliasNote?} | refusal."""
    from pspp.reaction_network_basis import SEED_CHEMICAL_SPECIES
    rows = species if species is not None else SEED_CHEMICAL_SPECIES
    alias_of = alias_of or {}
    qn_of = {r['name'] if isinstance(r, dict)
             else getattr(r, 'name', ''):
             (r.get('qn', -1) if isinstance(r, dict)
              else getattr(r, 'qn', -1)) for r in rows}
    mapped = {m: 0.0 for m in MOTIFS}
    unmapped_quantified = {}
    present_unquantified = []
    for name, amount in inventory.items():
        if amount is None:
            present_unquantified.append(name)
            continue
        if amount <= 0:
            continue
        canonical = alias_of.get(name)
        if canonical is not None \
                and inventory.get(canonical) is not None:
            continue  # aliased resource — counted once
        qn = qn_of.get(name, -1)
        if 0 <= qn <= 4:
            mapped[f'Q{qn}'] += float(amount)
        else:
            unmapped_quantified[name] = amount
    total = sum(mapped.values())
    if total <= 0:
        return {'ok': False,
                'refusal': 'no qn-carrying species remain quantified '
                           'in this inventory',
                'unmappedQuantified': unmapped_quantified,
                'suggestion': 'fewer/other steps — or record the '
                              'product state\'s distribution as a '
                              'qDistribution descriptor once measured'}
    return {'ok': True,
            'fractions': {m: v / total for m, v in mapped.items()},
            'unmappedQuantified': unmapped_quantified,
            'presentUnquantified': sorted(present_unquantified)}


def stepped_groups(cation, mr, steps=None, site=None, conditions=None,
                   datasets=None, species=None):
    """gsp-4b: Q-motif fractions AFTER scientist-driven network steps.
    Starts from the measured solution inventory, applies each step
    ({rule, times?, site?}) via network_stepping.step_once, then maps
    the surviving qn-carrying species populations to fractions —
    honest about every quantified species that carries NO qn (its Si
    share cannot enter the fractions) and everything present but
    unquantified."""
    from pspp.custom.network_stepping import solution_inventory, step_once

    start = solution_inventory(cation, mr, datasets=datasets)
    if not start.get('ok'):
        return start
    inventory = dict(start['inventory'])
    assumptions = list(start.get('assumptions') or [])
    applied = []
    for index, step in enumerate(steps or []):
        verdict = step_once(
            inventory, step.get('rule', ''),
            site=step.get('site', site),
            conditions=step.get('conditions', conditions),
            cation=cation, times=int(step.get('times', 1)))
        if not verdict.get('ok'):
            verdict['stepIndex'] = index
            verdict['applied'] = applied
            return verdict
        inventory = verdict['inventory']
        applied.append({'rule': verdict['rule'],
                        'times': verdict['times']})
        for note in verdict.get('assumptions') or []:
            if note not in assumptions:
                assumptions.append(note)

    mapping = inventory_q_fractions(
        inventory, species=species,
        alias_of={'di-siloxonate': 'siloxonate-q1'})
    if not mapping['ok']:
        mapping['mode'] = 'stepped'
        return mapping
    fractions = mapping['fractions']
    unmapped_quantified = mapping['unmappedQuantified']
    present_unquantified = mapping['presentUnquantified']
    if unmapped_quantified:
        assumptions.append(
            'fractions cover ONLY qn-carrying species — quantified '
            f'but unmapped: {sorted(unmapped_quantified)} (their Si '
            'share is outside the Q ledger)')
    return {
        'ok': True, 'mode': 'stepped', 'cation': cation, 'MR': mr,
        'stepsApplied': applied,
        'groups': _ranked_groups(fractions),
        'caveats': [_Q4_ARTIFACT_CAVEAT],
        'assumptions': assumptions,
        'unmappedQuantified': unmapped_quantified,
        'presentUnquantified': sorted(present_unquantified),
        'evidence': start.get('evidence'),
    }


def most_likely_groups(manager=None, material=None, state=None,
                       cation=None, mr=None, physical_state='glass',
                       datasets=None):
    """Dispatcher: state mode when material given, else reference."""
    if material:
        return state_groups(manager, material, state)
    if cation is None or mr is None:
        return {'ok': False,
                'refusal': 'need either material[+state] or '
                           'cation+MR',
                'suggestion': 'reference mode: ?cation=Na&mr=1.0 — '
                              'state mode: ?material=<name>'
                              '[&state=<state>]'}
    return reference_groups(cation, mr, physical_state=physical_state,
                            datasets=datasets)
