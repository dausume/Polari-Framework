"""
@module electrodevice.custom.cst_sources

cst-0 (PROTOTYPING_VIEWS_PLAN.md §2, §8): THE EVIDENCE a circuit state is read from — never typed:

  hal_init_modes(config)   the pin modes the config's HAL init functions WRITE, read from the rendered sources by a regex over each `hal_*_init` body
                           (DDRx |= _BV(Pxn) -> output; DDRx &= ~_BV(Pxn) -> input; PORTx |= _BV(Pxn) on an input -> pull-up; LED_DDR/LED_BIT resolve
                           through board_config.h's LED_PIN). Each mode names the line it came from.
  pin_writer(config)       the field that controls a pin and its writers / reader, from board.custom.firmware_state (the parsed atoms): for uno-light
                           `led_on` -> written by apply_command + led_toggle, read by led_follow_state which drives D6 (hal_led) to 0 or 1.
  press_record(config)     the committed press-latency record (board/custom/press_records/<config>.json): press -> the light pin's first rise, best/worst
                           ms, its sha — or None (then a transition says it was read from the source).
  circuit_for(config, t)   the CircuitDefinition the config's claimed board pins sit on (the BoardPinNet rows name the pins per circuit); the circuit
                           covering the most claimed pins wins, ties kept in words.
"""
import json
import os
import re
import shutil
import tempfile

PORT_PINS = {'D': lambda n: 'D%d' % n, 'B': lambda n: 'D%d' % (8 + n), 'C': lambda n: 'A%d' % n}   # ATmega328P on the UNO: PDn = Dn, PBn = D8+n, PCn = An


class SourceRefused(RuntimeError):
    pass


def _pin(port, bit):
    return PORT_PINS[port](int(bit)) if port in PORT_PINS else '%s%s' % (port, bit)


def _resolve_macro(name, defines):
    """LED_BIT / LED_DDR style macros -> the port letter + bit through board_config.h's LED_PIN (digital n -> PD n for n < 8, else PB n-8)."""
    pin = next((d['value'] for d in defines if d['name'] == 'LED_PIN'), '')
    m = re.fullmatch(r'(\d+)u?', pin or '')
    if m:
        n = int(m.group(1))
        return ('D', n) if n < 8 else ('B', n - 8)
    return None


def hal_init_modes(config):
    """{board pin: {'mode': 'output'|'input', 'pull': 'up'|'none', 'initial': 'low'|'', 'init': fn, 'source': 'file:line words'}} from the rendered config's hal sources."""
    from board.custom import firmware_state as FS
    from cmod.custom import projects as P
    spec, cfg = FS._config(config)
    work = tempfile.mkdtemp(prefix='cst-%s-' % config)
    try:
        r = P.render(spec, cfg, work)
        d = r['dir']
        defines = FS._defines(os.path.join(d, 'board_config.h'))
        out = {}
        for src in sorted(f for f in os.listdir(d) if f.endswith('.c')):
            # only the functions the preprocessor leaves in THIS config's build count (hal_button_init sits under #if HAL_INT0): the parsed TU names them
            walk, _probs = FS._parse_tu(os.path.join(d, src), r['include_dirs'])
            compiled = set(walk.funcs)
            for fn, body in FS._raw_bodies(os.path.join(d, src)).items():
                if not re.fullmatch(r'hal_\w*init', fn) or fn not in compiled:
                    continue
                for ln in body.splitlines():
                    code = ln.split('/*')[0]
                    m = re.search(r'(DDR|PORT)([BCD])\s*(\|=|&=)\s*(?:\(uint8_t\))?\s*~?\s*_BV\(P([BCD])(\d)\)', code)
                    macro = re.search(r'(LED_DDR|LED_PORT)\s*(\|=|&=)\s*~?\s*_BV\(LED_BIT\)', code)
                    if macro:
                        pb = _resolve_macro('LED_BIT', defines)
                        if pb is None:
                            continue
                        reg, port, op, bit = ('DDR' if macro.group(1) == 'LED_DDR' else 'PORT'), pb[0], macro.group(2), pb[1]
                    elif m:
                        reg, port, op, bit = m.group(1), m.group(4), m.group(3), int(m.group(5))
                    else:
                        continue
                    pin = _pin(port, bit)
                    e = out.setdefault(pin, {'mode': '', 'pull': 'none', 'initial': '', 'init': fn, 'source': ''})
                    where = '%s %s(): %s' % (src, fn, code.strip())
                    if reg == 'DDR':
                        e['mode'] = 'output' if op == '|=' else 'input'
                        e['initial'] = 'low' if op == '|=' else ''   # a fresh output pin: PORT bit 0 after reset, so low until written
                    else:
                        if op == '|=':
                            e['pull'] = 'up' if e['mode'] == 'input' else e['pull']
                            if e['mode'] == 'output':
                                e['initial'] = 'high'
                    e['source'] = (e['source'] + '; ' if e['source'] else '') + where
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


