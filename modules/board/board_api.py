"""
@module board.board_api

GET  /api/board                  the definitions' rule summary (RULE 1 per usb_rule, RULE 2, simulated)
GET  /api/board/detect           PREVIEW: hwmap's scanner on THIS server's host, matched — nothing stored
POST /api/board/detect           UPSERT: body = a host snapshot (`pol board detect --push`, the shape of
                                 board.custom.detect.scan_host()) or empty (scan this server's host); matched
                                 instances become BoardInstance rows; unadmitted devices are listed, never stored
GET  /api/board/roads            every road with its steps and status
GET  /api/board/facts?board=     the cited DatasheetFacts of one board
GET  /api/board/engines          where each board engine WOULD run (the engines ladder; nothing is run)
GET  /api/board/builds           every FirmwareBuild row (state, sizes, sha, where it was flashed)
POST /api/board/builds           UPSERT one FirmwareBuild (`pol board build|flash --api`): body {build: {...}, instance?:
                                 {name, firmware_sha, last_flash_at}} — a flashed build stamps its BoardInstance
GET  /api/board/sim-costs        the measured twin costs (BoardSimCost — the yardstick before another twin, plan §8a)

brd-fi: the firmware installer's doors (/api/board/installer…, /api/board/variants, /api/board/builds/{b}/compat) live in
board.installer_api.
"""
import json
import time

