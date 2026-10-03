"""
@module board.custom.ingest_zephyr

ZEPHYR → ROWS (brd-bo, PCB_FROM_SCRATCH_PLAN §2b "ingest in"): read a Zephyr board directory (its `.dts`, the `.dtsi` it
includes, the pinctrl `.dtsi`, `board.yml`, `<board>_defconfig`, `Kconfig`) — or ONE overlay we rendered — into BoardPin-shaped
dicts, the console, the aliases, the peripherals enabled, the SoC's memory/clock nodes. Every pin cites file:line.

What it derives (and what it does not):
  * a pin per `pinmux = <PERIPH_SIGNAL_GPIOn>` macro of a pinctrl group that an ENABLED node (`status = "okay"` after merging
    the SoC dtsi → the board dts → the overlay) points at with `pinctrl-0` — canonical GPIOn, peripheral = the node label,
    signal = the macro stem (UART0_TX), net = the stem, electrical = the group's flags (bias-pull-up, output-high …);
  * a pin per `gpio-keys` / `gpio-leds` child (`gpios = <&gpio0 N (FLAGS)>`), its alias from `aliases`;
  * NOT: pins of a DISABLED node (listed in `skipped`, never rows — the upstream i2s and twai groups overlap spi2's pins,
    legal only because they are off); pins a node uses WITHOUT pinctrl (the USB Serial/JTAG's GPIO18/19 — a fixed function,
    cited from the datasheet by the seed instead); connector/header labels (Zephyr's esp32c3_devkitm dts has none); the C
    identifiers firmware uses (not a devicetree concept — the ESP-IDF / bare-C views carry them).
"""
import hashlib
import json
import os
import re

from board.custom import dts

MACRO = re.compile(r'^([A-Z][A-Z0-9]*)_([A-Z0-9_]+?)_GPIO(\d+)$')
FUNCTION_OF = (('usb_serial', 'usb'), ('uart', 'uart'), ('spi', 'spi'), ('i2c', 'i2c'), ('i2s', 'i2s'), ('twai', 'can'), ('ledc', 'pwm'),
               ('adc', 'adc'))
ELECTRICAL = {'bias-pull-up': ('bias', 'pull-up'), 'bias-pull-down': ('bias', 'pull-down'), 'bias-disable': ('bias', 'disable'),
              'drive-open-drain': ('drive', 'open-drain'), 'drive-push-pull': ('drive', 'push-pull'), 'output-high': ('output', 'high'),
              'output-low': ('output', 'low'), 'input-enable': ('input', 'enable'), 'output-enable': ('output', 'enable')}
GPIO_FLAGS = {'GPIO_PULL_UP': ('bias', 'pull-up'), 'GPIO_PULL_DOWN': ('bias', 'pull-down'), 'GPIO_ACTIVE_LOW': ('active', 'low'),
              'GPIO_ACTIVE_HIGH': ('active', 'high')}


def function_of(label):
    for prefix, fn in FUNCTION_OF:
        if label.startswith(prefix):
            return fn
    return 'gpio'


def _sha(text):
    return hashlib.sha256(text.encode() if isinstance(text, str) else text).hexdigest()


def read_files(files):
    """files: [(relpath, text)] in MERGE order (includes before the file that includes them). → merged label table."""
    labels, chosen, aliases, keys, parsed = {}, {}, {}, [], []

    def merge(label, node, rel):
        cur = labels.setdefault(label, {'name': node['name'], 'props': {}, 'children': [], 'file': rel, 'line': node['line']})
        for k, (v, ln) in node['props'].items():
            cur['props'][k] = (v, rel, ln)
        for ch in node['children']:
            if ch['label']:
                merge(ch['label'], ch, rel)
            cur['children'].append(dict(ch, file=rel))

    for rel, text in files:
        tree = dts.parse(text)
        parsed.append({'path': rel, 'sha256': _sha(text), 'includes': tree['includes']})
        for root in tree['roots']:
            if root['ref']:
                merge(root['ref'], root, rel)
                continue
            for _, n in dts.walk(root['children']):
                if n['label']:
                    merge(n['label'], n, rel)
                if n['name'] == 'chosen':
                    chosen.update({k: (v, rel, ln) for k, (v, ln) in n['props'].items()})
                elif n['name'] == 'aliases':
                    aliases.update({k: (v, rel, ln) for k, (v, ln) in n['props'].items()})
                compat = dts.string(n['props'].get('compatible', ('', 0))[0])
                if compat in ('gpio-keys', 'gpio-leds'):
                    keys.append((compat, n, rel))
    return {'labels': labels, 'chosen': chosen, 'aliases': aliases, 'keys': keys, 'files': parsed}


