"""cmod_catom_config_selftest - cfg-0 (AI-Notes/plans/CATOM_CONFIG_PLAN.md): the shape and the verdict engine, proven on a TOY catom whose one check is
registered by this test only (no real group is wired until cfg-1). The plan's proof: one invalid, one compromise and one ideal option -> the ideal is chosen
automatically; a person's other choice is recorded with what it gives up; the same configuration judged in two Bench Solutions gets two verdicts and the
choice is flagged where it turns invalid; the isotope decides which options exist; cheapest-first checks skip the rest once one says invalid; no row copies
another's field; the doors; the manifest.

    PYTHONPATH=.:modules python3 -m cmod.cmod_catom_config_selftest      # from polari-framework/
"""
import json
import sys
import types

passed = total = 0
CATOM = 'toy-button'


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _manager():
    return types.SimpleNamespace(objectTables={}, idList=[], db=None, noteTreeMutation=lambda *a, **k: None)


def _bounce(option, ctx):
    """TOY layer-1 check (test only): contacts bounce for 5 ms, 8 ms when the bench may be as cold as 0 C; a debounce under the bounce is invalid,
    under twice the bounce a compromise (thin margin), over 100 ms a compromise (fast presses are lost), otherwise ideal."""
    if 'debounce_ms' not in option['values']:
        return None
    d = float(option['values']['debounce_ms'])
    bounce = 8.0 if ctx['conditions']['ambient_min_c'] <= 0 else 5.0
    margin = (d - bounce) / bounce
    if d < bounce:
        return {'outcome': 'invalid', 'margin': margin, 'why': 'debounce %g ms is shorter than the %g ms bounce' % (d, bounce), 'evidence': 'toy'}
    if d > 100:
        return {'outcome': 'compromise', 'margin': margin, 'gives_up': 'presses closer than %g ms apart are lost' % d, 'why': 'long window',
                'evidence': 'toy'}
    if d < 2 * bounce:
        return {'outcome': 'compromise', 'margin': margin, 'gives_up': 'margin %.0f %% over the bounce (recommended 100 %%)' % (100 * margin),
                'why': 'thin margin', 'evidence': 'toy'}
    return {'outcome': 'ideal', 'margin': margin, 'why': 'full margin', 'evidence': 'toy'}


def _never_reached(option, ctx):
    return {'outcome': 'ideal', 'margin': 1.0, 'why': 'a layer-3 check'}


def _seed(m):
    from cmod.custom import config_rows as R
    R.upsert(m, 'BenchConditions', 'room', ambient_min_c=15.0, ambient_max_c=30.0)
    R.upsert(m, 'BenchConditions', 'cold-garage', ambient_min_c=-5.0, ambient_max_c=30.0)
    R.upsert(m, 'BenchSolution', 'toy-on-desk', bench='home-bench', firmware_solution='toy-fw', conditions='room')
    R.upsert(m, 'BenchSolution', 'toy-in-garage', bench='garage-bench', firmware_solution='toy-fw', conditions='cold-garage')
    for slug, ms, iso in (('d2', 2, ''), ('d6', 6, ''), ('d20', 20, ''), ('d250', 250, ''), ('d30-poll', 30, 'poll')):
        R.upsert(m, 'ConfigOption', '%s:timing:%s' % (CATOM, slug), catom=CATOM, group='timing', level='values', title='debounce %d ms' % ms,
                 sets_json=json.dumps({'debounce_ms': ms}), isotope=iso, source='toy')


