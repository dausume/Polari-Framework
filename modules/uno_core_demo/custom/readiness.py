"""
@module uno_core_demo.custom.readiness

PURE readiness over the UNO core demo's six composed parts (UNO_CORE_DEMO_PLAN.md §3) + the composition's own
weakest-link status — `readiness(manager=None, parts=None)` reads each part's own live manager rows when a manager
is given, else the module's own SEED_PAIRS/pure builders (the same pure/live duality `cmod.custom.firmware`/
`cmod.custom.binding`/`board.custom.electrical_check` already use) — never a manager requirement to read what is
already seeded. `parts` is the manifest's `parts` block (uno_core_demo's own polari-app.json names it); the names
below are its DEFAULTS, so a test can call this with no manifest loaded at all.

Nothing here SEEDS a claim: an absent part is named honestly (exists=False, status='missing'), never guessed,
never crashed on (modules/README.md §5's refusal rule).
"""
import time

DEFAULT_PARTS = {
    'firmware': {'class': 'FirmwareSolution', 'name': 'uno-button-clock'},
    'bridge': {'class': 'HardwareBridgeDefinition', 'name': 'button-clock', 'state_class': 'ButtonClockState', 'event_class': 'ButtonClockEvent'},
    'polari_app': {'solution': 'button-clock-ledger', 'display': 'uno-core-demo'},
    'cross_domain': {'class': 'SolutionDefinition', 'name': 'uno-button-clock'},
    'circuit': {'class': 'CircuitDefinition', 'name': 'uno-button-clock'},
    'purpose': {'class': 'CapabilityDefinition', 'name': 'button-clock-to-os'},
}

#: a part's status word, ranked worst (0) to best (5) — the composition takes the WEAKEST of its six parts' ranks;
#: an unrecognised word (a status this module does not know yet) ranks as 'undetermined' (2) rather than failing.
_STATUS_RANK = {
    'missing': 0,
    'never-run': 1, 'planned': 1, 'refused': 1, 'failed': 1, 'fail': 1,
    'undetermined': 2, 'warn': 2, 'seeded': 2, 'unchecked': 2,
    'validated': 3, 'ok': 3, 'passed': 3,
    'proven-on-twin': 4,
    'proven-on-hardware': 5,
}


def _rank(status):
    return _STATUS_RANK.get(status, 2)


def _g(row, key, default=''):
    """One field off a dict OR a live treeObject row — the pure/live duality every part reads through."""
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _rows(manager, seed_pairs, class_name):
    """[row, ...] for one class: a live manager's own table when given (treeObject instances), else the dicts the
    owning module's own SEED_PAIRS carry (a fresh backend's seed tables — what a selftest with no manager reads)."""
    if manager is not None:
        return list((getattr(manager, 'objectTables', None) or {}).get(class_name, {}).values())
    return list(next((rs for n, _c, rs in (seed_pairs or []) if n == class_name), []))


def _row(part, ref_class, ref_name, exists, status, why, checked_at):
    refs = ('%s:%s' % (ref_class, ref_name)) if (ref_class and ref_name) else ''
    return {'name': 'uno-core-demo:%s' % part, 'part': part, 'ref_class': ref_class, 'ref_name': ref_name,
            'refs': refs, 'exists': bool(exists), 'status': status, 'why': why, 'checked_at': checked_at}


def _firmware_part(spec, manager, checked_at):
    name = spec.get('name', '')
    try:
        from cmod.cmod_seed import CMOD_SEED_PAIRS
    except Exception:
        CMOD_SEED_PAIRS = []
    rows = _rows(manager, CMOD_SEED_PAIRS, 'FirmwareSolution')
    row = next((r for r in rows if _g(r, 'name') == name), None)
    if row is None:
        return _row('firmware', 'FirmwareSolution', name, False, 'missing',
                    'no FirmwareSolution named %r (planned; composed by name only, per UNO_CORE_DEMO_PLAN.md §3)' % name,
                    checked_at)
    status = _g(row, 'validation') or _g(row, 'status') or 'seeded'
    status = status if status in ('ok', 'validated', 'seeded', 'built', 'run', 'refused') else status
    why = _g(row, 'validation_why') or ('FirmwareSolution %r: status=%s' % (name, _g(row, 'status')))
    return _row('firmware', 'FirmwareSolution', name, True, status, why, checked_at)


