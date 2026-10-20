"""
@module board.firmware_state_api

fst-1 (HARDWARE_BENCH_CONVERGENCE_PLAN.md §12): the doors of THE FIRMWARE STATE-OBJECTS PAGE — thin falcon handlers over board.custom.firmware_state
(derived on every read from the config's rendered sources, the pinned wire contract and the generated header; cached a minute).

GET /api/firmware-state/{config}            the whole document (objects, fields, enums, findings, counts) + `rows` = the objects (a configured table)
GET /api/firmware-state/{config}/fields     one row per field: C type, size, tag, proto type, direction, controls, persisted, writers, readers, finding
GET /api/firmware-state/{config}/enums      one row per enum value / enum-like define: value, meaning, set_by, compared_by
GET /api/firmware-state/{config}/findings   a field nobody writes beyond zeroing, nobody reads, …
GET /api/firmware-state/{config}/live?session=  the wire fields with their live values (the class row this config reports into; the twin session's status; the bridge)
GET /api/firmware-state/configs             the configs this page can show (the UNO's firmware variants), for the page's picker table

A refusal (no such config, a source that will not parse) answers {ok: false, error: <plain words>} with 404 / 422.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FirmwareStateAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/firmware-state/configs', self, suffix='configs')
            add('/api/firmware-state/{config}', self, suffix='doc')
            add('/api/firmware-state/{config}/fields', self, suffix='fields')
            add('/api/firmware-state/{config}/enums', self, suffix='enums')
            add('/api/firmware-state/{config}/findings', self, suffix='findings')
            add('/api/firmware-state/{config}/live', self, suffix='live')

    def _doc(self, response, config):
        from board.custom import firmware_state as FS
        if not config or config == 'undefined':
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': 'name the config: /api/firmware-state/<config> (GET /api/firmware-state/configs lists them; the page takes ?config=)'}
            return None
        try:
            return FS.derive(config, self.manager)
        except FS.StateRefused as e:
            response.status = e.status
            response.media = {'ok': False, 'error': str(e)}
        except Exception as e:   # noqa: BLE001 — a source that will not parse is said in words, never a 500 wall
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False, 'error': 'the state objects of %s could not be derived: %s' % (config, str(e)[:400])}
        return None

    def _rows(self, response, config, which):
        from board.custom import firmware_state as FS
        doc = self._doc(response, config)
        if doc is None:
            return
        rows = FS.rows(doc, which)
        response.media = {'ok': True, 'config': config, 'rows': rows, 'count': len(rows), 'counts': doc['counts'], 'derived_at': doc['derived_at']}

    def on_get_configs(self, request, response):
        from board.custom import variants as V
        from board.custom.installer import _rows
        rows = _rows(self.manager, 'FirmwareVariant') or V.SEED_FIRMWARE_VARIANTS
        out = []
        for r in rows:
            g = (lambda k: r.get(k, '') if isinstance(r, dict) else getattr(r, k, ''))
            if g('board_definition') in ('arduino-uno-r3', '', None):
                out.append({'name': g('name'), 'title': g('title'), 'app': g('app'), 'classes_json': g('classes_json')})
        response.media = {'ok': True, 'rows': out, 'count': len(out)}

    def on_get_doc(self, request, response, config):
        doc = self._doc(response, config)
        if doc is not None:
            response.media = dict(doc, rows=doc['objects'])

    def on_get_fields(self, request, response, config):
        self._rows(response, config, 'fields')

    def on_get_enums(self, request, response, config):
        self._rows(response, config, 'enums')

    def on_get_findings(self, request, response, config):
        self._rows(response, config, 'findings')

    def on_get_live(self, request, response, config):
        from board.custom import firmware_state as FS
        if self._doc(response, config) is None:
            return
        response.media = FS.live(self.manager, config, request.get_param('session') or '')
