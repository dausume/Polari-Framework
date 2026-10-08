"""
@module board.board_object_api

THE BOARD OBJECT's doors (brd-bo, PCB_FROM_SCRATCH_PLAN §2b) — over THIS server's rows:

GET  /api/board/{board}/pins        the pin assignment (BoardPin rows) + the SoC pins, nets, connectors, runtime profiles, the
                                    board sha and the rules (pins named once, a SoC pin assigned once …)
GET  /api/board/{board}/pins/{pin}  fs-2a (his ruling 2026-10-06): ONE pin's expanded detail — its roles, SoC pin,
                                    port register + bit (PORTx/DDRx/PINx), alternate functions (timer channel, ADC
                                    channel, USART/I2C/SPI signal, INT/PCINT), electrical limits, net, connector, and
                                    `registered_tasks` (RegisterAssignment rows across every FirmwareSolution whose
                                    lives_on names this pin: task, port, solution, lane, cooperating) — every fact
                                    with its DatasheetFact citation or `undetermined`
GET  /api/board/{board}/views       the BoardView rows (rendered out / ingested in, by sha; refusals too)
GET  /api/board/{board}/conflicts   the BoardConflict rows (shown, never auto-resolved)
POST /api/board/{board}/render      body {as: kicad|zephyr|esp-idf|bare-c} → the view's files + sha; a BoardView row (out)
POST /api/board/{board}/ingest      body {as, files: {name: text}} → BoardView (in) + one BoardConflict per disagreement; the
                                    rows are NOT changed

fs-2d (his ask, verbatim: "the power pins have no definitions at all"): GET /api/board/{board}/pins/{pin} no longer
404s for a power/reference connector label (IOREF, RESET, +3V3/5V, GND, VIN, AREF — none of these are BoardPin rows,
board.custom.board_uno only makes one per SoC-backed D/A pin) — board.custom.power_pins.detail_for() answers instead,
carried under `power_reference` (purpose / electrical / typical_uses / assignable=False + why / every physical
location / citations), alongside `parts_that_connect_here` (board.custom.kit_parts.parts_for_pin, his follow-up ask:
the kit parts register a sample firmware is built from) in place of `registered_tasks` (a power rail is never a task
target, so it never has any).

GET  /api/board/kit-parts           every KitPart row (board.custom.kit_parts) + `parts_without_sample` (the names
                                    with no sample_capabilities yet — the backlog for future sample firmwares)
GET  /api/board/kit-parts/{part}    one KitPart row by its bare key (e.g. 'tmp36') or full name ('arduino-starter-kit:tmp36')
"""
import json

