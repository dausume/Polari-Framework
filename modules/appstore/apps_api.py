"""
@module appstore.apps_api

The app-deb API (his ask 2026-09-13): an AI or a script asks for apps directly, without the HTML page —
  GET  /api/apps                               the catalogue: EVERY registered module (downloaded or not),
                                               per flavour availability, estimates, requirements, the space
  GET  /api/apps/{module}/status?flavor=…      is it available for download? (ready | generating | not-generated |
                                               refused), what the flavour carries, the space check
  POST /api/apps/{module}/request?flavor=…     make it available: fetch the module's repository if its code is
                                               not here, check the space, start generation → 202 + the status
                                               and download URLs; 200 when it is already ready; 507 when the
                                               disk cannot hold it (with the numbers)
  GET  /api/apps/{module}/download?flavor=…    the file when ready (200, the deb), 202 + status while it
                                               generates, 404/409 with a sentence otherwise
  GET  /api/downloads                          the pre-prepped platform installers with their URLs
Online vs offline is a first-class difference everywhere: ONLINE = the small deb, libraries fetched from the
internet at setup (listed with measured sizes); OFFLINE = the wheels ride inside (bigger, slower to generate)
and are installed at admission with --no-index, skipping what is already present; system engines are named by
where they really live (inside the Polari runtime image, host-level with the platform installer / offline
media, or a named gap). Every JSON reply says which. The HTML page (/downloads/apps) is a client of the same builder.
"""
import hashlib
import os
import shutil
import time

from objectTreeDecorators import treeObject, treeObjectInit

from appstore.custom import app_deb_builder as builder
from appstore.custom import module_requirements as modreqs

FLAVORS = ('online', 'offline')
SPACE_MARGIN_BYTES = 200 * 1024 * 1024   # keep this much free after a generation
_sha_cache = {}


def _flavor(request):
    f = request.params.get('flavor', 'online')
    return f if f in FLAVORS else 'online'


def _sha256(path):
    key = (path, os.path.getmtime(path))
    if key not in _sha_cache:
        h = hashlib.sha256()
        with open(path, 'rb') as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b''):
                h.update(chunk)
        _sha_cache[key] = h.hexdigest()
    return _sha_cache[key]


def _module_dir_bytes(module, entry):
    root = builder._framework_root() if hasattr(builder, '_framework_root') else None
    try:
        from moduleService.module_registry import _framework_root
        root = _framework_root()
    except Exception:
        pass
    path = os.path.join(root or '', entry.get('path') or f'modules/{module}')
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in ('__pycache__', '.git', 'node_modules')]
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total


