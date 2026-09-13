"""
@module security.custom.security_notices

Notices a USER should see (his ask 2026-09-13: tell people when the certificate on their app has expired
and that it needs renewing, when auto-renew did not or could not do it). Sources, in order of truth:
  1. a LIVE probe of this instance's own public hosts (the proxy's certificate as a browser sees it) —
     the backend cannot read the proxy's files, so it asks the proxy over TLS like a client would;
  2. the latest posted audit run's `certs` controls (edge cert days left, auto-renew installed);
  3. the ServiceIdentity rows (the cert manifests + ca/issued on a checkout).
Every notice carries the action: `pol cert renew` now, and `pol cert auto-renew install` so it never
recurs. Levels: error (expired), warning (expiring within 14 days), info (auto-renew absent).
"""
import os
import socket
import ssl
import time

WARN_DAYS = 14


def public_hosts():
    """The hosts this instance serves, from the environment the compose files set."""
    hosts = []
    for var in ('POLARI_PUBLIC_HOSTS', 'CORS_ORIGINS'):
        for h in (os.environ.get(var) or '').split(','):
            h = h.strip().replace('https://', '').replace('http://', '').split('/')[0]
            if h and h not in hosts and h != 'localhost':
                hosts.append(h)
    dom = os.environ.get('PROD_DOMAIN')
    if dom:
        for h in (dom, f'prf.{dom}', f'api.prf.{dom}'):
            if h not in hosts:
                hosts.append(h)
    return hosts


def probe_host(host, port=443, timeout=4.0):
    """Days left on the certificate the host serves, as a client sees it (no verification: we want the
    expiry even of a self-signed or expired cert). None when unreachable."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as s:
                der = s.getpeercert(binary_form=True)
    except (OSError, ssl.SSLError, socket.timeout):
        return None
    try:
        from cryptography import x509
        cert = x509.load_der_x509_certificate(der)
        not_after = cert.not_valid_after_utc if hasattr(cert, 'not_valid_after_utc') else cert.not_valid_after
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc) if not_after.tzinfo else datetime.datetime.utcnow()
        issuer = ','.join(a.value for a in cert.issuer if a.oid._name in ('organizationName', 'commonName'))
        return {'host': host, 'not_after': not_after.strftime('%Y-%m-%d'), 'days_left': (not_after - now).days, 'issuer': issuer}
    except Exception:
        return {'host': host, 'not_after': '', 'days_left': None, 'issuer': ''}


def notices_from(probes=None, audit_controls=None, identities=None, hosts=None):
    """Reduce the three sources to a short list of notices; probes win over rows for the same host."""
    out = []
    seen = set()
    for p in probes or []:
        if not p or p.get('days_left') is None:
            continue
        seen.add(p['host'])
        if p['days_left'] < 0:
            out.append({'level': 'error', 'code': 'cert-expired', 'host': p['host'], 'days_left': p['days_left'],
                        'title': f"The certificate for {p['host']} expired {abs(p['days_left'])} day(s) ago",
                        'text': 'Browsers will refuse or warn on this address until it is renewed.',
                        'action': 'On the machine that runs the proxy: pol cert renew — then pol cert auto-renew install so it never recurs.'})
        elif p['days_left'] <= WARN_DAYS:
            out.append({'level': 'warning', 'code': 'cert-expiring', 'host': p['host'], 'days_left': p['days_left'],
                        'title': f"The certificate for {p['host']} expires in {p['days_left']} day(s)",
                        'text': 'Auto-renew should replace it before then; if this notice is still here in a few days, renew by hand.',
                        'action': 'pol cert renew · check: pol cert auto-renew status'})
    ctl = {c.get('control'): c for c in (audit_controls or [])}
    ar = ctl.get('auto-renew')
    if ar and ar.get('status') == 'fail':
        out.append({'level': 'info', 'code': 'auto-renew-absent', 'host': '', 'days_left': None,
                    'title': 'Certificate auto-renew is not installed on this machine',
                    'text': 'Certificates will expire silently unless renewed by hand.', 'action': 'pol cert auto-renew install (a weekly cron running ca/renew.sh)'})
    edge = ctl.get('edge-cert')
    if edge and edge.get('status') == 'fail' and not any(n['code'] == 'cert-expired' for n in out):
        out.append({'level': 'error', 'code': 'cert-expired', 'host': 'the edge', 'days_left': None, 'title': 'The edge certificate has expired (from the last audit run)',
                    'text': edge.get('evidence', ''), 'action': 'pol cert renew · pol cert auto-renew install'})
    for r in identities or []:
        if r.get('issued') and isinstance(r.get('days_left'), int) and r['days_left'] < 0 and r.get('service') not in seen:
            out.append({'level': 'warning', 'code': 'internal-cert-expired', 'host': r['service'], 'days_left': r['days_left'],
                        'title': f"Internal certificate {r['service']} ({r.get('manifest', '')}) expired {abs(r['days_left'])} day(s) ago",
                        'text': 'Services that verify each other with it will fail to connect.', 'action': 'pol cert renew (internal certs are renewed by the same script)'})
    for h in hosts or []:
        if h not in seen and not any(n.get('host') == h for n in out):
            out.append({'level': 'info', 'code': 'host-unreachable', 'host': h, 'days_left': None, 'title': f'{h} did not answer a TLS probe from inside the instance',
                        'text': 'Nothing is known about its certificate from here.', 'action': 'pol prod status shows the certificate from the outside'})
    return out


def notices(manager=None, do_probe=True):
    hosts = public_hosts()
    probes = [probe_host(h) for h in hosts] if do_probe else []
    controls = []
    try:
        from security.custom.security_audit_feed import latest_runs
        runs = latest_runs(manager) if manager is not None else {}
        if runs:
            controls = max(runs.values(), key=lambda r: r['ran_at'])['controls']
    except Exception:
        pass
    identities = []
    try:
        from security.custom.security_network_rows import service_identity_rows
        identities = service_identity_rows()
    except Exception:
        pass
    items = notices_from(probes, controls, identities, hosts)
    worst = 'error' if any(n['level'] == 'error' for n in items) else ('warning' if any(n['level'] == 'warning' for n in items) else ('info' if items else 'ok'))
    return {'ok': True, 'checked_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'hosts': hosts, 'probes': [p for p in probes if p],
            'level': worst, 'notices': items, 'auto_renew': 'pol cert auto-renew install|status|remove — a weekly cron running ca/renew.sh (Let\'s Encrypt and internal certs)'}
