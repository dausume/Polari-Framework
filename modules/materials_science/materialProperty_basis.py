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
MaterialProperty Model

Abstract core reference object for material properties.
Specific property types (e.g., StormerViscosity, KrebsViscosity) inherit from this
or reference it to provide detailed measurement data.

For Level 3 measurements that come from testing devices, the deviceId field
references a MaterialRelatedDevice (e.g., Viscometer, HardnessTester).
"""

from objectTreeDecorators import treeObject, treeObjectInit


class MaterialProperty(treeObject):
    """
    Abstract core reference for material properties.

    This is meant to be a lightweight reference object that categorizes
    property types. Specific measurement details and data series belong
    in specialized classes like StormerViscosity and KrebsViscosity.

    For measurements, the deviceId field references the MaterialRelatedDevice
    (e.g., Viscometer, HardnessTester) that made the measurement.

    Attributes:
        name: Name of the property type (e.g., 'Viscosity', 'Density', 'pH')
        description: Description of what this property represents
        deviceId: ID reference to the MaterialRelatedDevice used for measurement
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='',
                 description='',
                 deviceId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.name = name
        self.description = description
        self.deviceId = deviceId

    def __repr__(self):
        return f"MaterialProperty(id='{self.id}', name='{self.name}')"
