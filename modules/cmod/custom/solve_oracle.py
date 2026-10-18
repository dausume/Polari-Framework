"""
@module cmod.custom.solve_oracle

sol-0: the per-pin FEASIBILITY ORACLE. For one hardware context (board x package) it answers, for one need, "which pins can take it, and why not the others":

  rung 1 (does the pin carry the function) .. rung 9 (existing claims)   board.custom.ladder.availability(pin, function, ctx, tables, cache) - CALLED, once per
                                                                          (pin, function, phase), the cache shared (a full ladder read is slow otherwise)
  occupied (a synthetic or given claim)                                   limits['occupied']: [{pin, by, why, blocks: 'all' | [kinds]}] - a rung-9 stand-in named as such
  a peripheral a task holds whole                                         pp-0's unresolved list (Timer2 held by the tick): a PWM pin on Timer2 is refused by name

A rung that is `blocked` refuses the pin and the refusal keeps the rung number, the ladder's own words and its citation; every other non-ok rung (conditional, unchecked,
undetermined, not-yet) stays on the option as a RISK, shown in the candidate - an unchecked rung is never counted as ok. Nothing is stored; the ladder is a computed view.
"""
from board.custom import ladder as L
from cmod.custom import solve_needs as N


def _short(text, n=170):
    text = str(text)
    return text if len(text) <= n else text[:n - 1] + '…'


class Oracle:
    def __init__(self, hw, tables, scar, universe, occupied=(), held=None, bench=None, prefer='least-specialised', ladder_extra=None, transport=True):
        self.hw, self.tables, self.scar, self.universe = hw, tables, scar, universe
        self.occupied = [dict(o) for o in occupied or []]
        self.held = held or {}
        self.bench = bench or {}
        self.prefer = prefer
        self.cache = {}                       # the ladder's shared cache
        self.memo = {}                        # (pin, function, phase, purpose) -> the first result
        self.ctx0 = dict({'board': hw['board'], 'package': hw['package']}, **(ladder_extra or {}))
        if transport:
            self.ctx0['transport'] = 'usb-serial'
        self.opt_memo = {}
        self.ladder_calls = 0

    # ------------------------------------------------------------------ the ladder, memoised
    def rungs(self, pin, fn, phase, purpose):
        key = (pin, fn, phase, purpose)
        if key not in self.memo:
            self.ladder_calls += 1
            res = L.availability(pin, fn, dict(self.ctx0, phase=phase, purpose=purpose), self.tables, self.cache)['results'][0]
            self.memo[key] = res
        return self.memo[key]

    def _occupied_by(self, pin, need):
        for o in self.occupied:
            if o['pin'] != pin:
                continue
            blocks = o.get('blocks', 'all')
            if blocks == 'all' or need['kind'] in blocks or need['okind'] in blocks:
                return o
        return None

    # ------------------------------------------------------------------ options for a need
    def options(self, need):
        """-> (options sorted cheapest-first, rejects). option = {pin, function, spec, wasted, risks, rungs_ok, bench}; reject = {pin, kind, rung, text, cite}."""
        key = (tuple(need['patterns']), need['kind'], need['okind'], tuple(need['phases']), need['reserved'], need['role'],
               tuple(sorted((o['pin'], str(o.get('blocks', 'all'))) for o in self.occupied)))
        if key in self.opt_memo:
            return self.opt_memo[key]
        opts, rejects = [], []
        for pin in self.universe:
            fn = N.pick_function(pin, need['patterns'])
            if fn is None:
                rejects.append({'pin': pin['canonical'], 'kind': 'no-function', 'rung': 1, 'text': '%s carries none of %s' % (pin['canonical'], ' / '.join(need['patterns'])), 'cite': ''})
                continue
            occ = self._occupied_by(pin['canonical'], need)
            if occ is not None:
                rejects.append({'pin': pin['canonical'], 'kind': 'occupied', 'rung': 9, 'text': '%s is occupied by %s: %s' % (pin['canonical'], occ.get('by', 'a claim'), occ.get('why', '')), 'cite': 'a given claim (stands in for rung 9)'})
                continue
            from board.custom.soc_atmega328p import FUNCTION_PERIPHERAL
            per = FUNCTION_PERIPHERAL.get(fn, ('', ''))[0]
            if per in self.held:
                rejects.append({'pin': pin['canonical'], 'kind': 'held-peripheral', 'rung': 6, 'text': '%s (%s) is on %s, which the Mission holds whole for %s' % (pin['canonical'], fn, per, self.held[per]),
                                'cite': 'cmod.custom.pin_profile_mission (a task needs the whole peripheral)'})
                continue
            blocked, risks = None, []
            for ph in need['phases']:
                r = self.rungs(pin['canonical'], fn, ph, need['reserved'])
                for x in r['rungs']:
                    if x['verdict'] == 'blocked' and blocked is None:
                        blocked = x
                    elif x['verdict'] in ('conditional', 'unchecked', 'undetermined', 'not-yet'):
                        risks.append({'rung': x['rung'], 'name': x['name'], 'verdict': x['verdict'], 'detail': _short(x['detail'])})
            if blocked is not None:
                rejects.append({'pin': pin['canonical'], 'kind': 'rung-%d-%s' % (blocked['rung'], blocked['name']), 'rung': blocked['rung'], 'text': _short(blocked['detail'], 260),
                                'cite': blocked.get('cite', '')})
                continue
            seen, uniq = set(), []
            for x in risks:
                if (x['rung'], x['verdict']) not in seen:
                    seen.add((x['rung'], x['verdict']))
                    uniq.append(x)
            spec, wasted = N.spec_cost(pin, fn, self.scar)
            opts.append({'pin': pin['canonical'], 'function': fn, 'spec': spec, 'wasted': wasted, 'risks': sorted(uniq, key=lambda x: (x['rung'], x['verdict'])),
                         'index': pin['index'], 'header': pin['header']})
        opts.sort(key=lambda o: (o['spec'], o['index']))
        self.opt_memo[key] = (opts, rejects)
        return opts, rejects

    def with_bench(self, need, opts):
        """Mark the option on the pin the bench circuit already wires for this need's role (only matters when prefer == 'bench-wiring')."""
        pin = next((p for p, role in self.bench.items() if role == need['role']), None)
        return [dict(o, bench=(o['pin'] == pin), nonbench=(0 if (self.prefer != 'bench-wiring' or o['pin'] == pin) else 1)) for o in opts]
