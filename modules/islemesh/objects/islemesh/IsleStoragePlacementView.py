"""
@module islemesh.objects.islemesh.IsleStoragePlacementView

Row class IsleStoragePlacementView of the islemesh module — one class per file (design §7).
Added by stm-2b (docs/STORAGE-MIGRATION-CONTRACT.md).
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IsleStoragePlacementView(treeObject):
    """The core's READ-ONLY hint of the storage placement record, one row per dataset
    (POST /api/islemesh/storage/placement replaces the whole set). A hint only: the authority stays the
    placement file on the core. It carries no decision."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: the dataset.
        name: str = '',
        dataset: str = '',
        domain: str = '',
        # The device the entry places the dataset on.
        device: str = '',
        # authorized | migrated | cutover | hosting | recovery-needed
        state: str = '',
        # Integer ownership epoch of the entry.
        generation: int = 0,
        planId: str = '',
        planRevision: int = 0,
        planDigest: str = '',
        # The entry pending intent as JSON (null when none).
        pending_json: str = 'null',
        source_device: str = '',
        # When the view was accepted (ISO).
        updated_at: str = '',
        # core device name : bearer fingerprint prefix (never the token).
        posted_by: str = '',

        manager=None,
    ):
        self.name = name
        self.dataset = dataset
        self.domain = domain
        self.device = device
        self.state = state
        self.generation = generation
        self.planId = planId
        self.planRevision = planRevision
        self.planDigest = planDigest
        self.pending_json = pending_json
        self.source_device = source_device
        self.updated_at = updated_at
        self.posted_by = posted_by