def _status(node):
    return dts.string(node['props'].get('status', ('okay', '', 0))[0])


def _pin(board, gpio, net, signal, function, peripheral, elec, alias, origin):
    c = 'GPIO%d' % gpio
    return {'name': '%s:%s' % (board, c), 'board': board, 'canonical': c, 'number': gpio, 'soc_pin': c, 'net': net, 'connector_pin': '',
            'function': function, 'peripheral': peripheral, 'signal': signal, 'firmware_symbol': '', 'alias': alias,
            'electrical_json': json.dumps(elec, sort_keys=True), 'facts_json': '[]', 'origin': 'ingested:%s' % origin,
            'undetermined': '', 'notes': ''}


def derive(m, board, tag=''):
    """The merged table → {'pins', 'skipped', 'twice', 'okay', 'console', 'aliases'}."""
    pins, skipped, okay = [], [], []
    at = ('@zephyr %s' % tag) if tag else ''
    for label, node in sorted(m['labels'].items()):
        st = _status(node) if 'status' in node['props'] else None
        if st == 'okay':
            okay.append(label)
        if 'pinctrl-0' not in node['props']:
            continue
        for g in [c.lstrip('&') for c in dts.cells(node['props']['pinctrl-0'][0])]:
            gnode = m['labels'].get(g)
            if gnode is None:
                skipped.append({'node': label, 'group': g, 'why': 'pinctrl group %s is not in the files read' % g})
                continue
            for sub in gnode['children']:
                if 'pinmux' not in sub['props']:
                    continue
                v, ln = sub['props']['pinmux']
                elec = {ELECTRICAL[p][0]: ELECTRICAL[p][1] for p in sub['props'] if p in ELECTRICAL}
                for macro in [c for part in v.split(',') for c in dts.cells(part.strip())]:
                    mm = MACRO.match(macro)
                    if not mm:
                        skipped.append({'node': label, 'group': g, 'why': 'pinmux %r is not PERIPH_SIGNAL_GPIOn' % macro})
                        continue
                    stem, gpio = '%s_%s' % (mm.group(1), mm.group(2)), int(mm.group(3))
                    if st != 'okay':
                        skipped.append({'node': label, 'group': g, 'pin': 'GPIO%d' % gpio, 'signal': stem,
                                        'why': 'node %s is %s — its pins are not an assignment' % (label, st or 'without a status')})
                        continue
                    pins.append(_pin(board, gpio, stem, stem, function_of(label), label.upper(), elec, '', '%s:L%d%s' % (sub['file'], ln, at)))
    rev = {dts.string(v).lstrip('&'): a for a, (v, _, _) in m['aliases'].items()}
    for compat, n, rel in m['keys']:
        for ch in n['children']:
            if 'gpios' not in ch['props']:
                continue
            v, ln = ch['props']['gpios']
            c = dts.cells(v)
            elec = {GPIO_FLAGS[f][0]: GPIO_FLAGS[f][1] for f in re.findall(r'GPIO_[A-Z_]+', c[2] if len(c) > 2 else '') if f in GPIO_FLAGS}
            if 'zephyr,code' in ch['props']:
                elec['code'] = dts.cells(ch['props']['zephyr,code'][0])[0]
            if 'label' in ch['props']:
                elec['label'] = dts.string(ch['props']['label'][0])
            alias = rev.get(ch['label'], '')
            net = (alias or ch['label'] or ch['name']).upper().replace('-', '_')
            pins.append(_pin(board, int(c[1]), net, '', 'button' if compat == 'gpio-keys' else 'led', 'GPIO0', elec, alias,
                             '%s:L%d%s' % (rel, ln, at)))
    seen, twice = {}, []
    for p in pins:
        if p['soc_pin'] in seen:
            twice.append((p['soc_pin'], seen[p['soc_pin']], p['signal'] or p['net']))
        seen.setdefault(p['soc_pin'], p['signal'] or p['net'])
    return {'pins': sorted(pins, key=lambda p: p['number']), 'skipped': skipped, 'twice': twice, 'okay': sorted(okay),
            'console': dts.string(m['chosen'].get('zephyr,console', ('', '', 0))[0]).lstrip('&'),
            'aliases': {a: dts.string(v).lstrip('&') for a, (v, _, _) in m['aliases'].items()}}


