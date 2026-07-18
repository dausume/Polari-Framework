"""
Selftest — ncg-7: the ncg levels as POLARI MODULE OBJECTS.

Run from polari-framework/:
    python3 -m polariPeers.selftest_ncg_modules

Dustin's definition of modularization, proven end-to-end: a level's
content EXPORTS as a bundle (a PolariModule object that can be
stored away), and DYNAMICALLY LOADS into an already-running instance
— import_bundle seeds the rows, the level WORKS on the target (the
loaded logic design evaluates through the reference simulator), the
PolariModule row records the install, and remove_module takes it
back out. Plus the closure builders: each ncg scope must carry
everything its level needs (nodes with designs, components+devices
with circuits, criteria+edges with procedures, cases with packs).
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from hwdigital.logic_basis import (LogicBlockDesign, LogicBlockNode,
                                   SEED_LOGIC_DESIGNS,
                                   SEED_LOGIC_NODES)
from polariPeers import ncg_module_scopes as ns
from polariPeers.module_exporter import export_module
from polariPeers.module_loader import import_bundle, remove_module

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


_CLASSES = {'LogicBlockDesign': LogicBlockDesign,
            'LogicBlockNode': LogicBlockNode}


def _manager(with_rows):
    """A live-shaped manager: real classes in the typing registry
    (fingerprints must match across instances), idList for
    treeObjectInit when the loader constructs rows."""
    m = SimpleNamespace(objectTables={}, objectTypingDict={},
                        idList=[], db=None)
    for cls_name, klass in _CLASSES.items():
        m.objectTypingDict[cls_name] = SimpleNamespace(
            classDefinition=klass)
        m.objectTables[cls_name] = {}
    m.objectTables['PolariModule'] = {}
    if with_rows:
        for seed in SEED_LOGIC_DESIGNS:
            m.objectTables['LogicBlockDesign'][seed['name']] = (
                SimpleNamespace(**seed))
        for seed in SEED_LOGIC_NODES:
            m.objectTables['LogicBlockNode'][seed['name']] = (
                SimpleNamespace(**seed))
    return m


def _closures():
    print('closure builders (a scope carries everything its level '
          'needs)')
    m = _manager(with_rows=True)
    scope = ns.logic_design_scope(m, ['demo-counter2'])
    check('a design scope pulls exactly its nodes',
          scope['classRows']['LogicBlockNode']
          == ['cnt2-counter', 'cnt2-en', 'cnt2-q'])
    suggestions = ns.suggest_ncg_module_scopes(m)
    check('suggestions offer the hwdigital level',
          any(s['name'] == 'hwdigital-level' for s in suggestions))

    jm = SimpleNamespace(objectTables={
        'LogicForkCriterion': {1: SimpleNamespace(
            name='crit-a', decision_procedure_name='demo-proc')},
        'DecisionProcedureEdge': {1: SimpleNamespace(
            name='edge-a', decision_procedure_name='demo-proc')},
        'LogicForkVote': {}, 'LogicForkBallot': {}})
    scope = ns.procedure_scope(jm, 'demo-proc')
    check('a procedure scope carries criteria + edges',
          scope['classRows'] == {'LogicForkCriterion': ['crit-a'],
                                 'DecisionProcedureEdge': ['edge-a']})

    cm = SimpleNamespace(objectTables={
        'CircuitDefinition': {1: SimpleNamespace(name='c1')},
        'CircuitNetDefinition': {},
        'CircuitComponentDefinition': {1: SimpleNamespace(
            name='x1', circuit_name='c1', kind='device',
            device_name='dev-a')},
        'ElectronicDeviceDefinition': {1: SimpleNamespace(
            name='dev-a')},
        'SpiceModelCard': {1: SimpleNamespace(
            name='card-1', device_name='dev-a')}})
    scope = ns.circuit_scope(cm, ['c1'])
    check('a circuit scope pulls its device + card closure',
          scope['classRows'].get('ElectronicDeviceDefinition')
          == ['dev-a']
          and scope['classRows'].get('SpiceModelCard') == ['card-1'])


def _round_trip():
    print('export -> store -> dynamic load into a running instance')
    source = _manager(with_rows=True)
    bundle = export_module(
        source, ns.logic_design_scope(source, ['demo-counter2'],
                                      name='hwdigital-counter'))
    manifest = bundle['manifest']
    check('bundle manifest: named, fingerprinted, counted',
          manifest['name'] == 'hwdigital-counter'
          and set(manifest['requiredClasses'])
          == {'LogicBlockDesign', 'LogicBlockNode'}
          and manifest['objectCounts']['LogicBlockNode'] == 3)

    target = _manager(with_rows=False)
    dry = import_bundle(target, bundle, dry_run=True)
    check('dry run previews without seeding',
          not dry['installed']
          and not target.objectTables['LogicBlockDesign'])
    report = import_bundle(target, bundle, source_kind='peer',
                           source_ref='selftest')
    check('bundle loads into the RUNNING target instance',
          report['installed']
          and report['created'].get('LogicBlockNode') == 3
          and not report['errors'])

    from hwdigital.logic_sim import LogicSimulator, design_specs
    specs = design_specs(target, 'demo-counter2')
    sim = LogicSimulator(specs)
    sim.set_inputs(**{'cnt2-en': 1})
    sim.step()
    sim.step()
    check('the LOADED design runs on the target (counter counts)',
          sim.outputs()['cnt2-q'] == 2)

    module_rows = list(target.objectTables['PolariModule'].values())
    check('a PolariModule row records the install (the module IS '
          'an object)',
          len(module_rows) == 1
          and getattr(module_rows[0], 'status', '') == 'installed'
          and getattr(module_rows[0], 'source_kind', '') == 'peer')

    again = import_bundle(target, bundle)
    check('re-install is idempotent (skips by name)',
          again['installed']
          and again['skipped'].get('LogicBlockNode') == 3
          and sum(again['created'].values()) == 0)

    removed = remove_module(target, 'hwdigital-counter')
    check('remove_module takes the level back out',
          removed.get('removed')
          and not target.objectTables['LogicBlockDesign'])


def main():
    _closures()
    _round_trip()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
