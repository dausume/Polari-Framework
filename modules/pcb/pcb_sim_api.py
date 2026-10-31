"""
@module pcb.pcb_sim_api

kxc-3 (KICAD_INTERCHANGE_PLAN.md): the SIMULATION doors of an ingested schematic - the deck is built from OUR rows (pcb.custom.kicad_spice), never
copied from KiCad's export.

GET  /api/pcb/{board}/spice-deck   the deck text + its elements, includes, directives, what was skipped and why
POST /api/pcb/{board}/simulate     build the deck and run it through ngspice's shared library (electrodevice.custom.ngspice_shared) - the result
                                   vectors, or a refusal naming what this host lacks (no libngspice here: econ-core has it, KiCad 10.0.6)
POST /api/pcb/export/bench/{bench}   kxc-5: the Bench (Boards on the Bench + connections) as a KiCad schematic - {text, design, report}; the
                                   library symbols come from the KiCad worker (a host with none refuses in words, 503)
kxc-3b: every run is KEPT (pcb.custom.spice_runs: SpiceRun + one SpiceVector per vector) and charted:
GET  /api/pcb/{board}/runs           {ok, rows}  the board's runs, newest first (a refused run is kept, with its reason)
POST /api/pcb/{board}/runs           {deck, result, host?, source?: worker|reference}  a run done elsewhere (a worker with libngspice) -> 201 + its name
GET  /api/pcb/runs/{run}/vectors     {ok, rows}  the run's vectors (name, unit, points, min / max) without their values
GET  /api/pcb/runs/{run}/projection  {ok, rows}  kxc-3c: the run's results on the board's nets - min / max / final (transient) or peak |V| (AC), and
                                   the PCB footholds on each net
GET  /api/pcb/runs/{run}/chart?max=  {ok, rows: [{x, y, series}]}  long form for the named graph pcb-spice-run, at most `max` points per series
GET  /api/pcb/{board}/thermal-spread?run=&h=  bob-3d: where the heat sits - the board as a thin plate in the FEM engine (pcb.custom.thermal_spread):
                                   {ok, summary, hotspots, field: {origin_mm, xs_mm, ys_mm, rise_c}}; h (W/m2K) a knob, default the cited free-air value
A board with no ingested schematic answers 404 in words.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PcbSimAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/pcb/{board}/spice-deck', self, suffix='deck')
            add('/api/pcb/{board}/simulate', self, suffix='simulate')
            add('/api/pcb/export/bench/{bench}', self, suffix='export_bench')
            add('/api/pcb/{board}/runs', self, suffix='runs')
            add('/api/pcb/runs/{run}/vectors', self, suffix='run_vectors')
            add('/api/pcb/runs/{run}/chart', self, suffix='run_chart')
            add('/api/pcb/runs/{run}/projection', self, suffix='run_projection')
            add('/api/pcb/{board}/thermal-spread', self, suffix='thermal_spread')

    def _rows(self, board):
        import inspect
        from pcb.pcb_basis import PCB_CLASSES
        tables = (self.manager.objectTables or {}) if self.manager is not None else {}
        out = {}
        for cls in PCB_CLASSES:
            if cls.__name__ not in ('SchematicSymbol', 'NetEndpoint', 'KiCadArtifact'):
                continue
            keys = [k for k in inspect.signature(cls.__init__).parameters if k not in ('self', 'manager')]
            out[cls.__name__] = [{k: getattr(o, k, None) for k in keys} for o in (tables.get(cls.__name__) or {}).values() if getattr(o, 'board', '') == board]
        return out

    def _deck(self, board, response):
        from pcb.custom import kicad_spice as P
        rows = self._rows(board)
        if not rows.get('SchematicSymbol'):
            response.status = '404 Not Found'
            response.media = {'ok': False, 'error': 'no ingested schematic for %r (POST /api/pcb/ingest first)' % board}
            return None, None
        return rows, P.build_deck(rows)

    def on_get_deck(self, request, response, board):
        rows, d = self._deck(board, response)
        if d is not None:
            response.media = dict({'ok': True, 'board': board}, **{k: v for k, v in d.items()})

    def on_post_simulate(self, request, response, board):
        from electrodevice.custom import ngspice_shared as NS
        rows, d = self._deck(board, response)
        if d is None:
            return
        files = {a['path']: a['content'] for a in rows.get('KiCadArtifact', []) if a['path'] in d['includes']}
        res = NS.run(d['deck'], files)
        import socket
        from pcb.custom import spice_runs as SR
        res = dict(res, run=SR.store(self.manager, board, d['deck'], res, 'local', socket.gethostname()))
        if not res.get('ok'):
            response.status = '503 Service Unavailable' if 'refused' in res else '422 Unprocessable Entity'
        response.media = dict(res, board=board, deck=d['deck'], problems=d['problems'], skipped=d['skipped'])

    def on_get_runs(self, request, response, board):
        from pcb.custom import spice_runs as SR
        response.media = {'ok': True, 'board': board, 'rows': SR.runs(self.manager, board)}

    def on_post_runs(self, request, response, board):
        from pcb.custom import spice_runs as SR
        body = request.get_media() or {}
        if not isinstance(body.get('result'), dict) or not isinstance(body.get('deck'), str):
            response.status, response.media = '400 Bad Request', {'ok': False, 'error': 'body needs {deck: text, result: {ok, plot, vectors}}'}
            return
        source = body.get('source', 'worker')
        if source not in ('worker', 'reference'):
            response.status, response.media = '400 Bad Request', {'ok': False, 'error': 'source must be worker or reference (a local run is /simulate)'}
            return
        name = SR.store(self.manager, board, body['deck'], body['result'], source, str(body.get('host', '')))
        response.status, response.media = '201 Created', {'ok': True, 'run': name, 'rows': SR.runs(self.manager, board)}

    def on_get_run_vectors(self, request, response, run):
        from pcb.custom import spice_runs as SR
        response.media = {'ok': True, 'run': run, 'rows': SR.vectors(self.manager, run)}

    def on_get_run_chart(self, request, response, run):
        from pcb.custom import spice_runs as SR
        try:
            mx = max(10, min(20000, int(request.get_param('max') or 2000)))
        except ValueError:
            mx = 2000
        status, body = SR.chart(self.manager, run, mx)
        response.status = {200: '200 OK', 404: '404 Not Found', 409: '409 Conflict'}[status]
        response.media = body

    def on_get_run_projection(self, request, response, run):
        from pcb.custom import spice_runs as SR
        rows, why = SR.projection(self.manager, '', run)
        if why:
            response.status = '404 Not Found'
        response.media = {'ok': not why, 'run': run, 'rows': rows, 'error': why}

    def on_get_thermal_spread(self, request, response, board):
        from pcb.custom import thermal_spread as TS
        try:
            h = float(request.get_param('h') or TS.H_FREE_AIR)
        except ValueError:
            h = -1.0
        if not 0 < h <= 1000:
            response.status, response.media = '400 Bad Request', {'ok': False, 'error': 'h must be a number of W/(m2 K) in (0, 1000]'}
            return
        summary, hotspots, field, why = TS.spread(self.manager, board, request.get_param('run') or None, h=h)
        if why:
            response.status = '404 Not Found'
        response.media = {'ok': not why, 'board': board, 'summary': summary, 'hotspots': hotspots, 'field': field, 'error': why}

    def on_post_export_bench(self, request, response, bench):
        from board.custom import bench_nets as BN
        from pcb.custom import bench_export as X
        from pcb.custom import pcb_engines as E
        from pcb.custom import schematic_writer as W
        feet, by_id = BN._boards(bench, self.manager)
        if feet is None:
            response.status, response.media = '404 Not Found', {'ok': False, 'error': 'no bench named %r' % bench}
            return
        boards = {bid: {'label': by_id[bid]['label'], 'footholds': f} for bid, f in feet.items()}
        d, mapping, rep = X.design(boards, BN.connections_of(bench, self.manager), bench)
        try:
            libs = X.fetch_libraries(d)
        except E.EngineRefused as e:
            response.status = '503 Service Unavailable'
            response.media = {'ok': False, 'refused': 'no KiCad libraries on this host: %s' % e, 'design': d, 'report': rep}
            return
        text, report = W.write(d, libs, title='%s (Polari bench)' % bench)
        response.media = {'ok': True, 'bench': bench, 'filename': '%s.kicad_sch' % d['board'], 'text': text, 'report': dict(rep, **report)}
