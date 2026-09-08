"""
@module islemesh.objects.islemesh.IsleCatalogEntry

Row class IsleCatalogEntry of the islemesh module — one class per file (design §7), split
from islemesh_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IsleCatalogEntry(treeObject):
    """One store listing (handoff §20.1/§20.3 — the general isle app
    store, appstore-1 generalized from shells to mesh-apps). An entry
    describes WHAT an app is and HOW it installs; the actual install
    runs on the host (`isle store install`, the mover-on-host
    discipline), never in the backend container.

    kind partitions the two proven variants + modules:
      'mesh-app'      — a compose app deployed to the isle (the
                        `isle app deploy` pipeline; source_ref = a
                        compose file/url or an image name)
      'polari-app'    — a polari or .isle web app installed as a
                        shared-shell launcher .deb (source_ref = the
                        app's .isle URL; the §22 launcher build)
      'polari-module' — a polari module .deb (source_ref = module
                        name; the module_bundle install, mac-8)
    """

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('books', 'polari', 'whoami').
        name: str = '',
        title: str = '',
        description: str = '',
        # IsleCatalogEntry kind (see class doc).
        kind: str = 'mesh-app',
        # What install consumes, per kind: compose ref / image
        # (mesh-app), .isle URL (polari-app), module name (module).
        source_ref: str = '',
        # For mesh-app: the primary service + port (deploy args).
        service: str = '',
        port: int = 0,
        # Desired .isle domain ('' → <name>.isle).
        domain: str = '',
        # Engine capability this app provides once installed
        # ('business-ops' → wires OdooInstanceConfig); '' = none.
        provides_engine: str = '',
        # Presentation.
        icon: str = '',
        category: str = '',
        # Store bookkeeping: published (listed) + who curated it.
        published: bool = True,
        source: str = 'official',
        is_mock: bool = False,
        notes: str = '',
        # hw-app-1: the VM fields a hardware-app / hardware-extension-app entry carries
        # (empty for every other kind). The domain XML + UCI are RENDERED from
        # the hardwareapps module's rows; these point at what to render.
        requires_tier: str = '',
        guest_kind: str = '',
        vm_image_ref: str = '',
        image_sha256_raw: str = '',
        memory_mb: int = 0,
        vcpus: int = 0,
        passthrough_json: str = '[]',
        extends: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.kind = kind
        self.source_ref = source_ref
        self.service = service
        self.port = port
        self.domain = domain
        self.provides_engine = provides_engine
        self.icon = icon
        self.category = category
        self.published = published
        self.source = source
        self.is_mock = is_mock
        self.notes = notes
        self.requires_tier = requires_tier
        self.guest_kind = guest_kind
        self.vm_image_ref = vm_image_ref
        self.image_sha256_raw = image_sha256_raw
        self.memory_mb = memory_mb
        self.vcpus = vcpus
        self.passthrough_json = passthrough_json
        self.extends = extends
