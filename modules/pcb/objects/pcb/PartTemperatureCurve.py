"""
@module pcb.objects.pcb.PartTemperatureCurve

PartTemperatureCurve — one class per file (design §7); tmp-5, the temperature plan (AI-Notes/plans/TEMPERATURE_PLAN.md).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PartTemperatureCurve(treeObject):
    """What it is: ONE QUANTITY OF A PART AGAINST TEMPERATURE, AS ITS DATASHEET GIVES IT IN NUMBERS - for the parts and quantities no SPICE model
    carries (a MOSFET's on-resistance, an LED's forward voltage, a capacitor dielectric's drift). Three shapes, each only what the document states:
      points   [[T C, value], ...] read straight from a table; between two points a straight line, outside them REFUSED (never extrapolated)
      linear   value(T) = value at t_ref_c + slope_per_k x (T - t_ref_c), from a stated value and a stated coefficient, over t_min_c .. t_max_c
      band     a bound, not a curve: the value lies within +- band_pct % (or +- band_ppm_k ppm/K x |T - t_ref_c|) of its nominal over t_min_c ..
               t_max_c - a class definition such as X7R; read as a low and a high corner
    Binding: '<board>:<ref>' is that placed part (`from_curve` names the catalogue row it was taken from); a row with no board is a catalogue
    curve, applying to every part whose symbol value or lib_id equals `part_key`. The catalogue rows are code-owned and cited
    (pcb.custom.temperature_curves.CITED). Provenance as DatasheetFact carries it.
    Related concepts: `PartTemperatureBehaviour` (rated range + R / C / L coefficients in the deck), `PartThermalModel`, the Board Details
    'Temperature curves' tab.
    """

    plain_words = 'How one number of a part - its resistance, its voltage, its capacitance - changes with temperature, as its datasheet lists it.'

    KINDS = ('points', 'linear', 'band')

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', ref: str = '', part_key: str = '', from_curve: str = '', quantity: str = '', unit: str = '',
                 kind: str = 'points', points_json: str = '[]', t_ref_c: float = 25.0, value_ref: float = 0.0, slope_per_k: float = 0.0,
                 band_pct: float = 0.0, band_ppm_k: float = 0.0, t_min_c: float = 0.0, t_max_c: float = 0.0, conditions: str = '',
                 document: str = '', revision: str = '', page_table: str = '', url: str = '', origin: str = 'given on the page', notes: str = '',
                 manager=None):
        self.name = name                # catalogue name, or '<board>:<ref>:<quantity>' for a placed part's own
        self.board = board              # '' = a catalogue curve
        self.ref = ref
        self.part_key = part_key        # the symbol value or lib_id a catalogue curve applies to
        self.from_curve = from_curve    # a placed part's curve: the catalogue row it was taken from
        self.quantity = quantity        # rds_on_max | vf_typ | capacitance | ...
        self.unit = unit                # ohm | V | F | ratio ...
        self.kind = kind                # points | linear | band
        self.points_json = points_json  # points: [[T C, value], ...] ascending T
        self.t_ref_c = t_ref_c          # linear / band: the temperature the stated value or the ppm/K is about
        self.value_ref = value_ref      # linear: the stated value at t_ref_c
        self.slope_per_k = slope_per_k  # linear: the stated coefficient, unit per K
        self.band_pct = band_pct        # band: +- this % of nominal over the range
        self.band_ppm_k = band_ppm_k    # band: +- this ppm/K x |T - t_ref_c|
        self.t_min_c = t_min_c          # linear / band: the range the document states it over (points: their own span)
        self.t_max_c = t_max_c
        self.conditions = conditions    # the document's test conditions in its words
        self.document = document
        self.revision = revision
        self.page_table = page_table
        self.url = url
        self.origin = origin            # cited | given on the page | ...
        self.notes = notes
