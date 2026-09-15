"""
@module iso.custom.iso_builder

Bases and builds. A BASE is Ubuntu's Server live ISO for a release: its exact file and checksum are read from
Ubuntu's SHA256SUMS (never typed), fetched once into the base cache with the checksum verified, and the release's
kernel `modules.alias` table fetched from the archive for the compatibility check. A BUILD takes a cached base and
the choices, lays the tree next to it (the autoinstall `nocloud/`, `polari/debs` with the platform installer and
any app debs, `polari/first-boot.sh`, per-device plans), patches GRUB to boot unattended, and assembles a hybrid ISO
with xorriso (genisoimage + isohybrid as the fallback) into the ISO POOL, which lives under the same policy as the
app-deb pool (holds of three slow downloads, eviction for room, a cap, a day's idle purge) with its own, larger cap.

@consumers
  - iso.iso_api, iso.iso_selftest, polari-cli (pol iso …)
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request

from iso.custom import iso_autoinstall

ISO_POOL_MAX_DEFAULT = 8 * 1024 ** 3
HOLD_MULTIPLIER = 3
HOLD_FLOOR = 1800          # an ISO is 2–3 GB: half an hour at least
IDLE_SECONDS = 86400
SPACE_MARGIN = 500 * 1024 * 1024
_jobs = {}
_LEDGER = {}


def work_dir():
    return os.environ.get('POLARI_ISO_DIR', os.path.join(os.environ.get('POLARI_APP_DEBS_DIR', '/app/data/app-debs').rsplit('/app-debs', 1)[0], 'iso'))


def bases_dir():
    return os.path.join(work_dir(), 'bases')


def pool_dir():
    return os.path.join(work_dir(), 'pool')


def ledger_path():
    return os.path.join(work_dir(), 'pool-ledger.json')


def _ledger():
    if not _LEDGER:
        try:
            _LEDGER.update(json.load(open(ledger_path())))
        except Exception:
            pass
    return _LEDGER


def _save():
    os.makedirs(work_dir(), exist_ok=True)
    tmp = ledger_path() + '.tmp'; json.dump(_LEDGER, open(tmp, 'w'), indent=1); os.replace(tmp, ledger_path())


def slow_bps():
    try:
        return int(os.environ.get('POLARI_SLOW_DOWNLOAD_BPS', '250000'))
    except ValueError:
        return 250000


def hold_seconds(size):
    return max(HOLD_FLOOR, int(HOLD_MULTIPLIER * (size or 0) / slow_bps()))


def pool_max_bytes():
    try:
        cap = int(os.environ.get('POLARI_ISO_POOL_MAX_BYTES', str(ISO_POOL_MAX_DEFAULT)))
    except ValueError:
        cap = ISO_POOL_MAX_DEFAULT
    probe = pool_dir()
    while probe and not os.path.isdir(probe):
        probe = os.path.dirname(probe.rstrip('/'))
    try:
        return max(0, min(cap, pool_used() + shutil.disk_usage(probe or '/').free - SPACE_MARGIN))
    except Exception:
        return cap


def _files():
    try:
        return [f for f in os.listdir(pool_dir()) if f.endswith('.iso')]
    except FileNotFoundError:
        return []


def pool_used():
    return sum(os.path.getsize(os.path.join(pool_dir(), f)) for f in _files())


def note_request(filename, size=None):
    now = time.time(); L = _ledger(); row = L.setdefault(filename, {'first_requested_at': now, 'requests': 0, 'downloads': 0})
    row.update({'requested_at': now, 'last_access': now, 'requests': row['requests'] + 1})
    if size:
        row['bytes'] = size
    row['hold_until'] = now + hold_seconds(row.get('bytes', size or 0)); _save(); return row


def note_download(filename, seconds=None, size=None):
    now = time.time(); L = _ledger(); row = L.setdefault(filename, {'first_requested_at': now, 'requests': 0, 'downloads': 0})
    row.update({'last_access': now, 'last_download_at': now, 'downloads': row['downloads'] + 1})
    if size:
        row['bytes'] = size
    row['hold_until'] = max(row.get('hold_until', 0), now + hold_seconds(row.get('bytes', size or 0))); _save(); return row


def pool_entry(filename):
    row = dict(_ledger().get(filename) or {}); now = time.time()
    row['hold_remaining_seconds'] = max(0, int(row.get('hold_until', 0) - now)); row['evictable'] = row['hold_remaining_seconds'] == 0
    return row


def pool_status():
    used = pool_used(); cap = pool_max_bytes()
    return {'used_bytes': used, 'max_bytes': cap, 'free_bytes': max(0, cap - used), 'files': len(_files()), 'slow_bps': slow_bps(), 'hold_floor_seconds': HOLD_FLOOR, 'idle_seconds': IDLE_SECONDS}


def make_room(needed):
    L = _ledger(); cap = pool_max_bytes(); used = pool_used(); evicted = []; blocked = []; now = time.time()
    if used + needed <= cap:
        return {'ok': True, 'evicted': [], 'blocked_by': [], 'note': ''}
    for f in sorted(_files(), key=lambda f: L.get(f, {}).get('last_access', 0)):
        if used + needed <= cap:
            break
        if L.get(f, {}).get('hold_until', 0) > now:
            blocked.append({'file': f, 'hold_remaining_seconds': int(L[f]['hold_until'] - now)}); continue
        size = os.path.getsize(os.path.join(pool_dir(), f)); os.remove(os.path.join(pool_dir(), f)); L.pop(f, None); evicted.append(f); used -= size
    if evicted:
        _save()
    ok = used + needed <= cap
    soonest = min((b['hold_remaining_seconds'] for b in blocked), default=0)
    return {'ok': ok, 'evicted': evicted, 'blocked_by': blocked[:10],
            'note': '' if ok else f'the ISO pool is full ({used >> 20} MB of {cap >> 20} MB) and every image in it is inside its minimum hold' + (f' — the earliest hold ends in {soonest // 60} min' if blocked else '') + '; try again then, or raise POLARI_ISO_POOL_MAX_BYTES'}


def purge_idle():
    L = _ledger(); now = time.time(); removed = []
    for f in _files():
        last = L.get(f, {}).get('last_access') or os.path.getmtime(os.path.join(pool_dir(), f))
        if now - last > IDLE_SECONDS:
            os.remove(os.path.join(pool_dir(), f)); L.pop(f, None); removed.append(f)
    if removed:
        _save()
    return removed


# --- bases ------------------------------------------------------------------------------------------------------

def discover_base(url):
    """Read Ubuntu's SHA256SUMS at the release URL: the exact live-server amd64 file and its checksum. Never typed."""
    try:
        with urllib.request.urlopen(url.rstrip('/') + '/SHA256SUMS', timeout=30) as r:
            text = r.read().decode()
    except Exception as exc:
        return {'ok': False, 'refusal': f'could not read SHA256SUMS at {url}: {exc}'}
    for line in text.splitlines():
        m = re.match(r'^([0-9a-f]{64})\s+\*?(ubuntu-[\d.]+-live-server-amd64\.iso)$', line.strip())
        if m:
            return {'ok': True, 'file': m.group(2), 'sha256': m.group(1), 'url': url.rstrip('/') + '/' + m.group(2)}
    return {'ok': False, 'refusal': f'no live-server amd64 ISO listed at {url}'}


