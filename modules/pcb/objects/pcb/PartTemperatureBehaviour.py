"""
@module pcb.objects.pcb.PartTemperatureBehaviour

PartTemperatureBehaviour — one class per file (design §7); tmp-1 / tmp-2, the temperature plan (AI-Notes/plans/TEMPERATURE_PLAN.md).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PartTemperatureBehaviour(treeObject):
    """What it is: HOW A PART'S ELECTRICAL BEHAVIOUR DEPENDS ON TEMPERATURE, AS ITS DATASHEET STATES IT, and the temperatures it is rated for:
    the operating range (`t_min_c` .. `t_max_c`, the datasheet's 'operating temperature') and, for a resistor, capacitor or inductor, its
    temperature coefficients - tc1 in ppm/K (a resistor's TCR, a C0G capacitor's ppm/K) and tc2 in ppm/K2 - which the SPICE deck writes as
    ngspice's tc1 / tc2 (value(T) = value(TNOM) x (1 + tc1 dT + tc2 dT^2), dT = T - 27 C). Without them an ideal R, C or L does not change
    with temperature at all. Diodes, transistors and op-amp models carry their temperature behaviour inside their own SPICE models.
    `given` lists which of the four a person or a document gave (0 is a real value for each, so nothing stands for 'not given').
    Binding: '<board>:<ref>' is that placed part; a row with no board applies to every part whose symbol value or lib_id equals `part_key`.
    Provenance as DatasheetFact carries it: document, page_table, url; entered numbers with no document say so in `origin`.
    Related concepts: `PartThermalModel` (how hot the part gets), `SpiceRun` (the runs at a temperature), the Board Details 'Temperature' tab.
    """

    plain_words = ('The temperatures a part is made to work at, and how much its value drifts as it warms up or cools down - as its datasheet '
                   'says.')

    QUANTITIES = ('t_min_c', 't_max_c', 'tc1_ppm_k', 'tc2_ppm_k2')

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', ref: str = '', part_key: str = '', t_min_c: float = 0.0, t_max_c: float = 0.0,
                 tc1_ppm_k: float = 0.0, tc2_ppm_k2: float = 0.0, given: str = '', document: str = '', page_table: str = '', url: str = '',
                 origin: str = 'given on the page', notes: str = '', manager=None):
        self.name = name                # '<board>:<ref>', or '<part_key>' for a behaviour shared by every board
        self.board = board              # '' = applies wherever part_key matches
        self.ref = ref
        self.part_key = part_key        # the symbol value or lib_id it applies to (when board is '')
        self.t_min_c = t_min_c          # the datasheet's lowest operating temperature, C
        self.t_max_c = t_max_c          # the datasheet's highest operating temperature, C
        self.tc1_ppm_k = tc1_ppm_k      # first-order temperature coefficient, ppm/K (R, C, L only)
        self.tc2_ppm_k2 = tc2_ppm_k2    # second-order temperature coefficient, ppm/K2 (R, C, L only)
        self.given = given              # comma list of the quantities given ('' = none)
        self.document = document
        self.page_table = page_table
        self.url = url
        self.origin = origin            # cited | given on the page | ...
        self.notes = notes
