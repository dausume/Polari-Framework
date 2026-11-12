"""
selftest_tls_policy — the backend TLS policy (polariApiServer.tls_policy), the outbound seam applying it, and the
TREE AUDIT: no unverified TLS anywhere but the one helper and the named allowlist.

    PYTHONPATH=.:modules python3 polariApiServer/selftest_tls_policy.py

No network: urllib.request.urlopen and requests.request are replaced by fakes that record what they were given.
"""
import io
import os
import re
import ssl
import subprocess
import sys
import tempfile
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'modules'))

from polariApiServer import tls_policy, outbound   # noqa: E402

PASSED, FAILED = [], []


def check(name, cond, detail=''):
    (PASSED if cond else FAILED).append(name if cond else f'{name} :: {detail}')


KNOBS = ('POL_TLS_CA', 'POL_TLS_INSECURE', 'POLARI_INSECURE', 'POL_TLS_ANNOUNCED')


@contextlib.contextmanager
def env(**kv):
    saved = {k: os.environ.get(k) for k in KNOBS}
    for k in KNOBS:
        os.environ.pop(k, None)
    os.environ.update({k: v for k, v in kv.items() if v is not None})
    tls_policy._said.clear()
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        try:
            yield err
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def _ca_file(tmp):
    pem = os.path.join(tmp, 'ca.pem')
    r = subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', os.path.join(tmp, 'k'),
                        '-out', pem, '-subj', '/CN=selftest-tls-policy', '-days', '1'], capture_output=True)
    return pem if r.returncode == 0 else None


def test_modes(tmp):
    ca = _ca_file(tmp)
    with env() as err:
        check('default: mode verified', tls_policy.mode() == 'verified')
        check('default: context None (system store)', tls_policy.context('https://x') is None)
        check('default: requests verify True', tls_policy.requests_verify('https://x') is True)
        check('default: nothing said', err.getvalue() == '', err.getvalue())
    with env(POL_TLS_INSECURE='1') as err:
        ctx = tls_policy.context('https://x/p')
        check('insecure: unverified context', tls_policy.is_unverified(ctx))
        check('insecure: marked as built by the policy', tls_policy.built_here(ctx) == tls_policy.POLICY)
        check('insecure: requests verify False', tls_policy.requests_verify('https://x/p') is False)
        tls_policy.context('https://x/p'); tls_policy.context('https://x/q')
        out = err.getvalue()
        check('insecure: once-per-process notice', out.count('OFF for this process') == 1, out)
        check('insecure: once per DISTINCT url, not per request', out.count('OFF (POL_TLS_INSECURE=1): https://x/p') == 1
              and 'https://x/q' in out, out)
    with env(POL_TLS_INSECURE='true') as err:
        check('insecure spelt true', tls_policy.mode() == 'insecure')
    with env(POLARI_INSECURE='1') as err:
        check('alias POLARI_INSECURE=1 -> insecure', tls_policy.mode() == 'insecure')
    if ca:
        with env(POL_TLS_CA=ca) as err:
            ctx = tls_policy.context('https://x')
            check('cacert: a verifying context', isinstance(ctx, ssl.SSLContext) and ctx.verify_mode == ssl.CERT_REQUIRED)
            check('cacert: hostname verification stays ON', ctx.check_hostname is True)
            check('cacert: trusts the file (1 CA loaded)', len(ctx.get_ca_certs()) == 1, repr(ctx.get_ca_certs()))
            check('cacert: requests verify = the file', tls_policy.requests_verify('https://x') == ca)
            check('cacert: nothing said', err.getvalue() == '', err.getvalue())
        with env(POL_TLS_CA=ca, POL_TLS_INSECURE='1') as err:
            ctx = tls_policy.context('https://x')
            check('both set: CA wins (verifying)', ctx is not None and ctx.verify_mode == ssl.CERT_REQUIRED)
            check('both set: the ignored bypass is said', 'POL_TLS_INSECURE ignored' in err.getvalue(), err.getvalue())
            u = tls_policy.unverified_context('a test reason', 'https://x')
            check('both set: unverified_context() also yields the verifying one', u.verify_mode == ssl.CERT_REQUIRED)
    else:
        check('cacert cases', True, 'openssl unavailable: skipped')
    with env(POL_TLS_CA=os.path.join(tmp, 'nope.pem')) as err:
        try:
            tls_policy.context('https://x'); raised = None
        except RuntimeError as exc:
            raised = exc
        check('cacert missing file: refused in words', raised is not None and 'nope.pem' in str(raised), repr(raised))
    with env() as err:
        u = tls_policy.unverified_context('join flow, dev posture', 'https://peer')
        check('unverified_context: unverified, marked explicit', tls_policy.is_unverified(u) and tls_policy.built_here(u) == tls_policy.EXPLICIT)
        check('unverified_context: announced with its reason', 'OFF (join flow, dev posture): https://peer' in err.getvalue(), err.getvalue())
        i = tls_policy.inspection_context()
        check('inspection_context: unverified, marked inspection', tls_policy.is_unverified(i) and tls_policy.built_here(i) == tls_policy.INSPECTION)
        raw = ssl.create_default_context(); raw.check_hostname = False; raw.verify_mode = ssl.CERT_NONE
        check('a context built elsewhere is not marked', tls_policy.built_here(raw) is None)
        hn = ssl.create_default_context(); hn.check_hostname = False
        check('is_unverified: CERT_REQUIRED with the hostname check off counts as unverified', tls_policy.is_unverified(hn))
        check('is_unverified: a default context is verified', not tls_policy.is_unverified(ssl.create_default_context()))


