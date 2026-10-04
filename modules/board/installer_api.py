"""
@module board.installer_api

THE FIRMWARE INSTALLER's doors (brd-fi, plan §7a) — a thin falcon shell over board.custom.installer / compat / attach:

GET  /api/board/installer                 one document for the page: this host's devices + adapters, the variants, every
                                          build with sizes vs the cited limits, sha, compat and engines, the twin, the
                                          last plans and records
GET  /api/board/variants                  the FirmwareVariant rows (what each tests, what to watch)
POST /api/board/installer/build           {variant} → gen against THIS server's contracts + build → FirmwareBuild
GET  /api/board/builds/{build}/compat     compatible | stale-header | unknown-class, per class with both orders + shas
POST /api/board/installer/plan            {instance, build} → the DRY-RUN as an InstallPlan row (exact argv, engine,
                                          adapter, compat, what will be stamped); nothing is opened
POST /api/board/installer/run             {plan, confirm: true} → the install, on THIS host only → InstallRecord
POST /api/board/installer/attach          {record} → the generated bridge at the port / the twin's pty (background)
POST /api/board/installer/detach          stop the installer's bridge
GET  /api/board/installer/result/{record} the first frames, frames/s, the row's fields now

A refusal answers {ok: false, error: <plain words>} with 400/403/404/409 — the page shows the words as they are. The
argv that runs is ALWAYS the plan row's, fixed at planning; no request field reaches a command line.
"""
import json

from objectTreeDecorators import treeObject, treeObjectInit


class BoardInstallerAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/installer', self, suffix='doc')
            add('/api/board/variants', self, suffix='variants')
            add('/api/board/installer/build', self, suffix='build')
            add('/api/board/builds/{build}/compat', self, suffix='compat')
            add('/api/board/installer/plan', self, suffix='plan')
            add('/api/board/installer/run', self, suffix='run')
            add('/api/board/installer/attach', self, suffix='attach')
            add('/api/board/installer/detach', self, suffix='detach')
            add('/api/board/installer/result/{record}', self, suffix='result')

    @staticmethod
    def _body(request):
        raw = request.bounded_stream.read() or b''
        return json.loads(raw) if raw.strip() else {}

    @staticmethod
    def _refuse(response, e):
        response.status = getattr(e, 'status', '409 Conflict')
        response.media = dict({'ok': False, 'error': str(e), 'exit': getattr(e, 'code', 1)}, **getattr(e, 'extra', {}))

    def _guard(self, request, response, fn):
        from board.custom.installer import InstallRefused
        try:
            body = self._body(request) if request.method == 'POST' else {}
        except ValueError as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
            return
        try:
            out = fn(body)
            response.media = dict(out, ok=True) if isinstance(out, dict) else out
        except InstallRefused as e:
            self._refuse(response, e)

    def on_get_doc(self, request, response):
        from board.custom.installer import document
        self._guard(request, response, lambda b: document(self.manager))

    def on_get_variants(self, request, response):
        from board.custom import variants as V
        from board.custom.installer import _rows
        rows = _rows(self.manager, 'FirmwareVariant') or V.SEED_FIRMWARE_VARIANTS
        keys = ('name', 'title', 'purpose', 'app', 'classes_json', 'features_json', 'knobs_json', 'what_to_watch', 'origin')
        response.media = {'ok': True, 'variants': [{k: (r.get(k) if isinstance(r, dict) else getattr(r, k, '')) for k in keys} for r in rows]}

    def on_post_build(self, request, response):
        from board.custom.installer import build_variant, InstallRefused

        def go(b):
            if not b.get('variant'):
                raise InstallRefused('name a variant to build', '400 Bad Request')
            rec = build_variant(self.manager, b['variant'])
            return {'build': rec['name'], 'state': rec['state'], 'variant': rec.get('variant'), 'notes': rec.get('notes'),
                    'flash_bytes': rec.get('flash_bytes'), 'ram_bytes': rec.get('ram_bytes'), 'artifact_sha256': rec.get('artifact_sha256')}
        self._guard(request, response, go)

    def on_get_compat(self, request, response, build):
        from board.custom import compat
        from board.custom.installer import find_build
        self._guard(request, response, lambda b: dict(compat.check(find_build(self.manager, build), self.manager), build=build))

    def on_post_plan(self, request, response):
        from board.custom.installer import plan, InstallRefused

        def go(b):
            if not b.get('instance') or not b.get('build'):
                raise InstallRefused('a plan needs {instance, build}', '400 Bad Request')
            p = plan(self.manager, b['instance'], b['build'])
            p.pop('row', None)
            if p['refused']:
                raise InstallRefused(p['why'], plan=p['name'], compat=p['compat'], argv_text=p['argv_text'])
            return {'plan': p['name'], 'argv': json.loads(p['argv_json']), 'argv_text': p['argv_text'], 'wrapper_text': p['wrapper_text'],
                    'engine': p['engine'], 'engine_how': p['engine_how'], 'engine_where': p['engine_where'], 'adapter': p['adapter'],
                    'compat': p['compat'], 'compat_why': p['compat_why'], 'will_stamp': p['will_stamp'], 'target_kind': p['target_kind'],
                    'host': p['host'], 'port': p['port'], 'state': p['state']}
        self._guard(request, response, go)

    def on_post_run(self, request, response):
        from board.custom.installer import run

        def go(b):
            r = run(self.manager, b.get('plan', ''), b.get('confirm') is True)
            return {k: r.get(k) for k in ('name', 'plan', 'build', 'variant', 'instance', 'target_kind', 'verdict', 'verify', 'verified_bytes',
                                          'firmware_sha', 'elapsed_s', 'row_class', 'row_name', 'notes')}
        self._guard(request, response, go)

    def on_post_attach(self, request, response):
        from board.custom.attach import attach
        self._guard(request, response, lambda b: attach(self.manager, b.get('record', '')))

    def on_post_detach(self, request, response):
        from board.custom.attach import detach
        self._guard(request, response, lambda b: detach())

    def on_get_result(self, request, response, record):
        from board.custom.attach import result
        self._guard(request, response, lambda b: result(self.manager, record))
