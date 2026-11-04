"""
@module mech.mech_analysis_seed

The mech engines REGISTERED as rows (his rule, 2026-11-03: no custom APIs
— "polari fully automates away api creation so long as functionality and
engines are wrapped by polari properly"):

  AnalysisDefinition  one per engine entry point, callable_ref →
                      mech.custom.analyses.<fn> (fn(manager, **params)
                      -> dict), params documented for the editor
  SolutionDefinition  one DirectInvocation → AnalysisCall → ReturnValue
                      graph per analysis, so each engine is runnable
                      through the generic solution-execution routes and
                      composable as a SolutionInvocation step in any
                      other no-code solution (the vpn_seed pattern)

Nothing here computes; the rows are the knobs (enabled = False refuses
plainly). Pairs ride MECH_SEED_PAIRS (mech_motion_seed) at the end, after
the rows the analyses read.

@consumers polariServer (seed pairs), mech.mech_analysis_selftest,
  SolutionExecutionEngine (AnalysisCall / SolutionInvocation)
"""
import json

from polariNoCode import graph_builder as gb

PROV = 'mxc-api'
_MOD = 'mech.custom.analyses'


def _analysis(name, fn, description, params):
    return {'name': name, 'domain': 'mech', 'callable_ref': f'{_MOD}:{fn}',
            'description': description, 'params_json': json.dumps(params),
            'enabled': True, 'is_prior': True, 'provenance_id': PROV, 'notes': ''}


#: name → (callable, description, {param: meaning})
_ANALYSES = [
    ('mech-catalogue-family', 'catalogue_family',
     'The part catalogue: every MechPartFamily with its variant count, or one family with its variants (mxc-1).',
     {'family': "MechPartFamily name ('' = the list)"}),
    ('mech-catalogue-variant', 'catalogue_variant',
     'One MechPartVariant with its MechFeature rows (threads, slots, grid cells, bores, faces).',
     {'variant': 'MechPartVariant name, e.g. iso4762-M5x10'}),
    ('mech-pairing', 'pairing',
     'Can feature A of variant A mate with feature B of variant B: key match + role pairing (male/female, rider/channel, '
     'cell/cell) + the advisory thread-engagement knob (1·d steel / 2·d aluminium / 2.5·d plastic).',
     {'variant_a': 'MechPartVariant', 'feature_a': 'feature tag or full name', 'variant_b': 'MechPartVariant',
      'feature_b': 'feature tag or full name'}),
    ('mech-pairings', 'pairings',
     'Every catalogue variant/feature that mates with each feature of one variant.',
     {'variant': 'MechPartVariant name'}),
    ('mech-material-preference', 'material_preference',
     "A part category's default / alternative / legacy materials: each default checked through composition's "
     'role_viability against its MechMaterialOption properties, the legacy ones with their IARC reasons (D-mxc-9).',
     {'preference': 'MechMaterialPreference name, e.g. deep_groove_ball_bearing'}),
    ('mech-assembly-dof', 'assembly_dof',
     'Free DOF per instance, assembly mobility, under-/over-constrained bodies — a Grübler COUNT in each joint frame, '
     'not a rank test; the note names what it cannot catch (mxc-2).',
     {'assembly': 'MechAssembly name, e.g. mfx-1'}),
    ('mech-assembly-check', 'assembly_check',
     'Every fit check over one assembly (thread engagement, ISO 273 clearance, slot/T-nut pairing, grid occupancy, '
     'drawer cantilever vs slide rating) + the DOF count → MechConflict dicts.',
     {'assembly': 'MechAssembly name'}),
    ('mech-motion-run', 'motion_run',
     "Run a MechMotionCase under a MechLoadCase on Polari's 1-DOF engine (linear or rotary; stick/slip friction, "
     'hard stops, detent): lands MechMotionRun + SimulationRun + MechMotionSimState + MechMotionVector rows; returns '
     'the report with every check and its number and the inputs_sha256 (D-mxc-11).',
     {'motion_case': 'MechMotionCase name', 'load_case': "MechLoadCase name ('' = first on the same assembly)",
      'fem_model': "FEMModelDefinition name for the structural check ('' = none; materialsScience runs it, D-mxc-7)"}),
    ('mech-freecad-compare', 'freecad_compare',
     "A run's position(t) against a FreeCAD Motion CSV (default: the mfx-0 reference recorded on econ, FreeCAD 1.1.4); "
     'frame 0 (pre-motion placement) is reported, never compared.',
     {'run': 'MechMotionRun name', 'csv': "CSV path ('' = the reference)", 'tol_mm': 'tolerance, default 0.1'}),
]

SEED_MECH_ANALYSES = [_analysis(n, fn, d, p) for n, fn, d, p in _ANALYSES]


def _solution(analysis_name, params, description):
    """DirectInvocation → AnalysisCall → ReturnValue: the analysis as a
    runnable, composable no-code solution. Input params flow in by name."""
    name = analysis_name.replace('mech-', 'mech-run-')
    graph = gb.solution(
        name,
        gb.node('Start', 'DirectInvocation', {}, outs=[['Call']]),
        gb.node('Call', 'AnalysisCall',
                {'analysis': analysis_name,
                 'params': {p: gb.var_src(p) for p in params},
                 'resultVariable': 'result'},
                outs=[['Return']]),
        gb.ret('Return', 'result'),
    )
    return {'name': name, 'function_name': name.replace('-', '_'),
            'target_runtime': 'python_backend', 'definition': json.dumps(graph),
            'contract_json': json.dumps({
                'description': description,
                'inputs': [{'name': p, 'required': False, 'description': meaning}
                           for p, meaning in params.items()],
                'returns': [{'name': 'result', 'description': 'the analysis dict (ok, …, _analysis provenance)'}],
                'executionRights': 'invoker'}),
            'category': ''}


SEED_MECH_SOLUTIONS = [_solution(n, p, d) for n, fn, d, p in _ANALYSES]


def mech_analysis_seed_pairs():
    from polariApiServer.solutionDefinition import SolutionDefinition
    from polariNoCode.analysis_calls import AnalysisDefinition
    return [('AnalysisDefinition', AnalysisDefinition, SEED_MECH_ANALYSES),
            ('SolutionDefinition', SolutionDefinition, SEED_MECH_SOLUTIONS)]