def base_path(filename):
    return os.path.join(bases_dir(), filename)


def base_status(row):
    """What this instance holds for a seeded base: discovered file, cached bytes, kernel table."""
    out = {'name': row.get('name'), 'release': row.get('release'), 'url': row.get('url'), 'file': '', 'sha256': '', 'cached': False, 'bytes': 0, 'kernel_table': ''}
    meta = os.path.join(bases_dir(), f"{row.get('name')}.json")
    try:
        out.update({k: v for k, v in json.load(open(meta)).items() if k in ('file', 'sha256', 'kernel_table', 'kernel_abi')})
    except Exception:
        pass
    if out['file'] and os.path.isfile(base_path(out['file'])):
        out['cached'] = True; out['bytes'] = os.path.getsize(base_path(out['file']))
    job = _jobs.get('base:' + str(row.get('name')))
    if job:
        out['job'] = {'state': job['state'], 'step': job['step'], 'progress': job.get('progress', 0)}
    return out


def fetch_base(row):
    """Background: discover, download with progress, verify the checksum, then fetch the kernel table."""
    key = 'base:' + row['name']
    if key in _jobs and _jobs[key]['state'] == 'running':
        return _jobs[key]
    job = {'state': 'running', 'step': 'discovering', 'progress': 0, 'startedAt': time.time(), 'result': None}; _jobs[key] = job

    def run():
        try:
            d = discover_base(row['url'])
            if not d['ok']:
                job.update({'state': 'refused', 'result': d}); return
            os.makedirs(bases_dir(), exist_ok=True)
            meta = os.path.join(bases_dir(), f"{row['name']}.json"); json.dump({'file': d['file'], 'sha256': d['sha256'], 'url': d['url']}, open(meta, 'w'))
            dest = base_path(d['file'])
            if not (os.path.isfile(dest) and _sha256(dest) == d['sha256']):
                job['step'] = f"downloading {d['file']}"
                tmp = dest + '.part'; h = hashlib.sha256(); done = 0
                with urllib.request.urlopen(d['url'], timeout=60) as r, open(tmp, 'wb') as fh:
                    total = int(r.headers.get('Content-Length') or 0)
                    while True:
                        chunk = r.read(1 << 22)
                        if not chunk:
                            break
                        fh.write(chunk); h.update(chunk); done += len(chunk); job['progress'] = int(done * 100 / total) if total else 0
                if h.hexdigest() != d['sha256']:
                    os.remove(tmp); job.update({'state': 'refused', 'result': {'ok': False, 'refusal': 'checksum mismatch after download — refused, nothing kept'}}); return
                os.replace(tmp, dest)
            job['step'] = 'fetching the kernel table'
            kt = fetch_kernel_table(row['release'], row['name'])
            m = json.load(open(meta)); m.update(kt); json.dump(m, open(meta, 'w'))
            job.update({'state': 'done', 'progress': 100, 'result': {'ok': True, 'file': d['file'], 'sha256': d['sha256'], **kt}})
        except Exception as exc:   # noqa: BLE001
            job.update({'state': 'refused', 'result': {'ok': False, 'refusal': f'{type(exc).__name__}: {exc}'}})
    threading.Thread(target=run, daemon=True).start()
    return job


