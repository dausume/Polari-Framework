"""
@module board.custom.gen

`pol board gen uno [--variant <name>]` (brd-1, plan §3 step 2; brd-fi: VARIANTS): render a plain-C avr-libc project
AROUND the generated per-class header(s). The project is the template (`board/custom/firmware/uno/`: the variant's app
`apps/<app>.c` copied as main.c, hal.c/hal.h, the Makefile) + board_config.h rendered from the variant's knobs
(board.custom.variants) + one `<class>_packets.h` per class the variant speaks, rendered with c_twin target=avr —

  * live from `GET <api>/api/grpc/exposures/<class>/c-header?target=avr` when --api is given,
  * from THIS server's own exposure when the installer generates in-process (a `manager`),
  * else from the pinned contract snapshot (custom/contracts/<class>.v<N>.json, which says what it pins).

No --variant = uno-sim-rig (brd-1's firmware, unchanged); `--class X` alone picks the seeded variant written for X.
RULE 2 is checked on the result: a generated project holds only .c/.h/.v/.sv + Makefile/linker script.

brd-bo (THE BOARD OBJECT): the pin constants of board_config.h (LED_PIN, PWM_PIN, ADC_CHANNEL) come from the board's BoardPin
rows (board_pins below — the server's rows, else the seeds); the text rendered is unchanged, so every seeded variant's .hex stays
byte-identical (board_object_selftest + tests/board_object_probe.py prove it); the repro block names the pins and the board sha.

brd-fi: the FirmwareBuild row also carries `header_sha256` + `tag_order_json` (per class, the wire order) captured HERE,
so the installer can judge compatibility on what the board will actually speak (board.custom.compat) — never on
contract_hash alone (brd-1's finding: v1/v2 share a hash yet differ in order).

Layout of a work dir (default module_home.module_home('board')/<board>/ — /app/data/board/<board>/ inside a backend
container, ~/.cache/polari-board/<board>/ on a bare host):
    project/              the buildable tree of the CURRENT variant (nothing else lives in it — RULE 2)
    out/                  firmware.elf / firmware.hex after `pol board build`
    firmware_build.json   the FirmwareBuild row (state generated → built | refused → flashed), its repro block
    builds/<build>/       the build store: every built variant's .hex + record, so any of them can be installed

    python3 -m board.custom.gen uno [--variant V | --class C] [--out DIR] [--api URL] [--rig-name N] [--device-id N] [--u2x 0|1]
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import ssl
import sys

from board.custom import variants as V
from board.custom import compat

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
TEMPLATES = {'arduino-uno-r3': os.path.join(HERE, 'firmware', 'uno')}
TEMPLATE_FILES = ('hal.c', 'hal.h', 'Makefile')   # + apps/<app>.c → main.c
#: ucd-0e2b: an app whose atoms share macros/globals through their OWN header (button_clock_defs.h, never a board-
#: wide one like hal.h) — copied alongside main.c, same reasoning as TEMPLATE_FILES
APP_EXTRA_HEADERS = {'button_clock': ('apps/button_clock_defs.h',), 'light': ('apps/light_defs.h',),
                     'light_v2': ('apps/light_v2_defs.h',)}   # fgm-6a
ALIASES = {'uno': 'arduino-uno-r3', 'arduino-uno': 'arduino-uno-r3', 'arduino-uno-r3': 'arduino-uno-r3'}
#: the classes a template has an app for (another class = a new app, brd-4)
TEMPLATE_CLASSES = {'arduino-uno-r3': tuple(sorted({c for cs in V.APP_CLASSES.values() for c in cs}))}
RULE2_EXT = ('.c', '.h', '.v', '.sv')
RULE2_NAMES = ('Makefile', 'link.ld')
CONTRACTS = compat.CONTRACTS
DEFAULT_KNOBS = {k: V.DEFAULT_KNOBS[k] for k in ('rig_name', 'device_id', 'usart_u2x')}


class GenRefused(ValueError):
    pass


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def board_name(alias):
    b = ALIASES.get(alias)
    if not b and str(alias).lower() in ('c3', 'esp32c3', 'esp32-c3'):
        raise GenRefused('%r: no firmware template in gen.py (the UNO\'s) — the ESP32-C3 has its own generator, board.custom.gen_c3 '
                         '(`pol board gen c3`, sc-3)' % alias)
    if not b:
        raise GenRefused('no firmware template for %r — the UNO and the ESP32-C3 are picked (plan §8a; sc-3); every other device is a Road' % alias)
    return b


def default_work(board):
    from polariApiServer.module_home import module_home
    return os.path.join(module_home('board', os.environ.get('POLARI_BOARD_HOME')), board)


def pinned_contract(cls):
    c, path = compat.pinned_contract(cls)
    if c is None:
        raise GenRefused('no pinned contract for %s — pass --api to fetch the live header' % cls)
    return c, path


def header(cls, api='', msg_type=1, manager=None, bridge='', rx_parser='resync'):
    """(text, provenance) of `<cls>_packets.h` with target=avr — brd-wire: the WIRE V2 header (prelude: instance index in
    the width `bridge`'s bindings imply + presence bits; the EnumMappings as enums). sc-1: `rx_parser` 'keep-tail' renders
    the receiver fix (c_twin_v2.RX_PARSERS) — offline from the pinned contract only (a server's header is its own)."""
    if rx_parser != 'resync' and (api or manager is not None):
        raise GenRefused('rx_parser %s is rendered offline from the pinned contract only — a live or in-process header is the '
                         'server\'s own (drop --api / generate offline)' % rx_parser)
    if api:
        url = '%s/api/grpc/exposures/%s/c-header?msg_type=%d&target=avr&wire=2&bridge=%s' % (api.rstrip('/'), cls, int(msg_type), bridge)
        from polariApiServer import outbound
        with outbound.http_request('self', 'board', 'GET', url, means='rest', timeout=30, lib='urllib') as r:
            text = r.read().decode()
        m = re.search(r'contract v(\d+)\s+hash (\w*)', text)
        if '%s_MSG_TYPE' % cls.upper() not in text or 'target avr' not in text:
            raise GenRefused('the server returned no AVR header for %s (exposure enabled?)' % cls)
        w2 = re.search(r'hash2 (\w+)\s+(?:index width (\d+))?', text)
        return text, {'source': 'live', 'url': url, 'contract_version': int(m.group(1)) if m else 0, 'contract_hash': m.group(2) if m else '',
                      'tag_order': _order_from_header(text, cls), 'hash_v2': w2.group(1) if w2 else '',
                      'index_width': int(w2.group(2)) if w2 and w2.group(2) else 0,
                      'instance_count': int((re.search(r'\((\d+) instance', text) or [0, 1])[1])}
    if manager is not None:
        now = compat.server_header(manager, cls, msg_type, 'avr', bridge=bridge)
        if now is None:
            raise GenRefused('this server knows no contract for %s (no gRPC exposure, no pinned snapshot)' % cls)
        prov = {k: now[k] for k in ('source', 'contract_version', 'contract_hash', 'tag_order', 'where', 'hash_v2', 'index_width', 'instance_count') if k in now}
        prov.update({k: now[k] for k in ('path', 'sha256') if k in now})
        if now['source'] == 'live':
            prov['url'] = 'in-process: %s' % now['where']
        return now['text'], prov
    from grpcbridge.custom.c_twin import render_c_header
    c, path = pinned_contract(cls)
    spec = compat.wire_spec(None, cls, c['field_map'], bridge)
    text = render_c_header(cls, c['field_map'], int(msg_type), version=c['contract_version'], contract_hash=c['contract_hash'], target='avr',
                           wire=spec, rx_parser=rx_parser)
    return text, {'source': 'pinned', 'path': os.path.relpath(path, os.path.dirname(MOD)), 'sha256': sha256(open(path, 'rb').read()),
                  'contract_version': c['contract_version'], 'contract_hash': c['contract_hash'], 'tag_order': compat.tag_order(c['field_map']),
                  'hash_v2': spec['hash_v2'], 'index_width': spec['index_width'], 'instance_count': spec['instance_count']}


def _order_from_header(text, cls):
    """The struct's field order in a generated header (= tag order: c_twin emits fields in tag order)."""
    m = re.search(r'typedef struct\s*\{(.*?)\}\s*%s_t;' % re.escape(cls), text, re.S)
    if not m:
        return []
    return re.findall(r'\s(\w+)(?:\[\d+\])?;', m.group(1))


def render_config(knobs):
    """brd-1's signature, kept: board_config.h for uno-sim-rig with these identity knobs."""
    v = V.find(V.DEFAULT_VARIANT)
    return V.render_config(V.resolve(v, knobs))


def rule2_violations(project):
    return sorted(fn for fn in os.listdir(project) if not (fn.endswith(RULE2_EXT) or fn in RULE2_NAMES))


def source_sha(project):
    h = hashlib.sha256()
    for fn in sorted(os.listdir(project)):
        h.update(fn.encode() + b'\0' + open(os.path.join(project, fn), 'rb').read() + b'\0')
    return h.hexdigest()


def pick_variant(classes, variant, rows=None):
    """--variant wins; else the seeded variant whose app speaks exactly `classes`; no classes = uno-sim-rig."""
    if variant:
        try:
            return V.find(variant, rows)
        except V.VariantRefused as e:
            raise GenRefused(str(e))
    if not classes:
        return V.find(V.DEFAULT_VARIANT)
    for v in V.SEED_FIRMWARE_VARIANTS:
        if json.loads(v['classes_json']) == list(classes):
            return dict(v)
    raise GenRefused('the UNO template has apps for %s; %s needs its own template app (a generated header alone is not firmware)'
                     % (', '.join(TEMPLATE_CLASSES['arduino-uno-r3']), ', '.join(classes)))


def board_pins(board, manager=None, board_tables=None):
    """brd-bo: (pin knobs, {knob: canonical}, board sha) from THE BOARD OBJECT's BoardPin rows — this server's tables when it holds
    them (a `manager`), the given tables (a test's edited copy), else the seed rows. The pin constants of board_config.h
    (LED_PIN, PWM_PIN, ADC_CHANNEL) are these numbers."""
    from board.custom import board_object as bo
    tables = board_tables
    if tables is None and manager is not None:
        t = bo.tables_from_manager(manager)
        tables = t if any(p.get('board') == board for p in t.get('BoardPin', [])) else None
    try:
        r = bo.rows_for(board, tables)
    except bo.BoardObjectRefused as e:
        raise GenRefused(str(e))
    knobs, src = bo.pin_knobs(board, tables)
    return knobs, src, bo.board_sha(r), r


def _check_pins(r, knobs, rows):
    """A pin knob must name a BoardPin of the board (D<n> / A<n>), never a number the board does not have."""
    have = {p['canonical'] for p in rows['pins']}
    why = ['%s %d: the board has no pin %s%d' % (k, r['knobs'][k], 'A' if k == 'adc_channel' else 'D', r['knobs'][k])
           for k in V.PIN_KNOBS if ('A' if k == 'adc_channel' else 'D') + str(r['knobs'][k]) not in have]
    if why:
        raise GenRefused('; '.join(why))


def hal_check(variant, knobs, manager=None):
    """hsp-3c: the variant's Catom variables (the HAL) judged with the knobs this build uses - a refused one stops the build, naming why; the values
    ride the repro block. None when the variant has no catom variables."""
    from cmod.custom import catom_variables as CV
    rows = list(((getattr(manager, 'objectTables', None) or {}).get('CatomVariable') or {}).values()) or None
    hal = CV.build_check(variant, knobs, rows)
    if hal and hal['refused']:
        raise GenRefused('the HAL refuses this build (catom variables of %s): %s' % (variant, '; '.join(hal['refused'])))
    return hal


def render_routes(r):
    """The catom route files of a resolved variant and the ONE HAL header they need -> (rendered button route | None,
    rendered sense route | None, merged HAL header | None). Writes nothing: gen() writes them into the project and the HAL page
    shows the same header (hal-1), so the page and the build can never differ."""
    # fgm-5a: a non-INT0 button route is RENDERED (Jinja2, catoms/read-button/isotopes/<iso>/template.c.j2) into one extra .c file
    route = str(r['knobs'].get('button_route') or 'int0')
    rendered = None
    if r['features']['button'] and route != 'int0':
        from board.custom import button_routes as BR
        try:
            rendered = BR.render(route, r['knobs'])
        except BR.RouteRefused as e:
            raise GenRefused(str(e))
        rendered['route'] = 'button:%s' % route
    # fgm-5b: the same for a non-INT1 sense route (catoms/sense-led-line/isotopes/<iso>/template.c.j2 -> hal_sense_*.c)
    sroute = str(r['knobs'].get('sense_route') or 'int1')
    rendered_sense = None
    if r['features']['sense'] and sroute != 'int1':
        from board.custom import sense_routes as SR
        try:
            rendered_sense = SR.render(sroute, r['knobs'])
        except SR.RouteRefused as e:
            raise GenRefused(str(e))
        rendered_sense['route'] = 'sense:%s' % sroute
    # hal-2: ONE generated HAL header for every isotope of the project (the union of what each requires: polari_hal_<soc>.h)
    # hal-3a: plus the units the shared template uno/hal.c needs for THIS build's features and pins (base_roles), each also
    # under its role name (HAL_LED_SET_HIGH ...). Always written: hal.c includes it; a build needing nothing gets an empty one.
    from hal.custom import project as HP
    parts = [x for x in (rendered, rendered_sense) if (x or {}).get('hal_header')]
    base = base_roles(r)
    base_hdr = HP.project_header('atmega328p', {b['variable']: b['ops'] for b in base}, {b['variable']: b['pin'] for b in base}) if base else None
    headers = ([base_hdr] if base_hdr else []) + [x['hal_header'] for x in parts]
    sources = (['hal.c'] if base_hdr else []) + [x['route'] for x in parts]
    aliases = [{'name': 'HAL_%s_%s' % (b['role'], _role_suffix(op, b['role'])), 'key': (base_hdr['macros_keys'][(b['variable'], op)]),
                'form': 'init' if op in b.get('init', ()) else 'call'} for b in base for op in b['ops']]
    hal_hdr = HP.merged_header('atmega328p', headers, sources, aliases=aliases, always=True)
    return rendered, rendered_sense, hal_hdr


# hal-3a: digital pin n of the UNO -> the ATmega328P pin (D0-D7 = PD0-7, D8-D13 = PB0-5, D14-D19 = A0-A5 = PC0-5; Figure 1-1 p.12)
def uno_soc_pin(n):
    n = int(n)
    return 'PD%d' % n if n < 8 else 'PB%d' % (n - 8) if n < 14 else 'PC%d' % (n - 14)


def _role_suffix(op, role=''):
    """HAL_GPIO_SET_HIGH -> SET_HIGH, HAL_INT_EDGE_VECTOR -> EDGE_VECTOR, HAL_PWM_SET_DUTY -> PWM_SET_DUTY (LED role: HAL_LED_PWM_SET_DUTY);
    a suffix that repeats the role drops the repeat (PWM role: HAL_PWM_SET_DUTY, never HAL_PWM_PWM_SET_DUTY)."""
    from hal.custom import operations as OPS
    sfx = OPS.by_name(op)['c_name'][len('HAL_'):].replace('GPIO_', '', 1) if OPS.by_name(op)['c_name'].startswith('HAL_GPIO_') else \
        OPS.by_name(op)['c_name'].replace('HAL_INT_', '').replace('HAL_', '', 1)
    return sfx[len(role) + 1:] if role and sfx.startswith(role + '_') else sfx


def base_roles(r):
    """hal-3a: what the shared uno/hal.c asks of the HAL for this resolved variant, per role -> [{role, variable, pin, ops, init}].
    The same conditions board_config.h turns hal.c's blocks on with: FEATURE_LED, HAL_INT0 without a button route (the INT0 button),
    HAL_INT1 without a sense route (the INT1 sense), FEATURE_PWM on a Timer0 / Timer1 output (its direction only). `init` = the
    operations hal.c calls from init code, which gets the unguarded _INIT form (interrupts are still off there)."""
    f, k = r['features'], r['knobs']
    flags = {n: v for n, v in (r.get('flags') or [])}   # a build flag can turn hal.c's INT0 block on too (uno-button-count: HAL_INT0=1);
    # HAL_INT1 is a RESERVED knob name (variants.RESERVED), so no flag reaches the INT1 branch below — kept so the two blocks read alike
    out = []
    if f.get('led'):
        led_ops = ['gpio.output', 'gpio.set_high', 'gpio.set_low']
        led_init = ()
        if str(k.get('led_route') or 'gpio') == 'pwm':   # smp-1 drive-led:pwm (LED_ROUTE_PWM): the LED pin is its timer's compare output
            led_ops += ['pwm.init_phase', 'pwm.set_duty', 'pwm.connect', 'pwm.disconnect']
            led_init = ('pwm.init_phase',)
        out.append({'role': 'LED', 'variable': 'led_pin', 'pin': uno_soc_pin(k['led_pin']), 'ops': led_ops, 'init': led_init})
    if (f.get('button') or int(flags.get('HAL_INT0') or 0)) and str(k.get('button_route') or 'int0') == 'int0':
        out.append({'role': 'BUTTON', 'variable': 'button_pin', 'pin': uno_soc_pin(k['button_pin']),
                    'ops': ['gpio.input', 'gpio.pull_up', 'int.edge_enable_falling', 'int.edge_vector'], 'init': ('int.edge_enable_falling',)})
    if (f.get('sense') or int(flags.get('HAL_INT1') or 0)) and str(k.get('sense_route') or 'int1') == 'int1':
        out.append({'role': 'SENSE', 'variable': 'sense_pin', 'pin': uno_soc_pin(k['sense_pin']),
                    'ops': ['gpio.input', 'gpio.read', 'int.edge_enable', 'int.edge_vector'], 'init': ('int.edge_enable',)})
    if f.get('pwm') and int(k['pwm_pin']) in (5, 6, 9, 10):
        out.append({'role': 'PWM', 'variable': 'pwm_pin', 'pin': uno_soc_pin(k['pwm_pin']),
                    'ops': ['gpio.output', 'pwm.init_fast', 'pwm.connect', 'pwm.set_duty'], 'init': ('pwm.init_fast', 'pwm.connect')})
    return out


def hal_header_for(variant, board='uno', manager=None, variant_rows=None, board_tables=None):
    """hal-1: the HAL header ONE firmware variant's build includes, without building it -> {variant, title, app, routes, header | None,
    why}. Only the units its isotopes require on the pins its configuration chose are in it; header None = the build includes no
    generated HAL header (its routes still name registers directly), said in `why`."""
    board = board_name(board)
    v = pick_variant([], variant, variant_rows)
    pins, _src, _bsha, _brows = board_pins(board, manager, board_tables)
    try:
        r = V.resolve(v, {}, base=pins)
    except V.VariantRefused as e:
        raise GenRefused(str(e))
    rendered, rendered_sense, hdr = render_routes(r)
    routes = [x['route'] for x in (rendered, rendered_sense) if x]
    hdr = hdr if hdr and hdr['keys'] else None   # always=True gives an EMPTY header file for the build; as a page answer that is "none"
    why = ('%d HAL unit(s), required by %s' % (len(hdr['keys']), ', '.join(sorted({u['required_by'] for u in hdr['units']}))) if hdr else
           'no HAL units: %s' % ('its routes (%s) still name registers directly' % ', '.join(routes) if routes
                                 else 'it uses no LED, button, sense or PWM pin; its USART / tick / ADC code still names registers (hal-3b)'))
    return {'variant': r['name'], 'title': v.get('title', ''), 'app': r['app'], 'routes': routes, 'header': hdr, 'why': why}


def gen(board='uno', classes=None, work=None, api='', variant=None, manager=None, variant_rows=None, board_tables=None, **knobs):
    board = board_name(board)
    v = pick_variant(list(classes or []), variant, variant_rows)
    pins, pin_src, bsha, brows = board_pins(board, manager, board_tables)
    try:
        r = V.resolve(v, {a: b for a, b in knobs.items() if b is not None}, base=pins)
    except V.VariantRefused as e:
        raise GenRefused(str(e))
    _check_pins(r, pins, brows)
    own = set(V._j(v.get('knobs_json'), {})) | {a for a, b in knobs.items() if b is not None}
    pin_prov = {k: ({'from': 'BoardPin', 'pin': pin_src.get(k, '')} if k not in own else {'from': 'variant knob', 'value': r['knobs'][k]})
                for k in V.PIN_KNOBS}
    hal = hal_check(r['name'], {k: r['knobs'][k] for k in own if k in r['knobs']}, manager)
    if classes and list(classes) != r['classes']:
        raise GenRefused('variant %s speaks %s, not %s' % (r['name'], ', '.join(r['classes']), ', '.join(classes)))
    work = work or default_work(board)
    project = os.path.join(work, 'project')
    if os.path.isdir(project):
        shutil.rmtree(project)
    shutil.rmtree(os.path.join(work, 'out'), ignore_errors=True)
    os.makedirs(project)
    tpl = TEMPLATES[board]
    for fn in TEMPLATE_FILES:
        shutil.copy(os.path.join(tpl, fn), os.path.join(project, fn))
    app_src = os.path.join(tpl, 'apps', '%s.c' % r['app'])
    shutil.copy(app_src, os.path.join(project, 'main.c'))
    extra_headers = APP_EXTRA_HEADERS.get(r['app'], ())
    for rel in extra_headers:
        shutil.copy(os.path.join(tpl, rel), os.path.join(project, os.path.basename(rel)))
    rendered, rendered_sense, hal_hdr = render_routes(r)
    for f in (rendered, rendered_sense, hal_hdr):
        if f:
            open(os.path.join(project, f['file']), 'w').write(f['text'])
    class_rows, orders = [], {}
    bridge = str(r['knobs'].get('bridge') or '')
    rx_parser = str(r['knobs'].get('rx_parser') or 'resync')
    for i, cls in enumerate(r['classes']):
        text, prov = header(cls, api, i + 1, manager, bridge, rx_parser)
        width = int(prov.get('index_width') or 0)
        prov['indexed'] = '%s_INDEX_WIDTH' % cls.upper() in text   # elided entirely for a single instance
        count = int(prov.get('instance_count') or 1)
        if int(r['knobs']['instance_index']) >= count:
            raise GenRefused('instance_index %d does not fit: %s has %d instance(s) bound on bridge %r (%s) — bind '
                             'another interface first, or pick 0..%d' % (r['knobs']['instance_index'], cls, count, bridge or '-',
                                                                         'no index at all' if count == 1 else '%d-bit index' % width
                                                                         if width else 'an explicit index', count - 1))
        hfn = '%s_packets.h' % cls.lower()
        open(os.path.join(project, hfn), 'w').write(text)
        order = prov.pop('tag_order', None) or _order_from_header(text, cls)
        orders[cls] = order
        class_rows.append(dict(prov, **{'class': cls, 'header': hfn, 'header_sha256': sha256(text), 'target': 'avr', 'msg_type': i + 1,
                                        'tag_order': order, 'wire': 2, 'bridge': bridge}))
    # brd-wire: the instance knob exists only for an indexed class (several boards bound on the bridge)
    open(os.path.join(project, 'board_config.h'), 'w').write(V.render_config(r, indexed=any(c.get('indexed') for c in class_rows)))
    viol = rule2_violations(project)
    if viol:
        raise GenRefused('RULE 2: a generated project holds only .c/.h/.v/.sv + Makefile/linker script — found %s' % viol)
    ssha = source_sha(project)
    now = datetime.datetime.now().isoformat(timespec='seconds')
    tfiles = [('template ' + fn, 'board/custom/firmware/uno/' + fn, os.path.join(tpl, fn)) for fn in TEMPLATE_FILES] \
        + [('template app %s (main.c)' % r['app'], 'board/custom/firmware/uno/apps/%s.c' % r['app'], app_src)] \
        + [('template app header %s' % os.path.basename(rel), 'board/custom/firmware/uno/' + rel, os.path.join(tpl, rel)) for rel in extra_headers]
    tinputs = []
    if rendered:   # the template + its macro file by sha256, and what rendered from them (the file is also hashed as a project input)
        tinputs = [{'label': 'isotope template (jinja2)', 'path': rendered['template'], 'sha256': rendered['template_sha256']},
                   {'label': 'isotope template macros (jinja2)', 'path': 'board/custom/firmware/uno/catoms/read-button/_common.j2', 'sha256': rendered['common_sha256']}]
    if rendered_sense:
        tinputs += [{'label': 'isotope template (jinja2)', 'path': rendered_sense['template'], 'sha256': rendered_sense['template_sha256']},
                    {'label': 'isotope template macros (jinja2)', 'path': 'board/custom/firmware/uno/catoms/sense-led-line/_common.j2', 'sha256': rendered_sense['common_sha256']}]
    if hal_hdr:
        tinputs.append({'label': 'generated HAL (%d units)' % len(hal_hdr['keys']), 'path': 'hal.custom.project -> ' + hal_hdr['file'],
                        'sha256': hal_hdr['sha256'], 'units': hal_hdr['keys']})
    row = {'name': '%s-%s' % (r['name'], ssha[:12]), 'board_definition': board, 'state': 'generated', 'variant': r['name'],
           'classes_json': json.dumps(class_rows), 'template': 'board/custom/firmware/uno', 'source_sha': ssha,
           'header_sha256': compat.combined_sha(class_rows), 'tag_order_json': json.dumps(orders),
           'contract_hash_v2': class_rows[0]['hash_v2'] if len(class_rows) == 1 else sha256('\n'.join('%s:%s' % (c['class'], c['hash_v2']) for c in class_rows))[:16],
           'bridge_name': bridge, 'instance_index': int(r['knobs']['instance_index']),
           'artifact_sha256': '', 'engines_json': '{}', 'size_text': 0, 'size_data': 0, 'size_bss': 0, 'built_at': '',
           'flashed_to': '', 'flash_log': '', 'generated_at': now, 'hex_path': '',
           'repro_json': json.dumps({'inputs': [{'label': lab, 'path': p, 'sha256': sha256(open(fp, 'rb').read())} for lab, p, fp in tfiles]
                                    + tinputs
                                    + [{'label': 'contract %s' % c['class'], 'path': c.get('path', c.get('url', '')), 'sha256': c.get('sha256', c['header_sha256'])} for c in class_rows],
                                    'knobs': dict(r['knobs'], variant=r['name'], app=r['app'], features=r['features'],
                                                  build_flags=['%s=%d' % f for f in r['flags']]),
                                    # brd-bo: where board_config.h's pin constants came from, and the board object's sha at gen time
                                    'board_object': {'board': board, 'board_sha': bsha, 'pins': pin_prov},
                                    # hsp-3c: the HAL values this build was judged with (catom_variables.build_check), when the variant has them
                                    **({'catom_hal': hal} if hal else {})}),
           'notes': 'generated (variant %s); `pol board build uno` compiles it' % r['name'], 'project_dir': project, 'work_dir': work}
    write_record(work, row)
    return row


def write_record(work, row):
    os.makedirs(work, exist_ok=True)
    json.dump(row, open(os.path.join(work, 'firmware_build.json'), 'w'), indent=1)


def read_record(work):
    p = os.path.join(work, 'firmware_build.json')
    if not os.path.isfile(p):
        raise GenRefused('no generated firmware in %s — run `pol board gen uno` first' % work)
    return json.load(open(p))


def store_dir(work, name):
    return os.path.join(work, 'builds', name)


def stored_builds(work):
    """Every built variant in the build store (newest first) — what the installer can put on a board."""
    root = os.path.join(work, 'builds')
    out = []
    if os.path.isdir(root):
        for name in os.listdir(root):
            try:
                out.append(read_record(os.path.join(root, name)))
            except GenRefused:
                continue
    return sorted(out, key=lambda r: r.get('built_at', ''), reverse=True)


def row_fields(row):
    """The FirmwareBuild constructor's fields only (the record carries a few local paths besides)."""
    import inspect
    from board.board_basis import FirmwareBuild
    names = set(inspect.signature(FirmwareBuild.__init__).parameters) - {'self', 'manager'}
    return {k: v for k, v in row.items() if k in names}


def main(argv):
    if argv and str(argv[0]).lower() in ('c3', 'esp32c3', 'esp32-c3'):   # sc-3: the ESP32-C3 template (ESP-IDF, FreeRTOS)
        from board.custom import gen_c3
        return gen_c3.main(argv)
    import argparse
    ap = argparse.ArgumentParser(prog='pol board gen')
    ap.add_argument('board')
    ap.add_argument('--variant', default='')
    ap.add_argument('--class', dest='classes', action='append')
    ap.add_argument('--out')
    ap.add_argument('--api', default='')
    ap.add_argument('--rig-name')
    ap.add_argument('--device-id', type=int)
    ap.add_argument('--u2x', type=int, dest='usart_u2x')
    ap.add_argument('--instance-index', type=int, dest='instance_index', help='brd-wire: this build\'s index among the bridge\'s bound instances')
    a = ap.parse_args(argv)
    try:
        row = gen(a.board, a.classes, a.out, a.api, variant=a.variant or None, rig_name=a.rig_name, device_id=a.device_id, usart_u2x=a.usart_u2x,
                  instance_index=a.instance_index)
    except GenRefused as e:
        print('[REFUSED] %s' % e)
        return 1
    cls = json.loads(row['classes_json'])
    print('[ OK ] %s  variant=%s  state=%s' % (row['name'], row['variant'], row['state']))
    print('       project  %s  (%s)' % (row['project_dir'], ', '.join(sorted(os.listdir(row['project_dir'])))))
    for c in cls:
        print('       header   %s  contract v%s hash %s  (%s)  sha256 %s' % (c['header'], c['contract_version'], c['contract_hash'], c['source'], c['header_sha256'][:16]))
        print('       wire v2  hash2 %s  index width %s bit(s)  bridge %s  instance %s' % (c.get('hash_v2'), c.get('index_width'), c.get('bridge') or '-', row['instance_index']))
        print('       wire     %s' % ', '.join(c['tag_order']))
    print('       next     pol board build %s' % a.board)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
