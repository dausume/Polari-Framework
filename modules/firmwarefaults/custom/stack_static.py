"""
@module firmwarefaults.custom.stack_static

THE STATIC STACK PEAK (FIRMWARE_SCENARIO_PLAN.md §4, D-sc-6): avr-gcc's own `-fstack-usage` (per-function frame bytes,
.su) and `-fcallgraph-info=su` (the call graph with those frames, .ci in VCG text) — GCC's built-in equivalent of
avstack.pl's .su + objdump call-graph walk, so no extra script is vendored. Peak = the deepest call chain from `main`
(frame bytes + 2 B return address per call, + 2 B for crt's `call main`) + the largest ISR frame (+ 2 B pushed PC;
ISRs do not nest on the AVR: SREG.I is cleared on entry).

Honest about what it cannot see: library functions with no .su (strcpy, memmove, libgcc's float and division
routines) count 0 B and are LISTED; a recursive cycle is refused (no peak), never truncated. The measured high-water
(--sp-watch, --stack-fill) is the truth; this is the cross-check.
"""
import re

_NODE = re.compile(r'node:\s*\{\s*title:\s*"([^"]+)"\s*label:\s*"([^"]*)"')
_EDGE = re.compile(r'edge:\s*\{\s*sourcename:\s*"([^"]+)"\s*targetname:\s*"([^"]+)"')
_BYTES = re.compile(r'(\d+) bytes \((static|dynamic[^)]*)\)')


def parse_ci(texts):
    """{node: frame bytes or None}, {node: set(callees)}, {node: plain name} over several .ci files."""
    frames, edges, names = {}, {}, {}
    for text in texts:
        for title, label in _NODE.findall(text):
            m = _BYTES.search(label.replace('\\n', '\n'))
            names[title] = label.split('\\n')[0]
            if m:
                frames[title] = int(m.group(1))
            else:
                frames.setdefault(title, None)
        for s, t in _EDGE.findall(text):
            edges.setdefault(s, set()).add(t)
    return frames, edges, names


def peak(frames, edges, names, root='main'):
    """{'ok', 'peak_bytes', 'main_chain', 'main_bytes', 'isr', 'isr_bytes', 'uncounted', 'why'}."""
    uncounted = sorted({names.get(n, n) for n, f in frames.items() if f is None})
    memo, onstack = {}, set()

    def depth(n):
        if n in memo:
            return memo[n]
        if n in onstack:
            raise ValueError('recursion through %s' % names.get(n, n))
        onstack.add(n)
        best, chain = 0, []
        for c in sorted(edges.get(n, ())):
            d, ch = depth(c)
            if d + 2 > best:
                best, chain = d + 2, ch
        onstack.discard(n)
        memo[n] = ((frames.get(n) or 0) + best, [names.get(n, n)] + chain)
        return memo[n]

    if root not in frames:
        return {'ok': False, 'why': 'no %s in the call graph' % root, 'uncounted': uncounted}
    try:
        main_b, main_chain = depth(root)
        isrs = [(depth(n)[0] + 2, names.get(n, n)) for n in frames if names.get(n, n).startswith('__vector_')]
    except ValueError as e:
        return {'ok': False, 'why': '%s — a static peak needs an acyclic call graph' % e, 'uncounted': uncounted}
    isr_b, isr = max(isrs) if isrs else (0, '')
    return {'ok': True, 'peak_bytes': main_b + 2 + isr_b, 'main_bytes': main_b + 2, 'main_chain': main_chain, 'isr': isr, 'isr_bytes': isr_b,
            'uncounted': uncounted,
            'method': 'avr-gcc -fstack-usage -fcallgraph-info=su: deepest chain from main (+2 B per call, +2 B crt call) + the largest ISR (+2 B PC)'}
