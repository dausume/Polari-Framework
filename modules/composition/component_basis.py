"""
@module composition.component_basis

arch-2: the PART COMPONENT — a single-material element, the bottom
of the separability hierarchy (PART_COMPOSITION_HANDOVER §1: one
material row, no internal interfaces).

Two hard-won attribute splits are fields here, not notes:
- COATING is distinct from material, with its own thickness, because
  build adds to diameter and therefore costs window area as a SQUARE
  (handover §3.4 — cotton covering was ruled out by arithmetic).
- MATERIAL CONDITION (temper) is a key, not prose: drawn-then-
  annealed copper is a different property set from as-cast under the
  same base material (practice map §1.2 — C11000-H02 vs O60).
  '' means UNSTATED, which screens like any missing datum.

@consumers polariServer seed passes, composition.node_basis,
composition.composition_seed
"""

from objectTreeDecorators import treeObject, treeObjectInit


class PartComponentDefinition(treeObject):
    """A single-material element: material (+condition), geometry,
    and optionally a coating with its own thickness."""

    @treeObjectInit
    def __init__(self, name='', display_name='', material_ref='',
                 material_condition='', shape_ref='',
                 shape_units='cm', coating_ref='',
                 coating_build_mm=0.0, process_state_ref='',
                 quantity=1, is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: Material row by NAME (data reference, resolved via
        #: composition.data_refs — never an import).
        self.material_ref = material_ref
        #: Temper/condition key; '' = unstated (screens unassessed).
        self.material_condition = material_condition
        #: MathShapeDefinition row + the units it is authored in
        #: (the 1.1 kg clock-motor lesson: units are per-part).
        self.shape_ref = shape_ref
        self.shape_units = shape_units
        #: Coating/covering is NOT the material: it has its own
        #: identity and thickness because it changes geometry one
        #: level up (enamel, oleoresinous varnish, sol-gel silica).
        self.coating_ref = coating_ref
        self.coating_build_mm = coating_build_mm
        #: RoutingOperation that produced this condition (arch-4);
        #: '' = as-received.
        self.process_state_ref = process_state_ref
        self.quantity = quantity
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
