"""
@module cmod.custom.cmod_engines

cmod's engines, resolved THROUGH THE BOARD ENGINES SEAM (board.custom.board_engines: BOARD_ENGINES_URL → local binary →
the local image prf-board-engines:trixie → topology provider board.engines → refusal). The module never assumes a device
(his rule 2026-09-24). Parsing needs NO engine (pycparser, in the framework process); only the COST does:

  avr-gcc   the measurement compile (-fstack-usage; once as shipped, once -fno-inline for an atom's standalone cost)
  avr-nm    per-function text bytes (`avr-nm -S --size-sort`) — binutils in the same image (the worker's /run lists it)
  make      the proof that a project builds with make ALONE — it runs where avr-gcc runs (the same rung), because make
            without the toolchain beside it proves nothing; the remote worker has no make → refused, never faked
"""
import os
import shutil

from board.custom import board_engines as be
from board.custom import engine_run

EXTRA = {'avr-nm': ('avr-nm', 'c-compiler', 'binutils, GPL-3.0+'), 'make': ('make', 'c-compiler', 'GNU make, GPL-3.0+'),
         'cmake': ('cmake', 'c-compiler', 'Kitware CMake, BSD-3-Clause')}   # ucd-0f: the exported project's build (beside avr-gcc, like make)
USED = ('avr-gcc', 'avr-nm', 'make', 'cmake')


def resolve(engine):
    if engine in be.ENGINES:
        return be.resolve(engine)
    if engine not in EXTRA:
        return {'how': 'refused', 'where': '', 'why': 'unknown engine %r' % engine}
    binary = EXTRA[engine][0]
    if engine in ('make', 'cmake'):
        g = be.resolve('avr-gcc')
        if g['how'] == 'local-binary':
            w = shutil.which(engine)
            return {'how': 'local-binary', 'where': w, 'why': 'beside the local avr-gcc'} if w else \
                {'how': 'refused', 'where': '', 'why': 'avr-gcc is local but %s is not on the PATH' % engine}
        if g['how'] == be.LOCAL_IMAGE:
            return {'how': be.LOCAL_IMAGE, 'where': g['where'], 'why': 'the board engines image (%s + avr-gcc)' % engine}
        return {'how': 'refused', 'where': g.get('where', ''), 'why': 'avr-gcc resolves to %s (%s); the board worker runs single engines, not %s' % (g['how'], g.get('where', ''), engine)}
    url = be.knob_url()
    if url:
        cap = be.remote_capability(url)
        if cap is None or not be._has(cap, engine):
            return {'how': 'refused', 'where': url, 'why': '%s=%s is unreachable or lacks %s' % (be.KNOB, url, engine)}
        return {'how': be.REMOTE, 'where': url, 'why': 'knob'}
    for cand in (shutil.which(binary), os.path.expanduser('~/.local/bin/%s' % binary)):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return {'how': 'local-binary', 'where': cand, 'why': 'on this device'}
    if be.local_image():
        return {'how': be.LOCAL_IMAGE, 'where': be.image_name(), 'why': 'the board engines image on this device'}
    turl = be.topology_url()
    if turl and be._has(be.remote_capability(turl), engine):
        return {'how': be.REMOTE, 'where': turl, 'why': 'topology provider %s' % be.PROVIDER_MODULE}
    return {'how': 'refused', 'where': '', 'why': 'no %s: not here, no %s image, no live %s provider' % (engine, be.image_name(), be.PROVIDER_MODULE)}


def run(engine, args, files=None, timeout=300):
    """engine_run.run for board's engines; the same rungs for avr-nm / make. Raises engine_run.EngineRefused."""
    if engine in be.ENGINES:
        return engine_run.run(engine, args, files or {}, timeout=timeout)
    where = resolve(engine)
    if where['how'] == 'refused':
        raise engine_run.EngineRefused(where['why'])
    binary = EXTRA[engine][0]
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
