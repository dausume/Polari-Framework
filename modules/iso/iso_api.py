"""
@module iso.iso_api

The ISO doors, for people and for scripts (ISO plan §P; his ask 2026-09-15: a standard part of the production deployment):
  GET  /downloads/iso                    the human page: 1 probe · 2 choose · 3 install (server-rendered, zero JS)
  GET  /api/iso                          summary: bases (cached?), probes, builds, the pool, the tools present
  GET  /api/iso/probe-kit                the probe kit as a zip (README.html + the three launchers)
  POST /api/iso/probe                    a probe report (JSON) → DeviceProbe row + the derived verdict
  GET  /api/iso/probes                   every probed device with its verdict and suggested role
  GET  /api/iso/compat/{hash}            one device's verdict (re-derived against the default base)
  POST /api/iso/bases/{name}/fetch       cache a base (download + checksum + kernel table) — a background job
  GET  /api/iso/bases                    the bases and their state
  POST /api/iso/build                    request an image {base, role, shape, encryption, secure_boot, posture, look, hostname, ssh_keys, join_*, target_hash, apps}
  GET  /api/iso/builds                   every build with its state
  GET  /api/iso/builds/{id}/status       one build (steps, refusal, file)
  GET  /api/iso/builds/{id}/download     the image, streamed, sha256 header
  GET  /api/iso/autoinstall/preview      the autoinstall YAML a set of choices renders to (no build)
"""
import glob
import hashlib
import html
import json
import os
import time

from objectTreeDecorators import treeObject, treeObjectInit

from iso.custom import iso_autoinstall, iso_builder, iso_compat, iso_probe_kit
from iso.iso_basis import DeviceProbe, IsoBase, IsoBuild, LOOKS, POSTURES, ROLES, SHAPES
from iso.iso_seed import SEED_ISO_BASES


def _platform_debs():
    """The platform installer(s) staged for /downloads — the ISO carries them (offline first)."""
    try:
        from appstore.downloads_page import downloads_dir
        return sorted(glob.glob(os.path.join(downloads_dir(), 'polari-complete_*.deb')))
    except Exception:
        return []


def core_public_key():
    """The core's outward ssh key (his ask 2026-09-15: manipulate every device from the core). Read from
    POLARI_CORE_SSH_PUBKEY (the text) or POLARI_CORE_SSH_PUBKEY_FILE (default /app/data/keys/core.pub) — placed
    by `pol iso keys init`; '' when the core has none yet."""
    txt = os.environ.get('POLARI_CORE_SSH_PUBKEY', '').strip()
    if txt:
        return txt
    path = os.environ.get('POLARI_CORE_SSH_PUBKEY_FILE', '/app/data/keys/core.pub')
    try:
        return open(path).read().strip()
    except OSError:
        return ''


def _app_debs(names):
    try:
        from appstore.custom import app_deb_builder as builder
        out = []
        for n in [x.strip() for x in (names or '').split(',') if x.strip()]:
            pf = builder.pool_file_for(n, 'offline', 'install')
            if pf:
                out.append(os.path.join(builder.pool_dir(), pf['file']))
        return out
    except Exception:
        return []


class _Stream:
    def __init__(self, path, filename, size):
        self._f = open(path, 'rb'); self._n = filename; self._s = size; self._t = time.time(); self._done = False

    def read(self, n=-1):
        return self._f.read(n)

    def close(self):
        if not self._done:
            self._done = True; self._f.close(); iso_builder.note_download(self._n, max(0.001, time.time() - self._t), self._s)


class IsoAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/downloads/iso', self, suffix='page')
            add('/api/iso', self)
            add('/api/iso/probe-kit', self, suffix='probe_kit')
            add('/api/iso/probe', self, suffix='probe')
            add('/api/iso/probes', self, suffix='probes')
            add('/api/iso/compat/{hw_hash}', self, suffix='compat')
            add('/api/iso/bases', self, suffix='bases')
            add('/api/iso/bases/{name}/fetch', self, suffix='base_fetch')
            add('/api/iso/build', self, suffix='build')
            add('/api/iso/builds', self, suffix='builds')
            add('/api/iso/builds/{build_id}/status', self, suffix='build_status')
            add('/api/iso/builds/{build_id}/download', self, suffix='build_download')
            add('/api/iso/autoinstall/preview', self, suffix='preview')
            add('/api/iso/joined', self, suffix='joined')
            add('/api/iso/core-key', self, suffix='core_key')

    # ---- helpers ------------------------------------------------------------------------------------------------
    def _rows(self, cls):
        return list(((getattr(self.manager, 'objectTables', None) or {}).get(cls, {}) or {}).values())

    def _upsert(self, class_name, cls, row):
        if self.manager is None:
            return None
        tables = getattr(self.manager, 'objectTables', None) or {}
        for r in (tables.get(class_name) or {}).values():
            if getattr(r, 'name', None) == row.get('name'):
                for k, v in row.items():
                    setattr(r, k, v)
                return r
        try:
            return cls(manager=self.manager, **row)
        except Exception:
            return None

    def _persist(self):
        """Rows posted from a stick must survive a restart: persist the tree off the request thread (the periodic
        persist may not run before a redeploy — seen 2026-09-15: a probe row vanished)."""
        m = self.manager
        if m is None or not hasattr(m, 'persistTree'):
            return
        import threading
        threading.Thread(target=lambda: (lambda: m.persistTree())() if True else None, daemon=True).start()

    @staticmethod
    def _json(response, body, status='200 OK'):
        response.status = status; response.media = body

    def _bases(self):
        rows = [dict(b) for b in SEED_ISO_BASES]
        return [{**b, **iso_builder.base_status(b)} for b in rows]

    def _default_base(self):
        bs = self._bases()
        return next((b for b in bs if b.get('default')), bs[0] if bs else None)

    def _alias_rows(self, base=None):
        b = base or self._default_base()
        return (iso_compat.load_alias_table(b['kernel_table']) if b and b.get('kernel_table') else []), (b['name'] if b else '')

    def _probe_rows(self):
        return [{k: getattr(r, k, '') for k in ('hw_hash', 'label', 'os_name', 'os_version', 'cpu', 'arch', 'memory_gb', 'free_gb', 'firmware', 'secure_boot', 'tpm', 'disk_encryption', 'raid_mode', 'gpu', 'wifi', 'nics', 'virtualization', 'apple_silicon', 'verdict', 'verdict_text', 'base_checked', 'drivers_in_kernel', 'drivers_firmware', 'drivers_third_party', 'drivers_missing', 'traps', 'suggested_role', 'suggested_reason', 'probed_at')}
                for r in self._rows('DeviceProbe')]

    def _build_rows(self):
        out = []
        for r in self._rows('IsoBuild'):
            d = {k: getattr(r, k, '') for k in ('name', 'base', 'role', 'shape', 'encryption', 'secure_boot', 'posture', 'look', 'hostname', 'target_hash', 'apps', 'offline', 'state', 'step', 'refusal', 'warnings', 'file', 'sha256', 'bytes', 'seconds', 'requested_at', 'built_at')}
            job = iso_builder.build_job_by_id(d['name'])   # the row's name IS the build id (re-hashing the row would miss: defaults differ)
            if job:
                d['state'] = job['state'] if job['state'] != 'done' else 'ready'; d['step'] = job['step']
                if job['result'] and job['result'].get('ok'):
                    d.update({'file': job['result']['file'], 'sha256': job['result']['sha256'], 'bytes': job['result']['bytes']})
                elif job['result']:
                    d['refusal'] = job['result'].get('refusal', '')
            if not d.get('file') and not (job and job['state'] == 'running'):
                # after a restart the job table is empty but the image may still be in the pool: recognise it by its id
                hit = glob.glob(os.path.join(iso_builder.pool_dir(), f"*-{d['name']}.iso"))
                if hit:
                    path = hit[0]; d.update({'file': os.path.basename(path), 'bytes': os.path.getsize(path), 'sha256': d.get('sha256') or iso_builder._sha256(path), 'state': 'ready', 'step': 'cached'})
            if d.get('file') and d.get('state') == 'ready':
                for k in ('file', 'sha256', 'bytes', 'state'):   # persist onto the row so the next read is free
                    setattr(r, k, d[k])
            if d.get('file'):
                d['hold'] = iso_builder.pool_entry(d['file']); d['download_url'] = f"/api/iso/builds/{d['name']}/download"
            out.append(d)
        return out

    # ---- routes -------------------------------------------------------------------------------------------------
    def on_get(self, request, response):
        iso_builder.purge_idle()
        self._json(response, {'ok': True, 'bases': self._bases(), 'probes': len(self._rows('DeviceProbe')), 'builds': len(self._rows('IsoBuild')), 'pool': iso_builder.pool_status(),
                              'tools': iso_builder.tools(), 'platform_debs': [os.path.basename(p) for p in _platform_debs()], 'roles': ROLES, 'shapes': SHAPES, 'postures': POSTURES, 'looks': LOOKS,
                              'how': 'GET /api/iso/probe-kit → the stick; POST /api/iso/probe ← a report; POST /api/iso/build ← choices; GET /api/iso/builds/{id}/download'})

    def on_get_probe_kit(self, request, response):
        data = iso_probe_kit.kit_zip()
        response.content_type = 'application/zip'; response.downloadable_as = 'polari-probe-kit.zip'
        response.set_header('Content-Length', str(len(data))); response.data = data

    def on_post_probe(self, request, response):
        try:
            report = request.media or {}
        except Exception:
            report = {}
        if not isinstance(report, dict) or not (report.get('device_ids') is not None or report.get('cpu') or report.get('apple_silicon')):
            return self._json(response, {'ok': False, 'refusal': 'body: the probe report JSON (probe/cache/<hash>.json from the stick)'}, '400 Bad Request')
        alias, base_name = self._alias_rows()
        v = iso_compat.verdict(report, alias, base_name)
        role, why = iso_compat.suggest_role(report)
        row = iso_compat.summarize(report)
        row.update({'name': 'probe:' + row['hw_hash'], 'verdict': v['verdict'], 'verdict_text': v['text'], 'base_checked': base_name, 'traps': '; '.join(t['text'] for t in v['traps']),
                    'drivers_in_kernel': v['counts'].get('in_kernel', 0), 'drivers_firmware': v['counts'].get('firmware', 0), 'drivers_third_party': v['counts'].get('third_party', 0), 'drivers_missing': v['counts'].get('missing', 0),
                    'suggested_role': role if not v['apple_silicon'] else '', 'suggested_reason': why if not v['apple_silicon'] else 'not installable'})
        obj = self._upsert('DeviceProbe', DeviceProbe, row); self._persist()
        self._json(response, {'ok': True, 'stored': obj is not None, 'hw_hash': row['hw_hash'], 'verdict': v, 'suggested_role': row['suggested_role'], 'suggested_reason': row['suggested_reason'],
                              'next': f"choose: POST /api/iso/build with target_hash={row['hw_hash']} and the role" if not v['apple_silicon'] else ''})

    def on_get_probes(self, request, response):
        self._json(response, {'ok': True, 'count': len(self._rows('DeviceProbe')), 'probes': self._probe_rows()})

    def on_get_compat(self, request, response, hw_hash):
        r = next((r for r in self._rows('DeviceProbe') if getattr(r, 'hw_hash', '') == hw_hash), None)
        if r is None:
            return self._json(response, {'ok': False, 'refusal': f'no probe with hash {hw_hash}'}, '404 Not Found')
        try:
            report = json.loads(getattr(r, 'raw_json', '') or '{}')
        except ValueError:
            report = {}
        alias, base_name = self._alias_rows()
        self._json(response, {'ok': True, 'hw_hash': hw_hash, **iso_compat.verdict(report, alias, base_name)})

    def on_get_bases(self, request, response):
        self._json(response, {'ok': True, 'bases': self._bases(), 'how': 'POST /api/iso/bases/{name}/fetch caches one (a 2–3 GB download + the kernel table)'})

    def on_post_base_fetch(self, request, response, name):
        row = next((b for b in SEED_ISO_BASES if b['name'] == name), None)
        if row is None:
            return self._json(response, {'ok': False, 'refusal': f'no base named {name}'}, '404 Not Found')
        job = iso_builder.fetch_base(row)
        self._json(response, {'ok': True, 'name': name, 'state': job['state'], 'step': job['step'], 'progress': job.get('progress', 0)}, '202 Accepted')

    def _choices(self, body):
        b = {k: body.get(k) for k in ('base', 'role', 'shape', 'encryption', 'secure_boot', 'posture', 'look', 'hostname', 'username', 'ssh_keys', 'join_core', 'join_fingerprint', 'join_tier', 'target_hash', 'apps', 'offline', 'password_hash', 'encryption_passphrase', 'report_to')}
        b['base'] = b.get('base') or (self._default_base() or {}).get('name', ''); b['role'] = b.get('role') or 'member'; b['shape'] = b.get('shape') or 'detect'
        b['encryption'] = bool(b.get('encryption')); b['secure_boot'] = b.get('secure_boot') or 'on'; b['posture'] = b.get('posture') or 'production'; b['look'] = b.get('look') or 'plasma-default'
        b['offline'] = True if b.get('offline') is None else bool(b['offline'])
        probs = []
        if b['role'] not in ROLES: probs.append(f'role must be one of {ROLES}')
        if b['shape'] not in SHAPES: probs.append(f'shape must be one of {SHAPES}')
        if b['posture'] not in POSTURES: probs.append(f'posture must be one of {POSTURES}')
        if b['look'] not in LOOKS: probs.append(f'look must be one of {LOOKS}')
        if b['secure_boot'] not in ('on', 'off'): probs.append('secure_boot must be on or off')
        return b, probs

    def on_get_preview(self, request, response):
        b, probs = self._choices({k: request.params.get(k) for k in request.params})
        if probs:
            return self._json(response, {'ok': False, 'refusal': '; '.join(probs)}, '400 Bad Request')
        refusal, warnings = iso_autoinstall.validate(b)
        self._json(response, {'ok': not refusal, 'refusal': refusal, 'warnings': warnings, 'choices': b, 'autoinstall': iso_autoinstall.render(b, ssh_keys=[k for k in (b.get('ssh_keys') or '').splitlines() if k.strip()])}, '200 OK' if not refusal else '409 Conflict')

    def on_post_build(self, request, response):
        try:
            body = request.media or {}
        except Exception:
            body = {}
        b, probs = self._choices(body)
        if probs:
            return self._json(response, {'ok': False, 'refusal': '; '.join(probs)}, '400 Bad Request')
        # where first boot reports back (his ask: the core sees every device it built): this core's own address unless told
        # behind the proxy the backend sees http; the person and the machine reach us over https — take the forwarded scheme
        # (the first VM install reported to http:// — the proxy had not set X-Forwarded-Proto and falcon's scheme is what the
        #  backend socket saw; a POST to http gets redirected and lost. Everything but a loopback core is served over https.)
        host = getattr(request, 'host', '') or ''
        scheme = request.get_header('X-Forwarded-Proto') if hasattr(request, 'get_header') else None
        scheme = scheme or ('http' if host.split(':')[0] in ('127.0.0.1', 'localhost', '::1') else 'https')
        b['report_to'] = b.get('report_to') or os.environ.get('POLARI_PUBLIC_API', '') or (f"{scheme}://{request.host}" if getattr(request, 'host', '') else '')
        refusal, warnings = iso_autoinstall.validate(b)
        if refusal:
            return self._json(response, {'ok': False, 'refusal': refusal, 'warnings': warnings}, '409 Conflict')
        base = next((x for x in self._bases() if x['name'] == b['base']), None)
        if not base or not base.get('cached'):
            return self._json(response, {'ok': False, 'refusal': f"base {b['base']} is not cached on this instance — POST /api/iso/bases/{b['base']}/fetch first (a 2–3 GB download)", 'base': base}, '409 Conflict')
        bid = iso_builder.build_id(b, core_public_key())   # the core key is part of the identity: a new key means a new image
        row = {**{k: v for k, v in b.items() if k not in ('password_hash', 'encryption_passphrase', 'report_to')}, 'name': bid, 'state': 'requested', 'warnings': ' | '.join(warnings), 'requested_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'ssh_keys': b.get('ssh_keys') or '', 'apps': b.get('apps') or ''}
        self._upsert('IsoBuild', IsoBuild, row); self._persist()
        keys = [k for k in (b.get('ssh_keys') or '').splitlines() if k.strip()]
        job = iso_builder.start_build(b, iso_builder.base_path(base['file']), _platform_debs(), _app_debs(b.get('apps')), keys, core_public_key())
        self._json(response, {'ok': True, 'build': bid, 'state': job['state'], 'step': job['step'], 'warnings': warnings, 'status_url': f'/api/iso/builds/{bid}/status', 'download_url': f'/api/iso/builds/{bid}/download'}, '202 Accepted')

    def on_get_core_key(self, request, response):
        k = core_public_key()
        self._json(response, {'ok': bool(k), 'core_public_key': k, 'placed_on_every_image': bool(k),
                              'how': 'pol iso keys init generates the pair on the core (untracked) and stages the public half for the instance'})

    def on_post_joined(self, request, response):
        """First boot on an installed machine reports back: {hw_hash, hostname, addresses, role, shape, detected}.
        The DeviceProbe row (or a new one) turns 'joined'; the core keeps what it needs to ssh in."""
        try:
            body = request.media or {}
        except Exception:
            body = {}
        h = body.get('hw_hash') or ''; host = body.get('hostname') or ''
        if not (h or host):
            return self._json(response, {'ok': False, 'refusal': 'body: {hw_hash, hostname, addresses: [...], role, shape, detected: {...}}'}, '400 Bad Request')
        row = next((r for r in self._rows('DeviceProbe') if getattr(r, 'hw_hash', '') == h), None) if h else None
        addrs = [a for a in (body.get('addresses') or []) if a]
        fields = {'joined_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'joined_hostname': host, 'joined_addresses': ', '.join(addrs), 'joined_role': body.get('role') or '',
                  'joined_shape': body.get('shape') or '', 'detected': json.dumps(body.get('detected') or {})[:2000], 'ssh_user': body.get('ssh_user') or 'polari'}
        if row is None:
            row = self._upsert('DeviceProbe', DeviceProbe, {'name': 'probe:' + (h or host), 'hw_hash': h or host, 'label': host, 'verdict': 'installed', 'verdict_text': 'reported by first boot (no probe before the install)'})
        if row is not None:
            for k, v in fields.items():
                setattr(row, k, v)
            self._persist()
        self._json(response, {'ok': True, 'device': h or host, 'ssh': f"ssh {fields['ssh_user']}@{addrs[0] if addrs else host}", 'recorded': list(fields)})

    def on_get_builds(self, request, response):
        self._json(response, {'ok': True, 'count': len(self._rows('IsoBuild')), 'builds': self._build_rows(), 'pool': iso_builder.pool_status()})

    def on_get_build_status(self, request, response, build_id):
        d = next((d for d in self._build_rows() if d['name'] == build_id), None)
        if d is None:
            return self._json(response, {'ok': False, 'refusal': f'no build {build_id}'}, '404 Not Found')
        self._json(response, {'ok': True, **d, 'download_url': f'/api/iso/builds/{build_id}/download' if d.get('file') else ''})

    def on_get_build_download(self, request, response, build_id):
        d = next((d for d in self._build_rows() if d['name'] == build_id), None)
        if d is None or not d.get('file') or not os.path.isfile(os.path.join(iso_builder.pool_dir(), d['file'])):
            st = '404 Not Found' if d is None else ('202 Accepted' if d and d.get('state') == 'running' else '409 Conflict')
            return self._json(response, {'ok': False, 'refusal': 'no such build' if d is None else f"not ready: {d.get('state')} — {d.get('step') or d.get('refusal')}"}, st)
        path = os.path.join(iso_builder.pool_dir(), d['file'])
        response.content_type = 'application/x-iso9660-image'; response.downloadable_as = d['file']
        response.set_header('X-Polari-Sha256', d.get('sha256') or ''); response.set_header('Content-Length', str(os.path.getsize(path)))
        response.stream = _Stream(path, d['file'], os.path.getsize(path))

    # ---- the human page -----------------------------------------------------------------------------------------
    def on_get_page(self, request, response):
        response.content_type = 'text/html; charset=utf-8'
        response.text = render_page(self)


def render_page(api):
    from appstore.custom.downloads_shared import wrap_page
    esc = html.escape
    bases = api._bases(); probes = api._probe_rows(); builds = api._build_rows(); tools = iso_builder.tools()
    base_rows = ''.join(f"<li><strong>Ubuntu {esc(b['release'])}</strong> ({esc(b['arch'])}) — {'cached, ' + str(b['bytes'] >> 20) + ' MB' if b['cached'] else 'not cached yet'}"
                        f"{'; kernel table ready' if b.get('kernel_table') else '; kernel table not fetched'}"
                        + (f" — <em>{esc(b['job']['step'])} {b['job'].get('progress', 0)}%</em>" if b.get('job') and b['job']['state'] == 'running' else '') + '</li>' for b in bases)
    probe_rows = ''.join(
        f"<li class=\"dl-card\"><span class=\"dl-info\"><span class=\"dl-name\">{esc(p['label'] or p['hw_hash'])} <code>{esc(p['hw_hash'])}</code></span>"
        f"<p class=\"blurb\">{esc(p['os_name'])} {esc(p['os_version'])} · {esc(p['cpu'])} · {p['memory_gb']:g} GB · firmware {esc(p['firmware'])}, Secure Boot {esc(p['secure_boot'])}, TPM {esc(p['tpm'])}</p>"
        f"<span class=\"prov {'prov-prepped' if p['verdict'] == 'compatible' else 'prov-demand'}\">{esc(p['verdict'])}: {esc(p['verdict_text'])}</span>"
        + (f"<span class=\"dl-meta\">Before installing: {esc(p['traps'])}</span>" if p['traps'] else '')
        + (f"<span class=\"dl-meta\">Suggested role: <strong>{esc(p['suggested_role'])}</strong> — {esc(p['suggested_reason'])}</span>" if p['suggested_role'] else '')
        + '</span></li>' for p in probes)
    build_rows = ''.join(
        f"<li class=\"dl-card\"><span class=\"dl-info\"><span class=\"dl-name\">{esc(p['role'])} · {esc(p['shape'])} · {esc(p['base'])} <code>{esc(p['name'])}</code></span>"
        f"<span class=\"dl-meta\">posture {esc(p['posture'])}, look {esc(p['look'])}, encryption {'on' if p['encryption'] else 'off'}, Secure Boot {esc(p['secure_boot'])}{', for device ' + esc(p['target_hash']) if p['target_hash'] else ''}</span>"
        f"<span class=\"prov {'prov-prepped' if p['state'] == 'ready' else 'prov-demand'}\">{esc(p['state'])}{': ' + esc(p['step']) if p['state'] == 'running' else ''}{': ' + esc(p['refusal']) if p['refusal'] else ''}</span>"
        + (f"<span class=\"dl-meta\">{esc(p['warnings'])}</span>" if p.get('warnings') else '') + '</span>'
        + (f"<a class=\"dl\" href=\"{p['download_url']}\" download>Download ISO ({int(p['bytes']) >> 20} MB)</a>" if p.get('file') else '') + '</li>' for p in builds)
    role_opts = ''.join(f'<option value="{r}">{r}</option>' for r in ROLES)
    shape_opts = ''.join(f'<option value="{s}">{s}</option>' for s in SHAPES)
    look_opts = ''.join(f'<option value="{l}">{l}</option>' for l in LOOKS)
    base_opts = ''.join(f"<option value=\"{esc(b['name'])}\"{' selected' if b.get('default') else ''}{'' if b['cached'] else ' disabled'}>Ubuntu {esc(b['release'])}{'' if b['cached'] else ' (not cached)'}</option>" for b in bases)
    body = f'''
<header class="hero"><h1>Get Polari and Ubuntu onto a new computer</h1>
<p class="lede">Three steps: probe the computer from a USB stick, choose what it should become, install from the same stick. Every choice is made here; nothing is asked on the machine.</p></header>

<section class="step"><h2>1 · Probe the computer</h2>
<p>Download the probe kit, copy it onto a USB stick (a Ventoy stick keeps it alongside the installers), plug the stick into the computer and open <code>README.html</code>. It reads the hardware, changes nothing, and tells you in plain words whether Ubuntu will run there. Then plug the stick into any computer with Polari, which reads the report.</p>
<p><a class="dl" href="/api/iso/probe-kit" download>Download the probe kit</a> <span class="dl-meta">README.html + the Windows, Mac and Linux launchers</span></p>
<p class="note">Scripts and AIs: <code>POST /api/iso/probe</code> with the report JSON.</p>
<h3>Probed computers ({len(probes)})</h3>
{('<ol class="dl-list">' + probe_rows + '</ol>') if probes else '<p class="option-note">No computer has been probed yet.</p>'}
</section>

<section class="step"><h2>2 · Choose what it becomes</h2>
<p>A role, a shape, and the options with their warnings. Secure Boot stays on unless you turn it off on purpose; disk encryption is off unless you turn it on, and is refused on a headless machine. Development posture shows its warning everywhere.</p>
<form class="finder" method="post" action="/api/iso/build" enctype="application/x-www-form-urlencoded">
  <label>base <select name="base">{base_opts}</select></label>
  <label>role <select name="role">{role_opts}</select></label>
  <label>shape <select name="shape">{shape_opts}</select></label>
  <label>look <select name="look">{look_opts}</select></label>
  <label>posture <select name="posture"><option value="production">production</option><option value="dev">dev (warning)</option></select></label>
  <label>Secure Boot <select name="secure_boot"><option value="on">on</option><option value="off">off (warning)</option></select></label>
  <label><input type="checkbox" name="encryption" value="1"> disk encryption (warning)</label>
  <label>hostname <input name="hostname" placeholder="polari-member"></label>
  <label>for device <input name="target_hash" placeholder="hash from a probe"></label>
  <label>join: core address <input name="join_core" placeholder="apt.isle or the core IP"></label>
  <label>join: CA fingerprint <input name="join_fingerprint" placeholder="from the core's core-install printout"></label>
  <label>your ssh public key <input name="ssh_keys" placeholder="ssh-ed25519 AAAA… you@laptop"></label>
  <button type="submit">Build the image</button>
</form>
<p class="note">Bases on this instance: <ul>{base_rows}</ul> A base is a 2–3 GB Ubuntu download cached once (<code>POST /api/iso/bases/&lt;name&gt;/fetch</code>). Tools here: {', '.join(k for k, v in tools.items() if v) or 'none — the overlay is laid, assembly happens elsewhere'}.</p>
</section>

<section class="step"><h2>3 · Install from the stick</h2>
<p>Copy the built image onto the Ventoy stick (a plain file copy), boot the computer from the stick, and leave it: the install is unattended, Polari installs from the image itself with no internet, and on first boot the machine becomes what you chose and joins your isle.</p>
<h3>Images ({len(builds)})</h3>
{('<ol class="dl-list">' + build_rows + '</ol>') if builds else '<p class="option-note">No image built yet.</p>'}
<p class="note">Images are held at least three slow downloads long, evicted only when room is needed, and freed after a day untouched. <a href="/downloads">&larr; Install Polari on an existing Ubuntu</a> · <a href="/downloads/apps">Apps &rarr;</a></p>
</section>
'''
    return wrap_page('Polari', body, 'New computer')
