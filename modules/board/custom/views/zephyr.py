"""
@module board.custom.views.zephyr

THE ZEPHYR VIEW (brd-bo): a devicetree OVERLAY (applied on top of the upstream board, e.g. esp32c3_devkitm) + a Kconfig fragment,
from the rows:
  * every BoardPin with a pinctrl signal → a pinctrl group `<node>_polari` (one group per distinct electrical flag set), the node
    `&<peripheral> { status = "okay"; pinctrl-0 = <&<node>_polari>; }` — the macro `<SIGNAL>_GPIO<n>` must exist in the stored
    upstream esp32c3-pinctrl.h (Zephyr v4.4.2), else the render is REFUSED (the GPIO matrix routes most signals anywhere, but
    the binding names only what it names);
  * every button / led pin → a gpio-keys / gpio-leds child `polari_<alias>` with its flags, and `aliases { <alias> = … }`;
  * the RuntimeProfile zephyr row → `chosen { zephyr,console }`, the peripherals it enables without pins (`&usb_serial`), and the
    .conf lines (its config_json — the upstream defconfig, ingested);
  * NOT carried (said in the overlay's header): pins without pinctrl (the USB Serial/JTAG's fixed GPIO18/19), C identifiers.
A board whose zephyr RuntimeProfile is unsupported (the UNO: no AVR in Zephyr) is REFUSED with that row's reason.
"""
import json
import os
import re

from board.custom.views import ViewRefused, banner

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PINCTRL_H = {'esp32c3': os.path.join(HERE, 'upstream', 'zephyr-v4.4.2', 'include', 'zephyr', 'dt-bindings', 'pinctrl', 'esp32c3-pinctrl.h')}
ELEC_ORDER = (('bias', 'bias-%s'), ('drive', 'drive-%s'), ('input', 'input-%s'), ('output', 'output-%s'))
FLAG = {('bias', 'pull-up'): 'GPIO_PULL_UP', ('bias', 'pull-down'): 'GPIO_PULL_DOWN', ('active', 'low'): 'GPIO_ACTIVE_LOW',
        ('active', 'high'): 'GPIO_ACTIVE_HIGH'}
_MACROS = {}


def macros(soc):
    if soc not in _MACROS:
        p = PINCTRL_H.get(soc)
        _MACROS[soc] = set(re.findall(r'^#define\s+([A-Z][A-Z0-9_]*_GPIO\d+)\s', open(p).read(), re.M)) if p and os.path.isfile(p) else None
    return _MACROS[soc]


def carried(p):
    """A pin the Zephyr view carries: a pinctrl signal, or a key/led."""
    return (bool(p.get('signal')) and p.get('peripheral') != 'USB_SERIAL') or p.get('function') in ('button', 'led')


