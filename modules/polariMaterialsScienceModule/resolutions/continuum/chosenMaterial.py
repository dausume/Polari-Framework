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
ChosenMaterial Model

Represents a material selected from available options based on
specific criteria or conditions.

Used when:
- Multiple material options exist
- Selection based on temperature/condition
- Design optimization studies
- Material substitution analysis
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.continuum.continuumResolution import ContinuumResolution


class ChosenMaterial(ContinuumResolution):
    """
    Material selected from available options.

    Represents a specific material choice from a set of candidates
    for a particular application or condition.

    Attributes:
        materialId: ID reference to the parent Material
        selectionCriteria: Criteria used to select this material
        conditionRange: Operating conditions for this selection
        alternativeIds: IDs of alternative materials considered
        selectionRationale: Explanation for the selection
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Chosen Material',
                 description='Selected material for specific conditions',
                 selectionCriteria='',
                 conditionRange='',
                 alternativeIds=None,
                 selectionRationale='',
                 youngsModulus=0.0,
                 poissonsRatio=0.0,
                 density=0.0):
        ContinuumResolution.__init__(self, manager=manager, branch=branch, id=id,
                                     materialId=materialId,
                                     name=name, description=description)
        self.selectionCriteria = selectionCriteria
        self.conditionRange = conditionRange
        self.alternativeIds = alternativeIds or []
        self.selectionRationale = selectionRationale
        self.youngsModulus = youngsModulus
        self.poissonsRatio = poissonsRatio
        self.density = density

    def __repr__(self):
        return f"ChosenMaterial(id='{self.id}', materialId='{self.materialId}', criteria='{self.selectionCriteria}')"
