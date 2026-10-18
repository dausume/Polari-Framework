"""
@module cmod.custom.pin_profile_mission

pp-0 (MISSION_PROFILE_SOLVER_PLAN.md §2.2, "Rolled up per Mission"): the MULTISET of pin profiles across a Mission's Purposes.
  - The same need on the same role is ONE profile, listing every Purpose that needs it (the LED drive that three light Purposes share counts
    once): key = (role, kind, drive need, load class).
  - plus the RESERVED profiles the host participant implies: the board's PinLifecycleConstraint rows that reserve a pin for the transport
    (policy reserved, condition transport=usb-serial) - uart-rx / uart-tx on the UNO - added to (or merged into) the transport profiles.
  - each merged profile carries an IMPORTANCE: the strongest of its Purposes' importance in the Mission (safety > required > important > desired),
    `required` when no Mission says otherwise.
The Mission is read from a `HardwareMission` row (mis-0) when the manager holds one - read generically from objectTables, no import, so this works
before and after mis-0 merges - or an explicit list of Purposes is handed in ([name | {purpose, importance}, ...]).
"""
import json

from cmod.custom import pin_profiles as PP


def _mission_purposes(mission, purposes, manager):
    """-> ([{purpose, importance}], basis text)."""
    if purposes:
        out = [{'purpose': p, 'importance': 'required'} if isinstance(p, str) else {'purpose': p['purpose'], 'importance': p.get('importance') or 'required'}
               for p in purposes]
        return out, 'an explicit list of Purposes'
    row = next((r for r in ((getattr(manager, 'objectTables', None) or {}).get('HardwareMission') or {}).values() if getattr(r, 'name', '') == mission), None) \
        if manager is not None else None
    if row is None:
        raise ValueError('no HardwareMission %r on this server (mis-0 adds them); name the Purposes instead: ?purposes=a,b' % mission)
    try:
        raw = json.loads(getattr(row, 'purposes_json', '') or '[]')
    except ValueError:
        raw = []
    return [{'purpose': x['purpose'], 'importance': x.get('importance') or 'required'} for x in raw if isinstance(x, dict) and x.get('purpose')], 'HardwareMission %s' % mission


def _strongest(a, b):
    return a if PP.IMPORTANCE.index(a) <= PP.IMPORTANCE.index(b) else b


def _participants(cap):
    try:
        return json.loads(cap.get('participants_json') or '[]')
    except ValueError:
        return []


def _reserved_transport(boards, manager):
    """[(kind, [lifecycle rows], evidence)] - the transport lines the host participant reserves on the boards in play."""
    from board.custom import board_object as BO, target_compat as TC
    out = []
    for board in sorted(boards):
        try:
            r = BO.rows_for(board)
        except Exception:  # noqa: BLE001 - a board with no pin rows reserves nothing we can name
            continue
        usb = json.loads((r['identity'] or {}).get('allowed_usb_interfaces_json') or '[]')
        if not usb:
            out.append((None, [], 'undetermined - BoardDefinition %s allows no USB interface row, so the transport condition is not known' % board))
            continue
        rows = [x for x in PP._lifecycle(board, manager) if x.get('policy') == 'reserved' and x.get('condition') == 'transport=usb-serial']
        for kind in ('uart-rx', 'uart-tx'):
            pins = {v['pin'] for v in TC.valid_targets(kind, r) if v['verdict'] == 'ok'}
            mine = [x for x in rows if x['pin'] in pins]
            if mine:
                out.append((kind, mine, 'host participant -> %s over USB interface %s (BoardDefinition allowed_usb_interfaces); %s' % (
                    board, ', '.join(usb), '; '.join(x['name'] for x in mine))))
    return out


