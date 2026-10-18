"""
@module cmod.custom.solve_engine

sol-0: THE ATTEMPT ENGINE (MISSION_PROFILE_SOLVER_PLAN.md sections 2.5 and 8.4). For each candidate HARDWARE (board x allowed package) -> each runtime TIER rt-0 does not block ->
each combination of isotope VARIANTS (one per job the Mission needs; the ones a missing bench part blocks are KEPT and flagged, never hidden, never called available)
-> the pin needs of that combination -> a constraint search (cmod.custom.solve_assign) over the ladder oracle (cmod.custom.solve_oracle) -> a Candidate, scored by the
Mission's objective (cmod.custom.solve_cost). A "wasteful" variant is SCORED worse, never excluded: it wins only when the better ones cannot be placed.

Every branch that does not become a candidate is recorded with its kind and reason (PrunedLog). When a (hardware, tier) has no complete placement at all, the engine places
by IMPORTANCE (safety > required > important > desired) and reports which lower-importance Purpose lost its pins and why. Deterministic: sorted inputs, fixed tie-breaks.
"""
import itertools
import json
import time

from cmod.custom import pin_profiles as PP
from cmod.custom import solve_assign as SA
from cmod.custom import solve_cost as SC
from cmod.custom import solve_inputs as SI
from cmod.custom import solve_needs as SN
from cmod.custom import solve_oracle as SO

DEFAULT_LIMITS = {'max_candidates': 40, 'max_combos': 5000, 'max_nodes': 20000, 'pruned_first': 8, 'occupied': [], 'only_jobs': None, 'prefer': 'least-specialised',
                  'share_pins': 'none', 'weights': {}, 'purposes': None, 'packages': None, 'undetermined_keep': 3, 'partial_combos': 60, 'ladder_context': {}}
TIERS = ('bare-c', 'freertos', 'zephyr')


def normalise_limits(limits):
    lim = json.loads(json.dumps(DEFAULT_LIMITS))
    for k, v in (limits or {}).items():
        if k not in DEFAULT_LIMITS:
            raise KeyError('no limit %r (one of %s)' % (k, ', '.join(sorted(DEFAULT_LIMITS))))
        lim[k] = v
    if lim['share_pins'] not in ('none', 'compatible', 'conditional'):
        raise KeyError("share_pins is 'none', 'compatible' or 'conditional'")
    if lim['prefer'] not in ('least-specialised', 'bench-wiring'):
        raise KeyError("prefer is 'least-specialised' or 'bench-wiring'")
    for o in lim['occupied']:
        if 'pin' not in o:
            raise KeyError('an occupied entry needs a pin: {pin, by, why, blocks}')
    return lim


class PrunedLog:
    """Every branch that did not become a candidate: counted by kind, the first N reasons of each kind kept. A reason is never empty."""
    KINDS = ('tier-blocked', 'no-variant', 'variant-ineligible', 'no-placement', 'pin-refused', 'limit', 'search-bounded', 'hardware-undetermined', 'tier-skipped')

    def __init__(self, first):
        self.first, self.count, self.items, self.total = first, {}, {}, 0

    def add(self, kind, where, reason):
        assert kind in self.KINDS and reason
        self.count[kind] = self.count.get(kind, 0) + 1
        self.total += 1
        lst = self.items.setdefault(kind, [])
        if len(lst) < self.first:
            lst.append({'kind': kind, 'where': where, 'reason': reason})

    def as_dict(self):
        return {'total': self.total, 'by_kind': {k: {'count': self.count[k], 'first': self.items[k]} for k in sorted(self.count)}}


