"""cmod_fsc_selftest - fsc-0/1/2: Firmware Score Profiles (AI-Notes/plans/FIRMWARE_SCORE_PROFILES_PLAN.md) on the UNO light Mission.

fsc-0  the failure rule (D-fsc-1), the safety_critical flag, the suggestion, Mission Solution <-> built config link, finished|plan, the seeded Firmware Score Terms (ScoreTerm rows)
fsc-1  the value writer (hardware:<board> / purpose:<name> contexts, kind + basis, importance-weighted splits D-fsc-5, cited offers D-fsc-2), the rows in the scoring module, the
       stock scoring engine agreeing with ours, today's two objectives as profiles and the REPRODUCED ranking
fsc-2  the seeded profiles, competitive scoring (top 100 / bottom 0), the doors (scores, top, breakdown, profiles, values), the CLI

    PYTHONPATH=.:modules python3 -m cmod.cmod_fsc_selftest
"""
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
from types import SimpleNamespace

UNO, LIGHT = 'arduino-uno-r3', 'uno-light-mission'


def fsc_parts(check):
    state = {}

    def built():
        if 'b' not in state:
            from cmod.custom import fsc_run as R
            state['b'] = R.build(LIGHT, None, [UNO])
        return state['b']

    def manager_built():
        """The Mission as a live server sees it: a manager whose ScenarioRuns say which Purposes are proven."""
        if 'mb' not in state:
            from cmod.custom import fsc_run as R
            from cmod.custom.selftest_purpose import _manager
            mgr = _manager()
            state['mgr'] = mgr
            state['mb'] = R.build(LIGHT, mgr, [UNO])
        return state['mb']

    # ------------------------------------------------------------------ fsc-0
    def terms_seeded():
        from cmod.custom import fsc_terms as T
        rows = T.term_rows()
        names = [r['name'] for r in rows]
        want = {'mission-cycle', 'worst-purpose-latency', 'deadline-fit', 'boot-to-ready', 'flash-free', 'ram-free', 'pins-free', 'blocks-free', 'cpu-idle', 'sleep-capable', 'risk-points',
                'shared-resources', 'confidence', 'proof-level', 'parts-to-acquire', 'part-count', 'wires', 'code-size', 'also-runs-on', 'bom-cost', 'cost-to-build-now', 'active-current', 'noise-immunity'}
        check('fsc-0 TERMS: every term of plan section 4 is a ScoreTerm row (category firmware), unique, each with a plain-words description, a direction and a stated normalization (%d terms)' % len(rows),
              want <= set(names) and len(names) == len(set(names)) and all(r['category'] == 'firmware' and r['description'] and json.loads(r['normalization_json'])['method'] == 'min-max-auto' for r in rows), sorted(want - set(names)))
        check('fsc-0 TERMS: active-current and noise-immunity are seeded as UNDETERMINED (no basis yet), said in their notes; every other term has a basis today',
              all('UNDETERMINED' in r['notes'] for r in rows if r['name'] in T.UNDETERMINED) and not any('UNDETERMINED' in r['notes'] for r in rows if r['name'] not in T.UNDETERMINED))
        from cmod.cmod_seed import CMOD_SEED_PAIRS
        pairs = {n: rs for n, _c, rs in CMOD_SEED_PAIRS if n in ('ScoreTerm', 'ScoreConcept')}
        check('fsc-0 SEED: the terms and the profiles converge through CMOD_SEED_PAIRS as the scoring module\'s OWN classes (ScoreTerm, ScoreConcept) - no new score class',
              {r['name'] for r in pairs['ScoreTerm']} == set(names) and len(pairs['ScoreConcept']) == 10 and all(r.get('_converge') for r in pairs['ScoreTerm']))
        from scoring.scoring_basis import CONTEXT_TYPES
        check('fsc-1: the scoring module knows the context types `hardware` and `purpose` (purpose more specific than hardware)', CONTEXT_TYPES.get('hardware') == 5 and CONTEXT_TYPES.get('purpose') == 6)

    def safety_flag_and_failures():
        from cmod.custom import approach_profile_input as AI
        from cmod.custom import fsc_failure as F
        from cmod.custom import mission_derived as MD
        row = AI.find_mission(LIGHT)
        base = {p['purpose']: p for p in AI.purposes_of(row)}
        check('fsc-0 FLAG: purposes_of reads `safety_critical` off the deadline criterion; the seeded Purposes carry no flag, so it defaults to false', all(p['safety_critical'] is False for p in base.values()) and len(base) == 4)
        orig = MD.capability

        def flagged(name, manager=None):
            cap = orig(name, manager)
            if cap and name == 'ensure-button-controls-light':
                spec = json.loads(cap['criteria_json'])
                for c in spec['criteria']:
                    if c['key'] == 'max_latency_ms':
                        c['safety_critical'] = True
                cap = dict(cap, criteria_json=json.dumps(spec))
            return cap
        MD.capability = flagged
        try:
            fl = {p['purpose']: p for p in AI.purposes_of(row)}
        finally:
            MD.capability = orig
        check('fsc-0 FLAG: a criterion with safety_critical: true makes THAT Purpose flagged and no other', fl['ensure-button-controls-light']['safety_critical'] is True and not fl['initialization']['safety_critical'])
        c0 = copy.deepcopy(built()['records'][0]['candidate'])
        check('fsc-0 FAIL RULE: a normal candidate (placed, all Purposes kept, no flagged deadline) does not fail', F.failure_of(c0) is None)
        c1 = copy.deepcopy(c0)
        crit = next(p for p in c1['cycle']['purposes'] if p['purpose'] == 'ensure-button-controls-light')['criterion']
        crit.update(state='violates', why='cycle over budget')
        check('fsc-0 FAIL RULE (his D-fsc-1): an UNFLAGGED deadline violation is NOT a failure (scored by closeness) but is listed', F.failure_of(c1) is None and F.unflagged_violations(c1)[0]['purpose'] == 'ensure-button-controls-light')
        crit['safety_critical'] = True
        f = F.failure_of(c1)
        check('fsc-0 FAIL RULE: the SAME violation on a deadline flagged safety_critical IS a failure, naming the Purpose and the reason', f and f['kind'] == 'safety-deadline' and f['purpose'] == 'ensure-button-controls-light' and 'safety-critical' in f['reason'], f)
        c2 = copy.deepcopy(c0)
        c2['lost'] = [{'job': 'sense-led-line', 'role': 'the sense line', 'purposes': ['ensure-polari-observes-hardware-state'], 'why': 'no pin left', 'importance': 'required'}]
        f2 = F.failure_of(c2)
        check('fsc-0 FAIL RULE: a lost Purpose fails, naming it', f2 and f2['kind'] == 'purpose-lost' and f2['purpose'] == 'ensure-polari-observes-hardware-state', f2)
        c3 = copy.deepcopy(c0)
        c3.update(rank_class=4, placement='undetermined')
        c3['risks'] = c3['risks'] + [{'kind': 'placement', 'text': 'pins cannot be placed: the C3 is not modelled'}]
        check('fsc-0 FAIL RULE: pins that cannot be placed fail', (F.failure_of(c3) or {}).get('kind') == 'unplaceable')
        miss = next(r['candidate'] for r in built()['records'] if r['candidate']['parts_missing'])
        check('fsc-0 FAIL RULE: MISSING PARTS are not a failure (a cost term): %s needs %s' % (miss['routes_text'][:60], ', '.join(p['class'] for p in miss['parts_missing'])[:60]), F.failure_of(miss) is None)
        pur = [dict(p, importance='safety') for p in base.values() if p['purpose'] == 'ensure-button-controls-light']
        sug = F.suggestions(pur)
        check('fsc-0 SUGGESTION: a Purpose of importance safety with an unflagged deadline yields "flag this deadline safety-critical?" and is never auto-flagged',
              len(sug) == 1 and 'Flag this deadline safety-critical?' in sug[0]['message'] and sug[0]['auto_applied'] is False and not pur[0]['safety_critical'])
        check('fsc-0 SUGGESTION: none when the deadline is already flagged, and none for a non-safety Purpose', F.suggestions([dict(pur[0], safety_critical=True)]) == [] and F.suggestions(list(base.values())) == [])

    def link_and_finished():
        from cmod.custom import fsc_link as L
        b = built()
        linked = {r['link']['config']: r for r in b['records'] if r['link']}
        check('fsc-0 LINK: the six built configs that carry a route for EVERY job of the Mission (the three of fgm-5b and the sample S2, S3, S4 of smp-1) resolve to the candidate whose routes they implement: %s' % sorted(linked),
              sorted(linked) == ['uno-button-clock', 'uno-light-all-pcint', 'uno-light-pwm-analog', 'uno-light-sense-pcint', 'uno-light-sense-poll', 'uno-light-transistor'], sorted(linked))
        want = {'uno-button-clock': {'read-button': 'ext-interrupt', 'sense-led-line': 'ext-interrupt', 'drive-led': 'gpio-out'}, 'uno-light-sense-poll': {'read-button': 'ext-interrupt', 'sense-led-line': 'gpio-poll', 'drive-led': 'gpio-out'},
                'uno-light-sense-pcint': {'read-button': 'ext-interrupt', 'sense-led-line': 'pin-change-interrupt', 'drive-led': 'gpio-out'},
                'uno-light-all-pcint': {'read-button': 'pin-change-interrupt', 'sense-led-line': 'pin-change-interrupt', 'drive-led': 'gpio-out'},
                'uno-light-pwm-analog': {'read-button': 'analog-threshold', 'sense-led-line': 'gpio-poll', 'drive-led': 'pwm'},
                'uno-light-transistor': {'read-button': 'ext-interrupt', 'sense-led-line': 'gpio-poll', 'drive-led': 'transistor-switch'}}
        check('fsc-0 LINK: the linked candidate\'s routes are exactly the config\'s DERIVED routes (derived from the variant features and knobs - button_route, sense_route, led_route - not typed in)',
              all(r['candidate']['routes'].get(j) == rt for cfg, r in linked.items() for j, rt in want[cfg].items()))
        check('fsc-0 LINK: uno-button-clock is a FirmwareSolution row; the two fgm-5b configs are FirmwareVariants (no FirmwareSolution row exists for them) and the link says which',
              linked['uno-button-clock']['link']['kind'] == 'FirmwareSolution' and linked['uno-light-sense-poll']['link']['kind'] == 'FirmwareVariant')
        un = {u['config']: u['why'] for u in b['unmatched_configs']}
        check('fsc-0 LINK (fsc-0b): configs built for ANOTHER job (uno-sim-rig, -pair, -blink-only, -adc-sweep, -echo: no route for a job that triggers a Purpose) are NOT candidates of this Mission and say why; the light configs are not in that list',
              set(un) == {'uno-sim-rig', 'uno-pair', 'uno-blink-only', 'uno-adc-sweep', 'uno-echo'} and all(w.startswith('not a candidate for this Mission: it was built for another job') for w in un.values()) and 'read-button' in un['uno-sim-rig'], sorted(un))
        cf = {f['config']: f for f in b['failures'] if f['kind'] == 'purpose-unfulfilled'}
        check('fsc-0b FAILURES: uno-light, -pcint, -analog and -v2 (built for this Mission, no route for sense-led-line) are FAILURES: the Purposes that job serves (derived from the Mission, not typed), the reason in plain words, no rank, no score',
              set(cf) == {'uno-light', 'uno-light-pcint', 'uno-light-analog', 'uno-light-v2'} and all(f['state'] == 'failed' and f['rank'] is None and f['purpose'] == 'ensure-button-controls-light, ensure-polari-can-control-light, ensure-polari-observes-hardware-state'
                                                                                                    and 'sense-led-line' in f['reason'] and 'does not fulfil' in f['reason'] and f['solution'] == f['config'] for f in cf.values()), sorted(cf))
        check('fsc-0b FAILURES: a failing config never appears among the records (so it is never scored or compared) and is counted in counts.failed (%d)' % b['counts']['failed'],
              not ({r['link']['config'] for r in b['records'] if r['link']} & set(cf)) and b['counts']['failed'] == len(b['failures']) and len(cf) == 4)
        from cmod.custom import fsc_context as C
        ctx = b['ctx']
        check('fsc-0b ATTEMPT: a config is built for the Mission when it carries a route for the job triggering each Purpose (button -> read-button, command -> receive-command, period -> report-state); uno-sim-rig has no button',
              L.attempt_of(L.config_routes(L.configs()['uno-light']), ctx)[0] and not L.attempt_of(L.config_routes(L.configs()['uno-sim-rig']), ctx)[0] and not L.attempt_of({}, ctx)[0])
        check('fsc-0 LINK: where the build\'s pins differ from the candidate\'s the link says so (the routes match, the pin choice is the solver\'s)',
              all(isinstance(r['link']['pins_agree'], bool) and r['link']['pins_note'] for r in linked.values()))
        check('fsc-0 FINISHED (no server): nothing is `finished` - no ScenarioRun can be read, so every built solution is listed as plan and says why',
              b['counts']['finished'] == 0 and all('no live server' in r['state_why'] for r in linked.values()), [r['state_why'][:60] for r in linked.values()])
        mb = manager_built()
        mgr = state['mgr']
        # no passing run yet in a fresh manager -> plan, naming the Purposes unproven
        r0 = next(r for r in mb['records'] if r['link'] and r['link']['config'] == 'uno-button-clock')
        check('fsc-0 FINISHED: built but with Purposes unproven (no passing ScenarioRun) -> plan, naming the unproven Purposes', r0['state'] == 'plan' and 'not every Purpose is proven' in r0['state_why'], r0['state_why'][:200])
        from cmod.custom import capabilities as CAP
        from cmod.custom import fsc_run as R
        runs = mgr.objectTables.setdefault('ScenarioRun', {})
        three = ['uno-button-clock', 'uno-light-sense-pcint', 'uno-light-sense-poll']

        def put(config, purposes=None, outcome='passed'):
            for i, p in enumerate(mb['ctx']['purposes']):
                if purposes is None or p['purpose'] in purposes:
                    cap = CAP.find(p['purpose'])
                    runs[(config, p['purpose'])] = SimpleNamespace(name='run-%s-%d' % (config, i), scenario=cap['acceptance_scenario'], variant=config, outcome=outcome, ran_at='2026-10-18T10:00:0%d' % i,
                                                                   repro_json='{"mode": "digital-twin"}', kind='measured', verdict_words=outcome)

        def finished(**kw):
            built_ = R.build(LIGHT, mgr, [UNO], **kw)
            return built_, {r['link']['config'] for r in built_['records'] if r['state'] == 'finished'}, {r['link']['config']: r for r in built_['records'] if r['link']}
        check('fsc-0b PROOF: all four Purposes of the Mission now have an acceptance scenario (initialization-acceptance), so nothing is `unprovable`',
              all(CAP.find(p['purpose']).get('acceptance_scenario') for p in mb['ctx']['purposes']) and CAP.find('initialization')['acceptance_scenario'] == 'initialization-acceptance')
        put('uno-light')
        b1, fin, by = finished()
        check('fsc-0b PROOF (the honest reading): every Purpose proven on uno-light proves NOTHING for the three linked configs - their firmware was not the one run - so none is finished and the reason says so',
              not fin and b1['counts']['finished'] == 0 and all("no ScenarioRun of config %s's own firmware" % c in by[c]['state_why'] for c in three), by['uno-button-clock']['state_why'][:300])
        for c in three:
            put(c)
        b2, fin, by = finished()
        check('fsc-0 FINISHED: built AND every Purpose proven by runs of THAT config\'s own firmware -> finished: %s; every other candidate stays plan (%d)' % (sorted(fin), b2['counts']['plan']),
              fin == set(three) and b2['counts']['finished'] == 3 and b2['counts']['plan'] == b2['counts']['distinct_plans'] - 3, b2['counts'])
        del runs[('uno-light-sense-poll', 'initialization')]
        _b3, fin, by = finished()
        check('fsc-0b PROOF: take away ONE Purpose\'s run for ONE config and only that config drops back to plan (naming the Purpose); the other two stay finished',
              fin == {'uno-button-clock', 'uno-light-sense-pcint'} and 'initialization' in by['uno-light-sense-poll']['state_why'] and by['uno-light-sense-poll']['state'] == 'plan', by['uno-light-sense-poll']['state_why'][:200])
        put('uno-light-sense-poll', {'initialization'}, outcome='failed')
        _b4, fin, _by = finished()
        check('fsc-0 FINISHED: a LATER FAILED run takes the proof away again (a stale pass is never carried forward)', 'uno-light-sense-poll' not in fin and len(fin) == 2)
        orig_find = CAP.find
        CAP.find = lambda name, rows=None: dict(orig_find(name, rows), acceptance_scenario='') if name == 'initialization' else orig_find(name, rows)
        try:
            R._CACHE.clear()
            put('uno-light-sense-poll', {'initialization'})
            strict, fin_s, by_s = finished()
            lenient, fin_l, _ = finished(unprovable='ignore')
        finally:
            CAP.find = orig_find
            R._CACHE.clear()
        check('fsc-0 FINISHED: a Purpose with NO acceptance scenario is `unprovable`: by default it keeps everything from finishing and the reason says so; unprovable=ignore leaves it out of the test',
              not fin_s and 'initialization (unprovable' in by_s['uno-button-clock']['state_why'] and fin_l == set(three), by_s['uno-button-clock']['state_why'][:200])

    # ------------------------------------------------------------------ fsc-1
    def value_writer():
        from cmod.custom import fsc_terms as T
        b = built()
        r = b['records'][0]
        have = set(r['values'])
        check('fsc-1 VALUES: every candidate carries a value for every term that has a basis (%d), none for the two undetermined terms' % len(have),
              all(set(x['values']) >= (set(T.TERM_NAMES) - set(T.UNDETERMINED)) and not (set(x['values']) & set(T.UNDETERMINED)) for x in b['records']), sorted(set(T.TERM_NAMES) - have))
        check('fsc-1 VALUES: every value has a kind (measured | estimated | cited | stand-in) and a non-empty BASIS in words; a stand-in is a number, never zero-by-default',
              all(v['kind'] in T.KINDS and v['basis'] for x in b['records'] for v in list(x['values'].values()) + [t for d in x['purpose_values'].values() for t in d.values()]))
        kinds = {v['kind'] for x in b['records'] for v in x['values'].values()}
        check('fsc-1 VALUES: the kinds actually present: %s (measured cycle counts, estimated sizes, cited prices, stand-ins where undetermined)' % sorted(kinds), {'measured', 'estimated', 'cited'} <= kinds, kinds)
        pv = r['purpose_values']
        check('fsc-1 PURPOSE CONTEXT: each Purpose of the Mission has its own values (its cycle, deadline-fit, route time, cost and parts share): %s' % sorted(pv),
              set(pv) == {'initialization', 'ensure-button-controls-light', 'ensure-polari-can-control-light', 'ensure-polari-observes-hardware-state'} and all({'worst-purpose-latency', 'route-time', 'bom-cost', 'parts-to-acquire'} <= set(d) for d in pv.values()))

    def splits():
        from cmod.custom import fsc_context as C
        b = built()
        tot_ok, rt_ok, pa_ok = [], [], []
        for x in b['records']:
            hw, pv = x['values'], x['purpose_values']
            tot_ok.append(abs(sum(d['bom-cost']['value'] for d in pv.values()) - hw['bom-cost']['value']) < 0.03)  # four Purposes, each rounded to a cent
            pa_ok.append(abs(sum(d['parts-to-acquire']['value'] for d in pv.values()) - hw['parts-to-acquire']['value']) < 0.005)
            pc = abs(sum(d['part-count']['value'] for d in pv.values()) - hw['part-count']['value']) < 0.005
            rt_ok.append(pc)
        check('fsc-1 SPLIT (D-fsc-5): across all %d candidates the Purposes\' shares of the cost add up to the whole solution\'s bom-cost, and of the parts to the part count and the parts to get' % len(b['records']),
              all(tot_ok) and all(pa_ok) and all(rt_ok), (sum(not t for t in tot_ok), sum(not t for t in pa_ok), sum(not t for t in rt_ok)))
        x = b['records'][0]
        basis = x['purpose_values']['ensure-button-controls-light']['bom-cost']['basis']
        check('fsc-1 SPLIT: a shared route / part / the board is split BY IMPORTANCE WEIGHT and every split is STATED in the basis ("shared by N Purposes, split by importance weight: ... required 3/12 = 25%")',
              'split by importance weight' in basis and 'required 3/' in basis and '%' in basis, basis[:300])
        ctx = {'by_name': {'a': {'weight': 4.0, 'importance': 'safety'}, 'b': {'weight': 3.0, 'importance': 'required'}, 'c': {'weight': 1.0, 'importance': 'desired'}}}
        sh, words = C.split(ctx, ['a', 'b', 'c'])
        check('fsc-1 SPLIT: safety 4 / required 3 / desired 1 split a shared thing 50%% / 37.5%% / 12.5%% (the knobs), stated: %s' % words[:80],
              [(n, round(s, 4)) for n, s in sh] == [('a', 0.5), ('b', 0.375), ('c', 0.125)] and 'safety 4/8 = 50%' in words, sh)
        w = C.mission_context(LIGHT, None, {'required': 1.0, 'safety': 9.0})
        check('fsc-1 SPLIT: the importance weights are KNOBS (mission_context takes them)', w['importance_weights']['safety'] == 9.0 and all(p['weight'] == 1.0 for p in w['purposes']))

    def prices():
        from cmod.custom import fsc_prices as PR
        offers = {'offers': [
            {'part_class': 'widget', 'condition': 'new', 'channel': 'online', 'unit_price': 10.0, 'currency': 'USD', 'vendor': 'A', 'cited_at': '2026-10-18', 'confidence': 'page-read', 'url': 'u1'},
            {'part_class': 'widget', 'condition': 'used', 'channel': 'online', 'unit_price': 4.0, 'currency': 'USD', 'vendor': 'B', 'cited_at': '2026-10-18', 'confidence': 'search-snippet', 'url': 'u2'},
            {'part_class': 'widget', 'condition': 'new', 'channel': 'local', 'unit_price': 7.0, 'currency': 'USD', 'vendor': 'Chain', 'cited_at': '2026-10-18', 'confidence': 'search-snippet', 'url': 'u3'}], 'gaps': []}
        d = tempfile.mkdtemp()
        path = os.path.join(d, 'offers.json')
        json.dump(offers, open(path, 'w'))
        pick = lambda **k: PR.cheapest('widget', k or None, path)   # noqa: E731
        check('fsc-1 PRICES (D-fsc-2): the cheapest offer the profile accepts wins - default accepts used and local (4.00 used), accept_used=false -> 7.00 local, neither -> 10.00 new online',
              pick()['unit_price'] == 4.0 and pick(accept_used=False)['unit_price'] == 7.0 and pick(accept_used=False, accept_local=False)['unit_price'] == 10.0)
        pp = PR.price_parts(['widget', 'gadget'], {'accept_used': False}, path)
        check('fsc-1 PRICES: the offer used is NAMED in the basis with vendor, condition/channel, cited date and the evidence strength (a search snippet says it is weaker); a part class with no offer is scored at the stated median stand-in, not zero',
              pp['kind'] == 'stand-in' and 'Chain' in pp['basis'] and 'search snippet' in pp['basis'] and 'gadget' in pp['missing'] and pp['total'] == 15.5 and 'stand-in' in pp['basis'], pp['basis'][:300])
        empty = os.path.join(d, 'none.json')
        e = PR.price_parts(['widget'], None, empty)
        check('fsc-1 PRICES: with no offers file at all the money is UNDETERMINED (total None, kind stand-in) and says so', e['total'] is None and e['kind'] == 'stand-in' and 'undetermined' in e['basis'])
        real = PR.load()
        check('fsc-1 PRICES: the committed offers file loads (%d offers) from board/custom/price_offers (NOT initialData, which is auto-seeded into a class at boot); every offer has a unit_price, url and cited_at' % len(real['offers']),
              real['present'] and len(real['offers']) >= 80 and 'initialData' not in real['path'] and all(o.get('url') and o.get('cited_at') for o in real['offers']))
        b = built()
        bom = b['records'][0]['values']['bom-cost']
        check('fsc-1 PRICES: bom-cost INCLUDES the board (an Arduino Uno R3 offer is in the basis) and cost-to-build-now does not (the board is already on the bench)',
              'Arduino Uno R3 (board)' in bom['basis'] and 'Arduino Uno R3' not in b['records'][0]['values']['cost-to-build-now']['basis'].split('|')[0], bom['basis'][:200])
        miss = next(r for r in b['records'] if r['candidate']['parts_missing'])
        check('fsc-1 PRICES: a plan that needs a part the bench lacks has a cost-to-build-now above zero and above a buildable plan\'s', miss['values']['cost-to-build-now']['value'] > b['records'][0]['values']['cost-to-build-now']['value'], miss['values']['cost-to-build-now'])
        from cmod.custom import fsc_score as S
        from cmod.custom import fsc_profiles as P
        prof = P.all_profiles()['fsc-cheapest']
        yes = S.score_profile(b['records'][:20], prof, b['ctx'])
        no = S.score_profile(b['records'][:20], dict(prof, knobs=dict(prof['knobs'], accept_used=False, accept_local=False)), b['ctx'])
        a0 = next(r['basis'] for r in yes['scores'][b['records'][0]['id']]['rows'])
        a1 = next(r['basis'] for r in no['scores'][b['records'][0]['id']]['rows'])
        check('fsc-1 PRICES: the money terms are recomputed under the PROFILE\'s own accept_used / accept_local knobs (the breakdown names the accepted offers)', a0 != a1 and 'accept_used=False' in a1 and 'accept_used=True' in a0)

    def rows_written():
        from cmod.custom import fsc_store as ST
        from cmod.custom.selftest_purpose import _manager
        b = built()
        mgr = _manager()
        n1 = ST.write(mgr, b, 5)
        n2 = ST.write(mgr, b, 5)
        tbl = lambda c: list(mgr.objectTables.get(c, {}).values())   # noqa: E731
        ctxs = {o.name: o.context_type for o in tbl('ScoreContext')}
        check('fsc-1 ROWS: the writer upserts ScoreContext rows hardware:arduino-uno-r3 (type hardware) and purpose:<name> (type purpose), ScoreSubject rows msol:<mission>:<id>, and one ContextualizedValue per term x context',
              ctxs.get('hardware:' + UNO) == 'hardware' and ctxs.get('purpose:ensure-button-controls-light') == 'purpose' and len(tbl('ScoreSubject')) == 5 and len(tbl('ContextualizedValue')) == n1['ContextualizedValue'] > 200, (n1, ctxs))
        check('fsc-1 ROWS: writing twice adds nothing (upsert by name): %d values both times' % n2['ContextualizedValue'], n1 == n2 and len(tbl('ContextualizedValue')) == n2['ContextualizedValue'])
        cv = tbl('ContextualizedValue')[0]
        check('fsc-1 ROWS: a value row carries the kind in `source` (fsc:<kind>) and its BASIS in `notes`', cv.source.startswith('fsc:') and cv.notes and json.loads(cv.context_names_json)[0].partition(':')[0] in ('hardware', 'purpose'), (cv.source, cv.context_names_json))

    def stock_engine_agrees():
        from scoring.custom.scoring_engine import score_concept
        from cmod.custom import fsc_profiles as P
        from cmod.custom import fsc_score as S
        from cmod.custom import fsc_store as ST
        b = built()
        row = P._row('probe', 'Probe', 'engine equality probe', [P._e('mission-cycle', 0.5), P._e('pins-free', 0.3), P._e('flash-free', 0.2)])
        engine_row = dict(row, required_context_names_json=json.dumps(['hardware:' + UNO]))
        mgr = ST.engine_tables(b, [engine_row])
        eng = score_concept(mgr, 'probe')
        mine = S.score_profile(b['records'], P.parse(row), b['ctx'])
        diffs = [abs(s['initialScore'] - mine['scores'][s['subject'].split(':')[-1]]['raw']) for s in eng['subjects']]
        check('fsc-1 ENGINE: the STOCK scoring engine (scoring.custom.scoring_engine.score_concept) over the written rows gives the same weighted score as ours for %d solutions (max difference %.2g) - the pipeline is reused, not copied' % (len(diffs), max(diffs)),
              eng['ok'] and len(diffs) == len(b['records']) and max(diffs) < 2e-6 and not any(s['termsMissing'] for s in eng['subjects']), (eng.get('error'), max(diffs) if diffs else None))

    def reproduction():
        from cmod.custom import fsc_profiles as P
        from cmod.custom import fsc_score as S
        from cmod.custom import solve as SV
        b = built()
        recs = b['records']
        ids = {r['id'] for r in recs}
        sol_min = [c['id'] for c in b_ranked(b, 'minimum-resources') if c['id'] in ids]
        profs = P.all_profiles()
        mr = S.score_profile(recs, profs['minimum-resources'], b['ctx'], 'sol-0-compatible')
        check('fsc-1 REPRODUCE (sol-0): the `minimum-resources` profile in the stated sol-0-compatible mode orders ALL %d non-failed distinct plans exactly as sol-0 solve does (same objective, same rank key)' % len(sol_min), mr['order'] == sol_min, [(a, c) for a, c in zip(mr['order'], sol_min) if a != c][:3])
        res = SV.solve(LIGHT, boards=[UNO], objective='fastest-cycle')
        rk = {c['id']: c['rank'] for c in res['_ranked']}
        sol_fast = sorted(ids, key=lambda i: rk[i])
        tie = {i: rk[i] for i in ids}
        fc = S.score_profile(recs, profs['fastest-cycle'], b['ctx'], 'sol-0-compatible', tie_rank=tie)
        check('fsc-1 REPRODUCE (sol-0): the one-term `fastest-cycle` profile (sol-0-compatible: plans that need a part the bench lacks rank after every buildable one, as sol-0 does) orders all %d plans exactly as `solve --objective fastest-cycle`' % len(sol_fast),
              fc['order'] == sol_fast, [(a, c) for a, c in zip(fc['order'], sol_fast) if a != c][:3])
        comp = S.score_profile(recs, profs['fastest-cycle'], b['ctx'], 'competitive', tie_rank=tie)
        byc = {r['id']: r['candidate']['parts_missing'] for r in recs}
        for grp, label in ((False, 'buildable with the bench'), (True, 'needing a part')):
            sub = [i for i in sol_fast if bool(byc[i]) == grp]
            got = [i for i in comp['order'] if bool(byc[i]) == grp]
            check('fsc-1 REPRODUCE (competitive): `fastest-cycle` (one term, default competitive normalization) orders the %d plans %s identically to sol-0' % (len(sub), label), got == sub)
        inter = sum(1 for a, c in zip(comp['order'], sol_fast) if a != c)
        mrc = S.score_profile(recs, profs['minimum-resources'], b['ctx'], 'competitive')
        moved = [(i, sol_min.index(i) + 1, mrc['order'].index(i) + 1) for i in sol_min if sol_min.index(i) != mrc['order'].index(i)]
        big = max(moved, key=lambda t: abs(t[1] - t[2])) if moved else None
        why = ''
        if big:
            a, bb = mr['scores'][big[0]], mrc['scores'][big[0]]
            ra = {r['term']: r['points'] for r in a['rows']}
            rb = {r['term']: r['points'] for r in bb['rows']}
            t = max(ra, key=lambda k: abs(ra[k] / max(1e-9, sum(ra.values())) - rb[k] / max(1e-9, sum(rb.values()))))
            why = 'largest mover %s #%d -> #%d, driven by %s (%.1f%% of its sol-0 points vs %.1f%% under competitive min-max, where each term spans only the observed range)' % (big[0], big[1], big[2], t, 100 * ra[t] / max(1e-9, sum(ra.values())), 100 * rb[t] / max(1e-9, sum(rb.values())))
        print('       REPORT: competitive `fastest-cycle` vs sol-0 differs in %d of %d positions (the bench gate interleaves); competitive `minimum-resources` vs sol-0: %d of %d plans change rank; %s' % (inter, len(sol_fast), len(moved), len(sol_min), why))
        check('fsc-1 REPRODUCE: under competitive normalization the rank differences of `minimum-resources` are REPORTED (not forced equal): %d plans move; top scorer sol-0 %s -> competitive %s' % (len(moved), sol_min[0], mrc['order'][0]), isinstance(moved, list), moved[:3])

    # ------------------------------------------------------------------ fsc-2
    def profiles_seeded():
        from cmod.custom import fsc_profiles as P
        from cmod.custom import fsc_terms as T
        pr = P.all_profiles()
        wt = lambda n: {(e['term'], e.get('purpose', '')): e['weight'] for e in pr[n]['entries']}   # noqa: E731
        check('fsc-2 PROFILES: the seven sample profiles (Fastest, Cheapest, Build it today, Balanced, Battery, Room to grow, Most trustworthy) with the plan weights, plus today\'s two objectives and one hardware profile',
              {pr[n]['display_name'] for n in pr} >= {'Fastest', 'Cheapest', 'Build it today', 'Balanced', 'Battery', 'Room to grow', 'Most trustworthy'} and len(pr) == 10
              and wt('fsc-battery')[('active-current', '')] == 0.5 and wt('fsc-battery')[('sleep-capable', '')] == 0.4 and abs(sum(wt('fsc-balanced').values()) - 1.0) < 1e-9 and wt('fsc-build-it-today')[('cost-to-build-now', '')] == 0.5
              and abs(sum(wt('fsc-most-trustworthy').values()) - 1.0) < 1e-9, sorted(pr))
        check('fsc-2 PROFILES: every term a profile weights is a known term; every profile is competitive by default and seeded ones are marked seeded (copy before editing)',
              all(e['term'] in T.TERM_NAMES for p in pr.values() for e in p['entries']) and all(p['knobs']['normalization'] == 'competitive' for p in pr.values()) and all(p['seeded'] for p in pr.values()))
        h = pr['fsc-uno-r3-per-purpose']
        pw = {}
        for e in h['entries']:
            pw.setdefault(e['purpose'], {})[e['term']] = e['weight']
        check('fsc-2 PROFILES: the hardware profile is unique to arduino-uno-r3 and weights latency vs cost PER Purpose as in plan section 5 (0.8/0.2, 0.5/0.5, 0.2/0.8)',
              h['hardware'] == UNO and pw['ensure-button-controls-light'] == {'worst-purpose-latency': 0.8, 'bom-cost': 0.2} and pw['ensure-polari-can-control-light'] == {'worst-purpose-latency': 0.5, 'bom-cost': 0.5}
              and pw['ensure-polari-observes-hardware-state'] == {'worst-purpose-latency': 0.2, 'bom-cost': 0.8}, pw)

    def scoring_is_competitive():
        from cmod.custom import fsc_profiles as P
        from cmod.custom import fsc_score as S
        b = built()
        ok, detail = True, []
        for n, p in P.all_profiles().items():
            res = S.score_profile(b['records'], p, b['ctx'])
            sc = [s['score'] for s in res['scores'].values()]
            top_ok = max(sc) == 100.0 and (min(sc) == 0.0 or len(set(round(x, 9) for x in sc)) == 1)
            ok = ok and top_ok
            detail.append((n, min(sc), max(sc)))
        check('fsc-2 COMPETITIVE: in every profile column the top scorer is exactly 100 and the bottom exactly 0 (all tied -> all 100); the raw weighted value is kept', ok, detail)
        p = P.all_profiles()['fsc-room-to-grow']
        res = S.score_profile(b['records'], p, b['ctx'])
        i = res['order'][0]
        rows = res['scores'][i]['rows']
        check('fsc-2 COMPETITIVE: per term the best compared solution gets 100 and the worst 0 (no chip limits as bounds): the winner\'s term rows are 0..100 and say "competitive min-max over %d solutions"' % len(b['records']),
              all(0 <= r['normalized'] <= 100 for r in rows) and any('competitive min-max over %d' % len(b['records']) in r['normalization'] or 'no competition' in r['normalization'] for r in rows))
        one = S.score_profile(b['records'][:1], p, b['ctx'])
        check('fsc-2 COMPETITIVE: a set of ONE scores 100 with the basis "no competition on this term"', one['scores'][b['records'][0]['id']]['score'] == 100.0 and all('no competition' in r['normalization'] for r in one['scores'][b['records'][0]['id']]['rows']))
        tied = [dict(r, values={k: dict(v, value=1.0) for k, v in r['values'].items()}) for r in b['records'][:4]]
        tr = S.score_profile(tied, P.all_profiles()['fsc-fastest'], b['ctx'])
        check('fsc-2 COMPETITIVE: every solution tied on a term -> 100 for all, "no competition on this term"', {s['score'] for s in tr['scores'].values()} == {100.0} and 'ties' in next(iter(tr['scores'].values()))['rows'][0]['normalization'])
        pu = S.score_profile(b['records'], P.all_profiles()['fsc-uno-r3-per-purpose'], b['ctx'])
        i = pu['order'][3]
        s = pu['scores'][i]
        rows = s['rows']
        check('fsc-2 PER-PURPOSE: Score = sum_p alpha_p x (sum_t w x norm / sum w): the breakdown\'s points add up to 100 x the raw weighted value (%.4f), over %d term rows in %d Purpose contexts' % (s['raw'], len(rows), len(s['groups'])),
              abs(sum(r['points'] for r in rows) - 100 * s['raw']) < 0.01 and len(s['groups']) == 3 and all(r['context'].startswith('purpose:') for r in rows) and abs(sum(g['alpha'] for g in s['groups']) - 1.0) < 1e-4, sum(r['points'] for r in rows))
        fb = S.score_profile(b['records'], P.all_profiles()['fsc-cheapest'], b['ctx'])
        check('fsc-2 CHEAPEST: with cited prices for the parts (the real offers) bom-cost is used directly - no fallback', not fb['notes'])

    def cheapest_falls_back():
        from cmod.custom import fsc_prices as PR
        from cmod.custom import fsc_profiles as P
        from cmod.custom import fsc_run as R
        from cmod.custom import fsc_score as S
        d = tempfile.mkdtemp()
        path = os.path.join(d, 'none.json')
        os.environ['POLARI_PRICE_OFFERS'] = path
        try:
            nb = R.build(LIGHT, None, [UNO])
            r = S.score_profile(nb['records'], P.all_profiles()['fsc-cheapest'], nb['ctx'])
            row = next(iter(r['scores'].values()))['rows']
            check('fsc-2 CHEAPEST: with NO cited price at all `Cheapest` falls back to cost-to-build-now + parts-to-acquire and SAYS SO (profile note + the rows name what they stand in for)',
                  r['notes'] and 'stands in' in r['notes'][0] and {x['term'] for x in row} == {'cost-to-build-now', 'parts-to-acquire'} and all(x['fallback_for'] == 'bom-cost' for x in row)
                  and 'bom-cost' not in nb['records'][0]['values'], r['notes'])
        finally:
            del os.environ['POLARI_PRICE_OFFERS']
        del PR

    def doors():
        import falcon
        from falcon import testing
        from cmod.cmod_fsc_api import FscAPI
        from cmod.cmod_solve_api import SolveAPI
        from cmod.cmod_mission_api import MissionAPI
        from cmod.custom.selftest_purpose import _manager
        mgr = _manager()
        order = (FscAPI, SolveAPI, MissionAPI)
        for first in (True, False):
            app = falcon.App()
            ps = SimpleNamespace(falconServer=app, manager=mgr, idList=[])
            try:
                for cls in (order if first else tuple(reversed(order))):
                    cls(polServer=ps, manager=mgr)
                clash = None
            except Exception as ex:   # noqa: BLE001
                clash = repr(ex)
            check('fsc-2 DOORS: the firmware-score doors ADD on ONE real falcon.App beside the solve and Mission doors (%s first)' % ('mine' if first else 'theirs'), clash is None, clash)
        c = testing.TestClient(app)
        q = {'mission': LIGHT, 'board': UNO, 'scope': 'all'}      # smp-0: the default scope is now the curated sample (tested in selftest_fsc_sample); these fsc-2 checks are about the whole set
        g = c.simulate_get('/api/firmware-scores', params=dict(q, profile='fsc-fastest'))
        rows = [r for r in g.json['rows'] if r['state'] != 'failed']
        check('fsc-2 DOOR scores: rows sorted TOP -> BOTTOM by the profile, with rank, finished|plan, score, and the deciding terms (the 2-3 largest weighted contributions); the top row scores 100',
              g.status_code == 200 and rows[0]['rank'] == 1 and rows[0]['score'] == 100.0 and [r['rank'] for r in rows] == list(range(1, len(rows) + 1)) and all(a['score'] >= b['score'] for a, b in zip(rows, rows[1:]))
              and all(r['state'] in ('finished', 'plan') for r in rows) and rows[0]['deciding_terms'] and g.json['count'] == len(g.json['rows']), (g.status_code, g.text[:200]))
        allp = c.simulate_get('/api/firmware-scores', params=q)
        check('fsc-2 DOOR scores: with no profile asked every profile is scored (%d) and each row carries its score and rank per profile' % len(allp.json['profiles']),
              allp.status_code == 200 and len(allp.json['profiles']) == 10 and all(len(r['scores']) == 10 for r in allp.json['rows'] if r['state'] != 'failed'))
        cfail_all = [r for r in g.json['rows'] if r['state'] == 'failed' and r.get('failed_purpose')]
        cfail = [r for r in cfail_all if r['solution'] != 'uno-light-slow-loop']      # smp-1: the sample failure F2 is a safety-deadline row of its own (tested in selftest_fsc_sample)
        check('fsc-0b DOOR scores: GET /api/firmware-scores?mission=uno-light-mission lists the four built light configs as FAILED rows (name, Purpose failed, why, no score) and never ranks them: %s' % sorted(r['solution'] for r in cfail),
              sorted(r['solution'] for r in cfail) == ['uno-light', 'uno-light-analog', 'uno-light-pcint', 'uno-light-v2'] and all(r['score'] is None and r['rank'] is None and 'sense-led-line' in r['reason']
                                                                                                                              and r['failed_purpose'] == 'ensure-button-controls-light, ensure-polari-can-control-light, ensure-polari-observes-hardware-state' for r in cfail)
              and {f['config'] for f in g.json['failures'] if f['kind'] == 'purpose-unfulfilled'} == {r['solution'] for r in cfail}, [r['solution'] for r in cfail_all])
        t = c.simulate_get('/api/firmware-scores/top', params=q)
        trow = t.json['rows'][0]
        check('fsc-2 DOOR top (the main tab): one row per profile {profile, profile_title, top_solution, score 100, runner_up, runner_up_score, compared_set, failed_count}',
              t.status_code == 200 and t.json['count'] == 10 and all(r['score'] == 100.0 and r['runner_up'] and r['compared_set'] and r['failed_count'] == 5 and r['profile_title'] for r in t.json['rows'])
              and {'profile', 'profile_title', 'top_solution', 'score', 'runner_up', 'runner_up_score', 'compared_set', 'failed_count'} <= set(trow), trow)
        top1 = rows[0]
        bd = c.simulate_get('/api/firmware-scores/breakdown', params=dict(q, solution=top1['solution'], profile='fsc-fastest'))
        tr = bd.json['terms'][0] if bd.status_code == 200 else {}
        check('fsc-2 DOOR breakdown: term rows {term, value, kind, normalized, weight, points, basis} for one solution and profile, with its score, rank, raw weighted value and the compared set named',
              bd.status_code == 200 and bd.json['score'] == 100.0 and bd.json['rank'] == 1 and bd.json['set'] and {'term', 'value', 'kind', 'normalized', 'weight', 'points', 'basis'} <= set(tr), bd.text[:200])
        bf = c.simulate_get('/api/firmware-scores/breakdown', params=dict(q, solution='uno-light-sense-poll', profile='fsc-balanced'))
        check('fsc-2 DOOR breakdown: a built config name finds its solution (uno-light-sense-poll) and the breakdown names the offers used', bf.status_code == 200 and bf.json['label'] and any('offer' in r['basis'] for r in bf.json['terms'] if r['term'] == 'bom-cost'), bf.text[:200])
        bad = [c.simulate_get('/api/firmware-scores', params={'profile': 'nope'}).status_code, c.simulate_get('/api/firmware-scores', params={'nope': '1'}).status_code,
               c.simulate_get('/api/firmware-scores', params={'mission': 'nope'}).status_code, c.simulate_get('/api/firmware-scores', params={'scope': 'nope'}).status_code,
               c.simulate_get('/api/firmware-scores/breakdown', params=dict(q, solution='nope', profile='fsc-fastest')).status_code, c.simulate_get('/api/firmware-scores/breakdown', params=q).status_code]
        check('fsc-2 DOORS: an unknown profile / parameter / scope is 422 naming what is known, an unknown Mission or solution is 404, a breakdown without ?solution & ?profile is 422', bad == [422, 422, 404, 422, 404, 422], bad)
        msg = c.simulate_get('/api/firmware-scores', params={'profile': 'nope'}).json['error']
        check('fsc-2 DOORS: the 422 for an unknown profile NAMES the known ones', 'fsc-fastest' in msg and 'minimum-resources' in msg, msg[:120])
        pf = c.simulate_get('/api/firmware-score-profiles')
        check('fsc-2 DOOR profiles: GET lists every profile with its terms, weights, hardware and whether it is seeded / editable', pf.status_code == 200 and pf.json['count'] == 10 and all(r['seeded'] and not r['editable'] for r in pf.json['rows']) and 'mission-cycle' in pf.json['terms'])
        post = lambda body: c.simulate_post('/api/firmware-score-profiles', body=json.dumps(body))   # noqa: E731
        seeded = post({'name': 'fsc-fastest', 'weights': {'wires': 1}})
        check('fsc-2 DOOR profiles: a SEEDED profile is never edited in place - 409 telling the person to copy it', seeded.status_code == 409 and 'copy_of' in seeded.json['error'] and 'fsc-fastest' in seeded.json['error'], seeded.text[:200])
        cp = post({'name': 'my-fast-and-cheap', 'copy_of': 'fsc-fastest', 'display_name': 'Fast and cheap', 'weights': {'bom-cost': 1.0}})
        check('fsc-2 DOOR profiles: POST copy_of + weights creates the person\'s own profile (201), the seeded one stays as it was', cp.status_code == 201 and cp.json['created'] and {t['term'] for t in cp.json['terms']} == {'mission-cycle', 'bom-cost'} and not cp.json['seeded'] and cp.json['editable'], cp.text[:200])
        after = {r['name']: r for r in c.simulate_get('/api/firmware-score-profiles').json['rows']}
        check('fsc-2 DOOR profiles: the seeded Fastest profile is untouched after the copy was edited (still mission-cycle 1.0 only)', [(t['term'], t['weight']) for t in after['fsc-fastest']['terms']] == [('mission-cycle', 1.0)] and 'my-fast-and-cheap' in after)
        up = post({'name': 'my-fast-and-cheap', 'weights': {'mission-cycle': 0.0, 'wires': 2}})
        check('fsc-2 DOOR profiles: POST on the person\'s OWN profile sets weights (200; a weight of 0 removes the term)', up.status_code == 200 and not up.json['created'] and {t['term']: t['weight'] for t in up.json['terms']} == {'bom-cost': 1.0, 'wires': 2.0}, up.text[:200])
        pw = post({'name': 'per-purpose-mine', 'copy_of': 'fsc-uno-r3-per-purpose', 'purpose_weights': {'ensure-button-controls-light': {'worst-purpose-latency': 1.0}}})
        check('fsc-2 DOOR profiles: purpose_weights set a per-Purpose weight on a copy of the hardware profile', pw.status_code == 201 and any(t.get('purpose') == 'ensure-button-controls-light' and t['term'] == 'worst-purpose-latency' and t['weight'] == 1.0 for t in pw.json['terms']), pw.text[:200])
        refused = [post({'name': 'x-one', 'weights': {'no-such-term': 1}}), post({'name': 'x-two', 'weights': {'wires': 1}, 'bogus': 1}), post({'name': 'x-three', 'weights': {'wires': 1}, 'knobs': {'zzz': 1}}),
                   post({'name': 'x-four', 'weights': {'wires': 1}, 'purpose_weights': {'no-such-purpose': {'wires': 1}}}), post({'name': 'BAD NAME', 'weights': {'wires': 1}}), post({'name': 'x-five', 'copy_of': 'nope'}), post({'name': 'x-six'})]
        check('fsc-2 DOORS: an unknown term / body key / knob / Purpose, a bad name, an unknown copy_of, or no weights at all is refused 422 naming what is known', [r.status_code for r in refused] == [422] * 7
              and 'wires' in refused[0].json['error'] and 'weights' in refused[1].json['error'] and 'accept_used' in refused[2].json['error'] and 'ensure-button-controls-light' in refused[3].json['error'], [r.text[:80] for r in refused])
        mine = c.simulate_get('/api/firmware-scores', params=dict(q, profile='my-fast-and-cheap'))
        check('fsc-2 DOORS: the person\'s own profile scores like any other (top 100)', mine.status_code == 200 and mine.json['rows'][0]['score'] == 100.0)
        w = c.simulate_post('/api/firmware-scores/values', body=json.dumps({'mission': LIGHT, 'board': UNO, 'limit': 3}))
        check('fsc-2 DOOR values: POST writes the ScoreContext / ScoreSubject / ContextualizedValue rows (201) and an unknown key is 422', w.status_code == 201 and w.json['written']['ScoreSubject'] == 3 and w.json['written']['ContextualizedValue'] > 100
              and c.simulate_post('/api/firmware-scores/values', body=json.dumps({'nope': 1})).status_code == 422, w.text[:200])

    def cli():
        from cmod.custom import fsc_cli as CLI

        def run(*argv):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = CLI.main(list(argv))
            return rc, buf.getvalue()
        rc, out = run('scores', '--mission', LIGHT, '--board', UNO, '--scope', 'all', '--profile', 'fsc-fastest', '--limit', '3')
        check('fsc-2 CLI: `scores --profile fsc-fastest --limit 3` prints the compared set, the top three with state and score, and the deciding terms', rc == 0 and 'Firmware scores' in out and '#1' in out and '100.0' in out and 'mission-cycle' in out.lower() or 'Mission cycle' in out, out[:300])
        rc, out = run('scores', '--mission', LIGHT, '--board', UNO, '--scope', 'all', '--top')
        check('fsc-2 CLI: `scores --top` prints the top scorer of each profile', rc == 0 and 'Top scorer of each profile' in out and 'Fastest' in out and 'Cheapest' in out, out[:200])
        rc, out = run('scores', '--mission', LIGHT, '--board', UNO, '--scope', 'all', '--profile', 'fsc-fastest', '--json')
        j = json.loads(out)
        check('fsc-2 CLI: --json is valid JSON with rows and the set', rc == 0 and j['ok'] and j['rows'] and j['set'])
        rc, out = run('profile', 'show', 'fsc-battery')
        check('fsc-2 CLI: `profile show <name>` prints its description, normalization and weights (and that it is seeded: copy before editing)', rc == 0 and 'active-current' in out and 'seeded' in out and 'competitive' in out, out[:200])
        rc, out = run('profile', 'create', 'mine', '--copy-of', 'fsc-fastest', '--weight', 'wires=1')
        check('fsc-2 CLI: `profile create` with no server REFUSES (exit 3) and prints the equivalent door call', rc == 3 and 'POST /api/firmware-score-profiles' in out and 'copy_of' in out, out[:200])
        rc, out = run('score-values', 'refresh', '--mission', LIGHT)
        check('fsc-2 CLI: `score-values refresh` with no server refuses (exit 3) and prints the equivalent door call', rc == 3 and 'POST /api/firmware-scores/values' in out)
        rc, out = run('scores', '--mission', 'nope')
        check('fsc-2 CLI: an unknown Mission is refused (exit 3, [REFUSED])', rc == 3 and '[REFUSED]' in out)

    def failure_end_to_end():
        """The failure rule through the REAL solver and doors: tighten one Purpose's deadline to 40 ms (a 10 ms budget after the 30 ms debounce) so every POLLED button plan misses it."""
        import falcon
        from falcon import testing
        from cmod.cmod_fsc_api import FscAPI
        from cmod.custom import fsc_run as R
        from cmod.custom import mission_derived as MD
        from cmod.custom import solve_doors as SD
        orig = MD.capability
        res = {}
        for flag in (False, True):
            def tight(name, manager=None, flag=flag):
                cap = orig(name, manager)
                if cap and name == 'ensure-button-controls-light':
                    spec = json.loads(cap['criteria_json'])
                    for c in spec['criteria']:
                        if c['key'] == 'max_latency_ms':
                            c['value'] = 40
                            c['safety_critical'] = flag
                    cap = dict(cap, criteria_json=json.dumps(spec))
                return cap
            MD.capability = tight
            SD._CACHE.clear()
            R._CACHE.clear()
            R._CTX.clear()
            try:
                res[flag] = R.build(LIGHT, None, [UNO])
                if flag:
                    app = falcon.App()
                    FscAPI(polServer=SimpleNamespace(falconServer=app, manager=None, idList=[]), manager=None)
                    c = testing.TestClient(app)
                    q = {'mission': LIGHT, 'board': UNO, 'scope': 'all'}
                    g = c.simulate_get('/api/firmware-scores', params=dict(q, profile='fsc-fastest'))
                    bd = c.simulate_get('/api/firmware-scores/breakdown', params=dict(q, solution=res[flag]['failures'][0]['solution'], profile='fsc-fastest'))
                    tp = c.simulate_get('/api/firmware-scores/top', params=q)
            finally:
                MD.capability = orig
                SD._CACHE.clear()
                R._CACHE.clear()
                R._CTX.clear()
        unf, fl = res[False], res[True]
        check('fsc-0 FAIL RULE end to end: with the deadline tightened but NOT flagged, nothing fails - the polled plans are scored by closeness (deadline-fit below 100) and the miss is listed',
              [f for f in unf['failures'] if (f['kind'] != 'purpose-unfulfilled' and not f.get('sample'))] == [] and any(r['unflagged_deadline_misses'] for r in unf['records'])
              and min(r['values']['deadline-fit']['value'] for r in unf['records']) < 100.0 and max(r['values']['deadline-fit']['value'] for r in unf['records']) == 100.0, unf['counts'])
        check('fsc-0 FAIL RULE end to end: the SAME deadline flagged safety_critical -> the plans that miss it FAIL (%d), each naming the Purpose and the reason; the survivors (%d) all meet it' % (len([f for f in fl['failures'] if (f['kind'] != 'purpose-unfulfilled' and not f.get('sample'))]), len(fl['records'])),
              [f for f in fl['failures'] if (f['kind'] != 'purpose-unfulfilled' and not f.get('sample'))] and all(f['purpose'] == 'ensure-button-controls-light' and 'safety-critical' in f['reason'] for f in fl['failures'] if (f['kind'] != 'purpose-unfulfilled' and not f.get('sample')))
              and all(r['values']['deadline-fit']['value'] == 100.0 for r in fl['records']) and len([f for f in fl['failures'] if (f['kind'] != 'purpose-unfulfilled' and not f.get('sample'))]) + len(fl['records']) == unf['counts']['distinct_plans'], fl['counts'])
        rows = [r for r in g.json['rows'] if r['state'] != 'failed']
        failed = [r for r in g.json['rows'] if r['state'] == 'failed']
        check('fsc-2 FAILURES (door): failed solutions are listed after the ranked ones with state `failed`, the Purpose and the reason, NO score and NO rank, and never enter the compared set (%d ranked, %d failed)' % (len(rows), len(failed)),
              g.status_code == 200 and failed and all(r['score'] is None and r['rank'] is None and r['failed_purpose'] and r['reason'] for r in failed) and len(rows) == len(fl['records']) and g.json['counts']['failed'] == len(failed))
        check('fsc-2 FAILURES (door): the breakdown of a failed solution says failed with the Purpose and reason and a null score, and the top tab counts the failures',
              bd.json['state'] == 'failed' and bd.json['score'] is None and bd.json['reason'] and tp.json['rows'][0]['failed_count'] == len(failed))

    def manifest():
        m = json.load(open(os.path.join(os.path.dirname(__file__), 'polari-app.json')))
        f = m['files']
        want = {'api': ['cmod_fsc_api'], 'selftests': ['cmod_fsc_selftest'],
                'custom': ['custom/fsc_%s' % n for n in ('context', 'doors', 'failure', 'labels', 'link', 'prices', 'profiles', 'run', 'score', 'store', 'terms', 'values', 'cli', 'sample')]}
        got = {k: [n for n in names if n not in f.get(k, [])] for k, names in want.items()}
        check('fsc MANIFEST: polari-app.json lists every new file (api, selftest, thirteen custom modules), requires the scoring module, and the class FscAPI', not any(got.values()) and 'FscAPI' in m['classes'] and 'scoring' in m['requires']['modules'], got)
        check('...each listed file exists on disk', all(os.path.isfile(os.path.join(os.path.dirname(__file__), n + '.py')) for n in sum(want.values(), [])))
        from cmod.cmod_endpoints import construct_cmod_endpoints
        check('fsc: construct_cmod_endpoints builds FscAPI (api.fsc)', 'FscAPI' in open(os.path.join(os.path.dirname(__file__), 'cmod_endpoints.py')).read() and construct_cmod_endpoints is not None)

    from cmod.custom.selftest_fsc_prove import prove_parts      # fsc-6: the per-config proof mechanism (the twin stubbed)
    from cmod.custom.selftest_fsc_sample import sample_parts    # smp-0/1: the curated sample, its scope, S5's hook and F2's measured safety failure
    return (terms_seeded, safety_flag_and_failures, link_and_finished, value_writer, splits, prices, rows_written, stock_engine_agrees, reproduction, profiles_seeded,
            scoring_is_competitive, cheapest_falls_back, doors, cli, manifest, failure_end_to_end, *prove_parts(check), *sample_parts(check))


def b_ranked(b, objective):
    """sol-0's own order of the distinct plans in `b` (its ranked candidates, filtered to the representatives)."""
    from cmod.custom import solve_doors as SD
    res = SD.compute(b['mission'], [UNO], None, None, {}, None)
    return res['_ranked']


def main():
    passed = total = 0
    failures = []

    def check(label, cond, detail=None):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
        else:
            failures.append(label)
        print('  [%s] %s%s' % ('ok' if cond else 'FAIL', label, '' if cond else '  <- %s' % (str(detail)[:300],)))
    print('cmod fsc selftest (fsc-0/1/2, fsc-6, smp-0/1)')
    for part in fsc_parts(check):
        print('-- %s' % part.__name__)
        part()
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
