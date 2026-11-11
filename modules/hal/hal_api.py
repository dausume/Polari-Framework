"""
@module hal.hal_api

The HAL doors (hal-0), derived on every read from hal.custom.generate (nothing generated is stored):

GET /api/hal/socs                                   the chips the HAL reaches: soc, title, arch, units resolved / total, facts from
GET /api/hal/operations                             the generalized vocabulary (HalOperation rows; the seed when no rows are loaded)
GET /api/hal/mechanisms                             the access mechanisms (HalAccessMechanism rows; the seed when none are loaded)
GET /api/hal/socs/{soc}/units[?pins=A,B&board=B]    one row per operation x pin: key, status, macro, the mechanisms, why (all pins
                                                    the cited tables reach when `pins` is absent; `board` reads pins as board pins)
GET /api/hal/socs/{soc}/header[?keys=K,..|pins=..]  the final generated header: name, sha256, text, and one row per line (line, text,
                                                    unit, step); every resolved unit of the chip when neither is given
GET /api/hal/isotopes                              hal-2: every catom isotope, what it REQUIRES of the HAL, and on how many pins of each chip it fits
GET /api/hal/isotopes/{key}/fit?soc=S              one isotope (key = catom:isotope) on one chip: per pin fits | missing, the missing operations, why
GET /api/hal/units/{key}[?view=V]                   one unit (key = soc:operation:pin). view = steps | levels | bindings | checks answers
                                                    that list as rows; no view = the unit with all four
An empty key (nothing picked yet on a page) answers no rows with a note; an unknown soc is 422, a malformed key 422.
"""
import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from hal.custom import crosscheck as CX
from hal.custom import generate as G
from hal.custom import isotopes as ISO
from hal.custom import mechanisms as MX
from hal.custom import operations as OPS
from hal.custom import render as RD
from hal.custom import soc_rules as SR

VIEWS = ('steps', 'levels', 'bindings', 'checks')


def _csv(v):
    return [x.strip() for x in (v or '').split(',') if x.strip()]


def unit_rows(soc, pins=None, board=''):
    if board:
        results = [G.unit(soc, op['name'], p, board) for p in pins for op in OPS.OPERATIONS]
    else:
        results = [G.unit(soc, op['name'], p) for p in (pins or G.default_pins(soc)) for op in OPS.OPERATIONS]
    rows = []
    for res in results:
        u = res['unit']
        rows.append({'key': u['key'], 'operation': u.get('operation', ''), 'pin': u.get('pin', ''), 'board_pin': u.get('board_pin', ''),
                     'status': u.get('status', ''), 'macro': u.get('macro', ''), 'c_text': u.get('c_text', ''), 'c_text_init': u.get('c_text_init', ''),
                     'mechanisms': ', '.join(b['mechanism'] for b in res['bindings'] if b.get('mechanism')),
                     'guarded': u.get('guarded', False), 'why': u.get('why', ''), 'steps_sha256': u.get('steps_sha256', '')})
    return rows


def unit_detail(k):
    p = G.parse_key(k)
    if not p:
        return None
    res = G.unit(*p)
    res['checks'] = CX.checks(res)
    res['levels'] = RD.levels(res)
    return res


class HalAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/hal/socs', self, suffix='socs')
            add('/api/hal/operations', self, suffix='operations')
            add('/api/hal/mechanisms', self, suffix='mechanisms')
            add('/api/hal/socs/{soc}/units', self, suffix='units')
            add('/api/hal/socs/{soc}/header', self, suffix='header')
            add('/api/hal/units/{key}', self, suffix='unit')
            add('/api/hal/isotopes', self, suffix='isotopes')
            add('/api/hal/isotopes/{key}/fit', self, suffix='isotope_fit')

    def _rows(self, class_name):
        return list(((getattr(self.manager, 'objectTables', None) or {}).get(class_name, {}) or {}).values())

    def _fail(self, response, status, text):
        response.status = status
        response.media = {'ok': False, 'error': text}

    def _soc_ok(self, response, soc):
        if soc not in SR.SOCS:
            self._fail(response, falcon.HTTP_422, 'soc must be one of %s' % ', '.join(SR.SOCS))
            return False
        return True

    def on_get_socs(self, request, response):
        rows = []
        for soc in SR.SOCS:
            us = unit_rows(soc)
            rows.append({'soc': soc, 'title': SR.RULES[soc]['title'], 'arch': SR.RULES[soc]['arch'], 'units': len(us),
                         'resolved': sum(u['status'] == 'resolved' for u in us), 'facts_from': SR.DOCS[soc]})
        response.media = {'ok': True, 'count': len(rows), 'rows': rows}

    def on_get_operations(self, request, response):
        loaded = self._rows('HalOperation')
        fields = ('name', 'family', 'title', 'role', 'action', 'setup', 'returns', 'c_name', 'intent', 'basis')
        rows = [{f: getattr(r, f, '') for f in fields} for r in loaded] if loaded else [{f: o.get(f, '') for f in fields} for o in OPS.OPERATIONS]
        response.media = {'ok': True, 'count': len(rows), 'rows': rows, 'from': 'rows' if loaded else 'seed'}

    def on_get_mechanisms(self, request, response):
        loaded = self._rows('HalAccessMechanism')
        fields = ('name', 'title', 'kind', 'meaning', 'selects_when', 'templates_json', 'isr_safe', 'chips', 'cite', 'implemented')
        rows = [{f: getattr(r, f, '') for f in fields} for r in loaded] if loaded else [{f: m.get(f, '') for f in fields} for m in MX.seed_rows()]
        response.media = {'ok': True, 'count': len(rows), 'rows': rows, 'order': MX.ORDER, 'from': 'rows' if loaded else 'seed'}

    def on_get_units(self, request, response, soc):
        if not self._soc_ok(response, soc):
            return
        pins = _csv(request.get_param('pins')) or None
        board = request.get_param('board') or ''
        if board and not pins:
            self._fail(response, falcon.HTTP_422, 'board needs pins (board pin names, e.g. pins=D13,D2)')
            return
        rows = unit_rows(soc, pins, board)
        response.media = {'ok': True, 'soc': soc, 'count': len(rows), 'rows': rows,
                          'resolved': sum(r['status'] == 'resolved' for r in rows)}

    def on_get_header(self, request, response, soc):
        if not self._soc_ok(response, soc):
            return
        keys = _csv(request.get_param('keys'))
        if not keys:
            pins = _csv(request.get_param('pins')) or None
            keys = [r['key'] for r in unit_rows(soc, pins) if r['status'] == 'resolved']
        h = RD.header(soc, keys)
        response.media = {'ok': True, 'soc': soc, 'name': h['name'], 'sha256': h['sha256'], 'text': h['text'], 'count': len(h['lines']),
                          'rows': h['lines'], 'units': len(h['units']), 'refused': h['refused']}

    def on_get_unit(self, request, response, key):
        view = request.get_param('view') or ''
        if view and view not in VIEWS:
            self._fail(response, falcon.HTTP_422, 'view must be one of %s' % ', '.join(VIEWS))
            return
        if not key or key == '-':
            response.media = {'ok': True, 'count': 0, 'rows': [], 'note': 'pick a unit (a row of the units table) to see it here'}
            return
        res = unit_detail(key)
        if res is None:
            self._fail(response, falcon.HTTP_422, 'a unit key is soc:operation:pin (e.g. atmega328p:gpio.set_high:PB5)')
            return
        if view:
            rows = res[view]
            response.media = {'ok': True, 'key': key, 'view': view, 'count': len(rows), 'rows': rows}
            return
        response.media = {'ok': True, 'key': key, 'unit': res['unit'], 'bindings': res['bindings'], 'steps': res['steps'],
                          'levels': res['levels'], 'checks': res['checks']}

    def on_get_isotopes(self, request, response):
        rows = ISO.summary()
        response.media = {'ok': True, 'count': len(rows), 'rows': rows}

    def on_get_isotope_fit(self, request, response, key):
        soc = request.get_param('soc') or ''
        if not key or key == '-':
            response.media = {'ok': True, 'count': 0, 'rows': [], 'note': 'pick an isotope to see where it fits'}
            return
        if not self._soc_ok(response, soc):
            return
        catom, _, iso = key.partition(':')
        rows = ISO.fit(catom, iso, soc)
        response.media = {'ok': True, 'key': key, 'soc': soc, 'count': len(rows), 'rows': rows,
                          'fits': sum(r['verdict'] == 'fits' for r in rows)}