# ------------------------------------------------------------------ variants usable on a hardware and tier
def usable_variants(job, hw, tier, manager, cache):
    """-> ([usable variant rows with their eligibility], [pruned (variant, reason)]). Blocked ONLY by a part the bench lacks = kept, flagged `needs_parts`."""
    from cmod.custom import isotope_variants as IV
    from cmod.custom import isotope_variants_eligibility as E
    out, gone = [], []
    for v in IV.variants(manager, job):
        key = (hw['board'], tier, v['name'])
        if key not in cache:
            cache[key] = E.eligible(v, hw['ctx'], tier=tier)
        e = cache[key]
        part_only = e['state'] == 'blocked' and all(c['check'] == 'part' for c in e['checks'] if c['state'] == 'blocked')
        if e['state'] == 'blocked' and not part_only:
            gone.append((v, e['summary']))
        else:
            out.append(dict(v, _elig=e, _needs_parts=part_only))
    return out, gone


def _standalone_key(v, objective):
    c, ps, _st = SC.variant_costs(v)
    pins = c['pins']['value'] or 0
    mode = SC.ROUTE_CYCLES.get(v['route'], ('polled',))[0]
    if objective == 'fastest-cycle':
        return (v['_needs_parts'], {'event': 0, 'immediate': 0, 'polled': 1}.get(mode, 1), SC.CPU_CLASS.get(v['route'], 9), pins, v['route'])
    return (v['_needs_parts'], len([p for p in ps if p['on_bench'] is False]), pins, c['peripherals']['value'] or 0, SC.CPU_CLASS.get(v['route'], 9), v['route'])


# ------------------------------------------------------------------ the explanation of a placement
def _why(need, o, opts, rej, bench, prefer='least-specialised'):
    cheapest = min(x['spec'] for x in opts)
    same = [x['pin'] for x in opts if x['spec'] == o['spec'] and x['pin'] != o['pin']]
    parts = ['%s as %s' % (o['pin'], o['function'])]
    if prefer == 'bench-wiring' and bench and bench.get('pin') == o['pin'] and o['spec'] > cheapest:
        parts.append('kept on the pin the bench is already wired to (cost %.2f; the least specialised choice would be %s at %.2f)' % (o['spec'], min(opts, key=lambda x: (x['spec'], x['index']))['pin'], cheapest))
    elif o['spec'] == cheapest:
        parts.append('the least specialised pin that can do it (cost %.2f)' % o['spec'])
        if same:
            parts.append('tied with %s, broken by pin order' % ', '.join(same[:3]))
    else:
        parts.append('the cheapest pin left (cost %.2f; the cheaper ones %s were taken by other needs)' % (o['spec'], ', '.join(x['pin'] for x in opts if x['spec'] < o['spec'])[:60] or 'none'))
    if o['wasted']:
        parts.append('it also carries %s, which stays unused' % ', '.join(o['wasted']))
    elif need['kind'] not in ('uart-rx', 'uart-tx'):
        parts.append('it carries nothing else scarce')
    if bench and bench.get('pin') == o['pin']:
        parts.append('the bench is wired here today')
    gone = next((r for r in rej if bench and r['pin'] == bench.get('pin') and r['kind'] != 'no-function'), None)
    if gone and bench.get('pin') != o['pin']:
        parts.append('the bench is wired to %s but it is not available: %s' % (gone['pin'], gone['text'][:140]))
    nxt = [x for x in opts if x['pin'] != o['pin']][:3]
    if nxt:
        parts.append('next best: ' + ', '.join('%s (%.2f)' % (x['pin'], x['spec']) for x in nxt))
    return '; '.join(parts)


def _refused(rej):
    """The pins this need may not use, by name, with the rung or claim: the ones that carry the function first, then a count of the rest."""
    named = [r for r in rej if r['kind'] != 'no-function']
    return [{'pin': r['pin'], 'rung': r['rung'], 'kind': r['kind'], 'why': r['text'], 'cite': r['cite']} for r in named], sum(1 for r in rej if r['kind'] == 'no-function')


