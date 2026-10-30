"""
@module electrodevice.custom.ngspice_shared_runner

kxc-3: run ONE SPICE deck through ngspice's SHARED LIBRARY (libngspice, which KiCad ships) and print the result vectors as JSON on stdout. A standalone
script (no framework imports) so it runs in its own process - bounded by the caller's timeout, and a solver crash takes only this process down
(electrodevice.custom.ngspice_shared.run). Usage: python3 -I ngspice_shared_runner.py <deck.cir>   (run with the deck's directory as the cwd, so
.include paths resolve)

Output: {"ok", "plot", "vectors": {name: {"real": [...]} | {"mag": [...], "phase_deg": [...]}}, "errors": [...], "library": path}
"""
import ctypes
import ctypes.util
import json
import math
import sys


class _VecInfo(ctypes.Structure):
    _fields_ = [('name', ctypes.c_char_p), ('type', ctypes.c_int), ('flags', ctypes.c_short), ('realdata', ctypes.POINTER(ctypes.c_double)),
                ('compdata', ctypes.POINTER(ctypes.c_double)), ('length', ctypes.c_int)]


def main(path):
    name = ctypes.util.find_library('ngspice') or 'libngspice.so.0'
    lib = ctypes.CDLL(name)
    out = []
    char_cb = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)(lambda s, i, p: out.append(s.decode(errors='replace')) or 0)
    stat_cb = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)(lambda s, i, p: 0)
    exit_cb = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)(lambda *a: 0)
    lib.ngSpice_Init(char_cb, stat_cb, exit_cb, None, None, None, None)
    lines = [ln for ln in open(path).read().splitlines() if ln.strip()]
    arr = (ctypes.c_char_p * (len(lines) + 1))(*[ln.encode() for ln in lines], None)
    lib.ngSpice_Circ(arr)
    lib.ngSpice_Command(b'run')
    lib.ngGet_Vec_Info.restype = ctypes.POINTER(_VecInfo)
    lib.ngSpice_CurPlot.restype = ctypes.c_char_p
    lib.ngSpice_AllVecs.restype = ctypes.POINTER(ctypes.c_char_p)
    plot = lib.ngSpice_CurPlot().decode()
    vecs, i, res = lib.ngSpice_AllVecs(plot.encode()), 0, {}
    while vecs[i]:
        vn = vecs[i].decode()
        vi = lib.ngGet_Vec_Info(('%s.%s' % (plot, vn)).encode()).contents
        if vi.realdata:
            res[vn] = {'real': [vi.realdata[k] for k in range(vi.length)]}
        elif vi.compdata:
            re_im = [(vi.compdata[2 * k], vi.compdata[2 * k + 1]) for k in range(vi.length)]
            res[vn] = {'mag': [math.hypot(a, b) for a, b in re_im], 'phase_deg': [math.degrees(math.atan2(b, a)) for a, b in re_im]}
        i += 1
    errors = [ln for ln in out if 'rror' in ln]
    print(json.dumps({'ok': not errors and bool(res), 'plot': plot, 'vectors': res, 'errors': errors[:20], 'library': name}))


if __name__ == '__main__':
    main(sys.argv[1])
