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
CNCMachinable Model

Defines base conditions for whether a material can be CNC machined
at all with a particular device. This is about fundamental machinability,
not application-specific optimization (like mold-making).

Key questions this answers:
- Can this material be machined with this device?
- What are the hard constraints?
- What basic parameters are required?
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.purposes.purposeCategory import PurposeCategory


class CNCMachinable(PurposeCategory):
    """
    Base machinability definition for a material with a specific device.

    Defines whether a material can realistically be CNC machined
    with a particular machine/setup. This is the prerequisite check
    before considering application-specific purposes like mold fabrication.

    Attributes:
        materialId: ID reference to the parent Material
        deviceId: ID reference to the CNC device/machine
        deviceName: Name of the CNC device for reference
        isMachinable: Whether the material can be machined at all
        machiningMethod: Primary method (milling, turning, drilling, grinding)

        # Hard constraints
        hardnessLimit: Maximum material hardness device can handle
        materialHardness: Hardness of this material
        spindlePowerRequired: Minimum spindle power needed (kW)
        spindlePowerAvailable: Spindle power of device (kW)
        rigidityRequired: Minimum machine rigidity needed

        # Basic operating parameters
        minSpindleSpeed: Minimum required spindle speed (RPM)
        maxSpindleSpeed: Maximum required spindle speed (RPM)
        deviceSpindleSpeedRange: Device spindle speed range (min-max RPM)
        feedRateRange: Required feed rate range (mm/min)

        # Material characteristics affecting machinability
        abrasiveness: Material abrasiveness (low, medium, high, extreme)
        chipCharacteristic: Chip behavior (stringy, breaking, powdery)
        heatSensitivity: Sensitivity to machining heat (low, medium, high)
        workHardeningRate: Rate of work hardening during machining

        # Requirements
        coolantRequired: Whether coolant is mandatory
        coolantType: Required coolant type if needed
        specialToolingRequired: Whether special tooling is needed
        specialToolingDescription: Description of special tooling
        enclosureRequired: Whether enclosed machining is required
        dustExtractionRequired: Whether dust extraction is mandatory

        # Limitations
        limitingFactors: List of factors limiting machinability
        notes: Additional notes about machining this material
    """

    PURPOSE_CATEGORY = 'cnc_machinable'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='CNC Machinable',
                 description='Base machinability conditions for CNC processing',
                 deviceId='',
                 deviceName='',
                 isMachinable=True,
                 machiningMethod='milling',
                 # Hard constraints
                 hardnessLimit=0.0,
                 materialHardness=0.0,
                 spindlePowerRequired=0.0,
                 spindlePowerAvailable=0.0,
                 rigidityRequired='standard',
                 # Basic operating parameters
                 minSpindleSpeed=0,
                 maxSpindleSpeed=0,
                 deviceSpindleSpeedRange='',
                 feedRateRange='',
                 # Material characteristics
                 abrasiveness='medium',
                 chipCharacteristic='breaking',
                 heatSensitivity='medium',
                 workHardeningRate='none',
                 # Requirements
                 coolantRequired=False,
                 coolantType='',
                 specialToolingRequired=False,
                 specialToolingDescription='',
                 enclosureRequired=False,
                 dustExtractionRequired=False,
                 # Limitations
                 limitingFactors='',
                 notes=''):
        PurposeCategory.__init__(self, manager=manager, branch=branch, id=id,
                                 materialId=materialId,
                                 name=name, description=description,
                                 categoryDescription='CNC machinability conditions')
        self.deviceId = deviceId
        self.deviceName = deviceName
        self.isMachinable = isMachinable
        self.machiningMethod = machiningMethod

        # Hard constraints
        self.hardnessLimit = hardnessLimit
        self.materialHardness = materialHardness
        self.spindlePowerRequired = spindlePowerRequired
        self.spindlePowerAvailable = spindlePowerAvailable
        self.rigidityRequired = rigidityRequired

        # Basic operating parameters
        self.minSpindleSpeed = minSpindleSpeed
        self.maxSpindleSpeed = maxSpindleSpeed
        self.deviceSpindleSpeedRange = deviceSpindleSpeedRange
        self.feedRateRange = feedRateRange

        # Material characteristics
        self.abrasiveness = abrasiveness
        self.chipCharacteristic = chipCharacteristic
        self.heatSensitivity = heatSensitivity
        self.workHardeningRate = workHardeningRate

        # Requirements
        self.coolantRequired = coolantRequired
        self.coolantType = coolantType
        self.specialToolingRequired = specialToolingRequired
        self.specialToolingDescription = specialToolingDescription
        self.enclosureRequired = enclosureRequired
        self.dustExtractionRequired = dustExtractionRequired

        # Limitations
        self.limitingFactors = limitingFactors
        self.notes = notes

    def __repr__(self):
        return f"CNCMachinable(id='{self.id}', materialId='{self.materialId}', device='{self.deviceName}', machinable={self.isMachinable})"
