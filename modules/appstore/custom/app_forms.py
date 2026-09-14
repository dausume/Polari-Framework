"""
@module appstore.custom.app_forms

The two FORMS of every app (his rulings 2026-09-14) and the install-time refusals:

  install  — the app itself: `polari-app-<m>[-offline]` (the module payload, staged for admission; the isle
             hosts it). Hardware apps and their expansions carry a `preinst` that REFUSES before anything is
             installed: a hardware app on a lightweight (docker-swarm) isle, an expansion without the hardware
             app it expands.
  access   — the app's SHELL: `polari-access-<m>[-offline]` (kind access-app): a launcher that opens the app the
             isle hosts. On first open it FINDS the app (the core's /api/access answer, then the conventional
             .isle names); when it cannot, it asks the person to pick from the isle's .isle addresses and remembers.
             Offline flavour carries the shell runtime deb (polari-shell-core) when the instance stages it.

Groups for the pages: software (library / polari-app / isle-app / suite-app), hardware (hardware-app), and each
hardware app's EXPANSIONS (hardware-extension-app with `extends`) as a subsection under it.

@consumers
  - appstore.custom.app_deb_builder (generate form='access', the preinst), appstore.apps_api, appstore.app_debs_page
  - appstore.apps_api_selftest
"""
import json
import os
import re

FORMS = ('install', 'access')
SOFTWARE_KINDS = ('library', 'polari-app', 'isle-app', 'suite-app', 'access-app', '')
HARDWARE_KINDS = ('hardware-app',)
EXPANSION_KINDS = ('hardware-extension-app',)

#: the sentences the debs print (his words), one place
LIGHTWEIGHT_ISLE_REFUSAL = ('the isle you are on is a lightweight isle, based on docker swarm, you need to install a '
                            'full isle version of Polari to install hardware apps')
NOT_HARDWARE_TIER_REFUSAL = ('this isle member is not the hardware tier (no /dev/kvm or libvirt here) — join the isle '
                             'as Hardware on a machine with virtualization, or install this app there')
EXPANSION_REFUSAL = '{module} expands {base}, which is not installed here — install {base} first, then this expansion'


def _framework_root():
    try:
        from moduleService.module_registry import _framework_root
        return _framework_root()
    except Exception:
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def manifest_app(module, root=None, entry=None):
    """The app block of modules/<m>/polari-app.json (kind, title, extends, agentTier, description) — the REGISTRY
    entry's `kind` is 'official'/'external', not the app kind. Absent manifest → a plain polari-app."""
    root = root or _framework_root()
    rel = (entry or {}).get('path') or f'modules/{module}'
    out = {'module': module, 'kind': 'polari-app', 'title': module, 'extends': '', 'agentTier': 'member', 'description': (entry or {}).get('description', '')}
    try:
        with open(os.path.join(root, rel, 'polari-app.json'), encoding='utf-8') as fh:
            m = json.load(fh)
        app = m.get('app') or {}
        out.update({'kind': app.get('kind') or 'polari-app', 'title': m.get('title') or module, 'extends': app.get('extends') or '',
                    'agentTier': app.get('agentTier') or 'member', 'description': m.get('description') or out['description']})
    except Exception:
        pass
    return out


def group_of(app):
    kind = (app or {}).get('kind', '')
    if kind in HARDWARE_KINDS:
        return 'hardware'
    if kind in EXPANSION_KINDS:
        return 'expansion'
    return 'software'


def grouped(modules, root=None):
    """{'software': [(module, entry, app)], 'hardware': [...], 'expansions': {base: [(module, entry, app)]},
    'orphans': [...]} — expansions nest under the hardware app they extend (by module id or dashed name)."""
    apps = {m: manifest_app(m, root, e) for m, e in modules.items()}
    out = {'software': [], 'hardware': [], 'expansions': {}, 'orphans': []}
    ids = {m: m for m in modules} | {m.replace('_', '-'): m for m in modules}
    for m, e in sorted(modules.items()):
        a = apps[m]
        g = group_of(a)
        if g == 'expansion':
            base = ids.get(a['extends'], '')
            (out['expansions'].setdefault(base, []) if base else out['orphans']).append((m, e, a))
        else:
            out[g].append((m, e, a))
    return out


