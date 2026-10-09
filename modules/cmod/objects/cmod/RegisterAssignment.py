"""
@module cmod.objects.cmod.RegisterAssignment

RegisterAssignment — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class RegisterAssignment(treeObject):
    """What it is: ONE REQUIRED TARGET of a `FirmwareSolution`, bound (or not) to a board pin / SoC register (D-fs-2, his
    ruling 2026-10-05: register assignment happens by dragging a task's target onto the PIN MAP; fs-0 builds this row +
    the `assign` door the drag calls, fs-1 builds the drag itself). One row per `TargetDefinition` the solution's graph
    derives (`cmod.custom.targets.derive`) — `task`/`port` name the same node/port a `TargetDefinition` already names;
    `target_kind` and `lives_on` START as that derivation's `kind`/`lives_on` and are RE-CHECKED against the solution's
    OWN resolved board (not just the graph's own `board` field, since `board_variable` can point anywhere at run time).
    `status` is bound (lives_on names a real `BoardPin` of the solution's board), unbound (no pin claimed — a real,
    exposed target, same posture as demo-4: "unbound targets are allowed and visibly marked"), or conflict (two tasks'
    rows both resolve to the same `BoardPin.name` — never silently last-write-wins). `config_json` (ucd-0b) is the
    canvas-authored design choice for this pin (`{mode, pull, edge, initial}`, cmod.custom.claims.pin_claims'
    overrides) — kept HAND-SET across a reseed (same posture as `notes`), so a person's pin-page choice survives;
    the POST .../assign door's `config` body key writes it.

    ucd-0b2a (§5h B2): `peripheral` / `signal` / `bus` are typed resource columns BESIDE `lives_on` (row names of a
    board `Peripheral` / `PeripheralSignal`, or a bus id string) for the NEXT binding mode a pin drag is not — AT
    MOST ONE of `lives_on` (non-'unbound') / `peripheral` / `signal` / `bus` is ever non-empty, checked by name in
    `cmod.custom.firmware.validate()`; every row this slice derives still binds by `lives_on` alone, so the three
    stay '' today. `signal_route` names the `PinFunction` row the bound pin's own alternate function activates
    (derived from the bound pin's `signal`, the same naming the solution's `PinClaim.pin_function` uses) — '' when
    the pin carries no alternate function (plain GPIO) or the row is unbound. `configuration` is the
    `FirmwareSolution` this assignment belongs to — explicit today (= `solution`) so the review's
    HardwareConfiguration split (ucd-0b2's HardwareBinding, NOT this slice) is a rename later, never a migration.
    Related concepts: `FirmwareSolution`, `TargetDefinition` (the graph-level derivation this row re-homes per solution),
    board's `BoardPin` / `Peripheral` / `PeripheralSignal` / `PinFunction`, `CGraphNode`/`CPort`, cmod's `PinClaim`.
    """

    plain_words = 'A register assignment says whether one task\'s target is tied to a real pin on THIS solution\'s board, or still unbound — and flags it when two tasks claim the same pin.'

    @treeObjectInit
    def __init__(self, name: str = '', solution: str = '', task: str = '', port: str = '', target_kind: str = 'dynamic',
                 controls: str = '', lives_on: str = 'unbound', status: str = 'unbound', provenance: str = 'derived',
                 peripheral: str = '', signal: str = '', bus: str = '', signal_route: str = '', configuration: str = '',
                 config_json: str = '{}', notes: str = '', manager=None):
        self.name = name                # '<solution>:<task>.<port>' (or '<solution>:<task>' for a whole-node target)
        self.solution = solution
        self.task = task                # the CGraphNode instance this target is on
        self.port = port                # '' for a whole-node / memory-field target
        self.target_kind = target_kind  # register | pin | peripheral | memory-field | bus | dynamic
        self.controls = controls        # the physical quantity/actuator, in plain words (from TargetDefinition)
        self.lives_on = lives_on        # 'unbound' or a BoardPin row name ('<board>:<canonical>')
        self.status = status            # bound | unbound | conflict
        self.provenance = provenance    # annotation | derived | canvas (mirrors TargetDefinition.provenance)
        self.peripheral = peripheral    # a Peripheral row name — AT MOST ONE of lives_on/peripheral/signal/bus is non-empty
        self.signal = signal            # a PeripheralSignal row name
        self.bus = bus                  # a bus id string (not a row yet)
        self.signal_route = signal_route  # the PinFunction row the bound pin's alternate function activates, '' for plain GPIO/unbound
        self.configuration = configuration  # the FirmwareSolution this assignment belongs to (= solution, explicit)
        self.config_json = config_json  # '{}' or '{"mode": "in", "pull": "up", "edge": "any", "initial": "low"}' (canvas)
        self.notes = notes
