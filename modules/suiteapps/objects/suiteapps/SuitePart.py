"""
@module suiteapps.objects.suiteapps.SuitePart

SuitePart — one member app of a suite, with where it must run.
"""
from objectTreeDecorators import treeObject, treeObjectInit

PART_KINDS = ('polari-app', 'isle-app', 'hardware-app', 'hardware-extension-app', 'library')
PLACEMENTS = ('any', 'core', 'hardware', 'node', 'same-as')
ROLES = ('design', 'material', 'mold', 'slice', 'control', 'measure', 'map', 'network', 'support')


class SuitePart(treeObject):
    """What it is: one app inside a suite: which app (`app` = a module id or a
    catalog entry name), its kind, the ROLE it plays in the purpose (design,
    material, mold, slice, control, measure, map, network, support), where
    it must run (`placement`: any device, the core, a hardware-tier device,
    a named node, or the same device as another part — `same_as`), whether
    the suite works without it (`required`), and the order it comes up in.
    Related concepts: `SuiteAppDefinition`, `SuitePlacement`,
    `HardwareAppDefinition` (hardware parts), `IsleCatalogEntry` (container
    parts), the module manifests (polari-app parts).
    How it is derived: hand-declared; the placement plan resolves it.
    """

    @treeObjectInit
    def __init__(self, name: str = '', suite: str = '', app: str = '', kind: str = 'polari-app', role: str = 'support',
                 placement: str = 'any', same_as: str = '', node: str = '', required: bool = True, order: int = 0,
                 notes: str = ''):
        self.name = name
        self.suite = suite
        self.app = app
        self.kind = kind
        self.role = role
        self.placement = placement
        self.same_as = same_as
        self.node = node
        self.required = required
        self.order = order
        self.notes = notes