def fetch_kernel_table(release, base_name):
    """The release's generic kernel `modules.alias` from the Ubuntu archive (linux-modules-<abi>-generic): the
    Packages index names the current abi; the deb's data.tar carries lib/modules/<abi>/modules.alias."""
    codename = {'26.04': 'resolute', '24.04': 'noble', '22.04': 'jammy'}.get(release, '')
    if not codename:
        return {'kernel_table': '', 'kernel_abi': '', 'kernel_note': f'no codename known for {release}'}
    try:
        idx = f'http://archive.ubuntu.com/ubuntu/dists/{codename}-updates/main/binary-amd64/Packages.gz'
        import gzip
        with urllib.request.urlopen(idx, timeout=60) as r:
            text = gzip.decompress(r.read()).decode('utf-8', 'ignore')
        cands = re.findall(r'Package: (linux-modules-(\d[\w.-]*)-generic)\n(?:.*\n)*?Filename: (\S+)', text)
        if not cands:
            return {'kernel_table': '', 'kernel_abi': '', 'kernel_note': 'no linux-modules-*-generic in the index'}
        pkg, abi, fn = sorted(cands, key=lambda c: [int(x) if x.isdigit() else x for x in re.split(r'[.-]', c[1])])[-1]
        dest = os.path.join(bases_dir(), f'{base_name}.modules.alias')
        with urllib.request.urlopen('http://archive.ubuntu.com/ubuntu/' + fn, timeout=120) as r:
            deb = r.read()
        # ar → data.tar.* → lib/modules/<abi>/modules.alias
        import io, tarfile
        pos = 8; data = None
        while pos + 60 <= len(deb):
            name = deb[pos:pos + 16].decode().strip(); size = int(deb[pos + 48:pos + 58].decode().strip()); body = deb[pos + 60:pos + 60 + size]
            if name.startswith('data.tar'):
                data = (name, body); break
            pos += 60 + size + (size % 2)
        if not data:
            return {'kernel_table': '', 'kernel_abi': abi, 'kernel_note': 'no data.tar in the kernel deb'}
        mode = {'data.tar.xz': 'r:xz', 'data.tar.gz': 'r:gz', 'data.tar.zst': None, 'data.tar': 'r:'}.get(data[0], None)
        if mode is None:
            return {'kernel_table': '', 'kernel_abi': abi, 'kernel_note': f'{data[0]} compression not readable here'}
        with tarfile.open(fileobj=io.BytesIO(data[1]), mode=mode) as t:
            m = next((m for m in t.getmembers() if m.name.endswith('/modules.alias')), None)
            if not m:
                return {'kernel_table': '', 'kernel_abi': abi, 'kernel_note': 'modules.alias not in the deb'}
            open(dest, 'wb').write(t.extractfile(m).read())
        return {'kernel_table': dest, 'kernel_abi': abi, 'kernel_note': ''}
    except Exception as exc:   # noqa: BLE001
        return {'kernel_table': '', 'kernel_abi': '', 'kernel_note': f'kernel table fetch failed: {type(exc).__name__}: {exc}'}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# --- builds -----------------------------------------------------------------------------------------------------

