"""
@module cmod.custom.solve_inputs

sol-0 (MISSION_PROFILE_SOLVER_PLAN.md section 8.4): what the attempt engine READS, gathered once per run and fingerprinted - never re-derived here, always CALLED:

  the Mission row + objective      cmod.custom.approach_profile_input.find_mission / mission_nocode.settings_of   (mis-0)
  the pin profiles of the Mission  cmod.custom.pin_profile_mission.mission_profiles                               (pp-0)
  the jobs and their variants      cmod.custom.isotope_variants                                                   (iso-0)
  eligibility per board and tier   cmod.custom.isotope_variants_eligibility.eligible                              (iso-0)
  the runtime tiers                cmod.custom.approach_profile (tiers, loop pass, kernel footprints)             (rt-0)
  the bench                        board.custom.pin_profile_bench-style BoardPinNet rows (the pins already wired) and the KitPart rows (via iso-0)
  the sharing verdicts             board.custom.profile_overlap through cmod.custom.mission_colocation.evaluate   (pp-1)

`gather()` returns one plain dict; `fingerprint()` hashes every input by sha256 (the reproducible-initial-conditions rule): the Mission row, the profiles, the
variants, the overlap table, the ladder rule files, the board rows and the tool versions.
"""
import hashlib
import json
import platform
import sys

SOLVER_VERSION = 'sol-0.1'
OBJECTIVES = ('minimum-resources', 'fastest-cycle')
#: the job a Mission profile serves, by its role (iso-0's JOB_ROLE) - the transport is told apart by the line (kind)
TRANSPORT_JOB = {'uart-tx': 'report-state', 'uart-rx': 'receive-command'}
#: the trigger of a Purpose -> the job that notices it (approach_profile_input.purposes_of gives the trigger kind)
TRIGGER_JOB = {'button': 'read-button', 'command': 'receive-command'}


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


_MP = {}


def mission_profiles(name, purposes, manager):
    """pp-0's roll-up. With NO manager (the pure path: seeds + committed files, which cannot change inside a process) the answer is remembered - it costs about ten seconds; with a
    manager the rows can change between calls, so it is derived afresh."""
    import copy
    from cmod.custom import pin_profile_mission as PM
    if manager is not None:
        return PM.mission_profiles(name, purposes=purposes, manager=manager)
    key = (name, json.dumps(purposes, sort_keys=True, default=str))
    if key not in _MP:
        _MP[key] = PM.mission_profiles(name, purposes=purposes)
    return copy.deepcopy(_MP[key])


def job_of(profile):
    from cmod.custom import isotope_variants_seeds as S
    if profile['role'] == 'the transport':
        return TRANSPORT_JOB.get(profile['kind'])
    return next((j for j, r in S.JOB_ROLE.items() if r == profile['role'] and j not in TRANSPORT_JOB.values()), None)


def mission_row(mission, manager=None):
    from cmod.custom import approach_profile_input as AI
    row = AI.find_mission(mission, manager)
    if row is None:
        raise ValueError('no HardwareMission %r (GET /api/missions lists them)' % (mission if isinstance(mission, str) else 'given'))
    return row


def objective_of(row, override=None):
    from cmod.custom import mission_nocode as MN
    obj = override or MN.settings_of(row)['objective']
    if obj not in OBJECTIVES:
        raise KeyError('no objective %r (one of %s)' % (obj, ', '.join(OBJECTIVES)))
    return obj


def job_plan(profiles, only_jobs=None):
    """-> ([job names in Mission order], {job: [Mission profiles]}, [profiles that serve no catalogued job])."""
    order, by_job, fixed = [], {}, []
    for p in profiles:
        j = job_of(p)
        if j is None:
            fixed.append(p)
        elif only_jobs and j not in only_jobs:
            continue
        else:
            if j not in by_job:
                order.append(j)
            by_job.setdefault(j, []).append(p)
    return order, by_job, fixed


def held_peripherals(unresolved):
    """Peripherals a task holds WHOLE (pp-0's unresolved list: 'needs the whole peripheral atmega328p:TIMER2 (kind timer), not a pin')."""
    import re
    out = {}
    for u in unresolved or []:
        m = re.search(r'needs the whole peripheral \S*?:?([A-Z0-9]+) \(kind', u.get('why', ''))
        if m:
            out.setdefault(m.group(1), u['task'])
    return out


def bench_pins(board, manager=None):
    """{pin: Mission role} the bench circuit already wires (pp-0's bench reader) - for the 'prefer the bench wiring' knob and the reference line."""
    from cmod.custom import pin_profile_bench as PB
    try:
        return {pin: info['role'] for pin, info in PB.bench(board, manager).items() if info.get('role')}
    except Exception:  # noqa: BLE001 - a board with no bench rows has no wiring to prefer
        return {}


