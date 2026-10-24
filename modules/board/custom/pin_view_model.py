"""
@module board.custom.pin_view_model

pv-0 (PIN_VIEW_PLAN.md 2.5 / 2.6 / 2.9): THE STRUCTURE of the pin view — surfaces, the pins at every level and the pin-to-pin connections between them — DERIVED on every read from the rows
the earlier arcs built (never retyped): SocPin / PackageContact / ConnectorPin / EnclosureContact (hsp-0), BoardPinNet + the circuit rows (ucd-0c), PinFunction / PeripheralSignal (the
signals), ElectricalCharacteristic (the pad class NAME only) and the shape rows (board.custom.pv_shapes).

LEVELS (his sketch, concentric: die inside package inside board)   die · package · board · part · bench
SURFACES                                                             board · enclosure (a package) · soc (a die) · board-part · bench-part
CONNECTIONS are PIN TO PIN ONLY: both ends are pin ids. Kinds:
  pad-to-leg   die pad <-> package leg                   to-header    leg <-> a header pin (or the ICSP1 header's pin)
  on-board     two legs on one rail                      to-board-part  leg <-> a pin of a part on the board
  chip-to-chip leg of one chip <-> leg of the other      to-bench     a header pin <-> a bench part's pin, or <-> another header pin by a bench wire
A crossing that ends nowhere a pin exists (an unused leg, a not-bonded pad, a line the rows only name by what consumes it) is NOT a connection: it is listed in `unresolved` with the reason.
A via is a WORD only (series resistor, buffer, capacitor ...) plus the part's name; no value is carried here — the numbers belong to the electrical view.
"""
import json

from board.custom import exposure_view as V
from board.custom import pv_families as F
from board.custom import pv_shapes as S
from board.custom import soc_functions as SF

LEVELS = ('die', 'package', 'board', 'part', 'bench')
VIA_WORD = {'direct': 'direct', 'series-resistor': 'series resistor', 'buffer': 'buffer', 'capacitor': 'capacitor', 'jumper': 'jumper', 'series-inductor': 'series inductor',
            'series-fuse': 'series fuse', 'not-bonded': 'not bonded', 'internal-only': ''}
POWER_KINDS = ('power', 'analog-supply', 'usb-supply')
GROUND_KINDS = ('ground', 'usb-ground', 'thermal-pad')


def _short(ref):
    return ref.partition(':')[2] if ':' in ref else ref


#: pv-6: the layout the bench parts are drawn on when the view has no binding — the SAME default the Layout page opens with (board.layout_page.DEFAULT_CONFIG; the selftest keeps them equal)
BENCH_LAYOUT_DEFAULT = {'arduino-uno-r3': 'uno-light'}


