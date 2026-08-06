"""
@module appstore.appstore_api

AppStoreAPI: the /api/appstore surface. The catalog joins
AppShellDefinition rows with polariapps' PolariAppDefinitions (the
content layer — never duplicated here); identity is the
unauthenticated reachability probe every installed shell uses;
enroll/redeem is the one-time-token pre-registration flow; download
serves the overlaid Gradle source archive or a presigned prebuilt.

Thin Falcon shell — logic lives in appstore_tokens /
appstore_payloads / shell_project / appstore_minio.

@consumers
  - polariServer (instantiated next to AppsAPI)
  - polari-app-shell (the native client)
  - appstore.selftest_appstore (function-level)
"""

import json
import secrets

from objectTreeDecorators import treeObject, treeObjectInit

from appstore.appstore_basis import (
    AppShellDefinition, DISTRIBUTIONS, PLATFORM_KEYS, SHELL_SCOPES,
    ShellArtifact, ShellEnrollment, ShellInstallation,
)
from appstore.appstore_minio import (
    ARTIFACT_BUCKET, object_exists, presigned_get, presigned_put,
    store_status,
)
from appstore.appstore_payloads import (
    deep_link, identity_payload, registration_document,
)
from appstore.appstore_tokens import (
    expiry_iso, judge, mint, now_iso, split_wire,
)
from appstore.shell_project import build_download, stamp_generation

#: Author-editable AppShellDefinition fields (the _APP_FIELDS idiom).
_SHELL_FIELDS = ('title', 'description', 'scope', 'app_name',
                 'platforms_json', 'distribution', 'branding_json',
                 'start_route', 'published', 'notes')


