"""
@module cmod.custom.solve_report

sol-0: the OUTPUT of a run, in plain words (no raw JSON on screens): the ranking, the TRADE STUDY (all candidates side by side), the SCORE CARD (the ranking with the deciding
differences), the chosen assignment with the reason for every pin, the pruned-branch log, and "Designed for" / "Also runs on" (SYSTEM_HIERARCHY_TERMINOLOGY.md section 8).

Ranking (deterministic): a candidate that is COMPLETE, placed, meets every Purpose bound and is buildable with what is on the bench first; then one needing a part the bench lacks
(named - never called available); then one that misses a Purpose bound (listed, advised against); then partial (a lower-importance Purpose lost its pins); then placement undetermined. Inside a class: the objective's score,
then the other objective's, then the number of open ladder rungs, then a fixed order.
"""
import json

CLASS_WORDS = {0: 'buildable on the bench', 1: 'needs a part the bench does not have', 2: 'does not meet a Purpose bound (latency)', 3: 'some Purposes lose their pins', 4: 'pins cannot be placed (hardware not modelled)'}


def rank(engine):
    hw_order = {(h['board'], h['package']): i for i, h in enumerate(engine.hardware)}
    tier_order = {t: i for i, t in enumerate(('bare-c', 'freertos', 'zephyr'))}
    from cmod.custom.solve_engine import rank_key
    out = sorted(engine.candidates, key=lambda c: rank_key(c, hw_order, tier_order))
    for i, c in enumerate(out):
        c['rank'] = i + 1
    return out


def short_hw(c):
    h = c['hardware']
    return '%s / %s' % (h['board'], h['package'] or 'package not modelled')


def label(c):
    return '%s / %s / %s' % (short_hw(c), c['tier'], ', '.join('%s via %s' % (j.replace('-', ' '), r) for j, r in sorted(c['routes'].items(), key=lambda kv: kv[0])))


def pins_text(c):
    if not c['assignment']:
        return 'not placed: pins cannot be worked out on this hardware'
    seen, out = set(), []
    for a in c['assignment']:
        k = (a['role'], a['pin'])
        if k in seen:
            continue
        seen.add(k)
        out.append('%s %s%s' % (a['part'] if a['part'] != a['role'] and a['kind'] in ('spi-sck', 'spi-miso', 'spi-mosi', 'i2c-sda', 'i2c-scl', 'digital-out') and a['job'] != 'drive-led' else a['role'], a['pin'],
                                (' (%s)' % a['function']) if a['function'] != 'GPIO' else ''))
    return '; '.join(out)


def _ms(us):
    return ('%.1f ms' % (us / 1000.0)) if us >= 1000 else ('%.1f us' % us)


def _term(c, key):
    return next(t for t in c['resources']['terms'] if t['key'] == key)


def deciding(c, w):
    """Why c is below the winner w, in plain words (its deciding differences)."""
    if c is w:
        return 'the chosen plan'
    out = []
    if c['rank_class'] != w['rank_class']:
        out.append(CLASS_WORDS[c['rank_class']] + (': ' + ', '.join(p['class'] for p in c['parts_missing']) if c['rank_class'] == 1 else ''))
        if c['rank_class'] == 3:
            out.append('; '.join('%s loses %s' % (', '.join(l['purposes']) or l['role'], l['role']) for l in c['lost']))
    diff = [(j, c['routes'].get(j), w['routes'].get(j)) for j in sorted(set(c['routes']) | set(w['routes'])) if c['routes'].get(j) != w['routes'].get(j)]
    if diff:
        out.append('; '.join('%s: %s instead of %s' % (j.replace('-', ' '), a or 'not placed', b or 'not placed') for j, a, b in diff[:3]))
    if short_hw(c) != short_hw(w):
        out.append('on %s instead of %s' % (short_hw(c), short_hw(w)))
    if c['tier'] != w['tier']:
        out.append('tier %s instead of %s' % (c['tier'], w['tier']))
    if c['rank_class'] < 4 and w['rank_class'] < 4:
        d = c['resource_score'] - w['resource_score']
        terms = sorted(((t['points'] - _term(w, t['key'])['points'], t) for t in c['resources']['terms']), key=lambda x: (-abs(x[0]), x[1]['key']))
        top = [(dp, t) for dp, t in terms if abs(dp) > 0.0005][:2]
        if top:
            out.append('resources %+.3f (%s)' % (d, ', '.join('%s %+.3f' % (t['label'], dp) for dp, t in top)))
        dc = c['cycle_us'] - w['cycle_us']
        if abs(dc) > 0.05:
            out.append('cycle %s %s' % ('+' if dc > 0 else '-', _ms(abs(dc))))
        if c['pins_used'] != w['pins_used'] and not diff:
            out.append('pins %s instead of %s' % (', '.join(c['pins_used']), ', '.join(w['pins_used'])))
    if not out:
        out.append('the same plan; the difference is only in the open ladder rungs (%d vs %d)' % (c['risk_points'], w['risk_points']))
    return '; '.join(x for x in out if x)