def hardware_contexts(boards, limits, tables, manager=None):
    """One context per (board, package). A board whose variant is PENDING gets every allowed package and carries every allowed USB interface (the ladder reads
    the package; the bridge changes only what is undetermined about the serial lines, said per interface)."""
    from cmod.custom import isotope_variants_eligibility as E
    out = []
    for board in boards:
        ctx = E.context(board, tables)
        if ctx is None:
            raise KeyError('no board %r with a SoC row (known: %s)' % (board, ', '.join(E.boards())))
        bd = next(b for b in tables['BoardDefinition'] if b['name'] == board)
        comps = [c for c in tables.get('BoardComponent', []) if c['board'] == board and c.get('role') == 'mcu']
        pins = [b for b in tables.get('BoardPin', []) if b['board'] == board]
        usb_rows = {u['name']: u for u in tables.get('UsbInterfaceDefinition', [])}
        usb = json.loads(bd.get('allowed_usb_interfaces_json') or '[]')
        usb_notes = {u: ('serial lines: %s' % str(usb_rows[u].get('serial_transport', ''))[:120] + ('; verification %s' % usb_rows[u].get('verification', '') if usb_rows[u].get('verification') else ''))
                     for u in usb if u in usb_rows}
        pending = bd.get('variant_status') == 'pending'
        if comps and pins:
            pk = [comps[0]['package']] + ([p for p in json.loads(bd.get('allowed_packages_json') or '[]') if p != comps[0]['package']] if pending else [])
        else:
            pk = ['']
        if limits.get('packages'):
            pk = [p for p in pk if p in limits['packages']]
        for package in pk:
            out.append({'board': board, 'soc': ctx['soc'], 'package': package, 'usb_interfaces': usb, 'usb_notes': usb_notes, 'variant_pending': pending,
                        'ladder': bool(comps and pins), 'ctx': ctx,
                        'clock_hz': next((int(r['clock_hz']) for r in ctx['runtime'] if r['runtime'] == 'bare-c' and r.get('clock_hz')), None) or next((int(r['clock_hz']) for r in ctx['runtime'] if r.get('clock_hz')), None),
                        'why_not_ladder': '' if (comps and pins) else 'the %s has no BoardPin rows (no header map) and no PinFunction rows, so no ladder rung can walk a pin of it' % board})
    return out


_LOCK = None


def tier_reports(boards, mission, spec, manager=None):
    """{board: rt-0's approach result} - the tiers (state, why, kernel), the recommendation, the loop pass. The spec is shared so the Mission is read once, and pp-0's roll-up
    (which rt-0 re-derives for every board, about ten seconds each) is remembered for the duration of THIS call, under a lock so a second request never sees the stand-in."""
    import threading
    from cmod.custom import approach_profile as AP
    from cmod.custom import pin_profile_mission as PM
    global _LOCK
    _LOCK = _LOCK or threading.Lock()
    with _LOCK:
        orig, memo = PM.mission_profiles, {}

        def remembered(mission_name='', purposes=None, manager=None):
            if manager is None:
                return mission_profiles(mission_name, purposes, None)      # the same roll-up this run already holds
            key = (mission_name, json.dumps(purposes, sort_keys=True, default=str))
            if key not in memo:
                memo[key] = orig(mission_name, purposes=purposes, manager=manager)
            return memo[key]
        PM.mission_profiles = remembered
        try:
            return {b: AP.approach_profile(mission, board=b, manager=manager, spec=spec) for b in boards}
        finally:
            PM.mission_profiles = orig


def loop_pass_us(approach):
    try:
        v = approach['demand']['superloop'][0]['pass_known_us']
        return v if v and v.get('value') is not None else None
    except (KeyError, IndexError, TypeError):
        return None


def source_sha(*modules):
    """sha256 of the source files of the rule modules (the 'rule versions' of the ladder and its helpers)."""
    out = {}
    for m in modules:
        try:
            out[m.__name__] = hashlib.sha256(open(m.__file__, 'rb').read()).hexdigest()
        except OSError:
            out[m.__name__] = 'unreadable'
    return out


def fingerprint(row, profiles, variants, hardware, tables, limits, objective, tiers_state):
    """Every input by sha256, plus the tool versions. Same inputs -> same fingerprint; a changed row, rule file or knob changes it."""
    from board.custom import ladder, profile_overlap, reachability, target_compat
    from board.custom import board_object as BO
    from cmod.custom import isotope_variants_eligibility as E
    import cmod.custom.mission_colocation as MC
    boards = sorted({h['board'] for h in hardware})
    rules = source_sha(ladder, target_compat, reachability, profile_overlap, MC, E, sys.modules[__name__])
    boards_sha = {}
    for b in boards:
        try:
            boards_sha[b] = BO.board_sha(BO.rows_for(b, tables))
        except Exception:  # noqa: BLE001 - a board with no pin rows: hash what it has
            boards_sha[b] = sha([x for x in tables['BoardDefinition'] if x['name'] == b])
    prof = [{k: p.get(k) for k in ('id', 'role', 'kind', 'importance', 'reserved', 'purposes', 'drive', 'lifecycle_phases')} for p in profiles]
    return {'mission_row': sha({k: v for k, v in row.items() if k != 'sample_solutions'}), 'profiles': sha(prof), 'variants': sha(variants), 'overlap_table': sha(profile_overlap.table()),
            'ladder_rules': rules, 'boards': boards_sha, 'kit': sha([r['name'] for r in E.context(boards[0], tables)['kit']] if boards else []),
            'tiers': sha(tiers_state), 'limits': sha(limits), 'objective': objective,
            'tool_versions': {'solver': SOLVER_VERSION, 'python': platform.python_version()}}
