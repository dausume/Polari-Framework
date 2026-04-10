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
CNCMill Model

Base class for CNC milling machines. Defines common capabilities
shared by all CNC mills.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.devices.deviceCategory import DeviceCategory


class CNCMill(DeviceCategory):
    """
    Base class for CNC milling machines.

    Defines common capabilities shared by all CNC mill types.
    Specific configurations (3-axis, 5-axis) inherit from this.

    Attributes:
        # Axes
        axisCount: Number of axes (3, 4, 5)
        workEnvelopeX: Work envelope X dimension (mm)
        workEnvelopeY: Work envelope Y dimension (mm)
        workEnvelopeZ: Work envelope Z dimension (mm)

        # Spindle
        spindlePower: Spindle power (kW)
        spindleSpeedMin: Minimum spindle speed (RPM)
        spindleSpeedMax: Maximum spindle speed (RPM)
        spindleTaper: Spindle taper type (BT30, BT40, CAT40, HSK)
        spindleTorqueMax: Maximum spindle torque (Nm)

        # Feed rates
        rapidTraverseX: Rapid traverse X (mm/min)
        rapidTraverseY: Rapid traverse Y (mm/min)
        rapidTraverseZ: Rapid traverse Z (mm/min)
        feedRateMax: Maximum cutting feed rate (mm/min)

        # Accuracy
        positioningAccuracy: Positioning accuracy (mm)
        repeatability: Repeatability (mm)

        # Tool handling
        toolChangerType: Tool changer type (manual, atc)
        toolCapacity: Tool magazine capacity
        maxToolDiameter: Maximum tool diameter (mm)
        maxToolLength: Maximum tool length (mm)

        # Coolant
        hasCoolantSystem: Whether coolant system exists
        coolantType: Coolant type (flood, mist, through-spindle)
        coolantPressure: Coolant pressure (bar)

        # Table
        tableSize: Table size (mm x mm)
        tableLoadCapacity: Table load capacity (kg)
        hasRotaryTable: Whether rotary table is available

        # Control
        controllerBrand: Controller brand (Fanuc, Siemens, Haas, etc.)
        controllerModel: Controller model

        # Enclosure
        hasEnclosure: Whether fully enclosed
        hasDustExtraction: Whether dust extraction system exists
    """

    DEVICE_CATEGORY = 'cnc_mill'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='CNC Mill',
                 description='',
                 manufacturer='',
                 model='',
                 # Axes
                 axisCount=3,
                 workEnvelopeX=0.0,
                 workEnvelopeY=0.0,
                 workEnvelopeZ=0.0,
                 # Spindle
                 spindlePower=0.0,
                 spindleSpeedMin=0,
                 spindleSpeedMax=0,
                 spindleTaper='',
                 spindleTorqueMax=0.0,
                 # Feed rates
                 rapidTraverseX=0.0,
                 rapidTraverseY=0.0,
                 rapidTraverseZ=0.0,
                 feedRateMax=0.0,
                 # Accuracy
                 positioningAccuracy=0.0,
                 repeatability=0.0,
                 # Tool handling
                 toolChangerType='manual',
                 toolCapacity=0,
                 maxToolDiameter=0.0,
                 maxToolLength=0.0,
                 # Coolant
                 hasCoolantSystem=True,
                 coolantType='flood',
                 coolantPressure=0.0,
                 # Table
                 tableSize='',
                 tableLoadCapacity=0.0,
                 hasRotaryTable=False,
                 # Control
                 controllerBrand='',
                 controllerModel='',
                 # Enclosure
                 hasEnclosure=True,
                 hasDustExtraction=False):
        DeviceCategory.__init__(self, manager=manager, branch=branch, id=id,
                                name=name, description=description,
                                categoryDescription='CNC milling machine')
        self.manufacturer = manufacturer
        self.model = model

        # Axes
        self.axisCount = axisCount
        self.workEnvelopeX = workEnvelopeX
        self.workEnvelopeY = workEnvelopeY
        self.workEnvelopeZ = workEnvelopeZ

        # Spindle
        self.spindlePower = spindlePower
        self.spindleSpeedMin = spindleSpeedMin
        self.spindleSpeedMax = spindleSpeedMax
        self.spindleTaper = spindleTaper
        self.spindleTorqueMax = spindleTorqueMax

        # Feed rates
        self.rapidTraverseX = rapidTraverseX
        self.rapidTraverseY = rapidTraverseY
        self.rapidTraverseZ = rapidTraverseZ
        self.feedRateMax = feedRateMax

        # Accuracy
        self.positioningAccuracy = positioningAccuracy
        self.repeatability = repeatability

        # Tool handling
        self.toolChangerType = toolChangerType
        self.toolCapacity = toolCapacity
        self.maxToolDiameter = maxToolDiameter
        self.maxToolLength = maxToolLength

        # Coolant
        self.hasCoolantSystem = hasCoolantSystem
        self.coolantType = coolantType
        self.coolantPressure = coolantPressure

        # Table
        self.tableSize = tableSize
        self.tableLoadCapacity = tableLoadCapacity
        self.hasRotaryTable = hasRotaryTable

        # Control
        self.controllerBrand = controllerBrand
        self.controllerModel = controllerModel

        # Enclosure
        self.hasEnclosure = hasEnclosure
        self.hasDustExtraction = hasDustExtraction

    def __repr__(self):
        return f"CNCMill(id='{self.id}', name='{self.name}', axes={self.axisCount})"
