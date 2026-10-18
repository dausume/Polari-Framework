"""
@module cmod.custom.fsc_link

fsc-0 (FIRMWARE_SCORE_PROFILES_PLAN.md section 2): the LINK between a Mission Solution (one solve candidate) and the firmware that realises it, and the derived words
  finished  = built AND every Purpose of the Mission proven (on the twin now; on hardware later)
  plan      = anything else that does not fail (a candidate nobody built, or built but with a Purpose unproven) - listed as plan, never finished
  failed    = cmod.custom.fsc_failure.failure_of(candidate)

A BUILT CONFIG is a `board.custom.variants` firmware variant (the UNO has twelve: uno-light, -pcint, -analog, -v2, -sense-poll, -sense-pcint, uno-sim-rig, -blink-only, -adc-sweep, -pair, -echo,
uno-button-clock). Its ROUTES are DERIVED from the variant's own features and knobs (led -> drive-led, button + button_route -> read-button, sense + sense_route -> sense-led-line, commands ->
receive-command and report-state, adc -> read-temperature) - never typed in. Three outcomes for a config against a Mission:
  - it carries a route for EVERY job the Mission needs: it resolves to the candidate whose routes it implements (`resolve`);
  - it was BUILT FOR THIS MISSION (it carries a route for the job that triggers each Purpose of the Mission: the button, the command and the periodic report - `TRIGGER_JOB`) but lacks the route for
    some other job: the owner's rule "Anything that does not fulfill all purposes is just a failure" makes it a FAILURE naming the Purposes that job serves (`misses`), with no score;
  - it lacks a trigger job (uno-sim-rig has no button, uno-echo no light): it was built for another job, is not a candidate for this Mission, and is listed as such (`resolve`'s `unmatched`).
Where a FirmwareSolution ROW of the same name exists (uno-light, uno-button-clock, uno-sim-rig) the link names it; the others are FirmwareVariants and are linked as such.

PROOF OF A CONFIG (the honest reading): a Purpose is proven for a config ONLY by a passed ScenarioRun of THAT config's own firmware - a run whose `variant` is the config and whose Scenario
proves that Purpose (`purposes_proof(..., config=)`). A run on another config proves nothing for this one, because the compiled firmware differs (the sense routes, the button routes and the wire
class are different code). A Scenario that proves the ISOTOPE of a route (sense-poll-line-acceptance, light-pcint-button-acceptance, ...) restates a catalogue route, not a Purpose of a Mission, so
it counts toward the config's BUILT state (cmod.custom.isotope_variants.status) and not toward its Purposes. `finished` = built AND every Purpose of the Mission proven for that config.
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


#: the job that TRIGGERS each kind of Purpose (a press -> read-button, a command from Polari -> receive-command, the periodic report -> report-state); `boot` has no job of its own
TRIGGER_JOB = {'button': 'read-button', 'command': 'receive-command', 'period': 'report-state'}


def attempt_of(routes, ctx):
    """-> (built_for_this_mission bool, words). True when the config carries a route for the trigger job of every Purpose of the Mission (a Purpose whose trigger kind is not in TRIGGER_JOB is not asked)."""
    need = sorted({TRIGGER_JOB[(p.get('trigger') or {}).get('kind')] for p in (ctx or {}).get('purposes', []) if (p.get('trigger') or {}).get('kind') in TRIGGER_JOB})
    gone = [j for j in need if j not in routes]
    have = ', '.join('%s via %s' % (j, '/'.join(r)) for j, r in sorted(routes.items())) or 'nothing'
    if not need:
        return False, 'the Mission states no trigger the configs can be matched on (it realises %s)' % have
    if gone:
        return False, "it was built for another job: it realises %s and carries no route for %s, the job(s) that trigger this Mission's Purposes" % (have, ', '.join(gone))
    return True, 'it carries a route for every trigger job of this Mission (%s)' % ', '.join(need)


def misses(jobs, ctx, manager=None):
    """-> failure rows [{kind 'purpose-unfulfilled', purpose, reason, id, solution (the config), routes, hardware, rank None, state 'failed', config}] for every config that was BUILT FOR this
    Mission (attempt_of) but carries no route for some job of it. The Purposes named are the ones that job serves in this Mission (ctx job_purposes), never typed in."""
    out = []
    for name, var in sorted(configs(manager).items()):
        routes = config_routes(var)
        lacking = [j for j in jobs if j not in routes]
        if not lacking or not attempt_of(routes, ctx)[0]:
            continue
        purposes = sorted({p for j in lacking for p in ctx['job_purposes'].get(j, [])})
        have = ', '.join('%s via %s' % (j, '/'.join(r)) for j, r in sorted(routes.items()))
        named = ', '.join(purposes) or 'the Mission'
        why = ('config %s is built for this Mission and realises %s, but it has no route for %s, which %s need%s: so it does not fulfil %s, and a firmware that does not fulfil all the Purposes is a failure'
               % (name, have, ', '.join(lacking), named, 's' if len(purposes) == 1 else '', named))
        out.append({'kind': 'purpose-unfulfilled', 'purpose': ', '.join(purposes), 'reason': why, 'id': 'config:%s' % name, 'solution': name, 'config': name, 'routes': have,
                    'hardware': var.get('board_definition') or 'arduino-uno-r3', 'rank': None, 'state': 'failed'})
    return out


def resolve(jobs, candidates, manager=None, ctx=None):
    """-> (links, unmatched). links = {candidate id: {config, solution, kind, pins_agree, pins_note}} (one config -> the best-ranked candidate whose routes it implements, pins agreeing
    first); unmatched = [{config, why}] for every config that is not a candidate of this Mission (built for another job, or no solve candidate uses its routes). A config built FOR
    this Mission that lacks a job is not listed here: `misses` makes it a failure."""
    fs = firmware_solution_names(manager)
    links, unmatched = {}, []
    for name, var in sorted(configs(manager).items()):
        routes = config_routes(var)
        lacking = [j for j in jobs if j not in routes]
        if lacking:
            built_for, words = attempt_of(routes, ctx)
            if not built_for:
                unmatched.append({'config': name, 'why': 'not a candidate for this Mission: %s' % words})
            continue     # built for this Mission but short of a job: a FAILURE (`misses`), not "unmatched"
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


def _config_runs(config, purpose, manager):
    """The ScenarioRuns of THIS config's firmware that prove `purpose`: the run's `variant` is the config and its Scenario's `capability` is the Purpose."""
    from firmwarefaults.custom import acceptance as ACC
    scen = {s['name'] for s in ACC.ACCEPTANCE_SCENARIOS if s.get('capability') == purpose}
    rows = ((getattr(manager, 'objectTables', None) or {}).get('ScenarioRun') or {}).values()
    return sorted((r for r in rows if getattr(r, 'scenario', '') in scen and getattr(r, 'variant', '') == config and getattr(r, 'outcome', '') != 'undetermined'),
                  key=lambda r: getattr(r, 'ran_at', ''))


