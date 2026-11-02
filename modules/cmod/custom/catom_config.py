"""
@module cmod.custom.catom_config

cfg-0 (AI-Notes/plans/CATOM_CONFIG_PLAN.md): A CATOM'S CONFIGURATION, JUDGED IN A BENCH SOLUTION. The steps, each its own function, over the rows
in config_rows, the checks in config_checks and the grading in config_grade:

  context(manager, bench_solution)               the Bench Solution, its conditions and its firmware solution (404 when either is missing)
  configuration(manager, firmware_solution, catom)   the CatomConfiguration, created on first use (isotope '' = not chosen yet)
  set_isotope(manager, firmware_solution, catom, isotope, who='person')   how the catom does its job (changes the code)
  evaluate(manager, bench_solution, catom)       grade every option of every group the catom has options in, in this Bench Solution; write one
                                                 ConfigOptionGrade per option and one ConfigOptionResult per check; set each group's automatic choice
                                                 (a person's choice is kept). -> view()
  choose(manager, bench_solution, catom, option, who='person')   a person picks an option (refused when invalid in this Bench Solution, with why);
                                                 option '' hands the group back to the automatic choice
  view(manager, bench_solution, catom)           what the catom page shows: the configuration, per group the chosen option (flagged when it is
                                                 invalid here), every option with its verdict, score and checks, and the same choice's verdict on
                                                 the other Bench Solutions that use this firmware solution
"""
from cmod.custom import config_checks as CC
from cmod.custom import config_grade as CG
from cmod.custom import config_rows as R
from cmod.custom.config_groups import GROUPS


def context(manager, bench_solution):
    bs = R.get(manager, 'BenchSolution', bench_solution)
    if bs is None:
        raise R.ConfigRefused('no Bench Solution %r' % bench_solution, status=404)
    cond = R.get(manager, 'BenchConditions', bs['conditions'])
    if cond is None:
        raise R.ConfigRefused('Bench Solution %r names conditions %r, which do not exist' % (bench_solution, bs['conditions']), status=404)
    if not bs['firmware_solution']:
        raise R.ConfigRefused('Bench Solution %r names no firmware solution' % bench_solution)
    return {'bench_solution': bs['name'], 'conditions': cond, 'firmware_solution': bs['firmware_solution']}


def configuration(manager, firmware_solution, catom):
    name = '%s:%s' % (firmware_solution, catom)
    return R.get(manager, 'CatomConfiguration', name) or R.upsert(manager, 'CatomConfiguration', name, firmware_solution=firmware_solution,
                                                                  catom=catom, isotope='', isotope_chosen_by='auto')


def set_isotope(manager, firmware_solution, catom, isotope, who='person'):
    configuration(manager, firmware_solution, catom)
    return R.upsert(manager, 'CatomConfiguration', '%s:%s' % (firmware_solution, catom), isotope=isotope, isotope_chosen_by=who)


def options(manager, catom, isotope):
    """The values-level options open to a configuration: the catom's shared ones and those of its chosen isotope, by group."""
    out = {}
    for o in R.rows(manager, 'ConfigOption', catom=catom, level='values'):
        if o['isotope'] in ('', isotope) and o['group'] in GROUPS:
            out.setdefault(o['group'], []).append(dict(o, values=R.sets(o)))
    return out


def _grade(group_options, ctx):
    graded = []
    for o in group_options:
        results = CC.run(o, ctx)
        v, why = CG.verdict(results)
        graded.append({'option': o, 'results': results, 'verdict': v, 'why': why})
    return CG.score(graded)


def _write(manager, bench_solution, g):
    gname = '%s|%s' % (bench_solution, g['option']['name'])
    R.upsert(manager, 'ConfigOptionGrade', gname, bench_solution=bench_solution, option=g['option']['name'], verdict=g['verdict'], score=g['score'],
             why=g['why'])
    R.drop(manager, 'ConfigOptionResult', grade=gname)
    for r in g['results']:
        R.upsert(manager, 'ConfigOptionResult', '%s#%s' % (gname, r['check']), grade=gname, check=r['check'], layer=r['layer'], outcome=r['outcome'],
                 margin=r['margin'], gives_up=r['gives_up'], why=r['why'], evidence=r['evidence'])


def evaluate(manager, bench_solution, catom):
    ctx = context(manager, bench_solution)
    conf = configuration(manager, ctx['firmware_solution'], catom)
    ctx['configuration'] = conf
    for group, opts in sorted(options(manager, catom, conf['isotope']).items()):
        graded = _grade(opts, ctx)
        for g in graded:
            _write(manager, bench_solution, g)
        auto = CG.default(graded)
        cname = '%s:%s' % (conf['name'], group)
        mine = R.get(manager, 'ConfigChoice', cname)
        if mine and mine['chosen_by'] == 'person':
            continue
        if auto is None:
            R.drop(manager, 'ConfigChoice', name=cname)
            continue
        R.upsert(manager, 'ConfigChoice', cname, configuration=conf['name'], option=auto['option']['name'], chosen_by='auto',
                 why='chosen automatically: %s, score %g (%s)' % (auto['verdict'], auto['score'], auto['score_why']))
    return view(manager, bench_solution, catom)


