"""
@module electrodevice.layout_api

lay-0/lay-1 doors (thin falcon handlers over electrodevice.custom.layout_core; the bodies live there):

GET  /api/layout/boards                         the board family: models (breadboard half 400 ties / full 830 ties, the UNO, protoboard + pcb reserved) and the boards on the bench
GET  /api/layout/{config}?board=&header=&scheme=  the layout of a built config on a bench board: placements, wires, nets, THE GATE'S VERDICT (words first)
GET  /api/layout/{config}/steps?board=          the build steps (derived, never typed): step k's `draw` is steps 0..k; `rows` = the same steps as table rows
GET  /api/layout/steps?config=&board=          the same steps by query (a configured table whose config is a page scope); /api/layout/verdict?config= likewise
GET  /api/layout/models                         lay-2: the board models as table rows
GET  /api/layout/{config}/verdict?board=        lay-2: the gate's verdict as table rows (the whole verdict, one row per design net, one per electrical rule)
POST /api/layout/{config}/edit                  {board?, subject: part:<ref>|wire:<name>, field: holes|colour, value, who?, note?, clear?, dry_run?} keep a person's edit BESIDE the derived value; re-gated
GET  /api/layout/wire-colors                    the wire colour schemes (seeded = copy before editing) and the colour names
POST /api/layout/wire-colors                    {copy_of, name, colors?} copy a scheme (optionally with colours set) | {name, set: {key: colour}} set colours on YOUR scheme
Every refusal is {ok: false, error: <plain words>} with the status the words call for (404 unknown, 409 conflicting, 422 cannot be built).
"""
import json

import falcon

from objectTreeDecorators import treeObject, treeObjectInit

from electrodevice.custom.layout_words import LayoutRefused


class LayoutAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/layout/boards', self, suffix='boards')
            add('/api/layout/wire-colors', self, suffix='colors')
            add('/api/layout/{config}', self, suffix='layout')
            add('/api/layout/{config}/steps', self, suffix='steps')
            add('/api/layout/{config}/verdict', self, suffix='verdict')
            add('/api/layout/steps', self, suffix='steps_q')
            add('/api/layout/verdict', self, suffix='verdict_q')
            add('/api/layout/models', self, suffix='models')
            add('/api/layout/{config}/edit', self, suffix='edit')

    # ------------------------------------------------------------ helpers
    def _fail(self, response, exc):
        response.status = falcon.code_to_http_status(getattr(exc, 'status', 422))
        response.media = {'ok': False, 'error': str(exc)}

    def _body(self, request, response):
        raw = request.bounded_stream.read() or b''
        try:
            body = json.loads(raw) if raw.strip() else {}
        except ValueError as e:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
            return None
        if not isinstance(body, dict):
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'the body must be a JSON object'}
            return None
        return body

    # ------------------------------------------------------------ doors
    def on_get_boards(self, request, response):
        from electrodevice.custom import layout_core as C
        out = C.boards_listing(self.manager)
        response.media = dict(out, ok=True, rows=out['boards'])   # `rows` = the boards on the bench, for a configured table

    def on_get_layout(self, request, response, config):
        from electrodevice.custom import layout_core as C
        try:
            r = C.layout_place(config, request.get_param('board'), self.manager, request.get_param('scheme'), request.get_param('header'))
        except LayoutRefused as e:
            return self._fail(response, e)
        response.media = C.public(r)

    def on_get_steps(self, request, response, config):
        from electrodevice.custom import layout_core as C
        try:
            response.media = C.steps_of(config, request.get_param('board'), self.manager, request.get_param('scheme'))
        except LayoutRefused as e:
            self._fail(response, e)

    def _config_q(self, request, response):
        config = request.get_param('config') or ''
        if not config:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'name the config: ?config=uno-light'}
        return config

    def on_get_steps_q(self, request, response):
        config = self._config_q(request, response)
        if config:
            self.on_get_steps(request, response, config)

    def on_get_verdict_q(self, request, response):
        config = self._config_q(request, response)
        if config:
            self.on_get_verdict(request, response, config)

    def on_get_models(self, request, response):
        from electrodevice.custom import layout_core as C
        rows = C.boards_listing(self.manager)['models']
        response.media = {'ok': True, 'rows': rows, 'count': len(rows)}

    def on_get_verdict(self, request, response, config):
        from electrodevice.custom import layout_core as C
        try:
            r = C.layout_place(config, request.get_param('board'), self.manager, request.get_param('scheme'), request.get_param('header'))
        except LayoutRefused as e:
            return self._fail(response, e)
        rows = C.verdict_rows(r)
        response.media = {'ok': True, 'config': config, 'board': r['board']['name'], 'rows': rows, 'count': len(rows)}

    def on_post_edit(self, request, response, config):
        from electrodevice.custom import layout_core as C
        from electrodevice.custom import layout_edits as LE
        body = self._body(request, response)
        if body is None:
            return
        bad = sorted(k for k in body if k not in ('board', 'subject', 'field', 'value', 'who', 'note', 'clear', 'dry_run'))
        if bad:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'unknown key(s) %s (known: board, subject, field, value, who, note, clear, dry_run)' % ', '.join(bad)}
            return
        try:
            board = body.get('board') or None
            base = C.layout_place(config, board, self.manager, with_edits=False)     # the DERIVED layout: edits are validated against it
            subject, field = body.get('subject', ''), body.get('field', 'holes')
            if not subject:
                raise LayoutRefused('an edit needs a subject: part:<ref> or wire:<name>')
            bname = base['board']['name']
            if body.get('dry_run'):
                LE.check_edit(base['_derived'], subject, field, body.get('value'))
                extra = [{'name': 'dry-run', 'subject': subject, 'field': field, 'value': body.get('value'), 'who': body.get('who', ''), 'note': body.get('note', ''), 'created_at': ''}]
                kept = None
            else:
                kept = LE.record(self.manager, config, bname, base['_derived'], subject, field, body.get('value'), body.get('who', ''), body.get('note', ''), bool(body.get('clear')))
                extra = None
            r = C.layout_place(config, board, self.manager, extra_edits=extra)
        except LayoutRefused as e:
            return self._fail(response, e)
        out = C.public(r)
        out['edit'] = kept
        out['dry_run'] = bool(body.get('dry_run'))
        response.media = out

    def on_get_colors(self, request, response):
        from electrodevice.custom import layout_colors as LC
        from electrodevice.objects.layout._shared import SCHEME_DEFAULT, WIRE_COLOURS
        rows = []
        for s in LC.all_schemes(self.manager).values():
            rows.append(dict(s, colors_text='; '.join('%s %s' % (k, v) for k, v in sorted(s['colors'].items()))))
        response.media = {'ok': True, 'count': len(rows), 'rows': rows, 'default': SCHEME_DEFAULT, 'colours': [{'name': n, 'hex': h} for n, h in sorted(WIRE_COLOURS.items())],
                          'note': 'Seeded schemes are copied before they are edited: POST {name: <new>, copy_of: <seeded>, colors: {key: colour}}.'}

    def on_post_colors(self, request, response):
        from electrodevice.custom import layout_colors as LC
        body = self._body(request, response)
        if body is None:
            return
        bad = sorted(k for k in body if k not in ('name', 'copy_of', 'colors', 'display_name', 'set'))
        if bad:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'unknown key(s) %s (known: name, copy_of, colors, display_name, set)' % ', '.join(bad)}
            return
        name = body.get('name', '')
        try:
            if body.get('set'):
                s = None
                for k, v in body['set'].items():
                    s = LC.set_colour(self.manager, name, k, v)
                response.media = dict(s or LC.get_scheme(self.manager, name), ok=True, created=False)
            else:
                if not body.get('copy_of'):
                    raise LayoutRefused('give copy_of (a scheme to copy) and name (the new scheme), or name + set {key: colour} for your own scheme')
                s = LC.copy_scheme(self.manager, name, body['copy_of'], body.get('colors'), body.get('display_name', ''))
                response.status = falcon.HTTP_201
                response.media = dict(s, ok=True, created=True)
        except LayoutRefused as e:
            self._fail(response, e)