# --- install-form refusals (maintainer scripts) -------------------------------------------------------------

def preinst_for(module, app):
    """The preinst of an INSTALL-form deb for a hardware app / expansion: refuse BEFORE anything is installed, and
    say why in his words. Software apps carry none. POLARI_ALLOW_POLARI_SIDE=1 lets a developer stage the Polari
    side anyway (the 2026-09-12 ruling: useful for development; the notice still says it will not work)."""
    kind = app.get('kind', '')
    if kind not in HARDWARE_KINDS + EXPANSION_KINDS:
        return ''
    base = (app.get('extends') or '').replace('_', '-')
    lines = ['#!/bin/sh', '# Polari install-time refusals (his rulings 2026-09-14) — nothing is installed when this exits non-zero',
             'set -e', '[ "${POLARI_ALLOW_POLARI_SIDE:-0}" = 1 ] && { echo "POLARI_ALLOW_POLARI_SIDE=1: staging the Polari side only (development); the hardware half will not work here"; exit 0; }',
             'full_isle() { [ -d /etc/isle-mesh ] && [ -f /etc/isle-mesh/ca/isle-root.crt -o -d /etc/isle-mesh/ca ]; }',
             'swarm_only() { command -v docker >/dev/null 2>&1 && [ "$(docker info --format "{{.Swarm.LocalNodeState}}" 2>/dev/null)" = active ] && ! full_isle; }',
             'hardware_tier() { [ -e /dev/kvm ] && { command -v virsh >/dev/null 2>&1 || systemctl list-unit-files libvirtd.service >/dev/null 2>&1; }; }']
    if kind in HARDWARE_KINDS:
        lines += [f'if swarm_only || ! full_isle; then echo "REFUSED: {LIGHTWEIGHT_ISLE_REFUSAL}" >&2; exit 1; fi',
                  f'if ! hardware_tier; then echo "REFUSED: {NOT_HARDWARE_TIER_REFUSAL}" >&2; exit 1; fi']
    else:
        msg = EXPANSION_REFUSAL.format(module=module, base=app.get('extends') or '?')
        lines += [f'if ! dpkg -s polari-app-{base} >/dev/null 2>&1 && ! dpkg -s polari-app-{base}-offline >/dev/null 2>&1 && ! [ -d /var/lib/polari/apps/{(app.get("extends") or "").replace("-", "_")} ]; then echo "REFUSED: {msg}" >&2; exit 1; fi',
                  f'if swarm_only || ! full_isle; then echo "REFUSED: {LIGHTWEIGHT_ISLE_REFUSAL}" >&2; exit 1; fi']
    lines.append('exit 0')
    return '\n'.join(lines) + '\n'


# --- the access form (the shell) ------------------------------------------------------------------------------

def access_deb_name(module, flavor='online'):
    name = 'polari-access-' + module.lower().replace('_', '-')
    return name + ('-offline' if flavor == 'offline' else '') if re.match(r'^[a-z0-9][a-z0-9+.-]+$', name) else ''


def access_url_candidates(module, app):
    """Where an app is reached on an isle, most likely first: an isle-app lives at <name>.isle; a Polari app is a
    page of the core's Polari at polari.isle. The core's /api/access/<m> answers the same from its registry."""
    dashed = module.replace('_', '-')
    if app.get('kind') == 'isle-app':
        return [f'https://{dashed}.isle', f'https://polari.isle/app/{module}']
    return [f'https://polari.isle/app/{module}', f'https://polari.isle/app/{dashed}', f'https://{dashed}.isle']   # app/:name = the app home route


