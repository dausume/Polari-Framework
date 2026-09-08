"""
@module islemesh.objects.islemesh.IsleAppService

Row class IsleAppService of the islemesh module — one class per file (design §7), split
from islemesh_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IsleAppService(treeObject):
    """One service row of one isle app (registry services[]): the
    containers behind the app's subdomains."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<app>/<service>' ('myapp/api').
        name: str = '',
        app_name: str = '',
        # The device whose registry declared this service — makes
        # the per-device replace semantics reach services too.
        device_name: str = '',
        service: str = '',
        subdomain: str = '',
        container: str = '',
        port: int = 0,
        protocol: str = 'http',
        is_mock: bool = False,
        manager=None,
    ):
        self.name = name
        self.app_name = app_name
        self.device_name = device_name
        self.service = service
        self.subdomain = subdomain
        self.container = container
        self.port = port
        self.protocol = protocol
        self.is_mock = is_mock