def _bridge_part(spec, manager, checked_at):
    bridge_name = spec.get('name', '')
    rows = _rows(manager, [], 'HardwareBridgeDefinition')   # never seeded by any module (D-ucd-2 §3: an explicit knob act)
    row = next((r for r in rows if _g(r, 'bridge_name') == bridge_name or _g(r, 'name') == '%s-hw-bridge' % bridge_name), None)
    try:
        from hardwareapps.hardwareapps_basis import HARDWAREAPPS_SEED_PAIRS
    except Exception:
        HARDWAREAPPS_SEED_PAIRS = []
    cap_rows = _rows(manager, HARDWAREAPPS_SEED_PAIRS, 'BridgingCapability')
    cap = next((r for r in cap_rows if _g(r, 'app') == 'Polari Firmware Installer'), None)
    if row is None:
        why = ('no LIVE HardwareBridgeDefinition named %r (grpcbridge.mapping_basis.SEED_BUTTON_CLOCK_BRIDGE is '
               'code-owned data for a test, never seeded — generation is an explicit knob act)' % bridge_name)
        if cap is not None:
            why += '; its BridgingCapability (%s) is %r, not yet relevant with no bridge row' % (_g(cap, 'app'), _g(cap, 'status'))
        return _row('bridge', 'HardwareBridgeDefinition', bridge_name, False, 'missing', why, checked_at)
    if cap is None:
        return _row('bridge', 'HardwareBridgeDefinition', bridge_name, True, 'never-run',
                    'the bridge row exists; no BridgingCapability row names an app for it yet', checked_at)
    status = _g(cap, 'status', 'never-run')
    why = ('BridgingCapability %r (app=%r): proven_by=%r, proven_at=%r — the bridge\'s OWN status, per '
          'UNO_CORE_DEMO_PLAN.md §3/§5c' % (_g(cap, 'name'), _g(cap, 'app'), _g(cap, 'proven_by'), _g(cap, 'proven_at')))
    return _row('bridge', 'HardwareBridgeDefinition', bridge_name, True, status, why, checked_at)


def _polari_app_part(spec, manager, checked_at):
    solution = spec.get('solution', '')
    display = spec.get('display', '')
    try:
        from hwnocode.hwnocode_seed import HWNOCODE_SEED_PAIRS
    except Exception:
        HWNOCODE_SEED_PAIRS = []
    sol_rows = _rows(manager, HWNOCODE_SEED_PAIRS, 'SolutionDefinition')
    sol = next((r for r in sol_rows if _g(r, 'name') == solution), None)
    try:
        from hwnocode.hwnocode_page import SEED_HWNOCODE_PAGE_DISPLAYS  # pages are NOT in HWNOCODE_SEED_PAIRS (module_pages_seed assembles DisplayDefinition separately)
    except Exception:
        SEED_HWNOCODE_PAGE_DISPLAYS = []
    disp_rows = _rows(manager, [('DisplayDefinition', None, SEED_HWNOCODE_PAGE_DISPLAYS)], 'DisplayDefinition')
    disp = next((r for r in disp_rows if _g(r, 'name') == display or _g(r, 'pageRoute') == display), None)
    ref_name = '%s + /display/%s' % (solution, display)
    if sol and disp:
        return _row('polari_app', '', ref_name, True, 'ok',
                    'SolutionDefinition %r and /display/%s both found' % (solution, display), checked_at)
    missing = ([] if sol else ['SolutionDefinition %r' % solution]) + ([] if disp else ['/display/%s' % display])
    return _row('polari_app', '', ref_name, False, 'missing', 'missing: ' + ', '.join(missing), checked_at)


def _cross_domain_part(spec, manager, checked_at):
    name = spec.get('name', '')
    try:
        from hwnocode.hwnocode_seed import HWNOCODE_SEED_PAIRS
    except Exception:
        HWNOCODE_SEED_PAIRS = []
    rows = _rows(manager, HWNOCODE_SEED_PAIRS, 'SolutionDefinition')
    row = next((r for r in rows if _g(r, 'name') == name), None)
    if row is None:
        return _row('cross_domain', 'SolutionDefinition', name, False, 'missing',
                    'no SolutionDefinition named %r' % name, checked_at)
    if _g(row, 'category') != 'cross-domain':
        return _row('cross_domain', 'SolutionDefinition', name, True, 'undetermined',
                    'SolutionDefinition %r exists but category=%r, not cross-domain' % (name, _g(row, 'category')), checked_at)
    try:
        import json as _json
        from hwnocode.custom import cross_domain as CD
        definition = _json.loads(_g(row, 'definition') or '{}')
        ok, why = CD.validate(definition)
        return _row('cross_domain', 'SolutionDefinition', name, True, ('ok' if ok else 'refused'), why, checked_at)
    except Exception as exc:  # noqa: BLE001 — never crash the readiness door over a structural check
        return _row('cross_domain', 'SolutionDefinition', name, True, 'undetermined',
                    'exists, but hwnocode.custom.cross_domain.validate raised %s: %s' % (type(exc).__name__, exc), checked_at)