def pin_writer(config, manager=None):
    """-> {'pin': 'D6', 'field': 'led_on', 'writers': [...], 'reader': 'led_follow_state', 'levels': ['low', 'high'], 'source': words} or None."""
    from board.custom import firmware_state as FS
    doc = FS.derive(config, manager)
    for f in doc['fields']:
        if f.get('controls'):
            m = re.match(r'(\w+) \((\w+)\) via (\w+)', f['controls'])
            if not m:
                continue
            writers = [w.split(' ')[0] for w in f['writers'].split(', ') if w and not w.startswith('main')]
            return {'pin': m.group(1), 'knob': m.group(2), 'reader': m.group(3), 'field': f['field'], 'object': f['object'], 'writers': sorted(set(writers)),
                    'levels': ['low', 'high'], 'direction': f['direction'],
                    'source': 'the parsed atoms (board.custom.firmware_state): %s.%s is written by %s and read by %s, which drives %s (hal_led) to the field\'s value'
                              % (f['object'], f['field'], ', '.join(sorted(set(writers))), m.group(3), m.group(1))}
    return None


def press_record(config):
    """The committed press-latency record of the config, or None."""
    from board.custom import press_latency as PL
    p = os.path.join(os.path.dirname(os.path.abspath(PL.__file__)), 'press_records', '%s.json' % config)
    if not os.path.isfile(p):
        return None
    r = json.load(open(p))
    return {'best_ms': r.get('best_ms'), 'worst_ms': r.get('worst_ms'), 'sha256': r.get('record_sha256', ''), 'what': r.get('what', ''), 'runs': len(r.get('runs') or []),
            'file': 'board/custom/press_records/%s.json' % config, 'recorded_at': r.get('recorded_at', '')}


def claimed_pins(config, manager=None):
    """The board pins the config's binding claims (cmod.custom.claims.pin_claims over its graph), as canonical names (D2, D3, D6, D0, D1)."""
    from cmod.custom import claims as C
    from cmod.custom.graph_seed import SEED_GRAPHS
    graph = next((g['name'] for g in SEED_GRAPHS if g.get('base_configuration') == config), None)
    if graph is None:
        graph = next((g['name'] for g in SEED_GRAPHS if config.startswith(g['name'].replace('-graph', ''))), '')
    try:
        return sorted({c['board_pin'].split(':')[-1] for c in C.pin_claims('%s@arduino-uno-r3' % config, graph, manager=manager)})
    except Exception:   # noqa: BLE001 — no binding for this config: the HAL init modes still name the pins
        return []


def circuit_for(config, tables, manager=None):
    """-> (circuit name, why) — the CircuitDefinition whose BoardPinNet rows cover the most of the pins the config's HAL init touches / its binding claims."""
    pins = set(hal_init_modes(config)) | set(claimed_pins(config, manager))
    pin_nets = tables.get('BoardPinNet') or []
    score = {}
    for pn in pin_nets:
        c = pn.get('circuit')
        if not c:
            continue
        canon = (pn.get('board_pin') or '').split(':')[-1]
        score.setdefault(c, set())
        if canon in pins:
            score[c].add(canon)
    if not score:
        raise SourceRefused('no CircuitDefinition has BoardPinNet rows, so no bench circuit can be matched to %s' % config)
    best = max(score.items(), key=lambda kv: (len(kv[1]), kv[0]))
    if not best[1]:
        raise SourceRefused('no bench circuit names a pin %s uses (%s) — wire one as CircuitDefinition + BoardPinNet rows first' % (config, ', '.join(sorted(pins))))
    ties = [c for c, s in score.items() if len(s) == len(best[1]) and c != best[0]]
    return best[0], 'circuit %s carries %s of the pins %s uses (%s)%s' % (best[0], len(best[1]), config, ', '.join(sorted(best[1])),
                                                                          ('; tied with %s, the first by name taken' % ', '.join(ties)) if ties else '')
