"""
@module board.custom.sim_gate

ins-0/1 (HARDWARE_BENCH_CONVERGENCE_PLAN.md §12): THE CONFIRMED-SIM GATE between a Sim install and a Real install. His words: "Validation via a
sim install is a step we want confirmed by a user before moving to a real install."

Two install MODES (`MODES`): `sim` = the twin (the simavr twin of the UNO, or a twin session on the engines worker), `real` = a detected board on
this host. A Real install of a config is OFFERED only when BOTH hold:

  1. the sim install ran the config's four Purposes on the twin — a passed ScenarioRun of the config's OWN firmware per Purpose of the Mission
     (cmod.custom.fsc_link.purposes_proof(config=…): the same reading the scores page uses; a run on another config proves nothing here);
  2. a person ticked `ATTEST` for the build's EXACT hex — a valid SimInstallConfirmation row (config, hex_sha256, who, when, the run names).

A new hex VOIDS the confirmation (`void_stale`). Until both hold the Real side says, in words, what is missing and offers the sim install
(`verdict()['offer']`). The gate advises; it never blocks a person who says "install anyway" WITH a reason — board.custom.installer records the
reason on the InstallPlan and the InstallRecord (`override_reason`) and the plan's notes say INSTALLED ANYWAY. A variant the Mission's Purposes do
not apply to (a bench test such as uno-echo or uno-blink-only) is not gated: `verdict()['gated']` is False and the words say why.

    verdict(manager, config, hex_sha)                     -> {gated, offered, words, missing[], purposes[], confirmation, offer, attest}
    purpose_runs(manager, config)                         -> [{purpose, scenario, status, run, why}] (status proven-on-twin | proven-on-hardware | planned | unprovable)
    confirm(manager, config, hex_sha, who, source, …)     -> the SimInstallConfirmation row (as a dict); voids the config's rows for other hexes
    void_stale(manager, config, hex_sha)                  -> the rows voided because `hex_sha` is the program now
    confirmations(manager, config='')                     -> the rows as dicts, newest first (a configured table's rows)
    sim_install(manager, config)                          -> runs the four Purposes on the twin HERE (the acceptance runs, stored on this server); refuses with the
                                                             exact command to run elsewhere when this host has no local twin (the proof-push rule)
"""
import datetime
import json

MODES = ('sim', 'real')
ATTEST = 'I checked the simulated board does what the firmware says'
PROVEN = ('proven-on-twin', 'proven-on-hardware')


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def _rows(manager, cls):
    return list(((getattr(manager, 'objectTables', None) or {}).get(cls) or {}).values()) if manager is not None else []


def _refused(msg, status='409 Conflict', **extra):
    from board.custom.installer import InstallRefused
    return InstallRefused(msg, status, **extra)


# ------------------------------------------------------------------ the Mission's Purposes on this config
DEFAULT_MISSION = 'uno-light-mission'   # = cmod.custom.fsc_doors.DEFAULT_MISSION (not imported: that module needs falcon)


def _mission(manager, mission=None):
    from cmod.custom import approach_profile_input as AI
    row = AI.find_mission(mission or DEFAULT_MISSION, manager)
    return row, ({'purposes': AI.purposes_of(row, manager)} if row else {'purposes': []})


def gated(config, manager=None, mission=None):
    """-> (True, why) when the Mission's Purposes apply to `config` (it is a built config of the Mission, so a sim install can prove it), else (False, why)."""
    from cmod.custom import capabilities as CAP
    from cmod.custom import fsc_link
    row, ctx = _mission(manager, mission)
    if row is None or not ctx['purposes']:
        return False, 'no Mission names Purposes here, so no sim proof is modeled — a bench test'
    scen = next(((CAP.find(p['purpose']) or {}).get('acceptance_scenario', '') for p in ctx['purposes']), '')
    why = fsc_link.proof_config_refusal(config, scen, manager, row['name']) if scen else 'the first Purpose has no acceptance scenario'
    if why:
        return False, 'not gated: %s' % why
    return True, 'config %s is a built config of Mission %s: its %d Purposes must pass on the twin before a real board' % (config, row['name'], len(ctx['purposes']))


