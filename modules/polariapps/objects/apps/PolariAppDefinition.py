"""
@module polariapps.objects.apps.PolariAppDefinition

Row class PolariAppDefinition of the polariapps module — one class per file (design §7), split
from apps_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PolariAppDefinition(treeObject):
    """One app = a named module configuration for a use-case."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        title: str = '',
        # WHO this configuration serves and what they do with it.
        use_case: str = '',
        description: str = '',
        # JSON list of module ids the app needs
        # (['waxprint', 'materialsScience', ...]).
        modules_json: str = '[]',
        # JSON list of frontend routes the app centers on
        # (['/wax-print-sim', ...]) — the app's front doors.
        pages_json: str = '[]',
        # nav-1: the app's OWN navigation menu as data —
        # [{group, items: [{label, route?, kind:
        #   page|simspace|view|tech-node, requires_module?, ref?}]}]
        # Item availability is DERIVED live; absent modules render
        # as bring-online affordances, never hidden.
        nav_json: str = '[]',
        # nav-1: who enters here (['electrical-engineer', ...]).
        personas_json: str = '[]',
        # nav-1: discipline tag ('' for use-case apps).
        discipline: str = '',
        # sep-4 (decision 9): the engine DATA PAGE this app carries
        # ('/engines/<kind>'; '' = not an engine). Dual-natured apps
        # (odoo-likes) keep their OWN UI as the tile's front and this
        # page as the secondary view — one tile, two natures.
        engine_page: str = '',
        # nav-1: seeds are priors, people's edits are not — flip to
        # False on a customized row and the upsert seed pass will
        # never touch it again (moduleService.seed_upsert contract).
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.use_case = use_case
        self.description = description
        self.modules_json = modules_json
        self.pages_json = pages_json
        self.nav_json = nav_json
        self.personas_json = personas_json
        self.discipline = discipline
        self.engine_page = engine_page
        self.is_prior = is_prior
        self.notes = notes
