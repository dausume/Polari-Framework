"""
@module islemesh.objects.islemesh.IsleStorageReceipt

Row class IsleStorageReceipt of the islemesh module — one class per file (design §7).
Added by stm-2b (docs/STORAGE-MIGRATION-CONTRACT.md).
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IsleStorageReceipt(treeObject):
    """One stored storage-operation receipt (contract 2.6). Evidence only: stored unverified,
    the backend never decides from it; the core CLI verifies the poster before it transitions anything."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: <dataset>/<sha256(actionId)[:16]>/<attempt>.
        name: str = '',
        kind: str = '',
        action_id: str = '',
        attempt: int = 1,
        dataset: str = '',
        device: str = '',
        plan_id: str = '',
        plan_revision: int = 0,
        plan_digest: str = '',
        epoch: int = 0,
        content_sha: str = '',
        manifest_sha: str = '',
        ok: bool = False,
        stage: str = '',
        # Canonical JSON of the receipt exactly as posted.
        receipt_json: str = '{}',
        # sha256 of the presented Bearer (never the token); empty when none.
        poster_fingerprint: str = '',
        poster_subject: str = '',
        # Always False here: the backend calls no verifier.
        verified: bool = False,
        # Times the identical body was posted.
        seen: int = 1,
        received_at: str = '',

        manager=None,
    ):
        self.name = name
        self.kind = kind
        self.action_id = action_id
        self.attempt = attempt
        self.dataset = dataset
        self.device = device
        self.plan_id = plan_id
        self.plan_revision = plan_revision
        self.plan_digest = plan_digest
        self.epoch = epoch
        self.content_sha = content_sha
        self.manifest_sha = manifest_sha
        self.ok = ok
        self.stage = stage
        self.receipt_json = receipt_json
        self.poster_fingerprint = poster_fingerprint
        self.poster_subject = poster_subject
        self.verified = verified
        self.seen = seen
        self.received_at = received_at
