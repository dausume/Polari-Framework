"""
@module mech.custom.analyses

The mech engines as Polari ANALYSES — `fn(manager, **params) -> dict`, the
contract of polariNoCode.analysis_calls (an AnalysisDefinition row names
each one by `callable_ref`; an AnalysisCall node in any no-code solution
runs it; provenance is stamped by call_analysis). This is how mech's
functionality reaches the surface: no custom API (his rule, 2026-11-03 —
"polari fully automates away api creation so long as functionality and
engines are wrapped by polari properly"). The engines themselves stay
pure in custom/{dof_solver,fit_checks,compatibility,material_registry,
motion_runs}.py; this file only adapts names → rows and trims what JSON
cannot carry.

Every analysis refuses by name with {'ok': False, 'error', 'suggestion'}
when a row is missing (knobs-and-suggestions), never raises for a bad
name.

@consumers mech.mech_analysis_seed (SEED_MECH_ANALYSES), SolutionExecutionEngine
"""
import json
import os

_REF_CSV = os.path.join(os.path.dirname(__file__), 'reference', 'mfx0_motion_econ.csv')


def _rows(manager, cls):
    t = (getattr(manager, 'objectTables', {}) or {}).get(cls) or {}
    return list(t.values()) if isinstance(t, dict) else list(t)


def _row(manager, cls, name):
    for r in _rows(manager, cls):
        if getattr(r, 'name', None) == name or (isinstance(r, dict) and r.get('name') == name):
            return r
    return None


def _g(row, key, default=''):
    return row.get(key, default) if isinstance(row, dict) else getattr(row, key, default)


def _public(row):
    src = row if isinstance(row, dict) else vars(row)
    out = {}
    for k, v in src.items():
        if k.startswith('_') or k in ('manager', 'polServer', 'branch', 'inTree'):
            continue
        if k.endswith('_json') and isinstance(v, str) and v:
            try:
                v = json.loads(v)
            except ValueError:
                pass
        out[k] = v
    return out


def _jsonable(value):
    if callable(value):
        return '<fn>'
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _missing(cls, name, known):
    return {'ok': False, 'error': f'no {cls} named {name!r}',
            'suggestion': {'knob': f'{cls}.name', 'evidence': sorted(known)[:20]}}


# ---- catalogue (mxc-1) ------------------------------------------------

def catalogue_family(manager, family=''):
    """One family with its variants (or the family list when family='')."""
    fams = _rows(manager, 'MechPartFamily')
    if not family:
        counts = {}
        for v in _rows(manager, 'MechPartVariant'):
            counts[_g(v, 'family_ref')] = counts.get(_g(v, 'family_ref'), 0) + 1
        return {'ok': True, 'count': len(fams),
                'families': [dict(_public(f), variant_count=counts.get(_g(f, 'name'), 0)) for f in fams]}
    fam = _row(manager, 'MechPartFamily', family)
    if fam is None:
        return _missing('MechPartFamily', family, [_g(f, 'name') for f in fams])
    return {'ok': True, 'family': _public(fam),
            'variants': [_public(v) for v in _rows(manager, 'MechPartVariant') if _g(v, 'family_ref') == family]}


def catalogue_variant(manager, variant=''):
    """One variant with its features."""
    var = _row(manager, 'MechPartVariant', variant)
    if var is None:
        return _missing('MechPartVariant', variant, [])
    return {'ok': True, 'variant': _public(var),
            'features': [_public(f) for f in _rows(manager, 'MechFeature') if _g(f, 'variant_ref') == variant]}


def pairing(manager, variant_a='', feature_a='', variant_b='', feature_b=''):
    """Can feature_a of variant_a mate with feature_b of variant_b? (key
    match + role pairing + the advisory thread-engagement knob)."""
    from mech.custom.compatibility import check_pairing
    va, vb = _row(manager, 'MechPartVariant', variant_a), _row(manager, 'MechPartVariant', variant_b)
    if va is None or vb is None:
        return _missing('MechPartVariant', variant_a if va is None else variant_b, [])
    return check_pairing(manager, variant_a, feature_a, variant_b, feature_b)   # by NAME (the engine resolves rows)


def pairings(manager, variant=''):
    """Every variant/feature in the catalogue that mates with this variant's features."""
    from mech.custom.compatibility import pairings_for
    var = _row(manager, 'MechPartVariant', variant)
    if var is None:
        return _missing('MechPartVariant', variant, [])
    return {'ok': True, 'variant': variant, 'pairings': pairings_for(manager, variant)}


# ---- materials (mxc-1) ------------------------------------------------

