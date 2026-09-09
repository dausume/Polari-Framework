"""
@module printcam.objects.printcam.TimelapseRecord

TimelapseRecord — one timelapse the camera produced for one print job.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TimelapseRecord(treeObject):
    """What it is: one rendered timelapse (Moonraker's timelapse component)
    tied to a `PrintJob`: where the file is, frames, duration, and a
    checksum — a `PrintOutcome`'s evidence.
    Related concepts: `CameraDefinition`, `PrintJob`, `PrintOutcome`.
    How it is measured: reported by Moonraker after the print; sha256 over
    the file when cached.
    """

    @treeObjectInit
    def __init__(self, name: str = '', camera: str = '', print_job: str = '', store_key: str = '', sha256: str = '',
                 frames: int = 0, duration_s: float = 0.0, created_at: str = '', notes: str = ''):
        self.name = name
        self.camera = camera
        self.print_job = print_job
        self.store_key = store_key
        self.sha256 = sha256
        self.frames = frames
        self.duration_s = duration_s
        self.created_at = created_at
        self.notes = notes