def open_script(module, app):
    """/usr/share/polari-access/<m>/open.sh — finds the app, remembers the address, opens the shell on it."""
    title = app.get('title') or module
    cands = ' '.join(access_url_candidates(module, app))
    return f'''#!/bin/bash
# open.sh — open "{title}" through the Polari shell: find where the isle hosts it (automatically; else ask), remember, open.
M="{module}"; TITLE="{title}"; KIND="{app.get('kind', 'polari-app')}"
DIR="$HOME/.config/polari/access"; URLF="$DIR/$M.url"; CFG="$DIR/$M.json"; mkdir -p "$DIR"
have(){{ command -v "$1" >/dev/null 2>&1; }}
gui(){{ [ -n "${{DISPLAY:-}}${{WAYLAND_DISPLAY:-}}" ] && have zenity; }}
probe(){{ curl -sk -m 4 -o /dev/null -w '%{{http_code}}' "$1" 2>/dev/null | grep -qE '^(200|30[0-9]|401|403)$'; }}
url=""; [ -s "$URLF" ] && url=$(cat "$URLF") && probe "$url" || url=""
if [ -z "$url" ]; then   # 1. the core knows where every app is
    for api in https://api.polari.isle https://polari.isle; do
        u=$(curl -sk -m 4 "$api/api/access/$M" 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin).get("url",""))' 2>/dev/null)
        [ -n "$u" ] && probe "$u" && url=$u && break
    done
fi
if [ -z "$url" ]; then   # 2. the conventional addresses
    for c in {cands}; do probe "$c" && url=$c && break; done
fi
if [ -z "$url" ]; then   # 3. ask: the isle's .isle addresses (the core's list, the isle's DNS, what resolves)
    names=$( {{ curl -sk -m 4 https://api.polari.isle/api/access 2>/dev/null | python3 -c 'import sys,json
for a in json.load(sys.stdin).get("apps", []): print(a.get("url",""))' 2>/dev/null; isle dns list 2>/dev/null | awk '{{print $1}}' | grep '\\.isle$' | sed 's|^|https://|'; getent hosts polari.isle >/dev/null 2>&1 && echo https://polari.isle; }} | grep -E '^https?://' | sort -u )
    if [ -n "$names" ]; then
        if gui; then url=$(echo "$names" | zenity --list --title "Where is $TITLE?" --width 520 --height 380 --text "The app could not be found automatically. Pick the .isle address that is $TITLE:" --column "Address" 2>/dev/null)
        else echo "Where is $TITLE? Pick the .isle address:"; select url in $names; do [ -n "$url" ] && break; done; fi
    fi
fi
if [ -z "$url" ]; then
    msg="$TITLE could not be found on this isle. Is this computer on the isle (isle status), and is the app installed on a host member? A URL can be set by hand: echo https://<app>.isle > $URLF"
    if gui; then zenity --error --title "$TITLE" --width 480 --text "$msg" 2>/dev/null; else echo "$msg" >&2; fi; exit 1
fi
echo "$url" > "$URLF"
python3 - "$M" "$TITLE" "$url" "$CFG" <<'PY'
import json, sys
m, title, url, cfg = sys.argv[1:5]
json.dump({{"kind": "polari-shell-registration", "schemaVersion": 1,
           "app": {{"name": m, "title": title, "scope": "app", "appName": m, "startRoute": "", "brandColor": "", "icon": "", "capabilities": []}},
           "instances": [{{"id": m, "displayName": title, "webUrl": url, "apiUrl": url, "identityUrl": "", "instanceId": "",
                          "auth": {{"authority": "", "realm": "Polari", "clientId": "polari-shell", "pkce": "S256", "scope": "openid profile email roles",
                                   "shellRedirectUri": "polari://oauth/callback", "loginHint": ""}}}}]}}, open(cfg, "w"), indent=1)
PY
exec /usr/bin/polari-app-shell --config "$CFG"
'''


