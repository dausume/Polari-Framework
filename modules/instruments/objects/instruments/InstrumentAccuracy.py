"""
@module instruments.objects.instruments.InstrumentAccuracy

InstrumentAccuracy - one class per file (design section 7); msv-0 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class InstrumentAccuracy(treeObject):
    """What it is: ONE CITED ACCURACY LINE of an instrument model - for one function (V dc, I dc, R) and one range: +/-(pct of reading + counts x
    resolution), from the instrument's datasheet, with the input impedance (V) or burden (I) the meter puts into the circuit. A MeasurementReading's
    instrument band is computed from it; a model with no row gives the band 'unmeasured' and says so (msv D-msv-2: the user's instruments first).
    Related concepts: `Instrument`, cmod `MeasurementReading`.
    """

    plain_words = ("How close one meter's reading is guaranteed to be on one range, copied from its datasheet, so a reading can be judged fairly.")

    @treeObjectInit
    def __init__(self, name: str = '', instrument: str = '', function: str = 'V dc', range_max: float = 0.0, pct_reading: float = -1.0, counts: int = 0, resolution: float = 0.0, input_ohms: float = -1.0, burden_v_per_a: float = -1.0, cite: str = '', notes: str = '', manager=None):
        self.name = name    # '<instrument>-acc-<function>-<range>'
        self.instrument = instrument    # an Instrument name
        self.function = function    # V dc | I dc | R
        self.range_max = range_max    # the range full scale in SI units
        self.pct_reading = pct_reading    # the % of reading term; -1 = unread
        self.counts = counts    # the counts (digits) term
        self.resolution = resolution    # one count in SI units on this range
        self.input_ohms = input_ohms    # V: the input impedance; -1 = unread
        self.burden_v_per_a = burden_v_per_a    # I: the burden (V per A, the shunt); -1 = unread
        self.cite = cite    # the datasheet and its table / page
        self.notes = notes