def trade_rows(cands, n):
    return [{'rank': c['rank'], 'candidate': label(c), 'hardware': short_hw(c), 'tier': c['tier'], 'routes': c['routes_text'], 'pins': pins_text(c),
             'resources': '%.3f' % c['resource_score'], 'cycle': _ms(c['cycle_us']), 'parts_to_get': ', '.join(p['class'] for p in c['parts_missing']) or 'none',
             'placement': CLASS_WORDS[c['rank_class']], 'open_rungs': c['risk_points'], 'undetermined_costs': c['resources']['undetermined'] + c['cycle']['undetermined'],
             'cycle_basis': cycle_basis_text(c)}
            for c in cands[:n]]


def cycle_basis_text(c):
    """cyc-0: which basis the candidate's cycle used, in plain words ('4 measured on the twin, 2 estimated/counted')."""
    b = (c.get('cycle') or {}).get('bases')
    if not b:
        return 'not stated'
    return '%d measured on the twin, %d estimated/counted%s' % (b['measured'], b['estimated'], (', %d undetermined' % b['undetermined']) if b['undetermined'] else '')


def _twin_key(c):
    return (c['hardware']['board'], c['tier'], tuple(sorted(c['routes'].items())), tuple((a['need'], a['pin']) for a in c['assignment']), c['rank_class'], tuple(l['job'] for l in c['lost']))


def score_card_rows(cands, n, objective):
    """One row per distinct plan: the same plan on another package of the same board is one row that says so (the trade study lists both)."""
    w = cands[0] if cands else None
    rows, seen = [], {}
    for c in cands:
        k = _twin_key(c)
        if k in seen:
            seen[k]['also_on'] = (seen[k]['also_on'] + '; ' if seen[k]['also_on'] else '') + (c['hardware']['package'] or 'package not modelled')
            continue
        if len(rows) >= n:
            continue
        seen[k] = {'rank': c['rank'], 'also_on': '', 'verdict': 'chosen' if c is w else ('runner-up' if c['rank_class'] == w['rank_class'] else CLASS_WORDS[c['rank_class']]),
                     'candidate': label(c), 'score': ('%.3f' % c['primary']) if objective == 'minimum-resources' else _ms(c['primary']),
                     'other_objective': _ms(c['secondary']) if objective == 'minimum-resources' else ('%.3f' % c['secondary']),
                     'risks': '; '.join(r['text'] for r in c['risks'][:3]) or 'none open', 'deciding_difference': deciding(c, w)}
        rows.append(seen[k])
    for r in rows:
        if r['also_on']:
            r['candidate'] += '  [the same plan also on %s]' % r['also_on']
    return rows


def unplaced(engine, w, n=8):
    """Better variants that COULD NOT be placed: the route is cheaper than the chosen one for its job (standalone) but every combination holding it failed - with the reason."""
    if w is None:
        return []
    from cmod.custom import solve_engine as EN
    key = {j: {v['route']: EN._standalone_key(dict(v, _needs_parts=False), engine.objective) for v in vs} for j, vs in engine.variants_all.items()}
    out, seen = [], set()
    for fk, why in sorted(engine.fail_by_key.items(), key=lambda kv: str(kv[0])):
        job = engine.fail_need.get(fk, '')
        route = dict(fk[3]).get(job)
        if not route or route == w['routes'].get(job):
            continue
        if key.get(job, {}).get(route, ()) >= key.get(job, {}).get(w['routes'].get(job), ()):
            continue
        sig = (job, route, why[:80])
        if sig in seen:
            continue
        seen.add(sig)
        out.append({'rank': '-', 'also_on': '', 'verdict': 'could not be placed', 'candidate': '%s / %s / %s via %s' % (fk[0], fk[1] or 'package not modelled', fk[2], '%s: %s' % (job.replace('-', ' '), route)),
                    'score': 'n/a', 'other_objective': 'n/a', 'risks': 'none (not placed)', 'deciding_difference': 'a cheaper route that did not fit: ' + why})
    return out[:n]


def assignment_rows(c):
    if c is None:
        return []
    rows = []
    for a in c['assignment']:
        ref = '; '.join('%s (rung %s: %s)' % (r['pin'], r['rung'], r['why'][:90]) for r in a['refused'][:4])
        rows.append({'need': a['role'] if a['part'] == a['role'] else '%s - %s' % (a['role'], a['part']), 'pin': a['pin'], 'function': a['function'], 'importance': a['importance'],
                     'purposes': ', '.join(a['purposes']), 'why_this_pin': a['why'], 'refused_by_name': ref or 'none', 'open_rungs': ', '.join('%d %s' % (r['rung'], r['verdict']) for r in a['risks']) or 'none'})
    return rows


def pruned_rows(log):
    d = log.as_dict()
    return [{'kind': k, 'count': v['count'], 'where': x['where'], 'reason': x['reason']} for k, v in d['by_kind'].items() for x in v['first']]


