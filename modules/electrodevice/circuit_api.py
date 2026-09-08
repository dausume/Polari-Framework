"""
@module electrodevice.circuit_api

ncg-4 knob surface for row-defined circuits. The knobs ARE the
CircuitDefinition/CircuitNetDefinition/CircuitComponentDefinition
rows (standard CRUDE); these routes serve the derived views: the
catalogue, the generated netlist (through the registered compiler
seam), and a live ngspice run.

@consumers
  - electrodevice.circuit_rows_selftest (function-level)
  - the frontend circuit-diagram editor (later, with Dustin)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from electrodevice.circuit_netlist_seed import run_circuit


def _loads_or_note(raw, default):
    """Row JSON fields are CRUDE-editable — a hand-broken field must
    degrade to a note in the catalogue, never a 500."""
    try:
        return json.loads(raw or json.dumps(default)), None
    except (TypeError, ValueError) as exc:
        return default, f'unparseable JSON on the row: {exc}'


def _validate_boards_payload(payload, need_boards=True):
    """Shared payload validation for the breadboard/drive acts —
    a plain-language error string, or None when the shapes are
    sound. A bare string for boards must NOT iterate into
    per-character board names."""
    boards = payload.get('boards')
    if need_boards and (not isinstance(boards, list) or not boards
                        or not all(isinstance(b, str)
                                   for b in boards)):
        return ("'boards' must be a non-empty list of board names, "
                f'got {boards!r}')
    analyses = payload.get('analyses')
    if analyses is not None:
        if not isinstance(analyses, list):
            return ("'analyses' must be a list of "
                    '{"type": ...} dicts')
        for analysis in analyses:
            if not isinstance(analysis, dict) \
                    or 'type' not in analysis:
                return (f'analysis entries must be dicts with a '
                        f'"type" — got {analysis!r}')
            if analysis['type'] == 'tran' and 'args' not in analysis:
                return ('tran analysis needs "args" '
                        '(e.g. "0.1m 60m")')
    probes = payload.get('probes')
    if probes is not None and (
            not isinstance(probes, list)
            or not all(isinstance(p, str) for p in probes)):
        return ("'probes' must be a list of probe strings, got "
                f'{probes!r}')
    return None


class CircuitRowsAPI(treeObject):
    """Catalogue + netlist + run for circuit rows."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/electrodevice/circuits'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/electrodevice/circuits', self,
                suffix='catalogue')
            add('/api/electrodevice/circuits/{name}/netlist', self,
                suffix='netlist')
            add('/api/electrodevice/circuits/{name}/run', self,
                suffix='run')

    def on_get_catalogue(self, request, response):
        tables = getattr(self.manager, 'objectTables', None) or {}
        circuits = []
        for row in (tables.get('CircuitDefinition') or {}).values():
            name = getattr(row, 'name', '')
            components = []
            for c in (tables.get('CircuitComponentDefinition')
                      or {}).values():
                if getattr(c, 'circuit_name', '') != name:
                    continue
                pins, pins_note = _loads_or_note(
                    getattr(c, 'pins_json', '[]'), [])
                entry = {'name': getattr(c, 'name', ''),
                         'kind': getattr(c, 'kind', ''),
                         'pins': pins,
                         'device': getattr(c, 'device_name', '')
                         or None}
                if pins_note:
                    entry['rowError'] = f'pins_json: {pins_note}'
                components.append(entry)
            analyses, analyses_note = _loads_or_note(
                getattr(row, 'analyses_json', '[]'), [])
            entry = {'name': name,
                     'description': getattr(row, 'description', ''),
                     'analyses': analyses,
                     'components': components}
            if analyses_note:
                entry['rowError'] = f'analyses_json: {analyses_note}'
            circuits.append(entry)
        response.media = {'ok': True, 'circuits': circuits}

    def on_get_netlist(self, request, response, name):
        from types import SimpleNamespace
        from polariNoCode.graph_compilers import compile_with
        from electrodevice.circuit_netlist_seed import (
            SEED_CIRCUIT_COMPILER)
        tables = getattr(self.manager, 'objectTables', None) or {}
        row = next((r for r in (tables.get('GraphCompilerDefinition')
                                or {}).values()
                    if getattr(r, 'name', '') == 'circuit-netlist'),
                   None) or SimpleNamespace(**SEED_CIRCUIT_COMPILER)
        try:
            result = compile_with(
                row, {'manager': self.manager, 'circuit_name': name})
        except (RuntimeError, ValueError) as exc:
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False, 'error': str(exc)}
            return
        response.content_type = 'text/plain'
        response.text = result['artifacts'][0]['text']

    def on_post_run(self, request, response, name):
        result = run_circuit(self.manager, name)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result


class BreadboardAPI(treeObject):
    """ncg-5: run one or more jumpered boards; the rows (boards,
    placements, jumpers) are edited through standard CRUDE."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/electrodevice/breadboards'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/electrodevice/breadboards/run', self,
                suffix='run')
            add('/api/electrodevice/designs/{name}/drive', self,
                suffix='drive')

    def on_post_run(self, request, response):
        from electrodevice.breadboard_netlist_seed import run_breadboards
        try:
            payload = json.load(request.bounded_stream)
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        shape_error = _validate_boards_payload(payload)
        if shape_error:
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False, 'error': shape_error}
            return
        result = run_breadboards(
            self.manager, payload['boards'],
            analyses=payload.get('analyses'),
            probes=payload.get('probes'))
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_post_drive(self, request, response, name):
        """ncg-6: evaluate a logic design and drive its bound
        circuit sources — the cross-level act."""
        from electrodevice.level_bridge_basis import (
            drive_boards_from_design)
        try:
            payload = json.load(request.bounded_stream)
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        shape_error = _validate_boards_payload(payload)
        inputs = payload.get('inputs')
        if shape_error is None and inputs is not None \
                and not isinstance(inputs, dict):
            shape_error = ("'inputs' must be a dict of "
                           f'{{node: int}}, got {inputs!r}')
        steps = payload.get('steps', 0)
        if shape_error is None and (
                isinstance(steps, bool)
                or not isinstance(steps, (int, float))):
            shape_error = f"'steps' must be a number, got {steps!r}"
        if shape_error:
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False, 'error': shape_error}
            return
        result = drive_boards_from_design(
            self.manager, name, inputs or {},
            payload['boards'], steps=steps,
            probes=payload.get('probes'))
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result
