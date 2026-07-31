"""
@cross-cutting
@module polariapps.apps_basis
@tags @xc:bindings

Polari-Apps (tt-12, Dustin 2026-07-18): an APP is a CONFIGURATION
OF MODULES for a particular capability or use-case — a local wax
3D-printing company trying wax simulations and auger-shape variants,
a lean judicial app, a DMV policy-analysis build. Apps ride the
existing module + topology machinery: deploying an app is PLANNED
first (never on-the-spot), the plan is EXPORTABLE as a
credential-free JSON package the pol CLI can point at
(`pol apps deploy <file.json>`), and applying only ever writes
ModuleAssignment rows — the actual container deploy stays the
human's pol command (knobs-and-suggestions).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - polariapps.apps_analysis / polariapps.apps_api
  - polari-cli scripts/apps.sh · polari-platform-angular /apps page
"""

from objectTreeDecorators import treeObject, treeObjectInit

PLAN_STATUSES = ('draft', 'exported', 'applied')


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
        # nav-1: seeds are priors, people's edits are not — flip to
        # False on a customized row and the upsert seed pass will
        # never touch it again (composition.seed_upsert contract).
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
        self.is_prior = is_prior
        self.notes = notes


class AppDeploymentPlan(treeObject):
    """A PLANNED deployment of one app onto one topology — computed,
    exportable, applied later; never executed on the spot."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<app>@<topology>@<created_at>'.
        name: str = '',
        app_name: str = '',
        topology_name: str = '',
        # JSON plan rows ({module, status, instances, suggested...}).
        placements_json: str = '[]',
        # PLAN_STATUSES entry.
        status: str = 'draft',
        created_at: str = '',
        applied_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.app_name = app_name
        self.topology_name = topology_name
        self.placements_json = placements_json
        self.status = status
        self.created_at = created_at
        self.applied_at = applied_at
        self.notes = notes