def material_preference(manager, preference=''):
    """A part category's default / alternative / legacy materials, each
    default checked through composition's role_viability, with the IARC
    reasons for the legacy ones."""
    from mech.custom.material_registry import legacy_comparison, preference_check
    check = preference_check(manager, preference)
    if not check.get('ok', True):
        return check
    return {'ok': True, 'preference': preference, 'check': check,
            'legacy': legacy_comparison(manager, preference)}


# ---- assemblies (mxc-2) -----------------------------------------------

def assembly_dof(manager, assembly=''):
    """Free DOF per instance + mobility + under/over-constrained bodies
    (a Grübler count, not a rank test — the result's note says what it
    cannot catch)."""
    from mech.custom.dof_solver import solve_dof
    asm = _row(manager, 'MechAssembly', assembly)
    if asm is None:
        return _missing('MechAssembly', assembly, [_g(a, 'name') for a in _rows(manager, 'MechAssembly')])
    return solve_dof(asm, manager)


def assembly_check(manager, assembly=''):
    """Every fit check + the DOF count over one assembly → MechConflict
    dicts (not persisted here; a solution may write them)."""
    from mech.custom.fit_checks import check_assembly
    asm = _row(manager, 'MechAssembly', assembly)
    if asm is None:
        return _missing('MechAssembly', assembly, [_g(a, 'name') for a in _rows(manager, 'MechAssembly')])
    conflicts = check_assembly(asm, manager)
    return {'ok': True, 'assembly': assembly, 'conflict_count': len(conflicts), 'conflicts': conflicts}


# ---- motion (mxc-4) ---------------------------------------------------

def motion_run(manager, motion_case='', load_case='', fem_model=''):
    """Run a motion case under a load case on Polari's 1-DOF engine; lands
    MechMotionRun + SimulationRun + MechMotionSimState + MechMotionVector
    rows on the manager. Returns the report (every check with its number)
    and the run's inputs_sha256; a run whose checks fail is still a
    completed run (report.ok False)."""
    from mech.custom.motion_runs import run_polari
    case = _row(manager, 'MechMotionCase', motion_case)
    if case is None:
        return _missing('MechMotionCase', motion_case, [_g(c, 'name') for c in _rows(manager, 'MechMotionCase')])
    load = _row(manager, 'MechLoadCase', load_case) if load_case else next(
        (l for l in _rows(manager, 'MechLoadCase') if _g(l, 'assembly_ref') == _g(case, 'assembly_ref')), None)
    if load is None:
        return _missing('MechLoadCase', load_case or f'<any on {_g(case, "assembly_ref")}>',
                        [_g(l, 'name') for l in _rows(manager, 'MechLoadCase')])
    out = run_polari(manager, case, load, fem_model_ref=fem_model)
    if 'error' in out:
        return out
    result = out.get('result') or {}
    return {'ok': True, 'run': _public(out['run']) if out.get('run') is not None else None,
            'report': out.get('report'), 'model': _jsonable(out.get('model')),
            'summary': result.get('summary'), 'units': result.get('units'),
            'steps': len(result.get('steps') or []), 'inputs_sha256': out.get('inputs_sha256'),
            'note': 'per-step rows: MechMotionSimState (simulation_series.build_series); '
                    'vectors: MechMotionVector <run>:<signal>'}


def freecad_compare(manager, run='', csv='', tol_mm=0.1):
    """Polari position(t) of a run vs a FreeCAD Motion CSV (default: the
    mfx-0 reference run recorded on econ, 2026-11-03)."""
    from mech.custom.motion_runs import compare_to_freecad
    row = _row(manager, 'MechMotionRun', run)
    if row is None:
        return _missing('MechMotionRun', run, [_g(r, 'name') for r in _rows(manager, 'MechMotionRun')])
    states = sorted((s for s in _rows(manager, 'MechMotionSimState') if _g(s, 'run_ref') == run),
                    key=lambda s: _g(s, 'step', 0))
    steps = [{'t_s': float(_g(s, 't_s', 0.0)), 'q': float(_g(s, 'q', 0.0))} for s in states]
    case = _row(manager, 'MechMotionCase', _g(row, 'motion_case_ref'))
    step_s = float(_g(case, 'step_s', 0) or 0) or None
    try:
        return compare_to_freecad(steps, csv or _REF_CSV, step_s=step_s, tol_mm=float(tol_mm))
    except (ValueError, OSError) as e:
        return {'ok': False, 'error': str(e), 'suggestion': {'knob': 'MechMotionCase.step_s / csv path'}}
