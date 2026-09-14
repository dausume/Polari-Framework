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
        self.media = None; self.status = '200 OK'; self.data = None; self.content_type = ''; self.downloadable_as = ''; self.headers = {}
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
    check('offline differences name the system engines as NOT inside', d['not_inside'] == ['ngspice'] and d['needs_internet_at_setup'] is True)
    r = S(); api.on_post_request(R(flavor='online'), r, mod)
    check('request → 202 accepted with the URLs', r.status.startswith('202') and r.media.get('accepted') and r.media['download_url'].endswith('flavor=online'))
    for _ in range(120):
        st = status_of(mod, 'online')
        if st['state'] in ('ready', 'refused'):
            break
        time.sleep(1)
    check('generation finished (ready) in the temp pool', st['state'] == 'ready' and st['bytes'] > 0 and len(st['sha256']) == 64, str(st.get('state')) + ' ' + str(st.get('refusal', '')))
    r = S(); api.on_get_download(R(flavor='online'), r, mod)
    check('download streams the deb with its sha256 header', r.data is not None and len(r.data) == st['bytes'] and r.headers.get('X-Polari-Sha256') == st['sha256'] and r.content_type.startswith('application/vnd.debian'))
    r = S(); api.on_post_request(R(flavor='online'), r, mod); check('request again when ready → 200 already available', r.status.startswith('200') and 'already available' in r.media['reading'])
    r = S(); api.on_get_downloads(R(), r); check('/api/downloads answers (installers list, may be empty here)', r.media.get('ok') is True and 'installers' in r.media)
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
