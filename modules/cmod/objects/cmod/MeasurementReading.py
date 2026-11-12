"""
@module cmod.objects.cmod.MeasurementReading

MeasurementReading - one class per file (design section 7); msv-0 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MeasurementReading(treeObject):
    """What it is: ONE REAL VALUE read off a real instrument on a BuiltUnit for one MeasurementPoint - by hand (via manual: typed off the screen) or
    from a device (usb-scpi / usb-serial / lan-scpi, msv-3). Never edited: a later reading of the same point supersedes it. Its judgement against the
    prediction and the bands is DERIVED on read (cmod.custom.measure_readings), never stored.
    Related concepts: `BuiltUnit`, `MeasurementPoint`, instruments `Instrument` / `InstrumentAccuracy` (the band), `WaveformCapture` (a scope reading).
    """

    plain_words = ('One number someone read off a meter on a real device, which meter it was and how it got into Polari; whether it matches the simulation is worked out when you look.')

    @treeObjectInit
    def __init__(self, name: str = '', unit: str = '', point: str = '', value: float = 0.0, entered: str = '', via: str = 'manual', instrument: str = '', range_max: float = -1.0, who: str = '', at: str = '', hex_sha256: str = '', evidence_sha256: str = '', evidence_path: str = '', session: str = '', step: str = '', note: str = '', manager=None):
        self.name = name    # '<unit>:<point>#r<n>'
        self.unit = unit    # a BuiltUnit name
        self.point = point    # a MeasurementPoint name
        self.value = value    # the value in SI units (V / A)
        self.entered = entered    # what was typed or sent, verbatim ('14.2 mA')
        self.via = via    # manual | usb-scpi | usb-serial | lan-scpi
        self.instrument = instrument    # an Instrument name (its InstrumentAccuracy rows give the band); '' = not said
        self.range_max = range_max    # the range used in SI units; -1 = the smallest range that holds the value
        self.who = who
        self.at = at
        self.hex_sha256 = hex_sha256    # the unit's build at the time
        self.evidence_sha256 = evidence_sha256    # a photo / file of the display or the instrument's reply
        self.evidence_path = evidence_path    # its file-store path
        self.session = session    # a TestSession (msv-0b)
        self.step = step
        self.note = note
