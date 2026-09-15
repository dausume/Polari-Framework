"""
@module appstore.custom.app_deb_builder

dl-4: the ON-REQUEST app-deb generator. Any module in the live
registry (modules/polari-modules.json) becomes an installable
`polari-app-<module>_<version>_all.deb` — generated at the moment
someone asks for it, streamed to them, and removed from the server
after a retry window (a deb is a DUPLICATE of content the instance
already holds, so it must not occupy disk unless someone currently
wants it — Dustin 2026-08-24).

Design points (DOWNLOADS_PAGE_PLAN.md §dl-4, all ratified):
- PURE-PYTHON deb writer (ar + tar.gz via tarfile) — containers
  don't carry dpkg-deb. Output is byte-deterministic (zeroed
  mtimes/owners, sorted entries), so identical content always
  yields the identical file — the version embeds the content hash
  and IS the cache key.
- Payload installs to /var/lib/polari/apps/<module>/: the module's
  code+data tree snapshot plus a manifest.json. STAGING ONLY — the
  payload goes LIVE through the dynamic-modules admit machinery
  (dev-dyn-1, its own merge gate); nothing here pretends otherwise
  and the manifest says so.
- SHARED-PAYLOAD FACTORING: identical files (by content hash, above
  a size floor) appearing in ≥2 registry modules are factored into
  generated `polari-app-shared-<key>` debs owning the real bytes
  under /var/lib/polari/apps/_shared/; the app debs carry symlinks
  and a dpkg `Depends:` on the shared deb — shared content installs
  ONCE, dpkg-enforced. Groups are keyed by the exact set of sharing
  modules, so on-demand generation of any single module is
  deterministic (the analysis always runs over the full registry).
- NAMED REFUSALS, never silent: unknown module, registered-but-not-
  downloaded code, and deb-name collisions (two module names
  mapping to one Debian package name) all refuse with a sentence.
- Every real generation appends a DebGenerationRecord row
  {module, contentHash, bytes, seconds, steps, generatedAt} to a
  JSONL ledger; the page quotes the median of recent runs as the
  honest wait estimate ("never generated yet" before any exist).
- TTL pool: POLARI_APP_DEB_TTL seconds (default 3600) so a flaky
  download can retry without regenerating; expired files are purged
  opportunistically on every request. POLARI_APP_DEB_PREBUILD=1
  lets a deployment pre-generate the whole registry (instant
  downloads at the cost of disk — the explicit knob, off by
  default).

@consumers
  - appstore.app_debs_page (/downloads/apps)
  - appstore.app_debs_selftest
  - isle CLI `isle apps build-debs` (thin verb over this module)
"""

import gzip
import hashlib
import io
import json
import shutil
import os
import re
import statistics
import subprocess
import tarfile
import threading
import time

from moduleService import module_registry

from appstore.custom import module_requirements as modreqs

BASE_VERSION = '0.1.0'
_DEB_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9+.-]+$')
_EXCLUDED_DIRS = {'__pycache__', '.git', 'node_modules'}
_EXCLUDED_SUFFIXES = ('.pyc', '.pyo')

#: Files smaller than this never factor into shared debs — a
#: symlink + dependency edge costs more than it saves.
SHARED_MIN_BYTES = 4096

INSTALL_ROOT = 'var/lib/polari/apps'


def work_dir():
    configured = os.environ.get('POLARI_APP_DEBS_DIR', '')
    if configured:
        return configured
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    return os.path.join(root, 'data', 'app-debs')


def pool_dir():
    return os.path.join(work_dir(), 'pool')


def ledger_path():
    return os.path.join(work_dir(), 'generation-ledger.jsonl')


def ttl_seconds():
    """Only the delete-after-delivery switch survives from the old TTL: POLARI_APP_DEB_TTL=0 removes a deb right after
    it is handed over; anything else means the pool policy (holds, room, idle) governs — no TTL deletion."""
    try:
        return int(os.environ.get('POLARI_APP_DEB_TTL', '1'))
    except ValueError:
        return 1


def deb_package_name(module):
    """Debian package name for a module; '' when the module name
    cannot map to one (caller renders the named refusal)."""
    name = 'polari-app-' + module.lower().replace('_', '-')
    return name if _DEB_NAME_RE.match(name) else ''


def registry_modules(root=None):
    """{module: entry} for every registry module, downloaded or not
    — the page lists the REGISTRY, never files on disk."""
    return module_registry.load_registry(root)['modules']


# --- payload walk + overlap analysis --------------------------------

def _walk_payload(module_dir):
    """Sorted [(relpath, abspath, size)] of one module's tree."""
    files = []
    for dirpath, dirnames, filenames in os.walk(module_dir):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in _EXCLUDED_DIRS)
        for fname in sorted(filenames):
            if fname.endswith(_EXCLUDED_SUFFIXES):
                continue
            abspath = os.path.join(dirpath, fname)
            rel = os.path.relpath(abspath, module_dir)
            files.append((rel, abspath, os.path.getsize(abspath)))
    return files


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b''):
            digest.update(chunk)
    return digest.hexdigest()


