"""
@module cmod.objects.cmod.CapabilityInstance

CapabilityInstance — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CapabilityInstance(treeObject):
    """What it is: ONE USE of a `CapabilityDefinition` (demo-4: dropping "temperature sensor solution" on the canvas twice
    proves "multiple temperature sensors" exist as rows, not just as a template; D-ucd-12: person-facing text calls the
    definition's grouping a Purpose — the class stays CapabilityInstance). `index` is the instance's position
    among the definition's instances (1, 2, …) — the same per-kind indexing brd-wire already uses for board instances, so
    a future bind-to-board-pin step (demo-5/D-demo-5, not built here) has a stable instance to point at. `bindings`
    carries the per-instance target bindings as they stand today (a target's `lives_on`, copied in — 'unbound' until a
    person ties this specific instance to a specific board pin).
    Related concepts: `CapabilityDefinition`, `TargetDefinition`, `CGraph`.
    """

    plain_words = ('A Purpose instance is one use of a Purpose — e.g. the SECOND temperature sensor dropped on a '
                   'drawing — with its own target bindings, separate from every other instance of the same Purpose.')

    @treeObjectInit
    def __init__(self, name: str = '', capability: str = '', graph: str = '', index: int = 1, bindings: str = '',
                 status: str = 'unbound', notes: str = '', manager=None):
        self.name = name              # '<capability>#<index>'
        self.capability = capability
        self.graph = graph
        self.index = index            # 1, 2, … among this capability's instances
        self.bindings = bindings      # csv of 'target_port_ref=lives_on'
        self.status = status          # unbound | bound (bound once every required target has a real lives_on)
        self.notes = notes