def test_seam(tmp):
    import urllib.request as ur
    seen = {}
    real = ur.urlopen

    def fake(target, **kw):
        seen.clear(); seen.update(kw); seen['target'] = target
        return io.BytesIO(b'{}')
    ur.urlopen = fake
    ca = _ca_file(tmp)
    try:
        with env() as err:
            outbound.http_request('self', 'board', 'GET', 'https://api/x', timeout=3, lib='urllib')
            check('seam default: no context passed (system store)', 'context' not in seen, repr(seen))
        with env(POL_TLS_INSECURE='1') as err:
            outbound.http_request('self', 'board', 'GET', 'https://api/x', timeout=3, lib='urllib')
            check('seam insecure: the policy context is passed', tls_policy.is_unverified(seen.get('context')))
            check('seam insecure: announced', 'OFF (POL_TLS_INSECURE=1): https://api/x' in err.getvalue(), err.getvalue())
        if ca:
            with env(POL_TLS_CA=ca) as err:
                outbound.http_request('self', 'board', 'GET', 'https://api/x', timeout=3, lib='urllib')
                c = seen.get('context')
                check('seam cacert: a verifying context trusting the file', c is not None and c.verify_mode == ssl.CERT_REQUIRED and len(c.get_ca_certs()) == 1)
        def refused(label, **call):
            seen.clear()
            try:
                outbound.http_request(**call); raised = None
            except ValueError as exc:
                raised = exc
            check(f'seam: {label} is REFUSED in words', raised is not None, 'no ValueError')
            check(f'seam: … and urlopen never ran ({label})', 'target' not in seen, repr(seen))
            return raised
        def foreign(cert_none=True, hostname=False):
            c = ssl.create_default_context()
            c.check_hostname = hostname
            if cert_none:
                c.verify_mode = ssl.CERT_NONE
            return c
        # caller-supplied unverified contexts under the verified default: refused, never silently rebuilt
        with env() as err:
            r = refused('a caller CERT_NONE context under the verified default', system_kind='self', system_name='board', method='GET',
                        url='https://api/x', timeout=3, lib='urllib', context=foreign())
            check('seam: … the refusal names the fix', r is not None and 'POL_TLS_INSECURE=1' in str(r) and 'client certificate' in str(r), repr(r))
            refused('a caller context with CERT_REQUIRED but the hostname check OFF (Isle finding 3)', system_kind='self', system_name='board',
                    method='GET', url='https://api/x', timeout=3, lib='urllib', context=foreign(cert_none=False, hostname=False))
            ok_ctx = ssl.create_default_context()
            outbound.http_request('self', 'board', 'GET', 'https://api/x', timeout=3, lib='urllib', context=ok_ctx)
            check('seam: a caller VERIFYING context is kept as is', seen.get('context') is ok_ctx)
        if ca:
            with env(POL_TLS_CA=ca) as err:
                refused('a caller hostname-off context under POL_TLS_CA', system_kind='self', system_name='board', method='GET',
                        url='https://api/x', timeout=3, lib='urllib', context=foreign(cert_none=False, hostname=False))
        # under the bypass: kept, but ANNOUNCED through the policy (Isle finding 2)
        with env(POL_TLS_INSECURE='1') as err:
            raw = foreign()
            outbound.http_request('self', 'board', 'GET', 'https://api/x', timeout=3, lib='urllib', context=raw)
            check('seam under the bypass: a caller CERT_NONE context is kept', seen.get('context') is raw)
            out = err.getvalue()
            check('seam under the bypass: … and announced (run notice + url)', 'OFF for this process' in out and 'caller-supplied unverified context): https://api/x' in out, out)
            hn = foreign(cert_none=False, hostname=False)
            outbound.http_request('self', 'board', 'GET', 'https://api/y', timeout=3, lib='urllib', context=hn)
            check('seam under the bypass: a hostname-off context is kept and announced', seen.get('context') is hn and 'https://api/y' in err.getvalue(), err.getvalue())
        # the policy's own contexts are honoured; the inspection one is refused for EVERY send (Isle finding 1)
        with env() as err:
            u = tls_policy.unverified_context('join flow, dev posture', 'https://peer')
            outbound.http_request('peer', 'kitchen', 'POST', 'https://peer/join', data=b'{}', timeout=3, lib='urllib', context=u)
            check('seam: an EXPLICIT policy-built context is honoured (dev join keeps working)', seen.get('context') is u)
            refused('the inspection context on a bare GET', system_kind='other', system_name='cert', method='GET', url='https://host/',
                    timeout=3, lib='urllib', context=tls_policy.inspection_context())
            refused('the inspection context on a GET with headers= and data= NAMED parameters (Isle repro)', system_kind='other',
                    system_name='cert', method='GET', url='https://host/', headers={'Authorization': 'test-only'}, data=b'x',
                    timeout=3, lib='urllib', context=tls_policy.inspection_context())
            req = ur.Request('https://host/', method='HEAD')
            refused('the inspection context on a pre-built HEAD Request', system_kind='other', system_name='cert', method='HEAD', url=req,
                    timeout=3, lib='urllib', context=tls_policy.inspection_context())
            refused('the inspection context on a POST', system_kind='other', system_name='cert', method='POST', url='https://host/',
                    timeout=3, lib='urllib', context=tls_policy.inspection_context())
    finally:
        ur.urlopen = real
    try:
        import requests
    except ImportError:
        check('requests path', True, 'requests not installed'); return
    rseen = {}
    rreal = requests.request

    def rfake(method, url, **kw):
        rseen.clear(); rseen.update(kw); return 'R'
    requests.request = rfake
    try:
        with env() as err:
            outbound.http_request('keycloak', 'Polari', 'GET', 'https://kc/', timeout=3, lib='requests')
            check('requests default: verify untouched (library default = verified)', 'verify' not in rseen, repr(rseen))
            outbound.http_request('keycloak', 'Polari', 'GET', 'https://kc/', timeout=3, lib='requests', verify=False)
            check('requests: verify=False from a caller is replaced (verified default)', 'verify' not in rseen, repr(rseen))
            check('requests: … and said', 'outbound keycloak/Polari' in err.getvalue(), err.getvalue())
        with env(POL_TLS_INSECURE='1') as err:
            outbound.http_request('keycloak', 'Polari', 'GET', 'https://kc/', timeout=3, lib='requests')
            check('requests insecure: verify False', rseen.get('verify') is False, repr(rseen))
        with env(POL_TLS_INSECURE='1') as err:
            outbound.http_request('keycloak', 'Polari', 'GET', 'https://kc/', timeout=3, lib='requests', verify=False)
            check('requests under the bypass: a caller verify=False is normalized through the policy and ANNOUNCED (Isle finding 2)',
                  rseen.get('verify') is False and 'OFF for this process' in err.getvalue() and 'https://kc/' in err.getvalue(), err.getvalue())
            outbound.http_request('keycloak', 'Polari', 'GET', 'https://kc/', timeout=3, lib='requests', verify=False, cert=('c.pem', 'k.pem'))
            check('requests: the caller cert= (client certificate) is kept', rseen.get('cert') == ('c.pem', 'k.pem'), repr(rseen))
        with env() as err:
            outbound.http_request('keycloak', 'Polari', 'GET', 'https://kc/', timeout=3, lib='requests', verify='/some/ca.pem')
            check('requests: a caller CA path is the caller\'s verifying choice, kept', rseen.get('verify') == '/some/ca.pem', repr(rseen))
        if ca:
            with env(POL_TLS_CA=ca) as err:
                outbound.http_request('keycloak', 'Polari', 'GET', 'https://kc/', timeout=3, lib='requests')
                check('requests cacert: verify = the file', rseen.get('verify') == ca, repr(rseen))
    finally:
        requests.request = rreal


