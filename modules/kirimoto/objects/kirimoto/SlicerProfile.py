"""
@module kirimoto.objects.kirimoto.SlicerProfile

SlicerProfile — a Kiri:Moto device/process profile for one printer.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SlicerProfile(treeObject):
    """What it is: the Kiri:Moto device definition for one printer (bed
    size, nozzle, gcode flavour, start/end gcode) plus the process defaults
    — what a `PrintProfile` is translated into when a `SliceJob` is sent.
    Related concepts: `PrinterDefinition` (voron), `PrintProfile`
    (printing_suite), `SliceJob`.
    How it is derived: from the PrinterDefinition's bed and kinematics
    (derived), the flavour is Klipper's; typed only where Kiri:Moto has no
    derivable source.
    """

    @treeObjectInit
    def __init__(self, name: str = '', printer: str = '', bed_x_mm: float = 350.0, bed_y_mm: float = 350.0, bed_z_mm: float = 340.0,
                 nozzle_mm: float = 0.4, gcode_flavor: str = 'klipper', device_json: str = '{}', process_json: str = '{}',
                 is_prior: bool = True, notes: str = ''):
        self.name = name
        self.printer = printer
        self.bed_x_mm = bed_x_mm
        self.bed_y_mm = bed_y_mm
        self.bed_z_mm = bed_z_mm
        self.nozzle_mm = nozzle_mm
        self.gcode_flavor = gcode_flavor
        self.device_json = device_json
        self.process_json = process_json
        self.is_prior = is_prior
        self.notes = notes
