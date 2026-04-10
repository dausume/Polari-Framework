#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
RulesOfMixturesExperimentalMaterial Model

Represents material properties predicted using rules-of-mixtures
calculations for composite/mixture materials.

Rules of mixtures provide estimates for composite properties:
- Rule of mixtures (Voigt): Upper bound, iso-strain assumption
- Inverse rule (Reuss): Lower bound, iso-stress assumption
- Halpin-Tsai: Semi-empirical for fiber composites
- Hashin-Shtrikman: Bounds for isotropic composites

Common applications:
- Polymer blends
- Fiber-reinforced composites
- Filled materials
- Multi-phase alloys
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.experimental.experimentalResolution import ExperimentalResolution


class RulesOfMixturesExperimentalMaterial(ExperimentalResolution):
    """
    Rules-of-mixtures predicted material properties.

    Contains predicted composite properties based on constituent
    materials and their volume/weight fractions.

    Attributes:
        materialId: ID reference to the parent Material (the composite)
        mixtureRule: Rule used (voigt, reuss, halpin-tsai, hashin-shtrikman)
        constituents: List of constituent material IDs
        volumeFractions: Volume fractions of each constituent
        weightFractions: Weight fractions of each constituent
        calculationDate: Date when prediction was made
        notes: Additional notes about the prediction
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Rules of Mixtures Material',
                 description='Predicted composite properties from rules of mixtures',
                 mixtureRule='voigt',
                 constituents=None,
                 volumeFractions=None,
                 weightFractions=None,
                 calculationDate='',
                 notes=''):
        ExperimentalResolution.__init__(self, manager=manager, branch=branch, id=id,
                                        materialId=materialId,
                                        name=name, description=description)
        self.mixtureRule = mixtureRule
        self.constituents = constituents or []
        self.volumeFractions = volumeFractions or []
        self.weightFractions = weightFractions or []
        self.calculationDate = calculationDate
        self.notes = notes

    def __repr__(self):
        return f"RulesOfMixturesExperimentalMaterial(id='{self.id}', materialId='{self.materialId}', rule='{self.mixtureRule}')"
