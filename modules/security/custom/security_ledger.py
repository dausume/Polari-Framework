"""
@module security.custom.security_ledger

AppSecurityRecord — ONE row per app (module id or fixed piece) for the scenario it runs in: which of the
automation steps it has been through and with what result, steps complete / total, and the first step that
blocks. Derived from the manifests (stanza + conform), the render manifests (MAC/DAC rendered), the latest
audit run (loaded / enforced / surface applied / audit verdict), the proxy snippets and the app rows. Never
typed; refreshed whenever the seed or the API recomputes it.
"""
import json
import time

from security.custom.security_facts import load_scenario, scenario_names
from security.custom.security_os_rows import _manifests, _stanza_hash, render_manifest
from security.custom.security_network_rows import proxy_snippet_rows

STEPS = ('stanza_declared', 'stanza_conforms', 'mac_rendered', 'mac_loaded', 'mac_enforced', 'dac_rendered', 'surface_applied',
         'proxy_snippets', 'channels_declared', 'content_policy', 'browser_policy', 'hardware_trial')


def _conforms(manifest):
    try:
        from moduleService.manifests import security_findings
        return not security_findings(manifest.get('security'))
    except Exception:
        sec = manifest.get('security') or {}
        return bool(sec) and sec.get('profile') in ('web-app', 'worker', 'gateway', 'vpn-gateway', 'hardware-extension')


def app_security_records(applied=None, audit_verdicts=None, channels=None, content_policies=None):
    applied = applied or {}
    audit_verdicts = audit_verdicts or {}
    channels = channels or []
    content_policies = content_policies or []
    manifests = _manifests()
    snippets = {}
    for s in proxy_snippet_rows():
        snippets.setdefault(s['app'], []).append(s)
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    rows = []
    for scn in scenario_names():
        sc = load_scenario(scn)
        rm = render_manifest(scn)
        if not sc:
            continue
        rendered = {x['name'] for x in ((rm or {}).get('apps', []) + (rm or {}).get('fixed', []))}
        folded = set((rm or {}).get('folded', []))
        mac_mode = (applied.get(scn) or {}).get('polari-apparmor', '')
        surface = (applied.get(scn) or {}).get('polari-surface', '')
        apps = [(mid, 'polari-app' if (m.get('app') or {}).get('kind') not in ('hardware-app', 'hardware-extension-app') else 'hardware-app', m) for mid, m in manifests.items()]
        apps += [(f['name'], 'fixed-piece', {'security': f, 'app': {}}) for f in sc['fixed']]
        for app, kind, m in apps:
            sec = m.get('security') or {}
            hw = kind == 'hardware-app'
            r = {'name': f'{scn}:{app}', 'app': app, 'kind': kind, 'scenario': scn,
                 'stanza_declared': bool(sec), 'stanza_hash': _stanza_hash(sec), 'stanza_conforms': 'yes' if (kind == 'fixed-piece' or _conforms(m)) else 'no',
                 'mac_rendered': app in rendered or app in folded, 'mac_mode': mac_mode or ('rendered' if (app in rendered or app in folded) else 'absent'),
                 'mac_enforced': mac_mode == 'enforce', 'dac_rendered': app in rendered or app in folded, 'surface_applied': surface in ('enforce', 'live'),
                 'proxy_snippets': f"{sum(1 for s in snippets.get(app, []) if s['state'] != 'absent')}/{len(snippets.get(app, [])) or 1}",
                 'channels_declared': sum(1 for c in channels if app in (c.get('to_app'), c.get('from_app'))),
                 'content_policy': 'derived' if any(c.get('app') == app for c in content_policies) else 'none',
                 'browser_policy': 'derived' if app in ('prf-frontend', 'pol-hub', 'psc-frontend', 'prf-isle-frontend') else 'n/a',
                 'hardware_trial': 'pending' if hw else 'n/a', 'audit_verdict': audit_verdicts.get(scn, ''), 'last_refresh': now}
            done = {'stanza_declared': r['stanza_declared'], 'stanza_conforms': r['stanza_conforms'] == 'yes', 'mac_rendered': r['mac_rendered'],
                    'mac_loaded': bool(mac_mode), 'mac_enforced': r['mac_enforced'], 'dac_rendered': r['dac_rendered'], 'surface_applied': r['surface_applied'],
                    'proxy_snippets': not r['proxy_snippets'].startswith('0/'), 'channels_declared': r['channels_declared'] > 0,
                    'content_policy': r['content_policy'] != 'none', 'browser_policy': r['browser_policy'] in ('derived', 'observed', 'enforced'),
                    'hardware_trial': r['hardware_trial'] in ('n/a', 'accepted')}
            total = len(STEPS) - (0 if r['browser_policy'] != 'n/a' else 1) - (0 if hw else 1)
            complete = sum(1 for k in STEPS if done[k] and not (k == 'browser_policy' and r['browser_policy'] == 'n/a') and not (k == 'hardware_trial' and not hw))
            r['steps_total'] = total
            r['steps_complete'] = complete
            r['blocking'] = next((k for k in STEPS if not done[k] and not (k == 'browser_policy' and r['browser_policy'] == 'n/a') and not (k == 'hardware_trial' and not hw)), '')
            rows.append(r)
    return rows


def ledger_summary(rows):
    by = {}
    for r in rows:
        b = by.setdefault(r['scenario'], {'apps': 0, 'complete': 0, 'blocking': {}})
        b['apps'] += 1
        b['complete'] += 1 if r['steps_complete'] == r['steps_total'] else 0
        if r['blocking']:
            b['blocking'][r['blocking']] = b['blocking'].get(r['blocking'], 0) + 1
    return [{'scenario': k, 'apps': v['apps'], 'fully_complete': v['complete'], 'most_common_block': max(v['blocking'], key=v['blocking'].get) if v['blocking'] else ''} for k, v in by.items()]
