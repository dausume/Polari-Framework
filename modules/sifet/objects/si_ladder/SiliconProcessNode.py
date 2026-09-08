"""
@module sifet.objects.si_ladder.SiliconProcessNode

Row class SiliconProcessNode of the sifet module — one class per file (design §7), split
from si_ladder_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SiliconProcessNode(treeObject):
    """One rung of the open-silicon ladder: a process node as a row
    with its two independent axes, the licence facts, the numbers we
    may use (each with its own source) and what we must NOT assume."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        node_nm: float = 0.0,
        architecture: str = 'planar-bulk',   # planar-bulk|finfet|tri-gate|soi
        vdd_v: float = 1.0,
        source: str = 'literature',   # FreePDK45|PTM|ASAP7|FreePDK15|literature|polari-model
        source_url: str = '',
        licence: str = '',            # SPDX; '' when none applies
        licence_verified: bool = False,
        licence_gplv3_compatible: str = 'to-verify',   # yes|no|to-verify
        rights_class: str = 'unresolved',
        fabrication_evidence: str = 'hypothetical',
        manufacturable=None,          # bool | None (evidence-only)
        manufacturable_reason: str = '',
        model_family: str = '',       # BSIM4|BSIM-CMG|VS|none
        key_numbers_json: str = '{}',
        what_we_can_use: str = '',
        what_we_must_not_assume: str = '',
        search_json: str = '{}',      # per SEARCH_PROTOCOL: have/missing
        evidence_json: str = '[]',    # EvidenceItem names
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.node_nm = node_nm
        self.architecture = architecture
        self.vdd_v = vdd_v
        self.source = source
        self.source_url = source_url
        self.licence = licence
        self.licence_verified = licence_verified
        self.licence_gplv3_compatible = licence_gplv3_compatible
        self.rights_class = rights_class
        self.fabrication_evidence = fabrication_evidence
        self.manufacturable = manufacturable
        self.manufacturable_reason = manufacturable_reason
        self.model_family = model_family
        self.key_numbers_json = key_numbers_json
        self.what_we_can_use = what_we_can_use
        self.what_we_must_not_assume = what_we_must_not_assume
        self.search_json = search_json
        self.evidence_json = evidence_json
        self.notes = notes
        self.is_prior = is_prior