def expected_bytes(module, entry, flavor, reqs=None):
    """What the deb will weigh: the median of recorded generations for this flavour, else the payload
    (+ the measured libraries for offline). Honest about being an estimate."""
    sizes = [r['bytes'] for r in builder.generation_records(module) if r.get('flavor', 'online') == flavor and isinstance(r.get('bytes'), (int, float))]
    if sizes:
        return int(sorted(sizes)[len(sizes) // 2]), 'median of recorded generations'
    payload = _module_dir_bytes(module, entry) if entry.get('downloaded') else 0
    if flavor == 'offline' and reqs:
        return int(payload * 0.4 + reqs.get('librariesBytes', 0)), 'payload + measured libraries (never generated yet)'
    return int(payload * 0.4) if payload else 0, 'compressed payload guess (never generated yet)' if payload else 'unknown until the code is fetched'


def space(needed_bytes):
    try:
        usage = shutil.disk_usage(builder.pool_dir() if os.path.isdir(builder.pool_dir()) else builder.work_dir())
        free = usage.free
    except Exception:
        return {'free_bytes': None, 'needed_bytes': needed_bytes, 'ok': True, 'note': 'disk usage unreadable'}
    needed = needed_bytes * 3 + SPACE_MARGIN_BYTES   # sources + the deb + the tar inside it
    return {'free_bytes': free, 'needed_bytes': needed, 'ok': free > needed,
            'note': '' if free > needed else f'not enough space to generate: {free // (1 << 20)} MB free, about {needed // (1 << 20)} MB needed'}


# where a SYSTEM engine really lives: Polari runs in its backend image, which bakes these in (Dockerfile apk);
# host-level ones come with the platform installer / the offline media; anything else is a named gap
ENGINES_IN_RUNTIME_IMAGE = ('ngspice', 'ffmpeg')
ENGINES_HOST_LEVEL = ('docker', 'libvirt', 'wireguard-tools', 'qemu')


def flavor_differences(reqs, flavor):
    libs = reqs.get('libraries') or []
    engines = reqs.get('engines') or []
    lib_mb = (reqs.get('librariesBytes') or 0) // (1 << 20)
    unmeasured = reqs.get('librariesUnmeasured') or 0
    sys_engines = [e.get('name') for e in engines if e.get('kind') == 'system']
    py_engines = [e.get('name') for e in engines if e.get('kind') == 'python']
    in_image = [e for e in sys_engines if e in ENGINES_IN_RUNTIME_IMAGE]
    host_level = [e for e in sys_engines if e in ENGINES_HOST_LEVEL]
    gap = [e for e in sys_engines if e not in ENGINES_IN_RUNTIME_IMAGE and e not in ENGINES_HOST_LEVEL]
    engines_note = {'in_runtime_image': in_image, 'host_level': host_level, 'not_available_anywhere_yet': gap}
    if flavor == 'online':
        return {'carries': 'the app only', 'fetched_at_setup': f"{len(libs)} pip libraries (~{lib_mb} MB measured{', ' + str(unmeasured) + ' unmeasured' if unmeasured else ''})" + (f" + python engines {py_engines}" if py_engines else ''),
                'not_inside': sys_engines, 'engines': engines_note, 'needs_internet_at_setup': True,
                'reading': 'small download; the machine needs the internet when the app is set up'}
    return {'carries': f"the app + {len(libs)} pip libraries as wheels (~{lib_mb} MB)" + (f" + python engines {py_engines}" if py_engines else ''),
            'fetched_at_setup': 'nothing from pip — installed from the carried wheels, skipping what is already present',
            'not_inside': sys_engines, 'engines': engines_note, 'needs_internet_at_setup': bool(host_level or gap),
            'reading': ('no internet needed at setup' + (f"; system engines {in_image} are already inside the Polari runtime image" if in_image else '')
                        + (f"; host-level engines {host_level} come with the platform installer / the offline media" if host_level else '')
                        + (f"; engines {gap} are NOT available anywhere yet (a gap, named)" if gap else ''))}


def status_of(module, flavor, registry=None):
    registry = registry or builder.registry_modules()
    entry = registry.get(module)
    if entry is None:
        return {'ok': False, 'module': module, 'flavor': flavor, 'state': 'unknown', 'refusal': f'"{module}" is not in the module registry'}
    builder.purge_expired()
    reqs = modreqs.module_requirements(module) if entry.get('downloaded') else {'libraries': [], 'librariesBytes': 0, 'librariesUnmeasured': 0, 'engines': modreqs.module_engines(module)}
    need, need_basis = expected_bytes(module, entry, flavor, reqs)
    pool = builder.pool_file_for(module, flavor)
    job = builder.generation_job(module, flavor)
    out = {'ok': True, 'module': module, 'flavor': flavor, 'downloaded': bool(entry.get('downloaded')), 'kind': entry.get('kind', ''), 'tier': entry.get('tier', ''),
           'repo': entry.get('repo', ''), 'description': entry.get('description', ''),
           'estimate_seconds': builder.estimate_seconds(module, flavor=flavor), 'expected_bytes': need, 'expected_basis': need_basis,
           'space': space(need), 'differences': flavor_differences(reqs, flavor), 'requirements': {'libraries': len(reqs.get('libraries') or []), 'librariesBytes': reqs.get('librariesBytes', 0), 'engines': reqs.get('engines') or []},
           'status_url': f'/api/apps/{module}/status?flavor={flavor}', 'request_url': f'/api/apps/{module}/request?flavor={flavor}', 'download_url': f'/api/apps/{module}/download?flavor={flavor}'}
    try:
        from moduleService.hardware_reach import hardware_summary
        import json as _json
        from moduleService.manifests import manifest_path
        mp = manifest_path(module)
        if mp and os.path.isfile(mp):
            hs = hardware_summary(_json.load(open(mp, encoding='utf-8')))
            if hs.get('notice'):
                out['hardware'] = hs
    except Exception:
        pass
    if pool:
        path = os.path.join(builder.pool_dir(), pool['file'])
        out.update({'state': 'ready', 'file': pool['file'], 'bytes': pool['bytes'], 'sha256': _sha256(path), 'age_seconds': pool['ageSeconds'],
                    'expires_in_seconds': max(0, builder.ttl_seconds() - pool['ageSeconds']) if builder.ttl_seconds() > 0 else None,
                    'reading': f"{module} ({flavor}) is ready: GET {out['download_url']}"})
    elif job and job['state'] == 'running':
        out.update({'state': 'generating', 'step': job.get('step'), 'elapsed_seconds': int(time.time() - job['startedAt']), 'reading': f"generating ({job.get('step')}) — poll {out['status_url']}"})
    elif job and job['state'] == 'refused':
        out.update({'state': 'refused', 'refusal': (job.get('result') or {}).get('refusal', ''), 'reading': 'the last generation was refused; POST request again after fixing the cause'})
    else:
        out.update({'state': 'not-generated', 'reading': ('not generated yet: POST ' + out['request_url']) if entry.get('downloaded') else ('the code is not on this instance: POST ' + out['request_url'] + ' fetches it from its repository, then generates')})
    return out


def ensure_code(manager, module, entry):
    """The module's code on this instance: fetch its repository when absent (the registry knows the repo)."""
    if entry.get('downloaded'):
        return {'ok': True, 'fetched': False}
    if manager is None:
        return {'ok': False, 'refusal': 'no manager: cannot fetch a repository on this instance'}
    repo = entry.get('repo')
    if not repo:
        return {'ok': False, 'refusal': f'{module}: no repository recorded in the registry'}
    try:
        from polariApiServer.live_admission import _upsert_source_config
        from polariPeers.module_fetcher import fetch_module_project
        cfg = _upsert_source_config(manager, module, 'git', repo)
        if not cfg.get('ok'):
            return {'ok': False, 'refusal': 'could not record the module source', 'detail': cfg}
        fetched = fetch_module_project(manager, module, modules_dir=os.environ.get('POLARI_FETCHED_MODULES_DIR') or None)
        if not fetched.get('ok'):
            return {'ok': False, 'refusal': fetched.get('error') or 'fetch failed', 'detail': fetched}
        return {'ok': True, 'fetched': True, 'action': fetched.get('action'), 'path': fetched.get('path')}
    except Exception as exc:
        return {'ok': False, 'refusal': f'fetch failed: {type(exc).__name__}: {exc}'}


class AppsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/apps', self)
            add('/api/apps/{module}/status', self, suffix='status')
            add('/api/apps/{module}/request', self, suffix='request')
            add('/api/apps/{module}/download', self, suffix='download')
            add('/api/downloads', self, suffix='downloads')

    @staticmethod
    def _json(response, body, status='200 OK'):
        response.status = status
        response.media = body

    def on_get(self, request, response):
        registry = builder.registry_modules()
        builder.purge_expired()
        items = []
        for module, entry in sorted(registry.items()):
            row = {'module': module, 'kind': entry.get('kind', ''), 'tier': entry.get('tier', ''), 'downloaded': bool(entry.get('downloaded')), 'repo': entry.get('repo', ''),
                   'description': (entry.get('description') or '')[:200], 'flavors': {}}
            for f in FLAVORS:
                pool = builder.pool_file_for(module, f); job = builder.generation_job(module, f)
                row['flavors'][f] = {'state': 'ready' if pool else ('generating' if job and job['state'] == 'running' else 'not-generated'),
                                     'bytes': pool['bytes'] if pool else None, 'estimate_seconds': builder.estimate_seconds(module, flavor=f),
                                     'status_url': f'/api/apps/{module}/status?flavor={f}', 'request_url': f'/api/apps/{module}/request?flavor={f}', 'download_url': f'/api/apps/{module}/download?flavor={f}'}
            items.append(row)
        self._json(response, {'ok': True, 'count': len(items), 'downloaded': sum(1 for i in items if i['downloaded']), 'space': space(0),
                              'flavors': {'online': 'the small deb; libraries fetched from the internet at setup', 'offline': 'wheels inside; system engines not inside yet'},
                              'how': 'GET /api/apps/{module}/status?flavor=online|offline · POST /api/apps/{module}/request?flavor=… · GET /api/apps/{module}/download?flavor=…',
                              'apps': items})

    def on_get_status(self, request, response, module):
        st = status_of(module, _flavor(request))
        self._json(response, st, '200 OK' if st.get('ok') else '404 Not Found')

    def on_post_request(self, request, response, module):
        flavor = _flavor(request)
        registry = builder.registry_modules()
        entry = registry.get(module)
        if entry is None:
            return self._json(response, {'ok': False, 'module': module, 'refusal': f'"{module}" is not in the module registry'}, '404 Not Found')
        pool = builder.pool_file_for(module, flavor)
        if pool:
            return self._json(response, {**status_of(module, flavor, registry), 'reading': 'already available — GET the download URL'})
        fetched = ensure_code(self.manager, module, entry)
        if not fetched.get('ok'):
            return self._json(response, {'ok': False, 'module': module, 'flavor': flavor, 'state': 'refused', **fetched}, '409 Conflict')
        registry = builder.registry_modules(); entry = registry.get(module) or entry
        reqs = modreqs.module_requirements(module)
        need, basis = expected_bytes(module, entry, flavor, reqs)
        sp = space(need)
        if not sp['ok']:
            return self._json(response, {'ok': False, 'module': module, 'flavor': flavor, 'state': 'refused', 'refusal': sp['note'], 'space': sp, 'expected_bytes': need, 'expected_basis': basis}, '507 Insufficient Storage')
        job = builder.start_generation(module, flavor)
        st = status_of(module, flavor, registry)
        st.update({'fetched': fetched.get('fetched', False), 'job_state': job['state'], 'accepted': True})
        self._json(response, st, '202 Accepted' if st.get('state') != 'ready' else '200 OK')

    def on_get_download(self, request, response, module):
        flavor = _flavor(request)
        builder.purge_expired()
        pool = builder.pool_file_for(module, flavor)
        if pool:
            path = os.path.join(builder.pool_dir(), pool['file'])
            response.content_type = 'application/vnd.debian.binary-package'
            response.downloadable_as = pool['file']
            response.set_header('X-Polari-Sha256', _sha256(path))
            with open(path, 'rb') as fh:
                response.data = fh.read()
            return
        st = status_of(module, flavor)
        if st.get('state') == 'generating':
            return self._json(response, st, '202 Accepted')
        if not st.get('ok'):
            return self._json(response, st, '404 Not Found')
        self._json(response, {**st, 'refusal': f'not available yet — POST {st["request_url"]} first'}, '409 Conflict')

    def on_get_downloads(self, request, response):
        try:
            from appstore.downloads_page import staged_debs
            debs = staged_debs()
        except Exception as exc:
            return self._json(response, {'ok': False, 'error': f'platform debs unreadable: {exc}'}, '500 Internal Server Error')
        self._json(response, {'ok': True, 'count': len(debs), 'installers': [{'file': d.get('file'), 'package': d.get('package', ''), 'version': d.get('version', ''), 'bytes': d.get('size'), 'url': f"/downloads/{d.get('file')}", 'built': d.get('built', '')} for d in debs],
                              'apps': '/api/apps', 'offline_media': '/downloads/offline'})
