"""
@module cmod.objects.cmod.MeasurementPoint

MeasurementPoint - one class per file (design section 7); msv-0 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MeasurementPoint(treeObject):
    """What it is: ONE THING TO MEASURE in a node's state - a quantity (V dc between two nets, I dc in series with a part) at a place, with the
    PREDICTION the simulation makes for it and where the prediction came from. Derived from the node's electrical circuit state (the cst slice's ngspice
    .op over the same rows the bench renders); a person may add one (origin person), kept beside the derived ones.
    Related concepts: `StructNode`, `MeasurementReading`, `StructNodeCollateral` (the electrical collateral the state comes from).
    """

    plain_words = ('One reading a person should take with a meter while the device is in a given situation, and what the simulation says it should read.')

    @treeObjectInit
    def __init__(self, name: str = '', node: str = '', quantity: str = 'V dc', plus_at: str = '', minus_at: str = 'GND', where: str = '', nominal: float = 0.0, si_unit: str = 'V', source: str = '', basis: str = '', run: str = '', hex_sha256: str = '', state: str = '', origin: str = 'derived', order: int = 0, manager=None):
        self.name = name    # '<node>-mp-<slug>'
        self.node = node    # a StructNode name
        self.quantity = quantity    # V dc | I dc
        self.plus_at = plus_at    # the net the red probe goes on (V) / the part the meter goes in series with (I)
        self.minus_at = minus_at    # the net the black probe goes on (V); for I the words say where to break the circuit
        self.where = where    # the probing words: the board pins on the net, or the part junction
        self.nominal = nominal    # the predicted value in SI units (V / A)
        self.si_unit = si_unit    # V | A
        self.source = source    # what predicted it: the engine and the state
        self.basis = basis    # what the prediction assumes, said
        self.run = run    # the StructNodeRun whose settled state was used
        self.hex_sha256 = hex_sha256    # the build of that run
        self.state = state    # the circuit state name (led-on ...)
        self.origin = origin    # derived | person
        self.order = order
