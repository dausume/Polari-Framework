"""
@module cmod.custom.approach_profile_atoms

rt-0 (MISSION_PROFILE_SOLVER_PLAN.md section 8.2): what the C ATOMS themselves say about time, read off the committed manifests and the atoms' own
source - never typed. For one atom (and everything it calls that is itself an atom):

  cycles_ub   an UPPER BOUND on the CPU cycles of one run, only when the code has no loop and calls nothing outside the atoms:
              (the atom's text_bytes_noinline / 2 instructions) x 4 cycles. Every AVR instruction is 2 or 4 bytes, so bytes/2 is at least the
              instruction count of a straight path; no instruction of the ATmega328P takes more than 4 cycles (the datasheet's Instruction Set
              Summary; this slice did not re-read that table, so the bound is ESTIMATED, not measured). No per-atom cycle count is measured
              yet (a twin cycle count per task closes this).
  blocking    a busy-wait on a hardware flag (`while (!(REG & _BV(FLAG))) { }`): the CPU spins until the flag sets. The USART transmit-empty
              wait has a duration that can be worked out (one byte = 10 bit times at the baud rate); any other flag is named and left
              undetermined.
  unbounded   the reasons this profiler cannot bound the atom: a loop that is not a recognised busy-wait, or a call to code outside the atoms
              (generated headers, libc).
"""
import math
import re

KINDS = ('measured', 'estimated', 'cited', 'criterion', 'undetermined')
MAX_CYCLES_PER_INSTRUCTION = 4
BYTES_PER_INSTRUCTION = 2

_BUSY = re.compile(r'while\s*\(\s*!?\s*\(?\s*(\w+)\s*&\s*_BV\(\s*(\w+)\s*\)\s*\)?\s*\)\s*(?:\{\s*\}|;)')
_BYTE_LOOP = re.compile(r'while\s*\(\s*(\w+)\s*--\s*\)')
_LOOP = re.compile(r'\b(for|while|do)\b')


def q(kind, value, unit, basis):
    """One labelled number: {kind, value, unit, basis}; kind is one of KINDS; value None = undetermined (the basis says why)."""
    assert kind in KINDS, kind
    return {'kind': kind, 'value': value, 'unit': unit, 'basis': basis}


def undetermined(why, unit=''):
    return q('undetermined', None, unit, why)


def text(quantity):
    """A quantity as plain words: '9.6 ms (estimated)' / 'undetermined'."""
    if quantity is None or quantity.get('value') is None:
        return 'undetermined'
    v, unit = quantity['value'], quantity.get('unit', '')
    if unit == 'us' and isinstance(v, (int, float)) and abs(v) >= 1000:
        v, unit = v / 1000.0, 'ms'
    v = (('%.1f' % v).rstrip('0').rstrip('.') if abs(v) < 1e6 else '%.3g' % v) if isinstance(v, float) else str(v)
    return ('%s %s (%s)' % (v, unit, quantity['kind'])).replace('  ', ' ')


def _functions(project):
    from cmod.custom import code_interface as CI
    out = {}
    for p, _m, a in CI._manifest_candidates():   # fgm-5a: several isotopes of one job share a function name (hal_take_toggle_pending); the FIRST - the shipped hal.c one, sorted before hal_button_*.c - answers
        if p == project:
            out.setdefault(a['function'], a)
    return out


def _body(project, atom):
    from cmod.custom import code_interface as CI
    from cmod.custom import projects as P
    from cmod.custom.annotation import _strip_comments
    spec = P.resolve(project)
    _path, lines, _s, _e = CI._function_span(spec['root'], atom['module'], atom['line'])
    return _strip_comments('\n'.join(lines))


def scan_body(src):
    """{busy_waits: [(register, flag)], byte_loops: [var], other_loops: n} over a comment-stripped function body."""
    waits = [(m.group(1), m.group(2)) for m in _BUSY.finditer(src)]
    rest = _BUSY.sub('', src)
    # drop the signature's own braces from consideration: keywords only count inside the body
    body = rest[rest.find('{') + 1:] if '{' in rest else rest
    bl = [m.group(1) for m in _BYTE_LOOP.finditer(body)]
    other = len(_LOOP.findall(_BYTE_LOOP.sub('', body)))
    return {'busy_waits': waits, 'byte_loops': bl, 'other_loops': other}