_ANALYZE_CACHE = {}
ANALYZE_TTL = 300   # the page must not re-hash every module's payload on every request (59 modules ≈ 25–70 s)


def analyze_cache_clear():
    _ANALYZE_CACHE.clear()


def analyze(root=None, fresh=False):
    """Memoised for ANALYZE_TTL seconds per root (the pages call it on every request); `fresh=True` re-walks."""
    froot = root or module_registry._framework_root()
    try:   # the registry file changing (a fetch, an admit, a test's rewrite) invalidates at once; otherwise the TTL
        st = os.stat(module_registry.registry_path(froot)); fp = (st.st_mtime_ns, st.st_size)
    except Exception:
        fp = None
    hit = _ANALYZE_CACHE.get(froot)
    if hit and not fresh and hit[2] == fp and time.time() - hit[0] < ANALYZE_TTL:
        return hit[1]
    result = _analyze(froot)
    _ANALYZE_CACHE[froot] = (time.time(), result, fp)
    return result


def _analyze(root=None):
    """One pass over the full registry: per-module payloads, the
    shared groups, and every named refusal.

    Returns {payloads: {module: [(rel, abspath, size, sha)]},
             shared: {debname: {'modules': [...],
                                'files': [(sharedrel, abspath, sha)],
                                'version': str}},
             sharedByModule: {module: [debname]},
             sharedTargets: {module: {rel: sharedrel}},
             refusals: {module: reason}}
    """
    froot = root or module_registry._framework_root()
    modules = registry_modules(froot)
    payloads, refusals = {}, {}
    seen_debnames = {}
    for module, entry in sorted(modules.items()):
        debname = deb_package_name(module)
        if not debname:
            refusals[module] = (f'module name "{module}" cannot map '
                                'to a Debian package name')
            continue
        if debname in seen_debnames:
            other = seen_debnames[debname]
            reason = (f'modules "{other}" and "{module}" both map '
                      f'to package "{debname}" — rename one')
            refusals[module] = reason
            refusals[other] = reason
            payloads.pop(other, None)
            continue
        seen_debnames[debname] = module
        # the module's code: in the tree (the register's path) or fetched onto the data volume at runtime
        # (POLARI_FETCHED_MODULES_DIR) — the shared resolver knows both roots
        from moduleService.module_loading import module_code_dir
        module_dir = module_code_dir(module, froot) or os.path.join(
            froot, entry.get('path', f'modules/{module}'))
        if not os.path.isdir(module_dir):
            refusals[module] = ('registered but its code is not '
                                'downloaded on this instance')
            continue
        payloads[module] = [(rel, abspath, size,
                             _sha256_file(abspath))
                            for rel, abspath, size
                            in _walk_payload(module_dir)]

    # content shared by >=2 modules, above the size floor
    by_content = {}
    for module, files in payloads.items():
        for rel, abspath, size, sha in files:
            if size < SHARED_MIN_BYTES:
                continue
            by_content.setdefault(sha, []).append(
                (module, rel, abspath))
    groups = {}
    for sha, owners in sorted(by_content.items()):
        modules_sharing = sorted({m for m, _, _ in owners})
        if len(modules_sharing) < 2:
            continue
        groups.setdefault(tuple(modules_sharing), []).append(
            (sha, owners[0][2]))
    shared, shared_by_module, shared_targets = {}, {}, {}
    for module_set, contents in sorted(groups.items()):
        key = hashlib.sha256(
            ','.join(module_set).encode()).hexdigest()[:8]
        debname = f'polari-app-shared-{key}'
        files = []
        for sha, abspath in sorted(contents):
            sharedrel = f'{sha[:12]}__{os.path.basename(abspath)}'
            files.append((sharedrel, abspath, sha))
        version_hash = hashlib.sha256(
            ''.join(sha for _, _, sha in files).encode()
        ).hexdigest()[:10]
        shared[debname] = {'modules': list(module_set),
                           'files': files,
                           'version': f'{BASE_VERSION}+g'
                                      f'{version_hash}'}
        for module in module_set:
            shared_by_module.setdefault(module, []).append(debname)
    # per-module: which payload rel goes to which shared file
    sha_to_shared = {sha: sharedrel
                     for group in shared.values()
                     for sharedrel, _, sha in group['files']}
    for module, files in payloads.items():
        targets = {rel: sha_to_shared[sha]
                   for rel, _, _, sha in files
                   if sha in sha_to_shared}
        if targets:
            shared_targets[module] = targets
    return {'payloads': payloads, 'shared': shared,
            'sharedByModule': shared_by_module,
            'sharedTargets': shared_targets, 'refusals': refusals}


# --- the pure-python deb writer -------------------------------------

def _ar_member(name, data):
    header = (f'{name:<16}{0:<12}{0:<6}{0:<6}{"100644":<8}'
              f'{len(data):<10}`\n').encode('ascii')
    return header + data + (b'\n' if len(data) % 2 else b'')


