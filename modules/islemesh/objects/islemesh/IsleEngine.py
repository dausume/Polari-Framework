"""
@module islemesh.objects.islemesh.IsleEngine

Row class IsleEngine of the islemesh module — one class per file (design §7), split
from islemesh_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IsleEngine(treeObject):
    """An isle app that DECLARES it provides a polari engine
    (handoff §20.4): `isle app deploy --engine <kind>=<url>` emits
    the declaration, the pusher ingests it, and the binder wires it
    into whatever polari surface consumes that kind (odoo →
    OdooInstanceConfig.base_url; generic → the provider ladder).

    `bound` records whether the polari-side consumer was actually
    wired (the consuming module may be absent — then the engine is
    available-but-unbound, stated honestly, not silently dropped)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<app>@<kind>' ('books@business-ops').
        name: str = '',
        app_name: str = '',
        device_name: str = '',
        # The engine capability provided: 'business-ops' (odoo),
        # 'compute', 'scoring', … — a polari-recognized kind.
        provides: str = '',
        # Where polari reaches the engine (an .isle URL or an
        # in-mesh container:port).
        url: str = '',
        # Which polari surface got wired, '' if none was available.
        bound_to: str = '',
        bound: bool = False,
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.app_name = app_name
        self.device_name = device_name
        self.provides = provides
        self.url = url
        self.bound_to = bound_to
        self.bound = bound
        self.is_mock = is_mock
        self.notes = notes
