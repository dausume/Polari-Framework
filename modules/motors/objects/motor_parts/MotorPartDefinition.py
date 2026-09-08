"""
@module motors.objects.motor_parts.MotorPartDefinition

Row class MotorPartDefinition of the motors module — one class per file (design §7), split
from motor_parts_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from motors.objects.motor_parts._shared import PART_FUNCTIONS

class MotorPartDefinition(treeObject):
    """One physical piece: its geometry, its material, and its job.

    `shape_ref` points at a MathShapeDefinition, so volume/mass/cost
    derive from the SAME rows the 3D view renders — the picture and
    the bill cannot disagree."""

    @treeObjectInit
    def __init__(self, name='', display_name='', design_ref='',
                 shape_ref='', shape_units='cm', material_ref='',
                 field_buffer_mm=None,
                 function='flux-path',
                 purpose='', why_this_material='', quantity=1,
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.design_ref = design_ref
        self.shape_ref = shape_ref
        #: Distance from the working gap. REQUIRED by the
        #: field-buffered role: a conductive part is acceptable
        #: only where dB/dt is small, and that is geometry, not a
        #: material property.
        self.field_buffer_mm = field_buffer_mm
        #: Units the SHAPE row is authored in. mathshapes'
        #: shape_properties reports volumeCm3, i.e. it assumes cm —
        #: but the Lavet v2 geometry is authored in mm (1 unit =
        #: 1 mm), and reading those as cm silently turned a clock
        #: motor into a 1.1 kg object. Declaring the unit per part
        #: makes the conversion explicit instead of a footnote
        #: nobody applies.
        #: MagneticMaterialOption name, or a supplychain item_ref
        #: for non-magnetic parts (copper wire, steel shaft).
        self.material_ref = material_ref
        self.function = (function if function in PART_FUNCTIONS
                         else 'structural')
        #: WHAT IT IS FOR, in a sentence a builder can act on.
        self.purpose = purpose
        #: Why THIS material for THIS job — the property that
        #: actually decided it, not a general description.
        self.why_this_material = why_this_material
        self.quantity = quantity
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
