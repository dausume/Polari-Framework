"""
@module appstore.app_deb_builder

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
  - appstore.selftest_app_debs
  - isle CLI `isle apps build-debs` (thin verb over this module)
"""

import gzip
import hashlib
import io
import json
import os
import re
import statistics
import subprocess
import tarfile
import threading
import time

from moduleService import module_registry

from appstore import module_requirements as modreqs

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
    try:
        return int(os.environ.get('POLARI_APP_DEB_TTL', '3600'))
    except ValueError:
        return 3600


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


def analyze(root=None):
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
        module_dir = os.path.join(froot,
                                  entry.get('path',
                                            f'modules/{module}'))
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
            info.mode = 0o644
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    tar.close()
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb', mtime=0,
                       compresslevel=9) as gz:
        gz.write(raw.getvalue())
    return buffer.getvalue()


def _write_deb(path, control_fields, data_entries):
    control = ''.join(f'{k}: {v}\n' for k, v in control_fields
                      if v).encode()
    control_tar = _tar_gz([('./', 'dir', None),
                           ('./control', 'file', control)])
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
             progress=None):
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
                 < ttl_seconds())
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
        # cache hit inside the TTL window — same content, same file
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
    ], entries)
    step('assemble deb', t0)

    seconds = round(time.time() - started, 3)
    _append_record({'module': module, 'flavor': flavor,
                    'contentHash': content_hash,
                    'bytes': size_bytes, 'seconds': seconds,
                    'steps': steps,
                    'generatedAt': int(started)})
    return {'ok': True, 'file': filename, 'path': path,
            'version': version, 'bytes': size_bytes,
            'seconds': seconds, 'cached': False,
            'sharedFiles': shared_files}


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


def pool_file_for(module, flavor='online'):
    """The unexpired pool deb for module+flavor, or None —
    {'file', 'bytes', 'ageSeconds'}. Drives the button honesty:
    an already-generated app offers Download, not Generate."""
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


def estimate_seconds(module, recent=10, flavor='online'):
    """Median of the module's recent generation times for ONE
    flavor (offline runs fetch wheels — a different animal), or
    None — the page renders None as the honest 'never generated
    yet'. Legacy rows without a flavor count as online."""
    times = [row['seconds'] for row in generation_records(module)
             if isinstance(row.get('seconds'), (int, float))
             and row.get('flavor', 'online') == flavor]
    return (round(statistics.median(times[-recent:]), 1)
            if times else None)


# --- background generation jobs (dl-8: the click must confirm,
# show progress, and hand the file over when ready) -------------------

_jobs = {}


def generation_job(module, flavor):
    return _jobs.get(f'{module}:{flavor}')


def start_generation(module, flavor='online', root=None):
    """Idempotent kick-off: a running job is returned as-is; a
    finished one whose pool file the TTL already purged restarts.
    The job dict is live — 'step' updates as generation moves."""
    key = f'{module}:{flavor}'
    job = _jobs.get(key)
    if job:
        if job['state'] == 'running':
            return job
        if (job['state'] == 'done'
                and os.path.isfile(job['result']['path'])):
            return job
    job = {'module': module, 'flavor': flavor, 'state': 'running',
           'step': 'starting', 'startedAt': time.time(),
           'result': None}
    _jobs[key] = job

    def run():
        try:
            result = generate(
                module, root=root, flavor=flavor,
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


# --- pool lifecycle -------------------------------------------------

def purge_expired(ttl=None):
    """Delete pool debs older than the TTL; returns names removed.
    Runs opportunistically on every page/download request — no
    background thread to die quietly."""
    ttl = ttl_seconds() if ttl is None else ttl
    removed = []
    now = time.time()
    try:
        for entry in os.listdir(pool_dir()):
            path = os.path.join(pool_dir(), entry)
            if (os.path.isfile(path)
                    and now - os.path.getmtime(path) > ttl):
                os.remove(path)
                removed.append(entry)
    except FileNotFoundError:
        pass
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
    """Thin CLI: python3 -m appstore.app_deb_builder <module>...
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
