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
MaterialTestingDevice Model

Base class for material testing equipment. These devices are used
to measure material properties and generate property measurements.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.devices.deviceCategory import DeviceCategory


class MaterialTestingDevice(DeviceCategory):
    """
    Base class for material testing devices.

    Testing devices measure material properties. Property measurements
    can reference the device that made them via deviceId.

    Attributes:
        testingType: Type of testing (rheological, mechanical, thermal, etc.)
        standardsCompliance: Standards the device complies with (ASTM, ISO)
        measurementRange: Range of measurement
        accuracy: Measurement accuracy
        resolution: Measurement resolution
        calibrationRequired: Whether calibration is required
        calibrationInterval: Calibration interval (days)
        samplePreparation: Sample preparation requirements
        testDuration: Typical test duration
    """

    DEVICE_CATEGORY = 'material_testing'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Material Testing Device',
                 description='',
                 manufacturer='',
                 model='',
                 testingType='',
                 standardsCompliance='',
                 measurementRange='',
                 accuracy='',
                 resolution='',
                 calibrationRequired=True,
                 calibrationInterval=365,
                 samplePreparation='',
                 testDuration=''):
        DeviceCategory.__init__(self, manager=manager, branch=branch, id=id,
                                name=name, description=description,
                                categoryDescription='Material testing equipment')
        self.manufacturer = manufacturer
        self.model = model
        self.testingType = testingType
        self.standardsCompliance = standardsCompliance
        self.measurementRange = measurementRange
        self.accuracy = accuracy
        self.resolution = resolution
        self.calibrationRequired = calibrationRequired
        self.calibrationInterval = calibrationInterval
        self.samplePreparation = samplePreparation
        self.testDuration = testDuration

    def __repr__(self):
        return f"MaterialTestingDevice(id='{self.id}', name='{self.name}', type='{self.testingType}')"
