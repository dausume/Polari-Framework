"""
@module electrodevice.custom.layout_core

lay-1: THE LAYOUT of a built config on a board — one call, `layout_place(config, board_instance)`, that runs the whole chain and returns one answer:

  design (layout_sources: the config's parts + pin assignment + circuit nets)
    -> derived placements and wires (layout_place: deterministic)
    -> a person's edits applied on top, kept beside the derived values (layout_edits)
    -> wire colours from the scheme, the per-wire override beside the derived colour (layout_colors)
    -> THE NETLIST GATE + the electrical rules (layout_gate): the layout's compiled nets must equal the design's
    -> the build steps (layout_steps), derived and never typed.

Nothing is stored except the person's edits (LayoutEdit rows) and their colour schemes; the layout is recomputed from the rows every time, so the same inputs give the same answer (the `sha`).
`manager` is the live server's manager, or None offline (seeds only; writes are refused in words).
"""
import hashlib
import json

from electrodevice.custom import board_family as BF
from electrodevice.custom import layout_colors as LCOL
from electrodevice.custom import layout_edits as LE
from electrodevice.custom import layout_gate as LG
from electrodevice.custom import layout_place as LP
from electrodevice.custom import layout_scene as LSC
from electrodevice.custom import layout_sources as S
from electrodevice.custom import layout_steps as LS
from electrodevice.custom.layout_words import LayoutRefused
from electrodevice.objects.layout._shared import BENCH_DEFAULT

HEADER_DEFAULT = 'bench-uno-1'


def _sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def boards_listing(manager=None):
    """The board family as plain rows: {'models': [...], 'boards': [...]}. A model row carries its DERIVED tie count and whether it equals the sold count."""
    models = []
    for name, m in sorted(BF.models(manager).items()):
        laid = m.kind == 'breadboard' and int(m.rows) > 0 and int(m.rail_holes) >= 0   # an unverified layout (-1) has no derived count
        derived = BF.derived_ties(m) if laid else 0
        models.append({'name': name, 'kind': m.kind, 'size': m.size, 'status': getattr(m, 'status', 'built'), 'rows': m.rows, 'rail_holes': m.rail_holes, 'pitch_mm': m.pitch_mm,
                       'nominal_ties': m.tie_points, 'derived_ties': derived, 'ties_agree': (derived == m.tie_points) if laid else None,
                       'board_definition': m.board_definition, 'source': m.layout_basis or m.notes, 'description': m.description,
                       'note': {'reserved': 'RESERVED: no geometry yet'}.get(getattr(m, 'status', 'built'), '')})
    boards = []
    for name, b in sorted(BF.bench_boards(manager).items()):
        m = BF.models(manager).get(b.model_name)
        boards.append({'name': name, 'model': b.model_name, 'kind': m.kind if m else '', 'label': b.label, 'owner': b.owner, 'notes': b.notes, 'migrated_from': b.migrated_from,
                       'default': name == BENCH_DEFAULT, 'ties': BF.derived_ties(m) if m and m.kind == 'breadboard' else 0})
    return {'models': models, 'boards': boards, 'default_board': BENCH_DEFAULT, 'default_header_board': HEADER_DEFAULT}


def _board_summary(geo, label):
    return {'name': geo.name, 'model': geo.model, 'kind': geo.kind, 'size': geo.size, 'rows': geo.rows, 'rail_holes': geo.rail_holes, 'label': label,
            'ties': BF.derived_ties(type('M', (), {'rows': geo.rows, 'holes_per_side': geo.holes_per_side, 'rail_holes': geo.rail_holes})) if geo.kind == 'breadboard' else 0}


