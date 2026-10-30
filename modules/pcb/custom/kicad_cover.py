"""
@module pcb.custom.kicad_cover

kxc-1 (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md): INGEST ENCAPSULATES EVERYTHING. His ruling 2026-10-30: Polari is the source of
truth, KiCad an input and an output; nothing KiCad wrote may be dropped silently. Three things here, all pure (no KiCad):

  artifacts(files, binaries, board, typed)  every project file → a KiCadArtifact row (sha256, size, kind, the text ≤ 1 MB kept)
  coverage(files, board)                    every top-level element kind of every .kicad_sch / .kicad_pcb → a KiCadCoverage row:
                                            typed / summarised / counted / preserved, the class holding it, the slice that types it
  sheet_instances(files, top)               the schematic walked by SHEET INSTANCE, not by file: a child sheet used twice is two
                                            instances (KiCad's /<root uuid>/<sheet uuid> paths), an ancestor cycle is refused
  symbol_rows(instances, board)             one SchematicSymbol per placed symbol per instance, every property kept, Sim.* split out
"""
import hashlib
import json
import os

from pcb.custom import sexpr as S

#: text kept in the row up to this size (D-kxc-1, recommended; larger text is listed until the file-store half lands)
KEEP_BYTES = 1 << 20
#: extension → artifact kind
KINDS = {'.kicad_sch': 'schematic', '.kicad_pcb': 'board', '.kicad_pro': 'project', '.kicad_prl': 'project-local',
         '.kicad_sym': 'symbol-library', '.kicad_mod': 'footprint', '.kicad_dru': 'design-rules', '.kicad_wks': 'worksheet',
         '.kicad_jobset': 'jobset', '.lib': 'spice-model', '.mod': 'spice-model', '.sub': 'spice-model', '.cir': 'spice-model',
         '.sp': 'spice-model', '.spice': 'spice-model', '.ibs': 'ibis-model', '.wbk': 'sim-workbook', '.step': '3d-model',
         '.stp': '3d-model', '.wrl': '3d-model', '.json': 'other'}
LIB_TABLES = ('sym-lib-table', 'fp-lib-table')
SIM_FIELDS = ('Sim.Device', 'Sim.Type', 'Sim.Name', 'Sim.Params', 'Sim.Pins', 'Sim.Library')

#: element head → (handling, polari class, next slice, note) per file kind; anything not named is PRESERVED (bytes only)
SCH = {'version': ('typed', 'Schematic', '', ''), 'generator': ('typed', 'Schematic', '', ''), 'generator_version': ('typed', 'Schematic', '', ''),
       'uuid': ('typed', 'Schematic', '', 'the root sheet uuid starts every instance path'), 'paper': ('preserved', '', 'kxc-5', 'page size'),
       'title_block': ('typed', 'Schematic', '', ''), 'lib_symbols': ('typed', 'Symbol', '', 'the embedded library symbols (pins with ERC types)'),
       'symbol': ('typed', 'SchematicSymbol', '', 'one row per placed instance'), 'sheet': ('typed', 'SchematicSheet', '', 'one row per sheet instance'),
       'sheet_instances': ('typed', 'SchematicSheet', '', 'page numbers'), 'symbol_instances': ('typed', 'SchematicSymbol', '', 'KiCad 6 instance table'),
       'wire': ('typed', 'SchematicNet', '', 'joined into nets (kxc-2)'), 'junction': ('typed', 'SchematicNet', '', 'joined into nets (kxc-2)'), 'no_connect': ('typed', 'SchematicNet', '', 'joined into nets (kxc-2)'),
       'label': ('typed', 'SchematicNet', '', 'net names (kxc-2)'), 'global_label': ('typed', 'SchematicNet', '', 'net names (kxc-2)'),
       'hierarchical_label': ('typed', 'SchematicNet', '', 'net names (kxc-2)'), 'bus': ('preserved', '', 'kxc-2', ''), 'bus_entry': ('preserved', '', 'kxc-2', ''),
       'bus_alias': ('preserved', '', 'kxc-2', ''), 'netclass_flag': ('preserved', '', 'kxc-2', 'net class directive'),
       'directive_label': ('preserved', '', 'kxc-2', 'net class directive'), 'text': ('preserved', '', 'kxc-3', 'free text — simulation directives live here'),
       'text_box': ('preserved', '', 'kxc-6', ''), 'polyline': ('preserved', '', 'kxc-6', 'drawing'), 'rectangle': ('preserved', '', 'kxc-6', 'drawing'),
       'circle': ('preserved', '', 'kxc-6', 'drawing'), 'arc': ('preserved', '', 'kxc-6', 'drawing'), 'image': ('preserved', '', 'kxc-6', 'drawing'),
       'table': ('preserved', '', 'kxc-6', ''), 'embedded_fonts': ('preserved', '', '', 'font embedding flag')}
