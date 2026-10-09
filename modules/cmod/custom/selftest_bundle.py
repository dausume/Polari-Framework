"""selftest_bundle — ucd-frames+bundle (UNO_CORE_DEMO_PLAN.md §5b): the two new export forms over
cmod.custom.export_cmake — `install-bundle` (ONLY what a person flashes with: firmware.hex + polari-install.json +
INSTALL.md, no sources) and `solution` (the board-agnostic C + graph/requirements/purposes as data, no
pin_config.*/board_config.h/Makefile — "builds nothing by itself"). Both FirmwareExport rows record their own `form`;
`source-dir`'s own selftest (selftest_export.export_parts) is unchanged — proving the existing form still passes.
Run by cmod_selftest.main() (bundle_parts).
"""
import json
import os
import tempfile


def bundle_parts(check):
    def install_bundle():
        _run_install_bundle(check)

    def solution_export():
        _run_solution(check)
    return (install_bundle, solution_export)


def _run_install_bundle(check):
    from cmod.custom import export_cmake as EX
    from cmod.custom import firmware_cli as CLI

    fs = CLI._solution('uno-button-clock')
    tmp = tempfile.mkdtemp(prefix='polari-bundle-selftest-')
    row = EX.export(fs, target='board', out_root=tmp, form='install-bundle')
    check('install-bundle: FirmwareExport row records form=install-bundle', row['form'] == 'install-bundle', row['form'])
    d = row['path']
    files = sorted(os.listdir(d))
    check('install-bundle: EXACTLY the three files (firmware.hex, polari-install.json, INSTALL.md) — no sources',
          set(files) == {'firmware.hex', 'polari-install.json', 'INSTALL.md'}, str(files))
    manifest = json.loads(open(os.path.join(d, 'polari-install.json')).read())
    import hashlib
    hexb = open(os.path.join(d, 'firmware.hex'), 'rb').read()
    hex_sha = hashlib.sha256(hexb).hexdigest()
    check('install-bundle: firmware.hex\'s own sha256 equals the manifest\'s hex_sha256', hex_sha == manifest['hex_sha256'],
          '%s vs %s' % (hex_sha[:16], manifest.get('hex_sha256', '')[:16]))
    from cmod.custom import glue as GL
    from cmod.custom.graph_seed import seed_graph
    g = seed_graph(fs['graph'])['graph']
    record = GL.load_record(fs['graph'])
    glue_sha = ((record or {}).get('build') or {}).get('hex_sha256', '')
    check('install-bundle: the hex matches the glue record\'s own hex_sha256 (the gate)', bool(glue_sha) and hex_sha == glue_sha,
          '%s vs glue %s' % (hex_sha[:16], glue_sha[:16]))
    argv_text = manifest.get('argv_text', '')
    check('install-bundle: the argv is avrdude -p atmega328p -c arduino -P <port> -b 115200 -D -U flash:w:firmware.hex:i',
          argv_text == 'avrdude -p atmega328p -c arduino -P <port> -b 115200 -D -U flash:w:firmware.hex:i', argv_text)
    install_md = open(os.path.join(d, 'INSTALL.md')).read()
    check('install-bundle: INSTALL.md carries the advice line verbatim', manifest['proof']['advice'] in install_md,
          manifest['proof'].get('advice', ''))
    check('install-bundle: INSTALL.md names the sha gate (compare the sha first)', 'sha' in install_md.lower() and 'first' in install_md.lower())


def _run_solution(check):
    from cmod.custom import export_cmake as EX
    from cmod.custom import firmware_cli as CLI

    fs = CLI._solution('uno-button-clock')
    tmp = tempfile.mkdtemp(prefix='polari-solution-selftest-')
    row = EX.export(fs, out_root=tmp, form='solution')
    check('solution: FirmwareExport row records form=solution', row['form'] == 'solution', row['form'])
    d = row['path']
    files = set(os.listdir(d))
    check('solution: no pin_config.*, no board_config.h, no Makefile',
          not (files & {'pin_config.c', 'pin_config.h', 'board_config.h', 'Makefile'}), str(sorted(files)))
    check('solution: carries the atoms\' own C (hal.c/h + the app\'s rendered C) + graph/requirements/purposes/manifest/README',
          {'hal.c', 'hal.h', 'polari_graph.c', 'polari_graph.h', 'graph.json', 'requirements.json', 'purposes.json',
           'README.md', 'polari-solution.json'} <= files, str(sorted(files)))
    reqs = json.loads(open(os.path.join(d, 'requirements.json')).read())
    check('solution: requirements.json has rows', len(reqs) > 0)
    check('solution: requirements.json rows carry NO lives_on', all('lives_on' not in r for r in reqs))
    check('solution: requirements.json rows carry kind/role/required/resource_kind/constraints',
          all(all(k in r for k in ('kind', 'role', 'required', 'resource_kind', 'constraints')) for r in reqs))
    graph_doc = json.loads(open(os.path.join(d, 'graph.json')).read())
    from cmod.custom.graph_seed import seed_graph
    seeded = seed_graph(fs['graph'])
    check('solution: graph.json node count equals the seeded graph\'s', len(graph_doc['nodes']) == len(seeded['nodes']),
          '%d vs %d' % (len(graph_doc['nodes']), len(seeded['nodes'])))
    check('solution: graph.json edge count equals the seeded graph\'s', len(graph_doc['edges']) == len(seeded['edges']))
    purposes = json.loads(open(os.path.join(d, 'purposes.json')).read())
    check('solution: purposes.json names the solution\'s own Purpose(s)', any(p['name'] == 'button-clock-to-os' for p in purposes),
          str(purposes))
    readme = open(os.path.join(d, 'README.md')).read()
    check('solution: README names the requirements a board must meet',
          'Requirements' in readme and 'requirements.json' in readme)
    check('solution: README says this folder builds nothing by itself', 'builds nothing by itself' in readme)
    check('solution: README names how to bind it to a board', 'pol firmware bind' in readme)
    manifest = json.loads(open(os.path.join(d, 'polari-solution.json')).read())
    check('solution: polari-solution.json records the manifest + shas', manifest.get('form') == 'solution' and
          all('sha256' in f for f in manifest.get('files', [])))
