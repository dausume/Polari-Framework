"""
@module cmod.custom.measure

THE COST OF EACH ATOM (C_MODULARIZATION_PLAN.md §9; the cost rule 2026-09-26; conventions as firmwarefaults/COST.md):
compile the project with ITS OWN Makefile flags (CC / CFLAGS / LDFLAGS read from the Makefile — never a second copy of
them) plus `-fstack-usage`, twice:

  shipped    exactly the Makefile build (+ MEASURE_FLAGS: -fstack-usage, -Wno-error — neither changes code) — the atom's bytes in the firmware as it
             ships; a static function GCC inlined into its caller has NO symbol: text 0, `inlined` (never a guess)
  noinline   the same + `-fno-inline` and `-Wl,--no-gc-sections` — what the atom costs as a separate node (what generated
             glue that calls it as a function would pay); every function has a symbol and a .su frame, even one nothing
             calls in that configuration (hal_presses: the twin reads its counter, no C caller)

text = `nm -S --size-sort` (avr-nm on the engine rung; the host's nm for a host project), stack = GCC's own .su frame
(bytes + static | dynamic | dynamic,bounded) — the frame of the function itself, not its call chain (the chain peak is
firmwarefaults.custom.stack_static's job). An ISR's symbol is avr-libc's `__vector_<n>` (registers.py vectors).
"""
import hashlib
import os
import re
import shutil

from board.custom import engine_run
from cmod.custom import cmod_engines as CE

_ASSIGN = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*(?::?=|\?=)\s*(.*)$')
_NM = re.compile(r'^([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([tTwW])\s+(\S+)$')
_SU = re.compile(r'^(.*?):(\d+):(\d+):(\S+)\t(\d+)\t(\S+)$')


#: added to the Makefile's flags for the measurement builds only. -fstack-usage changes no code; -Wno-error because GCC
#: WARNS (unconditionally) that it cannot compute a naked function's stack (hal_wdt_boot under HAL_WDT) and the
#: Makefile's -Werror would turn the measurement into a refusal — the Makefile's own -Werror build is proven by make_alone.
MEASURE_FLAGS = ['-fstack-usage', '-Wno-error']


class MeasureRefused(RuntimeError):
    pass


def makefile_vars(path):
    """NAME = value / := / ?= lines with $(VAR) expansion (no functions, no targets) — enough for a plain firmware Makefile;
    what it cannot expand stays as written and the caller refuses."""
    raw = {}
    for line in open(path).read().replace('\\\n', ' ').splitlines():
        if line.startswith('\t') or line.lstrip().startswith('#'):
            continue
        m = _ASSIGN.match(line.strip())
        if m:
            raw[m.group(1)] = m.group(2).split('#')[0].strip()

    def expand(v, depth=0):
        if depth > 8:
            return v
        return re.sub(r'\$\((\w+)\)', lambda mm: expand(raw.get(mm.group(1), ''), depth + 1) if mm.group(1) in raw else mm.group(0), v)
    return {k: expand(v) for k, v in raw.items()}


def build_flags(project_dir):
    mf = os.path.join(project_dir, 'Makefile')
    if not os.path.isfile(mf):
        raise MeasureRefused('no Makefile in %s' % project_dir)
    v = makefile_vars(mf)
    cc = v.get('CC', 'cc')
    cflags, ldflags = v.get('CFLAGS', '').split(), v.get('LDFLAGS', '').split()
    if any('$(' in x for x in cflags + ldflags + [cc]):
        raise MeasureRefused('the Makefile flags use make functions cmod does not expand: %s' % ' '.join(cflags))
    return cc, cflags, ldflags