def desktop_entry(module, app):
    title = app.get('title') or module
    return (f'[Desktop Entry]\nType=Application\nName={title}\nComment=Open {title} on your isle (access only — the app runs on the isle)\n'
            f'Exec=/usr/share/polari-access/{module}/open.sh\nIcon=isle-app-store\nTerminal=false\nCategories=Network;\n'
            f'X-Polari-Kind=access-app\nX-Polari-Module={module}\n')


def access_postinst(module, flavor):
    """Offline flavour: the shell runtime deb travels inside; when it is missing, install it right after dpkg
    finishes (a transient unit — dpkg holds its lock during postinst) or say the one command."""
    if flavor != 'offline':
        return ''
    return f'''#!/bin/sh
set -e
if ! dpkg -s polari-shell-core >/dev/null 2>&1; then
    DEP=$(ls /usr/share/polari-access/{module}/deps/polari-shell-core_*.deb 2>/dev/null | head -1)
    if [ -n "$DEP" ]; then
        if command -v systemd-run >/dev/null 2>&1; then
            systemd-run --quiet --on-active=3 --unit=polari-access-{module}-shell-core /usr/bin/env sh -c "apt-get install -y $DEP || dpkg -i $DEP" && echo "polari-shell-core (the shell runtime) installs in a moment from the carried copy"
        else
            echo "the shell runtime is carried here — run once: sudo apt-get install -y $DEP"
        fi
    else
        echo "NOTE: the shell runtime (polari-shell-core) is not installed and this offline access deb does not carry it (the core staged no shell deb) — install it from the platform installer"
    fi
fi
exit 0
'''


def access_entries(module, app, flavor='online', shell_core_deb=None):
    """(control_fields, data_entries, scripts, carried_bytes) for the access deb; shell_core_deb = a staged
    polari-shell-core deb path for the offline flavour (carried under deps/), or None."""
    debname = access_deb_name(module, flavor)
    online = access_deb_name(module, 'online')
    title = app.get('title') or module
    entries = [('./', 'dir', None), ('./usr', 'dir', None), ('./usr/share', 'dir', None), ('./usr/share/applications', 'dir', None),
               (f'./usr/share/applications/polari-access-{module}.desktop', 'file', desktop_entry(module, app).encode()),
               ('./usr/share/polari-access', 'dir', None), (f'./usr/share/polari-access/{module}', 'dir', None),
               (f'./usr/share/polari-access/{module}/open.sh', 'exec', open_script(module, app).encode()),
               (f'./usr/share/polari-access/{module}/access.json', 'file', json.dumps({'module': module, 'kind': 'access-app', 'title': title, 'accesses': app.get('kind', 'polari-app'),
                                                                                       'candidates': access_url_candidates(module, app), 'flavor': flavor}, indent=1).encode())]
    carried = 0
    if flavor == 'offline' and shell_core_deb and os.path.isfile(shell_core_deb):
        with open(shell_core_deb, 'rb') as fh:
            data = fh.read()
        carried = len(data)
        entries += [(f'./usr/share/polari-access/{module}/deps', 'dir', None), (f'./usr/share/polari-access/{module}/deps/{os.path.basename(shell_core_deb)}', 'file', data)]
    control = [('Package', debname), ('Architecture', 'all'), ('Maintainer', 'Polari Suite <downloads@polari>'),
               ('Provides', online if flavor == 'offline' else ''), ('Conflicts', online if flavor == 'offline' else ''), ('Replaces', online if flavor == 'offline' else ''),
               ('Depends', 'curl, python3' + (', polari-shell-core' if flavor == 'online' else '')),
               ('Recommends', 'zenity' + (', polari-shell-core' if flavor == 'offline' else '')),
               ('Section', 'net'), ('Priority', 'optional'), ('Polari-Kind', 'access-app'),
               ('Description', f'Polari access app — opens {title} on your isle (the app runs on the isle; this installs only its shell)')]
    scripts = {'postinst': access_postinst(module, flavor)}
    return control, entries, scripts, carried
