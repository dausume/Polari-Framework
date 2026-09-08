"""
@module appstore.objects.appstore.AppEdgeBehavior

Row class AppEdgeBehavior of the appstore module — one class per file (design §7), split
from appstore_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AppEdgeBehavior(treeObject):
    """sep-5 (decision 8): one EDGE BEHAVIOR as reusable data — what
    a shell may do beyond wrapping the webapp (attach a device, join
    a network, run a no-code graph edge-side) and with what
    configuration. Written once, referenced by ANY app whose
    AppShellDefinition.capabilities_json names it — the registration
    carries REFERENCES, never these definitions. The native half
    (Gradle capability modules, ServiceLoader) stays rare and gated
    on the declaration; `requires_native` names it so the gate can
    refuse honestly when the module is absent (§5l precedent: the
    helper holds the privilege, never the shell)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique reference key ('lora-radio-attach').
        name: str = '',
        title: str = '',
        description: str = '',
        # BEHAVIOR_KINDS entry.
        kind: str = 'device',
        # The reusable configuration (JSON object): which devices
        # (DeviceLink correspondence), which networks (ssid...),
        # which no-code graph runs edge-side.
        config_json: str = '{}',
        # Gradle capability module the shell needs ('' = pure
        # config, no native code).
        requires_native: str = '',
        published: bool = True,
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.kind = kind
        self.config_json = config_json
        self.requires_native = requires_native
        self.published = published
        self.is_prior = is_prior
        self.notes = notes
