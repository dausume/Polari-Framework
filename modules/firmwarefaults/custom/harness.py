"""
@module firmwarefaults.custom.harness

RENDER A SCENARIO INTO HARNESS FLAGS and run the twin once (FIRMWARE_SCENARIO_PLAN.md §2a): every step resolved
against THIS build's ELF (custom/disasm.py), the always-on measurements added (--sp-watch, --stack-fill from __bss_end,
--isr-latency, --fn-cycles over the guarded function, --uart-out, --seed), free-running (no wall clock in the loop —
a run = f(firmware, flags, seed)). The twin runs through the engines seam (local binary, the board engines image, or
the worker's POST /run); its files come back as bytes.

ucd-0d (UNO_CORE_DEMO_PLAN.md §5g): `irq-at-cycle` stays exactly as is (button-bounce-double-count and the other sc-1
scenarios already use it, raising a VECTOR at a cycle — fine for an edge train that does not need EICRA/EIMSK to be
real). NEW button scenarios use `pin-at` instead: {cycle, pin, level} → --pin-at, a LEVEL forced onto the pin itself,
so the simulated EICRA/EIMSK decide whether a vector fires at all (board.board_pinlevel_selftest.pin_parts is the
proof, on the twin directly — no Scenario row needs this kind yet).
"""
import hashlib
import json

from firmwarefaults.custom import fault_engines as fe

UART = 'uart.bin'
VCD = 'trace.vcd'


def render(resolved_steps, nm, seconds, seed, watch=None, fn=None, trace_window=(48, 160), adc0_mv=750, forcing=True):
    """resolved_steps: [(step, resolution)] with resolution from disasm.resolve_step; nm: parse_nm output.
    watch: (symbol, width); fn: (start_pc, end_pc). → argv (without the binary)."""
    a = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '%g' % seconds, '--status-ms', '0',
         '--adc0-mv', str(int(adc0_mv)), '--uart-out', UART, '--seed', str(int(seed)), '--sp-watch', '--isr-latency']
    if '__bss_end' in nm:
        a += ['--stack-fill', '0x%x' % nm['__bss_end']['addr']]
    if fn and fn[0] is not None and fn[1] is not None:
        a += ['--fn-cycles', '0x%x:0x%x' % fn]
    if watch and watch[0] in nm:
        a += ['--watch', '0x%x/%d=%s' % (nm[watch[0]]['addr'], watch[1], watch[0])]
    if forcing:
        for step, res in resolved_steps:
            args = json.loads(step['args_json'])
            cond = json.loads(step.get('condition_json') or '{}')
            if step['kind'] in ('irq-at-pc', 'align-at-pc'):
                spec = 'pc=0x%x,vec=%d,shots=%d' % (res['pc'], res['vec'], int(args.get('shots', 1)))
                if cond.get('symbol') in nm:
                    spec += ',when=0x%x/%d&0x%x=0x%x' % (nm[cond['symbol']]['addr'], int(cond['width']), int(cond['mask']), int(cond['value']))
                a += ['--irq-at' if step['kind'] == 'irq-at-pc' else '--align-at-pc', spec]
            elif step['kind'] == 'flip-bit-at-cycle':
                a += ['--flip-bit', flip_spec(args, nm)]
            elif step['kind'] == 'irq-at-cycle':
                a += ['--irq-at', 'cycle=%d,vec=%d' % (int(args['cycle']), int(args['vec']))]
            elif step['kind'] == 'corrupt-word':
                addr = nm[args['symbol']]['addr'] if args.get('symbol') in nm else int(str(args['addr']), 0)
                a += ['--poke', '0x%x/%d=0x%x@%d' % (addr, int(args.get('width', 1)), int(args['value']), int(args['cycle']))]
        a += ['--trace-vcd', VCD, '--trace-window', '%d:%d' % trace_window]
    return a


def flip_spec(args, nm):
    """flip-bit-at-cycle args {symbol|addr, byte (offset), bit, cycle} → '0xADDR:BIT@CYCLE' (the symbol re-resolved per build)."""
    base = nm[args['symbol']]['addr'] if args.get('symbol') in nm else int(str(args['addr']), 0)
    return '0x%x:%d@%d' % (base + int(args.get('byte', 0)), int(args['bit']), int(args['cycle']))


