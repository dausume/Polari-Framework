"""
@module islemesh.objects.islemesh.IsleIngestReceipt

Row class IsleIngestReceipt of the islemesh module — one class per file (design §7), split
from islemesh_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IsleIngestReceipt(treeObject):
    """One accepted ingest — the ledger the freshness/mock banner is
    derived from. Receipts are append-only history; the data rows
    they produced are replace-per-device."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<device>/<kind>/<sha256[:12]>'.
        name: str = '',
        device_name: str = '',
        # INGEST_KINDS entry.
        kind: str = 'registry',
        payload_sha256: str = '',
        # {'IsleApp': n, ...} — what this ingest upserted.
        row_counts_json: str = '{}',
        # THE mock flag (Dustin 2026-08-07): true only when the
        # sender declared mock_network — real isle data never does.
        mock_network: bool = False,
        ingested_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device_name = device_name
        self.kind = kind
        self.payload_sha256 = payload_sha256
        self.row_counts_json = row_counts_json
        self.mock_network = mock_network
        self.ingested_at = ingested_at
        self.notes = notes
