"""
@module cmod.custom.fsc_link

fsc-0 (FIRMWARE_SCORE_PROFILES_PLAN.md section 2): the LINK between a Mission Solution (one solve candidate) and the firmware that realises it, and the derived words
  finished  = built AND every Purpose of the Mission proven (on the twin now; on hardware later)
  plan      = anything else that does not fail (a candidate nobody built, or built but with a Purpose unproven) - listed as plan, never finished
  failed    = cmod.custom.fsc_failure.failure_of(candidate)

A BUILT CONFIG is a `board.custom.variants` firmware variant (the seven the UNO has: uno-light, -pcint, -analog, -sense-poll, -sense-pcint, uno-sim-rig, uno-button-clock). Its ROUTES are
DERIVED from the variant's own features and knobs (led -> drive-led, button + button_route -> read-button, sense + sense_route -> sense-led-line, commands -> receive-command and
report-state, adc -> read-temperature) - never typed in. A config resolves to a candidate when it carries a route for EVERY job the Mission needs and the candidate's route of each
job is one of them. A config that does not (no sense line, or a different job set) matches NO candidate, and is listed with why - it is a partial realisation of this Mission.
Where a FirmwareSolution ROW of the same name exists (uno-light, uno-button-clock, uno-sim-rig) the link names it; the others are FirmwareVariants and are linked as such.
"""
import json

LADDER = {'planned': 0, 'failing': 0, 'compiles': 0, 'declared': 0, 'template-exists': 0, 'proven-on-twin': 50, 'proven-on-hardware': 100}
BUILT_OK = ('compiles', 'proven-on-twin', 'proven-on-hardware')


def _j(s, d):
    try:
        return json.loads(s) if isinstance(s, str) and s else (s or d)
    except ValueError:
        return d


def config_routes(variant):
    """-> {job: [route, ...]} DERIVED from a firmware variant dict (features_json / knobs_json)."""
    f, k = _j(variant.get('features_json'), {}), _j(variant.get('knobs_json'), {})
    out = {}
    if f.get('led'):
        out.setdefault('drive-led', []).append('gpio-out')
    if f.get('pwm'):
        out.setdefault('drive-led', []).append('pwm')
    if f.get('button'):
        out['read-button'] = [{'pcint': 'pin-change-interrupt', 'adc': 'analog-threshold'}.get(k.get('button_route'), 'ext-interrupt')]
    if f.get('sense'):
        out['sense-led-line'] = [{'poll': 'gpio-poll', 'pcint': 'pin-change-interrupt'}.get(k.get('sense_route'), 'ext-interrupt')]
    if f.get('commands'):
        out['receive-command'] = ['uart-rx-interrupt']
        out['report-state'] = ['uart-tx']
    if f.get('adc'):
        out['read-temperature'] = ['analog-sensor']
    return out


def config_pins(variant):
    """{Mission role: 'D<n>'} the variant's own pin knobs, for comparison with a candidate's placement."""
    k = _j(variant.get('knobs_json'), {})
    out = {}
    for role, key in (('the button', 'button_pin'), ('the LED', 'led_pin'), ('the sense line', 'sense_pin')):
        if isinstance(k.get(key), int):
            out[role] = 'D%d' % k[key]
    return out


def configs(manager=None):
    from board.custom import variants as V
    rows = {v['name']: v for v in V.SEED_FIRMWARE_VARIANTS}
    for r in ((getattr(manager, 'objectTables', None) or {}).get('FirmwareVariant') or {}).values():
        rows[getattr(r, 'name', '')] = {k: getattr(r, k, '') for k in ('name', 'features_json', 'knobs_json', 'title')}
    return rows


def firmware_solution_names(manager=None):
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    names = {r['name'] for n, _c, rs in CMOD_SEED_PAIRS if n == 'FirmwareSolution' for r in rs}
    names |= {getattr(r, 'name', '') for r in ((getattr(manager, 'objectTables', None) or {}).get('FirmwareSolution') or {}).values()}
    return names


