"""
@module magnetics.objects.magnet.MagneticMaterialOption

Row class MagneticMaterialOption of the magnetics module — one class per file (design §7), split
from magnet_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from magnetics.objects.magnet._shared import OPTION_FAMILIES, REALIZATION_LEVELS

class MagneticMaterialOption(treeObject):
    """One row of the §1c option catalog: identity + realization
    level + forms + property values with per-value provenance.
    Role viability is NOT stored — magnet_analysis derives it."""

    @treeObjectInit
    def __init__(self, name='', display_name='', family='',
                 realization_level='theoretical', item_ref='',
                 msci_material_ref='', powder_ref='',
                 forms_json='[]', properties_json='{}',
                 role_overrides_json='{}', is_reference_only=False,
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.family = (family if family in OPTION_FAMILIES
                       else 'reference')
        self.realization_level = (
            realization_level
            if realization_level in REALIZATION_LEVELS
            else 'theoretical')
        #: supplychain item vocabulary link ('' = not a priced item);
        #: buyable_cited/recipe-seeded checks resolve THROUGH this.
        self.item_ref = item_ref
        #: MaterialsScienceMaterial.name — object coherence: numeric
        #: mu_eff etc. REFERENCE the msci row, values here carry
        #: their own provenance tags.
        self.msci_material_ref = msci_material_ref
        #: MagneticPowderDefinition.name when this option IS a powder.
        self.powder_ref = powder_ref
        self.forms_json = forms_json
        #: {prop: {'value': float, 'unit': str, 'provenance':
        #: 'measured'|'vendor'|'literature-est'|'theoretical',
        #: 'note': str}} — None/absent = honest unknown.
        self.properties_json = properties_json
        #: {role_name: {'verdict': 'viable'|'unviable',
        #: 'reason': str}} — the admin knob, reason REQUIRED.
        self.role_overrides_json = role_overrides_json
        #: NdFeB / electrical steel: priced for parity honesty,
        #: against the local ethos for USE — reports say so.
        self.is_reference_only = is_reference_only
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
