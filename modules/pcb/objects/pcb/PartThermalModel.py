"""
@module pcb.objects.pcb.PartThermalModel

PartThermalModel — one class per file (design §7); bob-3g, the Boards on the Bench plan (AI-Notes/plans/BENCH_BOARDS_PLAN.md bob-3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PartThermalModel(treeObject):
    """What it is: A PART'S OWN THERMAL BEHAVIOUR AS ITS DATASHEET STATES IT - for parts that are black boxes (a regulator, a MOSFET, a tube): the
    transient thermal impedance from the junction to a reference (the board under the part, or a case soldered to it) as FOSTER pairs (R K/W,
    tau s) in `foster_json` [[R, tau], ...] - Zth(t) = sum R_i (1 - exp(-t / tau_i)), the steady junction-to-reference Rth = sum R_i - plus the
    datasheet's maximum junction temperature and its junction-to-ambient Rth (measured on the datasheet's OWN test board, so it is shown beside the
    result for comparison and never added to this board's model). materialsScience.engines.thermal_rc runs it; pcb.custom.thermal_transient adds it on
    top of the board's temperature under the part.
    Binding: the row named '<board>:<ref>' is that placed part; a row with no board applies to every placed part whose symbol value or lib_id equals
    `part_key` (one datasheet, many boards). Provenance as DatasheetFact carries it: document, revision, page_table, url; entered numbers with no
    document say so in `origin`. 0 = not given (tj_max_c, rth_ja_k_w); a stage with R = 0 adds nothing.
    Related concepts: `PartPowerInput`, `DatasheetFact`, `Datasheet`, the Board Details 'Thermal over time' tab.
    """

    plain_words = ('How hot a part gets inside for the power it uses, as its datasheet says - how fast it warms up and how far above the board it '
                   'ends up - plus the hottest it is allowed to get.')

    REFERENCES = ('board', 'case')

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', ref: str = '', part_key: str = '', reference: str = 'board', foster_json: str = '[]',
                 tj_max_c: float = 0.0, rth_ja_k_w: float = 0.0, document: str = '', revision: str = '', page_table: str = '', url: str = '',
                 conditions: str = '', origin: str = 'given on the page', undetermined: str = '', notes: str = '', manager=None):
        self.name = name                # '<board>:<ref>', or '<part_key>' for a model shared by every board
        self.board = board              # '' = applies wherever part_key matches
        self.ref = ref
        self.part_key = part_key        # the symbol value or lib_id it applies to (when board is '')
        self.reference = reference      # board | case - what the Foster network's far end is held at (the board model gives it)
        self.foster_json = foster_json  # [[R K/W, tau s], ...] junction -> reference
        self.tj_max_c = tj_max_c        # the datasheet's maximum junction temperature (0 = not given)
        self.rth_ja_k_w = rth_ja_k_w    # the datasheet's junction-to-ambient Rth on ITS test board (0 = not given) - comparison only
        self.document = document
        self.revision = revision
        self.page_table = page_table
        self.url = url
        self.conditions = conditions    # the datasheet's test conditions (JESD51-7 board, mounting, airflow) in its words
        self.origin = origin            # cited | given on the page | ...
        self.undetermined = undetermined
        self.notes = notes
