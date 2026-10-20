"""
@module cmod.custom.fsc_values

fsc-1: the VALUE WRITER. One solve candidate (a Mission Solution) in -> its Firmware Score term values out, each {term, context, value, kind, basis}:
  context `hardware:<board>`   the whole solution on that board (mission-cycle, flash-free, bom-cost ...)
  context `purpose:<name>`     one Purpose's share: its own cycle and deadline-fit, the route work time and the cost of the routes its jobs use. A route (or a part class, or the
                               board itself) that several Purposes use is SPLIT in proportion to the Purposes' importance weights (D-fsc-5; safety 4, required 3, important 2, desired 1) and
                               every split is stated in the basis. A Purpose cycle itself is a latency, experienced whole, so it is not split.
kind is measured | estimated | cited | stand-in; an undetermined figure is carried at a stated stand-in, never zero. `active-current` and `noise-immunity` have no basis today
and get NO value (the scorer says so). Money comes from cited offers (cmod.custom.fsc_prices); with other knobs `money()` is called again by the scorer.
"""
import json

from cmod.custom import fsc_prices as PR
from cmod.custom import fsc_terms as T
from cmod.custom.fsc_context import split

q = T.q


def kind_of(k):
    return 'stand-in' if k == 'undetermined' else k


def active_current(config, manager=None):
    """cst-1: the Battery profile's `active-current` basis when one exists - the ground return of the config's `led-on` circuit state from its stored SPICE .op
    (electrodevice.custom.cst_verdict.active_current_ma), as q('measured', mA, basis); None when no run is stored (the term then stays without a value, as before).
    The MCU core current is not in it (no cited figure yet): the basis says so."""
    try:
        from electrodevice.custom import cst_verdict as CV
    except Exception:   # noqa: BLE001 - the electrodevice module may not be admitted
        return None
    ma, basis = CV.active_current_ma(config, manager)
    return q('measured', ma, basis) if ma is not None else None


def facts(c, ctx, manager=None):
    """What the candidate is made of, once: {classes {part class: {jobs, on_bench, why}}, board_part, atoms {job: n|None}, variants {job: row}}."""
    from cmod.custom import isotope_variants as IV
    classes, atoms, variants = {}, {}, {}
    for job, route in sorted(c['routes'].items()):
        v = (ctx['variants'].get(job) or {}).get(route)
        variants[job] = v
        if v is None:
            atoms[job] = None
            continue
        for p in IV.parts_of(v):
            e = classes.setdefault(p['class'], {'jobs': [], 'on_bench': p.get('on_bench'), 'why': p.get('why', '')})
            e['jobs'].append(job)
            if p.get('on_bench') is False:
                e['on_bench'] = False
        atoms[job] = len(IV._implementation(v)['atoms']) or None
    return {'classes': classes, 'board_part': PR.BOARD_PART.get(c['hardware']['board'], ''), 'atoms': atoms, 'variants': variants}


def money(c, f, ctx, knobs=None):
    """-> {bom: q, build: q, per_purpose: {purpose: {bom: q, build: q}}} under the given price knobs (accept_used / accept_local)."""
    names = [p['purpose'] for p in ctx['purposes']]
    cls = [(k, e) for k, e in sorted(f['classes'].items())]
    board = f['board_part']
    allc = ([board] if board else []) + [k for k, _ in cls]
    bom = PR.price_parts(allc, knobs)
    missing = [k for k, e in cls if e['on_bench'] is False]
    build = PR.price_parts(missing, knobs)
    unsure = [k for k, e in cls if e['on_bench'] == 'undetermined']

    def mk(pr, label, extra=''):
        if pr['total'] is None:
            return q('stand-in', None, pr['basis'])
        return q(pr['kind'], pr['total'], '%s %s%s' % (label, pr['basis'], extra))
    out = {'bom': mk(pr=bom, label='all parts incl. the board:'),
           'build': mk(pr=build, label='parts the bench lacks (%s; the board is already on the bench):' % (', '.join(missing) or 'none'),
                       extra=(' | bench status undetermined for: %s (not counted)' % ', '.join(unsure)) if unsure else ''),
           'per_purpose': {n: {} for n in names}}
    for key, items, label in (('bom', allc, 'bom-cost'), ('build', missing, 'cost-to-build-now')):
        shares = {n: 0.0 for n in names}
        words = []
        for k in items:
            users = names if k == board else sorted({p for j in f['classes'][k]['jobs'] for p in ctx['job_purposes'].get(j, [])})
            sh, sw = split(ctx, users)
            o = PR.cheapest(k, knobs)
            price = o['unit_price'] if o else PR.standin_price(None, knobs)
            if price is None:
                continue
            for n, s in sh:
                shares[n] += price * s
            words.append('%s %.2f %s - %s' % (k, price, 'cited' if o else 'stand-in', sw))
        kinds = [out[key]['kind']]
        for n in names:
            out['per_purpose'][n][key] = q(weakest_money(kinds), round(shares[n], 2), '%s share of Purpose %s: %s' % (label, n, ' | '.join(words) or 'no parts'))
    return out