def analyse(project, atom, ctx, _seen=None):
    """-> {atom, cycles_ub (int, the bounded part), bounded (bool), blocking [ops], unbounded [reasons], text_bytes, stack_bytes, peripherals [ids]}.
    ctx = {baud, frame_bytes} - what a recognised transmit wait needs to become a duration."""
    seen = set(_seen or ())
    cost = atom.get('cost') or {}
    tb = cost.get('text_bytes_noinline')
    if tb is None:
        tb = cost.get('text_bytes')
    out = {'atom': atom['name'], 'cycles_ub': 0, 'bounded': True, 'blocking': [], 'unbounded': [], 'text_bytes': tb,
           'stack_bytes': cost.get('stack_bytes'), 'peripherals': sorted({r['peripheral'] for r in atom.get('resources', []) if r.get('peripheral')})}
    if tb is None:
        out['bounded'] = False
        out['unbounded'].append('%s has no measured size, so no cycle bound' % atom['name'])
        return out
    try:
        scan = scan_body(_body(project, atom))
    except Exception as e:  # noqa: BLE001 - an unreadable body is unbounded, said
        out['bounded'] = False
        out['unbounded'].append('%s: source not readable (%s)' % (atom['name'], e))
        return out
    out['cycles_ub'] = int(math.ceil(tb / float(BYTES_PER_INSTRUCTION))) * MAX_CYCLES_PER_INSTRUCTION
    for reg, flag in scan['busy_waits']:
        out['blocking'].append(_blocking_op(atom['name'], reg, flag, scan['byte_loops'], ctx))
    if scan['other_loops'] or (scan['byte_loops'] and not any(f == 'UDRE0' for _r, f in scan['busy_waits'])):
        out['bounded'] = False
        out['unbounded'].append('%s contains %d loop(s) that are not a recognised wait on a hardware flag' % (
            atom['name'], scan['other_loops'] + (len(scan['byte_loops']) if not scan['busy_waits'] else 0)))
    fns = _functions(project)
    seen.add(atom['name'])
    for c in atom.get('calls', []):
        callee = fns.get(c)
        if callee is None:
            out['bounded'] = False
            out['unbounded'].append('%s calls %s, which is outside the atoms (generated or library code)' % (atom['name'], c))
        elif callee['name'] in seen:
            out['bounded'] = False
            out['unbounded'].append('%s is recursive through %s' % (atom['name'], callee['name']))
        else:
            sub = analyse(project, callee, ctx, seen)
            out['cycles_ub'] += sub['cycles_ub']
            out['blocking'] += sub['blocking']
            out['unbounded'] += sub['unbounded']
            out['bounded'] = out['bounded'] and sub['bounded']
            out['peripherals'] = sorted(set(out['peripherals']) | set(sub['peripherals']))
            out['stack_bytes'] = max(out['stack_bytes'] or 0, sub['stack_bytes'] or 0)
    return out


def _blocking_op(atom, reg, flag, byte_loops, ctx):
    if flag == 'UDRE0':
        baud, frame = ctx.get('baud'), ctx.get('frame_bytes')
        if baud and frame:
            per_byte_us = 10.0 / baud * 1e6
            return {'atom': atom, 'kind': 'usart-transmit-wait', 'what': 'waits on UDRE0 (USART0 transmit register empty) before each byte it sends',
                    'worst_us': q('estimated', round(frame * per_byte_us, 1), 'us',
                                  'at most %d bytes (header + the class payload maximum + CRC, from the generated packets header) x 10 bit times at %d Bd '
                                  '(8N1 = 10 bits/byte); the wait ends when the shifter frees, so this is the transmit time, not a measurement' % (frame, baud))}
        return {'atom': atom, 'kind': 'usart-transmit-wait', 'what': 'waits on UDRE0 before each byte it sends',
                'worst_us': undetermined('the baud rate or the largest frame is not known here')}
    return {'atom': atom, 'kind': 'flag-wait', 'what': 'waits on %s.%s to set' % (reg, flag),
            'worst_us': undetermined('how long %s.%s takes to set is not derived by this profiler (the peripheral\'s timing is not read)' % (reg, flag))}


def cycles_to_us(cycles, clock_hz):
    return cycles / float(clock_hz) * 1e6
