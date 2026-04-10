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
PurposeCategory Model

Base class for purpose categories. Categories group related
purposes together (e.g., manufacturing, finishing, assembly).
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.materialPurpose import MaterialPurpose


class PurposeCategory(MaterialPurpose):
    """
    Base class for purpose categories.

    Categories group related purposes together. Each category
    defines common attributes and behaviors for its purposes.

    Attributes:
        materialId: ID reference to the parent Material
        name: Name of the category
        description: Description of the category
        categoryDescription: Detailed description of what this category covers
    """

    PURPOSE_CATEGORY = 'category'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Purpose Category',
                 description='',
                 categoryDescription=''):
        MaterialPurpose.__init__(self, manager=manager, branch=branch, id=id,
                                 materialId=materialId,
                                 name=name, description=description)
        self.categoryDescription = categoryDescription

    def __repr__(self):
        return f"PurposeCategory(id='{self.id}', materialId='{self.materialId}', name='{self.name}')"
