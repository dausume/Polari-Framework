"""
@module pcb.pcb_temperature_api

tmp-1 / tmp-2 (AI-Notes/plans/TEMPERATURE_PLAN.md): the doors of A PCB'S CIRCUIT AT A TEMPERATURE - thin falcon handlers over
pcb.custom.spice_temperature and pcb.custom.temperature_inputs (the bodies live there).

GET    /api/pcb/{board}/temperature-grades                 {ok, rows}  the usual rated ranges, each a sweep (low end, 25 C, high end), with its basis
GET    /api/pcb/{board}/temperature-reach                  {ok, rows}  each deck element: does temperature act on it, through what, its own temperature?
POST   /api/pcb/{board}/simulate-at                        {temp_c}  one run with the whole board at temp_c (kept; 503 in words with no ngspice here)
POST   /api/pcb/{board}/temperature-sweep                  {temps: [C, ...]}  one run per temperature, one sweep name
POST   /api/pcb/{board}/temperature-sweep/{grade}          the same over a grade's low end, 25 C and high end
GET    /api/pcb/{board}/temperature-sweep?sweep=           {ok, rows}  each net at each temperature + the change from 25 C (the newest sweep by default)
GET    /api/pcb/{board}/temperature-ratings?sweep=         {ok, rows}  each part with a rated range against the sweep's temperatures
GET    /api/pcb/{board}/temperature-parts                  {ok, rows}  each part: its rated range and temperature coefficients
GET    /api/pcb/{board}/temperature-inputs/{ref}           {ok, rows}  the four numbers a person can give that part
PUT    /api/pcb/{board}/temperature-inputs/{ref}/{quantity}   {value}  give one (t_min_c, t_max_c, tc1_ppm_k, tc2_ppm_k2 - negatives allowed)
DELETE /api/pcb/{board}/temperature-inputs/{ref}/{quantity}   back to not given
POST   /api/pcb/{board}/temperature-behaviours/{ref}       {t_min_c?, t_max_c?, tc1_ppm_k?, tc2_ppm_k2?, document?, page_table?, url?, origin?}
POST   /api/pcb/temperature-behaviours/by-part/{part_key}  the same for every part whose symbol value or lib_id is part_key
GET    /api/pcb/{board}/part-temperatures?ambient=&mode=   {ok, rows}  tmp-2: each part's own temperature from the board over time
POST   /api/pcb/{board}/simulate-parts                     {ambient_c?, mode?: final|peak}  tmp-2: the board at ambient + each part at its own
"""
from objectTreeDecorators import treeObject, treeObjectInit

_STATUS = {200: '200 OK', 201: '201 Created', 400: '400 Bad Request', 404: '404 Not Found', 422: '422 Unprocessable Entity',
           503: '503 Service Unavailable'}
T_LO, T_HI, MAX_TEMPS = -200.0, 400.0, 12


def _temp(v, what='temp_c'):
    try:
        t = float(v)
    except (TypeError, ValueError):
        return None, '%s needs a number of C, got %r' % (what, v)
    if not T_LO <= t <= T_HI:
        return None, '%s must be within %g .. %g C, got %g' % (what, T_LO, T_HI, t)
    return t, ''


def _run_status(res):
    if res.get('status') == 404:
        return 404
    if res.get('ok'):
        return 200
    return 503 if 'refused' in res else 422


class PcbTemperatureAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/pcb/{board}/temperature-grades', self, suffix='grades')
            add('/api/pcb/{board}/temperature-reach', self, suffix='reach')
            add('/api/pcb/{board}/simulate-at', self, suffix='at')
            add('/api/pcb/{board}/temperature-sweep', self, suffix='sweep')
            add('/api/pcb/{board}/temperature-sweep/{grade}', self, suffix='grade_sweep')
            add('/api/pcb/{board}/temperature-ratings', self, suffix='ratings')
            add('/api/pcb/{board}/temperature-parts', self, suffix='parts')
            add('/api/pcb/{board}/temperature-inputs/{ref}', self, suffix='inputs')
            add('/api/pcb/{board}/temperature-inputs/{ref}/{quantity}', self, suffix='input')
            add('/api/pcb/{board}/temperature-behaviours/{ref}', self, suffix='behaviour')
            add('/api/pcb/temperature-behaviours/by-part/{part_key}', self, suffix='shared_behaviour')
            add('/api/pcb/{board}/part-temperatures', self, suffix='part_temps')
            add('/api/pcb/{board}/simulate-parts', self, suffix='parts_run')

    def _send(self, response, status, body):
        response.status, response.media = _STATUS[status], body

    def on_get_grades(self, request, response, board):
        from pcb.custom import spice_temperature as ST
        self._send(response, 200, {'ok': True, 'board': board, 'rows': ST.grades(board)})

    def on_get_reach(self, request, response, board):
        from pcb.custom import spice_temperature as ST
        rows = ST.reach(self.manager, board)
        self._send(response, 200 if rows else 404, {'ok': bool(rows), 'board': board, 'rows': rows,
                                                     'error': '' if rows else 'no simulation deck for %r (no ingested schematic)' % board})

    def on_post_at(self, request, response, board):
        from pcb.custom import spice_temperature as ST
        t, why = _temp((request.get_media() or {}).get('temp_c'))
        if why:
            return self._send(response, 400, {'ok': False, 'error': why})
        res = ST.run_at(self.manager, board, t)
        self._send(response, _run_status(res), res)

    def _sweep(self, response, board, temps):
        from pcb.custom import spice_temperature as ST
        name, results = ST.sweep(self.manager, board, temps)
        if results and all(r.get('status') == 404 for r in results):
            return self._send(response, 404, {'ok': False, 'error': results[0]['error']})
        ran = [r for r in results if r.get('ok')]
        body = {'ok': bool(ran), 'board': board, 'sweep': name, 'temperatures': temps,
                'runs': [{'temp_c': t, 'run': r.get('run'), 'ok': bool(r.get('ok')), 'why': r.get('refused') or '; '.join(r.get('errors') or [])}
                         for t, r in zip(temps, results)]}
        if not ran:
            body['error'] = 'no temperature ran: %s' % body['runs'][0]['why']
        self._send(response, 200 if ran else (503 if any('refused' in r for r in results) else 422), body)

    def on_post_sweep(self, request, response, board):
        temps = (request.get_media() or {}).get('temps')
        if not isinstance(temps, list) or not 1 <= len(temps) <= MAX_TEMPS:
            return self._send(response, 400, {'ok': False, 'error': 'body needs {temps: [C, ...]} with 1 to %d temperatures' % MAX_TEMPS})
        out = []
        for v in temps:
            t, why = _temp(v, 'each temperature')
            if why:
                return self._send(response, 400, {'ok': False, 'error': why})
            out.append(t)
        self._sweep(response, board, sorted(set(out)))

    def on_post_grade_sweep(self, request, response, board, grade):
        from pcb.custom import spice_temperature as ST
        temps = ST.grade_temps(grade)
        if temps is None:
            return self._send(response, 400, {'ok': False, 'error': 'no grade %r - %s' % (grade, ', '.join(g[0] for g in ST.GRADES))})
        self._sweep(response, board, temps)

    def on_get_sweep(self, request, response, board):
        from pcb.custom import spice_temperature as ST
        rows, why = ST.compare(self.manager, board, request.get_param('sweep') or None)
        self._send(response, 404 if why else 200, {'ok': not why, 'board': board, 'rows': rows, 'error': why})

    def on_get_ratings(self, request, response, board):
        from pcb.custom import spice_temperature as ST
        rows, why = ST.compare(self.manager, board, request.get_param('sweep') or None)
        temps = sorted({r['temp_c'] for r in rows})
        self._send(response, 200, {'ok': True, 'board': board, 'rows': ST.ratings(self.manager, board, temps) if temps else [], 'note': why})

    def on_get_parts(self, request, response, board):
        from pcb.custom import temperature_inputs as TI
        self._send(response, 200, {'ok': True, 'board': board, 'rows': TI.parts(self.manager, board)})

    def on_get_inputs(self, request, response, board, ref):
        from pcb.custom import temperature_inputs as TI
        self._send(response, 200, {'ok': True, 'board': board, 'ref': ref, 'rows': TI.quantities(self.manager, board, ref)})

    def on_put_input(self, request, response, board, ref, quantity):
        from pcb.custom import temperature_inputs as TI
        status, body = TI.set_quantity(self.manager, board, ref, quantity, (request.get_media() or {}).get('value'))
        self._send(response, status, body)

    def on_delete_input(self, request, response, board, ref, quantity):
        from pcb.custom import temperature_inputs as TI
        status, body = TI.clear_quantity(self.manager, board, ref, quantity)
        self._send(response, status, body)

    def on_post_behaviour(self, request, response, board, ref):
        from pcb.custom import temperature_inputs as TI
        status, body = TI.put_behaviour(self.manager, board, ref, '', request.get_media() or {})
        self._send(response, status, body)

    def on_post_shared_behaviour(self, request, response, part_key):
        from pcb.custom import temperature_inputs as TI
        status, body = TI.put_behaviour(self.manager, '', '', part_key, request.get_media() or {})
        self._send(response, status, body)

    def _ambient(self, v):
        from pcb.custom.spice_temperature import ROOM_C
        return _temp(ROOM_C if v in (None, '') else v, 'ambient')

    def on_get_part_temps(self, request, response, board):
        from pcb.custom import spice_temperature as ST
        t, why = self._ambient(request.get_param('ambient'))
        if why:
            return self._send(response, 400, {'ok': False, 'error': why})
        rows, why = ST.part_temperatures(self.manager, board, t, request.get_param('mode') or 'final')
        self._send(response, 200 if rows else 404, {'ok': bool(rows), 'board': board, 'rows': rows, 'error': why})

    def on_post_parts_run(self, request, response, board):
        from pcb.custom import spice_temperature as ST
        body = request.get_media() or {}
        t, why = self._ambient(body.get('ambient_c'))
        mode = body.get('mode') or 'final'
        if why or mode not in ('final', 'peak'):
            return self._send(response, 400, {'ok': False, 'error': why or 'mode must be final or peak'})
        res = ST.run_parts(self.manager, board, t, mode)
        self._send(response, _run_status(res), res)