def run(argv, hex_bytes, timeout=600):
    """→ {'ok', 'final' (the {"t":"scenario"} line), 'uart' bytes, 'vcd' bytes, 'stdout', 'how', 'where', 'cost', 'argv'}"""
    r = fe.run('avr-twin', argv, {'firmware.hex': hex_bytes}, timeout=timeout)
    final = None
    for line in (r.get('stdout') or '').splitlines():
        if line.startswith('{"t":"scenario"'):
            try:
                final = json.loads(line)
            except ValueError:
                final = None
    files = r.get('files') or {}
    return {'ok': r.get('ok') and final is not None, 'final': final, 'uart': files.get(UART, b''), 'vcd': files.get(VCD, b''),
            'stdout': r.get('stdout', ''), 'stderr': r.get('stderr', ''), 'how': r.get('how'), 'where': r.get('where'),
            'cost': r.get('cost', {}), 'argv': ['polari-avr-twin'] + list(argv)}


def window(vcd_bytes, center, before=12, after=36):
    """The VCD samples around `center` through pyvcd on the engine side (vcd-window). → list of dicts, sha, reader."""
    r = fe.run('vcd-window', [VCD, '--center', str(int(center)), '--before', str(int(before)), '--after', str(int(after))], {VCD: vcd_bytes}, timeout=120)
    try:
        d = json.loads(r.get('stdout') or '{}')
    except ValueError:
        d = {}
    return d.get('samples') or [], d.get('sha256', ''), d.get('reader', ''), r


# ---------------------------------------------------------------- sc-1: the host side, the power rail, the runaway
TXLOG = 'tx.bin'
RXLOG = 'rx.bin'


def variant_flags(variant):
    """{FLAG: int} of a scenario variant's build flags (the payload builders need e.g. SC_EEPROM_RECORD's layout)."""
    from firmwarefaults.custom.scenarios import scenario_variants
    for v in scenario_variants():
        if v['name'] == variant:
            return {f.split('=')[0]: int(f.split('=')[1]) for f in json.loads(v.get('build_flags_json') or '[]')}
    return {}


