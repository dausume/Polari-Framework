"""
@module waxprint.objects.waxprint.WaxReclaimBatch

Row class WaxReclaimBatch of the waxprint module — one class per file (design §7), split
from waxprint_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class WaxReclaimBatch(treeObject):
    """wp-r (2026-07-28): one melt-off reclaim event on a wax pool —
    THE geopolymer-wax-mold-reuse-cycles tracker. Melt the wax off a
    cast geopolymer piece, wash (citric neutralizes the ALKALINE
    residue before it saponifies the ester waxes), settle/filter the
    aluminosilicate fines, log what came back. `generation` counts
    how many melt cycles this pool has seen; quality fields stay 0/
    'untested' until MEASURED — the reuse ceiling is data we do not
    have yet, and these rows are how we get it."""

    @treeObjectInit
    def __init__(self, name='', pool_name='', generation=0,
                 source_note='', melted_off_kg=0.0,
                 recovered_kg=0.0, virgin_makeup_kg=0.0,
                 residue_note='', wash_done=False,
                 wash_ph_result='', melt_point_c_measured=0.0,
                 printability='untested', is_prior=False,
                 provenance_id='wp-r', notes='', manager=None):
        self.name = name
        #: Which wax pool this batch belongs to (pools are just
        #: named buckets of physical wax being cycled).
        self.pool_name = pool_name
        #: geopolymer-wax-mold-reuse-cycles for this pool after this
        #: batch — the counter Dustin asked to track.
        self.generation = generation
        self.source_note = source_note
        self.melted_off_kg = melted_off_kg
        self.recovered_kg = recovered_kg
        self.virgin_makeup_kg = virgin_makeup_kg
        #: What the geopolymer left ON the wax (fines, alkalinity).
        self.residue_note = residue_note
        self.wash_done = wash_done
        #: e.g. red-cabbage / strip result post-wash (research-tools
        #: tree) — neutral means the saponification risk is handled.
        self.wash_ph_result = wash_ph_result
        #: 0.0 = not measured; drift vs the feedstock's window is
        #: the printability early-warning.
        self.melt_point_c_measured = melt_point_c_measured
        #: untested | good | degraded | retired.
        self.printability = printability
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
