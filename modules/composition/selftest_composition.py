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
        'RoutingDefinition': table(cs.SEED_ROUTINGS),
        'RoutingOperation': table(cs.SEED_ROUTING_OPS),
        'DesignMatrixDefinition': table(cs.SEED_DESIGN_MATRICES),
        'PartArchetypeDefinition': table(cs.SEED_PART_ARCHETYPES),
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
          len(reports) == 10
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


# ---------------------------------------------------------------
# arch-4: routings — derived step counts, audited promotion
# ---------------------------------------------------------------

def selftest_arch4():
    import json
    import types as _t

    from composition.routing_basis import (
        audit_promotion, routing_report, variant_step_counts,
    )

    print('\n-- arch-4: routings + the promotion record --')
    m = _seed_mgr()

    counts = variant_step_counts(m, 'fp-m0-stator')
    by = {v['variant']: v for v in counts['variants']}
    check('step counts 1 / 3 / 4 DERIVE from routings (mag-26 cost '
          'axis)',
          by['cv-stator-simple']['stepCount'] == 1
          and by['cv-stator-bound']['stepCount'] == 3
          and by['cv-stator-layered-bound']['stepCount'] == 4)
    check('layered routing is per LAYER; every routing admissible '
          '(all rungs stated)',
          by['cv-stator-layered-bound']['perUnit'] == 'layer'
          and all(v['admissible'] for v in counts['variants']))
    check('promote steps identified per routing',
          by['cv-stator-bound']['promoteSteps'] == ['op-bound-cure']
          and by['cv-stator-layered-bound']['promoteSteps']
          == ['op-layer-bind'])

    # THE promotion audit: the bound-stator record is complete.
    audit = audit_promotion(m, 'op-bound-cure')
    check('bound-stator promotion audits CLEAN', audit['ok'],
          str(audit.get('problems')))
    check('it deletes exactly what the consumed interface carried',
          audit['modesDeleted'] == ['fm-fretting',
                                    'fm-turn-to-turn-abrasion'])
    check('it names genealogy, spent repairability and the '
          'qualifying act',
          audit['genealogySource'] == 'stator-simple'
          and 'ONE life' in audit['reversibilitySpent']
          and '3 mm former' in audit['qualifyingAct'])
    check('per-layer promotion audits clean (partial promotion)',
          audit_promotion(m, 'op-layer-bind')['ok'])

    # Refusals.
    check('auditing a non-promote op refuses',
          not audit_promotion(m, 'op-simple-wind').get('ok'))
    # The DFA gate: fusing the snap interface must REFUSE — its
    # members must separate for service (per-layer inspectability
    # is the whole point of the snap).
    m2 = _seed_mgr()
    m2.objectTables['RoutingOperation']['op-bad-fuse-snap'] = \
        _t.SimpleNamespace(
            name='op-bad-fuse-snap', routing_ref='rt-stator-layered',
            sequence=9, kind='promote',
            consumes_interface_refs_json='[]',
            fused_interface_refs_json=json.dumps(['if-layer-snap']),
            emits_node_ref='stator-layered',
            modes_deleted_refs_json='[]',
            modes_introduced_refs_json='[]',
            reversibility_spent='claims none',
            dfa_justification_json=json.dumps({
                'if-layer-snap': {
                    'moves_relative': False,
                    'different_material': False,
                    'separable_for_service': True,
                    'why': 'layers must come apart for per-layer '
                           'inspection and discard'}}),
            qualifying_act='n/a')
    bad = audit_promotion(m2, 'op-bad-fuse-snap')
    check('DFA gate REFUSES fusing the snap (separable-for-service)',
          not bad['ok']
          and any('SEPARATE for service' in p
                  for p in bad['problems']))
    check('and the contradiction is caught structurally too '
          '(fusing a separable-marked interface)',
          any('designed_separable=True' in p
              for p in bad['problems']))
    # A promotion that hides a mode the consumed interface carried
    # is caught.
    m3 = _seed_mgr()
    m3.objectTables['RoutingOperation']['op-bound-cure']\
        .modes_deleted_refs_json = json.dumps(['fm-fretting'])
    hid = audit_promotion(m3, 'op-bound-cure')
    check('a promotion that under-reports deleted modes is caught',
          not hid['ok']
          and any('fm-turn-to-turn-abrasion' in p
                  for p in hid['problems']))
    # A routing with an unstated rung is inadmissible, loudly.
    m4 = _seed_mgr()
    m4.objectTables['RoutingOperation']['op-simple-wind']\
        .capability_rung_ref = ''
    inadm = routing_report(m4, 'rt-stator-simple')
    check('unstated capability rung -> routing INADMISSIBLE '
          '(the mag-22 lesson)',
          inadm['ok'] and inadm['admissible'] is False
          and 'INADMISSIBLE' in inadm['admissibilityNote'])
    check('empty routing refuses',
          not routing_report(_seed_mgr(), 'rt-nonexistent').get('ok'))