def _find(root, name):
    for r, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(r, f)
            if f == os.path.basename(name) and p.endswith(name.replace('/', os.sep)):
                return p
    return None


def files_in_order(root, entry):
    """Depth-first include order starting at `entry`; unresolved .dts/.dtsi includes are returned too."""
    order, missing, seen = [], [], set()

    def visit(path):
        if path in seen:
            return
        seen.add(path)
        text = open(path).read()
        for inc in dts.parse(text)['includes']:
            if not inc.endswith(('.dtsi', '.dts')):
                continue
            p = _find(root, inc) or _find(os.path.dirname(path), os.path.basename(inc))
            if p:
                visit(p)
            else:
                missing.append(inc)
        order.append((os.path.relpath(path, root), text))

    visit(entry)
    return order, missing


def board_yml(text):
    out = {k: (re.search(r'^\s+%s:\s*(\S.*)$' % k, text, re.M) or [None, ''])[1].strip() for k in ('name', 'full_name', 'vendor')}
    out['socs'] = re.findall(r'-\s*name:\s*(\S+)', text)
    return out


def upstream(root, board_dir, board, tag):
    """Ingest a STORED upstream Zephyr board dir (custom/upstream/zephyr-<tag>/boards/<vendor>/<board>) → derive() + identity,
    runtime facts (defconfig lines, the board heap addition), the SoC nodes (cpu clock, memories, flash size, peripherals)."""
    bd = os.path.join(root, board_dir)
    ident = board_yml(open(os.path.join(bd, 'board.yml')).read())
    files, missing = files_in_order(root, os.path.join(bd, '%s.dts' % ident['name']))
    m = read_files(files)
    out = derive(m, board, tag)
    defconfig = [ln.strip() for ln in open(os.path.join(bd, '%s_defconfig' % ident['name'])).read().splitlines() if ln.startswith('CONFIG_')]
    heap = re.search(r'HEAP_MEM_POOL_ADD_SIZE_BOARD\s+int\s+default\s+(\d+)', open(os.path.join(bd, 'Kconfig')).read(), re.S)
    soc = {}
    cpu = m['labels'].get('cpu0')
    if cpu and 'clock-frequency' in cpu['props']:
        v, rel, ln = cpu['props']['clock-frequency']
        mm = re.search(r'DT_FREQ_M\((\d+)\)', v)
        soc['cpu_clock_hz'] = (int(mm.group(1)) * 1000000 if mm else 0, '%s:L%d' % (rel, ln))
    mem = []
    for lab in ('sram0', 'sram1', 'rtc_fast_ram', 'flash0'):
        n = m['labels'].get(lab)
        if n and 'reg' in n['props']:
            v, rel, ln = n['props']['reg']
            c = dts.cells(v)
            mk = re.match(r'DT_SIZE_([KM])\((\d+)\)', c[1] if len(c) > 1 else '')
            mem.append({'region': lab, 'start': c[0], 'size': int(mk.group(2)) * (1024 if mk.group(1) == 'K' else 1048576) if mk else (c[1] if len(c) > 1 else ''),
                        'cite': '%s:L%d@zephyr %s' % (rel, ln, tag)})
    periph = []
    for lab, n in sorted(m['labels'].items()):
        if 'reg' in n['props'] and 'compatible' in n['props'] and lab not in ('sram0', 'sram1', 'rtc_fast_ram', 'flash0', 'cpu0'):
            v, rel, ln = n['props']['reg']
            first = re.match(r'\s*"([^"]*)"', n['props']['compatible'][0])
            periph.append({'name': lab, 'compatible': first.group(1) if first else '', 'reg': dts.cells(v)[0],
                           'status': _status(n) if 'status' in n['props'] else 'okay', 'cite': '%s:L%d@zephyr %s' % (rel, ln, tag)})
    gpio = m['labels'].get('gpio0')
    if gpio and 'ngpios' in gpio['props']:
        v, rel, ln = gpio['props']['ngpios']
        soc['ngpios'] = (int(dts.cells(v)[0]), '%s:L%d' % (rel, ln))
    out.update(identity=ident, files=m['files'], missing_includes=missing, defconfig=defconfig, heap_add=int(heap.group(1)) if heap else 0,
               soc=soc, memory=mem, peripherals=periph, chosen={k: dts.string(v) for k, (v, _, _) in m['chosen'].items()})
    return out


def overlay(text, board, path='overlay'):
    """Ingest ONE overlay (what `render --as zephyr` writes) → derive()."""
    return derive(read_files([(path, text)]), board)