PCB = {'version': ('typed', 'PcbBoard', '', ''), 'generator': ('typed', 'PcbBoard', '', ''), 'generator_version': ('typed', 'PcbBoard', '', ''),
       'general': ('typed', 'PcbBoard', '', 'thickness'), 'layers': ('typed', 'PcbBoard', '', 'layers_json'), 'setup': ('summarised', 'PcbBoard', 'kxc-5', 'stackup + plot settings; the stackup is typed'),
       'net': ('typed', 'BoardNet', '', ''), 'footprint': ('typed', 'Placement', '', 'placement + every pad (PcbPad) + its drawings (PcbLayerGraphics)'),
       'segment': ('typed', 'NetGeometry', '', 'every segment, per net'), 'arc': ('typed', 'NetGeometry', '', 'every arc, per net'),
       'via': ('typed', 'NetGeometry', '', 'every via, per net'), 'zone': ('typed', 'PcbZone', '', 'pours, keep-outs, teardrops'),
       'gr_line': ('typed', 'PcbLayerGraphics', '', 'per layer: count + bounding box'),
       'gr_arc': ('typed', 'PcbLayerGraphics', '', 'per layer: count + bounding box'), 'gr_rect': ('typed', 'PcbLayerGraphics', '', 'per layer: count + bounding box'),
       'gr_circle': ('typed', 'PcbLayerGraphics', '', 'per layer: count + bounding box'), 'gr_poly': ('typed', 'PcbLayerGraphics', '', 'per layer: count + bounding box'),
       'paper': ('preserved', '', 'kxc-5', ''), 'title_block': ('typed', 'PcbBoard', '', ''), 'property': ('preserved', '', 'kxc-4', 'board text variables'),
       'gr_text': ('typed', 'PcbLayerGraphics', '', 'per layer: count + bounding box (the strings stay in the file)'), 'gr_text_box': ('preserved', '', 'kxc-4', ''), 'dimension': ('preserved', '', 'kxc-4', ''),
       'group': ('preserved', '', 'kxc-4', ''), 'generated': ('preserved', '', 'kxc-4', 'tuning patterns'), 'target': ('preserved', '', 'kxc-4', ''),
       'image': ('preserved', '', 'kxc-4', ''), 'table': ('preserved', '', 'kxc-4', ''), 'embedded_fonts': ('preserved', '', '', '')}


def sha(data):
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def kind_of(path):
    base = os.path.basename(path)
    if base in LIB_TABLES:
        return 'lib-table'
    return KINDS.get(os.path.splitext(base)[1].lower(), 'other')


def artifacts(files, binaries, board, typed):
    """files {path: text}, binaries [{path, sha256, bytes}], typed {paths rows were read from} → KiCadArtifact rows."""
    rows = []
    for path, text in sorted(files.items()):
        raw = text.encode()
        keep = len(raw) <= KEEP_BYTES
        rows.append({'name': '%s:%s' % (board, path), 'board': board, 'path': path, 'kind': kind_of(path), 'sha256': sha(raw), 'size_bytes': len(raw),
                     'handling': 'typed' if path in typed else ('kept' if keep else 'listed'), 'content': text if keep else '',
                     'notes': '' if keep else 'over 1 MB: listed by sha; the bytes go to the file store once D-kxc-1 is decided'})
    for b in sorted(binaries, key=lambda b: b['path']):
        rows.append({'name': '%s:%s' % (board, b['path']), 'board': board, 'path': b['path'], 'kind': kind_of(b['path']), 'sha256': b['sha256'],
                     'size_bytes': b['bytes'], 'handling': 'listed', 'content': '', 'notes': 'binary (or not UTF-8): listed by sha and size'})
    return rows


def coverage(files, board):
    """→ KiCadCoverage rows: every top-level element kind of every .kicad_sch / .kicad_pcb."""
    rows = []
    for path, text in sorted(files.items()):
        table = SCH if path.endswith('.kicad_sch') else PCB if path.endswith('.kicad_pcb') else None
        if table is None:
            continue
        counts = {}
        for el in S.parse(text)[1:]:
            if isinstance(el, list) and el:
                counts[str(el[0])] = counts.get(str(el[0]), 0) + 1
        for head, n in sorted(counts.items()):
            handling, cls, nxt, note = table.get(head, ('preserved', '', 'kxc-6', 'not yet named by the ingest'))
            rows.append({'name': '%s:%s:%s' % (board, path, head), 'board': board, 'file': path, 'element': head, 'count': n,
                         'handling': handling, 'polari_class': cls, 'next_slice': nxt, 'notes': note})
    return rows


