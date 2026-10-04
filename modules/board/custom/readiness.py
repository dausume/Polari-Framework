"""
@module board.custom.readiness

demo1 (his 2026-10-04 ask, mid-slice): "we need a clear separation between boards that have simulations and
no-code, and those that do not and/or have not been used, lumping them all together creates a lot of noise to
figure out where the currently actually usable boards are."

`compute_readiness` DERIVES a board's readiness from rows that already exist — it never reads or writes a
hand-set flag. Three signals, each itself derived:

  has_twin      BoardDefinition.twin is set, OR BoardDefinition.simulated is true (a twin kind picked for it).
  has_template  at least one FirmwareVariant.board_definition names this board (something buildable exists).
  has_run       at least one HardwareSolution.board_definition, OR one Scenario.target_board, names this board
                (a no-code solution or a fault scenario actually RUNS it — the ESP32-C3 has no solution yet but
                has scenarios, so this is true for it too).

  usable   all three signals true.
  partial  one or two of the three true (named in `readiness_why`).
  tracked  none true — a register row and (per plan §8a) a Road, nothing runnable yet.

Flipping a Road step changes nothing here on purpose (D: "a selftest proves ... that flipping a Road step
changes nothing unless the twin/template/solution exist") — the Road is the PLAN, these three are the PROOF.
"""


def compute_readiness(board, variants, solutions, scenarios):
    """board: one BoardDefinition row. variants/solutions/scenarios: the full CRUDE rows of FirmwareVariant,
    HardwareSolution, Scenario (any board — this function does its own filtering by name). Returns
    (readiness, readiness_why)."""
    name = getattr(board, 'name', '')
    has_twin = bool(getattr(board, 'twin', '') or getattr(board, 'simulated', False))
    has_template = any(getattr(v, 'board_definition', '') == name for v in variants)
    has_solution = any(getattr(s, 'board_definition', '') == name for s in solutions)
    has_scenario = any(getattr(sc, 'target_board', '') == name for sc in scenarios)
    has_run = has_solution or has_scenario

    if has_twin and has_template and has_run:
        why = 'usable — has a twin, a firmware template, and something that runs it (a no-code solution or fault scenarios)'
        if not has_solution:
            why = 'usable — has a twin, a firmware template, and fault scenarios run on it; no no-code solution yet'
        return 'usable', why

    signals = {'a twin': has_twin, 'a firmware template': has_template,
               'a no-code solution or scenario that targets it': has_run}
    present = [k for k, v in signals.items() if v]
    missing = [k for k, v in signals.items() if not v]
    if not present:
        return 'tracked', 'register row only — no twin, no firmware template, nothing runs it yet'
    return 'partial', 'has %s; still missing %s' % (', '.join(present), ', '.join(missing))


def readiness_rows(manager):
    """Every BoardDefinition, with readiness/readiness_why computed fresh from the live rows — used by the
    GET /api/board/boards/readiness door and by the selftest. `manager` is the server's object manager
    (`.objectTables`), read generically so this stays usable from board's own code without importing
    hwnocode/firmwarefaults classes."""
    tables = manager.objectTables or {}
    boards = list((tables.get('BoardDefinition') or {}).values())
    variants = list((tables.get('FirmwareVariant') or {}).values())
    solutions = list((tables.get('HardwareSolution') or {}).values())
    scenarios = list((tables.get('Scenario') or {}).values())
    rows = []
    for b in boards:
        readiness, why = compute_readiness(b, variants, solutions, scenarios)
        rows.append({
            'name': b.name, 'title': getattr(b, 'title', ''), 'device_class': getattr(b, 'device_class', ''),
            'register_status': getattr(b, 'register_status', ''), 'soc': getattr(b, 'soc', ''),
            'isa': getattr(b, 'isa', ''), 'usb_route': getattr(b, 'usb_route', ''),
            'programmer': getattr(b, 'programmer', ''), 'adapter_needed': getattr(b, 'adapter_needed', ''),
            'usb_rule': getattr(b, 'usb_rule', ''), 'simulated': getattr(b, 'simulated', False),
            'twin': getattr(b, 'twin', ''), 'road_status': getattr(b, 'road_status', ''),
            'readiness': readiness, 'readiness_why': why,
        })
    return rows