def _runner(cc):
    """(compile engine name, nm engine name, run function). avr-gcc → the board seam; a host compiler → this host."""
    if cc.startswith('avr-'):
        return 'avr-gcc', 'avr-nm', CE.run

    def host(engine, args, files=None, timeout=300):
        binary = shutil.which({'cc': cc, 'nm': 'nm'}[engine])
        if not binary:
            raise engine_run.EngineRefused('%s is not on this host' % engine)
        r = engine_run._local(binary, args, files or {}, timeout)
        r.update(how='local-binary', where=binary)
        return r
    return 'cc', 'nm', host


def base_symbol(name):
    """GCC's clones (`f.constprop.0`, `f.isra.0`, `f.part.0`) are the function f — their bytes are its bytes."""
    return re.sub(r'(\.(constprop|isra|part|cold|lto_priv)(\.\d+)?)+$', '', name)


def parse_nm(text):
    out = {}
    for line in text.splitlines():
        m = _NM.match(line.strip())
        if m:
            b = base_symbol(m.group(4))
            out[b] = out.get(b, 0) + int(m.group(2), 16)
    return out


def parse_su(texts):
    out = {}
    for t in texts:
        for line in t.splitlines():
            m = _SU.match(line.strip())
            if m:
                b = base_symbol(m.group(4))
                prev = out.get(b, {}).get('bytes', 0)
                out[b] = {'bytes': max(prev, int(m.group(5))), 'kind': m.group(6), 'file': os.path.basename(m.group(1)), 'line': int(m.group(2))}
    return out


def measure(project_dir, sources):
    """→ {'cc', 'cflags', 'ldflags', 'engine': {how, where}, 'modes': {shipped|noinline: {text, stack, elf_sha256}}}."""
    cc, cflags, ldflags = build_flags(project_dir)
    ce, ne, run = _runner(cc)
    files = {fn: open(os.path.join(project_dir, fn), 'rb').read() for fn in sorted(os.listdir(project_dir)) if fn.endswith(('.c', '.h'))}
    out = {'cc': cc, 'cflags': cflags, 'ldflags': ldflags, 'modes': {}}
    for mode, extra, ldx in (('shipped', [], []), ('noinline', ['-fno-inline'], ['-Wl,--no-gc-sections'])):
        r = run(ce, cflags + extra + MEASURE_FLAGS + ldflags + ldx + ['-o', 'firmware.elf'] + list(sources), files)
        if not r.get('ok') or 'firmware.elf' not in r.get('files', {}):
            raise MeasureRefused('%s (%s) failed: %s' % (cc, mode, (r.get('stderr') or '')[-600:]))
        elf = r['files']['firmware.elf']
        su = [v.decode(errors='replace') for k, v in r['files'].items() if k.endswith('.su')]
        n = run(ne, ['-S', '--size-sort', 'firmware.elf'], {'firmware.elf': elf})
        if not n.get('ok'):
            raise MeasureRefused('nm failed: %s' % (n.get('stderr') or '')[-300:])
        out['modes'][mode] = {'text': parse_nm(n['stdout']), 'stack': parse_su(su), 'elf_sha256': hashlib.sha256(elf).hexdigest(),
                              'elf_bytes': len(elf)}
        out['engine'] = {'how': r.get('how', ''), 'where': r.get('where', ''), 'cost': r.get('cost', {})}
    return out


def make_alone(project_dir):
    """The proof a project builds with `make` alone (no Polari in the loop): make's default target in a copy of the project
    on the rung avr-gcc runs on → {ok, hex_sha256, stdout tail, how, where}."""
    files = {fn: open(os.path.join(project_dir, fn), 'rb').read() for fn in sorted(os.listdir(project_dir))
             if fn.endswith(('.c', '.h')) or fn == 'Makefile'}
    r = CE.run('make', [], files)
    hexd = r.get('files', {}).get('firmware.hex')
    return {'ok': bool(r.get('ok') and hexd), 'hex_sha256': hashlib.sha256(hexd).hexdigest() if hexd else '', 'how': r.get('how', ''),
            'where': r.get('where', ''), 'tail': (r.get('stdout') or '')[-400:], 'stderr': (r.get('stderr') or '')[-400:]}
