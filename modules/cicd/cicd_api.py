"""
@module cicd.cicd_api

/api/cicd                    EVERYTHING for one pipeline device in ONE read: settings + stages + routes +
                             readiness + the rendered `device.env`. This is what `cicd-sync.sh pull` calls at
                             the top of every Jenkinsfile, so a run configures itself from Polari in a single
                             request (and keeps the file it has when the core does not answer).
/api/cicd/device             GET the device's settings and their validation; POST (ADMIN) change them —
                             validated by the SAME rule set device.sh uses, ported once to python.
/api/cicd/device/token       POST (ADMIN) mint the device's POSTING-ONLY ingest token. Shown ONCE, here;
                             only sha256(token) is stored. It may reach /api/cicd/ingest and nothing else.
/api/cicd/stages             POST (ADMIN) replace the ordered testing stages (his ask: stage 1 core, stage 2
                             household, …) — the list that decides what can ever be released.
/api/cicd/routes/{name}      POST (ADMIN) {"enabled": true|false} — the CI_ROUTES half Polari owns. `armed`
                             (the secret is present) is the DEVICE's reading and is never written here.
/api/cicd/setup              GET the LAST setup walkthrough the device pushed (ci-11a) — the protocol
                             document `polari-pipeline-setup/1`, reassembled from PipelineSetupStep rows, so
                             a browser with NO desktop shell still sees where that device got to. `live` is
                             always false: it is a mirror of the last push, never a live reading.
/api/cicd/ingest             THE MIRROR. POST {kind: device|secrets|run|isle-test|release|setup|test-verdict|deploy, …} with the
                             posting-only token. Six kinds, nothing else; a value-shaped field is a 400 and
                             nothing is stored.
/api/cicd/runs               GET the mirrored Jenkins builds
/api/cicd/results            GET the isle-test results, per run × stage
/api/cicd/releases           GET what each version shipped — and what it did not, with the reason

ci-8, his ask 2026-09-19: *"We may want a CICD app as well that is always enabled with the pipeline that can
allow us to read and modify the settings of the pipeline."*

THE SHAPE OF THE TRUST. A person changes settings; the pipeline reports facts. Those are different
credentials on purpose: the admin doors want `ADMIN_ROLES` and write the settings columns; the ingest door
wants the per-device token and can only ever write the reported ones. Neither can do the other's job, and
NEITHER is a Jenkins credential — nothing in this module can start, stop or read a build. The mirror flows
one way, inward.

EDITING IS ON THE ROWS' OWN PAGES (his per-object display rule). These doors exist because a pipeline needs
a machine-readable read and a machine-writable mirror; a person turns a knob through CRUDE on
/display/cicd-overview and /display/cicd-stages, gated by the `cicd-settings` permission profile. ci-8 wrote
no frontend component at all; ci-11a wrote exactly one, `pipeline-setup-panel`, and only because the ask it
serves needs a button that runs a command on the machine the browser is sitting on.

ci-11a, his ask 2026-09-19: run the pipeline as a desktop application, "guiding people through use like a
normal app", eliminating the terminal. The walkthrough itself is produced BY THE DEVICE
(`pol jenkins setup --json`) — this core cannot run `pol`, and should not be able to. `POST /api/cicd/ingest
{kind: setup}` mirrors it in and `GET /api/cicd/setup` reads it back, so a browser with no desktop shell
still sees where a device got to. Neither door can drive a device; the mirror still flows one way, inward.
"""
import datetime

from objectTreeDecorators import treeObject, treeObjectInit

from cicd.custom import cicd_rows as R
from cicd.custom.cicd_auth import (TOKEN_HEADER, TOKEN_SECRET, caller_sub, device_for_token, hash_token,
                                   is_admin, mint_token, token_from_request)
from cicd.custom.cicd_ingest import KINDS
from cicd.custom.cicd_validate import refusals, validate_settings


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


class CicdAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/cicd', self)
            add('/api/cicd/setup', self, suffix='setup')                   # GET the LAST walkthrough the device pushed
            add('/api/cicd/device', self, suffix='device')                # GET settings + validation; POST (admin) change them
            add('/api/cicd/device/token', self, suffix='device_token')    # POST (admin) mint the posting-only token, shown once
            add('/api/cicd/stages', self, suffix='stages')                # POST (admin) replace the ordered stages
            add('/api/cicd/routes/{route}', self, suffix='route')         # POST (admin) {"enabled": true|false}
            add('/api/cicd/ingest', self, suffix='ingest')                # the MIRROR — the posting-only token
            add('/api/cicd/runs', self, suffix='runs')
            add('/api/cicd/results', self, suffix='results')
            add('/api/cicd/releases', self, suffix='releases')
            add('/api/cicd/verdicts', self, suffix='verdicts')   # ci-12: one answer per tested sha
            add('/api/cicd/deploys', self, suffix='deploys')     # dep-1: what runs where, since when

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _body(request):
        try:
            return request.media or {}
        except Exception:
            return {}

    @staticmethod
    def _bad(response, msg, **extra):
        import falcon
        response.status = falcon.HTTP_400
        response.media = {'ok': False, 'error': msg, **extra}

    @staticmethod
    def _refuse(response, status, why, **extra):
        response.status = status
        response.media = {'ok': False, 'refusal': why, **extra}

    def _user_info(self, request):
        return getattr(getattr(request, 'context', None), 'user_info', None)

    def _admin_or_refuse(self, request, response, what):
        """ADMIN_ROLES, or a refusal that names the rule. Returns the caller's `sub`, or None."""
        ui = self._user_info(request)
        sub = caller_sub(ui)
        if not sub:
            self._refuse(response, '401 Unauthorized',
                         'sign in: %s is a settings change and Polari is the source of truth for the '
                         'pipeline\'s configuration' % what)
            return None
        if not is_admin(ui):
            self._refuse(response, '403 Forbidden',
                         'only an administrator may %s (ADMIN_ROLES: admin, polari-admin)' % what)
            return None
        return sub

    def _upsert(self, class_name, cls, rows):
        try:
            from moduleService.seed_upsert import upsert_seed_rows
            return upsert_seed_rows(self.manager, class_name, cls, rows, tag='CicdIngest')
        except Exception as exc:
            return {'class': class_name, 'errors': [{'error': str(exc)}]}

    def _device(self, request):
        return R.default_device(self.manager, (request.params.get('device') or '').strip())

    # --------------------------------------------------------------- GET /api/cicd
    def on_get(self, request, response):
        """The ONE read a pipeline run makes. Unauthenticated reads are allowed deliberately: these are
        knobs and verdicts, no secret value exists anywhere in the answer, and a pipeline that had to hold a
        READ credential as well would be one more secret on the device for no gain."""
        dev = self._device(request)
        response.media = R.everything(self.manager, dev)

    # ------------------------------------------------------------- /api/cicd/setup
    def on_get_setup(self, request, response):
        """ci-11a — THE LAST WALKTHROUGH THIS DEVICE PUSHED, reassembled into the protocol document.

        Read openly, like `GET /api/cicd`: it is knobs, verdicts and to-do text, and no secret value can
        exist in it (the ingest door refuses a secret question that carries anything but `present`).

        WHY THE DOOR EXISTS. The wizard runs `pol jenkins setup --json` on the DEVICE, through the shell's
        verb allowlist. A person who opens this page in a plain browser has no such shell — so the page
        reads this instead and shows the state read-only, with the exact commands beside each step. The
        answer therefore carries `live: false`: it is a MIRROR of the last push, never a live reading, and
        the page says so rather than implying it just ran.
        """
        from cicd.custom.cicd_ingest import SETUP_PROTOCOL
        dev = self._device(request)
        if dev is None:
            return self._bad(response,
                             'no PipelineDevice row (or several: name one with ?device=<name>). A device '
                             'appears here after its first `pol jenkins sync push`.',
                             protocol=SETUP_PROTOCOL,
                             devices=[str(getattr(r, 'name', '')) for r in R.devices(self.manager)])
        device = str(getattr(dev, 'name', ''))
        doc = R.setup_document(self.manager, dev)
        if not doc['steps']:
            response.media = {
                'ok': True, 'protocol': SETUP_PROTOCOL, 'live': False, 'device_name': device,
                'steps': [], 'todo': [], 'summary': {'complete': 0, 'total': 8, 'ready': False, 'blocking': ''},
                'how': ('this device has not pushed its walkthrough yet. On the device: `pol jenkins sync '
                        'push` (or `pol jenkins sync push-setup`). A Polari core cannot run `pol` itself — '
                        'only the device can, and that is deliberate.'),
            }
            return
        doc.update({'ok': True, 'protocol': SETUP_PROTOCOL, 'live': False, 'device_name': device})
        doc['how'] = ('a MIRROR of the last push, not a live reading. A desktop shell re-runs each step '
                      'through the verb allowlist (pol jenkins verbs); a plain browser shows this state '
                      'and the exact command beside each step.')
        response.media = doc

    # ------------------------------------------------------------ /api/cicd/device
    def on_get_device(self, request, response):
        dev = self._device(request)
        if dev is None:
            return self._bad(response, 'no PipelineDevice row (or several: name one with ?device=<name>)',
                             devices=[str(getattr(r, 'name', '')) for r in R.devices(self.manager)])
        from cicd.custom.cicd_validate import settings_from_device
        from cicd.custom.cicd_stages import rows_to_stages
        settings = settings_from_device(dev)
        stages = rows_to_stages(R.stages_of(self.manager, str(getattr(dev, 'name', ''))))
        response.media = {'ok': True, 'device': str(getattr(dev, 'name', '')), 'settings': settings,
                          'stages': stages,
                          'validation': validate_settings(dict(settings, stages=stages)),
                          'token_set': bool(getattr(dev, 'ingest_token_hash', '')),
                          'how': 'POST here (admin) to change a setting; the same rules device.sh applies, '
                                 'applied once. A FAIL row refuses the whole POST — nothing partial is written.'}

    def on_post_device(self, request, response):
        sub = self._admin_or_refuse(request, response, 'change the pipeline device settings')
        if sub is None:
            return
        body = self._body(request)
        name = str(body.get('device') or body.get('name') or '').strip()
        dev = R.device_named(self.manager, name) if name else self._device(request)
        if dev is None and not name:
            return self._bad(response, 'name the device: {"device": "<name>", "settings": {…}}',
                             devices=[str(getattr(r, 'name', '')) for r in R.devices(self.manager)])
        from cicd.custom.cicd_validate import settings_from_device
        from cicd.custom.cicd_stages import rows_to_stages, render
        current = settings_from_device(dev) if dev is not None else {}
        settings = dict(current, **(body.get('settings') or {}))
        stages = rows_to_stages(R.stages_of(self.manager, name or str(getattr(dev, 'name', ''))))
        rows = validate_settings(dict(settings, stages=stages))
        # The STAGES are the other door's business (POST /api/cicd/stages). A device with no stage list yet
        # has a real problem — and the validation still says so in the rows — but refusing to let somebody
        # raise the VM's RAM until they have written a stage list is the wrong coupling: it would make a new
        # device unconfigurable in the order people actually configure one.
        bad = [r for r in refusals(rows) if not r['key'].startswith(('CI_ISLE_STAGES', 'isle stages'))]
        if bad:
            return self._bad(response, 'refused: %s' % '; '.join('%s %s' % (r['key'], r['message']) for r in bad),
                             validation=rows)
        from cicd.cicd_basis import PipelineDevice
        payload = {
            'name': name or str(getattr(dev, 'name', '')),
            'role': str(body.get('role') or (getattr(dev, 'role', 'pipeline') if dev is not None else 'pipeline')),
            # his addendum 2026-09-19: the whole suite, or ONE app somebody maintains
            'mode': str(settings.get('mode') or 'suite'), 'app_name': str(settings.get('app_name') or ''),
            'app_repo': str(settings.get('app_repo') or ''),
            'core_source': str(settings.get('core_source') or 'release:latest'),
            'isle_target': settings['isle_target'], 'isle_ssh_alias': settings['isle_ssh_alias'],
            'isle_ssh_user': settings['isle_ssh_user'], 'vm_name': settings['vm_name'],
            'vm_ram_gb': int(settings['vm_ram_gb']), 'vm_vcpus': int(settings['vm_vcpus']),
            'vm_disk_gb': int(settings['vm_disk_gb']), 'nested': settings['nested'],
            'isle_pool': settings['isle_pool'], 'image_url': settings['image_url'],
            'min_free_gb': int(settings['min_free_gb']),
            'min_ram_headroom_gb': int(settings['min_ram_headroom_gb']),
            'executors': int(settings['executors']),
            'routes_json': __import__('json').dumps([str(r) for r in (settings.get('routes') or [])]),
            'stages_summary': render(stages), 'posted_by': sub,
        }
        report = self._upsert('PipelineDevice', PipelineDevice, [payload])
        response.media = {'ok': True, 'device': payload['name'], 'settings': settings, 'validation': rows,
                          'stored': report, 'changed_by': sub,
                          'how': 'the device picks this up at its next `cicd-sync.sh pull` (the top of every '
                                 'Jenkinsfile), which rewrites device.env from these rows'}

    # ----------------------------------------------------- /api/cicd/device/token
    def on_post_device_token(self, request, response):
        """Mint the device's posting-only ingest token. THE TOKEN IS SHOWN ONCE, HERE, AND NEVER AGAIN."""
        sub = self._admin_or_refuse(request, response, 'mint a pipeline ingest token')
        if sub is None:
            return
        body = self._body(request)
        name = str(body.get('device') or '').strip()
        dev = R.device_named(self.manager, name) if name else self._device(request)
        if dev is None:
            return self._bad(response, 'name the device: {"device": "<PipelineDevice.name>"}',
                             devices=[str(getattr(r, 'name', '')) for r in R.devices(self.manager)])
        token = mint_token()
        from cicd.cicd_basis import PipelineDevice
        self._upsert('PipelineDevice', PipelineDevice, [{
            'name': str(getattr(dev, 'name', '')), 'ingest_token_hash': hash_token(token),
            'token_issued_at': _now(), 'token_issued_by': sub, 'posted_by': sub}])
        response.media = {
            'ok': True, 'device': str(getattr(dev, 'name', '')), 'token': token, 'shown': 'once',
            'store_it_as': TOKEN_SECRET,
            'how': ('This is the ONLY time this value is shown: Polari keeps sha256(token) and nothing else. '
                    'On the device: printf %%s \'<token>\' | pol jenkins secrets put %s — it lands in '
                    '/etc/polari-jenkins/secrets (root:polari-ci 0640) under the ci-7 posture. It may POST '
                    '/api/cicd/ingest and nothing else: it cannot read or change a setting, cannot mint '
                    'another, and is not a Jenkins credential. Minting again REVOKES the previous one.'
                    % TOKEN_SECRET),
            'issued_by': sub, 'issued_at': _now()}

    # ------------------------------------------------------------ /api/cicd/stages
    def on_post_stages(self, request, response):
        """Replace the ordered testing stages. The whole list at once, because the ORDER is the setting."""
        sub = self._admin_or_refuse(request, response, 'change the isle testing stages')
        if sub is None:
            return
        body = self._body(request)
        name = str(body.get('device') or '').strip()
        dev = R.device_named(self.manager, name) if name else self._device(request)
        if dev is None:
            return self._bad(response, 'name the device: {"device": "<name>", "stages": [[], ["household"], …]}',
                             devices=[str(getattr(r, 'name', '')) for r in R.devices(self.manager)])
        device = str(getattr(dev, 'name', ''))
        raw = body.get('stages')
        if isinstance(raw, str):
            from cicd.custom.cicd_stages import parse
            stages = parse(raw)
        elif isinstance(raw, list):
            stages = [[str(a) for a in (s or []) if a and str(a) != 'core'] if isinstance(s, list) else []
                      for s in raw]
        else:
            return self._bad(response, 'stages: a list of app lists ([[], ["household"], ["gears","cntfet"]]) '
                                       'or the CI_ISLE_STAGES string ("core; household; gears,cntfet")')
        from cicd.custom.cicd_validate import validate_stages
        rows = validate_stages(stages)
        bad = refusals(rows)
        if bad:
            return self._bad(response, 'refused: %s' % '; '.join(r['message'] for r in bad), validation=rows)
        from cicd.cicd_basis import PipelineDevice, PipelineStage
        from cicd.custom.cicd_stages import render
        import json as _json
        wanted = [{'name': '%s:%d' % (device, i), 'device': device, 'index': i,
                   'apps_json': _json.dumps(apps), 'posted_by': sub}
                  for i, apps in enumerate(stages, start=1)]
        report = self._upsert('PipelineStage', PipelineStage, wanted)
        # a shorter list must LOSE its tail rows, or stage 4 of the old list would keep running
        keep = {w['name'] for w in wanted}
        removed = []
        table = (getattr(self.manager, 'objectTables', None) or {}).get('PipelineStage', {}) or {}
        for key, row in list(table.items()):
            if str(getattr(row, 'device', '')) == device and str(getattr(row, 'name', '')) not in keep:
                removed.append(str(getattr(row, 'name', '')))
                table.pop(key, None)
        self._upsert('PipelineDevice', PipelineDevice,
                     [{'name': device, 'stages_summary': render(stages), 'posted_by': sub}])
        response.media = {'ok': True, 'device': device, 'stages': stages, 'knob': render(stages),
                          'validation': rows, 'stored': report, 'removed': removed, 'changed_by': sub,
                          'release_rule': R.RELEASE_RULE}

    # ------------------------------------------------------ /api/cicd/routes/{route}
    def on_post_route(self, request, response, route):
        """{"enabled": true|false} — the CI_ROUTES half. `armed` is the device's reading, never set here."""
        sub = self._admin_or_refuse(request, response, 'enable or disable a publication route')
        if sub is None:
            return
        body = self._body(request)
        if 'enabled' not in body:
            return self._bad(response, 'body: {"enabled": true|false} — whether this route MAY publish for '
                                       'real (it still needs its secret present, and the release rule above both)')
        name = str(body.get('device') or '').strip()
        dev = R.device_named(self.manager, name) if name else self._device(request)
        if dev is None:
            return self._bad(response, 'name the device: {"device": "<name>", "enabled": true|false}')
        device = str(getattr(dev, 'name', ''))
        from cicd.cicd_basis import PipelineDevice, PipelineRoute
        from cicd.custom.cicd_validate import ACTIVE_ROUTES, PARKED_ROUTES
        if route in PARKED_ROUTES:
            return self._bad(response, 'route %r is PARKED — it needs an outside account and nothing asks for '
                                       'it (his rule). ACTIVE routes: %s' % (route, ', '.join(ACTIVE_ROUTES)))
        if route not in ACTIVE_ROUTES:
            return self._bad(response, 'unknown route %r — ACTIVE routes: %s' % (route, ', '.join(ACTIVE_ROUTES)))
        enabled = bool(body.get('enabled'))
        payload = {'name': '%s:%s' % (device, route), 'device': device, 'enabled': enabled, 'posted_by': sub}
        if 'target' in body:
            # WHOSE route this is (his addendum): an app developer publishes to their OWN namespace
            from cicd.custom.cicd_validate import refusals as _ref, validate_routes
            target = str(body.get('target') or '').strip()
            bad = _ref(validate_routes([{'route': route, 'target': target}],
                                       mode=str(getattr(dev, 'mode', 'suite')),
                                       app_name=str(getattr(dev, 'app_name', ''))))
            if bad:
                return self._bad(response, bad[0]['message'])
            payload['target'] = target
        self._upsert('PipelineRoute', PipelineRoute, [payload])
        import json as _json
        enabled_now = sorted(str(getattr(r, 'name', '')).split(':', 1)[-1]
                             for r in R.routes_of(self.manager, device) if bool(getattr(r, 'enabled', False)))
        self._upsert('PipelineDevice', PipelineDevice,
                     [{'name': device, 'routes_json': _json.dumps(enabled_now), 'posted_by': sub}])
        response.media = {'ok': True, 'device': device, 'route': route, 'enabled': enabled,
                          'ci_routes': enabled_now, 'changed_by': sub,
                          'how': 'enabled is Polari\'s half; the route publishes for real only when its secret '
                                 'is also present on the device (armed) AND the release rule is satisfied',
                          'release_rule': R.RELEASE_RULE}

    # ------------------------------------------------------------ /api/cicd/ingest
    def on_post_ingest(self, request, response):
        """THE MIRROR. Posting-only credential; six kinds; a value-shaped field is refused, not filtered."""
        from cicd.custom.cicd_ingest import check
        token = token_from_request(request)
        dev = device_for_token(R.devices(self.manager), token)
        if dev is None:
            return self._refuse(response, '401 Unauthorized',
                                'the posting-only pipeline credential is required (header %s, or a Bearer '
                                'authorization). An administrator mints it with POST /api/cicd/device/token; '
                                'the device keeps it as the secret %s.' % (TOKEN_HEADER, TOKEN_SECRET),
                                kinds=list(KINDS))
        body = self._body(request)
        ok, why = check(body)
        if not ok:
            return self._bad(response, why, kinds=list(KINDS))
        device = str(getattr(dev, 'name', ''))
        if str(body.get('device')) != device:
            return self._refuse(response, '403 Forbidden',
                                'this credential belongs to device %r and may post only for it (the body '
                                'names %r) — one device\'s token is never another\'s'
                                % (device, str(body.get('device'))))
        posted_by = 'cicd-ingest:%s' % device
        kind = str(body.get('kind'))
        handler = getattr(self, '_ingest_%s' % kind.replace('-', '_'))
        return handler(body, dev, posted_by, response)

    def _ingest_device(self, body, dev, posted_by, response):
        from cicd.cicd_basis import PipelineDevice, PipelineRoute, PipelineStage
        from cicd.custom.cicd_ingest import device_rows, route_rows, stage_rows
        payload, adopted = device_rows(body, existing=dev, posted_by=posted_by)
        payload['last_seen'] = payload.get('last_seen') or _now()
        reports = {'PipelineDevice': self._upsert('PipelineDevice', PipelineDevice, [payload])}
        if adopted:
            reports['PipelineStage'] = self._upsert('PipelineStage', PipelineStage, stage_rows(body, posted_by))
        rrows = route_rows(body, posted_by)
        if rrows:
            reports['PipelineRoute'] = self._upsert('PipelineRoute', PipelineRoute, rrows)
        response.media = {'ok': True, 'kind': 'device', 'device': payload['name'], 'adopted': adopted,
                          'stored': reports,
                          'how': ('a device post REPORTS; it does not override. The settings columns belong to '
                                  'Polari and are left as they are — except on ADOPTION, the first post for a '
                                  'device nobody has a row for yet.') if not adopted else
                                 ('adopted: this device had no row, so its own device.env became the first '
                                  'version of the truth. From now on Polari is the source and pulls overwrite '
                                  'device.env.')}

    def _ingest_setup(self, body, dev, posted_by, response):
        """ci-11a — the walkthrough the DEVICE computed, stored verbatim.

        Polari never re-derives a step: `pol jenkins setup --json` runs on the pipeline device, and this
        core cannot run `pol` (nor should it be able to). The rows are a mirror, not a second opinion.
        """
        from cicd.cicd_basis import PipelineDevice, PipelineSetupStep
        from cicd.custom.cicd_ingest import setup_step_rows
        rows = setup_step_rows(body, posted_by)
        report = self._upsert('PipelineSetupStep', PipelineSetupStep, rows)
        device = str(getattr(dev, 'name', ''))
        self._upsert('PipelineDevice', PipelineDevice, [{
            'name': device,
            'setup_steps_done': int(body.get('complete') or 0),
            'setup_steps_total': int(body.get('steps_total') or len(rows)),
            'setup_ready': bool(body.get('ready')),
            'setup_blocking': str(body.get('blocking') or ''),
            'setup_todo_json': str(body.get('todo_json') or '[]'),
            'setup_at': str(body.get('at') or _now()),
            'last_seen': _now(), 'posted_by': posted_by,
        }])
        response.media = {'ok': True, 'kind': 'setup', 'device': device, 'steps': len(rows),
                          'stored': report, 'protocol': str(body.get('setup_protocol') or ''),
                          'read_it_back': '/api/cicd/setup?device=%s' % device,
                          'how': ('the walkthrough is mirrored so a browser with NO desktop shell still sees '
                                  'where this device got to. A secret question carries `present` or nothing; '
                                  'the door refuses one that carries anything else, and nothing is stored.')}

    def _ingest_secrets(self, body, dev, posted_by, response):
        from cicd.cicd_basis import PipelineSecretPresence
        from cicd.custom.cicd_ingest import secret_rows
        rows = secret_rows(body, posted_by)
        report = self._upsert('PipelineSecretPresence', PipelineSecretPresence, rows)
        response.media = {'ok': True, 'kind': 'secrets', 'stored': report, 'count': len(rows),
                          'how': 'presence booleans and NAMES only — no value exists in this table or in this '
                                 'answer, and the door refuses a body that carries one'}

    def _ingest_run(self, body, dev, posted_by, response):
        from cicd.cicd_basis import PipelineDevice, PipelineRun
        from cicd.custom.cicd_ingest import run_row
        row = run_row(body, posted_by)
        report = self._upsert('PipelineRun', PipelineRun, [row])
        self._upsert('PipelineDevice', PipelineDevice,
                     [{'name': str(getattr(dev, 'name', '')), 'last_seen': _now(), 'posted_by': posted_by}])
        response.media = {'ok': True, 'kind': 'run', 'run': row['name'], 'status': row['status'], 'stored': report}

    def _ingest_isle_test(self, body, dev, posted_by, response):
        from cicd.cicd_basis import IsleTestResult
        from cicd.custom.cicd_ingest import isle_test_row
        row = isle_test_row(body, posted_by)
        report = self._upsert('IsleTestResult', IsleTestResult, [row])
        response.media = {'ok': True, 'kind': 'isle-test', 'result': row['name'], 'stored': report,
                          'release_rule': R.RELEASE_RULE}

    def _ingest_test_verdict(self, body, dev, posted_by, response):
        """ci-12 — the TEST pipeline's one answer for one sha.

        Mirrored, never judged: the verdict was computed by `polari-jenkins/verdict.py` on the device that
        ran the tests, and this door stores what it was told. `pol jenkins promote main` and
        `routes/_lib.sh` read the file on the device itself, so this row is the legible copy a person
        reads — it is not in the enforcement path, and a core that is down can never block a release
        decision.
        """
        from cicd.cicd_basis import TestVerdict
        from cicd.custom.cicd_ingest import test_verdict_row
        row = test_verdict_row(body, posted_by)
        report = self._upsert('TestVerdict', TestVerdict, [row])
        response.media = {'ok': True, 'kind': 'test-verdict', 'verdict': row['name'],
                          'says': row['verdict'], 'stored': report,
                          'release_rule': R.RELEASE_RULE,
                          'how': 'only a sha whose verdict is `passed` may be promoted to main; scans are '
                                 'carried in this row and change nothing'}

    def _ingest_deploy(self, body, dev, posted_by, response):
        """dep-1 — one deploy of one release to one target, as deploy/apply.sh recorded it. Mirrored, never judged."""
        from cicd.cicd_basis import DeployRecord
        from cicd.custom.cicd_ingest import deploy_row
        row = deploy_row(body, posted_by)
        if not row['target'] or not row['release']:
            return self._bad(response, 'a deploy names its target and its release')
        report = self._upsert('DeployRecord', DeployRecord, [row])
        response.media = {'ok': True, 'kind': 'deploy', 'deploy': row['name'], 'result': row['result'],
                          'stored': report,
                          'how': 'the pipeline\'s key on a target is restricted to the deploy agent: it stashes '
                                 'the volumes, replaces images, verifies — and cannot touch the secrets'}

    def _ingest_release(self, body, dev, posted_by, response):
        from cicd.cicd_basis import ReleaseRecord
        from cicd.custom.cicd_ingest import release_row
        row = release_row(body, posted_by)
        report = self._upsert('ReleaseRecord', ReleaseRecord, [row])
        response.media = {'ok': True, 'kind': 'release', 'release': row['name'], 'stored': report,
                          'release_rule': R.RELEASE_RULE}

    # ------------------------------------------------------------------ the reads
    def on_get_runs(self, request, response):
        device = (request.params.get('device') or '').strip()
        rows = R.runs(self.manager, device)
        response.media = {'ok': True, 'count': len(rows), 'runs': [
            {'run': str(getattr(r, 'name', '')), 'job': str(getattr(r, 'job', '')),
             'number': int(getattr(r, 'number', 0) or 0), 'version': str(getattr(r, 'version', '')),
             'status': str(getattr(r, 'status', '')), 'started': str(getattr(r, 'started', '')),
             'finished': str(getattr(r, 'finished', '')), 'summary': str(getattr(r, 'summary', '')),
             'url': str(getattr(r, 'url', ''))} for r in rows],
            'how': 'mirrored in by the pipeline; nothing here drives Jenkins. The url is the controller\'s '
                   'loopback console — reach it with ssh -L 8080:127.0.0.1:8080 <alias>.'}

    def on_get_deploys(self, request, response):
        """dep-1 — the DeployRecord rows, newest first: what runs where, since when, from which release."""
        device = (request.params.get('device') or '').strip()
        target = (request.params.get('target') or '').strip()
        rows = R.deploys(self.manager, device, target)
        response.media = {'ok': True, 'count': len(rows), 'deploys': [
            {'target': str(getattr(r, 'target', '')), 'release': str(getattr(r, 'release', '')),
             'from_release': str(getattr(r, 'from_release', '')), 'result': str(getattr(r, 'result', '')),
             'failed_at': str(getattr(r, 'failed_at', '')), 'rollback': str(getattr(r, 'rollback', '')),
             'stash': str(getattr(r, 'stash', '')), 'apply_seconds': int(getattr(r, 'apply_seconds', 0) or 0),
             'at': str(getattr(r, 'at', '')), 'device': str(getattr(r, 'device', ''))} for r in rows]}

    def on_get_verdicts(self, request, response):
        """ci-12 — the test verdicts, newest first. The column a person reads first is `why`."""
        import json as _json
        device = (request.params.get('device') or '').strip()
        sha = (request.params.get('sha') or '').strip()
        rows = R.verdicts(self.manager, device, sha)
        out = []
        for r in rows:
            out.append({'verdict': str(getattr(r, 'verdict', '')), 'sha': str(getattr(r, 'sha', '')),
                        'branch': str(getattr(r, 'git_branch', '')), 'why': str(getattr(r, 'why', '')),
                        'built': bool(getattr(r, 'built', False)),
                        'core_ok': bool(getattr(r, 'core_ok', False)),
                        'selftests': {'suites': int(getattr(r, 'selftest_suites', 0) or 0),
                                      'passed': int(getattr(r, 'selftest_passed', 0) or 0),
                                      'failed': int(getattr(r, 'selftest_failed', 0) or 0)},
                        'scans': _json.loads(getattr(r, 'scans_json', '{}') or '{}'),
                        'run': str(getattr(r, 'run', '')), 'at': str(getattr(r, 'at', ''))})
        response.media = {'ok': True, 'count': len(out), 'verdicts': out,
                          'how': 'ONE answer per superproject sha on the test branch. `passed` is the only '
                                 'one that may be promoted to main; scans are advisory and are carried here '
                                 'without ever changing a verdict.'}

    def on_get_results(self, request, response):
        device = (request.params.get('device') or '').strip()
        version = (request.params.get('version') or '').strip()
        rows = R.results(self.manager, device, version)
        import json as _json
        out = []
        for r in rows:
            try:
                res = _json.loads(getattr(r, 'results_json', '{}') or '{}')
            except Exception:
                res = {}
            out.append({'result': str(getattr(r, 'name', '')), 'run': str(getattr(r, 'run', '')),
                        'version': str(getattr(r, 'version', '')),
                        'stage': int(getattr(r, 'stage_index', 0) or 0),
                        'apps': _json.loads(getattr(r, 'apps_json', '[]') or '[]'),
                        'core_ok': bool(getattr(r, 'core_ok', False)), 'results': res,
                        # ci-10: the teardown, as two readings — the product's hand-back (gates the
                        # release) and our own leak diff (gates the next stage, never a release)
                        'uninstall_verdict': str(getattr(r, 'uninstall_verdict', 'skipped')),
                        'leak_verdict': str(getattr(r, 'leak_verdict', 'clean')),
                        'leaks': _json.loads(getattr(r, 'leaks_json', '[]') or '[]'),
                        'ram_delta_mb': int(getattr(r, 'ram_delta_mb', 0) or 0),
                        'disk_delta_mb': int(getattr(r, 'disk_delta_mb', 0) or 0),
                        'started': str(getattr(r, 'started', '')), 'finished': str(getattr(r, 'finished', '')),
                        'error': str(getattr(r, 'error', ''))})
        response.media = {'ok': True, 'count': len(out), 'results': out, 'release_rule': R.RELEASE_RULE}

    def on_get_releases(self, request, response):
        device = (request.params.get('device') or '').strip()
        rows = R.releases(self.manager, device)
        import json as _json
        out = []
        for r in rows:
            out.append({'release': str(getattr(r, 'name', '')), 'version': str(getattr(r, 'version', '')),
                        'tag': str(getattr(r, 'tag', '')), 'tag_pushed': bool(getattr(r, 'tag_pushed', False)),
                        'results_present': bool(getattr(r, 'results_present', False)),
                        'core_ok': bool(getattr(r, 'core_ok', False)),
                        'published_routes': _json.loads(getattr(r, 'published_routes_json', '[]') or '[]'),
                        'dry_routes': _json.loads(getattr(r, 'dry_routes_json', '{}') or '{}'),
                        'released': _json.loads(getattr(r, 'released_json', '[]') or '[]'),
                        'not_released': _json.loads(getattr(r, 'not_released_json', '{}') or '{}'),
                        'why_not': str(getattr(r, 'why_not', ''))})
        response.media = {'ok': True, 'count': len(out), 'releases': out, 'release_rule': R.RELEASE_RULE}