class AppStoreAPI(treeObject):
    """App-store endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/appstore'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/appstore', self, suffix='catalog')
            add('/api/appstore/identity', self, suffix='identity')
            add('/api/appstore/definition', self, suffix='definition')
            add('/api/appstore/enroll/redeem', self, suffix='redeem')
            add('/api/appstore/enrollments', self,
                suffix='enrollments')
            add('/api/appstore/artifacts', self, suffix='artifacts')
            add('/api/appstore/{shell_name}', self, suffix='shell')
            add('/api/appstore/{shell_name}/enroll', self,
                suffix='enroll')
            add('/api/appstore/{shell_name}/download', self,
                suffix='download')
            add('/api/appstore/{shell_name}/registration', self,
                suffix='registration')

    # ---- helpers ----------------------------------------------------

    def _payload(self, request):
        try:
            raw = request.bounded_stream.read()
            return (json.loads(raw) if raw else {}), None
        except Exception as e:
            return None, f'bad JSON payload: {e}'

    def _table(self, class_name):
        return (getattr(self.manager, 'objectTables', None)
                or {}).get(class_name, {})

    def _find(self, class_name, name):
        for row in self._table(class_name).values():
            if getattr(row, 'name', '') == name:
                return row
        return None

    def _save(self, row):
        try:
            self.manager.db.saveInstanceInDB(row)
        except Exception:
            pass

    def _refuse(self, response, error, status='400 Bad Request',
                extra=None):
        response.status = status
        media = {'ok': False, 'error': error}
        if extra:
            media.update(extra)
        response.media = media

    def _user(self, request):
        """(user_info, roles) — middleware is lenient, so authed
        endpoints gate here."""
        ctx = getattr(request, 'context', None)
        return (getattr(ctx, 'user_info', None) or None,
                list(getattr(ctx, 'roles', []) or []))

    def _require_user(self, request, response):
        user, roles = self._user(request)
        if user is None:
            self._refuse(response, 'authentication required '
                         '(Bearer token)', '401 Unauthorized')
            return None, roles
        return user, roles

    # ---- catalog / identity -----------------------------------------

    def _shell_summary(self, shell):
        platforms = []
        try:
            platforms = json.loads(
                getattr(shell, 'platforms_json', '[]') or '[]')
        except ValueError:
            pass
        availability = {}
        for platform in platforms:
            if platform == 'gradle-project':
                artifact = self._artifact_for(
                    getattr(shell, 'name', ''), 'gradle-project')
                availability[platform] = {
                    'available': artifact is not None,
                    'how': ('' if artifact is not None else
                            'upload a srcDistTar archive via '
                            'POST /api/appstore/artifacts')}
            else:
                artifact = self._artifact_for(
                    getattr(shell, 'name', ''), platform)
                ready = False
                if artifact is not None:
                    exists = object_exists(
                        self.manager,
                        getattr(artifact, 'object_key', ''),
                        getattr(artifact, 'bucket', '')
                        or ARTIFACT_BUCKET)
                    ready = exists.get('ok', False)
                availability[platform] = {'available': ready}
        return {'name': getattr(shell, 'name', ''),
                'title': getattr(shell, 'title', ''),
                'description': getattr(shell, 'description', ''),
                'scope': getattr(shell, 'scope', 'instance'),
                'appName': getattr(shell, 'app_name', ''),
                'distribution': getattr(shell, 'distribution', ''),
                'platforms': availability,
                'published': bool(getattr(shell, 'published', True))}

    def _artifact_for(self, shell_name, platform):
        """Latest ShellArtifact row for (shell, platform) by
        version-then-name ordering — honest None when absent."""
        rows = [a for a in self._table('ShellArtifact').values()
                if getattr(a, 'shell_name', '') == shell_name
                and getattr(a, 'platform', '') == platform]
        if not rows:
            return None
        rows.sort(key=lambda a: (getattr(a, 'version', ''),
                                 getattr(a, 'name', '')))
        return rows[-1]

    def on_get_catalog(self, request, response):
        shells = [self._shell_summary(s)
                  for s in self._table('AppShellDefinition').values()
                  if getattr(s, 'published', True)]
        shells.sort(key=lambda s: s['name'])
        shelled_apps = {s['appName'] for s in shells if s['appName']}
        apps = []
        for app in self._table('PolariAppDefinition').values():
            name = getattr(app, 'name', '')
            apps.append({
                'name': name,
                'title': getattr(app, 'title', ''),
                'installable': name in shelled_apps or any(
                    s['scope'] == 'instance' for s in shells),
                'how': ('' if name in shelled_apps else
                        'the instance shell covers it; publish a '
                        'dedicated shell via POST '
                        '/api/appstore/definition')})
        apps.sort(key=lambda a: a['name'])
        response.media = {'ok': True, 'shells': shells, 'apps': apps,
                          'store': store_status(self.manager)}

    def on_get_identity(self, request, response):
        response.media = identity_payload(self.manager)

    def on_get_shell(self, request, response, shell_name):
        shell = self._find('AppShellDefinition', shell_name)
        if shell is None:
            return self._refuse(response,
                                f'no shell "{shell_name}"',
                                '404 Not Found')
        media = self._shell_summary(shell)
        media['ok'] = True
        response.media = media

    # ---- authoring --------------------------------------------------

    def on_post_definition(self, request, response):
        user, _ = self._require_user(request, response)
        if user is None:
            return
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        name = (payload or {}).get('name', '')
        if not name:
            return self._refuse(response, 'payload needs {name}')
        scope = payload.get('scope', 'instance')
        if scope not in SHELL_SCOPES:
            return self._refuse(
                response, f'scope must be one of {SHELL_SCOPES}')
        if scope == 'app':
            app_name = payload.get('app_name', '')
            if not self._find('PolariAppDefinition', app_name):
                return self._refuse(
                    response,
                    f'no PolariAppDefinition named "{app_name}" — '
                    'apps are the content layer (see /api/apps)')
        dist = payload.get('distribution', 'generated-project')
        if dist not in DISTRIBUTIONS:
            return self._refuse(
                response,
                f'distribution must be one of {DISTRIBUTIONS}')
        row = self._find('AppShellDefinition', name)
        created = row is None
        updates = {k: payload[k] for k in _SHELL_FIELDS
                   if k in payload}
        # A person's shell is NOT a prior (the apps_api contract:
        # is_prior=False rows are never touched by the seed pass).
        updates['is_prior'] = bool(payload.get('is_prior', False))
        if created:
            row = AppShellDefinition(name=name, **updates,
                                     manager=self.manager)
        else:
            for k, v in updates.items():
                setattr(row, k, v)
        self._save(row)
        response.media = {'ok': True, 'name': name,
                          'created': created,
                          'updated': sorted(updates)}

    # ---- enrollment -------------------------------------------------

    def on_post_enroll(self, request, response, shell_name):
        """Mint a one-time enrollment token. The response is the ONLY
        place the plaintext token exists server-side."""
        user, _ = self._require_user(request, response)
        if user is None:
            return
        shell = self._find('AppShellDefinition', shell_name)
        if shell is None:
            return self._refuse(response,
                                f'no shell "{shell_name}"',
                                '404 Not Found')
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        token = mint()
        expires = expiry_iso((payload or {}).get('ttlSeconds'))
        username = (user.get('preferred_username')
                    or user.get('username') or '')
        row = ShellEnrollment(
            name=token['name'],
            token_hash=token['tokenHash'],
            shell_name=shell_name,
            instance_name=(payload or {}).get('instanceName', ''),
            user_sub=user.get('sub', ''),
            username=username,
            created_at=now_iso(),
            expires_at=expires,
            status='active',
            is_prior=False,
            notes=(payload or {}).get('deviceLabel', ''),
            manager=self.manager)
        self._save(row)
        doc = registration_document(
            self.manager, shell, enrollment_wire=token['wire'],
            enrollment_expires_at=expires, username=username)
        link = deep_link(self.manager, token['wire'])
        response.media = {
            'ok': True,
            'token': token['wire'],
            'tokenId': token['name'],
            'expiresAt': expires,
            'deepLink': link.get('deepLink', ''),
            'qrPayload': link.get('qrPayload', ''),
            'registration': doc if doc.get('ok') else None,
            'registrationProblem': (None if doc.get('ok') else doc),
        }

    def on_post_redeem(self, request, response):
        """Single-use redemption — the token IS the credential. The
        row flips to 'redeemed' and is SAVED before the response is
        written, so a replay of the same wire token always refuses."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        wire = (payload or {}).get('token', '')
        name, secret = split_wire(wire)
        if name is None:
            return self._refuse(response,
                                'token must be "<id>.<secret>"')
        row = self._find('ShellEnrollment', name)
        if row is None:
            return self._refuse(response, 'unknown token',
                                '404 Not Found')
        verdict = judge(getattr(row, 'status', ''),
                        getattr(row, 'token_hash', ''),
                        getattr(row, 'expires_at', ''), secret)
        if not verdict['ok']:
            return self._refuse(response, verdict['error'],
                                '403 Forbidden')
        row.status = 'redeemed'
        row.redeemed_at = now_iso()
        row.redeemed_by_platform = (payload or {}).get('platform', '')
        remote = ''
        try:
            remote = request.remote_addr or ''
        except Exception:
            pass
        device = (payload or {}).get('deviceLabel', '')
        row.redeemed_evidence = json.dumps(
            {'deviceLabel': device, 'remoteAddr': remote})
        self._save(row)
        install = ShellInstallation(
            name='inst-' + secrets.token_hex(6),
            enrollment_name=name,
            shell_name=getattr(row, 'shell_name', ''),
            instance_name=getattr(row, 'instance_name', ''),
            platform=(payload or {}).get('platform', ''),
            device_label=device,
            user_sub=getattr(row, 'user_sub', ''),
            registered_at=now_iso(),
            last_seen_at=now_iso(),
            is_prior=False,
            manager=self.manager)
        self._save(install)
        shell = self._find('AppShellDefinition',
                           getattr(row, 'shell_name', ''))
        if shell is None:
            return self._refuse(
                response,
                'enrollment names a shell that no longer exists',
                '410 Gone')
        doc = registration_document(
            self.manager, shell,
            username=getattr(row, 'username', ''))
        if not doc.get('ok'):
            return self._refuse(response, doc.get('error', ''),
                                extra={'suggestion':
                                       doc.get('suggestion')})
        doc['installation'] = getattr(install, 'name', '')
        response.media = doc

    def on_get_enrollments(self, request, response):
        """Own rows; 'admin' role sees all. NEVER hashes/secrets."""
        user, roles = self._require_user(request, response)
        if user is None:
            return
        sub = user.get('sub', '')
        is_admin = 'admin' in roles
        rows = []
        for row in self._table('ShellEnrollment').values():
            if not is_admin and getattr(row, 'user_sub', '') != sub:
                continue
            rows.append({
                'name': getattr(row, 'name', ''),
                'shellName': getattr(row, 'shell_name', ''),
                'username': getattr(row, 'username', ''),
                'createdAt': getattr(row, 'created_at', ''),
                'expiresAt': getattr(row, 'expires_at', ''),
                'status': getattr(row, 'status', ''),
                'redeemedAt': getattr(row, 'redeemed_at', ''),
                'redeemedByPlatform':
                    getattr(row, 'redeemed_by_platform', '')})
        rows.sort(key=lambda r: r['createdAt'], reverse=True)
        response.media = {'ok': True, 'enrollments': rows,
                          'scope': 'all' if is_admin else 'own'}

    def on_post_enrollments(self, request, response):
        """{action: 'revoke', name} — minter or admin."""
        user, roles = self._require_user(request, response)
        if user is None:
            return
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        if (payload or {}).get('action') != 'revoke':
            return self._refuse(response,
                                'unknown action (revoke)')
        name = payload.get('name', '')
        row = self._find('ShellEnrollment', name)
        if row is None:
            return self._refuse(response,
                                f'no enrollment "{name}"',
                                '404 Not Found')
        if ('admin' not in roles
                and getattr(row, 'user_sub', '') != user.get('sub')):
            return self._refuse(
                response,
                'only the minter or an admin can revoke',
                '403 Forbidden')
        row.status = 'revoked'
        self._save(row)
        response.media = {'ok': True, 'name': name,
                          'status': 'revoked'}

    # ---- downloads --------------------------------------------------

    def _registration_for(self, response, shell, enrollment_wire):
        """Registration doc for a download/registration request. An
        enrollment param must reference a LIVE token (unredeemed —
        redemption happens on first launch, not at download)."""
        username = ''
        expires = ''
        if enrollment_wire:
            name, secret = split_wire(enrollment_wire)
            row = self._find('ShellEnrollment', name) \
                if name else None
            if row is None:
                self._refuse(response, 'unknown enrollment token',
                             '404 Not Found')
                return None
            verdict = judge(getattr(row, 'status', ''),
                            getattr(row, 'token_hash', ''),
                            getattr(row, 'expires_at', ''), secret)
            if not verdict['ok']:
                self._refuse(response, verdict['error'],
                             '403 Forbidden')
                return None
            username = getattr(row, 'username', '')
            expires = getattr(row, 'expires_at', '')
        doc = registration_document(
            self.manager, shell,
            enrollment_wire=enrollment_wire or None,
            enrollment_expires_at=expires, username=username)
        if not doc.get('ok'):
            self._refuse(response, doc.get('error', ''),
                         extra={'suggestion': doc.get('suggestion')})
            return None
        return doc

    def on_get_registration(self, request, response, shell_name):
        """Config-only registration file (the climate ?download=1
        convention: envelope by default, raw file on demand)."""
        shell = self._find('AppShellDefinition', shell_name)
        if shell is None:
            return self._refuse(response,
                                f'no shell "{shell_name}"',
                                '404 Not Found')
        doc = self._registration_for(
            response, shell,
            request.params.get('enrollment', ''))
        if doc is None:
            return
        if request.params.get('download', '') == '1':
            body = json.dumps(
                {k: v for k, v in doc.items() if k != 'ok'},
                indent=2, sort_keys=True)
            response.content_type = 'application/json'
            response.downloadable_as = 'polari-shell.json'
            response.data = body.encode('utf-8')
            return
        response.media = {'ok': True, 'registration':
                          {k: v for k, v in doc.items()
                           if k != 'ok'},
                          'provenance': {
                              'shell': shell_name,
                              'generatedAt': now_iso()}}

    def on_get_download(self, request, response, shell_name):
        shell = self._find('AppShellDefinition', shell_name)
        if shell is None:
            return self._refuse(response,
                                f'no shell "{shell_name}"',
                                '404 Not Found')
        platform = request.params.get('platform', 'gradle-project')
        if platform not in PLATFORM_KEYS:
            return self._refuse(
                response,
                f'platform must be one of {PLATFORM_KEYS}')
        artifact = self._artifact_for(shell_name, platform)
        if platform == 'gradle-project':
            doc = self._registration_for(
                response, shell,
                request.params.get('enrollment', ''))
            if doc is None:
                return
            built = build_download(self.manager, shell, artifact,
                                   doc)
            if not built.get('ok'):
                return self._refuse(
                    response, built.get('error', ''),
                    extra={k: v for k, v in built.items()
                           if k not in ('ok', 'error')})
            stamp_generation(self.manager, artifact,
                             built['manifest'])
            response.content_type = 'application/gzip'
            response.downloadable_as = built['filename']
            response.data = built['data']
            return
        # Prebuilt: config never mutates the binary — signed
        # installers and APKs cannot be rewritten without re-signing,
        # so registration travels as the sidecar /registration file
        # or a deep link. Refusals say exactly that.
        if artifact is None:
            return self._refuse(
                response,
                f'no prebuilt artifact for platform "{platform}"',
                '404 Not Found',
                extra={'suggestion': {
                    'knob': 'POST /api/appstore/artifacts',
                    'action': 'build the shell for this platform '
                              'out-of-band and commit it'}})
        key = getattr(artifact, 'object_key', '')
        bucket = getattr(artifact, 'bucket', '') or ARTIFACT_BUCKET
        if request.params.get('direct', '') == '1':
            from appstore.appstore_minio import get_bytes
            fetched = get_bytes(self.manager, key, bucket)
            if not fetched.get('ok'):
                return self._refuse(response,
                                    fetched.get('error', ''),
                                    extra={'suggestion':
                                           fetched.get('suggestion')})
            response.content_type = 'application/octet-stream'
            response.downloadable_as = key.rsplit('/', 1)[-1]
            response.data = fetched['data']
            return
        signed = presigned_get(self.manager, key, bucket)
        if not signed.get('ok'):
            return self._refuse(response, signed.get('error', ''),
                                extra={'suggestion':
                                       signed.get('suggestion')})
        response.status = '302 Found'
        response.set_header('Location', signed['url'])
        response.media = {'ok': True, 'url': signed['url'],
                          'note': 'sidecar registration: GET '
                                  f'/api/appstore/{shell_name}/'
                                  'registration?download=1'}

    # ---- artifact uploads (admin) -----------------------------------

    def on_post_artifacts(self, request, response):
        """{action: 'presign-put'|'commit', ...} — admin role only.
        presign-put -> a time-limited PUT URL; commit verifies the
        object landed and records the ShellArtifact row."""
        user, roles = self._require_user(request, response)
        if user is None:
            return
        if 'admin' not in roles:
            return self._refuse(response, 'admin role required',
                                '403 Forbidden')
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        action = (payload or {}).get('action', '')
        if action == 'presign-put':
            shell = payload.get('shellName', '')
            platform = payload.get('platform', '')
            version = payload.get('version', '')
            if not shell or platform not in PLATFORM_KEYS \
                    or not version:
                return self._refuse(
                    response,
                    'needs {shellName, platform (one of '
                    f'{PLATFORM_KEYS}), version}}')
            key = f'{shell}/{platform}/{version}.tar.gz' \
                if platform == 'gradle-project' \
                else f'{shell}/{platform}/{version}'
            signed = presigned_put(self.manager, key)
            if not signed.get('ok'):
                return self._refuse(
                    response, signed.get('error', ''),
                    extra={'suggestion': signed.get('suggestion')})
            signed['objectKey'] = key
            response.media = signed
            return
        if action == 'commit':
            shell = payload.get('shellName', '')
            platform = payload.get('platform', '')
            version = payload.get('version', '')
            key = payload.get('objectKey', '')
            if not shell or not platform or not version or not key:
                return self._refuse(
                    response,
                    'needs {shellName, platform, version, '
                    'objectKey, sha256?, sizeBytes?}')
            exists = object_exists(self.manager, key)
            if not exists.get('ok'):
                return self._refuse(
                    response, exists.get('error', ''),
                    extra={'suggestion': exists.get('suggestion')})
            name = f'{shell}@{platform}@{version}'
            row = self._find('ShellArtifact', name)
            kind = ('source-archive'
                    if platform == 'gradle-project'
                    else 'prebuilt-binary')
            fields = dict(
                shell_name=shell, platform=platform,
                version=version, kind=kind,
                bucket=ARTIFACT_BUCKET, object_key=key,
                sha256=payload.get('sha256', ''),
                size_bytes=int(payload.get('sizeBytes')
                               or exists.get('sizeBytes', 0)),
                uploaded_by=user.get('sub', ''),
                uploaded_at=now_iso(), is_prior=False)
            if row is None:
                row = ShellArtifact(name=name, **fields,
                                    manager=self.manager)
            else:
                for k, v in fields.items():
                    setattr(row, k, v)
            self._save(row)
            response.media = {'ok': True, 'artifact': name,
                              'sizeBytes': fields['size_bytes']}
            return
        return self._refuse(
            response,
            'unknown action (presign-put | commit)')
