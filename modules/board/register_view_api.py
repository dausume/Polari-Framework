"""
@module board.register_view_api

rm-3 doors (REGISTER_MAPPING_PLAN.md §5) for the Registers bench view, derived on every read (model: `board.custom.register_view`). Under the literal `socs`
segment beside the register profile's doors (no clash with `/api/board/{board}/...`):

GET /api/board/socs                                      the chips the view knows: soc, board, registers, fields, state
GET /api/board/socs/{soc}/register-categories            one row per REGISTER CATEGORY: domain, category, count, registers, state (the C3: count 0, "not ingested yet")
GET /api/board/socs/{soc}/registers[?category=C]         the registers of one register category (or all): title, address, reset, categories, roles, fields, cite
GET /api/board/socs/{soc}/registers/{name}[?view=fields|settings|atoms]
        fields = every bit field with its access word spelled out (on_read / on_write from the RegisterAccessKind row), values, pin, signal, roles, cite;
        settings = the firmware's RegisterSetting / RegisterFieldSetting rows for it (phase, value, the field's meaning, the owning task);
        atoms = the C atoms whose body touches it. 404 a register not on the chip; 422 unknown view.
GET /api/board/socs/{soc}/fields/{name}/pins             the board pin the field drives + its lifecycle stages (rm-1); a field with no pin = no rows, said
GET /api/board/socs/{soc}/pins                           THE OTHER WAY IN: every pin with its board name, its functions and how many register fields reach it
GET /api/board/socs/{soc}/pins/{pin}/uses[?kind=K]       a pin (D2 or PD2) -> its register fields + their register categories, the firmware's settings of them, the
        Catom assertions naming it, the HAL variable at it, the C atoms that use it (certain: a uses() annotation or an assertion) or only share its register;
        `kind` narrows to one kind (register field | firmware setting | Catom assertion | HAL variable | C atom). 404 a pin the chip lacks.
An empty name / category (nothing clicked yet) answers no rows with a note; an unknown soc is 422.
"""
import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from board.custom import register_view as RV


class RegisterViewAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/socs', self, suffix='socs')
            add('/api/board/socs/{soc}/registers', self, suffix='registers')
            add('/api/board/socs/{soc}/register-categories', self, suffix='categories')
            add('/api/board/socs/{soc}/pins', self, suffix='pins')
            add('/api/board/socs/{soc}/pins/{pin}/uses', self, suffix='pin_uses')
            add('/api/board/socs/{soc}/registers/{name}', self, suffix='register')
            add('/api/board/socs/{soc}/fields/{name}/pins', self, suffix='field_pins')

    def _tables(self):
        t = getattr(self.manager, 'objectTables', None) or {}
        return {c: list((t.get(c) or {}).values()) for c in ('Register', 'RegisterField') if t.get(c)}

    def _ok(self, response, soc, view, rows, **extra):
        response.media = dict({'ok': True, 'soc': soc, 'view': view, 'count': len(rows), 'rows': rows}, **extra)

    def _fail(self, response, status, text):
        response.status = status
        response.media = {'ok': False, 'error': text}

    def _soc(self, response, soc):
        if soc not in RV.SOCS:
            self._fail(response, falcon.HTTP_422, 'soc must be one of %s' % ', '.join(RV.SOCS))
            return False
        return True

    def on_get_socs(self, request, response):
        rows = RV.socs(self._tables())
        response.media = {'ok': True, 'count': len(rows), 'rows': rows}

    def on_get_categories(self, request, response, soc):
        if self._soc(response, soc):
            self._ok(response, soc, 'register-categories', RV.categories(soc, self._tables()))

    def on_get_pins(self, request, response, soc):
        if self._soc(response, soc):
            self._ok(response, soc, 'pins', RV.pins(soc, self._tables()))

    def on_get_pin_uses(self, request, response, soc, pin):
        if not self._soc(response, soc):
            return
        t = getattr(self.manager, 'objectTables', None) or {}
        cm = {c: list((t.get(c) or {}).values()) or None for c in ('CatomAssertion', 'CatomVariable', 'FirmwareVariant')}
        rows = RV.pin_uses(soc, pin, self._tables(), cm)
        if rows is None:
            return self._fail(response, falcon.HTTP_404, 'no pin %r on %s' % (pin, soc))
        kind = request.get_param('kind') or ''
        self._ok(response, soc, 'uses', [r for r in rows if not kind or r['kind'] == kind], pin=pin, soc_pin=RV.resolve(soc, pin))

    def on_get_registers(self, request, response, soc):
        if self._soc(response, soc):
            self._ok(response, soc, 'registers', RV.registers(soc, request.get_param('category') or '', self._tables()))

    def on_get_register(self, request, response, soc, name):
        if not self._soc(response, soc):
            return
        view = request.get_param('view') or 'fields'
        if view not in RV.DETAIL_VIEWS:
            return self._fail(response, falcon.HTTP_422, 'view must be one of %s' % ', '.join(RV.DETAIL_VIEWS))
        rows = RV.detail(soc, name, view, self._tables())
        if rows is None:
            return self._fail(response, falcon.HTTP_404, 'no register %r on %s' % (name, soc))
        self._ok(response, soc, view, rows, register=name)

    def on_get_field_pins(self, request, response, soc, name):
        if not self._soc(response, soc):
            return
        rows = RV.field_pins(soc, name, self._tables())
        if rows is None:
            return self._fail(response, falcon.HTTP_404, 'no register field %r on %s' % (name, soc))
        self._ok(response, soc, 'pins', rows, field=name, **({} if rows else {'note': 'this field drives no pin (it configures the peripheral or reports)'}))
