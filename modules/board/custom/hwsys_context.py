"""
@module board.custom.hwsys_context

hsp-1: THE CONTEXT a Hardware System's paths are checked in, and the hop builders. Every verdict is CALLED from the code that owns the check — the availability ladder
(board.custom.ladder, one run per pin x function, every allowed package while the board's package variant is pending, the WORST verdict per rung), the electrical
rules (board.custom.electrical_check), the cmod Purpose proof status, the pinned wire contract (board.custom.compat) — never re-implemented. A hop whose input is missing
says `unchecked`; a ref that does not resolve is an explicit hop naming what is missing.

Severity (worst first): blocked > unchecked > conditional > undetermined > not-yet > ok. A hop OWNS some ladder rungs; rung 10 (isotope requirements, fgm-4) is carried in the list
as informational and never degrades a hop.
"""
import json

from board.custom import hwsys_refs as R
from board.custom import ladder as LD

SEV = {'blocked': 5, 'unchecked': 4, 'conditional': 3, 'undetermined': 2, 'not-yet': 1, 'ok': 0}
FINDING = {'refuse': 'blocked', 'warn': 'conditional', 'undetermined': 'undetermined', 'ok': 'ok'}
VERIFY = {'verified': 'ok', 'partial': 'conditional', 'unverified': 'undetermined', 'conflicted': 'blocked'}


def worst(verdicts):
    return max(verdicts, key=lambda v: SEV[v], default='unchecked')


