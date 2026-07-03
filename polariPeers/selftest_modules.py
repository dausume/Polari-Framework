"""
Self-test for the Track-3 module system: bundle format, exporter closure
walk (over the REAL seed content), loader import/remove semantics.

Run from polari-framework/:
    python3 -m polariPeers.selftest_modules
"""

import json
from types import SimpleNamespace

# Importing multi_scale_seed chains the newtonian, wind, and material
# seeds — the shared SEED_* lists then hold the full sample content.
import simulations.multi_scale_seed  # noqa: F401  (in-place list extends)
from simulations.seed_data import (
    SEED_SIMULATION_DEFINITIONS, SEED_SIMULATION_RUNS,
    SEED_PENDULUM_STEP_SOLUTION_DEFS, SEED_PENDULUM_STEP_SOLUTIONS,
    SEED_PENDULUM_EQUATIONS, SEED_PENDULUM_STEP_EQUATIONS,
    SEED_PENDULUM_SIMSPACES, SEED_PENDULUM_BINDINGS,
    SEED_PENDULUM_EVALUATION_EQUATIONS, SEED_PENDULUM_STEP_TEST_CASES,
    SEED_PENDULUM_BOB_ROWS, SEED_PENDULUM_STRING_ROWS,
)
from simulations.newtonian_pendulum_seed import (
    SEED_NEWTON_BOB_ROWS, SEED_NEWTON_ROD_ROWS,
)
from simulations.wind_field_seed import (
    SEED_WIND_GRID_ROWS, SEED_SIMULATION_COUPLINGS,
    SEED_NEWTON_WIND_BOB_ROWS, SEED_NEWTON_WIND_ROD_ROWS,
)
from simulations.material_space_seed import SEED_MATERIAL_ROWS
from simulations.multi_scale_seed import (
    SEED_MULTI_SCALE_SIMS, SEED_IC_INTERFACES, SEED_MSIM_GRAPHS,
)
from matrices.seed_data import SEED_MATRICES, SEED_MATRIX_EQUATIONS
from simSpace3D.seed_data import SEED_MATERIALS_3D, SEED_MESHES_3D

# The real classes — the source manager's typing registry mirrors live.
from simulations.simulation_definition import SimulationDefinition
from simulations.simulation_run import SimulationRun
from simulations.simulation_execution_solution import SimulationExecutionSolution
from simulations.sim_space_evaluation_equation import SimSpaceEvaluationEquation
from simulations.newtonian_pendulum_bob_sim_state import NewtonianPendulumBobSimState
from simulations.newtonian_pendulum_viz_states import NewtonianPendulumRodSimState
from simulations.pendulum_bob_sim_state import PendulumBobSimState
from simulations.pendulum_string_sim_state import PendulumStringSimState
from simulations.wind_field_grid_sim_state import WindFieldGridState
from simulations.material_condensation_state import MaterialCondensationState
from simulations.simulation_coupling_definition import SimulationCouplingDefinition
from simulations.multi_scale_simulation_definition import MultiScaleSimulationDefinition
from simulations.initial_condition_interface_definition import (
    InitialConditionInterfaceDefinition,
)
from polariApiServer.equationDefinition import EquationDefinition
from polariApiServer.solutionDefinition import SolutionDefinition
from polariApiServer.solutionTestCase import SolutionTestCase
from polariApiServer.graphDefinition import GraphDefinition
from matrices.matrix_definition import MatrixDefinition
from matrices.matrix_equation_definition import MatrixEquationDefinition
from simSpace.sim_space_definition import SimSpaceDefinition
from simSpace.sim_space_binding_definition import SimSpaceBindingDefinition
from simSpace3D.material_3d_definition import Material3DDefinition
from simSpace3D.mesh_3d_definition import Mesh3DDefinition
from polariPeers.polari_module import PolariModule

from polariPeers.module_bundle import (
    canonical_json, class_fields_fingerprint, init_param_names,
)
from polariPeers.module_exporter import export_module, suggest_module_scopes
from polariPeers.module_loader import import_bundle, remove_module

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


_CLASSES = {
    'SimulationDefinition': SimulationDefinition,
    'SimulationRun': SimulationRun,
    'SimulationExecutionSolution': SimulationExecutionSolution,
    'SimSpaceEvaluationEquation': SimSpaceEvaluationEquation,
    'NewtonianPendulumBobSimState': NewtonianPendulumBobSimState,
    'NewtonianPendulumRodSimState': NewtonianPendulumRodSimState,
    'PendulumBobSimState': PendulumBobSimState,
    'PendulumStringSimState': PendulumStringSimState,
    'WindFieldGridState': WindFieldGridState,
    'MaterialCondensationState': MaterialCondensationState,
    'SimulationCouplingDefinition': SimulationCouplingDefinition,
    'MultiScaleSimulationDefinition': MultiScaleSimulationDefinition,
    'InitialConditionInterfaceDefinition': InitialConditionInterfaceDefinition,
    'EquationDefinition': EquationDefinition,
    'SolutionDefinition': SolutionDefinition,
    'SolutionTestCase': SolutionTestCase,
    'GraphDefinition': GraphDefinition,
    'MatrixDefinition': MatrixDefinition,
    'MatrixEquationDefinition': MatrixEquationDefinition,
    'SimSpaceDefinition': SimSpaceDefinition,
    'SimSpaceBindingDefinition': SimSpaceBindingDefinition,
    'Material3DDefinition': Material3DDefinition,
    'Mesh3DDefinition': Mesh3DDefinition,
    'PolariModule': PolariModule,
}

