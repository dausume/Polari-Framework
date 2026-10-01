"""
@module board.custom.board_engines

THE ENGINES SEAM of the board arc — the same ladder as computelod.custom.eda_engines (D-brd-1/2: engines chosen
dynamically per device kind), so a toolchain or flasher runs wherever the topology says and the module never assumes
a device. brd-0 RESOLVES only; nothing is run here (the build/flash verbs and the worker image are brd-1).

Resolution, per engine, honest at every rung:
  1. BOARD_ENGINES_URL set        → that worker, ALWAYS (unreachable or lacking the engine = REFUSAL; a declared
                                    worker never silently degrades to local)
  2. knob unset, binary local     → the binary on the PATH (or ~/.local/bin)
  3. nothing local                → the topology's provider for module `board.engines` (LIVE candidates only)
  4. nothing                      → refusal naming the knob, the provider module, and that the worker image is brd-1
FLASHING adds a placement constraint (plan §2): it must run on the host holding the USB port — a remote worker is
refused for a flash, whatever the ladder says.

`ENGINES` also carries each engine's KIND, which is RULE 2's vocabulary: microcontroller and hardware work is C,
Verilog or SystemVerilog only, so an engine is a c-compiler, an hdl-toolchain, a flasher, or a simulator — an Arduino
core, MicroPython or a VHDL flow has no kind here and fails the rule by construction.
"""
import json
import os
import shutil
import time

KNOB = 'BOARD_ENGINES_URL'
PROVIDER_MODULE = 'board.engines'
REMOTE = 'remote'
_ENGINE = 'board'
#: RULE 2: the only engine kinds the board arc admits
RULE2_KINDS = ('c-compiler', 'hdl-toolchain', 'flasher', 'simulator')
#: engine name → (binary, kind, licence note)
ENGINES = {
    'avr-gcc': ('avr-gcc', 'c-compiler', 'GPL-3.0+ with the runtime exception; avr-libc modified BSD'),
    'avr-objcopy': ('avr-objcopy', 'c-compiler', 'binutils, GPL-3.0+'),
    'avr-size': ('avr-size', 'c-compiler', 'binutils, GPL-3.0+'),
    'avrdude': ('avrdude', 'flasher', 'GPL-2.0 (github.com/avrdudes/avrdude)'),
    'simavr': ('simavr', 'simulator', 'GPL-3.0 (github.com/buserror/simavr)'),
    'riscv-gcc': ('riscv64-unknown-elf-gcc', 'c-compiler', 'GPL-3.0+ with the runtime exception'),
    'arm-gcc': ('arm-none-eabi-gcc', 'c-compiler', 'GPL-3.0+ with the runtime exception'),
    'esptool': ('esptool.py', 'flasher', 'GPL-2.0+'),
    'dfu-util': ('dfu-util', 'flasher', 'GPL-2.0+'),
    'openocd': ('openocd', 'flasher', 'GPL-2.0+'),
    'wchisp': ('wchisp', 'flasher', 'open reimplementation; licence unverified (register §1 ch32v203)'),
    'wlink': ('wlink', 'flasher', 'MIT OR Apache-2.0 (register §1 ch32v003)'),
    'uf2-copy': ('cp', 'flasher', 'coreutils (a mass-storage copy)'),
    'dd': ('dd', 'flasher', 'coreutils (a mass-storage write)'),
    'openfpgaloader': ('openFPGALoader', 'flasher', 'Apache-2.0'),
    'change-gateware': ('ssh', 'flasher', 'runs change-gateware.sh ON the board over the USB network'),
    'yosys': ('yosys', 'hdl-toolchain', 'ISC'),
    'nextpnr-ice40': ('nextpnr-ice40', 'hdl-toolchain', 'ISC'),
    'libero': ('libero', 'hdl-toolchain', 'PROPRIETARY (Microchip Libero SoC, Silver licence) — an engine only, D-brd-2'),
}
_CAP_CACHE = {}
_CAP_TTL_S = 30.0


def knob_url():
    return os.environ.get(KNOB, '').rstrip('/')


