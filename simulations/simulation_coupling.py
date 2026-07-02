"""
@cross-cutting
@module simulations.simulation_coupling
@tags @xc:bindings

Cross-simulation coupling — the runner-side pre-pass that makes
SimulationCouplingDefinition rows actually flow data between spaces.

For each enabled coupling targeting the (sim, class) about to step:

  1. Inject the coupling's declared DEFAULTS into the step context
     (e.g. wind_vx/vy/vz = 0, wind_on = 0) — an uncoupled run behaves
     exactly as before the coupling existed.
  2. Resolve the SOURCE RUN from the target run's
     `coupled_run_refs_json` ({source_sim: source_run}). No entry →
     stay at defaults (this is how the vacuum pendulum run coexists
     with the wind-forced one under the same sim def).
  3. LAZY-PULL the source run forward: while its covered time
     (last_recorded_step × its dt) is behind the target's step time,
     advance it via run_step(). This is what lets the two spaces run
     at different timescales — the wind field steps at its own coarser
     dt and only when the pendulum actually needs new coverage. A
     pull-chain guard stops coupling cycles.
  4. SAMPLE: take the latest source row at time ≤ the target time
     (zero-order hold), build the sampler's operands per config_json,
     evaluate the coupling's (no-code) sampler MatrixEquationDefinition,
     and inject the result into the step context under the configured
     keys.

Failure model: SOFT. A coupling that can't sample (missing source run,
no rows yet, sampler error) leaves the defaults in place and surfaces a
warning — the target simulation still steps. Cross-space data flow
degrades to "uncoupled", never to "broken run".

@consumers
  - simulations.simulation_runner (per-class pre-pass in run_step)
@see /OVERLAP_MAP.md
"""

import json
from typing import Any, Dict, FrozenSet, List, Optional

# Backstop for a runaway lazy pull (a source run whose dt is pathologically
# small relative to the target's step time). Far above any sane ratio.
MAX_PULL_STEPS_PER_CALL = 10000