def _graded_from_rows(manager, bench_solution, option):
    gname = '%s|%s' % (bench_solution, option['name'])
    v = R.get(manager, 'ConfigOptionGrade', gname)
    if v is None:
        return None
    results = sorted(R.rows(manager, 'ConfigOptionResult', grade=gname), key=lambda r: (r['layer'], r['check']))
    return {'option': option, 'results': results, 'verdict': v['verdict'], 'why': v['why'], 'score': v['score']}


def choose(manager, bench_solution, catom, option, who='person'):
    ctx = context(manager, bench_solution)
    conf = configuration(manager, ctx['firmware_solution'], catom)
    if not option:
        R.drop(manager, 'ConfigChoice', configuration=conf['name'], chosen_by='person')
        return evaluate(manager, bench_solution, catom)
    o = R.get(manager, 'ConfigOption', option)
    if o is None or o['catom'] != catom:
        raise R.ConfigRefused('%r is not an option of catom %r' % (option, catom), status=404)
    g = _graded_from_rows(manager, bench_solution, o)
    if g is None:
        evaluate(manager, bench_solution, catom)
        g = _graded_from_rows(manager, bench_solution, o)
    if g is None:
        raise R.ConfigRefused('%r is not open to this configuration (isotope %r)' % (option, conf['isotope'] or 'not chosen'))
    if g['verdict'] == 'invalid':
        raise R.ConfigRefused('%r is invalid in Bench Solution %r: %s' % (option, bench_solution, g['why']))
    group_opts = [x for x in options(manager, catom, conf['isotope']).get(o['group'], [])]
    graded = [x for x in (_graded_from_rows(manager, bench_solution, x) for x in group_opts) if x]
    R.upsert(manager, 'ConfigChoice', '%s:%s' % (conf['name'], o['group']), configuration=conf['name'], option=option, chosen_by=who,
             why=CG.gives_up(g, CG.default(graded)))
    return view(manager, bench_solution, catom)


def _elsewhere(manager, ctx, choice):
    """The same chosen option's verdict on the other Bench Solutions that use this firmware solution."""
    out = []
    for bs in R.rows(manager, 'BenchSolution', firmware_solution=ctx['firmware_solution']):
        if bs['name'] == ctx['bench_solution']:
            continue
        v = R.get(manager, 'ConfigOptionGrade', '%s|%s' % (bs['name'], choice['option']))
        out.append({'bench_solution': bs['name'], 'verdict': v['verdict'] if v else 'not evaluated', 'why': v['why'] if v else ''})
    return out


def view(manager, bench_solution, catom):
    ctx = context(manager, bench_solution)
    conf = configuration(manager, ctx['firmware_solution'], catom)
    groups = []
    for group, opts in sorted(options(manager, catom, conf['isotope']).items()):
        graded = [x for x in (_graded_from_rows(manager, bench_solution, o) for o in opts) if x]
        choice = R.get(manager, 'ConfigChoice', '%s:%s' % (conf['name'], group))
        here = next((x for x in graded if choice and x['option']['name'] == choice['option']), None)
        auto = CG.default(graded)
        flagged = bool(choice and (here is None or here['verdict'] == 'invalid'))
        if choice and here is None:
            here = {'why': 'it is not open to the chosen isotope (%s) or not evaluated here' % (conf['isotope'] or 'none')}
        groups.append({
            'group': group, 'title': GROUPS[group]['title'], 'plain': GROUPS[group]['plain'],
            'chosen': choice['option'] if choice else '', 'chosen_by': choice['chosen_by'] if choice else '',
            'why': choice['why'] if choice else 'nothing chosen: every option is invalid here' if graded else 'not evaluated yet',
            'flagged': flagged,
            'flag_why': ('the chosen option is invalid in this Bench Solution: %s; the automatic choice would be %s'
                         % (here['why'], auto['option']['name'] if auto else 'none (every option is invalid)')) if flagged else '',
            'elsewhere': _elsewhere(manager, ctx, choice) if choice else [],
            'options': [{'option': x['option']['name'], 'title': x['option']['title'], 'values': x['option']['values'], 'verdict': x['verdict'],
                         'score': x['score'], 'why': x['why'], 'checks': x['results']} for x in graded],
        })
    return {'ok': True, 'bench_solution': bench_solution, 'firmware_solution': ctx['firmware_solution'], 'catom': catom,
            'configuration': conf['name'], 'isotope': conf['isotope'], 'isotope_chosen_by': conf['isotope_chosen_by'], 'groups': groups}
