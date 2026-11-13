"""
@module islemesh.objects.islemesh.IsleStorageWitness

Row class IsleStorageWitness of the islemesh module — one class per file (design §7).
Added by stm-2b (docs/STORAGE-MIGRATION-CONTRACT.md).
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IsleStorageWitness(treeObject):
    """One stored witness (contract 6): a third device saw the domain resolve to the target.
    Evidence of a moment, so a different witness for the same (dataset, generation, device) is refused."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: <dataset>/<generation>/<device>.
        name: str = '',
        dataset: str = '',
        device: str = '',
        # Ownership epoch the witness binds.
        generation: int = 0,
        content_sha: str = '',
        action_id: str = '',
        resolved_address: str = '',
        route_json: str = 'null',
        at: str = '',
        # Canonical JSON of the witness exactly as posted.
        witness_json: str = '{}',
        poster_fingerprint: str = '',
        poster_subject: str = '',
        verified: bool = False,
        seen: int = 1,
        received_at: str = '',

        manager=None,
    ):
        self.name = name
        self.dataset = dataset
        self.device = device
        self.generation = generation
        self.content_sha = content_sha
        self.action_id = action_id
        self.resolved_address = resolved_address
        self.route_json = route_json
        self.at = at
        self.witness_json = witness_json
        self.poster_fingerprint = poster_fingerprint
        self.poster_subject = poster_subject
        self.verified = verified
        self.seen = seen
        self.received_at = received_at
