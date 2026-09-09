"""
@module printing_suite.objects.printing.GcodeArtifact

GcodeArtifact — the sliced file, as a checksummed row.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class GcodeArtifact(treeObject):
    """What it is: one gcode file the slicer produced for a `SliceJob`:
    where it is (an object-store key or a Moonraker path on the printer
    guest), its sha256, size, the slicer + version, and the slicer's own
    estimates (time, filament). Parts pass THIS row, never a path.
    Related concepts: `SliceJob` (source), `PrintJob` (consumer), the
    pol-file-store / MinIO buckets (where the bytes live).
    How it is measured: sha256 + size on write; estimates are the slicer's
    claim (labelled `estimated_*`), replaced by the `PrintOutcome`.
    """

    @treeObjectInit
    def __init__(self, name: str = '', slice_job: str = '', store_key: str = '', sha256: str = '', bytes: int = 0,
                 slicer: str = '', slicer_version: str = '', estimated_seconds: int = 0, estimated_filament_mm: float = 0.0,
                 layers: int = 0, created_at: str = '', notes: str = ''):
        self.name = name
        self.slice_job = slice_job
        self.store_key = store_key
        self.sha256 = sha256
        self.bytes = bytes
        self.slicer = slicer
        self.slicer_version = slicer_version
        self.estimated_seconds = estimated_seconds
        self.estimated_filament_mm = estimated_filament_mm
        self.layers = layers
        self.created_at = created_at
        self.notes = notes