def engine_kind(engine):
    return ENGINES.get(engine, ('', '', ''))[1]


def rule2_ok(engine):
    """RULE 2 for one engine name: known, and of a C / Verilog-SystemVerilog / flasher / simulator kind."""
    return engine_kind(engine) in RULE2_KINDS


def topology_url():
    try:
        from topology.provider_registry import resolve_provider
        resolved = resolve_provider(PROVIDER_MODULE)
        if resolved.get('ok'):
            return resolved['url'].rstrip('/')
    except Exception:
        pass
    return ''


def remote_capability(url, timeout=5):
    now = time.time()
    cached = _CAP_CACHE.get(url)
    if cached and now - cached[0] < _CAP_TTL_S:
        return cached[1]
    cap = None
    try:
        from polariApiServer import outbound
        with outbound.http_request('engine', _ENGINE, 'GET', '%s/capability' % url, means='probe', timeout=timeout, lib='urllib') as response:
            cap = json.load(response)
    except Exception:
        cap = None
    _CAP_CACHE[url] = (now, cap)
    return cap


def _has(cap, engine):
    return bool(cap and (cap.get('engines') or {}).get(engine, {}).get('available'))


def local_binary(engine):
    b = ENGINES[engine][0]
    for cand in (shutil.which(b), os.path.expanduser('~/.local/bin/%s' % b)):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def _refusal(engine, flash):
    tail = ' (flashing: a local binary on the host holding the USB port)' if flash else ''
    return ('no %s: not on the PATH here, no live %s provider — set %s or `pol allocate %s <instance>`%s; '
            'the board engines worker image arrives with brd-1' % (engine, PROVIDER_MODULE, KNOB, PROVIDER_MODULE, tail))


def resolve(engine, flash=False):
    """{'how': 'remote'|'local-binary'|'refused', 'where', 'why', 'kind'} for ONE engine. flash=True adds the
    placement rule: only the host holding the USB port may flash."""
    if engine not in ENGINES:
        return {'how': 'refused', 'where': '', 'kind': '', 'why': 'unknown engine %r — one of %s' % (engine, sorted(ENGINES))}
    kind = engine_kind(engine)
    url = knob_url()
    if url:
        if flash:
            return {'how': 'refused', 'where': url, 'kind': kind, 'why': '%s=%s names a worker, but flashing runs only on the host holding the USB port (plan §2) — unset it on that host or install %s there' % (KNOB, url, engine)}
        cap = remote_capability(url)
        if cap is None:
            return {'how': 'refused', 'where': url, 'kind': kind, 'why': '%s=%s is set but the worker is unreachable — refusing (a declared worker never silently falls back to local)' % (KNOB, url)}
        if not _has(cap, engine):
            return {'how': 'refused', 'where': url, 'kind': kind, 'why': '%s=%s reached but that worker lacks %s' % (KNOB, url, engine)}
        return {'how': REMOTE, 'where': url, 'kind': kind, 'why': 'knob'}
    b = local_binary(engine)
    if b:
        return {'how': 'local-binary', 'where': b, 'kind': kind, 'why': 'on this device'}
    if not flash:
        url = topology_url()
        if url and _has(remote_capability(url), engine):
            return {'how': REMOTE, 'where': url, 'kind': kind, 'why': 'topology provider %s' % PROVIDER_MODULE}
    return {'how': 'refused', 'where': '', 'kind': kind, 'why': _refusal(engine, flash)}


def placement(engines=None):
    """Where each engine WOULD run, before any dispatch (GET /api/board/engines)."""
    names = list(engines or ENGINES)
    return {'knob': KNOB, 'knob_value': knob_url(), 'provider_module': PROVIDER_MODULE,
            'engines': {e: resolve(e) for e in names},
            'ladder': ['%s (always, or refusal; never for a flash)' % KNOB, 'local binary', 'topology provider %s (live only; never for a flash)' % PROVIDER_MODULE, 'refusal'],
            'rule2_kinds': list(RULE2_KINDS)}