def _tar_gz(entries):
    """Deterministic tar.gz. entries = [(arcname, kind, payload)]
    where kind='file' (payload=bytes), 'dir' (None), or
    'symlink' (target str). Parent dirs must be listed first."""
    raw = io.BytesIO()
    tar = tarfile.open(fileobj=raw, mode='w',
                       format=tarfile.GNU_FORMAT)
    for arcname, kind, payload in entries:
        info = tarfile.TarInfo(arcname)
        info.mtime = 0
        info.uid = info.gid = 0
        info.uname = info.gname = 'root'
        if kind == 'dir':
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            tar.addfile(info)
        elif kind == 'symlink':
            info.type = tarfile.SYMTYPE
            info.linkname = payload
            info.mode = 0o777
            tar.addfile(info)
        else:
            info.mode = 0o755 if kind == 'exec' else 0o644
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    tar.close()
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb', mtime=0,
                       compresslevel=9) as gz:
        gz.write(raw.getvalue())
    return buffer.getvalue()


def _write_deb(path, control_fields, data_entries, scripts=None):
    """scripts = {'preinst': text, 'postinst': text, ...} — maintainer scripts (mode 0755) in the control tar;
    the install-time refusals (his rulings 2026-09-14) and the access apps' first-run binding live there."""
    control = ''.join(f'{k}: {v}\n' for k, v in control_fields
                      if v).encode()
    members = [('./', 'dir', None), ('./control', 'file', control)]
    for name, text in sorted((scripts or {}).items()):
        if text:
            members.append((f'./{name}', 'exec', text.encode()))
    control_tar = _tar_gz(members)
    data_tar = _tar_gz(data_entries)
    with open(path, 'wb') as fh:
        fh.write(b'!<arch>\n')
        fh.write(_ar_member('debian-binary', b'2.0\n'))
        fh.write(_ar_member('control.tar.gz', control_tar))
        fh.write(_ar_member('data.tar.gz', data_tar))
    return os.path.getsize(path)


def _dir_chain(seen, arcname):
    """Emit not-yet-seen parent dir entries for ./x/y/z paths."""
    entries = []
    parts = arcname.strip('./').split('/')[:-1]
    for i in range(len(parts)):
        d = './' + '/'.join(parts[:i + 1]) + '/'
        if d not in seen:
            seen.add(d)
            entries.append((d, 'dir', None))
    return entries


# --- generation -----------------------------------------------------

def _content_hash(files, shared_targets):
    digest = hashlib.sha256()
    for rel, _, _, sha in files:
        digest.update(f'{rel}:{sha}:'
                      f'{shared_targets.get(rel, "")}'.encode())
    return digest.hexdigest()


