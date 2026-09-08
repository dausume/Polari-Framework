"""
@module appstore.objects.appstore_hosting.RemoteHostingOption

Row class RemoteHostingOption of the appstore module — one class per file (design §7), split
from appstore_hosting_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class RemoteHostingOption(treeObject):
    """One rentable hosting offering, with a DATED price."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('digitalocean-basic-8gb').
        name: str = '',
        provider: str = '',
        title: str = '',
        # HOSTING_KINDS_REMOTE entry.
        kind: str = 'cpu-vps',
        # Declared specs; 0 = varies/unknown (fit stays unverified).
        cores: int = 0,
        ram_mb: int = 0,
        disk_mb: int = 0,
        # '' = no GPU; else the model + VRAM ('RTX 4090 24GB').
        gpu_model: str = '',
        # The price, its unit, and — REQUIRED HONESTY — the date it
        # was last checked plus where.
        price_amount: float = 0.0,
        price_unit: str = 'USD/mo',
        price_as_of: str = '',
        price_source: str = '',
        # Billing gotchas ('billed while powered off — destroy to
        # stop') and anything the tile must say.
        price_note: str = '',
        # 'your-cloud' (rented infra you control) | 'intermediary'.
        sovereignty: str = 'your-cloud',
        notes: str = '',
        published: bool = True,
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.provider = provider
        self.title = title
        self.kind = kind
        self.cores = cores
        self.ram_mb = ram_mb
        self.disk_mb = disk_mb
        self.gpu_model = gpu_model
        self.price_amount = price_amount
        self.price_unit = price_unit
        self.price_as_of = price_as_of
        self.price_source = price_source
        self.price_note = price_note
        self.sovereignty = sovereignty
        self.notes = notes
        self.published = published
        self.is_prior = is_prior
