"""
@module firmwarefaults.custom.fault_engines

The scenario module's engines, resolved THROUGH THE BOARD ENGINES SEAM (board.custom.board_engines — the same knob
BOARD_ENGINES_URL, the same image prf-board-engines:trixie, the same topology provider board.engines, the same honest
refusal). The module never assumes a device (his rule 2026-09-24): the twin and the disassembler run wherever that
ladder says.

  avr-twin     polari-avr-twin with the sc-0 scenario flags (twin_forcing.c) — board's engine, reused as is
  avr-gcc      the -fstack-usage / -fcallgraph-info compile (the static stack peak) — board's engine
  avr-size     the section sizes per build — board's engine
  avr-objdump  the disassembly a scenario resolves its PCs against (the `lds` sequence of g_ms in hal_millis)
  avr-nm       the symbol table (__bss_end for the stack paint, symbol names for the trace rows)
  vcd-window   pyvcd (MIT) reading the twin's VCD into the "cycles around the fault" rows (polari-vcd-window)

The last three are binutils / pyvcd in the SAME image (sc-0 added them to the worker's /run table); board's own
ENGINES table is left as board owns it, so this module carries their entries here and runs them through
board.custom.engine_run's rungs (local binary → `docker run` of the image → the worker's POST /run).
"""
from board.custom import board_engines as be
from board.custom import engine_run

#: engine → (binary, kind, licence) — RULE 2's vocabulary: every one is a c-compiler-family tool or a simulator
EXTRA_ENGINES = {
    'avr-objdump': ('avr-objdump', 'c-compiler', 'binutils, GPL-3.0+'),
    'avr-nm': ('avr-nm', 'c-compiler', 'binutils, GPL-3.0+'),
    'vcd-window': ('polari-vcd-window', 'simulator', 'pyvcd 0.5.0, MIT (installed by sha256 in prf-board-engines); the script is ours'),
}
USED = ('avr-twin', 'avr-gcc', 'avr-size', 'avr-objdump', 'avr-nm', 'vcd-window')


def resolve(engine):
    """Where ONE engine would run — board's ladder, with this module's three extra engines known to it."""
    if engine in be.ENGINES:
        return be.resolve(engine)
    if engine not in EXTRA_ENGINES:
        return {'how': 'refused', 'where': '', 'kind': '', 'why': 'unknown engine %r' % engine}
    binary, kind, _ = EXTRA_ENGINES[engine]
    url = be.knob_url()
    if url:
        cap = be.remote_capability(url)
        if cap is None:
            return {'how': 'refused', 'where': url, 'kind': kind, 'why': '%s=%s is set but the worker is unreachable' % (be.KNOB, url)}
        if not be._has(cap, engine):
            return {'how': 'refused', 'where': url, 'kind': kind, 'why': '%s=%s lacks %s (an image older than sc-0 — rebuild it)' % (be.KNOB, url, engine)}
        return {'how': be.REMOTE, 'where': url, 'kind': kind, 'why': 'knob'}
    import os
    import shutil
    for cand in (shutil.which(binary), os.path.expanduser('~/.local/bin/%s' % binary)):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return {'how': 'local-binary', 'where': cand, 'kind': kind, 'why': 'on this device'}
    if be.local_image():
        return {'how': be.LOCAL_IMAGE, 'where': be.image_name(), 'kind': kind, 'why': 'the board engines image on this device'}
    turl = be.topology_url()
    if turl and be._has(be.remote_capability(turl), engine):
        return {'how': be.REMOTE, 'where': turl, 'kind': kind, 'why': 'topology provider %s' % be.PROVIDER_MODULE}
    return {'how': 'refused', 'where': '', 'kind': kind,
            'why': 'no %s: not here, no %s image, no live %s provider — build polari-rf-node/docker-compose.board-engines.yml' % (engine, be.image_name(), be.PROVIDER_MODULE)}


def run(engine, args, files=None, timeout=300):
    """engine_run.run for board's engines; the same rungs for the three extra ones. Raises engine_run.EngineRefused."""
    if engine in be.ENGINES:
        return engine_run.run(engine, args, files or {}, timeout=timeout)
    where = resolve(engine)
    if where['how'] == 'refused':
        raise engine_run.EngineRefused(where['why'])
    binary = EXTRA_ENGINES[engine][0]
    if where['how'] == 'local-binary':
        res = engine_run._local(where['where'], args, files or {}, timeout)
    elif where['how'] == be.LOCAL_IMAGE:
        res = engine_run._local(binary, args, files or {}, timeout, prefix=engine_run.docker_prefix(where['where']))
    else:
        res = engine_run._remote(where['where'], engine, args, files or {}, timeout)
    res.update(how=where['how'], where=where['where'])
    return res


def placement():
    return {e: resolve(e) for e in USED}


def available():
    """True when the twin AND the disassembler resolve somewhere (the probe skips honestly otherwise)."""
    return all(resolve(e)['how'] != 'refused' for e in ('avr-twin', 'avr-objdump', 'avr-gcc'))


def harness_digest():
    """What identifies the harness that produced a run: the image id on the local-image rung, else the binary path /
    worker URL (the run row records it — a run is a function of the row, the ELF, THIS and the seed)."""
    w = resolve('avr-twin')
    if w['how'] == be.LOCAL_IMAGE:
        return 'image %s %s' % (be.image_name(), be.local_image())
    return '%s %s' % (w['how'], w['where'])