def mission_profiles(mission='', purposes=None, manager=None):
    """-> {'mission', 'basis', 'purposes', 'profiles' [merged], 'unresolved', 'pins_needed'}."""
    plist, basis = _mission_purposes(mission, purposes, manager)
    merged, order, unresolved, boards, host = {}, [], [], set(), False
    for entry in plist:
        res = PP.derive_profiles(entry['purpose'], manager)
        cap = PP.find_purpose(entry['purpose'], manager) or {}
        for part in _participants(cap):
            if part.get('role') == 'board' and part.get('ref'):
                boards.add(part['ref'])
            host = host or part.get('role') == 'host'
        unresolved += [dict(u, purpose=entry['purpose']) for u in res['unresolved']]
        for p in res['profiles']:
            key = (p['role'], p['kind'], p['drive']['need'], p['drive']['load_class'])
            if key not in merged:
                merged[key] = {'id': 'mission:%s:%s' % (PP._slug(p['role']), p['kind']), 'role': p['role'], 'kind': p['kind'], 'serves': p['serves'],
                               'signal': p['signal'], 'drive': p['drive'], 'purposes': [], 'importance': entry['importance'], 'lifecycle_phases': [],
                               'lifecycle': [], 'reserved': False, 'count': 1, 'origin': set(), 'timing_by_purpose': {}, 'evidence_by_purpose': {},
                               'overrides': [], 'evidence': {}}
                order.append(key)
            m = merged[key]
            m['purposes'].append(entry['purpose'])
            m['importance'] = _strongest(m['importance'], entry['importance'])
            m['lifecycle_phases'] = sorted(set(m['lifecycle_phases']) | set(p['lifecycle_phases']), key=PP.PHASE_ORDER.index)
            m['reserved'] = m['reserved'] or p['reserved']
            m['origin'].add(p['origin'])
            m['timing_by_purpose'][entry['purpose']] = p['timing']
            m['evidence_by_purpose'][entry['purpose']] = p['evidence']
            m['overrides'] += [dict(o, purpose=entry['purpose']) for o in p['overrides']]
            known = {(c['name']) for c in m['lifecycle']}
            m['lifecycle'] += [c for c in p['lifecycle'] if c['name'] not in known]
    reserved_notes = []
    if host:
        for kind, rows, ev in _reserved_transport(boards, manager):
            if kind is None:
                reserved_notes.append(ev)
                continue
            key = next((k for k in order if k[0] == 'the transport' and k[1] == kind), None)
            if key is None:
                key = ('the transport', kind, 'undetermined', 'undetermined')
                sig, _ = PP._signal(kind, None)
                merged[key] = {'id': 'mission:the-transport:%s' % kind, 'role': 'the transport', 'kind': kind, 'serves': 'the host and Polari, over the transport',
                               'signal': sig, 'drive': {'need': 'undetermined', 'load_class': 'undetermined', 'current': PP.undetermined('no Purpose task uses this line')},
                               'purposes': [], 'importance': 'required', 'lifecycle_phases': [], 'lifecycle': [], 'reserved': False, 'count': 1,
                               'origin': set(), 'timing_by_purpose': {}, 'evidence_by_purpose': {}, 'overrides': [], 'evidence': {}}
                order.append(key)
            m = merged[key]
            m['reserved'] = True
            m['origin'].add('host participant')
            m['lifecycle'] += [{'name': x['name'], 'phase': x['phase'], 'policy': x['policy'], 'condition': x['condition']} for x in rows
                               if x['name'] not in {c['name'] for c in m['lifecycle']}]
            m['lifecycle_phases'] = sorted(set(m['lifecycle_phases']) | {x['phase'] for x in rows}, key=PP.PHASE_ORDER.index)
            m['evidence']['reserved'] = ev
    profiles = []
    for key in order:
        m = merged[key]
        m['origin'] = ', '.join(sorted(m['origin']))
        m['evidence']['purposes'] = 'needed by %s' % (', '.join(m['purposes']) or 'no Purpose (implied by the host participant only)')
        m['evidence_summary'] = ['%s: %s' % (k, v) for k, v in m['evidence'].items()]
        profiles.append(m)
    seen, un = set(), []
    for u in unresolved:
        if (u['task'], u['why']) not in seen:
            seen.add((u['task'], u['why']))
            un.append(u)
    return {'mission': mission, 'basis': basis, 'purposes': plist, 'profiles': profiles, 'unresolved': un, 'reserved_notes': reserved_notes,
            'pins_needed': len(profiles),
            'note': 'one pin per profile: the same role needed by two Purposes shares one pin; a need that differs in kind, role or drive is another pin'}