# ---------------------------------------------------------------
# arch-5: archetypes + design matrices
# ---------------------------------------------------------------

def selftest_arch5():
    import json

    from composition.archetype_basis import archetype_report
    from composition.design_matrix import classify, matrix_report
    import composition.composition_seed as cs

    print('\n-- arch-5: design matrices (cancellation as data) --')
    m = _seed_mgr()

    # THE acceptance: the M0 derives DECOUPLED with the tuning
    # order gauge → window → turns.
    m0 = matrix_report(m, 'dm-coil-winding')
    check('M0 matrix derives DECOUPLED (not uncoupled — turns '
          'depend on gauge via A_wound)',
          m0.get('ok') and m0['classification'] == 'decoupled')
    check('tuning order derives gauge → window → turns',
          m0['tuningOrder'] == ['gauge', 'window', 'turns'])
    check('the voltage cancellation is on the record (turns '
          'cancel)',
          any('TURNS CANCEL' in e.get('via', '')
              for e in m0['entries']))

    # The Lavet ratio trap surfaces as a finding.
    lavet = matrix_report(m, 'dm-lavet-magnet')
    traps = [f for f in lavet['findings']
             if f['kind'] == 'ratio-trap']
    check('remanence ratio-trap surfaces as a FINDING '
          '(stronger magnet ≠ better motor)',
          len(traps) == 1 and traps[0]['knob'] == 'remanence'
          and 'NOT' in traps[0]['warning'])

    # Toy matrices pin the classifier itself.
    check('diagonal matrix classifies UNCOUPLED',
          classify([{'knob': 'a', 'outcome': 'x',
                     'coupling': 'direct'},
                    {'knob': 'b', 'outcome': 'y',
                     'coupling': 'direct'}])['classification']
          == 'uncoupled')
    full = classify([{'knob': 'a', 'outcome': 'x',
                      'coupling': 'direct'},
                     {'knob': 'b', 'outcome': 'x',
                      'coupling': 'direct'},
                     {'knob': 'a', 'outcome': 'y',
                      'coupling': 'direct'},
                     {'knob': 'b', 'outcome': 'y',
                      'coupling': 'inverse'}])
    check('full matrix classifies COUPLED with the block named as '
          'a finding',
          full['classification'] == 'coupled'
          and sorted(full['coupledOutcomes']) == ['x', 'y']
          and any(f['kind'] == 'coupled-block'
                  for f in full['findings']))
    check('empty and malformed matrices refuse',
          not classify([])['ok']
          and not classify([{'knob': 'a', 'outcome': 'x',
                             'coupling': 'sideways'}])['ok'])

    print('\n-- arch-5: archetypes (the machine-elements join) --')
    rep = archetype_report(m, 'at-coil-winding')
    check('coil archetype joins roles + levelled equations + '
          'matrix + failure modes',
          rep['ok']
          and [r['role'] for r in rep['roles']]
          == ['current-carrying', 'static-structural']
          and len(rep['equationsByLevel'].get('part', [])) == 6
          and 'eq-coil-voltage-gauge'
          in rep['equationsByLevel']['part']
          and rep['designMatrix']['classification'] == 'decoupled')
    check('selection procedure step 2 checks voltage BEFORE '
          'optimisation (the mag-22 fix, as data)',
          'BEFORE optimising' in
          rep['selectionProcedure'][1]['what'])
    all_ok = [archetype_report(m, s['name'])
              for s in cs.SEED_PART_ARCHETYPES]
    check('all five archetype seeds report clean',
          len(all_ok) == 5 and all(r['ok'] for r in all_ok),
          str([r['problems'] for r in all_ok if not r['ok']]))
    check('an archetype without a matrix says so honestly '
          '(folklore, not data)',
          'folklore' in archetype_report(m, 'at-bobbin')
          ['designMatrix']['refusal'])
    # Cross-module agreement (the mag-25 lesson, again).
    from motors.physics_equations import SEED_PHYSICS_EQUATIONS
    eq_names = {e['name'] for e in SEED_PHYSICS_EQUATIONS}
    cited = {e['name'] for s in cs.SEED_PART_ARCHETYPES
             for e in json.loads(s['equation_refs_json'])}
    check('every archetype equation ref exists in '
          'physics_equations',
          cited and cited <= eq_names,
          f'missing: {cited - eq_names}')
    # A stale role name is a problem, not a silence.
    import types as _t
    m2 = _seed_mgr()
    m2.objectTables['PartArchetypeDefinition']['at-bad'] = \
        _t.SimpleNamespace(
            name='at-bad', summary='', parameter_set_json='[]',
            equation_refs_json='[]', failure_mode_refs_json='[]',
            role_refs_json=json.dumps(['no-such-role']),
            selection_procedure_json='[]', design_matrix_ref='')
    check('unknown role on an archetype is a named problem',
          not archetype_report(m2, 'at-bad')['ok'])


