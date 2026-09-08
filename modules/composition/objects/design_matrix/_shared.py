"""@module composition.objects.design_matrix._shared — what the design_matrix row classes share (constants, seeds, helpers); split from design_matrix_basis.py (sap-2c)."""
import json
from composition.custom.data_refs import resolve_named

COUPLINGS = ('direct', 'inverse', 'both')
def classify(entries):
    """Derive uncoupled/decoupled/coupled + the tuning order, and
    surface ratio-trap findings. Pure function over entry dicts."""
    bad = [e for e in entries
           if e.get('coupling') not in COUPLINGS]
    if bad:
        return {'ok': False,
                'refusal': f'entries with unknown coupling: '
                           f'{[e.get("coupling") for e in bad]} — '
                           f'one of {COUPLINGS}'}
    knobs, outcomes = [], []
    for e in entries:
        if e['knob'] not in knobs:
            knobs.append(e['knob'])
        if e['outcome'] not in outcomes:
            outcomes.append(e['outcome'])
    if not entries:
        return {'ok': False,
                'refusal': 'an empty matrix classifies nothing — '
                           'state at least one knob→outcome entry'}
    affects = {o: {e['knob'] for e in entries if e['outcome'] == o}
               for o in outcomes}
    drives = {k: {e['outcome'] for e in entries if e['knob'] == k}
              for k in knobs}
    uncoupled = (all(len(s) == 1 for s in affects.values())
                 and all(len(s) == 1 for s in drives.values()))
    # Triangularization by elimination: repeatedly retire an
    # outcome whose REMAINING driver set is a single knob (its
    # lead), or empty (fully set by knobs already ordered).
    remaining_out = {o: set(s) for o, s in affects.items()}
    remaining_knobs = set(knobs)
    order = []
    while remaining_out:
        step = None
        for o in outcomes:
            if o not in remaining_out:
                continue
            live = remaining_out[o] & remaining_knobs
            if len(live) <= 1:
                step = (o, next(iter(live)) if live else None)
                break
        if step is None:
            break
        o, k = step
        del remaining_out[o]
        if k is not None:
            remaining_knobs.discard(k)
            order.append({'knob': k, 'outcome': o})
    coupled_block = sorted(remaining_out) if remaining_out else []
    classification = ('uncoupled' if uncoupled else
                      'coupled' if coupled_block else 'decoupled')
    findings = []
    for e in entries:
        if e.get('coupling') == 'both':
            findings.append({
                'kind': 'ratio-trap',
                'knob': e['knob'], 'outcome': e['outcome'],
                'via': e.get('via', ''),
                'warning': f'"{e["knob"]}" feeds BOTH terms of '
                           f'"{e["outcome"]}" — more is NOT '
                           f'monotonically better, and any screen '
                           f'that stores it as an improvement gets '
                           f'this case wrong (handover §3.1)'})
    if classification == 'coupled':
        findings.append({
            'kind': 'coupled-block', 'outcomes': coupled_block,
            'warning': 'no tuning order exists for these outcomes: '
                       'optimising one silently moves the others — '
                       'the mag-22 failure shape. Surface the '
                       'cross-terms; do not optimise through them '
                       'blind'})
    return {
        'ok': True, 'knobs': knobs, 'outcomes': outcomes,
        'classification': classification,
        'tuningOrder': [s['knob'] for s in order]
        if classification == 'decoupled' else
        (knobs if classification == 'uncoupled' else []),
        'leadPairs': order,
        'coupledOutcomes': coupled_block,
        'findings': findings,
        'wellFormedNote': (
            'a characteristic equation set is WELL-FORMED when you '
            'can state it as N knobs → N outcomes with a tuning '
            'order (handover §2.5). This one '
            + {'uncoupled': 'is fully independent — tune in any '
                            'order.',
               'decoupled': 'has a required order — follow it and '
                            'each knob is set once.',
               'coupled': 'is NOT well-formed as stated — the '
                          'coupling is the thing to surface.'}[
                classification]),
    }
def matrix_report(manager, matrix_name):
    row, refusal = resolve_named(manager, 'DesignMatrixDefinition',
                                 matrix_name)
    if refusal:
        return {'ok': False, **refusal}
    try:
        entries = json.loads(getattr(row, 'entries_json', '') or '[]')
    except ValueError:
        return {'ok': False, 'matrix': matrix_name,
                'refusal': 'entries_json does not parse'}
    result = classify(entries)
    result['matrix'] = matrix_name
    result['archetype'] = getattr(row, 'archetype_ref', '')
    result['entries'] = entries
    return result