import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class BoardAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board', self, suffix='summary')
            add('/api/board/detect', self, suffix='detect')
            add('/api/board/roads', self, suffix='roads')
            add('/api/board/facts', self, suffix='facts')
            add('/api/board/engines', self, suffix='engines')
            add('/api/board/builds', self, suffix='builds')
            add('/api/board/sim-costs', self, suffix='sim_costs')

    def _table(self, class_name):
        return ((self.manager.objectTables or {}).get(class_name, {}) or {}) if self.manager is not None else {}

    def _rows(self, class_name):
        return list(self._table(class_name).values())

    def on_get_summary(self, request, response):
        from board.custom.board_engines import rule2_ok
        boards = self._rows('BoardDefinition')
        by_rule = {}
        for b in boards:
            by_rule.setdefault(b.usb_rule, []).append(b.name)
        rule2_bad = [b.name for b in boards if not all(rule2_ok(e) for e in json.loads(b.toolchain_engines_json or '[]'))]
        response.media = {'ok': True, 'devices': len(boards), 'adapters': len(self._rows('AdapterDefinition')),
                          'usbRule': {k: sorted(v) for k, v in by_rule.items()}, 'rule2Violations': rule2_bad,
                          'simulated': sorted(b.name for b in boards if b.simulated),
                          'instances': len(self._rows('BoardInstance'))}

    def _match(self, snapshot):
        from board.custom.detect import match
        return match(snapshot, self._rows('BoardDefinition'), self._rows('AdapterDefinition'))

    def on_get_detect(self, request, response):
        from board.custom.detect import scan_host
        result = self._match(scan_host())
        response.media = dict(result, ok=True, stored=False,
                              note='a preview on the server\'s own host; a container sees no host USB — run `pol board detect --push` on the host')

    def on_post_detect(self, request, response):
        from board.custom.detect import scan_host
        from board.board_basis import BoardInstance
        try:
            raw = request.bounded_stream.read() or b''
            snap = json.loads(raw) if raw.strip() else scan_host()
        except Exception as e:  # noqa: BLE001
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
            return
        if not isinstance(snap, dict) or 'usb' not in snap or not snap.get('host'):
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'a host snapshot needs host + usb + serial (python3 -m board.custom.detect --snapshot)'}
            return
        result = self._match(snap)
        by_name = {getattr(r, 'name', ''): r for r in self._rows('BoardInstance')}   # objectTables is keyed by id, not name
        stored = 0
        for inst in result['instances']:
            fields = {k: v for k, v in inst.items() if k != 'description'}
            fields['last_seen_at'] = fields.get('last_seen_at') or time.strftime('%Y-%m-%dT%H:%M:%S')
            row = by_name.get(fields['name'])
            if row is not None:
                for k, v in fields.items():
                    if k == 'target_board' and getattr(row, 'target_board', ''):
                        continue   # a person's answer is never overwritten by a scan
                    setattr(row, k, v)
            else:
                row = BoardInstance(manager=self.manager, **fields)
            try:
                self.manager.db.saveInstanceInDB(row)
                stored += 1
            except Exception:  # noqa: BLE001
                pass
        response.status = falcon.HTTP_201
        response.media = dict(result, ok=True, stored=stored)

    def on_get_roads(self, request, response):
        response.media = {'ok': True, 'roads': [{'road': r.name, 'board': r.board, 'status': r.status, 'steps': json.loads(r.steps_json or '[]'),
                                                 'conceptNode': r.concept_node} for r in sorted(self._rows('Road'), key=lambda r: r.name)]}

    def on_get_facts(self, request, response):
        board = request.get_param('board') or ''
        facts = [f for f in self._rows('DatasheetFact') if not board or f.board == board]
        response.media = {'ok': True, 'board': board,
                          'facts': [{'key': f.fact_key, 'value': f.value, 'unit': f.unit, 'document': f.document, 'revision': f.revision,
                                     'where': f.page_table, 'url': f.url, 'notes': f.notes} for f in facts],
                          'note': '' if facts else 'no cited facts for %s yet — its road\'s first step' % (board or 'any board')}

    def on_get_engines(self, request, response):
        from board.custom.board_engines import placement
        response.media = dict(placement(), ok=True)

    _BUILD_KEYS = ('name', 'board_definition', 'state', 'size_text', 'size_data', 'size_bss', 'artifact_sha256', 'source_sha',
                   'built_at', 'flashed_to', 'template', 'notes', 'variant', 'header_sha256', 'tag_order_json')

    def on_get_builds(self, request, response):
        rows = sorted(self._rows('FirmwareBuild'), key=lambda r: getattr(r, 'built_at', '') or '', reverse=True)
        response.media = {'ok': True, 'builds': [{k: getattr(r, k, '') for k in self._BUILD_KEYS} for r in rows]}

    def on_post_builds(self, request, response):
        from board.board_basis import FirmwareBuild
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception as e:  # noqa: BLE001
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
            return
        b = body.get('build') or {}
        if not b.get('name') or b.get('state') not in ('generated', 'built', 'refused', 'flashed'):
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'build needs a name and a state of generated | built | refused | flashed'}
            return
        import inspect
        allowed = set(inspect.signature(FirmwareBuild.__init__).parameters) - {'self', 'manager'}
        fields = {k: v for k, v in b.items() if k in allowed}
        row = next((r for r in self._rows('FirmwareBuild') if getattr(r, 'name', '') == fields['name']), None)
        if row is None:
            row = FirmwareBuild(manager=self.manager, **fields)
        else:
            for k, v in fields.items():
                setattr(row, k, v)
        stamped = None
        inst = body.get('instance') or {}
        if fields.get('state') == 'flashed' and inst.get('name'):
            target = next((r for r in self._rows('BoardInstance') if getattr(r, 'name', '') == inst['name']), None)
            if target is None:
                response.status = falcon.HTTP_409
                response.media = {'ok': False, 'error': 'flashed to %r, but no such BoardInstance — `pol board detect --push` first' % inst['name']}
                return
            if inst.get('firmware_sha') != fields.get('artifact_sha256'):
                response.status = falcon.HTTP_409
                response.media = {'ok': False, 'error': 'the instance stamp names a different firmware than the build'}
                return
            target.firmware_sha = inst['firmware_sha']
            target.last_flash_at = inst.get('last_flash_at', '')
            stamped = target
        try:
            self.manager.db.saveInstanceInDB(row)
            if stamped is not None:
                self.manager.db.saveInstanceInDB(stamped)
        except Exception:  # noqa: BLE001
            pass
        response.status = falcon.HTTP_201
        response.media = {'ok': True, 'build': fields['name'], 'state': fields['state'], 'stamped': getattr(stamped, 'name', '')}

    def on_get_sim_costs(self, request, response):
        response.media = {'ok': True, 'costs': [{k: getattr(r, k, '') for k in ('board', 'twin', 'object_count', 'state_bytes', 'cycles_per_s', 'host_class', 'measured_at', 'notes')}
                                               for r in self._rows('BoardSimCost')]}
