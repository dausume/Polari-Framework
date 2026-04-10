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
CNCLathe Model

CNC lathe/turning machine. For axially symmetric parts.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.devices.deviceCategory import DeviceCategory


class CNCLathe(DeviceCategory):
    """
    CNC lathe/turning machine.

    Defines capabilities for CNC turning operations.

    Attributes:
        # Capacity
        swingOverBed: Maximum swing over bed (mm)
        swingOverCrossSlide: Maximum swing over cross slide (mm)
        maxTurningDiameter: Maximum turning diameter (mm)
        maxTurningLength: Maximum turning length (mm)
        barCapacity: Maximum bar capacity (mm)

        # Spindle
        spindlePower: Spindle power (kW)
        spindleSpeedMin: Minimum spindle speed (RPM)
        spindleSpeedMax: Maximum spindle speed (RPM)
        spindleBore: Spindle bore diameter (mm)
        spindleNose: Spindle nose type (A2-5, A2-6, etc.)

        # Chuck/Collet
        chuckSize: Chuck size (mm)
        chuckType: Chuck type (3-jaw, 4-jaw, collet)
        colletType: Collet type if applicable

        # Axes
        axisCount: Number of axes (2, 3, etc.)
        xTravel: X-axis travel (mm)
        zTravel: Z-axis travel (mm)
        cAxisAvailable: Whether C-axis is available

        # Turret
        turretType: Turret type (drum, disc, gang)
        turretStations: Number of tool stations
        liveToolingAvailable: Whether live tooling is available
        liveToolPower: Live tool power if available (kW)
        liveToolSpeedMax: Live tool max speed (RPM)

        # Tailstock
        hasTailstock: Whether tailstock is available
        tailstockTravel: Tailstock travel (mm)
        tailstockTaper: Tailstock taper (MT2, MT3, etc.)

        # Feed rates
        rapidTraverseX: Rapid traverse X (mm/min)
        rapidTraverseZ: Rapid traverse Z (mm/min)

        # Accuracy
        positioningAccuracy: Positioning accuracy (mm)
        repeatability: Repeatability (mm)

        # Control
        controllerBrand: Controller brand
        controllerModel: Controller model
    """

    DEVICE_CATEGORY = 'cnc_lathe'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='CNC Lathe',
                 description='',
                 manufacturer='',
                 model='',
                 # Capacity
                 swingOverBed=0.0,
                 swingOverCrossSlide=0.0,
                 maxTurningDiameter=0.0,
                 maxTurningLength=0.0,
                 barCapacity=0.0,
                 # Spindle
                 spindlePower=0.0,
                 spindleSpeedMin=0,
                 spindleSpeedMax=0,
                 spindleBore=0.0,
                 spindleNose='',
                 # Chuck/Collet
                 chuckSize=0.0,
                 chuckType='3-jaw',
                 colletType='',
                 # Axes
                 axisCount=2,
                 xTravel=0.0,
                 zTravel=0.0,
                 cAxisAvailable=False,
                 # Turret
                 turretType='drum',
                 turretStations=0,
                 liveToolingAvailable=False,
                 liveToolPower=0.0,
                 liveToolSpeedMax=0,
                 # Tailstock
                 hasTailstock=True,
                 tailstockTravel=0.0,
                 tailstockTaper='',
                 # Feed rates
                 rapidTraverseX=0.0,
                 rapidTraverseZ=0.0,
                 # Accuracy
                 positioningAccuracy=0.0,
                 repeatability=0.0,
                 # Control
                 controllerBrand='',
                 controllerModel=''):
        DeviceCategory.__init__(self, manager=manager, branch=branch, id=id,
                                name=name, description=description,
                                categoryDescription='CNC lathe/turning machine')
        self.manufacturer = manufacturer
        self.model = model

        # Capacity
        self.swingOverBed = swingOverBed
        self.swingOverCrossSlide = swingOverCrossSlide
        self.maxTurningDiameter = maxTurningDiameter
        self.maxTurningLength = maxTurningLength
        self.barCapacity = barCapacity

        # Spindle
        self.spindlePower = spindlePower
        self.spindleSpeedMin = spindleSpeedMin
        self.spindleSpeedMax = spindleSpeedMax
        self.spindleBore = spindleBore
        self.spindleNose = spindleNose

        # Chuck/Collet
        self.chuckSize = chuckSize
        self.chuckType = chuckType
        self.colletType = colletType

        # Axes
        self.axisCount = axisCount
        self.xTravel = xTravel
        self.zTravel = zTravel
        self.cAxisAvailable = cAxisAvailable

        # Turret
        self.turretType = turretType
        self.turretStations = turretStations
        self.liveToolingAvailable = liveToolingAvailable
        self.liveToolPower = liveToolPower
        self.liveToolSpeedMax = liveToolSpeedMax

        # Tailstock
        self.hasTailstock = hasTailstock
        self.tailstockTravel = tailstockTravel
        self.tailstockTaper = tailstockTaper

        # Feed rates
        self.rapidTraverseX = rapidTraverseX
        self.rapidTraverseZ = rapidTraverseZ

        # Accuracy
        self.positioningAccuracy = positioningAccuracy
        self.repeatability = repeatability

        # Control
        self.controllerBrand = controllerBrand
        self.controllerModel = controllerModel

    def __repr__(self):
        return f"CNCLathe(id='{self.id}', name='{self.name}', swing={self.swingOverBed}mm)"
