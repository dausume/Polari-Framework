"""
Selftest for the tech-tree module (tt-3).

Run from polari-framework/:  python3 -m techtree.selftest_techtree

Stdlib-only (SimpleNamespace rows, no DB/falcon/treeObject). Covers:
active-tree resolution, structural validation (evidence + knob +
action on every failure), edge derivation from depends_on_json with
stable transient/primary designation, all four per-segment
done-tests, the completion rollup (assignment -> segment -> node ->
tree), and the baseline-achieved gate.
"""

import json
import types

from techtree.techtree_analysis import (
    active_tree_name, node_completion, sync_edges, tree_completion,
    tree_payload, validate_tree,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _ns(**fields):
    return types.SimpleNamespace(**fields)


def _node(name, deps=(), title=''):
    return _ns(name=name, tree_name='oseb-test', title=title,
               description='', depends_on_json=json.dumps(list(deps)),
               layout_hints_json='{}', notes='')


def _assignment(node, kind, ref):
    return _ns(name=f'{node}:{kind}:{ref}', tech_node=node,
               tree_name='oseb-test', segment_kind=kind,
               ref_name=ref, notes='')


def _mgr():
    """A little OSEB slice: printing + laser both depend on wax
    (shared dep -> transient designation), with all four segment
    kinds exercised."""
    rows = {
        'TechTreeDefinition': {
            'oseb-test': _ns(name='oseb-test', owner='polari',
                             description='', is_active=True,
                             is_baseline=True, notes=''),
        },
        'TechNode': {
            n.name: n for n in [
                _node('wax-materials'),
                _node('3d-printing', deps=('wax-materials',)),
                _node('laser-cnc', deps=('wax-materials',
                                         '3d-printing')),
            ]},
        'TechSegment': {
            # real weighs double on 3d-printing (knob row).
            '3d-printing:real': _ns(
                name='3d-printing:real', tech_node='3d-printing',
                tree_name='oseb-test', kind='real', weight=2.0,
                notes=''),
        },
        'TechSegmentAssignment': {
            a.name: a for a in [
                _assignment('wax-materials', 'theory',
                            'materialsScience'),
                _assignment('wax-materials', 'theory', 'waxsupply'),
                _assignment('3d-printing', 'theory', 'waxprint'),
                _assignment('3d-printing', 'real', 'waxprinter-v1'),
                _assignment('3d-printing', 'business',
                            'one-person-printfarm'),
                _assignment('laser-cnc', 'politics',
                            'open-hardware-tariff'),
            ]},
        'TechDependencyEdge': {},
        # theory substrate: waxprint + materialsScience enabled,
        # waxsupply NOT placed anywhere.
        'ModuleAssignment': {
            'waxprint@prf-a': _ns(name='waxprint@prf-a',
                                  module_name='waxprint',
                                  instance_name='prf-a',
                                  state='enabled'),
            'materialsScience@prf-a': _ns(
                name='materialsScience@prf-a',
                module_name='materialsScience',
                instance_name='prf-a', state='enabled'),
        },
        'PolariModule': {},
        # real/business/politics substrate (tt-6 shapes, duck-typed).
        'RealArtifact': {
            'waxprinter-v1': _ns(
                name='waxprinter-v1', proven=True,
                commercial_route_json='{"vendor": "any"}',
                self_manufacture_route_json='{"guide": "wiki"}'),
        },
        'BusinessModelDefinition': {
            'one-person-printfarm': _ns(
                name='one-person-printfarm', self_sustaining=False,
                evidence_json='[]'),
        },
        'PolicyDefinition': {},
    }
    return _ns(objectTables=rows)


if __name__ == '__main__':
    print('== suite: active tree resolution ==')
    mgr = _mgr()
    check('active tree resolves', active_tree_name(mgr) == 'oseb-test')
    mgr.objectTables['TechTreeDefinition']['oseb-test'].is_active = False
    check('baseline is the fallback when nothing is active',
          active_tree_name(mgr) == 'oseb-test')

    print('== suite: validation ==')
    mgr = _mgr()
    report = validate_tree(mgr, 'oseb-test')
    check('healthy tree validates', report.get('valid'),
          json.dumps(report.get('findings')))
    check('unknown tree refused honestly',
          not validate_tree(mgr, 'nope').get('ok'))
    broken = _mgr()
    broken.objectTables['TechNode']['ghost-consumer'] = _node(
        'ghost-consumer', deps=('no-such-tech',))
    broken.objectTables['TechSegmentAssignment']['bad'] = _ns(
        name='bad', tech_node='ghost-node', tree_name='oseb-test',
        segment_kind='vibes', ref_name='', notes='')
    report = validate_tree(broken, 'oseb-test')
    checks = {f['check'] for f in report['findings']}
    check('unknown dep + unknown node + bad kind + empty ref caught',
          {'unknown-tech-dependency', 'assignment-unknown-node',
           'unknown-segment-kind',
           'assignment-without-ref'} <= checks,
          json.dumps(sorted(checks)))
    check('every finding carries evidence + knob + action',
          all(f['evidence'] and f['knob'] and f['action']
              for f in report['findings']))

    print('== suite: edge derivation + designation ==')
    mgr = _mgr()
    result = sync_edges(mgr, 'oseb-test')
    edges = mgr.objectTables['TechDependencyEdge']
    check('edges derived from depends_on_json',
          sorted(result['created']) == [
              '3d-printing->wax-materials',
              'laser-cnc->3d-printing',
              'laser-cnc->wax-materials'])
    wax_edges = [e for e in edges.values()
                 if e.depends_on_tech == 'wax-materials']
    check('shared tech: one primary, one transient',
          sorted((e.is_primary, e.is_transient)
                 for e in wax_edges) == [(False, True),
                                         (True, False)])
    check('alphabetically-first dependent is primary',
          [e.tech_node for e in wax_edges
           if e.is_primary] == ['3d-printing'])
    check('solo dep is primary, not transient',
          all(e.is_primary and not e.is_transient
              for e in edges.values()
              if e.depends_on_tech == '3d-printing'))
    # Stability: hand the primary to laser-cnc; a re-sync keeps it.
    for e in wax_edges:
        e.is_primary = e.tech_node == 'laser-cnc'
        e.is_transient = not e.is_primary
    sync_edges(mgr, 'oseb-test')
    check('existing primary survives re-sync',
          [e.tech_node for e in wax_edges
           if e.is_primary] == ['laser-cnc'])
    # Stale edges drop when the dep statement changes.
    mgr.objectTables['TechNode']['laser-cnc'].depends_on_json = (
        json.dumps(['3d-printing']))
    result = sync_edges(mgr, 'oseb-test')
    check('stale edge removed on re-sync',
          result['removed'] == ['laser-cnc->wax-materials'])

    print('== suite: completion rollup ==')
    mgr = _mgr()
    wax = node_completion(mgr, 'oseb-test', 'wax-materials')
    check('theory 1/2 (waxsupply unplaced)',
          wax['segments'][0]['done'] == 1
          and wax['segments'][0]['total'] == 2)
    check('undone theory gap names the pol allocate knob',
          any('pol allocate waxsupply' in g['action']
              for g in wax['gaps']))
    check('absent segments take no space',
          wax['segmentsPresent'] == ['theory'])
    printing = node_completion(mgr, 'oseb-test', '3d-printing')
    check('3d-printing presents theory+real+business',
          printing['segmentsPresent'] == ['theory', 'real',
                                          'business'])
    # theory 1/1, real 1/1 (weight 2), business 0/1 ->
    # (1*1 + 1*2 + 0*1) / 4
    check('node completion is the weighted mean over present '
          'segments', abs(printing['completionLevel'] - 0.75) < 1e-9,
          str(printing['completionLevel']))
    check('unproven business names the missing evidence',
          any('self-sustaining' in g['evidence']
              for g in printing['gaps']))
    laser = node_completion(mgr, 'oseb-test', 'laser-cnc')
    check('politics without a PolicyDefinition is honest',
          laser['completionLevel'] == 0.0
          and any('no PolicyDefinition' in g['evidence']
                  for g in laser['gaps']))

    tree = tree_completion(mgr, 'oseb-test')
    check('tree completion is the mean over nodes',
          abs(tree['completionLevel']
              - (0.5 + 0.75 + 0.0) / 3) < 1e-9,
          str(tree['completionLevel']))
    check('baseline not achieved while gaps remain',
          not tree['baselineAchieved'])

    # Close every gap -> baseline achieved.
    mgr.objectTables['ModuleAssignment']['waxsupply@prf-a'] = _ns(
        name='waxsupply@prf-a', module_name='waxsupply',
        instance_name='prf-a', state='enabled')
    bm = mgr.objectTables['BusinessModelDefinition'][
        'one-person-printfarm']
    bm.self_sustaining = True
    bm.evidence_json = '["ran 12 months cash-positive"]'
    mgr.objectTables['PolicyDefinition']['open-hardware-tariff'] = _ns(
        name='open-hardware-tariff',
        policy='tariff exemption for open hardware',
        evidence_json='["EU pilot"]')
    tree = tree_completion(mgr, 'oseb-test')
    check('every gap closed => baseline achieved',
          tree['baselineAchieved'] and tree['completionLevel'] == 1.0,
          json.dumps(tree['gaps']))

    print('== suite: render payload ==')
    mgr = _mgr()
    sync_edges(mgr, 'oseb-test')
    payload = tree_payload(mgr, 'oseb-test')
    check('payload ok + tree meta', payload.get('ok')
          and payload['tree']['isBaseline'])
    check('payload carries segment colors for all four kinds',
          sorted(payload['segmentColors']) == [
              'business', 'politics', 'real', 'theory'])
    printing = [n for n in payload['nodes']
                if n['name'] == '3d-printing'][0]
    check('payload node carries derived segments + completion',
          printing['segmentsPresent'] == ['theory', 'real',
                                          'business']
          and abs(printing['completionLevel'] - 0.75) < 1e-9)
    check('payload edges carry designation',
          payload['edges'] and all(
              'isPrimary' in e and 'isTransient' in e
              for e in payload['edges']))
    check('unknown tree payload refused honestly',
          not tree_payload(mgr, 'nope').get('ok'))

    print('== suite: domain-tree seed coherence (tt-8) ==')
    from techtree.techtree_analysis import baseline_report
    from techtree.techtree_seed import (
        SEED_BUSINESS_MODELS, SEED_OSEB_POLARI_MODULES,
        SEED_POLICY_DEFINITIONS, SEED_REAL_ARTIFACTS,
        SEED_TECH_NODES, SEED_TECH_SEGMENT_ASSIGNMENTS,
        SEED_TECH_TREE_DEFINITIONS, TREE_ECONOMY, TREE_ELECTRONICS,
        TREE_SUPPLY, retire_legacy_trees,
    )
    from waxprint.waxprint_seed import SEED_WAXPRINT_MODULES

    def _table(seed_list):
        return {s['name']: _ns(**s) for s in seed_list}

    def _seeded_mgr():
        return _ns(objectTables={
            'TechTreeDefinition': _table(SEED_TECH_TREE_DEFINITIONS),
            'TechNode': _table(SEED_TECH_NODES),
            'TechSegment': {},
            'TechSegmentAssignment': _table(
                SEED_TECH_SEGMENT_ASSIGNMENTS),
            'TechDependencyEdge': {},
            'ModuleAssignment': {},
            'PolariModule': _table(SEED_WAXPRINT_MODULES
                                   + SEED_OSEB_POLARI_MODULES),
            'RealArtifact': _table(SEED_REAL_ARTIFACTS),
            'BusinessModelDefinition': _table(SEED_BUSINESS_MODELS),
            'PolicyDefinition': _table(SEED_POLICY_DEFINITIONS),
        })

    domains = _seeded_mgr()
    check('electronics is the active tree',
          active_tree_name(domains) == TREE_ELECTRONICS)
    for tree_name in (TREE_ELECTRONICS, TREE_SUPPLY, TREE_ECONOMY):
        report = validate_tree(domains, tree_name)
        check(f'{tree_name} seed validates with zero errors',
              report.get('valid'),
              json.dumps(report.get('findings')))
        sync_edges(domains, tree_name)
    by_tree = {}
    for n in SEED_TECH_NODES:
        by_tree[n['tree_name']] = by_tree.get(n['tree_name'], 0) + 1
    check('node counts: electronics 24 / supply 15 / economy 4',
          by_tree == {TREE_ELECTRONICS: 24, TREE_SUPPLY: 15,
                      TREE_ECONOMY: 4}, json.dumps(by_tree))

    edges = domains.objectTables['TechDependencyEdge'].values()
    pla_dependents = [
        e for e in edges if e.depends_on_tech
        == f'{TREE_ELECTRONICS}/precision-laser-apparatus']
    check('Precision Laser Apparatus shared by BLCNC + LASiS => '
          'one primary + transient copy',
          sorted(e.tech_node.split("/")[1]
                 for e in pla_dependents) == [
              'bombastic-laser-cnc', 'lasis']
          and sum(1 for e in pla_dependents if e.is_primary) == 1
          and sum(1 for e in pla_dependents if e.is_transient) == 1)
    cnt_dependents = [e for e in edges if e.depends_on_tech
                      == f'{TREE_SUPPLY}/cnt-supply']
    check('p-doped + n-doped CNT supplies branch off raw CNT supply',
          len(cnt_dependents) == 2
          and sum(1 for e in cnt_dependents if e.is_transient) == 1)
    check('os-pvd requires vacuum pump + piezoelectrics',
          any(e.tech_node == f'{TREE_ELECTRONICS}/os-pvd'
              and e.depends_on_tech
              == f'{TREE_ELECTRONICS}/vacuum-pump' for e in edges)
          and any(e.tech_node == f'{TREE_ELECTRONICS}/os-pvd'
                  and e.depends_on_tech
                  == f'{TREE_ELECTRONICS}/piezoelectrics'
                  for e in edges))

    printing3d = [
        n for n in tree_completion(
            domains, TREE_ELECTRONICS)['nodes']
        if n['node'] == f'{TREE_ELECTRONICS}/3d-printing'][0]
    check('3d-printing still presents ALL FOUR segments at 25%',
          printing3d['segmentsPresent'] == ['theory', 'real',
                                            'business', 'politics']
          and abs(printing3d['completionLevel'] - 0.25) < 1e-9)

    print('== suite: OSEB baseline across domain trees (tt-8) ==')
    baseline = baseline_report(domains)
    check('baseline rolls up all three domain trees',
          [t['name'] for t in baseline['trees']] == sorted([
              TREE_ELECTRONICS, TREE_SUPPLY, TREE_ECONOMY]))
    check('baseline carries domain titles',
          any(t['title'] == 'Electronics / Microelectronics'
              for t in baseline['trees'])
          and any(t['title'] == 'Raw Supply Chain'
                  for t in baseline['trees']))
    expected = sum(t['completionLevel']
                   for t in baseline['trees']) / 3
    check('combined completion is the mean over domain trees',
          abs(baseline['completionLevel'] - expected) < 1e-9)
    check('OSEB not achieved while any domain tree is open',
          not baseline['baselineAchieved'])
    check('shells stay honest gaps (agroforestry / microbusiness / '
          'cntsupply named)',
          any('"agroforestry"' in g['evidence']
              for t in baseline['trees'] for g in tree_completion(
                  domains, t['name'])['gaps'])
          and any('"microbusiness"' in g['evidence']
                  for g in tree_completion(
                      domains, TREE_ECONOMY)['gaps'])
          and any('"cntsupply"' in g['evidence']
                  for g in tree_completion(
                      domains, TREE_SUPPLY)['gaps']))
    for t in baseline['trees']:
        print(f"  ({t['title']}: "
              f"{round(t['completionLevel'] * 100, 1)}%)")
    print(f"  (combined OSEB: "
          f"{round(baseline['completionLevel'] * 100, 1)}%)")

    print('== suite: legacy oseb retirement (tt-8) ==')
    legacy = _seeded_mgr()
    legacy.objectTables['TechTreeDefinition']['oseb'] = _ns(
        name='oseb', title='', owner='polari', description='',
        is_active=False, is_baseline=True, notes='')
    legacy.objectTables['TechNode']['oseb/nanoparticles'] = _ns(
        name='oseb/nanoparticles', tree_name='oseb', title='',
        description='', depends_on_json='[]',
        layout_hints_json='{}', notes='')
    legacy.objectTables['PolariModule']['materialsScience'] \
        .tech_node_ref = 'oseb/nanoparticles'
    deletes = []
    legacy.db = _ns(
        deleteRowsWhere=lambda c, col, v: deletes.append(
            (c, col, v)) or 0,
        saveInstanceInDB=lambda row: None)
    removed = retire_legacy_trees(legacy)
    check('legacy tree + node rows removed from the object tree',
          'oseb' not in legacy.objectTables['TechTreeDefinition']
          and 'oseb/nanoparticles'
          not in legacy.objectTables['TechNode'])
    check('DB deletes issued for the legacy rows',
          ('TechTreeDefinition', 'name', 'oseb') in deletes
          and ('TechNode', 'tree_name', 'oseb') in deletes)
    check('stale tech_node_ref remapped (nanoparticles -> lasis)',
          legacy.objectTables['PolariModule']['materialsScience']
          .tech_node_ref == f'{TREE_ELECTRONICS}/lasis')
    check('baseline unaffected after retirement',
          not any(t['name'] == 'oseb'
                  for t in baseline_report(legacy)['trees']))
    check('retirement is idempotent',
          retire_legacy_trees(legacy) == {})

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed' + (f'; FAILED: {failed}' if failed else ''))
    raise SystemExit(1 if failed else 0)