def _config_status(config, purpose, manager):
    runs = _config_runs(config, purpose, manager)
    if not runs:
        return 'planned', "no ScenarioRun of config %s's own firmware proves %s (a run on another config proves nothing for this one)" % (config, purpose)
    last = runs[-1]
    if last.outcome != 'passed':
        return 'planned', 'the latest run of %s on %s (%s) did not pass: %s' % (last.scenario, config, last.name, getattr(last, 'verdict_words', ''))
    try:
        mode = json.loads(getattr(last, 'repro_json', '{}') or '{}').get('mode', 'digital-twin')
    except ValueError:
        mode = 'digital-twin'
    return ('proven-on-hardware' if mode == 'hardware' else 'proven-on-twin'), 'ScenarioRun %s @ %s on %s' % (last.name, getattr(last, 'ran_at', ''), config)


def purposes_proof(mission_ctx, manager=None, unprovable='block', config=None):
    """-> ({purpose: (status, why)}, all_proven bool, ladder_mean). With `config`: the proof of THAT config's firmware (see the module docstring - only its own runs count). Without: the Purpose's
    status read off cmod.custom.capabilities.derive_status (the latest evidential run of its acceptance Scenario, whichever config ran it) - used for the cache key and the Mission-level view.
    With no live manager nothing is proven (the seeded status is never evidence). A Purpose with NO acceptance scenario can never be proven: it is `unprovable` and, by default
    (`unprovable='block'`, the owner's "every Purpose proven"), keeps every solution from being finished; `unprovable='ignore'` leaves it out. (All four Purposes of the UNO light Mission
    have one since fsc-0b: initialization-acceptance.)"""
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
        if config is not None:
            out[p['purpose']] = _config_status(config, p['purpose'], manager) if manager is not None else ('planned', 'no live server: no ScenarioRun can be read')
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
        unp = '; '.join('%s (%s: %s)' % (p, s, w) for p, (s, w) in sorted(statuses.items()) if s not in ('proven-on-twin', 'proven-on-hardware'))
        return {'state': 'plan', 'why': 'config %s is built (%s) but not every Purpose is proven: %s' % (link['config'], bwhy, unp)}
    return {'state': 'finished', 'why': 'config %s is built (%s) and every Purpose is proven (%s)' % (link['config'], bwhy, '; '.join('%s %s' % (p, s) for p, (s, _w) in sorted(statuses.items())))}