def main():
    from cmod.custom import catom_config as CF
    from cmod.custom import config_checks as CC
    from cmod.custom import config_rows as R
    CC.register('timing', 1, 'toy-bounce', _bounce)
    CC.register('timing', 3, 'toy-sim', _never_reached)
    try:
        m = _manager()
        _seed(m)
        v = CF.evaluate(m, 'toy-on-desk', CATOM)
        g = v['groups'][0]
        by = {o['option'].split(':')[-1]: o for o in g['options']}
        check('PROOF 1: the three verdicts: debounce 2 ms invalid (under the bounce), 6 ms and 250 ms compromise (thin margin / lost presses), 20 ms ideal; '
              'the option of the other isotope (poll) is not offered while no isotope is chosen',
              (by['d2']['verdict'], by['d6']['verdict'], by['d20']['verdict'], by['d250']['verdict']) == ('invalid', 'compromise', 'ideal', 'compromise')
              and 'd30-poll' not in by, {k: o['verdict'] for k, o in by.items()})
        check('PROOF 2: the ideal is chosen automatically, and the card says so and why', g['chosen'].endswith(':d20') and g['chosen_by'] == 'auto'
              and g['why'].startswith('chosen automatically: ideal'), (g['chosen'], g['why']))
        check('SCORING: competitive over the valid options only (invalid = 0, best = 100, worst = 0)',
              by['d2']['score'] == 0 and max(o['score'] for o in g['options']) == 100 and min(o['score'] for o in g['options'] if o['verdict'] != 'invalid') == 0,
              {k: o['score'] for k, o in by.items()})
        d2checks = {c['check']: c['outcome'] for c in by['d2']['checks']}
        check('CHEAPEST FIRST: once the layer-1 check says invalid, the layer-3 check is recorded as skipped (not run)',
              d2checks == {'toy-bounce': 'invalid', 'toy-sim': 'skipped'} and [c['layer'] for c in by['d2']['checks']] == [1, 3], d2checks)
        try:
            CF.choose(m, 'toy-on-desk', CATOM, '%s:timing:d2' % CATOM)
            refused = ''
        except R.ConfigRefused as e:
            refused = e.why
        check('An invalid option cannot be chosen, and the refusal says why', 'invalid in Bench Solution' in refused and 'shorter than the 5 ms bounce' in refused,
              refused)
        v = CF.choose(m, 'toy-on-desk', CATOM, '%s:timing:d6' % CATOM)
        g = v['groups'][0]
        check('PROOF 3: a person\'s other choice is recorded as theirs, with what it gives up against the automatic one',
              g['chosen'].endswith(':d6') and g['chosen_by'] == 'person' and 'instead of the automatic ideal' in g['why'] and 'margin 20 %' in g['why'], g['why'])
        v = CF.evaluate(m, 'toy-on-desk', CATOM)
        check('A re-evaluation keeps the person\'s choice', v['groups'][0]['chosen'].endswith(':d6') and v['groups'][0]['chosen_by'] == 'person')
        w = CF.evaluate(m, 'toy-in-garage', CATOM)
        gw = w['groups'][0]
        byw = {o['option'].split(':')[-1]: o['verdict'] for o in gw['options']}
        check('PROOF 4: the SAME configuration (one firmware solution) judged in a second Bench Solution (down to -5 C, 8 ms bounce) gets its own verdicts: 6 ms '
              'is invalid there, and the person\'s choice is flagged there, offering the automatic one again',
              byw['d6'] == 'invalid' and byw['d20'] == 'ideal' and gw['flagged'] and gw['flag_why'].endswith('toy-button:timing:d20'), (byw, gw['flag_why']))
        v = CF.view(m, 'toy-on-desk', CATOM)
        check('ELSEWHERE: on the desk the catom page shows the same choice is invalid in the garage', v['groups'][0]['elsewhere']
              == [{'bench_solution': 'toy-in-garage', 'verdict': 'invalid', 'why': 'toy-bounce: debounce 6 ms is shorter than the 8 ms bounce'}],
              v['groups'][0]['elsewhere'])
        v = CF.choose(m, 'toy-on-desk', CATOM, '')
        check('option \'\' hands the group back to the automatic choice', v['groups'][0]['chosen'].endswith(':d20') and v['groups'][0]['chosen_by'] == 'auto')
        CF.set_isotope(m, 'toy-fw', CATOM, 'poll')
        v = CF.evaluate(m, 'toy-on-desk', CATOM)
        names = [o['option'].split(':')[-1] for o in v['groups'][0]['options']]
        check('ISOTOPE FIRST: choosing the poll isotope (changes the code) opens its own option (30 ms) beside the shared ones; isotope recorded as the '
              'person\'s', 'd30-poll' in names and v['isotope'] == 'poll' and v['isotope_chosen_by'] == 'person', names)
        conf = R.rows(m, 'CatomConfiguration')[0]
        choice = R.rows(m, 'ConfigChoice')[0]
        verdict = R.rows(m, 'ConfigOptionGrade')[0]
        check('NO OVERLAP: the configuration holds no values, the choice no group or values, the verdict no catom or configuration (each names the row it '
              'depends on)', not ({'sets_json', 'values', 'group'} & set(conf)) and not ({'group', 'sets_json', 'catom'} & set(choice))
              and not ({'catom', 'configuration', 'firmware_solution'} & set(verdict)), (sorted(conf), sorted(choice), sorted(verdict)))
        try:
            CF.view(m, 'nope', CATOM)
            nf = ''
        except R.ConfigRefused as e:
            nf = (e.status, e.why)
        check('An unknown Bench Solution is refused 404 in words', nf == (404, "no Bench Solution 'nope'"), nf)
        none = types.SimpleNamespace()
        try:
            R.upsert(none, 'ConfigChoice', 'x')
            nm = ''
        except R.ConfigRefused as e:
            nm = e.status
        check('With no live manager a write is refused 409, never faked', nm == 409, nm)

        from cmod.cmod_catom_config_api import CatomConfigAPI
        api = CatomConfigAPI(polServer=None, manager=m)

        def call(method, *args, body=None):
            resp = types.SimpleNamespace(status='200 OK', media=None)
            req = types.SimpleNamespace(get_param=lambda k: None, bounded_stream=types.SimpleNamespace(read=lambda: json.dumps(body or {}).encode()))
            getattr(api, method)(req, resp, *args)
            return resp
        gr = call('on_get_groups')
        gv = call('on_get', 'toy-on-desk', CATOM)
        bad = call('on_post_choose', 'toy-on-desk', CATOM, body={'option': '%s:timing:d2' % CATOM})
        iso = call('on_post_isotope', 'toy-on-desk', CATOM, body={'isotope': ''})
        nf = call('on_get', 'nope', CATOM)
        check('DOORS: GET config-groups lists 9 groups with the toy checks on timing; GET the view; POST choose an invalid option -> 422 with why; POST isotope '
              '\'\' re-evaluates without the poll option; unknown Bench Solution -> 404',
              len(gr.media['rows']) == 9 and any(r['group'] == 'timing' and len(r['checks']) == 2 for r in gr.media['rows']) and gv.media['ok']
              and bad.status.startswith('422') and 'invalid' in bad.media['error'] and iso.media['isotope'] == ''
              and 'd30-poll' not in [o['option'].split(':')[-1] for o in iso.media['groups'][0]['options']] and nf.status.startswith('404'),
              (bad.status, nf.status))
    finally:
        CC.unregister('timing', 'toy-bounce')
        CC.unregister('timing', 'toy-sim')
    from moduleService.manifests import conform
    for mod in ('cmod', 'board'):
        r = conform(mod)
        check('MANIFEST: pol modules conform %s is clean with the new rows and files listed' % mod, r['ok'], r.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
