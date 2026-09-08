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
Formulation Model

A composite material recipe combining multiple materials.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class Formulation(treeObject):
    """
    A composite material recipe.

    Attributes:
        name: Name of this formulation
        description: Description of the formulation
        targetProfileId: ID of the TargetMaterialProfile this aims to achieve
        baseMaterialId: ID of the primary base RawMaterial
        totalAdditiveLoadPercent: Total additive loading as weight percent
        provenanceId: ID of the DataProvenance record
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='',
                 description='',
                 targetProfileId='',
                 baseMaterialId='',
                 totalAdditiveLoadPercent=0.0,
                 provenanceId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.name = name
        self.description = description
        self.targetProfileId = targetProfileId
        self.baseMaterialId = baseMaterialId
        self.totalAdditiveLoadPercent = totalAdditiveLoadPercent
        self.provenanceId = provenanceId

    def __repr__(self):
        return f"Formulation(id='{getattr(self, 'id', '?')}', name='{getattr(self, 'name', '?')}')"