def render(r, bsha):
    prof = r['profiles'].get('zephyr') or {}
    if not prof.get('supported'):
        raise ViewRefused('no Zephyr view for %s: %s' % (r['board'], prof.get('refusal') or 'no zephyr RuntimeProfile row'))
    soc = (r['soc'] or {}).get('name', '')
    known = macros(soc)
    if known is None:
        raise ViewRefused('no stored Zephyr pinctrl header for SoC %s — ingest its upstream board first' % soc)
    groups, keys, skipped = {}, [], []
    for p in sorted(r['pins'], key=lambda p: int(p['number'])):
        if not carried(p):
            skipped.append('%s (%s%s)' % (p['canonical'], p['net'], ', no pinctrl' if p.get('function') == 'usb' else ''))
            continue
        if p['function'] in ('button', 'led'):
            keys.append(p)
            continue
        macro = '%s_%s' % (p['signal'], p['canonical'])
        if macro not in known:
            raise ViewRefused('%s on %s: no pinmux macro %s in Zephyr v4.4.2\'s %s-pinctrl.h' % (p['signal'], p['canonical'], macro, soc))
        node = p['peripheral'].lower()
        elec = json.loads(p.get('electrical_json') or '{}')
        g = groups.setdefault(node, [])
        k = json.dumps(elec, sort_keys=True)
        hit = next((x for x in g if x[0] == k), None)
        if hit is None:
            g.append((k, elec, [macro]))
        else:
            hit[2].append(macro)
    L = ['/*', ' * %s' % banner('zephyr', r, bsha), ' * An OVERLAY on the upstream board %s.' % (r['identity'].get('upstream_board') or '-'),
         ' * Not carried by a devicetree: %s.' % ('; '.join(skipped) or 'nothing'), ' */', '', '/ {', '\tchosen {']
    if prof.get('console_uart'):
        L.append('\t\tzephyr,console = &%s;' % prof['console_uart'])
    L.append('\t};')
    aliased = [p for p in keys if p.get('alias')]
    if aliased:
        L.append('\taliases {')
        L += ['\t\t%s = &polari_%s;' % (p['alias'], p['alias'].replace('-', '_')) for p in aliased]
        L.append('\t};')
    for compat, fn in (('gpio-keys', 'button'), ('gpio-leds', 'led')):
        ks = [p for p in keys if p['function'] == fn]
        if not ks:
            continue
        L += ['\tpolari_%s {' % compat.split('-')[1], '\t\tcompatible = "%s";' % compat]
        for p in ks:
            e = json.loads(p.get('electrical_json') or '{}')
            flags = ' | '.join(FLAG[(k, e[k])] for k in ('bias', 'active') if (k, e.get(k)) in FLAG) or '0'
            nm = (p.get('alias') or p['canonical'].lower()).replace('-', '_')
            L += ['\t\tpolari_%s: %s {' % (nm, nm), '\t\t\tgpios = <&gpio0 %d (%s)>;' % (int(p['number']), flags)]
            if e.get('label'):
                L.append('\t\t\tlabel = "%s";' % e['label'])
            if e.get('code'):
                L.append('\t\t\tzephyr,code = <%s>;' % e['code'])
            L.append('\t\t};')
        L.append('\t};')
    L += ['};', '', '&pinctrl {']
    for node in sorted(groups):
        L.append('\t%s_polari: %s_polari {' % (node, node))
        for i, (_, elec, ms) in enumerate(groups[node], 1):
            L += ['\t\tgroup%d {' % i, '\t\t\tpinmux = %s;' % ', '.join('<%s>' % m for m in ms)]
            L += ['\t\t\t%s;' % (fmt % elec[k]) for k, fmt in ELEC_ORDER if k in elec]
            L.append('\t\t};')
        L.append('\t};')
    L += ['};', '']
    for node in sorted(groups):
        L += ['&%s {' % node, '\tstatus = "okay";', '\tpinctrl-0 = <&%s_polari>;' % node, '\tpinctrl-names = "default";', '};', '']
    pinless = sorted(set(x for x in json.loads(prof.get('peripherals_json') or '[]') if isinstance(x, str)) - set(groups) - {'gpio0'})
    for node in pinless:
        L += ['&%s {' % node, '\tstatus = "okay";', '};', '']
    if keys:
        L += ['&gpio0 {', '\tstatus = "okay";', '};', '']
    conf = ['# %s.conf — %s' % (r['board'], banner('zephyr', r, bsha))] + json.loads(prof.get('config_json') or '[]')
    return {'%s.overlay' % r['board']: '\n'.join(L), '%s.conf' % r['board']: '\n'.join(conf) + '\n'}


def ingest(files, r):
    """→ pins (BoardPin-shaped, the Zephyr-carried fields) + the profile's console, from an overlay or an upstream board dir."""
    from board.custom import ingest_zephyr
    name = next((n for n in files if n.endswith(('.overlay', '.dts', '.dtsi'))), None)
    if name is None:
        raise ViewRefused('no .overlay / .dts among %s' % sorted(files))
    d = ingest_zephyr.overlay(files[name], r['board'], name)
    conf = next((t for n, t in files.items() if n.endswith('.conf')), '')
    prof = {'console_uart': d['console']} if d['console'] else {}
    if conf:
        prof['config_json'] = json.dumps([ln.strip() for ln in conf.splitlines() if ln.startswith('CONFIG_')])
    return {'pins': d['pins'], 'profile': prof, 'notes': json.dumps({'skipped': d['skipped'], 'twice': d['twice']})}
