"""
@module simulationLocks.advisor_stages

xsim-5: static write-set extraction over MultiScaleSimulationDefinition
stages — what each stage WILL write, expressed in the lock/advisor
selector vocabulary (id|name|range|class-wide). Facts (seam survey
2026-07-11):

- search-family stages write attempt SimulationRun rows named
  `<msim>-<stageKey>[-tag]-attempt-<idx>` and per-class state rows
  named `<run>-<role>-<step>` — ALL prefixed `<msim>-<stageKey>-`, so
  one range selector [prefix, prefix~] covers a whole fan-out (the
  100k-sweep-is-one-lock-row property) and distinct stages are
  PROVABLY disjoint.
- formulationSearch writes FormulationSearchRun + candidate rows
  prefixed `<searchName>-run-`.
- engineModel MUTATES A SHARED ROW: the FEM/DFT/MD/Meso model
  definition named by modelRef (last_result_json overwritten per
  execution) — the genuine overlap hazard when reused across stages
  or nested subModels.
- subModel's write-set is the UNION of its child msim's stage sets
  (recursive, cycle-guarded).
- an unresolvable ref is a DYNAMIC item: cannot prove disjoint,
  reported conservatively — never silence.
"""

import json
from typing import Dict, List

from simulationLocks.overlap_advisor import analyze_branches

_MAX_SUBMODEL_DEPTH = 4

_MODEL_TABLES = ('FEMModelDefinition', 'DFTModelDefinition',
                 'MDModelDefinition', 'MesoModelDefinition')


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {}) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)


def _find_by_name(manager, class_name, name):
    return next((r for r in _rows(manager, class_name)
                 if getattr(r, 'name', '') == name), None)


def _prefix_range(prefix: str) -> Dict:
    """Lexicographic cover of every name starting with `prefix`
    ('~' sorts above all name characters in use)."""
    return {'kind': 'range', 'value': json.dumps(
        {'lo': prefix, 'hi': prefix + '~'})}


def _attempt_items(manager, msim_name: str, stage: Dict) -> List[Dict]:
    prefix = f"{msim_name}-{stage.get('key', '')}-"
    items = [{'className': 'SimulationRun',
              'selector': _prefix_range(prefix)}]
    sim_ref = stage.get('simulationRef') \
        or stage.get('primarySimulationRef') or ''
    sim_def = _find_by_name(manager, 'SimulationDefinition', sim_ref)
    if sim_def is None:
        if sim_ref:
            items.append({'className': 'SimulationDefinition',
                          'selector': {'kind': 'name',
                                       'value': sim_ref},
                          'dynamic': True})
        return items
    try:
        state_classes = json.loads(getattr(
            sim_def, 'participating_sim_state_classes_json', '')
            or '[]')
    except (TypeError, ValueError):
        state_classes = []
    for cls in state_classes or []:
        items.append({'className': str(cls),
                      'selector': _prefix_range(prefix)})
    return items


def stage_write_set(manager, msim_name: str, stage: Dict,
                    depth: int = 0, seen_msims=None) -> List[Dict]:
    kind = stage.get('kind', '')
    if kind == 'formulationSearch':
        search_ref = stage.get('formulationSearchRef', '')
        if not _find_by_name(manager, 'FormulationSearchDefinition',
                             search_ref):
            return [{'className': 'FormulationSearchDefinition',
                     'selector': {'kind': 'name', 'value': search_ref},
                     'dynamic': True}]
        prefix = f'{search_ref}-run-'
        return [{'className': 'FormulationSearchRun',
                 'selector': _prefix_range(prefix)},
                {'className': 'FormulationCandidateResult',
                 'selector': _prefix_range(prefix)}]
    if kind == 'engineModel':
        model_ref = stage.get('modelRef', '')
        for table in _MODEL_TABLES:
            if _find_by_name(manager, table, model_ref):
                # the SHARED-row mutation: last_result_json overwritten
                return [{'className': table,
                         'selector': {'kind': 'name',
                                      'value': model_ref}}]
        return [{'className': 'EngineModelDefinition',
                 'selector': {'kind': 'name', 'value': model_ref},
                 'dynamic': True}]
    if kind == 'subModel':
        msim_ref = stage.get('msimRef', '')
        seen = set(seen_msims or ())
        if depth >= _MAX_SUBMODEL_DEPTH or msim_ref in seen:
            return [{'className': 'MultiScaleSimulationDefinition',
                     'selector': {'kind': 'name', 'value': msim_ref},
                     'dynamic': True}]
        child = _find_by_name(manager, 'MultiScaleSimulationDefinition',
                              msim_ref)
        if child is None:
            return [{'className': 'MultiScaleSimulationDefinition',
                     'selector': {'kind': 'name', 'value': msim_ref},
                     'dynamic': True}]
        from simulations.multi_scale_stages import parse_stages
        items: List[Dict] = []
        for child_stage in parse_stages(child):
            items.extend(stage_write_set(
                manager, msim_ref, child_stage, depth + 1,
                seen | {msim_ref}))
        return items
    # runToCompletion / coStep / plain search
    return _attempt_items(manager, msim_name, stage)


def analyze_write_sets(manager, msim) -> Dict:
    """The advisor entry: every stage becomes a branch; overlapping
    write sets become evidence-bearing findings; the union manifest is
    THE lock manifest for request_run_slot (one analysis, two
    consumers). Stages are serialized by the gate ladder, but a shared
    row written by two stages makes results order/rerun-dependent —
    still worth a warning, never an auto-rewrite."""
    from simulations.multi_scale_stages import parse_stages
    msim_name = getattr(msim, 'name', '')
    branches = []
    for stage in parse_stages(msim):
        label = f"stage:{stage.get('key', '?')}"
        branches.append({'branch': label,
                         'writeSet': stage_write_set(
                             manager, msim_name, stage)})
    report = analyze_branches(branches)
    report['msim'] = msim_name
    return report


def stage_manifest(manager, msim, stage) -> List[Dict]:
    """The ONE stage's declared write set in lock-manifest shape —
    what the single-writer gate locks for a stage-search run."""
    items = stage_write_set(manager, getattr(msim, 'name', ''), stage)
    return [{'authority': 'local', 'className': i['className'],
             'selector': i['selector']}
            for i in items if not i.get('dynamic')]