def weakest_money(kinds):
    return T.weakest(kinds)


def _purpose_kind(row):
    return T.weakest([kind_of(x['kind']) for x in row['parts']])


def _fit(row, exponent):
    crit = row['criterion']
    if 'budget_us' not in crit:
        return None
    cyc, bud = row['us'], crit['budget_us']
    fit = 100.0 if cyc <= bud or cyc <= 0 else 100.0 * (bud / cyc) ** exponent
    return q(_purpose_kind(row), round(fit, 3), 'Purpose %s cycle %.1f us against its budget %.1f us (%s); deadline-fit = 100 x min(1, budget / cycle) ^ %s (the exponent is a knob)%s' % (
        row['purpose'], cyc, bud, crit.get('why', ''), exponent, '; the deadline is flagged SAFETY-CRITICAL' if crit.get('safety_critical') else ''))


#: the size terms of a PLAN: summed from per-route atom sizes (and the declared on-chip blocks), never read off a build of the whole solution
PLAN_SIZED = ('flash-free', 'ram-free', 'blocks-free')


def honest_kinds(values, state):
    """A PLAN (nothing built, or built with a Purpose unproven) must not call its sizes measured: flash-free / ram-free / blocks-free are route-sum figures, so
    they read `estimated` and say so. `pins-free` (and the counted risk/sharing terms) stay measured: they are COUNTED from the solution's own pin assignment /
    placement, which is exact for a plan too - their basis says it is the plan's assignment. A finished solution is left as it is. -> values (edited in place)."""
    if state == 'finished':
        return values
    for term in PLAN_SIZED:
        x = values.get(term)
        if x and x['kind'] == 'measured':
            x['kind'] = 'estimated'
            x['basis'] += ' | PLAN: summed from the routes\' own sizes, not read from a build of this whole solution, so estimated'
    pins = values.get('pins-free')
    if pins and pins['kind'] == 'measured':
        pins['basis'] += ' | counted from this plan\'s own pin assignment (exact, not a build)'
    return values


