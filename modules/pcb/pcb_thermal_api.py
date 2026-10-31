"""
@module pcb.pcb_thermal_api

bob-3g (BENCH_BOARDS_PLAN bob-3): the doors of WHAT A PERSON GIVES the thermal views and of THE BOARD OVER TIME - thin falcon handlers over
pcb.custom.thermal_inputs and pcb.custom.thermal_transient (the bodies live there).

GET    /api/pcb/{board}/thermal-parts                     {ok, rows}  one row per placed part: run / given / used power, its datasheet model
GET    /api/pcb/{board}/thermal-inputs/{ref}              {ok, rows}  every number a person can give that part, one row each
PUT    /api/pcb/{board}/thermal-inputs/{ref}/{quantity}   {value}  give one number (power_w, on_s, period_s, tj_max_c, rth_ja_k_w, r<i>_k_w, tau<i>_s)
DELETE /api/pcb/{board}/thermal-inputs/{ref}/{quantity}   back to 'not given' (power_w: the run's figure is used again)
POST   /api/pcb/{board}/thermal-models/{ref}              {foster: [[R K/W, tau s], ...], tj_max_c?, rth_ja_k_w?, reference?, document?, revision?,
                                                           page_table?, url?, conditions?, origin?}  a whole datasheet model WITH its citation
POST   /api/pcb/thermal-models/by-part/{part_key}         the same, for every placed part whose symbol value or lib_id is part_key (one datasheet,
                                                           many boards)
GET    /api/pcb/{board}/thermal-transient?run=&h=&t_end=&ambient=   {ok, summary, junctions, chart}  the board over time + each part's junction
A bad number is 400 in words; a board with nothing to solve answers 404 with the reason.
"""
import json

from objectTreeDecorators import treeObject, treeObjectInit

_STATUS = {200: '200 OK', 400: '400 Bad Request', 404: '404 Not Found'}


class PcbThermalAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/pcb/{board}/thermal-parts', self, suffix='parts')
            add('/api/pcb/{board}/thermal-inputs/{ref}', self, suffix='inputs')
            add('/api/pcb/{board}/thermal-inputs/{ref}/{quantity}', self, suffix='input')
            add('/api/pcb/{board}/thermal-models/{ref}', self, suffix='model')
            add('/api/pcb/thermal-models/by-part/{part_key}', self, suffix='shared_model')
            add('/api/pcb/{board}/thermal-transient', self, suffix='transient')

    def on_get_parts(self, request, response, board):
        from pcb.custom import thermal_inputs as TI
        response.media = {'ok': True, 'board': board, 'rows': TI.parts(self.manager, board)}

    def on_get_inputs(self, request, response, board, ref):
        from pcb.custom import thermal_inputs as TI
        response.media = {'ok': True, 'board': board, 'ref': ref, 'rows': TI.quantities(self.manager, board, ref)}

    def on_put_input(self, request, response, board, ref, quantity):
        from pcb.custom import thermal_inputs as TI
        body = request.get_media() or {}
        status, out = TI.set_quantity(self.manager, board, ref, quantity, body.get('value') if isinstance(body, dict) else None)
        response.status, response.media = _STATUS[status], out

    def on_delete_input(self, request, response, board, ref, quantity):
        from pcb.custom import thermal_inputs as TI
        status, out = TI.clear_quantity(self.manager, board, ref, quantity)
        response.status, response.media = _STATUS[status], out

    def _model(self, request, response, name, fields):
        from pcb.custom import thermal_inputs as TI
        from materialsScience.engines.thermal_rc import check_stages
        body = request.get_media() or {}
        stages = body.get('foster') if isinstance(body, dict) else None
        bad = 'foster must be a list of [R K/W, tau s] pairs' if not isinstance(stages, list) else check_stages(stages)
        nums = {}
        for k in ('tj_max_c', 'rth_ja_k_w'):
            try:
                nums[k] = float(body.get(k) or 0)
            except (TypeError, ValueError):
                bad = bad or '%s needs a number' % k
        if not bad and body.get('reference', 'board') not in ('board', 'case'):
            bad = 'reference must be board or case (the place the board model gives)'
        if not bad and len(stages) > TI.STAGES:
            bad = 'at most %d Foster stages' % TI.STAGES
        if bad:
            response.status, response.media = _STATUS[400], {'ok': False, 'error': bad}
            return
        text = {k: str(body.get(k) or '') for k in ('document', 'revision', 'page_table', 'url', 'conditions', 'notes')}
        o = TI._save(self.manager, 'PartThermalModel', name, dict(fields, foster_json=json.dumps([[float(r), float(t)] for r, t in stages]),
                                                                  reference=body.get('reference', 'board'), origin=str(body.get('origin') or 'cited')
                                                                  if text['document'] else 'given, no document named', **nums, **text))
        response.status, response.media = '201 Created', {'ok': True, 'name': name, 'model': {k: TI._get(o, k) for k in ('board', 'ref', 'part_key', 'foster_json',
                                                                                                                            'tj_max_c', 'rth_ja_k_w', 'origin')}}

    def on_post_model(self, request, response, board, ref):
        self._model(request, response, '%s:%s' % (board, ref), {'board': board, 'ref': ref})

    def on_post_shared_model(self, request, response, part_key):
        self._model(request, response, part_key, {'board': '', 'ref': '', 'part_key': part_key})

    def on_get_transient(self, request, response, board):
        from board.custom.board_details import _num
        from pcb.custom import thermal_spread as TS
        from pcb.custom import thermal_transient as TT
        try:
            h = float(request.get_param('h') or TS.H_FREE_AIR)
        except ValueError:
            h = -1.0
        if not 0 < h <= 1000:
            response.status, response.media = _STATUS[400], {'ok': False, 'error': 'h must be a number of W/(m2 K) in (0, 1000]'}
            return
        summary, junctions, chart, why = TT.transient(self.manager, board, request.get_param('run') or None, h=h,
                                                      t_end=_num(request.params, 't_end', 0, 0, TT.T_END_MAX) or None,
                                                      ambient_c=_num(request.params, 'ambient', TS.AMBIENT_C, -60, 200))
        if why:
            response.status = _STATUS[404]
        response.media = {'ok': not why, 'board': board, 'summary': summary, 'junctions': junctions, 'chart': chart, 'error': why}
