"""apps_api_selftest — the app-deb API: the catalogue lists every registered module (downloaded or not) with
both flavours; status answers honestly per flavour (differences, space, estimate); request on a downloaded
module starts a real generation into a TEMP pool; download streams the file when ready with its sha256, and
answers 202/409 with a sentence otherwise; an unknown module is a named refusal. Uses request/response doubles."""
import os
import sys
import tempfile
import time

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, extra if not cond else ''))


class R:
    def __init__(self, **p):
        self.params = p


class S:
    def __init__(self):
        self.media = None; self.status = '200 OK'; self.data = None; self.stream = None; self.content_type = ''; self.downloadable_as = ''; self.headers = {}
    def set_header(self, k, v):
        self.headers[k] = v


def main():
    tmp = tempfile.mkdtemp(prefix='apps-api-')
    os.environ['POLARI_APP_DEBS_DIR'] = tmp
    from appstore.apps_api import AppsAPI, status_of, flavor_differences, space
    api = AppsAPI(polServer=None, manager=None)
    r = S(); api.on_get(R(), r); cat = r.media
    check('catalogue: every registered module, both flavours, downloaded flag', cat['ok'] and cat['count'] >= 50 and all(set(a['flavors']) == {'online', 'offline'} for a in cat['apps']) and cat['downloaded'] > 0)
    r = S(); api.on_get_status(R(flavor='offline'), r, 'nope'); check('unknown module → 404 with a sentence', r.status.startswith('404') and 'not in the module registry' in r.media['refusal'])
    mod = next(a['module'] for a in cat['apps'] if a['downloaded'] and a['module'] in ('gears', 'terms', 'mathshapes', 'zones'))
    on = status_of(mod, 'online'); off = status_of(mod, 'offline')
    check('status: online vs offline differ in what they carry', on['differences']['carries'] != off['differences']['carries'] and on['differences']['needs_internet_at_setup'] is True)
    check('status: space check present with numbers', isinstance(on['space'].get('ok'), bool) and 'needed_bytes' in on['space'])
    check('status: not generated yet before any request', on['state'] == 'not-generated')
    r = S(); api.on_get_download(R(flavor='online'), r, mod); check('download before request → 409 with the request URL', r.status.startswith('409') and 'request' in r.media['refusal'])
    d = flavor_differences({'libraries': [{'bytes': 1}], 'librariesBytes': 5 << 20, 'librariesUnmeasured': 0, 'engines': [{'name': 'ngspice', 'kind': 'system'}]}, 'offline')
    check('offline differences: ngspice is already inside the runtime image, so no internet is needed at setup', d['not_inside'] == ['ngspice'] and d['engines']['in_runtime_image'] == ['ngspice'] and d['needs_internet_at_setup'] is False)
    d2 = flavor_differences({'libraries': [], 'librariesBytes': 0, 'librariesUnmeasured': 0, 'engines': [{'name': 'verilator', 'kind': 'system'}, {'name': 'docker', 'kind': 'system'}]}, 'offline')
    check('offline differences: host-level engines named, unavailable ones named as a gap', d2['engines']['host_level'] == ['docker'] and d2['engines']['not_available_anywhere_yet'] == ['verilator'] and d2['needs_internet_at_setup'] is True)
    # the presence-checked offline install: pip with --no-index against a wheel dir; an already-present package is skipped, never fetched
    from moduleService.module_dependency_tracker import install_packages
    import subprocess, sys as _sys
    wheel_dir = tempfile.mkdtemp(prefix='wheels-')
    rep = install_packages(['pip'], find_links=wheel_dir)
    check('offline install: --no-index + find-links, an already-present package is skipped (no internet)', rep.get('offline') is True and 'pip' in rep.get('skippedPresent', []) and rep.get('ok') is True, str({k: rep.get(k) for k in ('ok', 'skippedPresent', 'error')}))
    rep2 = install_packages(['this-package-does-not-exist-polari'], find_links=wheel_dir)
    check('offline install: a package not carried and not present is an honest failure, not a download', rep2.get('ok') is False and '--no-index' in rep2['command'])
    r = S(); api.on_post_request(R(flavor='online'), r, mod)
    check('request → 202 accepted with the URLs', r.status.startswith('202') and r.media.get('accepted') and r.media['download_url'].endswith('flavor=online'))
    for _ in range(120):
        st = status_of(mod, 'online')
        if st['state'] in ('ready', 'refused'):
            break
        time.sleep(1)
    check('generation finished (ready) in the temp pool', st['state'] == 'ready' and st['bytes'] > 0 and len(st['sha256']) == 64, str(st.get('state')) + ' ' + str(st.get('refusal', '')))
    r = S(); api.on_get_download(R(flavor='online'), r, mod)
    body = r.stream.read() if getattr(r, 'stream', None) else r.data; r.stream.close() if getattr(r, 'stream', None) else None
    check('download streams the deb with its sha256 header (a stream, never read into memory)', body is not None and len(body) == st['bytes'] and r.headers.get('X-Polari-Sha256') == st['sha256'] and r.content_type.startswith('application/vnd.debian') and r.headers.get('Content-Length') == str(st['bytes']))
    r = S(); api.on_post_request(R(flavor='online'), r, mod); check('request again when ready → 200 already available', r.status.startswith('200') and 'already available' in r.media['reading'])
    r = S(); api.on_get_downloads(R(), r); check('/api/downloads answers (installers list, may be empty here)', r.media.get('ok') is True and 'installers' in r.media)
    # his rulings 2026-09-14: the ACCESS form of every app (online + offline), side by side with the install form
    from appstore.custom import app_forms
    r = S(); api.on_get_status(R(flavor='online', form='access'), r, mod); sa = r.media
    check('status form=access: the shell package, group, app kind, no fetch needed', sa['form'] == 'access' and sa['package'] == f"polari-access-{mod.replace('_', '-')}" and sa['group'] in ('software', 'hardware', 'expansion') and sa['app_kind'])
    r = S(); api.on_post_request(R(flavor='online', form='access'), r, mod)
    check('request form=access → 202/200 without touching module code', r.status[:3] in ('202', '200') and r.media.get('accepted') or 'already available' in str(r.media.get('reading', '')))
    for _ in range(60):
        st = status_of(mod, 'online', form='access')
        if st['state'] in ('ready', 'refused'):
            break
        time.sleep(1)
    check('access deb generated (small: a launcher, no wheels)', st['state'] == 'ready' and 0 < st['bytes'] < 200_000, st)
    r = S(); api.on_get_download(R(flavor='online', form='access'), r, mod)
    body = r.stream.read() if getattr(r, 'stream', None) else r.data
    r.stream.close() if getattr(r, 'stream', None) else None
    check('download form=access streams the access deb', body and len(body) == st['bytes'] and r.downloadable_as.startswith('polari-access-'))
    import tarfile, io, gzip
    def deb_members(blob):
        # ar: skip the 8-byte magic, walk members; return {name: bytes}
        out = {}; i = 8
        while i + 60 <= len(blob):
            name = blob[i:i+16].decode().strip(); size = int(blob[i+48:i+58].decode().strip()); out[name] = blob[i+60:i+60+size]; i += 60 + size + (size % 2)
        return out
    def tar_names(tgz):
        return {m.name: m for m in tarfile.open(fileobj=io.BytesIO(gzip.decompress(tgz)), mode='r:').getmembers()}
    mem = deb_members(body); data = tar_names(mem['data.tar.gz']); ctrl = tar_names(mem['control.tar.gz'])
    check('the access deb carries the .desktop, open.sh (executable) and access.json; Depends on polari-shell-core (online)',
          any(n.endswith('.desktop') for n in data) and any(n.endswith('/open.sh') and (m.mode & 0o111) for n, m in data.items()) and any(n.endswith('access.json') for n in data)
          and b'polari-shell-core' in mem['control.tar.gz'] or b'polari-shell-core' in gzip.decompress(mem['control.tar.gz']), list(data)[:6])
    r = S(); api.on_get_access_one(R(), r, mod); check('/api/access/{module} answers where the app is reached (url + candidates)', r.media.get('ok') and r.media['url'].startswith('https://') and r.media['candidates'])
    r = S(); api.on_get_access(R(), r); check('/api/access lists every app with an address', r.media.get('ok') and r.media['count'] >= 50)
    # the install-form refusals ride in the deb as a preinst (a hardware expansion here: reticulum extends isle-relay)
    hw = app_forms.manifest_app('reticulum'); pre = app_forms.preinst_for('reticulum', hw)
    check('preinst for an expansion: refuses without its base and on a lightweight isle, in his words', hw['kind'] == 'hardware-extension-app' and 'expands isle-relay' in pre and app_forms.LIGHTWEIGHT_ISLE_REFUSAL in pre and 'dpkg -s polari-app-isle-relay' in pre)
    check('preinst for a hardware app names the lightweight-isle and hardware-tier refusals; a software app carries none',
          app_forms.LIGHTWEIGHT_ISLE_REFUSAL in app_forms.preinst_for('x', {'kind': 'hardware-app'}) and app_forms.NOT_HARDWARE_TIER_REFUSAL in app_forms.preinst_for('x', {'kind': 'hardware-app'}) and app_forms.preinst_for('gears', app_forms.manifest_app('gears')) == '')
    g = app_forms.grouped({'reticulum': {}, 'isle_relay': {}, 'gears': {}})
    check('grouping: software / hardware / expansions nest under their base (isle_relay is still a polari-app in its manifest → reticulum is an orphan here)',
          any(m == 'gears' for m, _, _ in g['software']) and (('isle_relay' in g['expansions'] and g['expansions']['isle_relay'][0][0] == 'reticulum') or (g['orphans'] and g['orphans'][0][0] == 'reticulum')), {k: (v if k != 'expansions' else list(v)) for k, v in g.items()})
    # his policy 2026-09-14: the pool remembers requests/downloads, holds 3× a slow download, evicts only for room after the hold, idle-purges after a day
    import os as _os
    from appstore.custom import app_deb_builder as builder
    pool = builder.pool_dir(); files = sorted(f for f in _os.listdir(pool) if f.endswith('.deb'))
    e = builder.pool_entry(files[0])
    check('the pool ledger knows the generated deb: requested_at, requests ≥ 1, a hold ≥ the 10-minute floor', e.get('requested_at') and e.get('requests', 0) >= 1 and e.get('hold_remaining_seconds', 0) >= 590, e)
    check('the hold scales with size: 55 MB over a slow connection ≈ 3 × 220 s', builder.hold_seconds(55 * 1024 * 1024) >= 600 and builder.hold_seconds(55 * 1024 * 1024) == max(600, int(3 * 55 * 1024 * 1024 / builder.slow_bps())))
    before = e['requests']; builder.note_request(files[0], e.get('bytes')); check('a re-request refreshes the hold and counts', builder.pool_entry(files[0])['requests'] == before + 1)
    builder.inflight_begin(files[0]); r = builder.make_room(10 ** 12); builder.inflight_end(files[0])
    check('make_room never evicts a deb in flight or inside its hold — refuses with the earliest hold named', r['ok'] is False and r['blocked_by'] and 'inside its minimum hold' in r['note'], r)
    L = builder._ledger(); L[files[0]]['hold_until'] = time.time() - 1; L[files[0]]['last_access'] = time.time() - 5
    r2 = builder.make_room(builder.pool_max_bytes())   # needs the whole cap → must evict the now-evictable deb
    check('after the hold, room is made by evicting least-recently-accessed first', files[0] in r2['evicted'] and not _os.path.exists(_os.path.join(pool, files[0])), r2)
    _os.makedirs(pool, exist_ok=True); open(_os.path.join(pool, 'polari-app-idle_0.1.0_all.deb'), 'wb').write(b'x' * 100)
    builder._ledger()['polari-app-idle_0.1.0_all.deb'] = {'last_access': time.time() - builder.IDLE_SECONDS - 10, 'hold_until': time.time() + 10 ** 6, 'requests': 1, 'downloads': 0}
    removed = builder.purge_expired()
    check('the idle purge frees a deb untouched for a day even inside a long hold; holds alone never delete', 'polari-app-idle_0.1.0_all.deb' in removed)
    st = builder.pool_status(); check('pool status: used/max/free, the slow-connection speed and the policy knobs', st['max_bytes'] > 0 and 'slow_bps' in st and st['hold_multiplier'] == 3 and st['idle_seconds'] == 86400)
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
