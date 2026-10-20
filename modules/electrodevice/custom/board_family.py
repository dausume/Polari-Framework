"""
@module electrodevice.custom.board_family

lay-0: THE BOARD FAMILY — turns a board NAME into its geometry (a `Board` with kind, rows, rail holes, header pins), the TIE-POINT GRAMMAR extended to the hole, and the
tie-point count derived from the geometry.

Tie-point grammar (what `breadboard_netlist_seed` understands):
  r<N><col>                     a hole: strip N, column a-e (left of the trench) or f-j (right). a-e of one strip are ONE net, f-j of it another.
  r<N>L / r<N>R                 the older spelling of the same two strips (still valid; r5L is the net of r5a..r5e)
  rail:<top|bottom>:<+|->:<N>   hole N of a power rail; every hole of one rail is ONE net
  vplus / gnd                   the board's own supply net / SPICE ground (still valid; a wire from a header GND to a '-' rail joins a rail to ground)
  <label>                       a development board's header pin: a BoardPin canonical name (D6, A0) or a power label (GND, 5V, 3V3, VIN, IOREF, AREF, RESET)

Board resolution: a BenchBoard of that name -> its BoardModel's geometry; otherwise the older BreadboardDefinition row (rows from the row, 25 rail holes per rail up
to 30 rows, 50 above: the same common layout). Reserved kinds (protoboard, pcb) resolve to a Board with `reserved=True` and refuse to take a layout.
"""
import re
import types

HOLE_RE = re.compile(r'^r(\d+)([a-j])$')
STRIP_RE = re.compile(r'^r(\d+)([LR])$')
RAIL_RE = re.compile(r'^rail:(top|bottom):([+-]):(\d+)$')
LEFT_COLS, RIGHT_COLS = 'abcde', 'fghij'
RAILS = (('top', '+'), ('top', '-'), ('bottom', '+'), ('bottom', '-'))
#: header power labels as a person may type them -> the label the connectors use
POWER_ALIASES = {'5V': '+5V', '+5V': '+5V', '5v': '+5V', '3V3': '+3V3', '3.3V': '+3V3', '+3V3': '+3V3', 'VCC': '+5V'}
#: the two supply labels a layout needs, canonical
GROUND, FIVE_V = 'GND', '+5V'


def _rows(manager, cls):
    t = ((getattr(manager, 'objectTables', None) or {}).get(cls) or {}) if manager is not None else {}
    return list(t.values()) if isinstance(t, dict) else list(t)


def _as(row):
    return row if not isinstance(row, dict) else types.SimpleNamespace(**row)


def models(manager=None):
    """{name: BoardModel row}: the seeds, with live rows winning."""
    from electrodevice.objects.layout._shared import SEED_BOARD_MODELS
    out = {m['name']: _as(m) for m in SEED_BOARD_MODELS}
    out.update({getattr(r, 'name', ''): r for r in _rows(manager, 'BoardModel')})
    return out


def bench_boards(manager=None):
    """{name: BenchBoard row}: the seeds (the bench's own boards and the converged BreadboardDefinition ones), with live rows winning."""
    from electrodevice.layout_basis import SEED_BENCH_BOARDS_ALL
    out = {b['name']: _as(b) for b in SEED_BENCH_BOARDS_ALL}
    out.update({getattr(r, 'name', ''): r for r in _rows(manager, 'BenchBoard')})
    return out


def derived_ties(model):
    """The tie-point count the geometry gives: strips x holes x 2 sides + 4 rails x rail holes (400 half, 830 full)."""
    return int(model.rows) * int(model.holes_per_side) * 2 + len(RAILS) * int(model.rail_holes)


def devboard_pins(board_definition):
    """The header labels of a development board: its BoardPin canonical names + the connector power labels. () when the board module is not loaded or has no such board."""
    try:
        from board.custom import board_object as bo
        from board.custom import board_uno
        pins = {p['canonical'] for p in bo.rows_for(board_definition)['pins']}
        for _conn, (_ref, _kind, _fp, labels, _order) in board_uno.CONNECTORS.items():
            pins |= {l for l in labels if l != 'NC'}
        return frozenset(pins)
    except Exception:   # noqa: BLE001 - the board module is optional here; the caller says so in words
        return frozenset()


class Board:
    """One resolved board: what the connectivity compiler and the placer read."""

    def __init__(self, name, kind, rows=0, rail_holes=0, holes_per_side=5, model='', size='', reserved=False, board_definition='', status='built', instance=None):
        self.name, self.kind, self.rows, self.rail_holes, self.holes_per_side = name, kind, int(rows), int(rail_holes), int(holes_per_side)
        self.model, self.size, self.reserved, self.board_definition, self.status, self.instance = model, size, reserved, board_definition, status, instance

    @property
    def pins(self):
        return devboard_pins(self.board_definition) if self.kind == 'devboard' else frozenset()


def resolve(manager, name):
    """-> Board | None. A BenchBoard of the name wins; then an older BreadboardDefinition row; then nothing."""
    bench = {getattr(r, 'name', ''): r for r in _rows(manager, 'BenchBoard')}
    legacy = {getattr(r, 'name', ''): r for r in _rows(manager, 'BreadboardDefinition')}
    inst = bench.get(name)
    if inst is None and name not in legacy:
        inst = bench_boards(manager).get(name)    # the seeds (the bench's own boards) when no live row says otherwise
    if inst is not None:
        m = models(manager).get(getattr(inst, 'model_name', ''))
        if m is None:
            return None
        reserved = getattr(m, 'status', 'built') == 'reserved' or m.kind in ('protoboard', 'pcb')
        return Board(name, m.kind, m.rows, m.rail_holes, m.holes_per_side, model=m.name, size=getattr(m, 'size', ''), reserved=reserved,
                     board_definition=getattr(m, 'board_definition', ''), status=getattr(m, 'status', 'built'), instance=inst)
    row = legacy.get(name)
    if row is not None:
        rows = int(getattr(row, 'rows', 30))
        return Board(name, 'breadboard', rows, 25 if rows <= 30 else 50, 5, model='', size='half' if rows <= 30 else 'full')
    return None


def known_boards(manager):
    return sorted(set(bench_boards(manager)) | {getattr(r, 'name', '') for r in _rows(manager, 'BreadboardDefinition')})


def parse_tie(tie):
    """-> ('hole', row, col) | ('strip', row, 'L'|'R') | ('rail', pos, pol, n) | ('power', 'vplus'|'gnd') | None (not breadboard grammar)."""
    if tie in ('vplus', 'gnd'):
        return ('power', tie)
    m = HOLE_RE.match(tie)
    if m:
        return ('hole', int(m.group(1)), m.group(2))
    m = STRIP_RE.match(tie)
    if m:
        return ('strip', int(m.group(1)), m.group(2))
    m = RAIL_RE.match(tie)
    if m:
        return ('rail', m.group(1), m.group(2), int(m.group(3)))
    return None


def side_of(col):
    return 'L' if col in LEFT_COLS else 'R'


def header_label(tie):
    """A person's spelling of a header pin -> the label the connectors use (5V -> +5V); anything else unchanged."""
    return POWER_ALIASES.get(tie, tie)