def resolve(jobs, candidates, manager=None):
    """-> (links, unmatched). links = {candidate id: {config, solution, kind, pins_agree, pins_note}} (one config -> the best-ranked candidate whose routes it implements, pins agreeing
    first); unmatched = [{config, why}] for every config that realises no candidate of this Mission."""
    fs = firmware_solution_names(manager)
    links, unmatched = {}, []
    for name, var in sorted(configs(manager).items()):
        routes = config_routes(var)
        lacking = [j for j in jobs if j not in routes]
        if lacking:
            unmatched.append({'config': name, 'why': 'carries no route for the job(s) %s that this Mission needs (it realises %s) - a partial realisation of this Mission'
                                                        % (', '.join(lacking), ', '.join('%s via %s' % (j, '/'.join(r)) for j, r in sorted(routes.items())) or 'nothing it needs')})
            continue
        hits = [c for c in candidates if all(c['routes'].get(j) in routes[j] for j in jobs)]
        if not hits:
            unmatched.append({'config': name, 'why': 'no solve candidate uses its routes (%s)' % ', '.join('%s via %s' % (j, '/'.join(routes[j])) for j in jobs)})
            continue
        want = config_pins(var)

        def agree(c):
            got = {a['role']: a['pin'] for a in c['assignment']}
            return all(got.get(role) == pin for role, pin in want.items())
        hits.sort(key=lambda c: (not agree(c), c['rank']))
        c = hits[0]
        got = {a['role']: a['pin'] for a in c['assignment']}
        agrees = agree(c)
        note = ('the candidate places the pins where the build does (%s)' % ', '.join('%s %s' % (r, p) for r, p in sorted(want.items()))) if agrees else (
            'the build wires %s but the candidate places %s: the routes match, the pin choice is the solver\'s' % (
                ', '.join('%s %s' % (r, p) for r, p in sorted(want.items())), ', '.join('%s %s' % (r, got.get(r, '?')) for r in sorted(want))))
        prior = links.get(c['id'])
        if prior is None:
            links[c['id']] = {'config': name, 'solution': name if name in fs else '', 'kind': 'FirmwareSolution' if name in fs else 'FirmwareVariant',
                              'pins_agree': agrees, 'pins_note': note, 'all_candidates': len(hits)}
        else:
            unmatched.append({'config': name, 'why': 'resolves to the same candidate as %s' % prior['config']})
    return links, unmatched


def built_state(config, jobs, ctx, manager=None):
    """-> (built bool, why, route_status {job: status}) - built when every route the config carries that has atoms is at least `compiles` (IV.status)."""
    from cmod.custom import isotope_variants as IV
    var = configs(manager).get(config) or {}
    routes = config_routes(var)
    st, bad = {}, []
    for j in jobs:
        for r in routes.get(j, []):
            v = (ctx['variants'].get(j) or {}).get(r)
            s = IV.status(v, manager)['status'] if v is not None else 'declared'
            st['%s:%s' % (j, r)] = s
            if s not in BUILT_OK:
                bad.append('%s:%s is %s' % (j, r, s))
    return (not bad), ('every route the build carries compiles (%s)' % ', '.join('%s %s' % kv for kv in sorted(st.items())) if not bad else '; '.join(bad)), st


def purposes_proof(mission_ctx, manager=None, unprovable='block'):
    """-> ({purpose: (status, why)}, all_proven bool, ladder_mean). Read off cmod.custom.capabilities.derive_status (the latest evidential ScenarioRun); with no live manager the
    seeded status is read back unchanged and said so. A Purpose with NO acceptance scenario (the boot Purpose `initialization` has none today) can never be proven: it is shown as
    `unprovable` and, by default (`unprovable='block'`, the owner's "every Purpose proven"), keeps every solution from being finished; `unprovable='ignore'` leaves it out of the test."""
    from cmod.custom import capabilities as CAP
    out = {}
    for p in mission_ctx['purposes']:
        cap = CAP.find(p['purpose'])
        if cap is None:
            out[p['purpose']] = ('planned', 'no such Purpose row')
            continue
        if not cap.get('acceptance_scenario'):
            out[p['purpose']] = ('unprovable', 'no acceptance_scenario is defined for this Purpose, so nothing can prove it')
            continue
        status, proof, why, _kind = CAP.derive_status(cap, manager=manager)
        out[p['purpose']] = (status, proof or why)
    counted = {p: v for p, v in out.items() if not (unprovable == 'ignore' and v[0] == 'unprovable')}
    ok = bool(counted) and all(s in ('proven-on-twin', 'proven-on-hardware') for s, _w in counted.values())
    mean = sum(LADDER.get(s, 0) for s, _w in counted.values()) / float(len(counted) or 1)
    return out, ok, mean


def state_of(c, link, ctx, proof, manager=None):
    """-> {state: finished|plan, why}. `proof` = purposes_proof(...)."""
    if link is None:
        return {'state': 'plan', 'why': 'no built firmware realises this plan (not one of the built configs)'}
    built, bwhy, _st = built_state(link['config'], list(c['routes']), ctx, manager)
    statuses, ok, _m = proof
    if not built:
        return {'state': 'plan', 'why': 'config %s is not built: %s' % (link['config'], bwhy)}
    if manager is None:
        return {'state': 'plan', 'why': 'config %s is built (%s) but no live server is attached, so no ScenarioRun can be read: proof is never taken from seeded status words' % (link['config'], bwhy)}
    if not ok:
        unp = ', '.join('%s (%s%s)' % (p, s, ': ' + w if s == 'unprovable' else '') for p, (s, w) in sorted(statuses.items()) if s not in ('proven-on-twin', 'proven-on-hardware'))
        return {'state': 'plan', 'why': 'config %s is built (%s) but not every Purpose is proven: %s' % (link['config'], bwhy, unp)}
    return {'state': 'finished', 'why': 'config %s is built (%s) and every Purpose is proven (%s)' % (link['config'], bwhy, '; '.join('%s %s' % (p, s) for p, (s, _w) in sorted(statuses.items())))}
