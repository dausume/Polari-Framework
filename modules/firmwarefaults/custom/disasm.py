"""
@module firmwarefaults.custom.disasm

RESOLVE A STEP AGAINST ONE BUILD'S ELF (FIRMWARE_SCENARIO_PLAN.md §1: "symbol+offset so a rebuild re-resolves the
address"): `avr-objdump -d` and `avr-nm -n` through the engines seam, parsed here. The pattern sc-0 needs is
`lds-sequence`: inside function F, the loads of variable V (`lds rN, 0x…  ; 0x80…  <V>` then `<V+0x1>` …) — the PC of
load k is where an interrupt must be taken for the ISR to run between loads k-1 and k.

Also: a symbol table (byte addresses for text, data addresses for SRAM symbols), symbol+offset of any PC, the
instruction text at a PC (the trace rows), and the static cycle count of a straight-line function (AVR instruction
timing, ATmega328P datasheet §31 "Instruction Set Summary" — only the opcodes listed here; anything else → unknown).
"""
import re

_INS = re.compile(r'^\s+([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*(\S+)\s*([^;]*?)\s*(?:;\s*(.*))?$')
_LABEL = re.compile(r'^([0-9a-f]+) <([^>]+)>:$')
_NM = re.compile(r'^([0-9a-f]+) ([A-Za-z]) (\S+)$')
#: cycles per opcode on the ATmega328P (datasheet "Instruction Set Summary"); 2-word branches/calls are not here
CYCLES = {'lds': 2, 'sts': 2, 'in': 1, 'out': 1, 'cli': 1, 'sei': 1, 'mov': 1, 'movw': 1, 'ldi': 1, 'push': 2, 'pop': 2, 'ret': 4,
          'reti': 4, 'nop': 1, 'eor': 1, 'and': 1, 'or': 1, 'add': 1, 'adc': 1, 'sub': 1, 'sbc': 1, 'cpi': 1, 'cp': 1, 'cpc': 1}


def parse_nm(text):
    """{symbol: {'addr', 'type', 'space': 'text'|'data'}} — data symbols as SRAM addresses (0x800000 stripped)."""
    out = {}
    for line in text.splitlines():
        m = _NM.match(line.strip())
        if not m:
            continue
        a, t, n = int(m.group(1), 16), m.group(2), m.group(3)
        space = 'data' if a >= 0x800000 else 'text'
        out[n] = {'addr': a - 0x800000 if space == 'data' else a, 'type': t, 'space': space}
    return out


def parse_objdump(text):
    """{'functions': {name: [ins...]}, 'by_pc': {pc: ins}} with ins = {'pc', 'op', 'args', 'comment', 'bytes', 'fn'}."""
    fns, by_pc, cur = {}, {}, None
    for line in text.splitlines():
        m = _LABEL.match(line.strip())
        if m:
            cur = m.group(2)
            fns.setdefault(cur, [])
            continue
        m = _INS.match(line)
        if m and cur is not None:
            ins = {'pc': int(m.group(1), 16), 'bytes': len(m.group(2).split()), 'op': m.group(3), 'args': m.group(4).strip(),
                   'comment': (m.group(5) or '').strip(), 'fn': cur}
            fns[cur].append(ins)
            by_pc[ins['pc']] = ins
    return {'functions': fns, 'by_pc': by_pc}


def lds_sequence(dis, fn, var):
    """The loads of `var` inside `fn`, in order: [{'pc', 'reg', 'byte'}] — byte 0 is `<var>`, byte k `<var+0xk>`."""
    out = []
    for ins in dis['functions'].get(fn, []):
        if ins['op'] != 'lds':
            continue
        m = re.search(r'<%s(?:\+0x([0-9a-f]+))?>' % re.escape(var), ins['comment'])
        if m:
            out.append({'pc': ins['pc'], 'reg': ins['args'].split(',')[0].strip(), 'byte': int(m.group(1) or '0', 16)})
    return out


def ret_pc(dis, fn):
    rets = [i['pc'] for i in dis['functions'].get(fn, []) if i['op'] in ('ret', 'reti')]
    return rets[-1] if rets else None


def static_cycles(dis, fn):
    """Cycles of a STRAIGHT-LINE function from entry to (and including) its ret; None if it branches or uses an opcode
    not in CYCLES (never a guess)."""
    total = 0
    for ins in dis['functions'].get(fn, []):
        c = CYCLES.get(ins['op'])
        if c is None:
            return None
        total += c
    return total or None


def symbolize(nm, pc):
    """symbol+0xoff for a text byte address (the nearest text symbol at or below it)."""
    vec = nm.get('__vectors')
    if vec and vec['addr'] <= pc < vec['addr'] + 26 * 4:   # the ATmega328P vector table: 26 vectors x 4 B (a jmp each)
        return '__vectors+0x%x (vector %d)' % (pc - vec['addr'], (pc - vec['addr']) // 4)
    cands = [(s['addr'], not n.startswith('__'), n) for n, s in nm.items()
             # T/t = code; W only when it is not a linker marker at 0 (__heap_end, __vector_default)
             if s['space'] == 'text' and (s['type'] in 'Tt' or (s['type'] in 'Ww' and s['addr'] > 0)) and s['addr'] <= pc and not n.startswith('.')]
    best = (max(cands)[2], max(cands)[0]) if cands else None   # the nearest at or below; on a tie a plain name beats a __ one
    if best is None:
        return '0x%x' % pc
    off = pc - best[1]
    return best[0] if off == 0 else '%s+0x%x' % (best[0], off)


def instruction_at(dis, pc):
    ins = dis['by_pc'].get(pc)
    return ('%s %s' % (ins['op'], ins['args'])).strip() if ins else ''


def resolve_step(step_args, dis, nm, vector_size=4):
    """A step's args against THIS build → {'ok', 'pc', 'vec', 'why', 'loads', 'ret_pc', 'isr'}; ok False = inapplicable here
    (the function, the variable's loads or the ISR do not exist in this build), with the reason."""
    fn, var = step_args.get('symbol'), step_args.get('of')
    vec = int(step_args.get('vec', 0))
    isr = '__vector_%d' % vec
    out = {'ok': False, 'vec': vec, 'isr': isr, 'loads': [], 'ret_pc': None, 'pc': None}
    if isr not in nm:
        out['why'] = 'no %s in this build (vector %d %s has no ISR)' % (isr, vec, step_args.get('vector_name', ''))
        return out
    if fn not in dis['functions']:
        out['why'] = 'no function %s in this build' % fn
        return out
    if step_args.get('pattern') != 'lds-sequence':
        out['why'] = 'unknown pattern %r' % step_args.get('pattern')
        return out
    loads = lds_sequence(dis, fn, var)
    out['loads'] = loads
    out['ret_pc'] = ret_pc(dis, fn)
    k = int(step_args.get('before_load', 2))
    if len(loads) < k:
        out['why'] = '%s has %d load(s) of %s — no load %d to interrupt before (a single-load read cannot tear)' % (fn, len(loads), var, k)
        return out
    out.update(ok=True, pc=loads[k - 1]['pc'], why='%s: load %d of %s (%s) at 0x%x' % (fn, k, var, loads[k - 1]['reg'], loads[k - 1]['pc']))
    return out