def purpose_runs(manager, config, mission=None):
    """One entry per Purpose of the Mission: status (fsc_link's reading of THIS config's own ScenarioRuns), the run that proves it, the words."""
    from cmod.custom import capabilities as CAP
    from cmod.custom import fsc_link
    row, ctx = _mission(manager, mission)
    if row is None:
        return []
    statuses, _ok, _mean = fsc_link.purposes_proof(ctx, manager, config=config)
    out = []
    for p in ctx['purposes']:
        status, why = statuses.get(p['purpose'], ('planned', 'no reading'))
        scen = (CAP.find(p['purpose']) or {}).get('acceptance_scenario', '')
        runs = fsc_link._config_runs(config, p['purpose'], manager) if manager is not None else []
        last = runs[-1] if runs else None
        out.append({'purpose': p['purpose'], 'scenario': scen, 'status': status, 'run': getattr(last, 'name', '') if last else '',
                    'ran_at': getattr(last, 'ran_at', '') if last else '', 'outcome': getattr(last, 'outcome', '') if last else '', 'why': why})
    return out


# ------------------------------------------------------------------ confirmations
def _view(r):
    keys = ('name', 'config', 'hex_sha256', 'build', 'who', 'confirmed_at', 'runs_json', 'purposes_passed', 'purposes_total', 'source', 'session',
            'words', 'state', 'voided_at', 'voided_why')
    d = {k: getattr(r, k, '') for k in keys}
    d['hex_short'] = (d['hex_sha256'] or '')[:16]
    d['who_words'] = d['who'] or 'no sign-in on the request'
    return d


def confirmations(manager, config=''):
    rows = [r for r in _rows(manager, 'SimInstallConfirmation') if getattr(r, 'name', '') and (not config or r.config == config)]
    return [_view(r) for r in sorted(rows, key=lambda r: getattr(r, 'confirmed_at', ''), reverse=True)]


def valid_confirmation(manager, config, hex_sha):
    """The newest VALID row for this config at exactly this hex, or None."""
    hits = [r for r in _rows(manager, 'SimInstallConfirmation') if r.config == config and r.state == 'valid' and hex_sha and r.hex_sha256 == hex_sha]
    return _view(max(hits, key=lambda r: r.confirmed_at)) if hits else None


