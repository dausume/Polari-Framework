"""
@module pcb.objects.pcb.SpiceRun

SpiceRun — one class per file (design §7); kxc-3b, the KiCad interchange plan (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md §3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SpiceRun(treeObject):
    """What it is: ONE SIMULATION RUN of an ingested schematic - which deck (its sha256: the deck is rebuilt from our rows, so the sha says which rows),
    what analysis ngspice ended in (`plot`: tran1, ac1, op1), how many points, which solver and where it ran, and whether it finished. The result vectors
    are their own rows (`SpiceVector`, one per vector, naming this run), so a run row stays a summary.
    tmp-1 / tmp-2: the TEMPERATURE it ran at - `temp_c` the whole board's (ngspice's own 27 C when the deck set none: `temp_mode` 'default'),
    'board' when the deck set it (.temp), 'parts' when parts also had their own (`part_temps_json`, instance temp=); `sweep` names the
    temperature sweep the run belongs to ('' for a single run).
    A run can come from this host's libngspice, from a worker that has one (econ-core: KiCad 10.0.6's), or be a recorded reference (`source`).
    Related concepts: `SpiceVector` (the results), `KiCadArtifact` (the schematic and model files the deck includes), the single-Board view (its chart).
    """

    plain_words = 'One time the circuit was simulated: which version of the circuit, what kind of simulation, and whether it finished.'

    SOURCES = ('local', 'worker', 'reference')

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', ran_at: str = '', deck_sha256: str = '', plot: str = '', points: int = 0, engine: str = '',
                 source: str = 'local', host: str = '', ok: bool = False, refused: str = '', notes: str = '', temp_c: float = 27.0,
                 temp_mode: str = 'default', part_temps_json: str = '{}', sweep: str = '', manager=None):
        self.name = name                # '<board>:<deck sha[:12]>:<ran_at>'
        self.board = board              # the ingested board (KiCadArtifact / SchematicSymbol board)
        self.ran_at = ran_at            # ISO-8601 UTC
        self.deck_sha256 = deck_sha256  # the deck that ran (pcb.custom.kicad_spice.build_deck)
        self.plot = plot                # ngspice's plot name: tran1 | ac1 | op1 ...
        self.points = points            # points per vector
        self.engine = engine            # the solver library, as the runner reported it
        self.source = source            # local | worker | reference
        self.host = host                # the host or worker that ran it ('where' is an SQL keyword)
        self.ok = ok
        self.refused = refused          # why it did not run, in words ('' when it ran)
        self.notes = notes
        self.temp_c = temp_c            # the board's temperature, C (27 = ngspice's default, when temp_mode is 'default')
        self.temp_mode = temp_mode      # default | board | parts
        self.part_temps_json = part_temps_json   # {ref: C} the parts given their own temperature (temp_mode 'parts')
        self.sweep = sweep              # the temperature sweep this run is one temperature of ('' = a single run)