def _circuit_part(spec, manager, checked_at):
    name = spec.get('name', '')
    try:
        from electrodevice.objects.circuit._shared import SEED_CIRCUITS
    except Exception:
        SEED_CIRCUITS = []
    rows = _rows(manager, [('CircuitDefinition', None, SEED_CIRCUITS)], 'CircuitDefinition')
    row = next((r for r in rows if _g(r, 'name') == name), None)
    if row is None:
        return _row('circuit', 'CircuitDefinition', name, False, 'missing', 'no CircuitDefinition named %r' % name, checked_at)
    try:
        from board.custom import electrical_check as EC
        tables = EC.tables_for(manager)
        # the demo's own board (hwnocode.custom.solutions.BOARD) — a bare board name, never the FirmwareSolution
        # binding (which does not exist yet; `check` would still degrade gracefully, but this is the correct board)
        findings = EC.check(name, 'arduino-uno-r3', tables)
        rank = {'ok': 0, 'undetermined': 1, 'warn': 2, 'fail': 3}
        worst = max(findings, key=lambda f: rank.get(f.get('status'), 1)) if findings else None
        if worst is None:
            return _row('circuit', 'CircuitDefinition', name, True, 'unchecked', 'CircuitDefinition %r exists; no findings produced' % name, checked_at)
        status = {'ok': 'ok', 'undetermined': 'undetermined', 'warn': 'warn', 'fail': 'failed'}.get(worst.get('status'), 'undetermined')
        return _row('circuit', 'CircuitDefinition', name, True, status,
                    'worst finding (%s, %s): %s' % (worst.get('rule', '?'), worst.get('subject', ''), worst.get('detail', '')), checked_at)
    except Exception as exc:  # noqa: BLE001
        return _row('circuit', 'CircuitDefinition', name, True, 'unchecked',
                    'CircuitDefinition %r exists; board.custom.electrical_check raised %s: %s (not independently checked)'
                    % (name, type(exc).__name__, exc), checked_at)


def _purpose_part(spec, manager, checked_at):
    name = spec.get('name', '')
    try:
        from cmod.custom.capabilities import SEED_CAPABILITIES
    except Exception:
        SEED_CAPABILITIES = []
    rows = _rows(manager, [('CapabilityDefinition', None, SEED_CAPABILITIES)], 'CapabilityDefinition')
    row = next((r for r in rows if _g(r, 'name') == name), None)
    if row is None:
        return _row('purpose', 'CapabilityDefinition', name, False, 'missing', 'no CapabilityDefinition (Purpose) named %r' % name, checked_at)
    status = _g(row, 'status', 'planned')
    why = 'Purpose %r: %s' % (name, _g(row, 'last_proof') or 'no proof run yet')
    return _row('purpose', 'CapabilityDefinition', name, True, status, why, checked_at)


_BUILDERS = {
    'firmware': _firmware_part, 'bridge': _bridge_part, 'polari_app': _polari_app_part,
    'cross_domain': _cross_domain_part, 'circuit': _circuit_part, 'purpose': _purpose_part,
}

#: the plain-words order every reader (the page, the API, the selftest) shows the six parts in, before `composition`
PARTS_ORDER = ('firmware', 'bridge', 'polari_app', 'cross_domain', 'circuit', 'purpose')


def readiness(manager=None, parts=None):
    """[{name, part, ref_class, ref_name, refs, exists, status, why, checked_at}, ...] — one row per part named in
    `parts` (the manifest's `parts` block; DEFAULT_PARTS when omitted) in PARTS_ORDER, plus a final `composition`
    row whose `status` is the WEAKEST of the six (by `_STATUS_RANK`) — 'incomplete' whenever any part is missing
    (UNO_CORE_DEMO_PLAN.md §3: "the composition's status = the weakest part"), never a crash when a part's rows are
    absent (the parallel firmware/bridge agents may not have landed yet)."""
    parts = parts or DEFAULT_PARTS
    checked_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    rows = []
    for part in PARTS_ORDER:
        spec = parts.get(part) or {}
        rows.append(_BUILDERS[part](spec, manager, checked_at))
    weakest = min(rows, key=lambda r: _rank(r['status']))
    if any(not r['exists'] for r in rows):
        comp_status = 'incomplete'
    else:
        comp_status = weakest['status']
    comp_why = 'weakest part: %s (%s) — %s' % (weakest['part'], weakest['status'], weakest['why'])
    missing = [r['part'] for r in rows if not r['exists']]
    if missing:
        comp_why = 'missing part(s): %s; ' % ', '.join(missing) + comp_why
    rows.append(_row('composition', '', ', '.join('%s:%s' % (r['part'], r['status']) for r in rows), True, comp_status, comp_why, checked_at))
    return rows
