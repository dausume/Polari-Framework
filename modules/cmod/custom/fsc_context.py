"""
@module cmod.custom.fsc_context

fsc-1: what the value writer needs to know about a MISSION beyond the solve candidates - its Purposes (importance, trigger, deadline, the safety flag), which Purposes use each job
(the shared-route question), the route variants by job, and the importance-weighted SPLIT of anything a route shares (D-fsc-5: "split according to weighting of the importance of a
purpose": safety 4, required 3, important 2, desired 1 - knobs in cmod.custom.fsc_terms).
"""
from cmod.custom import fsc_terms as T


def mission_context(mission, manager=None, importance_weights=None):
    """-> {mission, purposes [{purpose, importance, weight, trigger, deadline_ms, safety_critical, budget_us}], by_name, job_purposes {job: [purpose names]}, variants {job: {route: row}}}."""
    from cmod.custom import approach_profile_input as AI
    from cmod.custom import isotope_variants as IV
    from cmod.custom import solve_inputs as SI
    iw = dict(T.IMPORTANCE_WEIGHTS, **(importance_weights or {}))
    row = SI.mission_row(mission, manager)
    purposes = AI.purposes_of(row, manager)
    pm = SI.mission_profiles(row['name'], None, manager)
    order, by_job, _fixed = SI.job_plan(pm['profiles'], None)
    job_purposes = {j: sorted({p for m in by_job[j] for p in m['purposes']}) for j in order}
    for p in purposes:
        p['weight'] = iw.get(p['importance'], iw['required'])
    return {'mission': row['name'], 'purposes': purposes, 'by_name': {p['purpose']: p for p in purposes}, 'job_purposes': job_purposes, 'importance_weights': iw,
            'variants': {j: {v['route']: v for v in IV.variants(manager, j)} for j in order}}


def split(ctx, purpose_names):
    """The importance-weighted shares of a shared thing among the named Purposes (only those the Mission has). -> ([(purpose, share)], words)."""
    names = [n for n in purpose_names if n in ctx['by_name']]
    if not names:
        return [], 'no Purpose of the Mission uses it'
    tot = sum(ctx['by_name'][n]['weight'] for n in names)
    shares = [(n, ctx['by_name'][n]['weight'] / tot) for n in names]
    if len(names) == 1:
        return shares, 'used by one Purpose (%s), which takes all of it' % names[0]
    return shares, 'shared by %d Purposes, split by importance weight: %s' % (len(names), ', '.join('%s %s %.0f/%.0f = %.0f%%' % (
        n, ctx['by_name'][n]['importance'], ctx['by_name'][n]['weight'], tot, 100 * s) for n, s in shares))
