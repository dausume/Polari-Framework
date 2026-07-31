"""
@module composition.selftest_composition

Composition selftests (PART_ARCHETYPES_PLAN arch-1..). Standalone,
fake-manager style: python3 -m composition.selftest_composition
(from polari-framework/ with PYTHONPATH=modules).
"""

import types

from composition.seed_upsert import (
    diff_fields, upsert_seed_rows, upsert_seed_pairs,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


# ---------------------------------------------------------------
# arch-1: the seed upsert path
# ---------------------------------------------------------------

class _FakeRow:
    """Stands in for a treeObject: registers itself on the manager
    table at construction, like treeObjectInit does."""

    def __init__(self, manager=None, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        table = manager.objectTables.setdefault('FakeRow', {})
        table[id(self)] = self


def _mgr(rows=()):
    m = types.SimpleNamespace()
    m.objectTables = {'FakeRow': {id(r): r for r in rows}}
    m.objectTypingDict = {'FakeRow': object()}
    saved = []
    m.db = types.SimpleNamespace(saveInstanceInDB=saved.append)
    m.saved = saved
    return m


def _row(**kwargs):
    return types.SimpleNamespace(**kwargs)


def selftest_upsert():
    print('\n-- arch-1: seed upsert path --')

    # 1. Missing row is inserted.
    m = _mgr()
    rep = upsert_seed_rows(
        m, 'FakeRow', _FakeRow,
        [{'name': 'a', 'value': 1, 'is_prior': True}])
    check('missing row inserted', rep['inserted'] == ['a']
          and len(m.objectTables['FakeRow']) == 1)

    # 2. Changed field on a prior row converges; untouched fields
    #    survive; the row is persisted.
    row = _row(name='b', value=1, keep='original', is_prior=True)
    m = _mgr([row])
    rep = upsert_seed_rows(m, 'FakeRow', _FakeRow,
                           [{'name': 'b', 'value': 2}])
    check('changed field converges',
          row.value == 2 and rep['updated'] ==
          [{'name': 'b', 'fields': ['value']}])
    check('unmentioned field survives', row.keep == 'original')
    check('updated row persisted to db', m.saved == [row])

    # 3. THE gotcha case: a field added to the seed after the row
    #    exists reaches the live row (ten strikes ended here).
    row = _row(name='c', value=1, is_prior=True)
    m = _mgr([row])
    upsert_seed_rows(m, 'FakeRow', _FakeRow,
                     [{'name': 'c', 'value': 1, 'new_field': 'now'}])
    check('NEW seed field lands on existing row',
          getattr(row, 'new_field', None) == 'now')

    # 4. Customized rows (is_prior=False) are never touched.
    row = _row(name='d', value='measured', is_prior=False)
    m = _mgr([row])
    rep = upsert_seed_rows(m, 'FakeRow', _FakeRow,
                           [{'name': 'd', 'value': 'prior'}])
    check('is_prior=False row untouched',
          row.value == 'measured'
          and rep['skipped_custom'] == ['d'] and not m.saved)

    # 5. Identical row reports unchanged, no db write.
    row = _row(name='e', value=3, is_prior=True)
    m = _mgr([row])
    rep = upsert_seed_rows(m, 'FakeRow', _FakeRow,
                           [{'name': 'e', 'value': 3}])
    check('identical row unchanged, not rewritten',
          rep['unchanged'] == ['e'] and not m.saved)

    # 6. A failing row lands in errors; the rest still converge.
    class _Boom:
        def __init__(self, manager=None, **kwargs):
            raise RuntimeError('constructor refused')
    m = _mgr()
    rep = upsert_seed_rows(m, 'FakeRow', _Boom,
                           [{'name': 'f1'}, {'name': 'f2'}])
    check('per-row failure isolated',
          len(rep['errors']) == 2
          and rep['errors'][0]['op'] == 'insert')

    # 7. Gated-off class skipped loudly by the pairs runner.
    m = _mgr()
    reps = upsert_seed_pairs(
        m, [('NotBooted', _FakeRow, [{'name': 'x'}]),
            ('FakeRow', _FakeRow, [{'name': 'y'}])])
    check('gated-off class skipped, booted class seeded',
          reps[0].get('skipped') is True
          and reps[1]['inserted'] == ['y'])

    # 8. diff_fields treats a missing attribute as a difference.
    check('diff_fields flags missing attribute',
          diff_fields(_row(name='z'), {'name': 'z', 'added': 1})
          == ['added'])


# ---------------------------------------------------------------
# arch-2: core rows, derived levels, extraction
# ---------------------------------------------------------------

def _seed_mgr():
    """Fake manager over the real seeds — the magnetics selftest
    pattern."""
    import composition.composition_seed as cs

    def table(seed):
        return {s['name']: types.SimpleNamespace(**s) for s in seed}
    m = types.SimpleNamespace()
    m.objectTables = {
        'PartComponentDefinition': table(cs.SEED_PART_COMPONENTS),
        'CompositionNode': table(cs.SEED_COMPOSITION_NODES),
        'InterfaceDefinition': table(cs.SEED_INTERFACES),
        'FailureModeDefinition': table(cs.SEED_FAILURE_MODES),
        'FunctionalPartDefinition': table(cs.SEED_FUNCTIONAL_PARTS),
        'ConstructionVariantDefinition':
            table(cs.SEED_CONSTRUCTION_VARIANTS),
    }
    m.objectTypingDict = {k: object() for k in m.objectTables}
    return m


def selftest_arch2():
    import json

    from composition.data_refs import resolve_named
    from composition.node_basis import (
        CompositionNode, derive_level, composition_report,
    )
    import composition.composition_seed as cs

    print('\n-- arch-2: derived levels (mag-26 acceptance) --')
    m = _seed_mgr()

    # THE acceptance: three constructions, three levels, derived
    # from interface rows alone.
    simple = derive_level(m, 'stator-simple')
    bound = derive_level(m, 'stator-bound')
    layered = derive_level(m, 'stator-layered')
    check('simple stator derives ASSEMBLY',
          simple.get('ok') and simple['derived'] == 'assembly')
    check('bound stator derives PART',
          bound.get('ok') and bound['derived'] == 'part')
    check('layered stator derives PART-WITH-SEPARABLE-SUB-PARTS',
          layered.get('ok')
          and layered['derived'] == 'part-with-separable-sub-parts')
    check('layered separable set names the snap, bound set the '
          'groove',
          layered.get('separableSet') == ['if-layer-snap']
          and layered.get('boundSet') == ['if-layer-wire-groove'])
    check('every declared level matched its derivation',
          all(r.get('declared') in ('', r.get('derived'))
              or r.get('declared') == 'subassembly'
              for r in (simple, bound, layered)))

    print('\n-- arch-2: refusals are informative --')
    # Declared label may not overrule structure.
    m2 = _seed_mgr()
    m2.objectTables['CompositionNode']['stator-simple']\
        .declared_level = 'part'
    mismatch = derive_level(m2, 'stator-simple')
    check('declared-vs-derived mismatch refuses, naming interfaces',
          not mismatch.get('ok')
          and 'may not overrule' in mismatch.get('refusal', '')
          and mismatch.get('decidingInterfaces'))
    # Interfaces unstated = I-do-not-know, with the pairs to state.
    m3 = _seed_mgr()
    m3.objectTables['CompositionNode']['no-ifaces'] = \
        types.SimpleNamespace(
            name='no-ifaces', declared_level='',
            members_json=json.dumps([
                {'ref': 'pc-spool-core', 'kind': 'component',
                 'quantity': 1},
                {'ref': 'pc-sol-gel-binder', 'kind': 'component',
                 'quantity': 1}]))
    unk = derive_level(m3, 'no-ifaces')
    check('missing interfaces refuse with the pairs that need rows',
          not unk.get('ok')
          and unk.get('suggestion', {}).get('pairs'))
    # Unresolved member refuses rather than guessing.
    m4 = _seed_mgr()
    m4.objectTables['CompositionNode']['ghost'] = \
        types.SimpleNamespace(
            name='ghost', declared_level='',
            members_json=json.dumps([
                {'ref': 'no-such-component', 'kind': 'component',
                 'quantity': 1}]))
    ghost = derive_level(m4, 'ghost')
    check('unresolved member refuses',
          not ghost.get('ok') and ghost.get('unresolved'))
    # Single-component wrapper derives component.
    m5 = _seed_mgr()
    m5.objectTables['CompositionNode']['bare'] = \
        types.SimpleNamespace(
            name='bare', declared_level='',
            members_json=json.dumps([
                {'ref': 'pc-spool-core', 'kind': 'component',
                 'quantity': 1}]))
    check('single-component node derives COMPONENT',
          derive_level(m5, 'bare').get('derived') == 'component')
    # Module-not-booted is distinguished from no-such-row.
    _, ref1 = resolve_named(m, 'NotBootedClass', 'x')
    _, ref2 = resolve_named(m, 'CompositionNode', 'no-such-node')
    check('module-not-booted vs no-such-row distinguished',
          ref1['kind'] == 'module-not-booted'
          and ref2['kind'] == 'no-such-row')
    rep = composition_report(m)
    check('composition report covers all seeded nodes, no refusals',
          rep['count'] == 3 and not rep['refusals'])

    print('\n-- arch-2: extraction + cross-module data agreement --')
    from composition.part_roles import (
        ROLE_REQUIREMENTS as C_ROLES, role_viability as c_via,
    )
    from motors.part_roles import (
        ROLE_REQUIREMENTS as M_ROLES, role_viability as m_via,
    )
    check('motors re-exports the SAME role engine (no fork)',
          C_ROLES is M_ROLES and c_via is m_via
          and len(C_ROLES) == 10)
    # Failure-mode refs resolve, with the right locus at the right
    # place.
    fm = {s['name']: s for s in cs.SEED_FAILURE_MODES}
    iface_refs = [r for s in cs.SEED_INTERFACES
                  for r in json.loads(s['failure_mode_refs_json'])]
    bulk_refs = [r for s in cs.SEED_COMPOSITION_NODES
                 for r in json.loads(
                     s['bulk_failure_mode_refs_json'])]
    check('interface rows cite only interface-locus modes',
          iface_refs and all(
              fm[r]['locus'] == 'interface' for r in iface_refs))
    check('nodes cite only bulk-locus modes',
          bulk_refs and all(
              fm[r]['locus'] == 'bulk' for r in bulk_refs))
    # Two modules asserting the same fact must AGREE (mag-25
    # lesson): equation refs must be live physics_equations names.
    from motors.physics_equations import SEED_PHYSICS_EQUATIONS
    eq_names = {e['name'] for e in SEED_PHYSICS_EQUATIONS}
    cited = {s['equation_ref'] for s in cs.SEED_FAILURE_MODES
             if s['equation_ref']}
    cited |= {r for s in cs.SEED_INTERFACES
              for r in json.loads(s['equation_refs_json'])}
    check('every cited equation exists in physics_equations',
          cited and cited <= eq_names,
          f'missing: {cited - eq_names}')
    # Material refs are live catalog names.
    from magnetics.magnet_seed import SEED_MATERIAL_OPTIONS
    opts = {s['name'] for s in SEED_MATERIAL_OPTIONS}
    mats = {s['material_ref'] for s in cs.SEED_PART_COMPONENTS}
    check('every component material_ref is a live catalog name',
          mats <= opts, f'missing: {mats - opts}')
    # The promoted node records its genealogy and its bulk debt.
    check('bound stator carries genealogy + the crack-short mode it '
          'traded for',
          cs.SEED_COMPOSITION_NODES[1]['genealogy_ref']
          == 'stator-simple'
          and 'fm-potted-winding-crack-short' in bulk_refs)
    # Seeds flow through the arch-1 upsert (smoke, real classes not
    # needed: gated-off tables skip loudly).
    empty = types.SimpleNamespace(objectTables={},
                                  objectTypingDict={})
    reports = cs.seed_composition(empty)
    check('seed_composition runs the upsert path per class',
          len(reports) == 6
          and all(r.get('skipped') for r in reports))


# ---------------------------------------------------------------
# arch-3: EBOM/MBOM split — one functional part, three builds
# ---------------------------------------------------------------

def selftest_arch3():
    import types as _t

    from composition.fill_models import (
        SCRAMBLE_FILL, fill_for_class, groove_viability,
    )
    from composition.functional_basis import variant_report

    print('\n-- arch-3: EBOM/MBOM split --')
    m = _seed_mgr()
    rep = variant_report(m, 'fp-m0-stator')
    check('one functional stator, three construction variants',
          rep.get('ok') and rep['count'] == 3)
    by = {v['variant']: v for v in rep['variants']}
    check('variants carry their DERIVED levels (not stamps)',
          by['cv-stator-simple']['level'] == 'assembly'
          and by['cv-stator-bound']['level'] == 'part'
          and by['cv-stator-layered-bound']['level']
          == 'part-with-separable-sub-parts')
    check('repairability FOLLOWS from separability',
          by['cv-stator-simple']['repairable'] is True
          and by['cv-stator-bound']['repairable'] is False
          and by['cv-stator-layered-bound']['repairable'] is False)
    check('scramble fill known without geometry; ordered fill '
          'REFUSED without it',
          by['cv-stator-simple']['fill'] == SCRAMBLE_FILL
          and by['cv-stator-layered-bound']['fill'] is None
          and 'unstated' in
          by['cv-stator-layered-bound']['fillNote'])

    # THE mag-26 acceptance numbers, from the extracted model.
    d_wound = 0.2019 + 0.025  # 32 AWG bare + enamel build (mm)
    rep50 = variant_report(m, 'fp-m0-stator',
                           wound_diameter_mm=d_wound, wall_mm=0.05)
    by50 = {v['variant']: v for v in rep50['variants']}
    check('50 um wall: grooved 0.5274 is WORSE than scramble 0.600 '
          '(the mag-26 result, intact)',
          by50['cv-stator-layered-bound']['fill'] == 0.5274
          and by50['cv-stator-simple']['fill'] == 0.600)
    g = groove_viability(d_wound, 0.05)
    check('break-even wall ~14% of wound diameter (derived)',
          g['maxWallAsFractionOfWire'] == 0.1441
          and not g['beatsScramble'])
    check('just under the ~33 um break-even wall it still beats '
          'scramble; just over, it loses',
          groove_viability(d_wound, 0.032)['beatsScramble']
          and not groove_viability(d_wound, 0.034)['beatsScramble'])
    nested = groove_viability(d_wound, 0.05, nested=True)
    check('rigid floor forfeits fill vs nesting (0.785 vs 0.907 '
          'ceilings)',
          nested['orderedFill'] > g['orderedFill']
          and g['packingCeilingNoWalls'] == 0.7854
          and nested['packingCeilingNoWalls'] == 0.9069)

    # Cross-module agreement: motors uses THE SAME model object.
    import motors.stator_construction as sc
    check('motors re-imports the SAME fill model (no fork)',
          sc.groove_viability is groove_viability
          and sc.SCRAMBLE_FILL is SCRAMBLE_FILL)
    cmp_ = sc.compare_variants(awg=32, wall_mm=0.05)
    check('compare_variants reproduces from the extracted model '
          '(0.5274, not justified at this wall)',
          cmp_['groove']['orderedFill'] == 0.5274
          and 'WORSE than' in cmp_['finding'])

    # Refusals.
    check('unknown fill class refuses',
          not fill_for_class('tidy')['ok'])
    m2 = _seed_mgr()
    m2.objectTables['FunctionalPartDefinition']['fp-lonely'] = \
        _t.SimpleNamespace(name='fp-lonely', purpose='x',
                           allocated_role_refs_json='[]',
                           tunable_toward='')
    lonely = variant_report(m2, 'fp-lonely')
    check('functional part with no variants refuses (a requirement '
          'is not a design)',
          not lonely.get('ok')
          and 'no construction variants' in lonely['refusal'])


def main():
    selftest_upsert()
    selftest_arch2()
    selftest_arch3()
    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    raise SystemExit(main())