def sheet_instances(files, top):
    """→ ([{file, tree, path, uuids, page}], problems). The walk is by INSTANCE: each (sheet …) element of a sheet instance opens a
    child instance, even when the same file was opened before; a file that is its own ancestor is refused (a cycle)."""
    root = S.parse(files[top])
    root_uuid = S.value(root, 'uuid')
    pages = {}
    for si in S.find(root, 'sheet_instances'):
        for p in S.find(si, 'path'):
            pages[str(p[1])] = S.value(p, 'page')
    out, problems = [], []
    stack = [(top, root, '/', [root_uuid] if root_uuid else [], (top,))]
    while stack:
        fname, tree, path, uuids, ancestors = stack.pop(0)
        out.append({'file': fname, 'tree': tree, 'path': path, 'uuids': uuids, 'page': pages.get('/' + '/'.join(uuids[1:]), '') if uuids else ''})
        for sh in S.find(tree, 'sheet'):
            sub = S.prop(sh, 'Sheetfile') or S.prop(sh, 'Sheet file')
            name = S.prop(sh, 'Sheetname') or S.prop(sh, 'Sheet name') or sub
            if sub not in files:
                problems.append('sheet %s names %s, which is not among the files' % (name, sub))
            elif sub in ancestors:
                problems.append('sheet %s: %s is its own ancestor (%s) — a cycle, not walked' % (name, sub, ' → '.join(ancestors)))
            else:
                stack.append((sub, S.parse(files[sub]), path + name + '/', uuids + [S.value(sh, 'uuid')], ancestors + (sub,)))
    for i, inst in enumerate(out, 1):
        inst['page'] = inst['page'] or str(i)
    return out, problems


def _instance_ref(sym, uuids):
    """(reference, unit) of this symbol IN this sheet instance: KiCad 7+ keeps (instances (project … (path "/<root>/<sheet>…"
    (reference R) (unit N)))) on the symbol; the instance whose path is ours wins, else the symbol's own Reference property."""
    want = '/' + '/'.join(uuids)
    for inst in S.find(sym, 'instances'):
        for proj in S.find(inst, 'project'):
            for p in S.find(proj, 'path'):
                if str(p[1]).rstrip('/') == want:
                    return S.value(p, 'reference'), S.value(p, 'unit')
    return S.prop(sym, 'Reference'), S.value(sym, 'unit', '1')


def _props(sym):
    return {str(p[1]): str(p[2]) for p in S.find(sym, 'property') if len(p) > 2}


def symbol_rows(instances, board):
    """→ (SchematicSymbol rows, problems) — one per placed symbol per sheet instance."""
    rows, problems, names = [], [], set()
    for inst in instances:
        for s in S.find(inst['tree'], 'symbol'):
            ref, unit = _instance_ref(s, inst['uuids'])
            props = _props(s)
            x, y, rot = S.xy(s)
            mirror = S.value(s, 'mirror')
            name = '%s:%s:%s' % (board, ref, unit)
            if name in names:
                problems.append('%s placed twice (%s) — a duplicate reference; named by uuid' % (ref, inst['path']))
                name = '%s:%s' % (name, S.value(s, 'uuid'))
            names.add(name)
            rows.append({'name': name, 'board': board, 'ref': ref, 'unit': int(S.num(unit, 1)), 'lib_id': S.value(s, 'lib_id'),
                         'value': props.get('Value', ''), 'footprint': props.get('Footprint', ''), 'uuid': S.value(s, 'uuid'),
                         'instance_path': '/' + '/'.join(inst['uuids']), 'sheet': inst['path'], 'file': inst['file'],
                         'x_mm': x, 'y_mm': y, 'rotation': rot, 'mirror': mirror, 'in_bom': S.value(s, 'in_bom', 'yes'),
                         'on_board': S.value(s, 'on_board', 'yes'), 'dnp': S.value(s, 'dnp', 'no'),
                         'exclude_from_sim': S.value(s, 'exclude_from_sim', 'no'), 'power': 'yes' if ref.startswith('#') else 'no',
                         'properties_json': json.dumps({k: v for k, v in props.items() if k not in SIM_FIELDS}, sort_keys=True),
                         'sim_device': props.get('Sim.Device', ''), 'sim_type': props.get('Sim.Type', ''), 'sim_name': props.get('Sim.Name', ''),
                         'sim_params': props.get('Sim.Params', ''), 'sim_pins': props.get('Sim.Pins', ''), 'sim_library': props.get('Sim.Library', ''),
                         'notes': ''})
    return rows, problems
