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

ins-0/1 — the Sim | Real modes and THE CONFIRMED-SIM GATE (board.custom.sim_gate):
GET  /api/board/installer/gate?config=&hex=|build= the Real side's verdict for one config at one program: offered | not offered + what is missing, in words
GET  /api/board/installer/sim-confirmations[?config=] the SimInstallConfirmation rows (`rows` for a configured table) + the verdict per config
POST /api/board/installer/sim-confirmations {config, hex_sha256?|build?, session?, source?, words?} the person's tick (who = the signed-in user)
POST /api/board/installer/sim-install      {config} run the config's four Purposes on the twin HERE (stored as ScenarioRuns); refused with the exact
                                          `pol firmware prove` command when this host has no local twin
POST /api/board/installer/plan            also takes {install_anyway: true, reason} for a real install the gate does not offer (recorded)

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
            add('/api/board/installer/gate', self, suffix='gate')   # ins-1
            add('/api/board/installer/sim-confirmations', self, suffix='confirmations')   # ins-1
            add('/api/board/installer/sim-install', self, suffix='sim_install')   # ins-0

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

    @staticmethod
    def _who(request):
        """The signed-in person as the row names them: Keycloak preferred_username, else the opaque subject id; '' with no sign-in."""
        ui = getattr(getattr(request, 'context', None), 'user_info', None)
        if not isinstance(ui, dict):
            return ''
        return str(ui.get('preferred_username') or ui.get('name') or ui.get('sub') or '')

    def _hex_of(self, body):
        """The program a confirmation / verdict is about: body.hex_sha256, else body.build's sha, else the config's newest installable build's sha."""
        from board.custom.installer import all_builds
        if body.get('hex_sha256'):
            return str(body['hex_sha256']), str(body.get('build') or '')
        builds = all_builds(self.manager)
        if body.get('build'):
            b = builds.get(str(body['build']))
            return (b or {}).get('artifact_sha256', ''), str(body['build'])
        fit = sorted((b for b in builds.values() if b.get('variant') == body.get('config') and b.get('state') in ('built', 'flashed')),
                     key=lambda b: b.get('built_at', ''), reverse=True)
        return (fit[0].get('artifact_sha256', ''), fit[0].get('name', '')) if fit else ('', '')

    def on_get_gate(self, request, response):
        from board.custom import sim_gate as G
        cfg = request.get_param('config') or ''
        if not cfg:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': 'name the config: ?config=<variant>[&hex=<sha256>|&build=<name>]'}
            return
        hex_sha, build = self._hex_of({'config': cfg, 'hex_sha256': request.get_param('hex') or '', 'build': request.get_param('build') or ''})
        self._guard(request, response, lambda b: dict(G.verdict(self.manager, cfg, hex_sha), build=build))

    def on_get_confirmations(self, request, response):
        from board.custom import sim_gate as G
        cfg = request.get_param('config') or ''
        rows = G.confirmations(self.manager, cfg)
        response.media = {'ok': True, 'rows': rows, 'count': len(rows), 'attest': G.ATTEST}

    def on_post_confirmations(self, request, response):
        from board.custom import sim_gate as G
        from board.custom.installer import InstallRefused

        def go(b):
            cfg = str(b.get('config') or '')
            if not cfg:
                raise InstallRefused('a confirmation needs {config} (and the program: hex_sha256 or build; else the config\'s newest build is taken)', '400 Bad Request')
            hex_sha, build = self._hex_of(b)
            out = G.confirm(self.manager, cfg, hex_sha, self._who(request), str(b.get('source') or 'installer'), str(b.get('session') or ''),
                            str(b.get('words') or ''), build)
            return dict(confirmation=out, verdict=G.verdict(self.manager, cfg, hex_sha), name=out['name'])
        self._guard(request, response, go)

    def on_post_sim_install(self, request, response):
        from board.custom import sim_gate as G
        from board.custom.installer import InstallRefused

        def go(b):
            if not b.get('config'):
                raise InstallRefused('name the config to run on the twin: {config}', '400 Bad Request')
            api = (request.prefix or '').rstrip('/') if hasattr(request, 'prefix') else ''
            return G.sim_install(self.manager, str(b['config']), api=api)
        self._guard(request, response, go)

    def on_get_doc(self, request, response):
        from board.custom.installer import document
        self._guard(request, response, lambda b: document(self.manager))

    def on_get_variants(self, request, response):
        from board.custom import variants as V
        from board.custom.installer import _rows
        rows = _rows(self.manager, 'FirmwareVariant') or V.SEED_FIRMWARE_VARIANTS
        keys = ('name', 'title', 'purpose', 'app', 'classes_json', 'features_json', 'knobs_json', 'what_to_watch', 'origin')
        vs = [{k: (r.get(k) if isinstance(r, dict) else getattr(r, k, '')) for k in keys} for r in rows]
        response.media = {'ok': True, 'variants': vs, 'rows': vs}   # lay-2/sim-3: `rows` too, for a configured table

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
            p = plan(self.manager, b['instance'], b['build'], install_anyway=b.get('install_anyway') is True, reason=str(b.get('reason') or ''))
            p.pop('row', None)
            if p['refused']:
                raise InstallRefused(p['why'], plan=p['name'], compat=p['compat'], argv_text=p['argv_text'], gate=p.get('gate_detail'))
            return {'plan': p['name'], 'argv': json.loads(p['argv_json']), 'argv_text': p['argv_text'], 'wrapper_text': p['wrapper_text'],
                    'engine': p['engine'], 'engine_how': p['engine_how'], 'engine_where': p['engine_where'], 'adapter': p['adapter'],
                    'compat': p['compat'], 'compat_why': p['compat_why'], 'will_stamp': p['will_stamp'], 'target_kind': p['target_kind'],
                    'host': p['host'], 'port': p['port'], 'state': p['state'], 'install_mode': p['install_mode'], 'gate': p['gate'],
                    'gate_words': p['gate_words'], 'override_reason': p['override_reason'], 'notes': p['notes']}
        self._guard(request, response, go)

    def on_post_run(self, request, response):
        from board.custom.installer import run

        def go(b):
            r = run(self.manager, b.get('plan', ''), b.get('confirm') is True)
            return {k: r.get(k) for k in ('name', 'plan', 'build', 'variant', 'instance', 'target_kind', 'verdict', 'verify', 'verified_bytes',
                                          'firmware_sha', 'elapsed_s', 'row_class', 'row_name', 'notes', 'install_mode', 'override_reason')}
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