import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class BoardObjectAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/{board}/pins', self, suffix='pins')
            add('/api/board/{board}/pins/{pin}', self, suffix='pin_one')
            add('/api/board/{board}/chain/{pin}', self, suffix='chain')   # ucd-0a: the hardware chain of one pin, as rows
            add('/api/board/{board}/views', self, suffix='views')
            add('/api/board/{board}/conflicts', self, suffix='conflicts')
            add('/api/board/{board}/render', self, suffix='render')
            add('/api/board/{board}/ingest', self, suffix='ingest')
            add('/api/board/kit-parts', self, suffix='kit_parts')
            add('/api/board/kit-parts/{part}', self, suffix='kit_part_one')

    def _tables(self):
        from board.custom import board_object as bo
        return bo.tables_from_manager(self.manager)

    def _rows(self, board, response):
        from board.custom import board_object as bo
        try:
            return bo.rows_for(board, self._tables())
        except bo.BoardObjectRefused as e:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': str(e)}
            return None

    def on_get_pins(self, request, response, board):
        from board.custom import board_object as bo
        r = self._rows(board, response)
        if r is None:
            return
        response.media = {'ok': True, 'board': r['board'], 'boardSha': bo.board_sha(r), 'soc': r['soc'], 'pins': r['pins'],
                          'socPins': r['soc_pins'], 'nets': r['nets'], 'connectors': r['connectors'], 'connectorPins': r['connector_pins'],
                          'hardware': r['hardware'], 'runtimeProfiles': r['profiles'], 'rules': bo.validate(r) or ['ok']}

    def on_get_pin_one(self, request, response, board, pin):
        """fs-2a: ONE pin's expanded detail (his ruling: "an expanded detail view of the register and info about
        it"), derived from BoardPin + SocPin + DatasheetFact rows — nothing hand-written per pin — plus the
        `registered_tasks` claiming it across every FirmwareSolution on this server."""
        from board.custom import board_object as bo
        from board.custom.soc_atmega328p import FUNCTION_PERIPHERAL
        from board.custom import power_pins as PP
        from board.custom import kit_parts as KP
        r = self._rows(board, response)
        if r is None:
            return
        bp = bo.pin_by_canonical(r, pin)
        if bp is None:
            if PP.is_power_reference_label(pin):
                self._power_pin_detail(request, response, r, pin, KP)
                return
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': '%s has no pin %s (GET /api/board/%s/pins lists them)' % (r['board'], pin, r['board'])}
            return
        soc_pin = next((s for s in r['soc_pins'] if s['pin'] == bp.get('soc_pin')), None)
        functions = json.loads(soc_pin['functions_json']) if soc_pin else []
        alt = []
        for fn in functions:
            peripheral, signal = FUNCTION_PERIPHERAL.get(fn, ('', fn))
            kind = ('timer channel' if peripheral.startswith('TIMER') else 'ADC channel' if peripheral == 'ADC'
                    else 'USART signal' if peripheral == 'USART0' else 'I2C signal' if peripheral == 'TWI'
                    else 'SPI signal' if peripheral == 'SPI' else 'external interrupt' if fn in ('INT0', 'INT1')
                    else 'pin-change interrupt' if fn.startswith('PCINT') else 'other')
            alt.append({'function': fn, 'peripheral': peripheral or 'undetermined', 'signal': signal, 'kind': kind,
                        'fact': (soc_pin or {}).get('fact', '') or 'undetermined'})
        electrical = json.loads(bp.get('electrical_json') or '{}')
        connector_pin = next((c for c in r['connector_pins'] if c.get('board_pin') == pin), None)
        registered = self._registered_tasks('%s:%s' % (r['board'], pin))
        response.media = {
            'ok': True, 'board': r['board'], 'pin': pin, 'roles': [bp.get('function') or 'gpio'],
            'soc_pin': bp.get('soc_pin', ''),
            'register': {'port': (soc_pin or {}).get('port', '') or 'undetermined', 'bit': (soc_pin or {}).get('bit', None),
                        'package_pin': (soc_pin or {}).get('package_pin', '') or 'undetermined',
                        'default_function': (soc_pin or {}).get('default_function', '') or 'undetermined',
                        'fact': (soc_pin or {}).get('fact', '') or 'undetermined'},
            'alternate_functions': alt,
            'current_assignment': {'function': bp.get('function', ''), 'peripheral': bp.get('peripheral', ''),
                                   'signal': bp.get('signal', ''), 'firmware_symbol': bp.get('firmware_symbol', '')},
            'electrical': electrical or {'undetermined': 'no electrical facts cited for this pin'},
            'net': bp.get('net', ''), 'connector': connector_pin.get('connector') if connector_pin else '',
            'connector_number': connector_pin.get('number') if connector_pin else None,
            'facts': json.loads(bp.get('facts_json') or '[]'),
            'registered_tasks': registered, 'unregistered': not registered,
        }

    def on_get_chain(self, request, response, board, pin):
        """ucd-0a (UNO_CORE_DEMO_PLAN.md §5f): GET /api/board/<board>/chain/<pin> — THE HARDWARE CHAIN of one pin as
        ordered rows a configured table shows as is: board pin → SoC pin → every PinFunction → the PeripheralSignals →
        the Peripherals → their Registers (the ones with fields for THIS pin first) → the cited RegisterFields that
        configure this pin or its signals. `ref` is the Class:name link of each hop (the `refs` column format), so a
        novice clicks any hop into its object page and walks on from there. Computed over the live tables (the same
        rows the object pages read); the seed when the server has none. `pol board chain <board> <pin>` prints it."""
        from board.custom import board_object as bo
        from board.custom import hardware_chain as HC
        tables = self._tables()
        if not tables.get('PinFunction'):   # a server booted before ucd-0a's rows landed: the seed's chain, said so
            tables = bo.seed_tables()
            note = 'seed (the live server has no PinFunction rows yet)'
        else:
            note = 'live'
        try:
            hops = HC.chain_for(board, pin, tables)
        except bo.BoardObjectRefused as e:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': str(e)}
            return
        except KeyError as e:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': '%s (GET /api/board/%s/pins lists them)' % (e.args[0], bo.board_name(board))}
            return
        response.media = {'ok': True, 'board': bo.board_name(board), 'pin': pin, 'source': note, 'rows': hops}

    def _power_pin_detail(self, request, response, r, pin, KP):
        """fs-2d: the pin-detail door for a power/reference connector label (never a BoardPin row — IOREF, RESET,
        +3V3, +5V, GND, VIN, AREF). Shaped like on_get_pin_one's normal payload (same top-level keys a caller already
        expects: soc_pin/register/alternate_functions/electrical/net/connector/facts/registered_tasks) with the
        SoC-specific ones honestly empty, PLUS `power_reference` (board.custom.power_pins.detail_for) and
        `parts_that_connect_here` (board.custom.kit_parts.parts_for_pin, his follow-up ask) in place of the
        (always-empty, for a power rail) registered_tasks."""
        from board.custom import power_pins as PP
        label = PP.label_for(pin)
        parts = KP.parts_for_pin(pin, r)
        detail = PP.detail_for(pin, r, parts_that_connect_here=parts)
        locs = detail['locations']
        response.media = {
            'ok': True, 'board': r['board'], 'pin': label, 'roles': [detail['role']], 'soc_pin': '',
            'register': {'port': 'undetermined', 'bit': None, 'package_pin': 'undetermined',
                        'default_function': 'undetermined', 'fact': 'undetermined'},
            'alternate_functions': [],
            'current_assignment': {'function': detail['role'], 'peripheral': '', 'signal': '', 'firmware_symbol': ''},
            'electrical': detail['electrical'], 'net': detail['net'],
            'connector': locs[0]['connector'] if locs else '', 'connector_number': locs[0]['number'] if locs else None,
            'facts': [], 'registered_tasks': [], 'unregistered': False,
            'power_reference': detail, 'parts_that_connect_here': parts,
        }

    def on_get_kit_parts(self, request, response):
        from board.custom import kit_parts as KP
        rows = KP.rows()
        # `rows` is the convention class-rows-table's dataPath reads (payload.rows ?? []); `parts` is the same list,
        # named for anyone reading this door directly (its own docstring, tests — no `pol board kit-parts` CLI yet).
        response.media = {'ok': True, 'kit': KP.KIT, 'rows': rows, 'parts': rows, 'parts_without_sample': KP.parts_without_sample(),
                          'parts_without_sample_how': 'KitPart rows with an empty sample_capabilities — the backlog for future sample firmwares'}

    def on_get_kit_part_one(self, request, response, part):
        from board.custom import kit_parts as KP
        row = KP.by_name(part) or KP.by_name('%s:%s' % (KP.KIT, part))
        if row is None:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no kit part %r (GET /api/board/kit-parts lists them)' % part}
            return
        response.media = {'ok': True, 'part': row}

    def _cross_module_rows(self, cls):
        """Raw attribute rows of a class NOT owned by this module (RegisterAssignment/ScheduleSlot are cmod's) —
        objectTables is server-wide, but board.custom.board_object.as_dict looks classes up in board_basis only, so
        a cross-module class is read directly off the live objects here instead."""
        if self.manager is None:
            return []
        return [{k: v for k, v in vars(r).items() if not k.startswith('_') and k != 'manager'}
                for r in ((self.manager.objectTables or {}).get(cls, {}) or {}).values()]

    def _registered_tasks(self, lives_on):
        """[{task, port, solution, lane, status, cooperating}, ...] — RegisterAssignment rows across EVERY
        FirmwareSolution on this server that claim this exact BoardPin (fs-2a: "the Registered Tasks")."""
        asg = self._cross_module_rows('RegisterAssignment')
        sched = {(s.get('solution'), s.get('task')): s.get('lane', '') for s in self._cross_module_rows('ScheduleSlot')}
        out = []
        for a in asg:
            if a.get('lives_on') != lives_on:
                continue
            out.append({'task': a.get('task', ''), 'port': a.get('port', ''), 'solution': a.get('solution', ''),
                        'lane': sched.get((a.get('solution'), a.get('task')), ''), 'status': a.get('status', ''),
                        'cooperating': a.get('status') != 'conflict'})
        return sorted(out, key=lambda x: (x['solution'], x['task']))

    def _list(self, cls, board):
        from board.custom import board_object as bo
        rows = [r for r in self._tables_cls(cls) if r.get('board') == bo.board_name(board)]
        return sorted(rows, key=lambda r: str(r.get('at') or r.get('detected_at') or ''), reverse=True)

    def _tables_cls(self, cls):
        from board.custom import board_object as bo
        return [bo.as_dict(r, cls) for r in ((self.manager.objectTables or {}).get(cls, {}) or {}).values()] if self.manager is not None else []

    def on_get_views(self, request, response, board):
        response.media = {'ok': True, 'board': board, 'views': self._list('BoardView', board)}

    def on_get_conflicts(self, request, response, board):
        rows = self._list('BoardConflict', board)
        response.media = {'ok': True, 'board': board, 'conflicts': rows, 'open': sum(1 for r in rows if r.get('state') == 'open'),
                          'note': 'shown, never auto-resolved — a person edits the rows or the view\'s source'}

    @staticmethod
    def _body(request, response):
        try:
            raw = request.bounded_stream.read() or b''
            return json.loads(raw) if raw.strip() else {}
        except ValueError as e:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
            return None

    def on_post_render(self, request, response, board):
        from board.custom import ingest as I
        body = self._body(request, response)
        r = None if body is None else self._rows(board, response)
        if r is None:
            return
        res, row = I.render_row(board, str(body.get('as') or ''), r=r, path='(api)')
        I.save_rows(self.manager, views=[row])
        if res is None:
            response.status = falcon.HTTP_409
            response.media = {'ok': False, 'refused': True, 'error': row['refusal'], 'view': row}
            return
        response.media = {'ok': True, 'view': row, 'files': res['files'], 'sha256': res['sha256'], 'boardSha': res['board_sha']}

    def on_post_ingest(self, request, response, board):
        from board.custom import ingest as I
        from board.custom.views import ViewRefused
        body = self._body(request, response)
        r = None if body is None else self._rows(board, response)
        if r is None:
            return
        files = body.get('files') or {}
        if not isinstance(files, dict) or not files:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'body needs files: {name: text}'}
            return
        try:
            res = I.ingest(board, files, body.get('as') or None, r=r, path='(api)')
        except ViewRefused as e:
            response.status = falcon.HTTP_409
            response.media = {'ok': False, 'error': str(e)}
            return
        saved = I.save_rows(self.manager, views=[res['view']], conflicts=res['conflicts'])
        response.status = falcon.HTTP_201
        response.media = {'ok': True, 'view': res['view'], 'conflicts': res['conflicts'], 'saved': saved,
                          'note': 'the rows are unchanged; %d conflict(s) recorded' % len(res['conflicts'])}
