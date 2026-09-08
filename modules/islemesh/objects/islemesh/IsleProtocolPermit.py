"""
@module islemesh.objects.islemesh.IsleProtocolPermit

Row class IsleProtocolPermit of the islemesh module — one class per file (design §7), split
from islemesh_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IsleProtocolPermit(treeObject):
    """One permitted protocol path, DERIVED from the agent nginx
    fragments isle controls (handoff §11: the proxies ARE the
    policy — these rows make it visible as the protocol matrix).
    Never hand-written: parse output only."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<device>/<server_name>:<port>'.
        name: str = '',
        # The device whose agent enforces this permit.
        device_name: str = '',
        # The app the fragment belongs to ('' if unattributed).
        app_name: str = '',
        # nginx server_name this vhost answers to.
        server_name: str = '',
        listen_port: int = 0,
        # PERMIT_PROTOCOLS entry (https-mtls = client cert required).
        protocol: str = 'http',
        # Where the proxy sends it ('http://myapp_backend' or an
        # upstream member 'backend:8443'; comma-joined if several).
        upstream: str = '',
        # Source fragment filename ('myapp.conf') — provenance.
        fragment_ref: str = '',
        is_mock: bool = False,
        manager=None,
    ):
        self.name = name
        self.device_name = device_name
        self.app_name = app_name
        self.server_name = server_name
        self.listen_port = listen_port
        self.protocol = protocol
        self.upstream = upstream
        self.fragment_ref = fragment_ref
        self.is_mock = is_mock
