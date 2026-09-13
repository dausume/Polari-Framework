"""
@module security.custom.security_network_rows

The Network domain's rows, DERIVED: ProxyConfig from the proxy templates' text (server names, upstreams,
TLS versions, HSTS, headers, rate limits); ProxySnippet = the per-app security/proxy/*.conf.j2 files
(absent today, so the rows say so per app); ServiceIdentity from the cert manifests + ca/issued;
FirewallRuleSet from the rendered chains per scenario + the audit's applied flag.
"""
import glob
import json
import os
import re
import subprocess

from security.custom.security_facts import SUITE, scenario_names

PROXY = os.path.join(SUITE, 'pol-proxy')
MODULES = os.path.join(SUITE, 'polari-rf-node', 'polari-framework', 'modules')
OUT = os.path.join(SUITE, 'os-security', 'out')
CERT_MANIFESTS = (('suite', os.path.join(SUITE, 'ca', 'cert-manifest.conf'), os.path.join(SUITE, 'ca', 'issued')),
                  ('rf-node', os.path.join(SUITE, 'polari-rf-node', 'ca', 'cert-manifest.conf'), os.path.join(SUITE, 'polari-rf-node', 'ca', 'issued')))


def proxy_config_rows(guard=None):
    guard = guard or {}
    rows = []
    for p in sorted(glob.glob(os.path.join(PROXY, 'nginx.*.conf.template')) + glob.glob(os.path.join(PROXY, 'nginx.*.conf'))):
        env = os.path.basename(p).split('.')[1]
        txt = open(p, encoding='utf-8', errors='replace').read()
        names = sorted({n for line in re.findall(r'server_name\s+([^;]+);', txt) for n in line.split()})
        ups = sorted(set(re.findall(r'set\s+\$(\w+)\s', txt)) | set(re.findall(r'proxy_pass\s+\$?(\w+)', txt)))
        tls = ' '.join(sorted(set(re.findall(r'ssl_protocols\s+([^;]+);', txt))))
        hsts = 'Strict-Transport-Security' in txt or 'HSTS_HEADER' in txt   # ${HSTS_HEADER}: set by pol prod once the edge is public
        headers = sorted(set(re.findall(r'add_header\s+([\w-]+)', txt)))
        rl = sorted(set(re.findall(r'limit_req_zone[^;]*zone=(\w+)', txt)))
        rows.append({'name': f'suite-proxy:{env}', 'route': 'suite-proxy', 'env': env, 'template': os.path.relpath(p, SUITE),
                     'rendered': f'.generated/nginx.{env}.conf', 'server_names': ', '.join(names)[:400], 'upstreams': ', '.join(ups)[:300],
                     'tls_versions': tls or '(not set: nginx default)', 'hsts': hsts, 'headers': ', '.join(headers)[:300], 'rate_limits': ', '.join(rl),
                     'guard_verdict': guard.get(env, 'not-run'), 'snippets_included': 0})
    rows.append({'name': 'isle-agent', 'route': 'isle-agent', 'env': 'isle', 'template': 'Isle-Mesh (the agent renders from registry.json)', 'rendered': '/etc/nginx/configs (in the agent)',
                 'server_names': '<app>.isle per registered app', 'upstreams': 'per app', 'tls_versions': 'isle CA leaf per domain', 'hsts': False,
                 'headers': '', 'rate_limits': '', 'guard_verdict': "isle-core's half", 'snippets_included': 0})
    return rows


def proxy_snippet_rows():
    rows = []
    for p in sorted(glob.glob(os.path.join(MODULES, '*', 'polari-app.json'))):
        app = os.path.basename(os.path.dirname(p))
        sdir = os.path.join(os.path.dirname(p), 'security', 'proxy')
        found = sorted(glob.glob(os.path.join(sdir, '*.conf.j2')))
        if found:
            for f in found:
                scope = os.path.basename(f).split('.')[0]
                rows.append({'name': f'{app}:{scope}', 'app': app, 'scope': scope, 'kind': 'location', 'template': os.path.relpath(f, SUITE), 'rendered': '',
                             'enabled': True, 'order': 100, 'requires': '', 'state': 'rendered' if os.path.getsize(f) else 'absent'})
        else:
            rows.append({'name': f'{app}:api', 'app': app, 'scope': 'api', 'kind': 'location', 'template': f'modules/{app}/security/proxy/api.conf.j2', 'rendered': '',
                         'enabled': False, 'order': 100, 'requires': '', 'state': 'absent'})
    return rows


def _cert_dates(path):
    try:
        out = subprocess.run(['openssl', 'x509', '-in', path, '-noout', '-enddate'], capture_output=True, text=True, timeout=10).stdout.strip()
        end = out.split('=', 1)[1] if '=' in out else ''
        import datetime
        d = datetime.datetime.strptime(end, '%b %d %H:%M:%S %Y %Z')
        return d.strftime('%Y-%m-%d'), (d - datetime.datetime.utcnow()).days
    except Exception:
        return '', -1


def service_identity_rows():
    rows = []
    for label, mf, issued in CERT_MANIFESTS:
        if not os.path.isfile(mf):
            continue
        for line in open(mf, encoding='utf-8'):
            line = line.strip()
            if not line or line.startswith('#') or '|' not in line:
                continue
            parts = [x.strip() for x in line.split('|')]
            if len(parts) < 3:
                continue
            svc, issuer, sans = parts[0], parts[1], parts[2]
            crt = os.path.join(issued, svc + '.crt')
            present = os.path.isfile(crt)
            not_after, days = _cert_dates(crt) if present else ('', -1)
            rows.append({'name': f'{label}:{svc}', 'service': svc, 'manifest': os.path.relpath(mf, SUITE), 'issuer': issuer, 'hostnames': sans[:400],
                         'path': os.path.relpath(crt, SUITE) if present else '', 'issued': present, 'not_after': not_after, 'days_left': days,
                         'verifies': 'browsers / peers by the suite root or the public CA', 'mtls_required_by': ''})
    return rows


def firewall_rule_rows(applied=None):
    applied = applied or {}
    rows = []
    for scn in scenario_names():
        for chain, fname in (('docker-user', 'docker-user.sh'), ('ufw', 'ufw.sh')):
            p = os.path.join(OUT, scn, fname)
            if not os.path.isfile(p):
                continue
            txt = open(p, encoding='utf-8', errors='replace').read()
            rules = [l.strip() for l in txt.splitlines() if l.strip() and not l.strip().startswith('#') and (l.strip().startswith(('iptables', 'ufw', 'nft')))]
            live = (applied.get(scn) or {}).get(chain, '')
            rows.append({'name': f'{scn}:{chain}', 'scenario': scn, 'chain': chain, 'rules': '\n'.join(rules)[:1500], 'rule_count': len(rules),
                         'applied': live or 'rendered only (printed unless --enforce)', 'sources_resolved': 'admin-lan' not in txt and 'isle-lan' not in txt,
                         'artifact': os.path.relpath(p, SUITE)})
    return rows