_SEED_TABLES = {
    'SimulationDefinition': SEED_SIMULATION_DEFINITIONS,
    'SimulationRun': SEED_SIMULATION_RUNS,
    'SolutionDefinition': SEED_PENDULUM_STEP_SOLUTION_DEFS,
    'SimulationExecutionSolution': SEED_PENDULUM_STEP_SOLUTIONS,
    'EquationDefinition': SEED_PENDULUM_EQUATIONS + SEED_PENDULUM_STEP_EQUATIONS,
    'MatrixDefinition': SEED_MATRICES,
    'MatrixEquationDefinition': SEED_MATRIX_EQUATIONS,
    'SimSpaceDefinition': SEED_PENDULUM_SIMSPACES,
    'SimSpaceBindingDefinition': SEED_PENDULUM_BINDINGS,
    'SimSpaceEvaluationEquation': SEED_PENDULUM_EVALUATION_EQUATIONS,
    'SolutionTestCase': SEED_PENDULUM_STEP_TEST_CASES,
    'Material3DDefinition': SEED_MATERIALS_3D,
    'Mesh3DDefinition': SEED_MESHES_3D,
    'WindFieldGridState': SEED_WIND_GRID_ROWS,
    'MaterialCondensationState': SEED_MATERIAL_ROWS,
    'NewtonianPendulumBobSimState': SEED_NEWTON_BOB_ROWS + SEED_NEWTON_WIND_BOB_ROWS,
    'NewtonianPendulumRodSimState': SEED_NEWTON_ROD_ROWS + SEED_NEWTON_WIND_ROD_ROWS,
    'PendulumBobSimState': SEED_PENDULUM_BOB_ROWS,
    'PendulumStringSimState': SEED_PENDULUM_STRING_ROWS,
    'MultiScaleSimulationDefinition': SEED_MULTI_SCALE_SIMS,
    'InitialConditionInterfaceDefinition': SEED_IC_INTERFACES,
    'SimulationCouplingDefinition': SEED_SIMULATION_COUPLINGS,
    'GraphDefinition': SEED_MSIM_GRAPHS,
}


def _source_manager():
    """A fake manager mirroring the live one: real classes in the typing
    registry, seed dicts as rows."""
    m = SimpleNamespace(objectTables={}, objectTypingDict={}, db=None)
    for cls_name, klass in _CLASSES.items():
        m.objectTypingDict[cls_name] = SimpleNamespace(classDefinition=klass)
    for cls_name, seeds in _SEED_TABLES.items():
        m.objectTables[cls_name] = {
            s['name']: SimpleNamespace(**s) for s in seeds
        }
    m.objectTables['PolariModule'] = {}
    m.objectTables['PeerNode'] = {}
    return m


def _twin_class(real_cls, drop=()):
    """A constructible stand-in with the SAME __init__ field set as the
    real class (identical fingerprint) that tolerates a fake manager."""
    params = [p for p in init_param_names(real_cls) if p not in drop]
    args = ', '.join(f'{p}=None' for p in params)
    body = '\n'.join(f'    self.{p} = {p}' for p in params) or '    pass'
    ns = {}
    exec(f'def __init__(self, {args}, manager=None):\n{body}', ns)
    return type(real_cls.__name__, (), {'__init__': ns['__init__']})


def _target_manager(mismatch_class=None, drop=()):
    """An empty fake instance whose classes fingerprint-match the source
    (except `mismatch_class`, built without the `drop` fields)."""
    m = SimpleNamespace(objectTables={}, objectTypingDict={}, db=None)
    for cls_name, klass in _CLASSES.items():
        d = drop if cls_name == mismatch_class else ()
        m.objectTypingDict[cls_name] = SimpleNamespace(
            classDefinition=_twin_class(klass, drop=d))
    return m


def _names(bundle, cls):
    return {r.get('name') for r in bundle['objects'].get(cls, [])}


def _export(mgr, name):
    scope = next(s for s in suggest_module_scopes(mgr) if s['name'] == name)
    return export_module(mgr, scope)


