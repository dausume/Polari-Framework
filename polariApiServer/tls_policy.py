"""
polariApiServer.tls_policy — ONE TLS policy for every HTTPS call the backend makes (user ruling 2026-11-07, the
backend half of polari-cli lib/tls.sh; Isle review limits 2026-11-07).

    from polariApiServer import tls_policy
    context=tls_policy.context(url)            # for urllib: None = the system trust store
    verify=tls_policy.requests_verify(url)     # for requests: True | <cafile> | False

The same two names as the CLI, read from the environment at call time:

  default              verified against the system trust store (an isle mounts its generated trust; the
                       container's SSL_CERT_FILE / REQUESTS_CA_BUNDLE keep working as before).
  POL_TLS_CA=<pem>     a PEM file to trust INSTEAD (self-signed / private deployments): the VERIFYING answer.
                       Hostname verification stays on. A missing file refuses in words (RuntimeError).
  POL_TLS_INSECURE=1   an explicit, announced bypass for intended non-isle lightweight / dev settings: an
                       unverified context, plus "[WARN] TLS verification OFF ..." once per process at first use and
                       once per distinct URL (contexts are built once and reused, so the promise is per distinct
                       message, not per request).
  both set             POL_TLS_CA wins and the ignored bypass is said once.
  aliases              POLARI_INSECURE=1 means POL_TLS_INSECURE=1 (one knob, one name).

This module is the ONLY place the backend may build an unverified context: `unverified_context(reason, url)` for the
two explicit per-request choices that exist by design (the dev-posture join flow, which records a SecurityEvent;
the API profiler's verify_ssl=False), each announced with its reason; and `inspection_context()` for reading a peer
certificate's expiry (security_notices.probe_host), which never sends data and is said so. selftest_tls_policy.py
audits the tree: any other _create_unverified_context / CERT_NONE / check_hostname = False / verify=False fails
by path unless it is on the named allowlist with its reason.

Never auto-enabled: the generated Isle provider config, enrollment and CA rotation do not set these knobs.
"""
import os
import ssl
import sys

_TRUE = ('1', 'true', 'yes', 'on')
_said = set()


def _say(msg):
    if msg not in _said:
        _said.add(msg)
        print(msg, file=sys.stderr, flush=True)


def _on(name):
    return os.environ.get(name, '') in _TRUE


def mode():
    """'verified' | 'cacert' | 'insecure' for the current environment (POLARI_INSECURE is the alias)."""
    if _on('POLARI_INSECURE') and os.environ.get('POL_TLS_INSECURE', '') == '':
        os.environ['POL_TLS_INSECURE'] = '1'
    if os.environ.get('POL_TLS_CA'):
        return 'cacert'
    if _on('POL_TLS_INSECURE'):
        return 'insecure'
    return 'verified'


def _announce_once():
    if not os.environ.get('POL_TLS_ANNOUNCED'):
        _say('[WARN] TLS verification OFF for this process (POL_TLS_INSECURE=1): every HTTPS call is unverified')
        os.environ['POL_TLS_ANNOUNCED'] = '1'


#: the kinds of unverified context this module builds; the seam honours THESE and overrides any other
POLICY, EXPLICIT, INSPECTION = 'policy', 'explicit', 'inspection'


def _insecure(kind):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx._polari_tls = kind          # the mark the seam checks (outbound._apply_tls_policy)
    return ctx


def built_here(ctx):
    """'policy' | 'explicit' | 'inspection' when `ctx` was built by this module, else None."""
    return getattr(ctx, '_polari_tls', None)


def context(url=''):
    """The ssl context for an outbound HTTPS call under the policy: None (system store), a verifying context
    trusting POL_TLS_CA, or the announced unverified one."""
    m = mode()
    if m == 'cacert':
        ca = os.environ['POL_TLS_CA']
        if _on('POL_TLS_INSECURE'):
            _say('[WARN] POL_TLS_INSECURE ignored: POL_TLS_CA=%s is set and verification against it wins' % ca)
        if not os.path.isfile(ca):
            raise RuntimeError('[FAIL] POL_TLS_CA=%s is not a readable PEM file' % ca)
        return ssl.create_default_context(cafile=ca)
    if m == 'insecure':
        _announce_once()
        _say('[WARN] TLS verification OFF (POL_TLS_INSECURE=1): %s' % (url or 'urllib'))
        return _insecure(POLICY)
    return None


def requests_verify(url=''):
    """The `verify=` value for the requests library under the policy: True | <cafile> | False (announced)."""
    ctx = context(url)
    if ctx is None:
        return True
    if ctx.verify_mode == ssl.CERT_NONE:
        return False
    return os.environ['POL_TLS_CA']


def is_unverified(ctx):
    """True when `ctx` is an ssl context that does not verify the peer."""
    return isinstance(ctx, ssl.SSLContext) and ctx.verify_mode == ssl.CERT_NONE


def unverified_context(reason, url=''):
    """The ONE constructor for an explicitly chosen unverified context, announced with its reason. POL_TLS_CA still
    wins (the caller asked to skip verification; a file to verify against is the safer explicit choice)."""
    if mode() == 'cacert':
        _say('[WARN] %s: unverified context NOT built, POL_TLS_CA=%s is set and verification against it wins'
             % (reason, os.environ['POL_TLS_CA']))
        return context(url)
    _say('[WARN] TLS verification OFF (%s): %s' % (reason, url or 'urllib'))
    return _insecure(EXPLICIT)


def inspection_context():
    """For READING a peer's certificate (expiry, issuer) as any client would see it, including a self-signed or
    expired one: no verification by design, and no data is ever sent on that socket. The outbound seam refuses it
    for anything but a bare GET/HEAD with no body and no credentials, so it can never become a general bypass."""
    return _insecure(INSPECTION)
