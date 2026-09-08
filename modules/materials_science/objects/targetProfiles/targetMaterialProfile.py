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
TargetMaterialProfile Model

A named profile of desired property values for a specific use case.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class TargetMaterialProfile(treeObject):
    """
    A named target profile for desired material properties.

    Attributes:
        name: Name of this target profile
        description: Description of the use case
        purposeId: ID of the PurposeCategory this profile targets
        referenceMaterialId: Optional ID of a baseline ReferenceMaterial
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='',
                 description='',
                 purposeId='',
                 referenceMaterialId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.name = name
        self.description = description
        self.purposeId = purposeId
        self.referenceMaterialId = referenceMaterialId

    def __repr__(self):
        return f"TargetMaterialProfile(id='{getattr(self, 'id', '?')}', name='{getattr(self, 'name', '?')}')"
