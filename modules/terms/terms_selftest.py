"""terms_selftest — the documents seed well-formed, the API gates and records
acceptances correctly (hash/version checks, subject resolution, append-only),
the page has no raw JSON. Stdlib + the framework's manager stub only."""
import json
import sys
from types import SimpleNamespace

from terms import TERMS_CLASSES, TERMS_SEED_PAIRS
from terms.terms_api import TermsAPI, body_hash
from terms.terms_basis import TermsAcceptance, TermsDocument
from terms.terms_page import SEED_TERMS_PAGE_DISPLAYS
from terms.terms_seed import SEED_TERMS_DOCUMENTS

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, extra if not cond else ''))


class _Manager:
    """Enough of managerObject for the API: objectTables + a no-op db."""
    def __init__(self):
        self.objectTables = {'TermsDocument': {}, 'TermsAcceptance': {}}
        self.db = None
        self.objectTypingDict = {}
        self.idList = []

    # rows register themselves into objectTables when constructed with manager=


class _Req:
    def __init__(self, params=None, media=None, user=None, addr='10.0.0.9', ua='selftest'):
        self._p = params or {}
        self._m = media or {}
        self.context = SimpleNamespace(user_info=user)
        self.remote_addr = addr
        self.user_agent = ua

    def get_param(self, k):
        return self._p.get(k)

    def get_media(self):
        return self._m


class _Resp:
    def __init__(self):
        self.media = None
        self.status = '200 OK'
        self.content_type = ''
        self.text = ''


def main():
    m = _Manager()
    for name, cls, rows in TERMS_SEED_PAIRS:
        for r in rows:
            cls(**r, manager=m)
    api = TermsAPI(polServer=None, manager=m)
    check('two classes, one seed pair, three documents',
          TERMS_CLASSES == [TermsDocument, TermsAcceptance] and len(TERMS_SEED_PAIRS) == 1 and len(SEED_TERMS_DOCUMENTS) == 3)
    check('every document has name, version, body, kind/scope in vocabulary',
          all(d['name'] and d['version'] and d['body_md'] and d['kind'] in ('demo', 'standard', 'privacy', 'custom')
              and d['scope'] in ('global', 'app') for d in SEED_TERMS_DOCUMENTS))
    check('only the demo terms are active by default; the demo turns the bar on',
          [d['name'] for d in SEED_TERMS_DOCUMENTS if d['active']] == ['demo-terms']
          and next(d for d in SEED_TERMS_DOCUMENTS if d['name'] == 'demo-terms')['show_bar'])
    # active: anonymous session, nothing accepted yet
    r = _Resp(); api.on_get_active(_Req({'app': 'meal-planning', 'session': 'sess-1'}), r)
    check('active lists the demo terms as pending for a fresh session, bar on',
          r.media['pending'] == ['demo-terms'] and r.media['show_bar'] and r.media['subject_kind'] == 'anonymous')
    demo = next(d for d in r.media['documents'] if d['name'] == 'demo-terms')
    check('the served document carries its sha256', demo['body_sha256'] == body_hash(demo['body_md']))
    # accept with a wrong hash → refused
    r = _Resp(); api.on_post_accept(_Req(media={'terms_name': 'demo-terms', 'terms_version': demo['version'],
                                                'body_sha256': 'deadbeef', 'session': 'sess-1', 'app': 'meal-planning'}), r)
    check('acceptance of a different text is refused (409)', r.status.startswith('409') and not r.media['ok'])
    # accept properly
    r = _Resp(); api.on_post_accept(_Req(media={'terms_name': 'demo-terms', 'terms_version': demo['version'],
                                                'body_sha256': demo['body_sha256'], 'session': 'sess-1', 'app': 'meal-planning'}), r)
    check('a matching acceptance is recorded (clickwrap, anonymous subject, hashed client)',
          r.media['ok'] and r.media['accepted']['subject_kind'] == 'anonymous'
          and len(m.objectTables['TermsAcceptance']) == 1
          and next(iter(m.objectTables['TermsAcceptance'].values())).client_hash != '10.0.0.9'
          and next(iter(m.objectTables['TermsAcceptance'].values())).method == 'clickwrap')
    r = _Resp(); api.on_get_active(_Req({'app': 'meal-planning', 'session': 'sess-1'}), r)
    check('after acceptance nothing is pending for that session; the bar stays on', r.media['pending'] == [] and r.media['show_bar'])
    r = _Resp(); api.on_get_active(_Req({'app': 'meal-planning', 'session': 'sess-2'}), r)
    check('another session is still pending', r.media['pending'] == ['demo-terms'])
    # logged-in user wins over the session id
    user = {'sub': 'kc-user-1'}
    r = _Resp(); api.on_post_accept(_Req(media={'terms_name': 'demo-terms', 'terms_version': demo['version'],
                                                'body_sha256': demo['body_sha256'], 'session': 'sess-9'}, user=user), r)
    r2 = _Resp(); api.on_get_active(_Req({'session': 'other'}, user=user), r2)
    check('a logged-in user is the subject (not the session) and is remembered across sessions',
          r.media['accepted']['subject_kind'] == 'user' and r2.media['pending'] == [])
    # version bump re-prompts
    doc = next(iter(m.objectTables['TermsDocument'].values()))
    d = [x for x in m.objectTables['TermsDocument'].values() if x.name == 'demo-terms'][0]
    d.version = '2027-01-01'
    r = _Resp(); api.on_get_active(_Req({'session': 'sess-1'}), r)
    check('bumping the version re-prompts everyone', r.media['pending'] == ['demo-terms'])
    # per-app scope
    TermsDocument(name='meal-terms', title='Meal terms', kind='custom', scope='app', app_name='meal-planning',
                  version='1', active=True, requires_acceptance=True, body_md='x', manager=m)
    r = _Resp(); api.on_get_active(_Req({'app': 'meal-planning', 'session': 'sess-3'}), r)
    r2 = _Resp(); api.on_get_active(_Req({'app': 'other-app', 'session': 'sess-3'}), r2)
    check('an app-scoped document applies only to its app',
          'meal-terms' in r.media['pending'] and 'meal-terms' not in r2.media['pending'])
    # page render
    r = _Resp(); api.on_get_page(_Req(), r, 'demo-terms')
    check('/terms/<name> renders the document without JS', '<h1>Demo terms</h1>' in r.text and '<script' not in r.text)
    check('page has no api-json-panel', 'api-json-panel' not in json.dumps(SEED_TERMS_PAGE_DISPLAYS))
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