# ---------------------------------------------------------------
# arch-6: derived realization + the condition key
# ---------------------------------------------------------------

def selftest_arch6():
    import json

    from composition.data_refs import material_prop
    from composition.realization import (
        REALIZATION_LEVELS, node_realization,
    )

    print('\n-- arch-6: realization rolls up, derived --')
    # Two modules assert the same ladder — test that they agree.
    from magnetics.magnet_basis import (
        REALIZATION_LEVELS as MAG_LEVELS,
    )
    check('composition and magnetics agree on the realization '
          'ladder',
          tuple(REALIZATION_LEVELS) == tuple(MAG_LEVELS))

    m = _seed_mgr()
    from magnetics.magnet_seed import SEED_MATERIAL_OPTIONS
    m.objectTables['MagneticMaterialOption'] = {
        s['name']: types.SimpleNamespace(**s)
        for s in SEED_MATERIAL_OPTIONS}
    simple = node_realization(m, 'stator-simple')
    check('simple stator floor = recipe-seeded, limited by the '
          'FIRED CERAMIC spool (copper wire is made-and-measured)',
          simple.get('ok') and simple['level'] == 'recipe-seeded'
          and any(c.get('material') == 'opt-fired-ceramic'
                  for c in simple['limitedBy']))
    layered = node_realization(m, 'stator-layered')
    check('layered stator floor = THEORETICAL, limited by its '
          'unbuilt interfaces (IRL: the interface is what has not '
          'been demonstrated)',
          layered['level'] == 'theoretical'
          and all(c['kind'] == 'interface'
                  for c in layered['limitedBy']))
    check('the limiting interface names its advancing act',
          'measure' in layered['nextAct']
          or 'fill' in layered['nextAct'])
    # A missing material is unassessed, never the floor.
    m2 = _seed_mgr()  # no MagneticMaterialOption table at all
    gap = node_realization(m2, 'stator-simple')
    check('unresolvable material -> level UNASSESSED with the gap '
          'named (never a silent floor)',
          gap['level'] == 'unassessed' and gap['unassessed'])

    print('\n-- arch-6: material condition is a KEY --')
    mm = types.SimpleNamespace(objectTables={
        'MagneticMaterialOption': {'cu': types.SimpleNamespace(
            name='cu',
            properties_json=json.dumps({
                'tensile_mpa': {'conditions': {
                    'drawn': {'value': 380.0,
                              'provenance': 'literature-est'},
                    'annealed': {'value': 210.0,
                                 'provenance': 'literature-est'}}},
                'sigma_s_m': {'value': 5.96e7,
                              'provenance': 'literature-est'}}))}},
        objectTypingDict={'MagneticMaterialOption': object()})
    check('stated condition selects its own property row '
          '(drawn 380 vs annealed 210)',
          material_prop(mm, 'cu', 'tensile_mpa', 'drawn')[0] == 380.0
          and material_prop(mm, 'cu', 'tensile_mpa',
                            'annealed')[0] == 210.0)
    check('UNSTATED condition on a condition-dependent property is '
          'unassessed, not the headline value',
          material_prop(mm, 'cu', 'tensile_mpa')[0] is None)
    check('condition-independent properties answer regardless',
          material_prop(mm, 'cu', 'sigma_s_m',
                        'drawn')[0] == 5.96e7)


def main():
    selftest_upsert()
    selftest_arch2()
    selftest_arch3()
    selftest_arch4()
    selftest_arch5()
    selftest_arch6()
    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    raise SystemExit(main())