def render_sc1(steps, nm, seconds, seed, observe=None, variant='', adc0_mv=750, extra_steps=(), fn=None):
    """sc-1 steps (+ the statistics tier's extra steps) → (argv, files, meta). meta: what the host sent (for the ideal
    count), the symbols each step resolved to, and `missing` — a symbol a step needs that this build lacks (the run is
    then inapplicable here, with that reason)."""
    from firmwarefaults.custom import payloads
    observe = observe or {}
    a = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '%g' % seconds, '--status-ms', '0',
         '--adc0-mv', str(int(adc0_mv)), '--uart-out', UART, '--uart-tx-log', TXLOG, '--seed', str(int(seed)), '--sp-watch', '--isr-latency']
    files, meta = {}, {'sent': 0, 'injected': [], 'resolved': [], 'missing': [], 'host_bytes_sha256': []}
    if '__bss_end' in nm:
        a += ['--stack-fill', '0x%x' % nm['__bss_end']['addr']]
    for sym, w in observe.get('watch', []):
        if sym in nm and nm[sym]['space'] == 'data':
            a += ['--watch', '0x%x/%d=%s' % (nm[sym]['addr'], int(w), sym)]
    if fn and fn[0] is not None:      # the function that prices the technique: entry → its return, whichever ret (SP mode)
        a += ['--fn-cycles', '0x%x:ret' % fn[0]]
    if observe.get('eeprom_dump'):
        a += ['--eeprom-dump', '0x%x:%d' % tuple(observe['eeprom_dump'])]
    flags = variant_flags(variant)
    host = False
    for k, step in enumerate(list(steps) + list(extra_steps)):
        args = json.loads(step['args_json']) if isinstance(step.get('args_json'), str) else dict(step.get('args') or {})
        kind = step['kind']
        if kind == 'irq-at-cycle':
            a += ['--irq-at', 'cycle=%d,vec=%d' % (int(args['cycle']), int(args['vec']))]
        elif kind == 'pin-at':   # ucd-0d: a LEVEL on the pin, not a vector — new button scenarios use this
            a += ['--pin-at', 'cycle=%d,pin=%s,level=%d' % (int(args['cycle']), args['pin'], int(args['level']))]
        elif kind == 'respond':
            body = payloads.ack() if args.get('reply') == 'ack' else bytes.fromhex(args['reply_hex'])
            fname = 'reply%d.bin' % k
            files[fname] = body
            a += ['--respond', '0x%s=%s,delay=%d,max=%d' % (args['match'], fname, int(args.get('delay_cycles', 0)), int(args.get('max', 1 << 20)))]
            host = True
        elif kind == 'drop-nth-frame':
            d = args.get('direction', 'rx')
            if d == 'rx':
                a += ['--drop-frame', 'rx:%d' % int(args['n'])]
            elif d == 'tx':        # sc-2: board→host (the Nth frame, optionally of one msg_type)
                a += ['--drop-frame', 'tx:%d' % int(args['n']) + (',type=0x%x' % int(args['msg_type']) if args.get('msg_type') is not None else '')]
            else:
                raise ValueError('drop-nth-frame: direction must be rx (host→board) or tx (board→host), not %r' % d)
        elif kind == 'drop-prob':  # sc-2: each host→board unit lost with probability p, from the seed
            a += ['--drop-frame', 'rx:p=%g' % float(args['p'])]
        elif kind == 'flip-bit-at-cycle':
            if args.get('symbol') and args['symbol'] not in nm:
                meta['missing'].append('no %s in this build (the bit flip is aimed at it)' % args['symbol'])
                continue
            a += ['--flip-bit', flip_spec(args, nm)]
        elif kind == 'inject-bytes':
            p = args['payload']
            if p == 'residual':
                body, info = payloads.residual(int(args.get('trailing_bytes', 10)))
            elif p == 'record-command':
                body, info = payloads.command(1, int(args['value'])), {'sent': 1}
            elif p == 'command-stream':
                body, info = payloads.command_stream(int(args['n']))
            else:
                raise ValueError('unknown inject payload %r' % p)
            fname = 'inject%d.bin' % k
            files[fname] = body
            meta['sent'] += int(info.get('sent', 0))
            meta['injected'].append(body)
            a += ['--inject', '%s@%d' % (fname, int(args['cycle']))]
            host = True
        elif kind == 'eeprom-preload':
            layout = flags.get('SC_EEPROM_RECORD') if args.get('layout') == 'from-variant' else args.get('layout')
            if not layout:
                meta['missing'].append('variant %s has no EEPROM record layout (SC_EEPROM_RECORD unset)' % variant)
                continue
            for addr, body in payloads.eeprom_record(layout, int(args['value'])):
                a += ['--eeprom-set', '0x%x=%s' % (addr, body.hex())]
        elif kind == 'reset-at':
            if 'symbol' in args:
                if args['symbol'] not in nm:
                    meta['missing'].append('no %s in this build (the reset is aimed at its entry)' % args['symbol'])
                    continue
                pc = nm[args['symbol']]['addr']
                meta['resolved'].append('%s = 0x%x' % (args['symbol'], pc))
                a += ['--reset-at', 'pc=0x%x,nth=%d,after=%d' % (pc, int(args.get('nth', 1)), int(args.get('after_cycle', 0)))]
            else:
                a += ['--reset-at', 'cycle=%d' % int(args['cycle'])]
        elif kind == 'jump-at':
            if args['symbol'] not in nm:
                meta['missing'].append('no %s in this build' % args['symbol'])
                continue
            pc = nm[args['symbol']]['addr']
            meta['resolved'].append('%s = 0x%x' % (args['symbol'], pc))
            meta['jump_cycle'] = int(args['cycle'])
            a += ['--jump-at', 'cycle=%d,pc=0x%x' % (int(args['cycle']), pc)]
        elif kind == 'uart-ber':
            a += ['--uart-ber', '%g' % float(args['p'])]
        elif kind == 'rx-noise':
            a += ['--rx-noise', '%g' % float(args['rate'])]
            host = True
        elif kind == 'ret-log':
            a += ['--ret-log', '%d:%s' % (int(args['vec']), args.get('file', 'retlog.txt'))]
        else:
            raise ValueError('step kind %s is not rendered by render_sc1' % kind)
    if host:
        a += ['--uart-rx-log', RXLOG]
    meta['host_bytes_sha256'] = [hashlib.sha256(x).hexdigest() for x in meta['injected']] + \
        [hashlib.sha256(v).hexdigest() for k2, v in sorted(files.items()) if k2.startswith('reply')]
    return a, files, meta


def run_files(argv, hex_bytes, files, timeout=600):
    """harness.run with extra input files (payloads); returns the logs too."""
    r = fe.run('avr-twin', argv, dict(files, **{'firmware.hex': hex_bytes}), timeout=timeout)
    final = None
    for line in (r.get('stdout') or '').splitlines():
        if line.startswith('{"t":"scenario"'):
            try:
                final = json.loads(line)
            except ValueError:
                final = None
    out = r.get('files') or {}
    return {'ok': r.get('ok') is not False and final is not None, 'final': final, 'uart': out.get(UART, b''), 'tx': out.get(TXLOG, b''),
            'rx': out.get(RXLOG, b''), 'files': out, 'stdout': r.get('stdout', ''), 'stderr': r.get('stderr', ''), 'how': r.get('how'),
            'where': r.get('where'), 'cost': r.get('cost', {}), 'argv': ['polari-avr-twin'] + list(argv), 'returncode': r.get('returncode')}
