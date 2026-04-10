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
MaterialRelatedDevice Model

Base class for devices related to material processing, testing, and fabrication.
This is a peer concept to MaterialProperty, MaterialResolution, and MaterialPurpose.

Unlike the other three which attach TO a Material via materialId, devices are
independent entities that can be REFERENCED BY purposes to define constraints
and capabilities for material processing.

Relationship:
- Material has Properties, Resolutions, and Purposes attached via materialId
- Purposes reference Devices via deviceId to check compatibility
- Device capabilities determine if a material's purpose can be fulfilled
"""

from objectTreeDecorators import treeObject, treeObjectInit


class MaterialRelatedDevice(treeObject):
    """
    Base class for material-related devices.

    Devices define capabilities and constraints that purposes reference
    to determine material compatibility.

    Attributes:
        name: Device name/model
        description: Device description
        deviceCategory: Category of device (testing, 3d_printing, cnc, etc.)
        manufacturer: Device manufacturer
        model: Model number/name
        serialNumber: Serial number if applicable
        location: Physical location of device
        status: Operational status (operational, maintenance, offline)
        acquisitionDate: When device was acquired
        lastCalibrationDate: Last calibration date for testing devices
        notes: Additional notes
    """

    DEVICE_CATEGORY = ''

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='',
                 description='',
                 deviceCategory='',
                 manufacturer='',
                 model='',
                 serialNumber='',
                 location='',
                 status='operational',
                 acquisitionDate='',
                 lastCalibrationDate='',
                 notes=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.name = name
        self.description = description
        self.deviceCategory = deviceCategory or self.DEVICE_CATEGORY
        self.manufacturer = manufacturer
        self.model = model
        self.serialNumber = serialNumber
        self.location = location
        self.status = status
        self.acquisitionDate = acquisitionDate
        self.lastCalibrationDate = lastCalibrationDate
        self.notes = notes

    def __repr__(self):
        return f"MaterialRelatedDevice(id='{self.id}', name='{self.name}', category='{self.deviceCategory}')"