def _save(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:  # noqa: BLE001 — an in-memory manager (selftest) has no db
        pass


def void_stale(manager, config, hex_sha):
    """A new hex voids every valid confirmation of the config made for another hex. -> the voided rows (dicts)."""
    out = []
    for r in _rows(manager, 'SimInstallConfirmation'):
        if r.config == config and r.state == 'valid' and hex_sha and r.hex_sha256 != hex_sha:
            r.state, r.voided_at = 'voided', _now()
            r.voided_why = 'a new program was built for %s (sha256 %s…); the tick was for %s… — look at the new one on the twin and tick again' % (config, hex_sha[:16], (r.hex_sha256 or '')[:16])
            _save(manager, r)
            out.append(_view(r))
    return out


def confirm(manager, config, hex_sha, who='', source='installer', session='', words='', build=''):
    """The person's tick, stored. Refuses (409) without a config or a hex — a tick must name the exact program it is about."""
    from board.board_basis import SimInstallConfirmation
    if not config:
        raise _refused('a confirmation needs the config (the firmware variant) it is about', '400 Bad Request')
    if not hex_sha:
        raise _refused('a confirmation needs the hex sha256 of the exact program looked at (build it, or run it on the twin, first)', '400 Bad Request')
    if source not in ('installer', 'sim-bench', 'cli'):
        source = 'installer'
    if manager is None or getattr(manager, 'objectTables', None) is None:
        raise _refused('no live manager on this server to keep the confirmation on', '422 Unprocessable Entity')
    voided = void_stale(manager, config, hex_sha)
    runs = purpose_runs(manager, config)
    passed = sum(1 for r in runs if r['status'] in PROVEN)
    n = len([r for r in _rows(manager, 'SimInstallConfirmation') if r.config == config]) + 1
    row = SimInstallConfirmation(manager=manager, name='simconf-%s-%d' % (config, n), config=config, hex_sha256=hex_sha, build=build or '', who=who or '',
                                 confirmed_at=_now(), runs_json=json.dumps([{k: r[k] for k in ('purpose', 'scenario', 'run', 'status')} for r in runs]),
                                 purposes_passed=passed, purposes_total=len(runs), source=source, session=session or '', words=(words or ATTEST)[:300],
                                 state='valid')
    _save(manager, row)
    return dict(_view(row), voided=voided)


# ------------------------------------------------------------------ the verdict
def verdict(manager, config, hex_sha='', mission=None):
    """What the Real side shows for one config at one hex: offered or not, and in words what is missing."""
    is_gated, gwhy = gated(config, manager, mission)
    runs = purpose_runs(manager, config, mission) if is_gated else []
    conf = valid_confirmation(manager, config, hex_sha) if is_gated else None
    missing = []
    if is_gated:
        unproven = [r for r in runs if r['status'] not in PROVEN]
        if not runs:
            missing.append('the Mission names no Purposes to run')
        elif unproven:
            missing.append('the sim install has not run every Purpose on the twin yet — %d of %d passed; missing: %s'
                           % (len(runs) - len(unproven), len(runs), ', '.join('%s (%s)' % (r['purpose'], r['status']) for r in unproven)))
        if conf is None:
            others = [c for c in confirmations(manager, config) if c['state'] == 'valid']
            if not hex_sha:
                missing.append('no build to confirm yet — build %s first' % config)
            elif others:
                missing.append('the tick on file is for another program (%s…), not this build (%s…) — look at this one on the twin and tick again'
                               % (others[0]['hex_short'], hex_sha[:16]))
            else:
                missing.append('nobody has ticked "%s" for this program (%s…)' % (ATTEST, hex_sha[:16]))
    offered = (not is_gated) or not missing
    if not is_gated:
        words = 'Real install offered without a sim gate: %s' % gwhy
    elif offered:
        words = 'Real install offered: every Purpose passed on the twin (%s) and %s ticked "%s" at %s for this program (%s…)' % (
            ', '.join(r['run'] for r in runs), conf['who_words'], conf['words'], conf['confirmed_at'], hex_sha[:16])
    else:
        words = 'Real install not offered yet: %s' % '; '.join(missing)
    offer = '' if offered else ('Do the sim install first: install %s into the twin, run its Purposes there, watch it, then tick "%s".' % (config, ATTEST))
    return {'config': config, 'hex_sha256': hex_sha, 'gated': is_gated, 'gate_why': gwhy, 'offered': offered, 'missing': missing, 'words': words,
            'offer': offer, 'purposes': runs, 'confirmation': conf, 'attest': ATTEST,
            'anyway': '' if offered else 'A real install anyway is possible: say why, and the reason is recorded on the plan and the record.'}


# ------------------------------------------------------------------ the sim install's Purposes, run here
def prove_command(config, api=''):
    return 'pol firmware prove %s --api %s' % (config, api or '<this server>')


def sim_install(manager, config, mission=None, api=''):
    """Run the four Purposes of the Mission on `config`'s own build on the twin HERE and store the ScenarioRuns on this server. Refuses, with the exact
    command, when this host has no local twin (the proof-push rule: a remote single-engine worker cannot run the twin build; the runs are then pushed
    from a host that can, e.g. isle-core)."""
    is_gated, gwhy = gated(config, manager, mission)
    if not is_gated:
        raise _refused('no Purposes to run for %s: %s' % (config, gwhy), '409 Conflict')
    from board.custom import light_twin as LT
    ready, why = LT.engine_ready()
    if not ready:
        raise _refused('this server cannot run the twin itself (%s) — run the four Purposes from a host with the simavr twin and push them here: %s'
                       % (why, prove_command(config, api)), '409 Conflict', retry=prove_command(config, api))
    if manager is None or getattr(manager, 'objectTables', None) is None:
        raise _refused('no live manager on this server to store the runs on', '422 Unprocessable Entity')
    from firmwarefaults.custom import acceptance as ACC
    from firmwarefaults.custom.sink import ManagerSink
    sink = ManagerSink(manager)
    out = []
    for p in purpose_runs(manager, config, mission):
        if not p['scenario']:
            out.append(dict(p, outcome='inapplicable', words='no acceptance scenario'))
            continue
        r = ACC.run(p['scenario'], mode='digital-twin', manager=manager, sink=sink, variant=config)
        out.append({'purpose': p['purpose'], 'scenario': p['scenario'], 'run': r['name'], 'outcome': r['outcome'], 'words': r['verdict_words'][:200]})
    return {'config': config, 'runs': out, 'all_passed': bool(out) and all(r['outcome'] == 'passed' for r in out), 'purposes': purpose_runs(manager, config, mission)}