def layout_place(config, board_instance=None, manager=None, scheme=None, header_board=None, with_edits=True, extra_edits=None):
    """The whole layout of `config` on the BenchBoard `board_instance` (default: the half breadboard). -> a dict (see the module words); a LayoutRefused names why it cannot be built."""
    board = board_instance or BENCH_DEFAULT
    header_board = header_board or HEADER_DEFAULT
    geo = BF.resolve(manager, board)
    if geo is None:
        raise LayoutRefused("no board %r on the bench (boards: %s)" % (board, ', '.join(BF.known_boards(manager))), status=404)
    if geo.reserved or geo.kind != 'breadboard':
        raise LayoutRefused("board %s is a %s%s: layouts are placed on breadboards so far" % (board, geo.kind, ' (reserved: no geometry built yet)' if geo.reserved else ''))
    hgeo = BF.resolve(manager, header_board)
    if hgeo is None or hgeo.kind != 'devboard':
        raise LayoutRefused("%r is not a development board on the bench (the board the wires start from; default %s)" % (header_board, HEADER_DEFAULT), status=404)
    design = S.design_of(manager, config)
    derived = LP.place(design, geo, header_board)
    edits = (LE.load(manager, config, board) if with_edits else []) + list(extra_edits or [])
    laid, overrides, applied, problems = LE.apply(derived, edits)
    sch = scheme if isinstance(scheme, dict) else LCOL.get_scheme(manager, scheme)
    LCOL.colour_wires(laid['wires'], sch, overrides, manager)
    try:
        verdict = LG.gate(manager, design, laid, board, header_board)
    except LayoutRefused as exc:
        verdict = {'ok': False, 'equal': False, 'words': 'REFUSED: %s' % exc, 'mismatches': [], 'findings': [], 'design_nets': design['nets'], 'layout_groups': [], 'nets_compared': len(design['nets']),
                   'suggestions': []}
    occ = LE.occupancy(laid)
    if occ:
        verdict['findings'] = occ + verdict['findings']
        verdict['ok'] = False
        verdict['words'] = 'REFUSED: ' + ' | '.join(f['words'] for f in occ) + ('' if verdict['ok'] or not verdict['words'].startswith('REFUSED: ') else ' | ' + verdict['words'][len('REFUSED: '):])
    pin_where = lambda label: S.pin_where(manager, label)   # noqa: E731
    steps = LS.build_steps(design, laid, board, pin_where, header_board)
    scene = LSC.scene(geo, hgeo, design, laid['placements'], getattr(geo.instance, 'label', ''), getattr(hgeo.instance, 'label', ''))   # lay-2: what the renderer draws
    core = {'placements': laid['placements'], 'wires': laid['wires']}
    return {'ok': True, 'config': config, 'board': _board_summary(geo, getattr(geo.instance, 'label', '')), 'header_board': header_board, 'scheme': sch['name'],
            'placements': laid['placements'], 'wires': laid['wires'], 'strips': laid['strips'], 'rows_used': laid['rows_used'], 'nets': design['nets'], 'assignment': design['assignment'],
            'notes': design['notes'] + design['drift'], 'edits': {'applied': [e['name'] for e in applied], 'problems': problems, 'count': len(edits)}, 'verdict': verdict,
            'scene': scene, 'sha': _sha(core), 'steps_sha': LS.steps_sha(steps), 'steps_count': len(steps), 'circuit': design['circuit'], '_steps': steps, '_design': design, '_derived': derived}


def public(result):
    """The layout without the internals the doors do not send."""
    return {k: v for k, v in result.items() if not k.startswith('_')}


def verdict_rows(result):
    """The gate's verdict as ROWS for a configured table: the whole verdict first, then one row per design net (equal or wrong, in words) and one per electrical rule."""
    v = result['verdict']
    bad = {m['net']: m['words'] for m in v.get('mismatches', [])}
    rows = [{'check': 'The netlist gate', 'subject': result['config'], 'status': 'ok' if v['ok'] else 'refused', 'words': v['words']}]
    for net, terms in sorted(v.get('design_nets', {}).items()):
        rows.append({'check': 'Net %s' % net, 'subject': net, 'status': 'wrong' if net in bad else 'equal',
                     'words': bad.get(net) or 'the layout joins exactly %s' % ', '.join(terms)})
    for f in v.get('findings', []):
        rows.append({'check': 'Rule %s' % f.get('rule', ''), 'subject': f.get('subject', ''), 'status': f.get('status', ''), 'words': f.get('words', '')})
    return rows


def steps_of(config, board_instance=None, manager=None, scheme=None):
    """The build steps of a layout: {'config','board','verdict','steps','sha','walkthrough'}."""
    r = layout_place(config, board_instance, manager, scheme)
    return {'ok': True, 'config': config, 'board': r['board']['name'], 'verdict': {'ok': r['verdict']['ok'], 'words': r['verdict']['words']}, 'steps': r['_steps'], 'sha': r['steps_sha'],
            'walkthrough': LS.walkthrough_lines(r['_steps']),
            'rows': [{'step': st['index'] + 1, 'kind': st['kind'], 'title': st['title'], 'text': st['text']} for st in r['_steps']]}   # lay-2: the same steps as table rows