def build_shared_deb(debname, group, pool):
    filename = f'{debname}_{group["version"]}_all.deb'
    path = os.path.join(pool, filename)
    if os.path.isfile(path):
        return filename
    seen = set()
    entries = [('./', 'dir', None)]
    root = f'./{INSTALL_ROOT}/_shared'
    for sharedrel, abspath, _ in group['files']:
        arcname = f'{root}/{sharedrel}'
        entries.extend(_dir_chain(seen, arcname))
        with open(abspath, 'rb') as fh:
            entries.append((arcname, 'file', fh.read()))
    total = sum(os.path.getsize(a) for _, a, _ in group['files'])
    _write_deb(path, [
        ('Package', debname),
        ('Version', group['version']),
        ('Architecture', 'all'),
        ('Maintainer', 'Polari Suite <downloads@polari>'),
        ('Installed-Size', str(max(1, total // 1024))),
        ('Section', 'misc'),
        ('Priority', 'optional'),
        ('Description',
         'Polari shared app payload — files used by modules: '
         + ', '.join(group['modules'])),
    ], entries)
    return filename


def _fetch_wheels(libraries, dest):
    """Download wheels for the OFFLINE flavor: installed libraries
    pinned to their measured versions, unmeasured ones by name.
    Returns sorted wheel filenames; raises RuntimeError with pip's
    words on failure (caller renders the named refusal). Module-
    level seam so selftests can substitute a fake fetcher."""
    specs = [f'{l["name"]}=={l["version"]}' if l['installed']
             else l['name'] for l in libraries]
    if not specs:
        return []
    os.makedirs(dest, exist_ok=True)
    result = subprocess.run(
        ['python3', '-m', 'pip', 'download', '--no-deps',
         '-d', dest] + specs,
        capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            'wheel download failed: '
            + (result.stderr or result.stdout).strip()[-400:])
    return sorted(os.listdir(dest))


def generate(module, root=None, analysis=None, flavor='online',
             progress=None, form='install'):
    """Generate module's deb (+ any shared debs it depends on) into
    the pool. flavor='online' (default): the small deb — libraries
    + engines install DYNAMICALLY after download, and the manifest
    says exactly what and how big. flavor='offline': the deb
    CARRIES the pip-library wheels under wheels/ for no-internet
    installs (package name gains -offline + Provides/Conflicts/
    Replaces the online name so the two can never coexist); system
    engines can never ride a wheel — the manifest names them as
    coming from the distro/offline media instead. Returns
    {'ok': True, file, path, version, bytes, seconds, cached,
    sharedFiles: [...]} or {'ok': False, 'refusal': sentence} —
    named refusals, never exceptions, for bad input."""
    started = time.time()
    steps = []
    progress = progress or (lambda name: None)

    def step(name, t0):
        steps.append({'step': name,
                      'seconds': round(time.time() - t0, 3)})

    progress('analyzing payload, shared overlap + requirements')

    if flavor not in ('online', 'offline'):
        return {'ok': False,
                'refusal': f'unknown flavor "{flavor}" — online '
                           '(deps install after download) or '
                           'offline (deps ride inside)'}
    if form not in ('install', 'access'):
        return {'ok': False, 'refusal': f'unknown form "{form}" — install (the app itself) or access (its shell)'}
    if form == 'access':
        return generate_access(module, root, flavor, progress, started)
    t0 = time.time()
    analysis = analysis or analyze(root)
    if module in analysis['refusals']:
        return {'ok': False,
                'refusal': f'{module}: '
                           f'{analysis["refusals"][module]}'}
    if module not in analysis['payloads']:
        return {'ok': False,
                'refusal': f'"{module}" is not in the module '
                           'registry — see /downloads/apps for '
                           'what this instance offers'}
    files = analysis['payloads'][module]
    shared_targets = analysis['sharedTargets'].get(module, {})
    shared_names = analysis['sharedByModule'].get(module, [])
    requirements = modreqs.module_requirements(module, root)
    step('analyze payload + shared overlap + requirements', t0)

    wheels = []
    if flavor == 'offline':
        progress('fetching dependency wheels')
        t0 = time.time()
        wheel_dir = os.path.join(work_dir(), 'wheels', module)
        fresh = (os.path.isdir(wheel_dir) and os.listdir(wheel_dir)
                 and time.time() - os.path.getmtime(wheel_dir)
                 < IDLE_SECONDS)
        try:
            names = (sorted(os.listdir(wheel_dir)) if fresh
                     else _fetch_wheels(requirements['libraries'],
                                        wheel_dir))
        except RuntimeError as error:
            return {'ok': False, 'refusal': f'{module}: {error}'}
        wheels = [(name, os.path.join(wheel_dir, name),
                   os.path.getsize(os.path.join(wheel_dir, name)))
                  for name in names]
        step('fetch dependency wheels'
             + (' (cached)' if fresh else ''), t0)

    content_hash = hashlib.sha256(
        (_content_hash(files, shared_targets) + flavor
         + ''.join(f'{n}:{s}' for n, _, s in wheels)).encode()
    ).hexdigest()

    debname = deb_package_name(module) + (
        '-offline' if flavor == 'offline' else '')
    version = f'{BASE_VERSION}+g{content_hash[:10]}'
    filename = f'{debname}_{version}_all.deb'
    pool = pool_dir()
    os.makedirs(pool, exist_ok=True)
    path = os.path.join(pool, filename)
    shared_files = [
        build_shared_deb(name, analysis['shared'][name], pool)
        for name in shared_names]
    if os.path.isfile(path):
        # cache hit — same content, same file; the re-request refreshes its hold
        note_request(filename, os.path.getsize(path), f'{module}|install|{flavor}')
        return {'ok': True, 'file': filename, 'path': path,
                'version': version, 'bytes': os.path.getsize(path),
                'seconds': round(time.time() - started, 3),
                'cached': True, 'sharedFiles': shared_files}

    progress('packaging module files')
    t0 = time.time()
    seen = set()
    entries = [('./', 'dir', None)]
    module_root = f'./{INSTALL_ROOT}/{module}'
    data_files = []
    payload_bytes = 0
    for rel, abspath, size, sha in files:
        arcname = f'{module_root}/{rel}'
        entries.extend(_dir_chain(seen, arcname))
        if rel in shared_targets:
            entries.append((arcname, 'symlink',
                            f'/{INSTALL_ROOT}/_shared/'
                            f'{shared_targets[rel]}'))
        else:
            with open(abspath, 'rb') as fh:
                entries.append((arcname, 'file', fh.read()))
            payload_bytes += size
        if not rel.endswith('.py'):
            data_files.append(rel)
    for name, abspath, size in wheels:
        arcname = f'{module_root}/wheels/{name}'
        entries.extend(_dir_chain(seen, arcname))
        with open(abspath, 'rb') as fh:
            entries.append((arcname, 'file', fh.read()))
        payload_bytes += size
    step('package module files', t0)

    t0 = time.time()
    entry = registry_modules(root).get(module, {})
    manifest = {
        'module': module,
        'package': debname,
        'version': version,
        'contentHash': content_hash,
        'description': entry.get('description', ''),
        'kind': entry.get('kind', ''),
        'repo': entry.get('repo', ''),
        'licence': 'GPL-3.0-or-later',
        'dataFiles': data_files,
        'sharedDepends': shared_names,
        'flavor': flavor,
        'requirements': {
            **requirements,
            'delivery': ('carried-wheels: pip libraries ride in '
                         'wheels/ — install with pip install '
                         '--no-index --find-links wheels/; '
                         'SYSTEM engines never ride a wheel, '
                         'they come from the distro or the '
                         'offline media closure'
                         if flavor == 'offline' else
                         'dynamic-after-install: libraries + '
                         'engines are fetched from the internet '
                         'when the app is admitted'),
            'wheels': [name for name, _, _ in wheels],
        },
        'admit': ('staged under /var/lib/polari/apps/ — goes live '
                  'through the dynamic-modules admit machinery; '
                  'until that merges, admission is a manual step '
                  'on the instance'),
    }
    manifest_bytes = json.dumps(manifest, indent=2).encode()
    arcname = f'{module_root}/manifest.json'
    entries.extend(_dir_chain(seen, arcname))
    entries.append((arcname, 'file', manifest_bytes))
    step('write manifest', t0)

    t0 = time.time()
    depends = ', '.join(
        f'{name} (= {analysis["shared"][name]["version"]})'
        for name in shared_names)
    description = entry.get('description',
                            f'Polari module {module}')
    progress('assembling the deb')
    online_name = deb_package_name(module)
    # his rulings 2026-09-14: hardware apps / expansions refuse at preinst (lightweight isle, missing base)
    from appstore.custom.app_forms import manifest_app, preinst_for
    scripts = {'preinst': preinst_for(module, manifest_app(module, root, entry))}
    size_bytes = _write_deb(path, [
        ('Package', debname),
        ('Version', version),
        ('Provides', online_name if flavor == 'offline' else ''),
        ('Conflicts', online_name if flavor == 'offline' else ''),
        ('Replaces', online_name if flavor == 'offline' else ''),
        ('Architecture', 'all'),
        ('Maintainer', 'Polari Suite <downloads@polari>'),
        ('Installed-Size',
         str(max(1, (payload_bytes + len(manifest_bytes)) // 1024))),
        ('Depends', depends),
        ('Section', 'misc'),
        ('Priority', 'optional'),
        ('Description', f'Polari app — {description}'),
    ], entries, scripts)
    step('assemble deb', t0)

    seconds = round(time.time() - started, 3)
    note_request(filename, size_bytes, f'{module}|install|{flavor}')
    _append_record({'module': module, 'flavor': flavor,
                    'contentHash': content_hash,
                    'bytes': size_bytes, 'seconds': seconds,
                    'steps': steps,
                    'generatedAt': int(started)})
    return {'ok': True, 'file': filename, 'path': path,
            'version': version, 'bytes': size_bytes,
            'seconds': seconds, 'cached': False,
            'sharedFiles': shared_files}


def staged_shell_core_deb():
    """The polari-shell-core deb staged with the platform installers (POLARI_DOWNLOADS_DIR), or None — the
    offline access flavour carries it so a computer with no internet still gets the shell runtime."""
    try:
        from appstore.downloads_page import downloads_dir
        d = downloads_dir()
        for entry in sorted(os.listdir(d)):
            if entry.startswith('polari-shell-core_') and entry.endswith('.deb'):
                return os.path.join(d, entry)
    except Exception:
        pass
    return None


def generate_access(module, root=None, flavor='online', progress=None, started=None):
    """The ACCESS form (his rulings 2026-09-14): the app's shell — a launcher that finds and opens the app the isle
    hosts. Exists for every app kind, online and offline (offline carries the shell runtime deb when staged)."""
    from appstore.custom.app_forms import access_deb_name, access_entries, manifest_app
    started = started or time.time(); steps = []; progress = progress or (lambda name: None)
    entry = registry_modules(root).get(module)
    if entry is None:
        return {'ok': False, 'refusal': f'"{module}" is not in the module registry'}
    debname = access_deb_name(module, flavor)
    if not debname:
        return {'ok': False, 'refusal': f'"{module}" cannot map to a Debian package name'}
    app = manifest_app(module, root, entry)
    shell = staged_shell_core_deb() if flavor == 'offline' else None
    t0 = time.time(); progress('assembling the access deb (the shell)')
    control, entries, scripts, carried = access_entries(module, app, flavor, shell)
    content_hash = hashlib.sha256((json.dumps([list(c) for c in control]) + ''.join(e[0] for e in entries) + (os.path.basename(shell) if shell else '')).encode()).hexdigest()
    version = f'{BASE_VERSION}+g{content_hash[:10]}'
    filename = f'{debname}_{version}_all.deb'
    pool = pool_dir(); os.makedirs(pool, exist_ok=True); path = os.path.join(pool, filename)
    if os.path.isfile(path):
        note_request(filename, os.path.getsize(path), f'{module}|access|{flavor}')
        return {'ok': True, 'file': filename, 'path': path, 'version': version, 'bytes': os.path.getsize(path), 'seconds': round(time.time() - started, 3), 'cached': True, 'sharedFiles': [], 'form': 'access'}
    control.insert(1, ('Version', version))
    size_bytes = _write_deb(path, control, entries, scripts)
    steps.append({'step': 'assemble access deb' + (' (carries polari-shell-core)' if carried else ''), 'seconds': round(time.time() - t0, 3)})
    seconds = round(time.time() - started, 3)
    note_request(filename, size_bytes, f'{module}|access|{flavor}')
    _append_record({'module': module, 'flavor': flavor, 'form': 'access', 'contentHash': content_hash, 'bytes': size_bytes, 'seconds': seconds, 'steps': steps, 'generatedAt': int(started)})
    return {'ok': True, 'file': filename, 'path': path, 'version': version, 'bytes': size_bytes, 'seconds': seconds, 'cached': False, 'sharedFiles': [], 'form': 'access',
            'carries_shell_runtime': bool(carried), 'shell_runtime_note': '' if (flavor == 'online' or carried) else 'the core staged no polari-shell-core deb — the offline access deb carries only the launcher'}


# --- the DebGenerationRecord ledger ---------------------------------

def _append_record(record):
    os.makedirs(work_dir(), exist_ok=True)
    with open(ledger_path(), 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(record) + '\n')


def generation_records(module=None):
    records = []
    try:
        with open(ledger_path(), encoding='utf-8') as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if module is None or row.get('module') == module:
                    records.append(row)
    except FileNotFoundError:
        pass
    return records


def record_download(filename, size_bytes, seconds):
    """dl-9: DOWNLOAD times are measured too — a row per completed
    transfer, so the page can predict from history instead of
    guessing bandwidth."""
    _append_record({'kind': 'download', 'file': filename,
                    'bytes': size_bytes,
                    'seconds': round(seconds, 3),
                    'generatedAt': int(time.time())})


def download_estimate_seconds(size_bytes, recent=10):
    """Predicted transfer time for size_bytes from the median
    measured throughput, or None — no prior data means SAY no
    prior data, never invent a speed."""
    rates = [row['bytes'] / row['seconds']
             for row in generation_records()
             if row.get('kind') == 'download'
             and row.get('seconds') and row.get('bytes')]
    if not rates or not size_bytes:
        return None
    return round(size_bytes / statistics.median(rates[-recent:]),
                 1)


def pool_file_for(module, flavor='online', form='install'):
    """The unexpired pool deb for module+flavor(+form), or None —
    {'file', 'bytes', 'ageSeconds'}. Drives the button honesty:
    an already-generated app offers Download, not Generate."""
    if form == 'access':
        from appstore.custom.app_forms import access_deb_name
        debname = access_deb_name(module, flavor)
    else:
        debname = deb_package_name(module) + (
            '-offline' if flavor == 'offline' else '')
    try:
        for entry in sorted(os.listdir(pool_dir())):
            if entry.startswith(debname + '_'):
                path = os.path.join(pool_dir(), entry)
                return {'file': entry,
                        'bytes': os.path.getsize(path),
                        'ageSeconds': int(time.time()
                                          - os.path.getmtime(path))}
    except FileNotFoundError:
        pass
    return None


def estimate_seconds(module, recent=10, flavor='online', form='install'):
    """Median of the module's recent generation times for ONE
    flavor (offline runs fetch wheels — a different animal), or
    None — the page renders None as the honest 'never generated
    yet'. Legacy rows without a flavor count as online."""
    times = [row['seconds'] for row in generation_records(module)
             if isinstance(row.get('seconds'), (int, float))
             and row.get('flavor', 'online') == flavor
             and row.get('form', 'install') == form]
    return (round(statistics.median(times[-recent:]), 1)
            if times else None)


# --- background generation jobs (dl-8: the click must confirm,
# show progress, and hand the file over when ready) -------------------

_jobs = {}


def generation_job(module, flavor, form='install'):
    return _jobs.get(f'{module}:{flavor}' + (':access' if form == 'access' else ''))


def start_generation(module, flavor='online', root=None, form='install'):
    """Idempotent kick-off: a running job is returned as-is; a
    finished one whose pool file the TTL already purged restarts.
    The job dict is live — 'step' updates as generation moves."""
    key = f'{module}:{flavor}' + (':access' if form == 'access' else '')
    job = _jobs.get(key)
    if job:
        if job['state'] == 'running':
            return job
        if (job['state'] == 'done'
                and os.path.isfile(job['result']['path'])):
            return job
    job = {'module': module, 'flavor': flavor, 'form': form, 'state': 'running',
           'step': 'starting', 'startedAt': time.time(),
           'result': None}
    _jobs[key] = job

    def run():
        try:
            result = generate(
                module, root=root, flavor=flavor, form=form,
                progress=lambda name: job.__setitem__('step',
                                                      name))
            job['result'] = result
            job['state'] = 'done' if result.get('ok') else 'refused'
        except Exception as error:      # noqa: BLE001 — the page
            job['result'] = {'ok': False,   # must never lose a job
                             'refusal': f'unexpected: {error}'}
            job['state'] = 'refused'

    threading.Thread(target=run, daemon=True).start()
    return job


# --- pool lifecycle (his policy 2026-09-14) --------------------------------------------------------------------
# Every deb in the pool remembers WHEN it was requested (a re-request refreshes), how often, and when it was last
# downloaded. Its MINIMUM HOLD is three times the predicted download time over a slow connection (from the size:
# the slower of a knob and the slow quartile of measured downloads), floored at HOLD_FLOOR. After the hold a deb may
# be EVICTED only when room is needed for another requested deb (least recently used first, never one being
# downloaded). The pool is CAPPED (POLARI_APP_POOL_MAX_BYTES, also bounded by free disk minus the margin). A deb
# nobody touched for IDLE_SECONDS goes regardless, so a quiet day frees the space.

HOLD_MULTIPLIER = 3
HOLD_FLOOR = 600            # s — a 40 KB deb still gets ten minutes
IDLE_SECONDS = 86400        # a day untouched → freed
SPACE_MARGIN = 200 * 1024 * 1024
_POOL_LEDGER = {}
_INFLIGHT = {}              # filename → open download streams (never evicted)


def pool_ledger_path():
    return os.path.join(work_dir(), 'pool-ledger.json')


def _ledger():
    if not _POOL_LEDGER:
        try:
            with open(pool_ledger_path(), encoding='utf-8') as fh:
                _POOL_LEDGER.update(json.load(fh))
        except (OSError, ValueError):
            pass
    return _POOL_LEDGER


def _save_ledger():
    os.makedirs(work_dir(), exist_ok=True)
    tmp = pool_ledger_path() + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(_POOL_LEDGER, fh, indent=1)
    os.replace(tmp, pool_ledger_path())


def pool_max_bytes():
    """The cap: the knob (default 2 GiB), never more than free disk minus the margin (measured at the pool)."""
    try:
        cap = int(os.environ.get('POLARI_APP_POOL_MAX_BYTES', str(2 * 1024 ** 3)))
    except ValueError:
        cap = 2 * 1024 ** 3
    probe = pool_dir()
    while probe and not os.path.isdir(probe):
        probe = os.path.dirname(probe.rstrip('/'))
    try:
        free = shutil.disk_usage(probe or '/').free
        return max(0, min(cap, pool_used_bytes() + free - SPACE_MARGIN))
    except Exception:
        return cap


def slow_bps():
    """Bytes per second of a somewhat slow connection: the slower of the knob (default 250 KB/s ≈ 2 Mbit/s) and the
    slow quartile of measured downloads — never a LAN speed masquerading as the internet."""
    try:
        knob = int(os.environ.get('POLARI_SLOW_DOWNLOAD_BPS', '250000'))
    except ValueError:
        knob = 250000
    rates = sorted(row['bytes'] / row['seconds'] for row in generation_records()
                   if row.get('kind') == 'download' and row.get('seconds') and row.get('bytes'))
    if len(rates) >= 4:
        return max(1, min(knob, int(rates[len(rates) // 4])))
    return knob


def hold_seconds(size_bytes):
    return max(HOLD_FLOOR, int(HOLD_MULTIPLIER * (size_bytes or 0) / slow_bps()))


def pool_used_bytes():
    try:
        return sum(os.path.getsize(os.path.join(pool_dir(), f)) for f in os.listdir(pool_dir()) if os.path.isfile(os.path.join(pool_dir(), f)))
    except FileNotFoundError:
        return 0


def note_request(filename, size_bytes=None, key=''):
    """A request (or re-request) refreshes the clock and the hold."""
    now = time.time(); L = _ledger()
    row = L.setdefault(filename, {'first_requested_at': now, 'requests': 0, 'downloads': 0, 'key': key})
    row.update({'requested_at': now, 'last_access': now, 'requests': row.get('requests', 0) + 1, 'key': key or row.get('key', '')})
    if size_bytes:
        row['bytes'] = size_bytes
    row['hold_until'] = now + hold_seconds(row.get('bytes', size_bytes or 0))
    _save_ledger()
    return row


def note_download(filename, seconds=None, size_bytes=None):
    """A completed download counts as access (refreshes the hold too) and is a throughput measurement."""
    now = time.time(); L = _ledger()
    row = L.setdefault(filename, {'first_requested_at': now, 'requests': 0, 'downloads': 0})
    row.update({'last_access': now, 'last_download_at': now, 'downloads': row.get('downloads', 0) + 1})
    if size_bytes:
        row['bytes'] = size_bytes
    row['hold_until'] = max(row.get('hold_until', 0), now + hold_seconds(row.get('bytes', size_bytes or 0)))
    _save_ledger()
    if seconds and size_bytes:
        record_download(filename, size_bytes, seconds)
    return row


def inflight_begin(filename):
    _INFLIGHT[filename] = _INFLIGHT.get(filename, 0) + 1


def inflight_end(filename):
    _INFLIGHT[filename] = max(0, _INFLIGHT.get(filename, 0) - 1)


def pool_entry(filename):
    """What the pool knows about one deb (for the page and the API)."""
    row = dict(_ledger().get(filename) or {})
    now = time.time()
    row['hold_remaining_seconds'] = max(0, int(row.get('hold_until', 0) - now))
    row['in_flight'] = _INFLIGHT.get(filename, 0)
    row['evictable'] = row['hold_remaining_seconds'] == 0 and not row['in_flight']
    return row


def pool_status():
    used = pool_used_bytes(); cap = pool_max_bytes()
    return {'used_bytes': used, 'max_bytes': cap, 'free_bytes': max(0, cap - used), 'files': len([f for f in _pool_files()]),
            'slow_bps': slow_bps(), 'hold_multiplier': HOLD_MULTIPLIER, 'hold_floor_seconds': HOLD_FLOOR, 'idle_seconds': IDLE_SECONDS}


def _pool_files():
    try:
        return [f for f in os.listdir(pool_dir()) if os.path.isfile(os.path.join(pool_dir(), f))]
    except FileNotFoundError:
        return []


def _remove(filename):
    try:
        os.remove(os.path.join(pool_dir(), filename))
    except OSError:
        pass
    _ledger().pop(filename, None)


def make_room(needed_bytes, now=None):
    """Room for a requested deb: evict (least recently accessed first) only debs past their hold and not being
    downloaded, until it fits. {'ok', 'evicted': [...], 'blocked_by': [...], 'note'}."""
    now = now or time.time(); L = _ledger()
    cap = pool_max_bytes(); used = pool_used_bytes(); evicted = []
    if used + needed_bytes <= cap:
        return {'ok': True, 'evicted': [], 'blocked_by': [], 'note': ''}
    candidates = sorted(_pool_files(), key=lambda f: L.get(f, {}).get('last_access', 0))
    blocked = []
    for f in candidates:
        if used + needed_bytes <= cap:
            break
        row = L.get(f, {})
        if _INFLIGHT.get(f) or row.get('hold_until', 0) > now:
            blocked.append({'file': f, 'hold_remaining_seconds': max(0, int(row.get('hold_until', 0) - now)), 'in_flight': _INFLIGHT.get(f, 0)}); continue
        size = os.path.getsize(os.path.join(pool_dir(), f)); _remove(f); evicted.append(f); used -= size
    if evicted:
        _save_ledger()
    ok = used + needed_bytes <= cap
    soonest = min((b['hold_remaining_seconds'] for b in blocked), default=0)
    note = '' if ok else (f'the deb pool is full ({used // (1 << 20)} MB of {cap // (1 << 20)} MB) and every deb in it is inside its minimum hold'
                          + (f' — the earliest hold ends in {soonest // 60} min' if blocked else '') + '; try again then, or raise POLARI_APP_POOL_MAX_BYTES')
    return {'ok': ok, 'evicted': evicted, 'blocked_by': blocked[:10], 'note': note}


def purge_expired(ttl=None):
    """The idle purge: a deb nobody requested or downloaded for IDLE_SECONDS is removed whether or not the pool is
    full (a file the ledger never saw is judged by its mtime). Holds never delete on their own — eviction is
    make_room's job. Returns the names removed. Runs on every page/API request — no background thread to die quietly."""
    idle = IDLE_SECONDS if ttl is None else ttl
    removed = []; now = time.time(); L = _ledger()
    for f in _pool_files():
        if _INFLIGHT.get(f):
            continue
        mtime = os.path.getmtime(os.path.join(pool_dir(), f))
        # an explicit ttl judges by the file's age (the old TTL semantics, used by tests and operators); the policy judges by access
        last = mtime if ttl is not None else (L.get(f, {}).get('last_access') or mtime)
        if now - last > idle:
            _remove(f); removed.append(f)
    for f in [k for k in L if k not in set(_pool_files())]:   # ledger rows for files that are gone
        L.pop(f, None)
    if removed:
        _save_ledger()
    return removed


def prebuild_enabled():
    return os.environ.get('POLARI_APP_DEB_PREBUILD', '') in (
        '1', 'true', 'yes')


def prebuild_all(root=None):
    """The explicit pre-prepped-pool option: generate every
    generatable registry module now. Returns per-module results."""
    analysis = analyze(root)
    return {module: generate(module, root=root, analysis=analysis)
            for module in sorted(analysis['payloads'])}


def resolve_pool_file(filename):
    """Traversal-safe absolute path for a pool deb, or None."""
    if not re.match(r'^[a-z0-9][a-z0-9+.-]*_[^_/]+_all\.deb$',
                    filename or ''):
        return None
    directory = os.path.realpath(pool_dir())
    path = os.path.realpath(os.path.join(directory, filename))
    if not path.startswith(directory + os.sep):
        return None
    return path if os.path.isfile(path) else None


def main(argv):
    """Thin CLI: python3 -m appstore.custom.app_deb_builder <module>...
    (or --all). The isle CLI verb `isle apps build-debs` calls this
    — ONE implementation, no twin scripts."""
    if not argv or argv == ['--all']:
        results = prebuild_all()
    else:
        analysis = analyze()
        results = {m: generate(m, analysis=analysis) for m in argv}
    failures = 0
    for module, result in sorted(results.items()):
        if result.get('ok'):
            state = 'cached' if result['cached'] else 'generated'
            print(f'{module}: {state} {result["file"]} '
                  f'({result["bytes"]} B, {result["seconds"]} s)')
        else:
            failures += 1
            print(f'{module}: REFUSED — {result["refusal"]}')
    print(f'pool: {pool_dir()}')
    return 1 if failures else 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
