"""selftest_export — ucd-0f: the firmware export (cmod.custom.export_cmake). The directory a person carries away: the
rendered C byte for byte, CMakeLists.txt with the Makefile's flags and the board/twin/size/flash targets, the toolchain
file, the one-command build, a README rendered from the rows, polari-export.json with every sha; refusals named; the
CMake build verified on the engines rung when it is there (parity with the Makefile build), said when it is not.
Run by cmod_selftest.main() (export_parts).
"""
import json
import os
import tempfile


def export_parts(check):
    def firmware_export():
        _run(check)
    return (firmware_export,)


def _run(check):
    from cmod.custom import export_cmake as EX
    from cmod.custom import firmware_cli as CLI
    from cmod.custom import glue as GL

    fs = CLI._solution('uno-sim-rig')
    tmp = tempfile.mkdtemp(prefix='polari-exp-selftest-')
    row = EX.export(fs, target='both', out_root=tmp)
    d = row['path']
    files = sorted(os.listdir(d))
    check('export: the directory holds the rendered C project + CMakeLists.txt + toolchain + one-command build + README + manifest',
          {'hal.c', 'hal.h', 'polari_graph.c', 'polari_graph.h', 'board_config.h', 'Makefile', 'polari-firmware.json', 'CMakeLists.txt',
           'avr-gcc.toolchain.cmake', 'polari-build.cmake', 'README.md', 'polari-export.json'} <= set(files), str(files))
    g = __import__('cmod.custom.graph_seed', fromlist=['seed_graph']).seed_graph(fs['graph'])['graph']
    src = GL.project_dir(g)
    same = all(open(os.path.join(d, f), 'rb').read() == open(os.path.join(src, f), 'rb').read()
               for f in files if f in os.listdir(src) and not f.startswith('firmware.'))
    check('export: the C project files are BYTE FOR BYTE the committed render (nothing rewritten on the way out)', same)
    cm = open(os.path.join(d, 'CMakeLists.txt')).read()
    check('export: CMakeLists carries the Makefile\'s exact flags, the toolchain, and the board / twin / size / flash targets',
          all(x in cm for x in ('-mmcu=${MCU} -Os -std=gnu99 -Wall -Wextra -Werror -ffunction-sections -fdata-sections', '-Wl,--gc-sections',
                                'avr-gcc.toolchain.cmake', 'add_custom_target(board ALL', 'add_custom_target(twin', 'add_custom_target(size',
                                'add_custom_target(flash', '-b 115200 -D -U', 'POLARI_TARGET')))
    man = json.load(open(os.path.join(d, 'polari-export.json')))
    import hashlib
    shas_ok = all(hashlib.sha256(open(os.path.join(d, f['file']), 'rb').read()).hexdigest() == f['sha256'] for f in man['files'])
    check('export: polari-export.json names the solution, graph, board as DATA (usb ids, programmer, baud) and every file\'s sha256 (all match)',
          man['solution'] == 'uno-sim-rig' and man['board']['name'] == 'arduino-uno-r3' and man['board']['usb_ids'] and man['board']['programmer']
          and man['board']['baud'] == 115200 and shas_ok and man['makefile_hex_sha256'])
    rd = open(os.path.join(d, 'README.md')).read()
    check('export: the README explains itself — build, the two cases, the flash gate, the board, tasks by lane, the register map, sizes, shas, provenance',
          all(h in rd for h in ('## Build (no Polari)', '## The two cases', '## Flash (the gate)', '## The board', '## Tasks and schedule', '## Register map',
                                '## Sizes', '## Files (sha256)', '## Provenance')) and 'adc' in rd.lower() and 'A0' in rd)
    check('export: the tar.gz exists beside the directory and its sha is recorded', os.path.isfile(row['tar_path']) and row['tar_sha256']
          and row['download_url'] == '/api/firmware/exports/%s/download' % row['name'])
    check('export: a bad target is refused by name', _refused(EX, fs, target='rtl', out_root=tmp, needle='rtl'))
    check('export: a solution whose graph has no render is refused by name',
          _refused(EX, dict(fs, name='x', graph='no-such-graph'), out_root=tmp, needle='no graph'))
    # the proof: the exported CMake build on the engines rung, compared with the Makefile build
    v = EX.verify(d, row['makefile_sha256'])
    if v['parity'] == 'not-run':
        check('export: verify REFUSED honestly (no cmake rung here): %s' % v['verify_log'][:120], 'refused' in v['verify_log'] or 'failed' in v['verify_log'])
    else:
        check('export: the exported CMake build produced firmware.hex on the engines rung (parity with the Makefile build: %s)' % v['parity'],
              v['status'] == 'verified' and v['cmake_sha256'] and v['parity'] in ('identical', 'differs'))
        check('export: parity is IDENTICAL — the same bytes the proven Makefile build made', v['parity'] == 'identical', v['verify_log'][-300:])
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


def _refused(EX, fs, needle, **kw):
    try:
        EX.export(fs, **kw)
    except EX.ExportRefused as e:
        return needle in str(e)
    return False
