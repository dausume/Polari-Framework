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

    print('== suite: OSEB seed coherence (tt-5) ==')
    from techtree.techtree_seed import (
        SEED_OSEB_POLARI_MODULES, SEED_TECH_NODES,
        SEED_TECH_SEGMENT_ASSIGNMENTS, SEED_TECH_TREE_DEFINITIONS,
    )
    from waxprint.waxprint_seed import SEED_WAXPRINT_MODULES

    def _table(seed_list):
        return {s['name']: _ns(**s) for s in seed_list}

    oseb = _ns(objectTables={
        'TechTreeDefinition': _table(SEED_TECH_TREE_DEFINITIONS),
        'TechNode': _table(SEED_TECH_NODES),
        'TechSegment': {},
        'TechSegmentAssignment': _table(
            SEED_TECH_SEGMENT_ASSIGNMENTS),
        'TechDependencyEdge': {},
        'ModuleAssignment': {},
        'PolariModule': _table(SEED_WAXPRINT_MODULES
                               + SEED_OSEB_POLARI_MODULES),
        'RealArtifact': {}, 'BusinessModelDefinition': {},
        'PolicyDefinition': {},
    })
    check('oseb is the active baseline tree',
          active_tree_name(oseb) == 'oseb')
    report = validate_tree(oseb, 'oseb')
    check('oseb seed validates with zero errors',
          report.get('valid'), json.dumps(report.get('findings')))
    check('oseb carries the 13 domains + os-pvd + 5 phases',
          len(SEED_TECH_NODES) == 19)
    sync_edges(oseb, 'oseb')
    edges = oseb.objectTables['TechDependencyEdge'].values()
    blcnc_dependents = [e for e in edges if e.depends_on_tech
                        == 'oseb/bombastic-laser-cnc']
    check('BLCNC shared by P1+P4+... => transient designation live',
          sum(1 for e in blcnc_dependents if e.is_primary) == 1
          and sum(1 for e in blcnc_dependents if e.is_transient)
          == len(blcnc_dependents) - 1
          and len(blcnc_dependents) >= 2)
    tree = tree_completion(oseb, 'oseb')
    check('theory substrate counts (baseline already >40%)',
          0.4 < tree['completionLevel'] < 1.0,
          str(tree['completionLevel']))
    check('unbuilt sims stay honest gaps naming blcnc/ospvd',
          any('"blcnc"' in g['evidence'] for g in tree['gaps'])
          and any('"ospvd"' in g['evidence'] for g in tree['gaps']))
    check('waxprint module row satisfies the 3d-printing theory ref',
          [n for n in tree['nodes']
           if n['node'] == 'oseb/3d-printing'][0]
          ['completionLevel'] == 1.0)
    print(f"  (seeded OSEB baseline completion: "
          f"{round(tree['completionLevel'] * 100, 1)}%)")

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed' + (f'; FAILED: {failed}' if failed else ''))
    raise SystemExit(1 if failed else 0)
