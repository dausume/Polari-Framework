"""
@module hwnocode.hwnocode_api

GET /api/hwnocode                                  the summary: solutions, node kinds on the canvas, the compiler row
GET /api/hwnocode/solutions                        every HardwareSolution row
GET /api/hwnocode/solutions/{solution}             the row + its HardwareNodePlacement rows
GET /api/hwnocode/solutions/{solution}/placement   the placement computed NOW from the live rows (refusals named; nothing written)
GET /api/hwnocode/solutions/{solution}/render      hn-split in memory: the board half's files + shas vs cmod-1's record, the backend
                                                   half's states — or the refusal (422); nothing written
GET /api/hwnocode/solutions/{solution}/suggest     the runtime suggestion with its evidence — SUGGEST ONLY (D-hn-3): never applied
GET /api/hwnocode/solutions/{solution}/chart       {ok, rows}: the chart's two series (temp_c, temp_avg) over uptime — the
                                                   named-graph-panel's dataPath
GET /api/hwnocode/interface?binding=<name>         one HardwareInterfaceBinding (the hw-interface overlay): the row it ties, the
                                                   board instance, the port / twin pty, frames seen, refused frames
Writing a project, building and the twin are `pol hwnocode render | build` + `pol board twin uno up --work …` (files / engines).
"""
import inspect

from objectTreeDecorators import treeObject, treeObjectInit


class HwNoCodeAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/hwnocode', self, suffix='summary')
            add('/api/hwnocode/solutions', self, suffix='solutions')
            add('/api/hwnocode/solutions/{solution}', self, suffix='solution_one')
            add('/api/hwnocode/solutions/{solution}/placement', self, suffix='placement')
            add('/api/hwnocode/solutions/{solution}/render', self, suffix='render')
            add('/api/hwnocode/solutions/{solution}/suggest', self, suffix='suggest')
            add('/api/hwnocode/solutions/{solution}/chart', self, suffix='chart')
            add('/api/hwnocode/interface', self, suffix='interface')

    def _rows(self, cls):
        return list(((self.manager.objectTables or {}).get(cls, {}) or {}).values()) if self.manager is not None else []

    @staticmethod
    def _d(row):
        keys = [k for k in inspect.signature(type(row).__init__).parameters if k not in ('self', 'manager')]
        return {k: getattr(row, k, None) for k in keys}

    def _solution(self, name, response):
        import falcon
        hit = [r for r in self._rows('HardwareSolution') if r.name == name]
        if not hit:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no HardwareSolution %r (GET /api/hwnocode/solutions lists them)' % name}
        return hit[0] if hit else None

    def on_get_summary(self, request, response):
        from hwnocode.hwnocode_basis import NODE_KIND_CLASSES
        typing = getattr(self.manager, 'objectTypingDict', {}) or {}
        response.media = {'ok': True,
                          'solutions': [{k: getattr(r, k, '') for k in ('name', 'variant_kind', 'status', 'cgraph', 'interface',
                                                                         'firmware_runtime', 'placement_summary')}
                                        for r in sorted(self._rows('HardwareSolution'), key=lambda r: r.name)],
                          'node_kinds': [{'class': c.__name__, 'kind': c.statePalette['nodeKind'], 'placement': c.statePalette['placement'],
                                          'on_palette': bool(getattr(typing.get(c.__name__), 'isStateSpaceObject', False))}
                                         for c in NODE_KIND_CLASSES],
                          'compiler': 'hn-split (polariNoCode.graph_compilers) → cmod-glue for the board half',
                          'policy': 'firmware_runtime is the person\'s knob; the suggestion is shown, never applied (D-hn-3)'}

    def on_get_solutions(self, request, response):
        response.media = {'ok': True, 'solutions': [self._d(r) for r in sorted(self._rows('HardwareSolution'), key=lambda r: r.name)]}

    def on_get_solution_one(self, request, response, solution):
        s = self._solution(solution, response)
        if s is None:
            return
        pl = sorted((r for r in self._rows('HardwareNodePlacement') if r.solution == solution), key=lambda r: r.order)
        response.media = {'ok': True, 'solution': self._d(s), 'placement': [self._d(r) for r in pl]}

    def on_get_placement(self, request, response, solution):
        import falcon
        from hwnocode.custom import placement as PL
        from hwnocode.custom import split as SP
        if self._solution(solution, response) is None:
            return
        try:
            r = SP.place_solution(solution, self.manager)
        except Exception as e:  # noqa: BLE001 — a refusal in plain words
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'refused': str(e)}
            return
        response.media = {'ok': not r['refusals'], 'summary': PL.summary(r), 'nodes': r['nodes'], 'refusals': r['refusals'],
                          'runtime': r['runtime'], 'device_side': r['device_side'], 'target': r['target']}

    def on_get_render(self, request, response, solution):
        import falcon
        from hwnocode.custom import split as SP
        from cmod.custom import glue as GL
        if self._solution(solution, response) is None:
            return
        try:
            p = SP.solution_rows(solution, self.manager)
            r = SP.compile_parts(p)
        except Exception as e:  # noqa: BLE001
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'refused': str(e)}
            return
        pv = r['provenance']
        crec = GL.load_record(p['solution']['cgraph']) or {}
        response.media = {'ok': True, 'solution': solution, 'split_sha256': pv['split_sha256'], 'placement_summary': pv['placement_summary'],
                          'board_half': {'compiler': 'cmod-glue', 'graph_sha256': pv['glue']['graph_sha256'],
                                         'files': [{'file': f, 'sha256': s, 'equal_to_cmod1': s == (crec.get('files') or {}).get(f)}
                                                   for f, s in sorted(pv['glue_files'].items())],
                                         'files_sha256': pv['glue_files_sha256'], 'cmod1_files_sha256': crec.get('files_sha256', ''),
                                         'unchanged_output': pv['glue_files_sha256'] == crec.get('files_sha256')},
                          'backend_half': {'solution': r['definition']['solutionName'],
                                           'states': [{'state': s['stateName'], 'class': s.get('stateClass')} for s in r['definition']['stateInstances']]},
                          'how': 'split in this process from the live rows; nothing written (pol hwnocode render writes the project)'}

    def on_get_suggest(self, request, response, solution):
        import falcon
        from hwnocode.custom import suggest as SG
        if self._solution(solution, response) is None:
            return
        try:
            r = SG.suggest(solution, self.manager)
        except Exception as e:  # noqa: BLE001
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'refused': str(e)}
            return
        response.media = dict(r, ok=True)

    def on_get_chart(self, request, response, solution):
        from hwnocode.custom import derive as DV
        s = self._solution(solution, response)
        if s is None:
            return
        obj = ''
        for b in self._rows('HardwareInterfaceBinding'):
            if b.name == s.interface:
                obj = b.object_name
        try:
            last = int(request.get_param('last') or 300)
        except ValueError:
            last = 300
        rows = DV.chart_rows(self.manager, obj, last)
        if not rows:
            response.media = {'ok': False, 'rows': [],
                              'refusal': 'no samples yet for %s: the backend half writes one per frame the bridge applies to the '
                                         'row (start the twin + the bridge — `pol hwnocode build %s`, `pol board twin uno up --work …`)'
                                         % (obj or s.interface, solution)}
            return
        response.media = {'ok': True, 'rows': rows, 'rowCount': len(rows), 'series': ['temp_c', 'temp_avg'], 'x': 'uptime_s',
                          'source_object': obj}

    def on_get_interface(self, request, response):
        import falcon
        name = request.get_param('binding') or ''
        hit = [b for b in self._rows('HardwareInterfaceBinding') if b.name == name]
        if not hit:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no HardwareInterfaceBinding %r' % name}
            return
        response.media = {'ok': True, 'binding': self._d(hit[0]), 'placement': 'bridge',
                          'role': 'the split point: frames UP to the row, Commands DOWN from a PUT of the row'}