def _exporter():
    print('Modules — exporter closure walk (real seed content)\n')
    m = _source_manager()

    scopes = suggest_module_scopes(m)
    by_name = {s['name']: s for s in scopes}
    check('suggested scopes: the natural 4-way partition',
          set(by_name) == {'pendulum-core', 'wind-space', 'material-space',
                           'pendulum-in-wind-composition'},
          f'scopes={sorted(by_name)}')
    check('composition depends on the three space modules',
          set(by_name['pendulum-in-wind-composition']['dependsOn'])
          == {'pendulum-core', 'wind-space', 'material-space'})

    wind = _export(m, 'wind-space')
    check('wind-space closure: sim def + step solution + wrapper',
          'wind-field-3d' in _names(wind, 'SimulationDefinition')
          and 'wind-field-3d.grid.evolve' in _names(wind, 'SolutionDefinition')
          and 'wind-field-3d.grid.evolve'
          in _names(wind, 'SimulationExecutionSolution'))
    check('wind-space closure: graph-referenced matrix equation + template '
          'run + step-0 grid row',
          'wind-field-evolve' in _names(wind, 'MatrixEquationDefinition')
          and 'wind-field-run' in _names(wind, 'SimulationRun')
          and len(wind['objects'].get('WindFieldGridState', [])) == 1)
    check('wind-space closure: scene bindings + referenced 3D material',
          'WindFieldGridState-3d' in _names(wind, 'SimSpaceBindingDefinition')
          and 'arrow-wind' in _names(wind, 'Material3DDefinition'))
    fp = wind['manifest']['requiredClasses'].get('WindFieldGridState', '')
    check('requiredClasses carries a 16-hex fields fingerprint',
          len(fp) == 16 and int(fp, 16) >= 0,
          f'fp={fp}')
    check('fingerprint matches the real class',
          fp == class_fields_fingerprint(WindFieldGridState))

    again = _export(m, 'wind-space')
    check('version is a stable content hash (re-export identical)',
          wind['manifest']['version'] == again['manifest']['version']
          and canonical_json(wind) == canonical_json(again),
          f"v={wind['manifest']['version']}")

    comp = _export(m, 'pendulum-in-wind-composition')
    check('composition bundle: msim + coupling + picker + gate solution',
          'pendulum-in-wind' in _names(comp, 'MultiScaleSimulationDefinition')
          and 'wind-to-newtonian-pendulum'
          in _names(comp, 'SimulationCouplingDefinition')
          and 'bob-material-picker'
          in _names(comp, 'InitialConditionInterfaceDefinition')
          and 'solid-ball-achievable' in _names(comp, 'SolutionDefinition'))
    check('composition excludes its dependencies\' content (no sim defs, '
          'no evolve solution)',
          not _names(comp, 'SimulationDefinition')
          and 'wind-field-3d.grid.evolve'
          not in _names(comp, 'SolutionDefinition'))
    check('composition still REQUIRES the coupled classes',
          {'NewtonianPendulumBobSimState', 'WindFieldGridState'}
          <= set(comp['manifest']['requiredClasses']))
    return m, wind, comp


def _loader(source_mgr, wind, comp):
    print('\nModules — loader import/remove semantics\n')

    target = _target_manager()
    report = import_bundle(source_mgr and target, wind, source_kind='peer',
                           source_ref='a:wind-space')
    created_total = sum(report['created'].values())
    check('import into an empty instance creates everything, no errors',
          report['installed'] and not report['errors'] and created_total > 5,
          f'created={created_total}')
    check('module registered as installed with the cached bundle',
          any(getattr(r, 'status', '') == 'installed'
              and getattr(r, 'bundle_json', '')
              for r in target.objectTables.get('PolariModule', {}).values()))

    again = import_bundle(target, wind)
    check('re-import is idempotent (all skipped, none created)',
          sum(again['created'].values()) == 0
          and sum(again['skipped'].values()) == created_total)

    dry_target = _target_manager()
    dry = import_bundle(dry_target, wind, dry_run=True)
    check('dry run reports what WOULD be created and touches nothing',
          dry['dryRun'] and sum(dry['created'].values()) == created_total
          and not dry_target.objectTables.get('SimulationDefinition')
          and not dry_target.objectTables.get('PolariModule'))

    mismatch = _target_manager(mismatch_class='WindFieldGridState',
                               drop=('cells_json',))
    bad = import_bundle(mismatch, wind)
    check('a mismatched class version refuses with a plain explanation',
          not bad['installed']
          and any('DIFFERENT version' in e for e in bad['errors']))

    deps_target = _target_manager()
    dep_report = import_bundle(deps_target, comp)
    check('missing dependencies warn (plainly) but do not block',
          dep_report['installed']
          and any('depends on' in w for w in dep_report['warnings']),
          f"warnings={len(dep_report['warnings'])}")

    removal = remove_module(target, 'wind-space')
    check('remove_module empties the module\'s objects and reports the '
          'DB-delete gap honestly',
          removal['removed']
          and sum(removal['removedCounts'].values()) == created_total
          and any('reappear after' in w for w in removal['warnings'])
          and not target.objectTables.get('SimulationDefinition'))


if __name__ == '__main__':
    m, wind, comp = _exporter()
    _loader(m, wind, comp)
    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
