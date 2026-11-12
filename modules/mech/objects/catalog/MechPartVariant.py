"""
@module mech.objects.catalog.MechPartVariant

Row class MechPartVariant of the mech module — one class per file (design §7).
mxc-1 (MECH_FREECAD_INTERCHANGE_PLAN §3.1). The class docstring below is the
explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MechPartVariant(treeObject):
    """ONE ORDERABLE / PRINTABLE SIZE of a family: ISO 4762 M5x10, a 2020
    profile cut to 300, a 2x2x6 Gridfinity bin. The family's dimension
    row is RESOLVED here into numbers (dims_json) and its feature
    templates into named MechFeature rows (interfaces_json). Mass is
    per material and stays -1 until an instance sets one (mxc-2)."""

    @treeObjectInit
    def __init__(self, name='', family_ref='', size_key='',
                 designation='', axis_values_json='{}', dims_json='{}',
                 length_mm=-1.0, mass_g=-1.0, mass_g_basis='undetermined',
                 interfaces_json='[]', item_ref='', is_prior=True,
                 provenance_id='', notes='', manager=None):
        #: '<family>-<size key>': 'iso4762-M5x10', 'extrusion-2020-L300',
        #: 'gridfinity-bin-2x2x6', 'drawer-slide-L300'.
        self.name = name
        #: MechPartFamily name.
        self.family_ref = family_ref
        #: The value of the family's size axis that picked the dimension
        #: row ('M5', '2020', '608', '2x2x6').
        self.size_key = size_key
        #: Human designation as the standard writes it: 'ISO 4762 M5x10'.
        self.designation = designation
        #: {axis: value} for every variant axis of the family.
        self.axis_values_json = axis_values_json
        #: The resolved dimension row (numbers, mm) plus whatever the
        #: length rule adds (e.g. 'L'); -1 = undetermined.
        self.dims_json = dims_json
        #: Nominal / cut length in mm; -1 when the family has no length
        #: axis (a nut, a bearing).
        self.length_mm = length_mm
        #: Mass in grams for the family's default material; -1 until set.
        self.mass_g = mass_g
        #: catalog._shared.BASES — how mass_g was arrived at.
        self.mass_g_basis = mass_g_basis
        #: The resolved MechFeature NAMES this variant exposes, in template
        #: order. Every name must resolve to a MechFeature row (selftest).
        self.interfaces_json = interfaces_json
        #: supplychain item reference ('' = not yet an orderable item).
        self.item_ref = item_ref
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
