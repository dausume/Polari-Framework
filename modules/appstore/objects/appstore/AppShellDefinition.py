"""
@module appstore.objects.appstore.AppShellDefinition

Row class AppShellDefinition of the appstore module — one class per file (design §7), split
from appstore_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AppShellDefinition(treeObject):
    """One published store entry: a way to install an app (or the
    whole instance) as a native shell."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('polari-instance-shell').
        name: str = '',
        title: str = '',
        description: str = '',
        # SHELL_SCOPES entry.
        scope: str = 'instance',
        # PolariAppDefinition.name when scope == 'app'; '' otherwise.
        app_name: str = '',
        # JSON list of PLATFORM_KEYS entries this shell targets.
        platforms_json: str = '["gradle-project"]',
        # DISTRIBUTIONS entry.
        distribution: str = 'generated-project',
        # {'brandColor': '', 'icon': '<base64 png>'} — shell chrome.
        branding_json: str = '{}',
        # Initial web-UI route; '' = the app's first page (scope=app)
        # or '/' (scope=instance).
        start_route: str = '',
        # sep-2: JSON list of edge-behavior REFERENCES the shell may
        # use (camera, device passthrough...). The definitions live
        # as rows in the app's own module (sep-5); this names them.
        capabilities_json: str = '[]',
        published: bool = True,
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.scope = scope
        self.app_name = app_name
        self.platforms_json = platforms_json
        self.distribution = distribution
        self.branding_json = branding_json
        self.start_route = start_route
        self.capabilities_json = capabilities_json
        self.published = published
        self.is_prior = is_prior
        self.notes = notes
