"""
@module suiteapps.objects.suiteapps.SuiteAppDefinition

SuiteAppDefinition — one purpose, composed of parts.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SuiteAppDefinition(treeObject):
    """What it is: an overarching, purpose-oriented app: a named composition
    of smaller apps of any kind (polari-app modules, isle-app containers,
    hardware-app KVM guests, hardware-extension-apps) that together do one
    thing — e.g. production 3D printing: CAD shape → material/mold → slice
    → print → measure. Too big for one computer by construction; the
    placement plan spreads it.
    Related concepts: `SuitePart` (the members, with placement needs),
    `SuiteContract` (the object classes parts exchange), `SuitePlacement`
    (the computed plan), `PolariAppDefinition` (a single app = one module
    configuration; a suite composes those), the test-coverage planner
    (same budget + nodes).
    How it is derived: hand-declared by its module's seed; placement is
    computed (`suiteapps.custom.placement`), never typed.
    """

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', purpose: str = '', description: str = '',
                 front_page: str = '', personas_json: str = '[]', is_prior: bool = True, notes: str = ''):
        self.name = name
        self.title = title
        self.purpose = purpose
        self.description = description
        self.front_page = front_page
        self.personas_json = personas_json
        self.is_prior = is_prior
        self.notes = notes
