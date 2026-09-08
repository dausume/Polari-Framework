"""
@module gears.objects.gear.GearDefinition

Row class GearDefinition of the gears module — one class per file (design §7), split
from gear_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class GearDefinition(treeObject):
    """One physical gear body. Material is BY REFERENCE into the
    existing catalogs (msci material / magnetics option / supply
    item) so cost cascades and realization gates travel unchanged —
    the same discipline as motor material slots."""

    @treeObjectInit
    def __init__(self, name='', display_name='', train_ref='',
                 gear_type_ref='spur', teeth=20, module_mm=1.0,
                 face_width_mm=6.0, pressure_angle_deg=20.0,
                 shaft_ref='', material_ref='',
                 backlash_mm_prior=0.0, is_input=False,
                 is_output=False, is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.train_ref = train_ref
        self.gear_type_ref = gear_type_ref
        #: Tooth count. For a rack this is the (virtual) count used
        #: only for the travel-per-turn math; the type row says so.
        self.teeth = teeth
        #: Module (mm of pitch diameter per tooth) — pitch diameter
        #: = module * teeth. The metric convention; diametral pitch
        #: is a display concern, not a second stored number.
        self.module_mm = module_mm
        self.face_width_mm = face_width_mm
        self.pressure_angle_deg = pressure_angle_deg
        #: The shaft this body rides — bodies sharing a shaft turn
        #: at the SAME speed (that is what makes a compound stage a
        #: compound stage).
        self.shaft_ref = shaft_ref
        self.material_ref = material_ref
        #: Prior until a measured GearVerificationRun replaces it.
        #: Cast T0 parts carry a lot; the train ACCUMULATES it.
        self.backlash_mm_prior = backlash_mm_prior
        self.is_input = is_input
        self.is_output = is_output
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
