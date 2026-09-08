"""
@module sifet.objects.si.SolGelDielectric

Row class SolGelDielectric of the sifet module — one class per file (design §7), split
from si_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SolGelDielectric(treeObject):
    """Gate dielectric row — thermal SiO2 is the reference member
    of the same class (precursor 'thermal-oxidation'). k / breakdown
    / leakage are PRIORS; leakage never enters Id (refused)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        material: str = 'SiO2',          # SiO2 | HfO2 | ZrO2
        precursor: str = 'TEOS',         # TEOS | Hf-alkoxide | HfCl4 | thermal-oxidation
        solvent: str = 'ethanol',
        hydrolysis_ratio: float = 4.0,   # r = [H2O]/[alkoxide]
        anneal_c: float = 500.0,
        anneal_min: float = 60.0,
        thickness_nm: float = 2.0,
        k_rel: float = 3.9,
        breakdown_mv_per_cm: float = 10.0,
        leakage_prior_a_per_cm2: float = 1e-8,
        density_fraction_of_thermal: float = 1.0,
        confidence: str = 'high',
        citation: str = '[SZE07]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.material = material
        self.precursor = precursor
        self.solvent = solvent
        self.hydrolysis_ratio = hydrolysis_ratio
        self.anneal_c = anneal_c
        self.anneal_min = anneal_min
        self.thickness_nm = thickness_nm
        self.k_rel = k_rel
        self.breakdown_mv_per_cm = breakdown_mv_per_cm
        self.leakage_prior_a_per_cm2 = leakage_prior_a_per_cm2
        self.density_fraction_of_thermal = density_fraction_of_thermal
        self.confidence = confidence
        self.citation = citation
        self.notes = notes
