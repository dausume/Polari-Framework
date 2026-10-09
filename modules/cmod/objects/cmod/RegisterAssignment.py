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
    Related concepts: `FirmwareSolution`, `TargetDefinition` (the graph-level derivation this row re-homes per solution),
    board's `BoardPin`, `CGraphNode`/`CPort`, cmod's `PinClaim` (the row this config feeds).
    """

    plain_words = 'A register assignment says whether one task\'s target is tied to a real pin on THIS solution\'s board, or still unbound — and flags it when two tasks claim the same pin.'

    @treeObjectInit
    def __init__(self, name: str = '', solution: str = '', task: str = '', port: str = '', target_kind: str = 'dynamic',
                 controls: str = '', lives_on: str = 'unbound', status: str = 'unbound', provenance: str = 'derived',
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
        self.config_json = config_json  # '{}' or '{"mode": "in", "pull": "up", "edge": "any", "initial": "low"}' (canvas)
        self.notes = notes