def _risks(assignment, hw, combo, tier_rep, lost):
    out, pts = [], 0
    rungs = {}
    for nid, a in assignment.items():
        for r in a['risks']:
            rungs.setdefault((r['rung'], r['name'], r['verdict']), []).append(a['pin'])
            pts += 1
    for (rung, name, verdict), pins in sorted(rungs.items()):
        out.append({'kind': 'ladder', 'text': 'rung %d (%s) %s on %s' % (rung, name, verdict, ', '.join(sorted(set(pins)))), 'rung': rung})
    if tier_rep:
        if tier_rep.get('state') == 'undetermined':
            out.append({'kind': 'tier', 'text': 'the %s tier is undetermined here: %s' % (tier_rep['tier'], tier_rep['why'][:140])})
    for u, note in sorted(hw['usb_notes'].items()):
        if 'undetermined' in note or 'unverified' in note:
            out.append({'kind': 'usb', 'text': 'USB interface %s: %s' % (u, note[:160])})
    for j, v in sorted(combo.items()):
        if v.get('_needs_parts'):
            out.append({'kind': 'part', 'text': 'the %s route needs a part the bench does not have' % v['route']})
    return out, pts


class Engine:
    def __init__(self, mission, boards, tiers, objective, limits, manager, spec=None):
        from board.custom import board_object as BO
        from cmod.custom import approach_profile_input as AI
        from cmod.custom import isotope_variants as IV
        from cmod.custom import isotope_variants_eligibility as E
        self.lim = normalise_limits(limits)
        self.manager = manager
        self.row = SI.mission_row(mission, manager)
        self.objective = SI.objective_of(self.row, objective)
        self.secondary = [o for o in SI.OBJECTIVES if o != self.objective][0]
        self.pm = SI.mission_profiles(self.row['name'], self.lim['purposes'], manager)
        self.profiles = self.pm['profiles']
        self.order, self.by_job, self.fixed = SI.job_plan(self.profiles, self.lim['only_jobs'])
        self.tables = BO.seed_tables()
        part = next((p.get('ref') for p in json.loads(self.row.get('participants_json') or '[]') if p.get('role') == 'board'), '')
        known = E.boards()
        self.boards = boards or ([part] if part in known else []) + [b for b in known if b != part]
        self.tiers_ask = tiers
        self.spec = spec or AI.from_mission(self.row, manager)
        self.approach = SI.tier_reports(self.boards, self.row['name'], self.spec, manager)
        self.hardware = SI.hardware_contexts(self.boards, self.lim, self.tables, manager)
        self.variants_all = {j: IV.variants(manager, j) for j in self.order}
        self.siblings = {j: {v['route']: v for v in vs} for j, vs in self.variants_all.items()}
        self.directions = {j['name']: j['direction'] for j in IV.jobs(manager)}
        self.job_purposes = {j: {p for m in self.by_job[j] for p in m['purposes']} for j in self.order}
        self.held = SI.held_peripherals(self.pm.get('unresolved'))
        self.pruned = PrunedLog(self.lim['pruned_first'])
        self.oracles = {}
        self.elig = {}
        self.counts = {'combos': 0, 'placed': 0, 'ladder_calls': 0, 'nodes': 0}
        self.candidates, self.fail_by_key, self.fail_need, self.tier_gone = [], {}, {}, {}
        self.skip_atoms = set()
        for j in self.order:
            for v in self.variants_all[j]:
                self.skip_atoms |= set(json.loads(v['implemented_by_json'] or '{}').get('atoms', []))
        self.purposes = self.spec['purposes']
        if self.lim['purposes']:
            keep = {p if isinstance(p, str) else p['purpose'] for p in self.lim['purposes']}
            self.purposes = [p for p in self.purposes if p['purpose'] in keep]

    def fingerprint(self):
        rows = [v for j in self.order for v in self.variants_all[j]]
        return SI.fingerprint(self.row, self.profiles, rows, self.hardware, self.tables, dict(self.lim, tiers=self.tiers_ask, boards=self.boards),
                              self.objective, {b: {t: r['state'] for t, r in a['tiers'].items()} for b, a in self.approach.items()})

    # ------------------------------------------------------------------ the loop
    def run(self):
        for hw in self.hardware:
            appr = self.approach[hw['board']]
            oracle = None
            if hw['ladder']:
                uni = SN.pin_universe(hw, self.tables)
                oracle = SO.Oracle(hw, self.tables, SN.scarcity(uni), uni, self.lim['occupied'], self.held, SI.bench_pins(hw['board'], self.manager), self.lim['prefer'],
                                   self.lim['ladder_context'], transport=any(p.get('reserved') for p in self.profiles))
                hw['n_header'] = sum(1 for p in uni if p['header'])
                self.oracles[(hw['board'], hw['package'])] = oracle
            else:
                hw['n_header'] = 20
            for tier in TIERS:
                rep = appr['tiers'][tier]
                if self.tiers_ask and tier not in self.tiers_ask:
                    self.pruned.add('tier-skipped', '%s / %s' % (hw['board'], tier), 'not in the tiers asked for (%s)' % ', '.join(self.tiers_ask))
                    continue
                if rep['state'] == 'blocked':
                    self.pruned.add('tier-blocked', '%s / %s' % (hw['board'], tier), rep['why'])
                    self.tier_gone[(hw['board'], hw['package'], tier)] = rep['why']
                    continue
                self._tier(hw, tier, rep, appr, oracle)
            if oracle:
                self.counts['ladder_calls'] += oracle.ladder_calls
        return self

    def _tier(self, hw, tier, rep, appr, oracle):
        where = '%s / %s / %s' % (hw['board'], hw['package'] or 'package not modelled', tier)
        usable = {}
        for j in self.order:
            use, gone = usable_variants(j, hw, tier, self.manager, self.elig)
            for v, why in gone:
                self.pruned.add('variant-ineligible', '%s / %s' % (where, v['name']), why)
            if not use:
                why = 'no variant of the job %s can run here: %s' % (j, '; '.join(sorted({w for _v, w in gone}))[:300] or 'none catalogued')
                self.pruned.add('no-variant', where, why)
                self.tier_gone[(hw['board'], hw['package'], tier)] = why
                return
            usable[j] = sorted(use, key=lambda v: _standalone_key(v, self.objective))
        combos = list(itertools.product(*[usable[j] for j in self.order]))
        if len(combos) > self.lim['max_combos']:
            self.pruned.add('limit', where, '%d variant combinations exist; only the first %d (cheapest first) were tried (max_combos)' % (len(combos), self.lim['max_combos']))
            combos = combos[:self.lim['max_combos']]
        timings = {}

        def timing_for(job, v):
            k = (hw['board'], v['name'])
            if k not in timings:
                proc = (self.spec['processors'] or [{}])[0]
                timings[k] = SC.route_timing(v, self.directions.get(job, 'in'), hw, {'baud': proc.get('baud'), 'frame_bytes': proc.get('frame_bytes')}, self.siblings)
            return timings[k]
        made, infeasible = [], []
        for ci, combo_t in enumerate(combos):
            combo = dict(zip(self.order, combo_t))
            self.counts['combos'] += 1
            needs = SN.needs_for(combo, self.by_job, self.fixed)
            if oracle is None:
                made.append(self._candidate(hw, tier, rep, appr, combo, needs, None, [], timing_for, ci, where))
                continue
            res = SA.assign(needs, oracle, self.lim['max_nodes'], self.lim['share_pins'])
            self.counts['nodes'] += res['nodes']
            if res['bounded']:
                self.pruned.add('search-bounded', '%s / %s' % (where, ' + '.join(v['route'] for v in combo.values())), 'the search hit max_nodes (%d); the best found is kept if there is one' % self.lim['max_nodes'])
            self._log_refusals(hw, needs, res, where)
            if res['ok']:
                self.counts['placed'] += 1
                made.append(self._candidate(hw, tier, rep, appr, combo, needs, res, [], timing_for, ci, where))
            else:
                infeasible.append((ci, combo, needs, res))
                fk = (hw['board'], hw['package'], tier, tuple(sorted((j, v['route']) for j, v in combo.items())))
                self.fail_by_key[fk] = res['fail']['why']
                self.fail_need[fk] = res['fail']['need'].partition(':')[0]
                self.pruned.add('no-placement', '%s / %s' % (where, ' + '.join('%s:%s' % (j, v['route']) for j, v in combo.items())), res['fail']['why'])
        if oracle is None:
            made.sort(key=lambda c: (c['primary'], c['secondary'], c['ci']))
            for c in made[self.lim['undetermined_keep']:]:
                self.pruned.add('hardware-undetermined', where, 'variant combination %s kept out of the list: placement cannot be worked out on this hardware (%s)' % (c['routes_text'], hw['why_not_ladder']))
            made = made[:self.lim['undetermined_keep']]
        elif not made and infeasible:
            for ci, combo, needs, res in infeasible[:self.lim['partial_combos']]:
                kept, lost, full = SA.place_by_importance(needs, self.order, oracle, self.lim['max_nodes'], self.lim['share_pins'])
                if kept is not None:
                    made.append(self._candidate(hw, tier, rep, appr, {j: v for j, v in combo.items() if j not in {x['job'] for x in lost}}, [n for n in needs if n['job'] not in {x['job'] for x in lost}],
                                                kept, lost, timing_for, ci, where, full_combo=combo))
        self.candidates += made

    def _log_refusals(self, hw, needs, res, where):
        for n in needs:
            key = (hw['board'], hw['package'], n['kind'], n['okind'], tuple(n['patterns']), n['role'], n['reserved'])
            seen = self.__dict__.setdefault('_seen_ref', set())
            if key in seen:
                continue
            seen.add(key)
            named, nofn = _refused(res['rejmap'][n['id']])
            for r in named:
                self.pruned.add('pin-refused', '%s / %s (%s)' % (where, n['role'], n['kind']), '%s refused at rung %s (%s): %s' % (r['pin'], r['rung'], r['kind'], r['why']))

    # ------------------------------------------------------------------ one candidate
    def _candidate(self, hw, tier, rep, appr, combo, needs, res, lost, timing_for, ci, where, full_combo=None):
        from cmod.custom import pin_profiles as PPm
        asg, rows, bench = {}, [], SI.bench_pins(hw['board'], self.manager)
        if res is not None:
            for n in needs:
                o = res['assignment'][n['id']]
                opts = res['optmap'][n['id']]
                refused, nofn = _refused(res['rejmap'][n['id']])
                b_pin = next((p for p, r in bench.items() if r == n['role']), '')
                asg[n['id']] = o
                rows.append({'need': n['id'], 'role': n['role'], 'part': n['part'], 'kind': n['kind'], 'job': n['job'], 'route': n['route'], 'pin': o['pin'], 'function': o['function'],
                             'importance': n['importance'], 'purposes': n['purposes'], 'spec_cost': o['spec'], 'wasted': o['wasted'], 'bus_shared': n['bus_shared'],
                             'why': _why(n, o, opts, res['rejmap'][n['id']], {'pin': b_pin}, self.lim['prefer']), 'options': len(opts), 'refused': refused[:12], 'refused_no_function': nofn,
                             'risks': o['risks'], 'bench_pin': b_pin})
        used = sorted({r['pin'] for r in rows})
        full = full_combo or combo
        res_cost = SC.resources(combo, len(used) if res is not None else sum(1 for n in needs), hw['n_header'], rep, self.lim['weights'])
        cyc = SC.cycle(combo, timing_for, self.purposes, hw, self.spec, self.approach[hw['board']], self.job_purposes, self.skip_atoms)
        res_score = res_cost['score']
        cyc_us = cyc['total_us']['value']
        risks, risk_pts = _risks(asg, hw, {j: v for j, v in combo.items()}, rep, lost)
        if res is not None:
            for x in res.get('periph', []):
                risks.append({'kind': 'peripheral', 'text': '%s and %s share one peripheral (%s): %s' % (x['a'], x['b'], x['verdict'], x['condition'][:160])})
            for x in res['nets']:
                if not x['applies'] or x['verdict'] != 'compatible':
                    risks.append({'kind': 'net', 'text': 'the wire %s -> %s: %s%s' % (x['a'], x['b'], x['verdict'], (' - ' + x['condition']) if x['condition'] else (' - ' + x['reason'][:140]))})
            for x in res['sharing']:
                risks.append({'kind': 'sharing', 'text': 'pin %s is shared by %s%s' % (x['pin'], ' + '.join(x['needs']), (' if ' + '; '.join(x['conditions'])) if x['conditions'] else '')})
        soc_opts = []
        if res is None:
            risks.append({'kind': 'placement', 'text': 'pins cannot be placed: %s' % hw['why_not_ladder']})
            socpins = [{'canonical': sp['pin'], 'functions': json.loads(sp['functions_json'] or '[]')} for sp in self.tables['SocPin'] if sp['soc'] == hw['soc']]
            for n in needs:
                hit = [sp['canonical'] for sp in socpins if SN.pick_function(sp, n['patterns'])]
                soc_opts.append({'need': n['id'], 'role': n['role'], 'kind': n['kind'], 'soc_pins_by_name': len(hit), 'examples': hit[:4],
                                 'verdict': 'undetermined: the name matches only; the routing, the header and the overlap rules for %s are not modelled' % hw['soc']})
        if lost:
            for l in lost:
                risks.append({'kind': 'lost', 'text': 'the %s loses its pins: %s' % (l['role'], l['why'][:200])})
        missing = res_cost['parts_missing']
        viol = cyc['criteria_violated']
        for t in viol:
            risks.append({'kind': 'criterion', 'text': 'does not meet a Purpose bound - ' + t})
        for r_ in cyc['purposes']:
            if r_['criterion']['state'] == 'fits (with a stand-in)':
                risks.append({'kind': 'criterion', 'text': 'fits %s only with a stand-in for an undetermined time' % r_['purpose']})
        rank_class = 4 if res is None else (3 if lost else (2 if viol else (1 if missing else 0)))
        primary, secondary = (res_score, cyc_us) if self.objective == 'minimum-resources' else (cyc_us, res_score)
        routes = {j: v['route'] for j, v in full.items()}
        lw = tuple(sum(1 for l in lost if l['importance'] == lvl) for lvl in PPm.IMPORTANCE)
        cid = SI.sha([hw['board'], hw['package'], tier, sorted(routes.items()), [l['job'] for l in lost]])[:10]
        return {'id': cid, 'ci': ci, 'hardware': {'board': hw['board'], 'soc': hw['soc'], 'package': hw['package'], 'usb_interfaces': hw['usb_interfaces'], 'variant_pending': hw['variant_pending']},
                'tier': tier, 'tier_state': rep['state'], 'routes': routes, 'routes_text': ', '.join('%s:%s' % kv for kv in sorted(routes.items())),
                'variant_status': {j: SC.variant_costs(v)[2] for j, v in full.items()}, 'rank_class': rank_class, 'placement': ['placed', 'placed', 'placed', 'partial', 'undetermined'][rank_class],
                'complete': not lost and res is not None, 'meets_criteria': not viol, 'lost': lost, 'lost_weight': lw, 'assignment': rows, 'pins_used': used,
                'sharing': res['sharing'] if res else [], 'nets': res['nets'] if res else [], 'resources': res_cost, 'cycle': cyc, 'resource_score': res_score, 'cycle_us': cyc_us,
                'primary': primary, 'secondary': secondary, 'risks': risks, 'risk_points': risk_pts, 'parts_missing': missing, 'parts_unsure': res_cost['parts_unsure'],
                'soc_options': soc_opts, 'buildable_on_bench': not missing, 'search': {'nodes': res['nodes'] if res else 0, 'bounded': res['bounded'] if res else False}, 'where': where}


def rank_key(c, hw_order, tier_order):
    return (c['rank_class'], c['lost_weight'], c['primary'], c['secondary'], c['risk_points'], hw_order[(c['hardware']['board'], c['hardware']['package'])], tier_order.get(c['tier'], 9), c['ci'], c['id'])