#: every file (relative to ROOT) that may contain an unverified-TLS construct, with the reason; nothing else may.
ALLOWLIST = {
    'polariApiServer/tls_policy.py': 'the ONE helper',
    'accessControl/store_identity.py': "cert_reqs='CERT_NONE' only when store.secure is False, i.e. plain http: no TLS at all",
    'modules/iso/custom/iso_autoinstall.py': 'a bash heredoc that runs on the TARGET machine at first boot, before any framework exists there; the trust is the isle fingerprint, not TLS',
}
PATTERN = re.compile(r"_create_unverified_context|CERT_NONE|check_hostname\s*=\s*False|verify\s*=\s*False")
SKIP_DIRS = ('node_modules', 'tests', 'moduleService/dyn_proofs', '.git', '__pycache__')


def test_audit():
    hits = {}
    for dirpath, dirs, files in os.walk(ROOT):
        rel = os.path.relpath(dirpath, ROOT)
        if any(rel == d or rel.startswith(d + os.sep) for d in SKIP_DIRS) or any(part in ('node_modules', '__pycache__', '.git') for part in rel.split(os.sep)):
            continue
        for fn in files:
            if not fn.endswith('.py') or 'selftest' in fn:
                continue
            path = os.path.join(dirpath, fn); r = os.path.relpath(path, ROOT)
            with open(path, errors='replace') as fh:
                for i, line in enumerate(fh, 1):
                    if PATTERN.search(line.split('#', 1)[0]):
                        hits.setdefault(r, []).append(i)
    new = sorted(set(hits) - set(ALLOWLIST)); gone = sorted(set(ALLOWLIST) - set(hits))
    check('audit: no unverified TLS outside tls_policy and the named allowlist', not new,
          '; '.join(f'{f}:{",".join(map(str, hits[f]))}' for f in new))
    check('audit: every allowlisted file still has its construct (the list describes the tree)', not gone, repr(gone))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        for fn in (lambda: test_modes(tmp), lambda: test_seam(tmp), test_audit):
            try:
                fn()
            except Exception as exc:    # noqa: BLE001
                FAILED.append(f'{getattr(fn, "__name__", "case")} BLEW UP :: {type(exc).__name__}: {exc}')
    for line in FAILED:
        print('FAIL', line)
    print(f'selftest_tls_policy: {len(PASSED)}/{len(PASSED) + len(FAILED)}')
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
