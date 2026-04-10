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
MaterialAdditive Model

A material used as an additive to modify properties of a base material.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class MaterialAdditive(treeObject):
    """
    A material used as a property-modifying additive.

    Attributes:
        rawMaterialId: ID of the RawMaterial this additive references
        name: Display name of the additive
        description: Description of the additive and its uses
        additiveForm: Physical form (powder, fiber, flake, liquid)
        maxLoadingPercent: Maximum loading percentage by weight
        compatibilizerRequired: Whether a compatibilizer is needed
        provenanceId: ID of the DataProvenance record
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 rawMaterialId='',
                 name='',
                 description='',
                 additiveForm='',
                 maxLoadingPercent=0.0,
                 compatibilizerRequired=False,
                 provenanceId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.rawMaterialId = rawMaterialId
        self.name = name
        self.description = description
        self.additiveForm = additiveForm
        self.maxLoadingPercent = maxLoadingPercent
        self.compatibilizerRequired = compatibilizerRequired
        self.provenanceId = provenanceId

    def __repr__(self):
        return f"MaterialAdditive(id='{getattr(self, 'id', '?')}', name='{getattr(self, 'name', '?')}', form='{getattr(self, 'additiveForm', '?')}')"
