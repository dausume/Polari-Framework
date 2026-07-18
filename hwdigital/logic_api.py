"""
@module hwdigital.logic_api

ncg-3 knob surface for logic designs. The knobs ARE the
LogicBlockDesign/LogicBlockNode rows (standard CRUDE editing); these
routes serve the derived views: the catalogue, the reference
evaluation (the teaching trace), and the generated artifacts through
the registered compiler seam.

@consumers
  - hwdigital.selftest_logic (function-level)
  - the frontend logic-diagram editor (later, with Dustin)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from hwdigital.logic_sim import (LogicSimulator, design_specs,
                                 is_clocked)


class LogicDesignAPI(treeObject):
    """Catalogue + compile + evaluate for LogicBlockDesign rows."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/hw/logic-designs'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/hw/logic-designs', self, suffix='catalogue')
            add('/api/hw/logic-designs/{name}/artifact/{artifact}',
                self, suffix='artifact')
            add('/api/hw/logic-designs/{name}/evaluate', self,
                suffix='evaluate')

    def on_get_catalogue(self, request, response):
        tables = getattr(self.manager, 'objectTables', None) or {}
        designs = []
        for row in (tables.get('LogicBlockDesign') or {}).values():
            name = getattr(row, 'name', '')
            try:
                specs = design_specs(self.manager, name)
                shape = {'nodes': len(specs),
                         'clocked': is_clocked(specs),
                         'inputs': sorted(
                             n for n, s in specs.items()
                             if s['kind'] == 'input'),
                         'outputs': sorted(
                             n for n, s in specs.items()
                             if s['kind'] == 'output')}
            except ValueError as exc:
                shape = {'error': str(exc)}
            designs.append(dict(
                {'name': name,
                 'displayName': getattr(row, 'display_name', ''),
                 'target': getattr(row, 'target', ''),
                 'description': getattr(row, 'description', '')},
                **shape))
        response.media = {'ok': True, 'designs': designs}

    def on_get_artifact(self, request, response, name, artifact):
        from polariNoCode.graph_compilers import compile_with
        row = self._compiler_row()
        try:
            result = compile_with(
                row, {'manager': self.manager, 'design_name': name})
        except (RuntimeError, ValueError) as exc:
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False, 'error': str(exc)}
            return
        match = next((a for a in result['artifacts']
                      if a['kind'] == artifact
                      or a['name'] == artifact), None)
        if match is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f'no artifact {artifact!r}',
                'artifacts': [a['kind'] for a in result['artifacts']]}
            return
        response.content_type = 'text/plain'
        response.text = match['text']

    #: Honest ceiling on clock steps per evaluate call — each step
    #: re-settles the whole design, so an unbounded count is a
    #: trivial CPU pin.
    MAX_EVALUATE_STEPS = 10000

    def on_post_evaluate(self, request, response, name):
        """The reference evaluator as an act: inputs (+ optional
        clock steps) -> outputs, the slow-motion teaching trace."""
        try:
            payload = json.load(request.bounded_stream)
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        inputs = payload.get('inputs') or {}
        if not isinstance(inputs, dict):
            response.status = '422 Unprocessable Entity'
            response.media = {
                'ok': False,
                'error': f'inputs must be an object of '
                         f'{{node: value}}, got '
                         f'{type(inputs).__name__}'}
            return
        raw_steps = payload.get('steps', 0)
        try:
            steps = int(raw_steps)
        except (TypeError, ValueError):
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False,
                              'error': f'steps must be an integer, '
                                       f'got {raw_steps!r}'}
            return
        if not 0 <= steps <= self.MAX_EVALUATE_STEPS:
            response.status = '422 Unprocessable Entity'
            response.media = {
                'ok': False,
                'error': f'steps must be between 0 and '
                         f'{self.MAX_EVALUATE_STEPS} (got {steps}) '
                         f'— chunk longer runs into multiple calls'}
            return
        try:
            specs = design_specs(self.manager, name)
            sim = LogicSimulator(specs)
            # Positional dict — no ** splat, so arbitrary keys
            # (including 'self') reach set_inputs' own validation.
            sim.set_inputs(inputs)
            trace = [dict(sim.outputs())]
            for _ in range(steps):
                sim.step()
                trace.append(dict(sim.outputs()))
        except ValueError as exc:
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False, 'error': str(exc)}
            return
        response.media = {'ok': True, 'clocked': is_clocked(specs),
                          'outputs': trace[-1], 'trace': trace}

    def _compiler_row(self):
        tables = getattr(self.manager, 'objectTables', None) or {}
        row = next((r for r in (tables.get('GraphCompilerDefinition')
                                or {}).values()
                    if getattr(r, 'name', '') == 'hwdigital-logic'),
                   None)
        if row is not None:
            return row
        from types import SimpleNamespace
        from hwdigital.logic_compile import SEED_HWDIGITAL_COMPILER
        return SimpleNamespace(**SEED_HWDIGITAL_COMPILER)
