"""
@module cmod.custom.fsc_failure

fsc-0 (D-fsc-1, his words 2026-10-18: "If it is a deadline flagged as being safety critical then yes it needs to count as a failure. If it is not flagged as safety critical,
then no, it should just be scoring based on how close it gets to it."): a Mission Solution FAILS when
  - a Purpose is LOST (its pins could not be placed while others were), or
  - the pins cannot be placed at all (the hardware is not modelled / no complete placement), or
  - a deadline FLAGGED `safety_critical: true` on the Purpose criterion is violated.
An unflagged deadline violation is NOT a failure (the `deadline-fit` term scores how close it gets). Missing parts are NOT a failure (a cost term). A failed solution is listed
with the Purpose and the reason and NEVER gets a score. A Purpose of importance `safety` whose deadline is not flagged yields a SUGGESTION ("flag this deadline
safety-critical?") - never an auto-flag (knobs-and-suggestions rule).
"""


def failure_of(c):
    """-> None, or {kind, purpose, reason} for the first reason this candidate fails (lost Purpose, unplaceable, safety-critical deadline violated)."""
    if c.get('rank_class') == 4 or c.get('placement') == 'undetermined':
        why = '; '.join(r['text'] for r in c.get('risks', []) if r.get('kind') == 'placement') or 'pins cannot be placed on this hardware'
        return {'kind': 'unplaceable', 'purpose': 'every Purpose', 'reason': why}
    if c.get('lost'):
        names = sorted({p for l in c['lost'] for p in (l.get('purposes') or [l.get('role', '')])})
        why = '; '.join('the %s loses its pins: %s' % (l.get('role', '?'), str(l.get('why', ''))[:160]) for l in c['lost'])
        return {'kind': 'purpose-lost', 'purpose': ', '.join(names), 'reason': why}
    for p in (c.get('cycle') or {}).get('purposes', []):
        crit = p.get('criterion') or {}
        if crit.get('state') == 'violates' and crit.get('safety_critical'):
            return {'kind': 'safety-deadline', 'purpose': p['purpose'],
                    'reason': 'safety-critical deadline violated: %s' % crit.get('why', '')}
    return None


def unflagged_violations(c):
    """The deadlines this candidate misses that are NOT flagged safety-critical - scored by closeness, listed so the miss is never hidden."""
    return [{'purpose': p['purpose'], 'why': (p.get('criterion') or {}).get('why', '')} for p in (c.get('cycle') or {}).get('purposes', [])
            if (p.get('criterion') or {}).get('state') == 'violates' and not (p.get('criterion') or {}).get('safety_critical')]


def suggestions(purposes):
    """One suggestion row per Purpose of importance `safety` that states a deadline without flagging it safety-critical. `purposes` = approach_profile_input.purposes_of rows."""
    out = []
    for p in purposes:
        if p.get('importance') == 'safety' and p.get('deadline_ms') and not p.get('safety_critical'):
            out.append({'purpose': p['purpose'], 'kind': 'flag-deadline-safety-critical',
                        'message': 'Flag this deadline safety-critical? Purpose %s is of importance safety and states %s = %s ms, but the criterion does not say safety_critical: true, '
                                   'so missing it only lowers the deadline-fit score instead of failing the solution.' % (p['purpose'], p.get('deadline_key', 'a deadline'), p['deadline_ms']['value']),
                        'knob': 'criteria[%s].safety_critical' % p.get('deadline_key', ''), 'auto_applied': False})
    return out