def designed_for(w, engine):
    if w is None:
        return None
    return {'hardware': short_hw(w), 'board': w['hardware']['board'], 'package': w['hardware']['package'], 'usb_interfaces': w['hardware']['usb_interfaces'], 'tier': w['tier'],
            'variants': w['routes'], 'pins': pins_text(w), 'objective': engine.objective, 'mission': engine.row['name'],
            'basis': 'the best candidate of this run - the origin context of the Task Plan; written once, never changed (terminology section 8)'}


def also_runs_on(w, cands, engine):
    """Hardware the SAME variant choice also resolves on, each with HOW WE KNOW; and where it does not, with the reason."""
    if w is None:
        return [], []
    same = [c for c in cands if c is not w and c['routes'] == w['routes']]
    ok, no = [], []
    for c in same:
        if c['rank_class'] <= 1 and (short_hw(c), c['tier']) != (short_hw(w), w['tier']):
            changed = []
            pw = {a['need']: a['pin'] for a in w['assignment']}
            pc = {a['need']: a['pin'] for a in c['assignment']}
            changed = ['%s %s -> %s' % (n, pw.get(n, '?'), pc[n]) for n in sorted(pc) if pw.get(n) != pc[n]]
            ok.append({'hardware': short_hw(c), 'tier': c['tier'], 'how_we_know': 'resolver-valid: every requirement met by the ladder rungs that could be checked; NOT run on a twin or on the hardware (open: %s)' % (
                '; '.join(r['text'] for r in c['risks'][:3]) or 'none'),
                'what_changed': ('pins differ: ' + ', '.join(changed)) if changed else 'nothing: the same pins', 'proof_of_the_routes': ', '.join('%s %s' % (j, s) for j, s in sorted(c['variant_status'].items()))})
        elif c['rank_class'] >= 2:
            no.append({'hardware': short_hw(c), 'tier': c['tier'], 'why': CLASS_WORDS[c['rank_class']] + ': ' + '; '.join(r['text'] for r in c['risks'] if r['kind'] in ('placement', 'lost', 'criterion'))[:240]})
    for key, why in sorted(engine.fail_by_key.items()):
        if key[3] == tuple(sorted(w['routes'].items())):
            no.append({'hardware': '%s / %s' % (key[0], key[1] or 'package not modelled'), 'tier': key[2], 'why': 'does not resolve: ' + why})
    for (board, pkg, tier), why in sorted(engine.tier_gone.items()):
        no.append({'hardware': '%s / %s' % (board, pkg or 'package not modelled'), 'tier': tier, 'why': 'tier not available: ' + why})
    return ok, no


def reference_wiring(w, engine):
    """The bench's wiring today, checked for the winner's variant choice: is it also valid, and what does it cost against the chosen pins?"""
    if w is None or not w['assignment']:
        return None
    pairs, spec_b, spec_w, missing = [], 0.0, 0.0, []
    for a in w['assignment']:
        spec_w += a['spec_cost']
        if a['bench_pin']:
            pairs.append('%s on %s' % (a['role'], a['bench_pin']))
    return {'bench_wiring': pairs, 'note': 'The bench is wired today: %s. Run again with prefer = bench-wiring to place the same routes on exactly those pins when they are free.' % ('; '.join(pairs) or 'nothing recorded')}


def summary(c):
    return {'id': c['id'], 'rank': c['rank'], 'hardware': short_hw(c), 'tier': c['tier'], 'routes': c['routes'], 'pins': {a['need']: a['pin'] for a in c['assignment']},
            'placement': c['placement'], 'resource_score': c['resource_score'], 'cycle_us': c['cycle_us'], 'parts_missing': [p['class'] for p in c['parts_missing']], 'risk_points': c['risk_points']}


def view_rows(res, view):
    cands = res['_ranked']
    if view == 'score-card':
        return score_card_rows(cands, res['limits']['max_candidates'], res['objective'])
    if view == 'trade-study':
        return trade_rows(cands, res['limits']['max_candidates'])
    if view == 'assignment':
        return assignment_rows(res['chosen_candidate'])
    if view == 'pruned':
        return res['pruned_rows']
    if view == 'designed-for':
        d = res['designed_for']
        rows = [{'what': 'Designed for', 'hardware': d['hardware'], 'tier': d['tier'], 'detail': 'variants: %s; pins: %s' % (', '.join('%s via %s' % kv for kv in sorted(d['variants'].items())), d['pins']), 'how_we_know': d['basis']}] if d else []
        rows += [{'what': 'Also runs on', 'hardware': x['hardware'], 'tier': x['tier'], 'detail': x['what_changed'], 'how_we_know': x['how_we_know']} for x in res['also_runs_on']]
        rows += [{'what': 'Does not run on', 'hardware': x['hardware'], 'tier': x['tier'], 'detail': x['why'], 'how_we_know': 'read off the rows: a reason, not a guess'} for x in res['does_not_run_on']]
        return rows
    raise KeyError('no view %r (score-card, trade-study, assignment, pruned, designed-for)' % view)


VIEWS = ('score-card', 'trade-study', 'assignment', 'pruned', 'designed-for')