def apply_couplings(
    manager,
    run,
    sim_def,
    cls_name: str,
    baseline: Dict[str, Any],
    time_value: float,
    warnings: List[str],
    pull_chain: FrozenSet[str],
) -> None:
    """Mutate `baseline` in place with every enabled coupling targeting
    (sim_def.name, cls_name). See module docstring for the sequence."""
    couplings = _couplings_for(manager, getattr(sim_def, 'name', ''), cls_name)
    for coupling in couplings:
        config = _parse_json(getattr(coupling, 'config_json', '{}') or '{}', {})
        if not isinstance(config, dict):
            warnings.append(
                f"Coupling '{getattr(coupling, 'name', '')}': config_json "
                f"malformed — skipping."
            )
            continue

        # 1. Defaults first — overwritten below only on a successful sample.
        defaults = config.get('defaults') or {}
        if isinstance(defaults, dict):
            for key, val in defaults.items():
                baseline[key] = val

        # 2. Which source run feeds THIS target run?
        source_sim = getattr(coupling, 'source_simulation_ref', '') or ''
        source_run_name = _coupled_run_name(run, source_sim)
        if not source_run_name:
            # Uncoupled run — defaults stand, silently (by design).
            continue
        source_run = _find_run(manager, source_run_name)
        if source_run is None:
            warnings.append(
                f"Coupling '{getattr(coupling, 'name', '')}': run "
                f"'{getattr(run, 'name', '')}' names source run "
                f"'{source_run_name}' but it does not exist — using defaults."
            )
            continue

        # 3. Lazy-pull the source run to cover the target's time.
        _ensure_source_covers(
            manager, source_run, time_value, warnings, pull_chain,
        )

        # 4. Sample the latest source row ≤ t and inject.
        src_row = _latest_source_row(
            manager, getattr(coupling, 'source_class_name', '') or '',
            source_run_name, time_value,
        )
        if src_row is None:
            warnings.append(
                f"Coupling '{getattr(coupling, 'name', '')}': source run "
                f"'{source_run_name}' has no "
                f"{getattr(coupling, 'source_class_name', '?')} row at "
                f"time <= {time_value} — using defaults."
            )
            continue
        try:
            sample = _evaluate_sampler(
                manager, coupling, config, src_row, baseline,
            )
        except Exception as exc:
            warnings.append(
                f"Coupling '{getattr(coupling, 'name', '')}': sampler failed "
                f"({type(exc).__name__}: {exc}) — using defaults."
            )
            continue
        _inject_sample(config, sample, baseline, warnings, coupling)


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def _parse_json(text: str, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return default


def _couplings_for(manager, sim_def_name: str, cls_name: str) -> List:
    table = manager.objectTables.get('SimulationCouplingDefinition', {}) or {}
    out = []
    for c in table.values():
        if getattr(c, 'target_simulation_ref', '') != sim_def_name:
            continue
        if getattr(c, 'target_class_name', '') != cls_name:
            continue
        if not getattr(c, 'enabled', True):
            continue
        out.append(c)
    out.sort(key=lambda c: getattr(c, 'name', ''))
    return out


def _coupled_run_name(run, source_sim: str) -> Optional[str]:
    refs = _parse_json(
        getattr(run, 'coupled_run_refs_json', '') or '{}', {}
    )
    if not isinstance(refs, dict):
        return None
    val = refs.get(source_sim)
    return val if isinstance(val, str) and val else None


def _find_run(manager, run_name: str):
    table = manager.objectTables.get('SimulationRun', {}) or {}
    for r in table.values():
        if getattr(r, 'name', '') == run_name:
            return r
    return None


def _run_dt(manager, run) -> float:
    """A run's effective dt — per-run override when > 0, else its sim
    def's, else a defensive 0.01 (mirrors the runner's resolution)."""
    run_dt = float(getattr(run, 'time_step_seconds', 0.0) or 0.0)
    if run_dt > 0:
        return run_dt
    sim_name = getattr(run, 'simulation_ref', '')
    table = manager.objectTables.get('SimulationDefinition', {}) or {}
    for s in table.values():
        if getattr(s, 'name', '') == sim_name:
            return float(getattr(s, 'time_step_seconds', 0.01) or 0.01)
    return 0.01


def _ensure_source_covers(
    manager,
    source_run,
    time_value: float,
    warnings: List[str],
    pull_chain: FrozenSet[str],
) -> None:
    """Advance the source run until last_recorded_step × dt reaches the
    target time. Cycle-guarded via pull_chain (the set of run names
    already being advanced up-stack)."""
    source_name = getattr(source_run, 'name', '')
    if source_name in pull_chain:
        warnings.append(
            f"Coupling cycle detected pulling run '{source_name}' — "
            f"sampling whatever rows it already has."
        )
        return
    # Imported here, not at module top: the runner imports this module,
    # and the pull re-enters the runner (one level per coupling hop).
    from simulations.simulation_runner import run_step

    dt = _run_dt(manager, source_run)
    chain = pull_chain | {source_name}
    pulls = 0
    while (int(getattr(source_run, 'last_recorded_step', 0) or 0) * dt
           < time_value - 1e-9):
        if pulls >= MAX_PULL_STEPS_PER_CALL:
            warnings.append(
                f"Lazy pull of run '{source_name}' hit the "
                f"{MAX_PULL_STEPS_PER_CALL}-step backstop — check the "
                f"dt ratio between the coupled simulations."
            )
            break
        result = run_step(manager, source_run, _pull_chain=chain)
        pulls += 1
        if not result.get('success'):
            warnings.append(
                f"Lazy pull of run '{source_name}' failed at step "
                f"{result.get('step')}: {result.get('error')} — sampling "
                f"whatever rows it already has."
            )
            break


def _latest_source_row(
    manager,
    source_class: str,
    source_run_name: str,
    time_value: float,
):
    """The source class's row with the greatest step whose time ≤ the
    target time (zero-order hold across the timescale gap)."""
    table = manager.objectTables.get(source_class, {}) or {}
    best = None
    best_step = -1
    for inst in table.values():
        if getattr(inst, 'simulation_run_ref', '') != source_run_name:
            continue
        try:
            row_time = float(getattr(inst, 'time', 0.0) or 0.0)
            row_step = int(getattr(inst, 'step', 0) or 0)
        except (TypeError, ValueError):
            continue
        if row_time > time_value + 1e-9:
            continue
        if row_step > best_step:
            best, best_step = inst, row_step
    return best


# ---------------------------------------------------------------------------
# Sampling + injection
# ---------------------------------------------------------------------------


def _evaluate_sampler(manager, coupling, config, src_row, baseline):
    """Build the sampler's operand bindings per config and evaluate its
    (no-code) MatrixEquationDefinition. Returns the result as a plain
    Python scalar or (nested) list."""
    sampler_cfg = config.get('sampler') or {}
    operand_specs = sampler_cfg.get('operands') or {}
    binding_values: Dict[str, Any] = {}
    for sym, spec in operand_specs.items():
        binding_values[sym] = _resolve_operand(spec, src_row, baseline)

    eq_name = getattr(coupling, 'sampler_equation_ref', '') or ''
    eq_def = None
    table = manager.objectTables.get('MatrixEquationDefinition', {}) or {}
    for inst in table.values():
        if getattr(inst, 'name', '') == eq_name:
            eq_def = inst
            break
    if eq_def is None:
        raise ValueError(f"sampler equation '{eq_name}' not found")

    from matrices.matrix_equation_executor import evaluate_equation
    arr = evaluate_equation(eq_def, binding_values=binding_values, manager=manager)
    if hasattr(arr, 'ndim') and arr.ndim == 0:
        return arr.item()
    if hasattr(arr, 'tolist'):
        return arr.tolist()
    return arr


def _resolve_operand(spec, src_row, baseline):
    """One sampler operand — see SimulationCouplingDefinition's
    config_json schema."""
    if not isinstance(spec, dict):
        return spec
    kind = spec.get('kind')
    if kind == 'source_field_json':
        raw = getattr(src_row, spec.get('field', ''), '') or '[]'
        parsed = _parse_json(raw, None)
        if parsed is None:
            raise ValueError(
                f"source field '{spec.get('field')}' is not valid JSON"
            )
        return parsed
    if kind == 'source_field':
        return float(getattr(src_row, spec.get('field', ''), 0.0) or 0.0)
    if kind == 'target_fields':
        fields = spec.get('fields') or []
        return [float(baseline.get(f, 0.0) or 0.0) for f in fields]
    if kind == 'constant':
        return spec.get('value')
    raise ValueError(f"unknown sampler operand kind {kind!r}")


def _inject_sample(config, sample, baseline, warnings, coupling) -> None:
    inject = config.get('inject') or {}
    if not isinstance(inject, dict):
        return
    for key, spec in inject.items():
        if not isinstance(spec, dict):
            baseline[key] = spec
            continue
        kind = spec.get('kind')
        if kind == 'sample':
            baseline[key] = sample
        elif kind == 'sample_element':
            try:
                baseline[key] = float(sample[int(spec.get('index', 0))])
            except (TypeError, ValueError, IndexError):
                warnings.append(
                    f"Coupling '{getattr(coupling, 'name', '')}': inject "
                    f"'{key}' could not extract element "
                    f"{spec.get('index')} from the sample — default kept."
                )
        elif kind == 'constant':
            baseline[key] = spec.get('value')
        else:
            warnings.append(
                f"Coupling '{getattr(coupling, 'name', '')}': inject "
                f"'{key}' has unknown kind {kind!r} — default kept."
            )