def hardware_values(c, ctx, f, evidence, also_runs_on, manager=None, exponent=T.DEADLINE_EXPONENT, knobs=None):
    """-> {term: q} for the context hardware:<board>."""
    from cmod.custom import solve_inputs as SI
    v = {}
    rows = c['cycle']['purposes']
    tot = c['cycle']['total_us']
    v['mission-cycle'] = q(kind_of(tot['kind']), c['cycle_us'], tot['basis'])
    live = [r for r in rows if r['trigger'] != 'boot']
    if live:
        w = max(live, key=lambda r: r['us'])
        v['worst-purpose-latency'] = q(_purpose_kind(w), w['us'], 'the slowest Purpose is %s at %.1f us: %s' % (w['purpose'], w['us'], '; '.join('%s %.1f us (%s)' % (x['what'], x['us'], x['kind']) for x in w['parts'])[:600]))
    fits = [(r, _fit(r, exponent)) for r in rows]
    fits = [(r, x) for r, x in fits if x]
    if fits:
        r, x = min(fits, key=lambda rx: rx[1]['value'])
        v['deadline-fit'] = q(T.weakest([x2['kind'] for _r, x2 in fits]), x['value'], 'the worst of %d stated deadlines: %s' % (len(fits), x['basis']))
    else:
        v['deadline-fit'] = q('stand-in', 100.0, 'no Purpose states a deadline, so there is nothing to miss; scored 100 as a stated stand-in')
    boot = [r for r in rows if r['trigger'] == 'boot']
    if boot:
        v['boot-to-ready'] = q(_purpose_kind(boot[0]), boot[0]['us'], 'the %s Purpose cycle (the init lane): %s' % (boot[0]['purpose'], '; '.join('%s %.2f us' % (x['what'], x['us']) for x in boot[0]['parts'])[:400]))
    rt = {t['key']: t for t in c['resources']['terms']}
    for term, key in (('flash-free', 'flash'), ('ram-free', 'ram'), ('pins-free', 'pins'), ('blocks-free', 'peripherals'), ('cpu-idle', 'cpu')):
        t = rt[key]
        v[term] = q(kind_of(t['kind']), round(100.0 * (1.0 - t['fraction']), 4), '%s | free = 100 x (1 - %.4f used)%s' % (t['basis'], t['fraction'], ' [stand-in]' if t['stand_in'] else ''))
    trig = []
    for p in ctx['purposes']:
        job = SI.TRIGGER_JOB.get((p.get('trigger') or {}).get('kind', ''))
        if job and job in c['cycle']['timings']:
            trig.append((p['purpose'], job, c['cycle']['timings'][job]['mode']))
    if trig:
        ev = sum(1 for _p, _j, m in trig if m == 'event')
        v['sleep-capable'] = q('estimated', round(100.0 * ev / len(trig), 2), 'trigger routes: ' + '; '.join('%s via %s is %s' % (p, j, 'interrupt/event driven' if m == 'event' else m + ' (cannot sleep)') for p, j, m in trig))
    v['risk-points'] = q('measured', c['risk_points'], 'open ladder rungs counted from the placement: %d (%s)' % (c['risk_points'], '; '.join(r['text'] for r in c['risks'] if r['kind'] == 'ladder')[:300]))
    nshare = len(c['sharing']) + sum(1 for r in c['risks'] if r['kind'] == 'peripheral')
    v['shared-resources'] = q('measured', nshare, '%d pin(s)/block(s) shared between needs: %s' % (nshare, '; '.join(r['text'] for r in c['risks'] if r['kind'] in ('sharing', 'peripheral'))[:300] or 'none'))
    v['parts-to-acquire'] = q('measured', len(c['parts_missing']), 'part classes the bench lacks: %s' % (', '.join(p['class'] for p in c['parts_missing']) or 'none'))
    v['part-count'] = q('estimated', len(f['classes']), 'part classes the chosen routes declare (union): %s' % (', '.join(sorted(f['classes'])) or 'none'))
    v['wires'] = q('estimated', len(c['pins_used']), 'pins used (%s), the stated proxy for wires and joints' % ', '.join(c['pins_used']))
    have = [n for n in f['atoms'].values() if n]
    avg = sum(have) / float(len(have)) if have else 0
    miss = [j for j, n in f['atoms'].items() if not n]
    v['code-size'] = q('stand-in' if miss else 'measured', round(sum(have) + avg * len(miss), 2), 'atoms of the chosen routes: %s%s' % (
        ', '.join('%s %s' % (j, n or 'no atoms yet') for j, n in sorted(f['atoms'].items())),
        ('; routes without atoms (%s) counted at the mean %.1f of the others (stand-in)' % (', '.join(miss), avg)) if miss else ''))
    v['also-runs-on'] = q('measured', also_runs_on, 'other hardware / package / tier combinations carrying the same routes: %d' % also_runs_on)
    v['proof-level'] = evidence
    m = money(c, f, ctx, knobs)
    v['bom-cost'], v['cost-to-build-now'] = m['bom'], m['build']
    v = {k: x for k, x in v.items() if x['value'] is not None}
    kinds = [x['kind'] for k, x in v.items()]
    cnt = {k: kinds.count(k) for k in T.KINDS}
    conf = 100.0 * sum(T.KIND_CONFIDENCE[k] for k in kinds) / float(len(kinds) or 1)
    v['confidence'] = q('measured', round(conf, 2), 'share of this solution own figures that are evidence: %d measured, %d cited, %d estimated (half), %d stand-in (none) of %d' % (
        cnt['measured'], cnt['cited'], cnt['estimated'], cnt['stand-in'], len(kinds)))
    return v


