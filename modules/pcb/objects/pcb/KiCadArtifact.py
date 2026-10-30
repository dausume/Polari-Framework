"""
@module pcb.objects.pcb.KiCadArtifact

KiCadArtifact — one class per file (design §7); kxc-1, the KiCad interchange plan (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md §3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class KiCadArtifact(treeObject):
    """What it is: ONE FILE of an ingested KiCad project, kept as it came (his ruling 2026-10-30: Polari is the source of truth and
    ingest encapsulates everything KiCad has). Every file under the project directory is an artifact — design files, lib tables,
    project libraries, SPICE model files, the simulator workbook, the local settings — with its sha256 and size. Text up to
    1 MB is kept in `content` byte for byte (D-kxc-1, recommended); larger or binary files (3D models) are listed by sha only and
    say so. `handling` says what the ingest made of it: typed (rows were read from it), kept (stored, not yet read into rows),
    listed (sha + size only).
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', path: str = '', kind: str = '', sha256: str = '', size_bytes: int = 0,
                 handling: str = '', content: str = '', notes: str = '', manager=None):
        self.name = name  # board:path
        self.board = board  # the ingested project (the board name the rows share)
        self.path = path  # relative to the project directory
        self.kind = kind  # schematic | board | project | project-local | symbol-library | footprint | lib-table | design-rules | spice-model | sim-workbook | 3d-model | other
        self.sha256 = sha256
        self.size_bytes = size_bytes
        self.handling = handling  # typed | kept | listed
        self.content = content  # the text, byte for byte ('' when listed)
        self.notes = notes
