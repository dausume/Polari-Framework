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
DeviceCategory Model

Base class for device categories. Categories group related
devices together (e.g., 3D printers, CNC machines, testing equipment).
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.materialRelatedDevice import MaterialRelatedDevice


class DeviceCategory(MaterialRelatedDevice):
    """
    Base class for device categories.

    Categories group related devices together. Each category
    defines common attributes and capabilities for its devices.

    Attributes:
        name: Category name
        description: Category description
        categoryDescription: Detailed description of what this category covers
    """

    DEVICE_CATEGORY = 'category'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Device Category',
                 description='',
                 categoryDescription=''):
        MaterialRelatedDevice.__init__(self, manager=manager, branch=branch, id=id,
                                       name=name, description=description)
        self.categoryDescription = categoryDescription

    def __repr__(self):
        return f"DeviceCategory(id='{self.id}', name='{self.name}')"