def purpose_values(c, ctx, f, manager=None, exponent=T.DEADLINE_EXPONENT, knobs=None):
    """-> {purpose: {term: q}} for the contexts purpose:<name>."""
    out = {}
    m = money(c, f, ctx, knobs)
    rows = {r['purpose']: r for r in c['cycle']['purposes']}
    for p in ctx['purposes']:
        n = p['purpose']
        r = rows.get(n)
        if r is None:
            continue
        d = {}
        d['worst-purpose-latency'] = q(_purpose_kind(r), r['us'], 'Purpose %s cycle, trigger to last task, %.1f us (experienced whole, not split): %s' % (n, r['us'], '; '.join('%s %.1f us (%s)' % (x['what'], x['us'], x['kind']) for x in r['parts'])[:500]))
        fit = _fit(r, exponent)
        if fit:
            d['deadline-fit'] = fit
        us, kinds, words = 0.0, [], []
        for job in sorted(c['routes']):
            if n not in ctx['job_purposes'].get(job, []):
                continue
            part = next((x for x in r['parts'] if x['what'].startswith(job + ' via ')), None)
            if part is None:
                continue
            sh, sw = split(ctx, ctx['job_purposes'][job])
            share = dict(sh)[n]
            us += part['us'] * share
            kinds.append(kind_of(part['kind']))
            words.append('%s via %s %.2f us x %.0f%% (%s)' % (job, c['routes'][job], part['us'], 100 * share, sw))
        d['route-time'] = q(T.weakest(kinds), round(us, 3), 'route work attributed to Purpose %s: %s' % (n, ' | '.join(words) or 'it uses no route'))
        d['bom-cost'] = m['per_purpose'][n]['bom']
        d['cost-to-build-now'] = m['per_purpose'][n]['build']
        cls = [(k, e) for k, e in sorted(f['classes'].items())]
        for term, items in (('part-count', [k for k, _ in cls]), ('parts-to-acquire', [k for k, e in cls if e['on_bench'] is False])):
            tot, words = 0.0, []
            for k in items:
                users = sorted({pp for j in f['classes'][k]['jobs'] for pp in ctx['job_purposes'].get(j, [])})
                sh, sw = split(ctx, users)
                s = dict(sh).get(n, 0.0)
                tot += s
                words.append('%s x %.0f%% (%s)' % (k, 100 * s, sw))
            d[term] = q('estimated' if term == 'part-count' else 'measured', round(tot, 3), '%s attributed to Purpose %s: %s' % (term, n, ' | '.join(words) or 'none'))
        out[n] = d
    return out


def to_rows(subject_name, hw_board, hw, per_purpose, state=''):
    """Flatten into ContextualizedValue-shaped dicts (name, term_name, subject_name, context_names_json, pre_normalized_value, source, notes)."""
    rows = []

    def one(term, ctxname, x):
        rows.append({'name': '%s@%s@%s' % (term, subject_name, ctxname), 'term_name': term, 'subject_name': subject_name, 'context_names_json': json.dumps([ctxname]),
                     'pre_normalized_value': x['value'], 'source': 'fsc:%s%s' % (x['kind'], (':' + state) if state else ''), 'notes': x['basis'], 'provenance_id': 'fsc-values'})
    for term, x in sorted(hw.items()):
        one(term, 'hardware:%s' % hw_board, x)
    for pn, d in sorted(per_purpose.items()):
        for term, x in sorted(d.items()):
            one(term, 'purpose:%s' % pn, x)
    return rows
