"""
@module magnetics.objects.magnet.MaterialUseRole

Row class MaterialUseRole of the magnetics module — one class per file (design §7), split
from magnet_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MaterialUseRole(treeObject):
    """One functional role in the taxonomy (mag-2r), with
    required-property PREDICATES as editable JSON knobs so viability
    is DERIVED from property rows, never hand-stamped."""

    @treeObjectInit
    def __init__(self, name='', display_name='', description='',
                 predicates_json='{}', applicable_forms_json='[]',
                 honesty_note='', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        #: {'all': [{prop, op, value, unit?}, ...]} — every predicate
        #: must hold; or {'any': [{mechanism, all: [...]}, ...]} —
        #: alternative mechanisms, the MATCHED mechanism is tagged on
        #: the verdict (flux-containment's shunt-vs-fence split).
        self.predicates_json = predicates_json
        #: JSON list of MATERIAL_FORMS where this role makes sense.
        self.applicable_forms_json = applicable_forms_json
        #: Physics honesty that TRAVELS WITH EVERY MATCH (Earnshaw on
        #: magnetic-bearing, the copper gap on signal conduction).
        self.honesty_note = honesty_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