class Model:
    def __init__(self, tables, board, bench_layout=None):
        self.t, self.board = tables, board
        self.bench_layout = bench_layout   # pv-6: the public layout payload (electrodevice.custom.layout_core.layout_place) the bench parts sit on, or None (then they pack into the bench column)
        self.bench = {'config': (bench_layout or {}).get('config', ''), 'board': None, 'placed': [], 'unplaced': [], 'why': ''}
        self.surfaces, self.pins, self.connections, self.unresolved = [], {}, [], []
        self.shapes = {r['name']: r for r in S.shape_rows(tables, board)}
        self.pos = {}   # surface id -> {'x','y','rot','parent'}
        self._fn_rows = {}
        for f in SF.pin_functions(tables):   # c3-derive: stored + derived rows
            self._fn_rows.setdefault(f['soc_pin'], {})[f['function']] = f
        self._sig = {s['name']: s for s in tables.get('PeripheralSignal', [])}
        self._soc = {s['name']: s for s in tables.get('SocPin', [])}
        self._cls = {c['name']: c for c in tables.get('ConnectorPin', [])}
        self._bp = {b['canonical']: b for b in tables.get('BoardPin', []) if b['board'] == board}
        self._contacts = V.board_rows(tables, board)
        self.comps = [c for c in tables.get('BoardComponent', []) if c['board'] == board and c.get('package')]
        self._conn_seen, self._ids = set(), set()
        self.rail_of = {}   # leg / pad pin id -> the BoardNet name it ties to (the rail), from the E2 crossings
        self.labels = S.leg_labels(tables)

    # ------------------------------------------------------------ pins
    def signals_of(self, soc_pin_name, functions):
        out = []
        for fn in functions:
            fr = self._fn_rows.get(soc_pin_name, {}).get(fn)
            srows = [self._sig[fr['signal']]] if fr and fr.get('signal') in self._sig else []
            for fam in (F.families_of_function(fn) or ['']):
                if fam:
                    out.append({'function': fn, 'family': fam, 'signal': srows[0]['name'] if srows else '', 'direction': F.direction_of(fn, srows)})
        return out

    def add_pin(self, **kw):
        sig = kw.pop('signals', [])
        fams = []
        for s in sig:
            if s['family'] not in fams:
                fams.append(s['family'])
        for extra in kw.pop('extra_families', []):
            if extra and extra not in fams:
                fams.append(extra)
        pin = dict({'id': '', 'level': '', 'surface': '', 'label': '', 'number': None, 'x': 0.0, 'y': 0.0, 'side': '', 'kind': '', 'bonded': True, 'soc': '', 'soc_pin': '', 'canonical': '',
                    'functions': [], 'default_function': '', 'drive_class': '', 'drive_role': 'undetermined', 'ref': '', 'notes': '', 'stage': 'unassigned', 'stage_why': '', 'consumers': [],
                    'lit': None, 'dim': False, 'short_label': ''}, **kw)
        pin['signals'], pin['families'] = sig, fams
        self.pins[pin['id']] = pin
        return pin

    def add_surface(self, **kw):
        s = dict({'id': '', 'kind': '', 'level': '', 'title': '', 'parent': '', 'shape': '', 'x': 0.0, 'y': 0.0, 'rot': 0, 'w': 0.0, 'h': 0.0, 'ref': '', 'component': '', 'soc': '', 'package': '',
                  'pin_ids': [], 'notes': '', 'links': {}, 'short_title': '', 'title_pos': None, 'extent': None}, **kw)
        self.surfaces.append(s)
        return s

    def connect(self, kind, a, b, via='direct', via_part='', source='', enclosure='', verification='', note=''):
        if a not in self.pins or b not in self.pins or a == b:
            self.unresolved.append({'source': source, 'reason': 'an end is not a pin (%s / %s)' % (a if a not in self.pins else 'ok', b if b not in self.pins else 'ok'), 'a': a, 'b': b})
            return None
        key = (kind, tuple(sorted((a, b))), via_part, source)
        if key in self._conn_seen:
            return None
        self._conn_seen.add(key)
        source = 'rail' if source.startswith('rail:') else source.split('=')[0]   # the row name without its outer end (a net name like +5V is not carried in a connection)
        cid, n = '%s--%s' % (a, b), 1
        while cid in self._ids:
            n += 1
            cid = '%s--%s#%d' % (a, b, n)
        self._ids.add(cid)
        c = {'id': cid, 'a': a, 'b': b, 'kind': kind, 'via': VIA_WORD.get(via, via), 'via_part': via_part, 'enclosure': enclosure, 'source': source, 'verification': verification, 'note': note}
        self.connections.append(c)
        return c

    # ------------------------------------------------------------ build
    def build(self):
        self._board_surface()
        for comp in self.comps:
            self._chip(comp)
        self._parts()
        self._headers()
        self._crossings()
        self._bench()
        self._canonicals()
        self._finish_surfaces()
        return self

    def _board_surface(self):
        shp = self.shapes[S.shape_name('board', self.board)]
        p = S.params(shp)
        self.board_p = p
        self.add_surface(id='board:%s' % self.board, kind='board', level='board', title='%s board' % self.board, shape=shp['name'], w=p['bbox'][0], h=p['bbox'][1], ref='HardwareEnclosure:%s:board' % self.board)
        self.board_id = 'board:%s' % self.board
        self.place = {pl['ref']: pl for pl in p['placements']}

    def _chip(self, comp):
        pkg = next(p for p in self.t['PackageDefinition'] if p['name'] == comp['package'])
        pkg_shape = self.shapes[S.shape_name('pkg', pkg['name'])]
        lay = S.layout(pkg_shape)
        pl = self.place.get(comp['ref'], {'x': 0.0, 'y': 0.0, 'rot': 0})
        pid = 'package:%s:%s' % (self.board, comp['ref'])
        did = 'die:%s:%s' % (self.board, comp['ref'])
        body = S.params(pkg_shape)['body']
        self.add_surface(id=pid, kind='enclosure', level='package', title='%s %s package (%s)' % (comp['ref'], comp['soc'], pkg['package_type']), parent=self.board_id, shape=pkg_shape['name'],
                         x=pl['x'], y=pl['y'], rot=pl['rot'], w=body[0], h=body[1], ref='HardwareEnclosure:%s:%s:package' % (self.board, comp['ref']), component=comp['ref'], soc=comp['soc'], package=pkg['name'],
                         short_title=S.package_short_title(comp['ref'], pkg['package_type']))
        legs = {}
        pcs = [c for c in self.t['PackageContact'] if c['package'] == pkg['name']]
        by_num = {p['number']: p for p in lay['pins']}
        for c in pcs:
            pos = by_num.get(c['number']) or (lay['pad'] and {'x': lay['pad']['x'], 'y': lay['pad']['y'], 'side': 'center'}) or {'x': 0.0, 'y': 0.0, 'side': ''}
            sp = self._soc.get(c.get('soc_pin') or '')
            fns = (['GPIO'] + json.loads(sp['functions_json'] or '[]')) if sp else json.loads(c.get('functions_json') or '[]')
            fam_kind = F.family_of_kind(c['kind'])
            legs[c['number']] = self.add_pin(
                id='PackageContact:%s' % c['name'], level='package', surface=pid, label=c['label'], number=c['number'], x=round(pos['x'], 4), y=round(pos['y'], 4), side=pos.get('side', ''), kind=c['kind'],
                soc=comp['soc'], soc_pin=c.get('soc_pin', ''), functions=fns, default_function=(sp or {}).get('default_function', ''), drive_class=c.get('electrical_class', ''), ref='PackageContact:%s' % c['name'],
                drive_role=self.drive_role(c['kind']), signals=self.signals_of(c.get('soc_pin', ''), fns) if sp else self._named(fns), extra_families=[fam_kind], notes=c.get('undetermined', ''))
        # the die: one pad per SocPin of this chip + one per supply / signal pad the package's crossings name
        e1 = [x for x in V.contacts(self.t) if x['enclosure'] == '%s:%s:package' % (self.board, comp['ref'])]
        groups, order = {}, []
        for x in e1:
            if not x['inner_ref']:   # the exposed pad: the package has it, the rows name no die pad behind it
                self.unresolved.append({'source': 'EnclosureContact:%s' % x['name'], 'reason': 'no die pad is named behind %s (%s)' % (x['label'], x['undetermined'] or 'die pads undetermined'), 'a': '', 'b': x['outer_ref']})
                continue
            if x['inner_ref'] not in groups:
                order.append(x['inner_ref'])
            groups.setdefault(x['inner_ref'], []).append(x)
        for sp in self.t['SocPin']:
            if sp['soc'] == comp['soc'] and 'SocPin:%s' % sp['name'] not in groups:
                order.append('SocPin:%s' % sp['name'])
                groups['SocPin:%s' % sp['name']] = []

        def first_leg(ref):
            nums = [int(x['outer_ref'].rpartition(':')[2]) for x in groups[ref] if x['outer_ref']]
            return min(nums) if nums else 10 ** 6
        order.sort(key=lambda r: (first_leg(r), r))
        die_shape = self.shapes[S.shape_name('die', comp['soc'])]
        dl = S.die(S.params(die_shape), len(order))
        self.add_surface(id=did, kind='soc', level='die', title='%s die (%s)' % (comp['ref'], comp['soc']), parent=pid, shape=die_shape['name'], w=dl['ring']['w'], h=dl['ring']['h'],
                         ref='SocDefinition:%s' % comp['soc'], component=comp['ref'], soc=comp['soc'], links={'register_profile': '/api/board/socs/%s/register-profile' % comp['soc']})
        for ref, pos in zip(order, dl['pins']):
            xs = groups[ref]
            cls, _, rest = ref.partition(':')
            sp = self._soc.get(rest) if cls == 'SocPin' else None
            label = sp['pin'] if sp else rest.rpartition(':')[2]
            leg = next((legs.get(int(x['outer_ref'].rpartition(':')[2])) for x in xs if x['outer_ref']), None)
            if sp:
                fns = ['GPIO'] + json.loads(sp['functions_json'] or '[]')
                sig = self.signals_of(sp['name'], fns)
            elif cls == 'SocSignal':
                fns = [label]
                sig = self._named(fns)
            else:
                fns, sig = [], []
            bonded = any(x['outer_ref'] for x in xs) if xs else bool(sp and sp['package_contacts_refs_json'] != '[]')
            kind = (leg or {}).get('kind') or ('io' if sp else 'signal')
            self.add_pin(id=ref, level='die', surface=did, label=label, x=round(pos['x'], 4), y=round(pos['y'], 4), side=pos['side'], kind=kind, bonded=bonded, soc=comp['soc'],
                         soc_pin=sp['name'] if sp else '', functions=fns, default_function=(sp or {}).get('default_function', ''), drive_class=(sp or {}).get('electrical_class', '') or (leg or {}).get('drive_class', ''),
                         drive_role=self.drive_role(kind), ref=ref, signals=sig, extra_families=[F.family_of_kind(kind)],
                         notes='' if bonded else (xs[0]['notes'] if xs else 'no package crossing names this pad'))
            for x in xs:
                lg = legs.get(int(x['outer_ref'].rpartition(':')[2])) if x['outer_ref'] else None
                if lg:
                    self.connect('pad-to-leg', ref, lg['id'], x['via'], x['via_part'], source='EnclosureContact:%s' % x['name'], enclosure=x['enclosure'], verification=x['verification'])
                else:
                    self.unresolved.append({'source': 'EnclosureContact:%s' % x['name'], 'reason': '%s: %s' % (x['via'], x['notes'] or x['label']), 'a': ref, 'b': ''})

    def _named(self, fns):
        return [{'function': f, 'family': fam, 'signal': '', 'direction': F.direction_of(f, [])} for f in fns for fam in (F.families_of_function(f) or [])]

    @staticmethod
    def drive_role(kind):
        """The ELECTRICAL role of a pad / leg kind (drive side, never the signal direction): sources-and-sinks | supplied | returns | sources | draws-leakage-only | differential-pair | undetermined."""
        if kind == 'io':
            return 'sources-and-sinks'
        if kind in POWER_KINDS:
            return 'supplied'
        if kind in GROUND_KINDS:
            return 'returns'
        if kind == 'regulator-output':
            return 'sources'
        if kind in ('analog-input', 'clock-input', 'analog-reference'):
            return 'draws-leakage-only'
        if kind == 'usb-data':
            return 'differential-pair'
        return 'undetermined'

    # ------------------------------------------------------------ board parts, headers
    def _parts(self):
        for ref, names in S.part_names(self.t, self.board).items():
            shp = self.shapes[S.shape_name('part', ref.replace(' ', '_'))]
            lay = S.layout(shp)
            pl = self.place.get(ref, {'x': 0.0, 'y': 0.0, 'rot': 0})
            sid = 'part:%s:%s' % (self.board, ref)
            geo = S.part_geometry(S.params(shp))
            bx = S.params(shp)['box']
            self.add_surface(id=sid, kind='board-part', level='part', title=ref, parent=self.board_id, shape=shp['name'], x=pl['x'], y=pl['y'], rot=pl['rot'], w=bx[0], h=bx[1], ref='SchematicPart:%s' % ref,
                             short_title=geo['short_title'], title_pos=geo['title'], extent=geo['extent'])
            by = {p['name']: p for p in lay['pins']}
            for n in names:
                p = by[n]
                self.add_pin(id=self.part_pin_id(ref, n), level='part', surface=sid, label=n, short_label=geo['pins'][n], x=round(p['x'], 4), y=round(p['y'], 4), side=p['side'], kind='part', drive_role='undetermined', ref='SchematicPart:%s' % ref,
                             notes='the schematic pin number of this part is `undetermined` in the rows (the line is named by what it carries)' if ':' not in n and not n.isdigit() and ref.startswith(('C', 'RN', 'Y', 'CST')) else '')

    @staticmethod
    def part_pin_id(ref, name):
        return 'SchematicPart:%s:%s' % (ref, name)

    def _headers(self):
        sid = self.board_id
        for h in self.board_p['headers']:
            pos = {p['number']: p for p in S.header(h)}
            for cp in [c for c in self.t['ConnectorPin'] if c['name'].startswith(h['name'] + ':')]:
                p = pos.get(cp['number'], {'x': h['x'], 'y': h['y']})
                self.add_pin(id='ConnectorPin:%s' % cp['name'], level='board', surface=sid, label=cp['label'], number=cp['number'], x=round(p['x'], 4), y=round(p['y'], 4), kind='header:%s' % h['connector'],
                             canonical=cp.get('board_pin', ''), ref='ConnectorPin:%s' % cp['name'], drive_role='undetermined')

    # ------------------------------------------------------------ crossings of the board (E2)
    def _crossings(self):
        rails = {}
        for x in [c for c in self._contacts if c['level'] == 'E2']:
            a = x['inner_ref']
            if a not in self.pins:
                self.unresolved.append({'source': 'EnclosureContact:%s' % x['name'], 'reason': 'inner end %s is not a pin of the modelled packages' % a, 'a': a, 'b': ''})
                continue
            o = x['outer_ref']
            src, enc = 'EnclosureContact:%s' % x['name'], x['enclosure']
            args = dict(via=x['via'], via_part=x['via_part'], source=src, enclosure=enc, verification=x['verification'])
            cls, _, rest = o.partition(':')
            if cls == 'ConnectorPin':
                self.connect('to-header', a, o, **args)
            elif cls == 'BoardNet':
                net = rest.split(':', 1)[1] if ':' in rest else rest
                rails.setdefault(net, []).append((a, x))
                self.rail_of[a] = net
                for hp in V.header_pins(o, self.t):
                    self.connect('to-header', a, 'ConnectorPin:%s' % hp, **args)
            elif cls == 'PackageContact':
                self.connect('chip-to-chip', a, o, **args)
            elif cls == 'SchematicPart':
                ref, _, pin = rest.rpartition(':')
                self.connect('to-header' if ref.startswith('ICSP') else 'to-board-part', a, self.part_pin_id(ref, pin), **args)
            elif x['via'] == 'internal-only' and x['via_part']:
                self.connect('to-board-part', a, self.part_pin_id(x['via_part'], S.part_pin_name(x, self.labels)), **dict(args, via='direct', via_part=''))
            else:
                self.unresolved.append({'source': src, 'reason': '%s: %s' % (x['via'], x['consumed_by'] or x['notes'] or x['label']), 'a': a, 'b': ''})
        for net, ends in sorted(rails.items()):   # two legs on one rail: on-board
            for i, (a, xa) in enumerate(ends):
                for b, xb in ends[i + 1:]:
                    self.connect('on-board', a, b, via='direct', source='rail:%s' % net, enclosure=xa['enclosure'], verification=xa['verification'])

    # ------------------------------------------------------------ the bench (BoardPinNet + the circuit rows)
    def _bench(self):
        nets = [n for n in self.t.get('BoardPinNet', []) if n['board'] == self.board]
        if not nets:
            return
        net_row = {n['name']: n for n in self.t.get('CircuitNetDefinition', [])}
        bp_header = {b['name']: 'ConnectorPin:%s:%s' % (self.board, b['connector_pin']) for b in self.t['BoardPin'] if b['board'] == self.board and b.get('connector_pin')}
        on_board = self._bench_board()   # pv-6: {component row name: its placement on the breadboard} (empty without a layout)
        for circuit, c, label in S.bench_components(self.t, self.board):
            sid = 'bench:%s:%s' % (circuit, c['name'])
            shp = self.shapes[S.shape_name('part', 'bench-%s' % c['name'])]
            geo = S.part_geometry(S.params(shp))
            placed = on_board.get(c['name'])
            if not any(s['id'] == sid for s in self.surfaces):
                bx = S.params(shp)['box']
                if placed:
                    self.add_surface(id=sid, kind='bench-part', level='bench', title='%s (%s on %s) — %s on the breadboard' % (c['name'], c['kind'], circuit, placed['name']), shape=shp['name'],
                                     w=placed['w'], h=placed['h'], ref='CircuitComponentDefinition:%s' % c['name'], x=placed['x'], y=placed['y'], short_title=geo['short_title'], title_pos=placed['title_pos'],
                                     extent=placed['extent'], notes='legs in holes %s' % ', '.join(placed['holes']))
                else:
                    pl = self.place.get('bench-%s' % c['name'], {'x': 0.0, 'y': 0.0})
                    self.add_surface(id=sid, kind='bench-part', level='bench', title='%s (%s on %s)' % (c['name'], c['kind'], circuit), shape=shp['name'], w=bx[0], h=bx[1], ref='CircuitComponentDefinition:%s' % c['name'],
                                     x=pl['x'], y=pl['y'], short_title=geo['short_title'], title_pos=geo['title'], extent=geo['extent'])
            pos = {p['name']: p for p in S.layout(shp)['pins']}[label]
            if placed and label in placed['pins']:   # the pin sits in the hole its leg occupies (the part's frame = the centre of its legs)
                pos = placed['pins'][label]
            self.add_pin(id='CircuitPin:%s:%s:%s' % (circuit, c['name'], label), level='bench', surface=sid, label=label, short_label=geo['pins'][label], x=round(pos['x'], 4), y=round(pos['y'], 4), side=pos['side'], kind=c['kind'],
                         drive_role='undetermined', ref='CircuitComponentDefinition:%s' % c['name'])
        by_net = {}
        for n in nets:
            by_net.setdefault((n['circuit'], n['circuit_net']), []).append(n)
        for (circuit, net_name), rows in sorted(by_net.items()):
            nr = net_row.get(net_name)
            if nr is None:
                self.unresolved.append({'source': 'BoardPinNet:%s' % rows[0]['name'], 'reason': 'no circuit net row %s' % net_name, 'a': '', 'b': ''})
                continue
            label = nr['net']
            heads = []
            for r in rows:
                if r['board_pin']:
                    heads.append((bp_header.get(r['board_pin'], ''), r))
                else:   # a rail (GND): every header pin of that label
                    heads += [('ConnectorPin:%s' % cp['name'], r) for cp in self.t['ConnectorPin'] if cp['board'] == self.board and cp['label'] == label]
            targets = [pid for pid, p in self.pins.items() if p['level'] == 'bench' and p['id'].startswith('CircuitPin:%s:' % circuit) and p['label'] == label]
            for hid, r in heads:
                if hid not in self.pins:
                    self.unresolved.append({'source': 'BoardPinNet:%s' % r['name'], 'reason': 'its header pin is not a pin of this board', 'a': hid, 'b': ''})
                    continue
                for tid in targets:
                    self.connect('to-bench', hid, tid, via='bench wire', source='BoardPinNet:%s' % r['name'])
            hh = [h for h, _ in heads if h and not self.pins[h]['label'] == label]   # a rail's header pins are not jumpered to each other
            for i, a in enumerate(hh):   # two header pins on one bench net: the jumper wire between them
                for b in hh[i + 1:]:
                    self.connect('to-bench', a, b, via='jumper', source='BoardPinNet:%s' % rows[0]['name'])

    def _bench_board(self):
        """pv-6: the breadboard of the bench layout as a surface beside the board (where the packed bench column used to start), and every bench part's place on it: its frame at the centre of
        its legs' holes, its box spanning them, its pins IN those holes (by the leg's net). -> {component row name: {x, y, w, h, pins: {label: {x, y, side}}, title_pos, extent, holes, name}}.
        Nothing here is drawn by hand: the holes come from the layout engine's placements (electrodevice.custom.layout_place), the hole positions from the layout view's own geometry."""
        lay = self.bench_layout
        if not lay or not lay.get('ok') or not lay.get('board'):
            return {}
        b = lay['board']
        pitch = next((float(x.get('pitch_mm') or 2.54) for x in (lay.get('scene') or {}).get('boards', []) if x.get('role') == 'bench'), 2.54)
        geo = S.breadboard_geometry(b['rows'], b['rail_holes'], pitch)
        row = S.bench_board_row(b['model'], b['rows'], b['rail_holes'], pitch)
        self.shapes[row['name']] = row
        x0, y0 = S.BENCH_REGION['x0'], S.BENCH_REGION['y0']
        sid = 'bench-board:%s' % b['name']
        self.add_surface(id=sid, kind='bench-board', level='bench', title='%s (%s, %d strips): the layout of %s' % (b.get('label') or b['model'], b['model'], b['rows'], lay['config']), shape=row['name'],
                         w=geo['w'], h=geo['h'], x=x0 + geo['w'] / 2, y=y0 + geo['h'] / 2, ref='BenchBoard:%s' % b['name'],
                         notes='the breadboard the layout page places this build on; parts sit in the holes the layout gives their legs; wires are the layout page\'s (here a bench wire is drawn pin to pin)')
        self.bench.update({'board': {'name': b['name'], 'model': b['model'], 'rows': b['rows'], 'rail_holes': b['rail_holes'], 'label': b.get('label', ''), 'surface': sid}, 'config': lay['config']})
        f, gap = S.LABEL['font'], S.LABEL['gap']
        out = {}
        for pl in lay.get('placements', []):
            legs = [(leg, S.hole_xy(geo, leg.get('hole', ''))) for leg in pl.get('legs', [])]
            legs = [(leg, xy) for leg, xy in legs if xy]
            if not legs:
                self.bench['unplaced'].append({'part': pl.get('row') or pl.get('name'), 'why': 'no leg of %s names a breadboard hole' % pl.get('name')})
                continue
            xs, ys = [xy[0] for _, xy in legs], [xy[1] for _, xy in legs]
            cx, cy = x0 + (min(xs) + max(xs)) / 2, y0 + (min(ys) + max(ys)) / 2
            w, h = max(xs) - min(xs) + pitch, max(ys) - min(ys) + pitch
            pins = {}
            for leg, (hx, hy) in legs:
                lx, ly = round(x0 + hx - cx, 4), round(y0 + hy - cy, 4)
                side = 'left' if lx < -1e-6 else ('right' if lx > 1e-6 else 'center')
                pins.setdefault(leg.get('net', ''), {'x': lx, 'y': ly, 'side': side})   # two legs on one net (the pushbutton's pairs): the first hole stands for the net
            ext = {'x0': -w / 2, 'y0': -h / 2, 'x1': w / 2, 'y1': h / 2}
            for net, p in pins.items():
                tw = S.text_w(S.short(net, S.LABEL['max_pin']))
                if p['side'] == 'left':
                    ext['x0'] = min(ext['x0'], p['x'] - gap - tw)
                else:
                    ext['x1'] = max(ext['x1'], (p['x'] if p['side'] == 'right' else w / 2) + gap + tw)
                ext['y0'], ext['y1'] = min(ext['y0'], p['y'] - f / 2), max(ext['y1'], p['y'] + f / 2)
            title_y = ext['y1'] + gap
            ext['y1'] = title_y + f
            ext['x0'], ext['x1'] = min(ext['x0'], -S.text_w(pl.get('row', '')) / 2), max(ext['x1'], S.text_w(pl.get('row', '')) / 2)
            out[pl.get('row', '')] = {'name': pl.get('name', ''), 'x': round(cx, 4), 'y': round(cy, 4), 'w': round(w, 4), 'h': round(h, 4), 'pins': pins, 'title_pos': {'x': 0.0, 'y': round(title_y, 4)},
                                      'extent': {k: round(v, 4) for k, v in ext.items()}, 'holes': [leg.get('hole', '') for leg, _ in legs]}
            self.bench['placed'].append({'part': pl.get('row', ''), 'name': pl.get('name', ''), 'holes': [leg.get('hole', '') for leg, _ in legs]})
        return out

    def _canonicals(self):
        """The board's own pin names (D0 .. A5) on the die pad, the leg and the header pins of the line: BoardPin rows name the SoC pin of the board's MCU; headers follow the crossings."""
        mcu = next((c for c in self.comps if c['role'] == 'mcu'), None)
        if mcu is None:
            return
        by_soc = {'%s:%s' % (mcu['soc'], b['soc_pin']): b['canonical'] for b in self._bp.values()}
        for p in self.pins.values():
            if p['level'] in ('die', 'package') and p['soc_pin'] in by_soc and p['soc'] == mcu['soc']:
                p['canonical'] = by_soc[p['soc_pin']]
        for c in self.connections:
            if c['kind'] == 'to-header':
                a, b = self.pins[c['a']], self.pins[c['b']]
                if a['canonical'] and not b['canonical'] and b['level'] == 'board':
                    b['canonical'] = a['canonical']

    def _finish_surfaces(self):
        by = {}
        for p in self.pins.values():
            by.setdefault(p['surface'], []).append(p['id'])
        for s in self.surfaces:
            s['pin_ids'] = by.get(s['id'], [])
        # bench parts sit outside the board: their placement is the board row's (S.part_placements packs them into the bench column, pv-2)
        # a part on the board without a placement keeps (0,0) only if the board row has none: the board row always places every part
        for s in self.surfaces:
            if s['level'] == 'part' and s['ref'].partition(':')[2] in self.place:
                pl = self.place[s['ref'].partition(':')[2]]
                s['x'], s['y'], s['rot'] = pl['x'], pl['y'], pl['rot']


def build(tables, board='arduino-uno-r3', bench_layout=None):
    return Model(tables, board, bench_layout).build()
