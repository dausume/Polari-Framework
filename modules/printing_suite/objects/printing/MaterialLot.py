"""
@module printing_suite.objects.printing.MaterialLot

MaterialLot — a spool/batch of printable material on hand.
"""
from objectTreeDecorators import treeObject, treeObjectInit

MATERIAL_FORMS = ('filament', 'pellet', 'resin', 'wax')


class MaterialLot(treeObject):
    """What it is: one physical lot of printable material (a filament spool,
    a wax batch, a resin bottle): its material (a materials_science
    `Material` / waxprint `WaxFeedstockDefinition` by name), form, diameter,
    mass remaining, vendor lot, and where it is.
    Related concepts: `PrintProfile` (how it prints), `Material`
    (materials_science), `WaxFeedstockDefinition` (waxprint),
    `WaxSourceDefinition` (waxsupply), supplychain sourcing rows.
    How it is measured: typed from the label + weighed (`mass_g`); the
    material's properties come from the material rows, not from here.
    """

    @treeObjectInit
    def __init__(self, name: str = '', material: str = '', form: str = 'filament', diameter_mm: float = 1.75,
                 mass_g: float = 0.0, colour: str = '', vendor: str = '', vendor_lot: str = '', location: str = '',
                 opened_at: str = '', dried_at: str = '', is_prior: bool = True, notes: str = ''):
        self.name = name
        self.material = material
        self.form = form
        self.diameter_mm = diameter_mm
        self.mass_g = mass_g
        self.colour = colour
        self.vendor = vendor
        self.vendor_lot = vendor_lot
        self.location = location
        self.opened_at = opened_at
        self.dried_at = dried_at
        self.is_prior = is_prior
        self.notes = notes
