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
MaterialPurpose Model

Base class for material purposes/applications. MaterialPurpose defines
how a material is intended to be used or processed.

This is a peer concept to MaterialProperty and MaterialResolution:
- MaterialProperty: What characteristics does the material have?
- MaterialResolution: At what scale is the material being modeled?
- MaterialPurpose: What is the material being used for?

Examples:
- 3D printing (FDM, SLA, SLS)
- CNC machining
- Injection molding
- Coating/painting
- Adhesive bonding
- Nanoparticle Embeddings
"""

from objectTreeDecorators import treeObject, treeObjectInit


class MaterialPurpose(treeObject):
    """
    Base class for material purposes/applications.

    A MaterialPurpose defines the intended use or processing method
    for a material. Each purpose may have specific requirements,
    parameters, and constraints.

    Attributes:
        materialId: ID reference to the parent Material
        name: Name of the purpose
        description: Description of the purpose
        purposeCategory: Category of purpose (manufacturing, finishing, etc.)
    """

    PURPOSE_CATEGORY = ''

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='',
                 description='',
                 purposeCategory=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.materialId = materialId
        self.name = name
        self.description = description
        self.purposeCategory = purposeCategory or self.PURPOSE_CATEGORY

    def __repr__(self):
        return f"MaterialPurpose(id='{self.id}', materialId='{self.materialId}', name='{self.name}')"
