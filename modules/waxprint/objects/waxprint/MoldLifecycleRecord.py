"""
@module waxprint.objects.waxprint.MoldLifecycleRecord

Row class MoldLifecycleRecord of the waxprint module — one class per file (design §7), split
from waxprint_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MoldLifecycleRecord(treeObject):
    """Mold-strategy tracking (Dustin 2026-07-28): one MOLD's life —
    what it is made of, how many casts it has survived (the reuse
    counter for geopolymer/ceramic molds, sibling of the wax pool's
    reuse-cycles), what releases it from the casting (fresh
    geopolymer BONDS to cured geopolymer — same aluminosilicate
    chemistry — so a release agent is not optional), and where it
    went when it died: crushed-to-aggregate closes the loop back
    into new geopolymer."""

    @treeObjectInit
    def __init__(self, name='', mold_material='geopolymer',
                 product_cast='', master_ref='', mass_kg=0.0,
                 casts_completed=0, release_agent='',
                 condition='in-service', retired_reason='',
                 end_of_life='', crushed_kg_recovered=0.0,
                 is_prior=False, provenance_id='mold-1', notes='',
                 manager=None):
        self.name = name
        #: wax-printed | geopolymer | ceramic-fired (a geopolymer
        #: mold FIRED into ceramic — the Table 8.8 upgrade path).
        self.mold_material = mold_material
        self.product_cast = product_cast
        #: The wax-printed master this mold was cast from ('' for
        #: directly printed wax molds).
        self.master_ref = master_ref
        self.mass_kg = mass_kg
        #: THE reuse counter for this mold.
        self.casts_completed = casts_completed
        #: wax-coat | oil | none — 'none' on geopolymer-in-geopolymer
        #: is a bonded part waiting to happen.
        self.release_agent = release_agent
        #: in-service | degraded | retired.
        self.condition = condition
        self.retired_reason = retired_reason
        #: crushed-to-aggregate | landfill | '' (still alive).
        self.end_of_life = end_of_life
        #: kg recovered as aggregate for NEW geopolymer batches.
        self.crushed_kg_recovered = crushed_kg_recovered
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
