# Matrix validator — structural sanity checks for a MatrixDefinition.
#
# Never raises: collects problems into {valid, errors, warnings, ...} so the
# UI can surface them inline as the user authors a matrix. For literal matrices
# it attempts a dry evaluation to confirm shapes actually compose; for computed
# matrices (elementwise / matrix_op) it only checks that referenced names
# resolve, since concrete shapes may depend on runtime bindings.

from __future__ import annotations

from typing import Any

from matrices.matrix_executor import (
    MatrixEvalError,
    evaluate,
    parse_shape,
    _find_named,
    _parse_json,
    _product,
)


def validate(matrix_def, manager=None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    shape: list[int] | None = None
    composed_shape: list[int] | None = None

    # --- shape ---
    try:
        shape_t = parse_shape(getattr(matrix_def, 'shape_json', '[]'))
        shape = list(shape_t)
    except MatrixEvalError as e:
        errors.append(str(e))
        shape_t = None

    etype = getattr(matrix_def, 'element_type', 'float') or 'float'
    if etype not in ('float', 'int', 'complex', 'equation', 'matrix', 'mixed'):
        errors.append(f"unknown element_type '{etype}'")

    computation = _parse_json(getattr(matrix_def, 'computation_json', '') or '{}', {})
    if not isinstance(computation, dict):
        errors.append("computation_json must be a JSON object")
        computation = {}
    kind = computation.get('kind', 'literal')
    if kind not in ('literal', 'elementwise', 'matrix_op'):
        errors.append(f"unknown computation kind '{kind}'")

    # --- per-kind structural checks ---
    if kind == 'literal' and shape_t is not None:
        values = _parse_json(getattr(matrix_def, 'values_json', '[]') or '[]', None)
        if not isinstance(values, list):
            errors.append("values_json must be a flat, row-major list")
        else:
            expected = _product(shape_t)
            is_template = bool(getattr(matrix_def, 'is_template', False))
            if is_template and len(values) == 0:
                warnings.append("template matrix: shape declared, no values")
            elif len(values) != expected:
                errors.append(
                    f"expected {expected} element(s) for shape {shape}, got {len(values)}")
            if etype == 'matrix':
                _check_block_refs(matrix_def, values, manager, errors)
            elif etype == 'equation':
                _check_equation_refs(values, manager, warnings)
            elif etype == 'mixed':
                _check_mixed_refs(matrix_def, values, manager, errors, warnings)
    elif kind == 'elementwise':
        _check_named_ref('EquationDefinition', computation.get('equationRef'),
                         computation.get('latex'), manager, errors, 'elementwise')
        _check_operand_refs(computation.get('bindings') or {}, manager, errors)
    elif kind == 'matrix_op':
        if not computation.get('expr'):
            errors.append("matrix_op requires 'expr'")
        _check_operand_refs(computation.get('operands') or {}, manager, errors)

    # --- recursive-nesting (cycle) detection for matrix/mixed elements ---
    if kind == 'literal' and etype in ('matrix', 'mixed'):
        cycle = _detect_cycle(matrix_def, manager)
        if cycle:
            errors.append("recursive matrix nesting would loop: "
                          + " → ".join(cycle))

    # --- dry run (only when structurally clean + concrete) ---
    if not errors and kind == 'literal' and etype not in ('equation', 'mixed'):
        # Equation-element + mixed literals may need bindings to fully reduce,
        # so skip their dry run here (the Test tab exercises that with real
        # values).
        try:
            arr = evaluate(matrix_def, manager=manager)
            composed_shape = list(arr.shape)
        except MatrixEvalError as e:
            errors.append(str(e))
        except Exception as e:  # pragma: no cover - defensive
            errors.append(f"unexpected error: {type(e).__name__}: {e}")

    return {
        'valid': not errors,
        'errors': errors,
        'warnings': warnings,
        'shape': shape,
        'composedShape': composed_shape,
        'elementType': etype,
        'kind': kind,
    }


# ---------------------------------------------------------------------------

def _check_block_refs(matrix_def, values, manager, errors):
    default_ref = getattr(matrix_def, 'element_matrix_ref', '') or ''
    self_name = getattr(matrix_def, 'name', '')
    for i, entry in enumerate(values):
        ref = entry if isinstance(entry, str) else (
            entry.get('matrixRef') or entry.get('ref') if isinstance(entry, dict) else None)
        ref = ref or default_ref
        if not ref:
            errors.append(f"block {i}: no matrixRef and no element_matrix_ref default")
            continue
        if ref == self_name:
            errors.append(f"block {i}: matrix references itself ('{ref}')")
            continue
        if _find_named('MatrixDefinition', ref, manager) is None:
            errors.append(f"block {i}: referenced matrix '{ref}' not found")


def _matrix_refs_of(mdef, manager) -> list:
    """Matrix names referenced as block/mixed elements by a literal matrix."""
    comp = _parse_json(getattr(mdef, 'computation_json', '') or '{}', {})
    if isinstance(comp, dict) and comp.get('kind', 'literal') != 'literal':
        return []
    etype = getattr(mdef, 'element_type', '') or ''
    values = _parse_json(getattr(mdef, 'values_json', '') or '[]', [])
    default_ref = getattr(mdef, 'element_matrix_ref', '') or ''
    refs = []
    if not isinstance(values, list):
        return refs
    for cell in values:
        ref = None
        if etype == 'matrix':
            if isinstance(cell, str):
                ref = cell
            elif isinstance(cell, dict):
                ref = cell.get('matrixRef') or cell.get('ref')
            ref = ref or default_ref
        elif etype == 'mixed' and isinstance(cell, dict):
            is_matrix = cell.get('kind') == 'matrix' or (
                cell.get('kind') is None and ('matrixRef' in cell or 'ref' in cell))
            if is_matrix:
                ref = cell.get('matrixRef') or cell.get('ref')
        if ref:
            refs.append(ref)
    return refs


def _detect_cycle(matrix_def, manager):
    """DFS over matrix-element references; return the path (list of names) if a
    cycle back to the matrix under validation exists, else None."""
    start = getattr(matrix_def, 'name', '') or '<this matrix>'

    def dfs(mdef, path):
        for ref in _matrix_refs_of(mdef, manager):
            if ref == start:
                return [*path, ref]
            if ref in path:
                continue  # already on the current path — don't recurse forever
            child = _find_named('MatrixDefinition', ref, manager)
            if child is not None:
                found = dfs(child, [*path, ref])
                if found:
                    return found
        return None

    return dfs(matrix_def, [start])


def _check_mixed_refs(matrix_def, values, manager, errors, warnings):
    """Per-cell checks for self-describing 'mixed' elements."""
    self_name = getattr(matrix_def, 'name', '')
    for i, cell in enumerate(values):
        if isinstance(cell, (int, float)):
            continue
        if not isinstance(cell, dict):
            errors.append(f"cell {i}: must be a number or a {{kind, …}} object")
            continue
        kind = cell.get('kind')
        if kind == 'matrix' or (kind is None and ('matrixRef' in cell or 'ref' in cell)):
            ref = cell.get('matrixRef') or cell.get('ref')
            if not ref:
                errors.append(f"cell {i}: matrix cell has no matrixRef")
            elif ref == self_name:
                errors.append(f"cell {i}: matrix references itself ('{ref}')")
            elif _find_named('MatrixDefinition', ref, manager) is None:
                errors.append(f"cell {i}: referenced matrix '{ref}' not found")
        elif kind == 'equation' or (kind is None and ('latex' in cell or 'equationRef' in cell)):
            eq_ref = cell.get('equationRef')
            if eq_ref and _find_named('EquationDefinition', eq_ref, manager) is None:
                warnings.append(f"cell {i}: equation '{eq_ref}' not found")
            elif not eq_ref and not cell.get('latex'):
                errors.append(f"cell {i}: equation cell needs latex or equationRef")


def _check_equation_refs(values, manager, warnings):
    for i, entry in enumerate(values):
        if isinstance(entry, dict) and entry.get('equationRef'):
            if _find_named('EquationDefinition', entry['equationRef'], manager) is None:
                warnings.append(f"element {i}: equation '{entry['equationRef']}' not found")


def _check_named_ref(class_name, ref, inline, manager, errors, ctx):
    if not ref and not inline:
        errors.append(f"{ctx}: needs an equationRef or inline latex")
        return
    if ref and _find_named(class_name, ref, manager) is None:
        errors.append(f"{ctx}: referenced {class_name} '{ref}' not found")


def _check_operand_refs(operands: dict, manager, errors):
    for sym, spec in operands.items():
        ref = None
        if isinstance(spec, str):
            ref = spec
        elif isinstance(spec, dict):
            ref = spec.get('matrixRef') or spec.get('ref')
        # Bare names may be runtime bindings (resolved at evaluate time) — only
        # flag dict refs that name a matrix which doesn't exist.
        if isinstance(spec, dict) and ref and _find_named('MatrixDefinition', ref, manager) is None:
            errors.append(f"operand '{sym}': referenced matrix '{ref}' not found")
