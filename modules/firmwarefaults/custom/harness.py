"""
@module firmwarefaults.custom.harness

RENDER A SCENARIO INTO HARNESS FLAGS and run the twin once (FIRMWARE_SCENARIO_PLAN.md §2a): every step resolved
against THIS build's ELF (custom/disasm.py), the always-on measurements added (--sp-watch, --stack-fill from __bss_end,
--isr-latency, --fn-cycles over the guarded function, --uart-out, --seed), free-running (no wall clock in the loop —
a run = f(firmware, flags, seed)). The twin runs through the engines seam (local binary, the board engines image, or
the worker's POST /run); its files come back as bytes.
"""
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
            if step['kind'] == 'irq-at-pc':
                spec = 'pc=0x%x,vec=%d,shots=%d' % (res['pc'], res['vec'], int(args.get('shots', 1)))
                if cond.get('symbol') in nm:
                    spec += ',when=0x%x/%d&0x%x=0x%x' % (nm[cond['symbol']]['addr'], int(cond['width']), int(cond['mask']), int(cond['value']))
                a += ['--irq-at', spec]
            elif step['kind'] == 'irq-at-cycle':
                a += ['--irq-at', 'cycle=%d,vec=%d' % (int(args['cycle']), int(args['vec']))]
            elif step['kind'] == 'corrupt-word':
                addr = nm[args['symbol']]['addr'] if args.get('symbol') in nm else int(str(args['addr']), 0)
                a += ['--poke', '0x%x/%d=0x%x@%d' % (addr, int(args.get('width', 1)), int(args['value']), int(args['cycle']))]
        a += ['--trace-vcd', VCD, '--trace-window', '%d:%d' % trace_window]
    return a


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