def build_id(build):
    return hashlib.sha256(json.dumps({k: build.get(k) for k in ('base', 'role', 'shape', 'encryption', 'secure_boot', 'posture', 'look', 'hostname', 'username', 'ssh_keys', 'join_core', 'join_fingerprint', 'join_tier', 'target_hash', 'apps', 'offline')}, sort_keys=True).encode()).hexdigest()[:12]


def iso_filename(build):
    return f"polari-{build.get('role', 'member')}-{build.get('shape', 'detect')}-{build.get('base', 'ubuntu')}-{build_id(build)}.iso"


def tools():
    return {'xorriso': shutil.which('xorriso'), 'genisoimage': shutil.which('genisoimage'), 'isohybrid': shutil.which('isohybrid')}


def lay_tree(build, base_file, dest, platform_debs=(), app_debs=(), ssh_keys=(), core_key=''):
    """The overlay the ISO gets: nocloud/ (autoinstall), polari/ (debs, first-boot, plans), boot/grub/grub.cfg patched."""
    os.makedirs(os.path.join(dest, 'nocloud'), exist_ok=True); os.makedirs(os.path.join(dest, 'polari', 'debs'), exist_ok=True)
    os.makedirs(os.path.join(dest, 'polari', 'apps'), exist_ok=True); os.makedirs(os.path.join(dest, 'polari', 'plans'), exist_ok=True)
    ai = iso_autoinstall.render(build, ssh_keys=ssh_keys, core_key=core_key, apps=[os.path.basename(a) for a in app_debs])
    try:
        import yaml
        text = yaml.safe_dump(ai, sort_keys=False)
    except Exception:
        text = json.dumps(ai, indent=1)   # YAML is a superset of JSON: subiquity reads it
    open(os.path.join(dest, 'nocloud', 'user-data'), 'w').write('#cloud-config\n' + text)
    open(os.path.join(dest, 'nocloud', 'meta-data'), 'w').write('')
    open(os.path.join(dest, 'polari', 'first-boot.sh'), 'w').write(iso_autoinstall.first_boot_script()); os.chmod(os.path.join(dest, 'polari', 'first-boot.sh'), 0o755)
    open(os.path.join(dest, 'polari', 'polari-first-boot.service'), 'w').write(iso_autoinstall.first_boot_unit())
    for p in platform_debs:
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(dest, 'polari', 'debs', os.path.basename(p)))
    for p in app_debs:
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(dest, 'polari', 'apps', os.path.basename(p)))
    if build.get('target_hash'):
        json.dump({k: build.get(k) for k in ('role', 'shape', 'join_core', 'join_fingerprint', 'join_tier', 'look', 'posture')}, open(os.path.join(dest, 'polari', 'plans', f"{build['target_hash']}.json"), 'w'), indent=1)
    # GRUB: boot straight into the unattended install (D4: no question on the machine)
    grub = ('set timeout=3\nmenuentry "Install Ubuntu + Polari (unattended)" {\n    set gfxpayload=keep\n'
            '    linux /casper/vmlinuz autoinstall ds=nocloud\\;s=/cdrom/nocloud/ ---\n    initrd /casper/initrd\n}\n')
    os.makedirs(os.path.join(dest, 'boot', 'grub'), exist_ok=True); open(os.path.join(dest, 'boot', 'grub', 'grub.cfg'), 'w').write(grub)
    return dest


