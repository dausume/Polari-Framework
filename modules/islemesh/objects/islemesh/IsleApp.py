"""
@module islemesh.objects.islemesh.IsleApp

Row class IsleApp of the islemesh module — one class per file (design §7), split
from islemesh_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IsleApp(treeObject):
    """One mesh-app as isle knows it (a registry.json entry) plus
    the mac-1 convergence fields (orchestrator, availability triple,
    automation knob). One app — many realizations (see
    MeshAppRealization)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: the isle app name ('myapp').
        name: str = '',
        # Primary domain ('myapp.local' today; '<app>.isle' is the
        # convergence target — both may exist during transition).
        domain: str = '',
        # Device currently hosting the containers ('' = unknown).
        device_name: str = '',
        # JSON list of APP_MODES entries (registry 'modes').
        modes_json: str = '[]',
        # ORCHESTRATORS entry.
        orchestrator: str = 'compose',
        # AVAILABILITY_MODES preset as isle records it today.
        availability_mode: str = 'always-available',
        # The general trigger triple (isle AVAILABILITY-MODES
        # vocabulary; presets above are shorthands for these).
        up_trigger: str = 'boot',
        down_trigger: str = 'never',
        placement: str = 'single-host',
        # The per-app auto/manual knob (handoff §2b.1): what auto
        # may touch. {'triggers_allowed': [...], 'may_relocate':
        # false} — manual-everything by default (knobs rule).
        automation_json: str = '{"triggers_allowed": [], '
                               '"may_relocate": false}',
        # Observed run state as last ingested ('' = unknown;
        # 'up'|'down'|'waking' once the isle side reports it).
        status: str = '',
        # Registry updated_at, as isle recorded it.
        updated_at: str = '',
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.domain = domain
        self.device_name = device_name
        self.modes_json = modes_json
        self.orchestrator = orchestrator
        self.availability_mode = availability_mode
        self.up_trigger = up_trigger
        self.down_trigger = down_trigger
        self.placement = placement
        self.automation_json = automation_json
        self.status = status
        self.updated_at = updated_at
        self.is_mock = is_mock
        self.notes = notes
