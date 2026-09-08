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
Compatibilizer Model

A material that enables combination of otherwise incompatible materials.
Generalizes the EmulsifierMaterial concept to include coupling agents,
dispersants, and surfactants.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class Compatibilizer(treeObject):
    """
    A material enabling combination of incompatible materials.

    Attributes:
        rawMaterialId: ID of the RawMaterial this compatibilizer references
        name: Display name of the compatibilizer
        compatibilizationType: Type (emulsifier, coupling_agent, dispersant, surfactant)
        effectiveness: Effectiveness rating 0-1
        compatibleBaseTypes: Comma-separated list of compatible base material types
        compatibleAdditiveTypes: Comma-separated list of compatible additive types
        provenanceId: ID of the DataProvenance record
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 rawMaterialId='',
                 name='',
                 compatibilizationType='',
                 effectiveness=0.0,
                 compatibleBaseTypes='',
                 compatibleAdditiveTypes='',
                 provenanceId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.rawMaterialId = rawMaterialId
        self.name = name
        self.compatibilizationType = compatibilizationType
        self.effectiveness = effectiveness
        self.compatibleBaseTypes = compatibleBaseTypes
        self.compatibleAdditiveTypes = compatibleAdditiveTypes
        self.provenanceId = provenanceId

    def __repr__(self):
        return f"Compatibilizer(id='{getattr(self, 'id', '?')}', name='{getattr(self, 'name', '?')}', type='{getattr(self, 'compatibilizationType', '?')}')"
