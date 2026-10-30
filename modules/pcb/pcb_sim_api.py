"""
@module pcb.pcb_sim_api

kxc-3 (KICAD_INTERCHANGE_PLAN.md): the SIMULATION doors of an ingested schematic - the deck is built from OUR rows (pcb.custom.kicad_spice), never
copied from KiCad's export.

GET  /api/pcb/{board}/spice-deck   the deck text + its elements, includes, directives, what was skipped and why
POST /api/pcb/{board}/simulate     build the deck and run it through ngspice's shared library (electrodevice.custom.ngspice_shared) - the result
                                   vectors, or a refusal naming what this host lacks (no libngspice here: econ-core has it, KiCad 10.0.6)
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
        if not res.get('ok'):
            response.status = '503 Service Unavailable' if 'refused' in res else '422 Unprocessable Entity'
        response.media = dict(res, board=board, deck=d['deck'], problems=d['problems'], skipped=d['skipped'])
