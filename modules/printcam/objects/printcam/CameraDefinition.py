"""
@module printcam.objects.printcam.CameraDefinition

CameraDefinition — one USB camera on one printer guest.
"""
from objectTreeDecorators import treeObject, treeObjectInit

STREAMERS = ('ustreamer', 'camera-streamer')


class CameraDefinition(treeObject):
    """What it is: one USB camera watching one printer: the guest it is passed
    into (`hardware_app`, the voron guest), the streamer that serves it
    inside the guest, resolution/fps, the Moonraker webcam name Mainsail
    shows, and whether timelapse is on.
    Related concepts: `HardwareAppDefinition` (the guest it extends),
    `PrinterDefinition` (voron), `HardwarePort` (the camera as the map sees
    it: role `camera`), `TimelapseRecord`.
    How it is realised: `printcam.custom.provision.render_provision` renders
    the in-guest install (ustreamer service on :8080, moonraker webcam +
    timelapse config); the port comes from the hardware map.
    """

    @treeObjectInit
    def __init__(self, name: str = '', hardware_app: str = 'voron-printer', printer: str = 'voron-2.4-350',
                 streamer: str = 'ustreamer', device: str = '/dev/video0', width: int = 1280, height: int = 720, fps: int = 15,
                 stream_port: int = 8080, webcam_name: str = 'printcam', timelapse: bool = True, timelapse_mode: str = 'layermacro',
                 is_prior: bool = True, notes: str = ''):
        self.name = name
        self.hardware_app = hardware_app
        self.printer = printer
        self.streamer = streamer
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.stream_port = stream_port
        self.webcam_name = webcam_name
        self.timelapse = timelapse
        self.timelapse_mode = timelapse_mode
        self.is_prior = is_prior
        self.notes = notes
