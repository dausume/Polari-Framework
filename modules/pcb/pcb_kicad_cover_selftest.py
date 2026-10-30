"""pcb_kicad_cover_selftest - kxc-1 (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md): INGEST ENCAPSULATES EVERYTHING (his ruling 2026-10-30:
Polari is the source of truth; nothing KiCad wrote is dropped silently). Fixtures: KiCad's own demos from Debian's kicad-demos 9.0.2
(GPL-2+, custom/upstream/kicad-demos-9.0.2/SOURCE.json): complex_hierarchy (one child sheet, ampli_ht.kicad_sch, used TWICE),
simulation/rectifier (simulation fields + a diode.mod model file), ecc83 (the pcb-0 board).
Run by pcb_selftest.main().
"""
import json
import os
import shutil
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEMOS = os.path.join(HERE, 'custom', 'upstream', 'kicad-demos-9.0.2')


def _read(sub, board):
    from pcb.custom import kicad_read as K
    d = os.path.join(DEMOS, sub)
    files = K.read_dir(d)
    return files, K.read_project(files, board, binaries=K.binaries_in(d))


def run_kicad_cover(check):
    from pcb.custom import kicad_cover as C
    from pcb.custom import kicad_read as K

    files, r = _read('complex_hierarchy', 'complex_hierarchy')
    on_disk = sorted(os.path.relpath(os.path.join(dp, f), os.path.join(DEMOS, 'complex_hierarchy'))
                     for dp, _, fs in os.walk(os.path.join(DEMOS, 'complex_hierarchy')) for f in fs)
    arts = {a['path']: a for a in r['KiCadArtifact']}
    check('KXC-1 ARTIFACTS: every file of the project directory is a KiCadArtifact (17: schematics, board, project, symbol library, lib tables, '
          'ten project footprints) with its sha256 and size; the text is kept byte for byte; the files rows were read from are "typed"',
          sorted(arts) == on_disk and all(a['content'] == files[a['path']] and a['sha256'] == C.sha(files[a['path']]) for a in arts.values())
          and {p for p, a in arts.items() if a['handling'] == 'typed'} == {'complex_hierarchy.kicad_sch', 'ampli_ht.kicad_sch', 'complex_hierarchy.kicad_pcb',
                                                                          'sym-lib-table', 'fp-lib-table'}, sorted(set(on_disk) ^ set(arts)))
    sheets = [(s['path'], s['file']) for s in r['SchematicSheet']]
    child = [s for s in r['SchematicSymbol'] if s['file'] == 'ampli_ht.kicad_sch']
    paths = sorted({s['instance_path'] for s in child})
    check('KXC-1 SHEETS BY INSTANCE: ampli_ht.kicad_sch is used twice -> two sheet instances, and each instance\'s symbols are rows with their OWN '
          'references (KiCad\'s per-instance (path "/<root>/<sheet>")) - 92 child-sheet symbol rows (46 per instance; 90 references, the dual '
          'op-amp U201 / U301 being two units each), 119 in all where the walk by filename stopped at 73',
          sheets[1:] == [('/ampli_ht_vertical/', 'ampli_ht.kicad_sch'), ('/ampli_ht_horizontal/', 'ampli_ht.kicad_sch')] and len(paths) == 2
          and len(child) == 92 and len({s['ref'] for s in child}) == 90
          and sorted(s['unit'] for s in child if s['ref'] == 'U201') == [1, 2] and len(r['SchematicSymbol']) == r['Schematic'][0]['symbols'] == 119
          and all(len(p.split('/')) == 3 for p in paths), (sheets, len(child), paths))
    cov = {(c['file'], c['element']): c for c in r['KiCadCoverage']}
    from pcb.custom import sexpr as S
    every = {(f, str(el[0])) for f in ('complex_hierarchy.kicad_sch', 'ampli_ht.kicad_sch', 'complex_hierarchy.kicad_pcb')
             for el in S.parse(files[f])[1:] if isinstance(el, list) and el}
    check('KXC-1 COVERAGE: every top-level element kind of every schematic and board file has a KiCadCoverage row with its count and handling '
          '(typed / summarised / counted / preserved); symbols are typed as SchematicSymbol, wires as SchematicNet (kxc-2), footprints with every pad '
          '(kxc-4) - nothing unaccounted',
          set(cov) == every and cov[('ampli_ht.kicad_sch', 'symbol')]['polari_class'] == 'SchematicSymbol'
          and cov[('ampli_ht.kicad_sch', 'wire')]['handling'] == 'typed' and cov[('ampli_ht.kicad_sch', 'wire')]['polari_class'] == 'SchematicNet'
          and cov[('complex_hierarchy.kicad_pcb', 'footprint')]['handling'] == 'typed'
          and all(c['count'] > 0 and c['handling'] in ('typed', 'summarised', 'counted', 'preserved') for c in cov.values()), sorted(every ^ set(cov))[:5])
    check('KXC-1 VOLTS UNKNOWN: ingested BoardNet rows say -1 (unknown) and why - a KiCad net carries no voltage, so 0.0 (a real 0 V rail) '
          'is never invented', r['BoardNet'] and all(n['volts'] == K.UNKNOWN_VOLTS == -1.0 and 'volts unknown' in n['notes'] for n in r['BoardNet']))

    files, r = _read('simulation/rectifier', 'rectifier')
    v1 = next(s for s in r['SchematicSymbol'] if s['ref'] == 'V1')
    arts = {a['path']: a for a in r['KiCadArtifact']}
    check('KXC-1 SIMULATION FIELDS + MODEL FILE: V1\'s Sim.* fields survive split out (Sim.Device SPICE, Sim.Params type="V" model="SINE(0 1.5 1k ...)"), '
          'every other property is kept in properties_json, and diode.mod (the SPICE model library) is a kept spice-model artifact, not dropped',
          v1['sim_device'] == 'SPICE' and 'SINE(0 1.5 1k' in v1['sim_params'] and 'Fieldname' in json.loads(v1['properties_json'])
          and not any(k.startswith('Sim.') for k in json.loads(v1['properties_json']))
          and arts['diode.mod']['kind'] == 'spice-model' and arts['diode.mod']['handling'] == 'kept' and arts['diode.mod']['content'] == files['diode.mod'],
          (v1['sim_device'], v1['sim_params'], sorted(arts)))

    tmp = tempfile.mkdtemp(prefix='kxc1-')
    try:
        proj = os.path.join(tmp, 'p')
        shutil.copytree(os.path.join(DEMOS, 'simulation', 'rectifier'), proj)
        open(os.path.join(proj, 'rectifier.wbk'), 'w').write('{"version": 1, "tabs": []}\n')
        open(os.path.join(proj, 'model.step'), 'wb').write(b'\x00\x9f\x92\x96 binary')
        os.makedirs(os.path.join(proj, 'rectifier-backups'))
        open(os.path.join(proj, 'rectifier-backups', 'old.zip'), 'wb').write(b'PK\x03\x04')
        files = K.read_dir(proj)
        rr = K.read_project(files, 'rectifier', binaries=K.binaries_in(proj))
        arts = {a['path']: a for a in rr['KiCadArtifact']}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    check('KXC-1 EVERY FILE, BOUNDED: a simulator workbook (.wbk) is kept as sim-workbook, a binary file is listed by sha + size (never read as text, '
          'never dropped), KiCad\'s own backups directory is skipped',
          arts['rectifier.wbk']['kind'] == 'sim-workbook' and arts['rectifier.wbk']['handling'] == 'kept' and arts['model.step']['handling'] == 'listed'
          and arts['model.step']['kind'] == '3d-model' and arts['model.step']['size_bytes'] == 11 and not any('backups' in p for p in arts), sorted(arts))

    files, r = _read('ecc83', 'ecc83-pp')
    check('KXC-1 THE pcb-0 BOARD UNCHANGED: ecc83-pp still reads with no problems, 11 Part / 15 Placement / 13 BoardNet rows, and now 26 SchematicSymbol rows '
          '(every placed symbol incl. power symbols) + one artifact per file',
          r['problems'] == [] and len(r['Part']) == 11 and len(r['Placement']) == 15 and len(r['BoardNet']) == 13 and len(r['SchematicSymbol']) == 26
          and len(r['KiCadArtifact']) == len(files), (len(r['Part']), len(r['SchematicSymbol'])))