def assemble(base_iso, overlay, out_path, label='POLARI'):
    """Hybrid ISO = the base's contents + the overlay, El Torito BIOS + EFI boot kept from the base. xorriso first;
    genisoimage + isohybrid as the fallback; without either, a named refusal (the tree is still laid for a manual build)."""
    t = tools()
    if t['xorriso']:
        cmd = ['xorriso', '-indev', base_iso, '-outdev', out_path, '-map', overlay, '/', '-boot_image', 'any', 'replay', '-volid', label]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return {'ok': r.returncode == 0, 'tool': 'xorriso', 'log': (r.stderr or r.stdout)[-2000:]}
    if t['genisoimage']:
        # genisoimage cannot overlay onto an existing ISO: extract the base first (bsdtar/7z), then rebuild
        work = out_path + '.tree'; shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
        ex = shutil.which('bsdtar') or shutil.which('7z')
        if not ex:
            return {'ok': False, 'tool': 'genisoimage', 'log': 'no bsdtar/7z to extract the base ISO — install xorriso'}
        r = subprocess.run([ex, '-xf', base_iso, '-C', work] if 'bsdtar' in ex else [ex, 'x', '-y', f'-o{work}', base_iso], capture_output=True, text=True)
        if r.returncode != 0:
            return {'ok': False, 'tool': 'genisoimage', 'log': (r.stderr or r.stdout)[-2000:]}
        shutil.copytree(overlay, work, dirs_exist_ok=True)
        cmd = ['genisoimage', '-r', '-V', label, '-o', out_path, '-J', '-l', '-b', 'boot/grub/i386-pc/eltorito.img', '-c', 'boot.catalog', '-no-emul-boot', '-boot-load-size', '4', '-boot-info-table',
               '-eltorito-alt-boot', '-e', 'EFI/boot/bootx64.efi', '-no-emul-boot', work]
        r = subprocess.run(cmd, capture_output=True, text=True); shutil.rmtree(work, ignore_errors=True)
        if r.returncode == 0 and t['isohybrid']:
            subprocess.run([t['isohybrid'], '--uefi', out_path], capture_output=True)
        return {'ok': r.returncode == 0, 'tool': 'genisoimage', 'log': (r.stderr or r.stdout)[-2000:]}
    return {'ok': False, 'tool': '', 'log': 'no ISO tool on this instance (xorriso or genisoimage): the overlay tree is laid; assemble it elsewhere'}


def start_build(build, base_file, platform_debs=(), app_debs=(), ssh_keys=(), core_key='', progress=None):
    """Background build into the pool; the job dict is live (step, state, result)."""
    key = 'build:' + build_id(build)
    job = _jobs.get(key)
    if job and job['state'] == 'running':
        return job
    filename = iso_filename(build); out = os.path.join(pool_dir(), filename)
    if os.path.isfile(out):
        note_request(filename, os.path.getsize(out))
        job = {'state': 'done', 'step': 'cached', 'startedAt': time.time(), 'result': {'ok': True, 'file': filename, 'path': out, 'bytes': os.path.getsize(out), 'sha256': _sha256(out), 'cached': True}}
        _jobs[key] = job; return job
    job = {'state': 'running', 'step': 'starting', 'startedAt': time.time(), 'result': None}; _jobs[key] = job

    def run():
        t0 = time.time()
        try:
            refusal, warnings = iso_autoinstall.validate(build)
            if refusal:
                job.update({'state': 'refused', 'result': {'ok': False, 'refusal': refusal}}); return
            need = os.path.getsize(base_file) + sum(os.path.getsize(p) for p in list(platform_debs) + list(app_debs) if os.path.isfile(p)) + (100 << 20)
            room = make_room(need)
            if not room['ok']:
                job.update({'state': 'refused', 'result': {'ok': False, 'refusal': room['note'], 'blocked_by': room['blocked_by']}}); return
            os.makedirs(pool_dir(), exist_ok=True)
            job['step'] = 'laying the overlay (autoinstall, debs, first boot)'
            overlay = os.path.join(work_dir(), 'work', build_id(build)); shutil.rmtree(overlay, ignore_errors=True)
            lay_tree(build, base_file, overlay, platform_debs, app_debs, ssh_keys, core_key)
            job['step'] = 'assembling the ISO'
            res = assemble(base_file, overlay, out)
            shutil.rmtree(overlay, ignore_errors=True)
            if not res['ok']:
                job.update({'state': 'refused', 'result': {'ok': False, 'refusal': f"assembly failed ({res['tool'] or 'no tool'}): {res['log'][-300:]}"}}); return
            job['step'] = 'checksum'
            sha = _sha256(out); size = os.path.getsize(out); note_request(filename, size)
            job.update({'state': 'done', 'result': {'ok': True, 'file': filename, 'path': out, 'bytes': size, 'sha256': sha, 'seconds': round(time.time() - t0, 1), 'warnings': warnings, 'tool': res['tool'], 'cached': False}})
        except Exception as exc:   # noqa: BLE001
            job.update({'state': 'refused', 'result': {'ok': False, 'refusal': f'unexpected: {type(exc).__name__}: {exc}'}})
    threading.Thread(target=run, daemon=True).start()
    return job


def build_job(build):
    return _jobs.get('build:' + build_id(build))