class Ctx:
    def __init__(self, tables, manager=None, system=None, extra=None):
        self.tables, self.manager, self.extra = tables, manager, extra or {}
        s = system or {}
        self.system = s
        self.system_name = s.get('name', '')
        parts = json.loads(s.get('participants_json') or '[]')
        self.board = next((R.refs_of([p['ref']])[0].partition(':')[2] for p in parts if p.get('kind') == 'hardware' and p['ref'].startswith('BoardDefinition:')), 'arduino-uno-r3')
        self.pending = any(p.get('variant') == 'pending' for p in parts if p['ref'].startswith('BoardDefinition:'))
        self.circuit = next((p['ref'].partition(':')[2] for p in parts if p['ref'].startswith('CircuitDefinition:')), '')
        fw = next((p['ref'].partition(':')[2] for p in parts if p['ref'].startswith('FirmwareSolution:')), '')
        self.firmware = fw
        self.binding = '%s@%s' % (fw, self.board) if fw else ''
        self.transport = 'usb-serial' if any(p['ref'] in ('HardwareBridgeDefinition:uno-light-bridge',) or p['ref'].startswith('HardwareBridgeDefinition:') for p in parts) else ''
        self._lad, self.cache = {}, {}

    # ---- the ladder, merged over every allowed package (worst verdict per rung)
    def ladder(self, pin, fn, purpose=False, chip=''):
        key = (pin, fn, purpose, chip)
        if key not in self._lad:
            c = {'board': self.board, 'circuit': self.circuit, 'binding': self.binding, 'transport': self.transport, 'purpose': purpose}
            if chip:
                c['chip'] = chip
            if self.pending:
                c['variant_pending'] = True
            res = LD.availability(pin, fn, {k: v for k, v in c.items() if v}, self.tables, cache=self.cache)
            rungs = []
            for i in range(10):
                per = [r['rungs'][i] for r in res['results']]
                w = max(per, key=lambda r: SEV[r['verdict']])
                d = w['detail'] + ((' [package %s]' % res['results'][per.index(w)]['package']) if len(per) > 1 and w['verdict'] != 'ok' else '')
                rungs.append(dict(w, detail=d))
            self._lad[key] = {'rungs': rungs, 'packages': [r['package'] for r in res['results']], 'soc_pin': res['soc_pin']}
        return self._lad[key]

    def rungs_hop(self, lad, which, label):
        """-> (verdict, detail, extra) of the ladder rungs a hop OWNS; `extra` carries all ten rung verdicts."""
        own = [r for r in lad['rungs'] if r['rung'] in which]
        v = worst([r['verdict'] for r in own])
        bad = [r for r in own if r['verdict'] != 'ok']
        d = '; '.join('rung %d %s [%s]: %s' % (r['rung'], r['name'], r['verdict'], r['detail'][:170]) for r in (bad or own[:2]))
        return v, d, {'rungs': [{'rung': r['rung'], 'name': r['name'], 'verdict': r['verdict']} for r in lad['rungs']], 'packages': lad['packages']}

    # ---- the electrical rules of the system's circuit, with the firmware's own PinClaims
    def findings(self, rules, match=''):
        if not self.circuit:
            return 'unchecked', 'no circuit among the participants: the electrical rules run on a circuit'
        key = ('ec', self.circuit, self.binding)
        if key not in self.cache:   # the SAME cache key the ladder's rung 7 uses: one run of the electrical rules per design
            from board.custom import electrical_check as EC
            et = LD._etables(dict(self.tables, _manager=self.manager) if '_manager' not in self.tables else self.tables, self.cache)
            self.cache[key] = EC.check(self.circuit, self.binding or self.board, et, context={'transport': self.transport} if self.transport else {})
        mine = [f for f in self.cache[key] if f['rule'] in rules and (not match or match in f['subject'] + ' ' + f['detail'])]
        if not mine:
            return 'unchecked', 'no finding of rule(s) %s%s was produced' % ('/'.join(rules), (' for ' + match) if match else '')
        v = worst([FINDING[f['status']] for f in mine])
        pick = [f for f in mine if FINDING[f['status']] == v]
        return v, '; '.join('%s [%s] %s: %s' % (f['rule'], f['status'], f['subject'], f['detail'][:200]) for f in pick)

    # ---- the hop
    def hop(self, kind, ref, what, check, verdict, detail='', missing_blocks=False, **extra):
        ok, why = R.resolves(ref, self.tables, self.manager, self.extra) if ref else (False, 'no ref')
        if verdict == 'ok' and check in ('', 'none'):   # no hop says ok without a check
            verdict, detail = 'unchecked', 'no check owns this hop' + ((': ' + detail) if detail else '')
        h = {'n': 0, 'kind': kind, 'ref': ref, 'what': what, 'check': check, 'verdict': verdict, 'detail': detail, 'resolved': ok}
        if not ok:
            h['verdict'] = 'blocked' if missing_blocks else ('undetermined' if verdict in ('ok', 'conditional', 'unchecked', 'not-yet') else verdict)
            h['detail'] = ('%s is missing: %s' % (ref, why) if missing_blocks else 'unresolved %s: %s' % (ref, why)) + ((' — ' + detail) if detail else '')
        h.update(extra)
        return h

    def contract(self):
        from board.custom import compat
        c, path = compat.pinned_contract('LightState')
        return c

    def purpose_proof(self, purpose):
        """-> (verdict, detail): the cmod Purpose's proof status (the twin proof), and whether every task it names resolves."""
        try:
            from cmod.custom import capabilities as C
        except Exception as e:   # noqa: BLE001
            return 'unchecked', 'cmod is absent here (%s): no proof status can be read' % e
        row = next((p for p in C.purposes_for_graph('%s-graph' % self.firmware, self.manager) if p.get('name') == purpose), None)
        if row is None:
            return 'undetermined', 'no Purpose %s over graph %s-graph' % (purpose, self.firmware)
        missing = []
        for rt, refs in json.loads(row.get('tasks_by_runtime_json') or '{}').items():
            for ref in refs:
                ok, why = C.task_exists(rt, ref, self.manager)
                if not ok:
                    missing.append('%s: %s' % (ref, why))
        if missing:
            return 'blocked', 'Purpose %s names task(s) that do not resolve — %s' % (purpose, '; '.join(missing[:3]))
        st, last, why, _pk = C.derive_status(row, manager=self.manager)
        v = {'failing': 'blocked', 'planned': 'unchecked', 'proven-on-twin': 'conditional', 'proven-on-hardware': 'ok'}.get(st, 'unchecked')
        return v, 'Purpose %s is %s (%s)%s' % (purpose, st, why, '; proven on the simavr twin only, not on a board' if st == 'proven-on-twin' else '')


def finish(hops):
    """Number the hops 1..n, the path verdict (worst hop), the first blocked hop, gap-free."""
    for i, h in enumerate(hops, 1):
        h['n'] = i
    first = next((h['n'] for h in hops if h['verdict'] == 'blocked'), 0)
    gap_free = bool(hops) and all(h['resolved'] or h['verdict'] in ('blocked', 'undetermined') for h in hops)
    return {'hops': hops, 'verdict': worst([h['verdict'] for h in hops]), 'blocked_at': first, 'gap_free': gap_free}
