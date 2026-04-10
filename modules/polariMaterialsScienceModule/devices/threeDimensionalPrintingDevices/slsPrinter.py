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
SLSPrinter Model

SLS (Selective Laser Sintering) printer.
Defines capabilities specific to powder-based 3D printing.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.devices.threeDimensionalPrintingDevices.threeDimensionalPrintingDevice import ThreeDimensionalPrintingDevice


class SLSPrinter(ThreeDimensionalPrintingDevice):
    """
    SLS 3D printer device.

    Defines capabilities specific to powder sintering printers.
    These capabilities are referenced by ThreeDimensionalPrintable
    to determine material compatibility.

    Attributes:
        # Laser
        laserType: Laser type (co2, fiber)
        laserPower: Laser power (W)
        laserSpotSize: Laser spot size (um)
        scanSpeed: Maximum scan speed (mm/s)

        # Powder bed
        bedTempMax: Maximum powder bed temperature (C)
        bedHeatingZones: Number of heating zones
        powderLayerThicknessMin: Minimum layer thickness (mm)
        powderLayerThicknessMax: Maximum layer thickness (mm)

        # Powder handling
        powderCapacity: Powder capacity (L or kg)
        hasPowderRecycling: Whether powder recycling is supported
        hasInertAtmosphere: Whether inert atmosphere (N2/Ar) is used
        atmosphereType: Atmosphere type (air, nitrogen, argon)

        # Thermal management
        hasChamberHeating: Whether chamber is heated
        chamberTempMax: Maximum chamber temperature (C)
        cooldownTimeTypical: Typical cooldown time (hours)

        # Safety
        hasFireSuppression: Whether fire suppression exists
        hasPowderContainment: Whether powder containment system exists
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='SLS Printer',
                 description='',
                 manufacturer='',
                 model='',
                 buildVolumeX=0.0,
                 buildVolumeY=0.0,
                 buildVolumeZ=0.0,
                 minLayerHeight=0.06,
                 maxLayerHeight=0.15,
                 # Laser
                 laserType='co2',
                 laserPower=0.0,
                 laserSpotSize=0.0,
                 scanSpeed=0.0,
                 # Powder bed
                 bedTempMax=0.0,
                 bedHeatingZones=1,
                 powderLayerThicknessMin=0.0,
                 powderLayerThicknessMax=0.0,
                 # Powder handling
                 powderCapacity=0.0,
                 hasPowderRecycling=False,
                 hasInertAtmosphere=False,
                 atmosphereType='air',
                 # Thermal management
                 hasChamberHeating=True,
                 chamberTempMax=0.0,
                 cooldownTimeTypical=0.0,
                 # Safety
                 hasFireSuppression=False,
                 hasPowderContainment=False):
        ThreeDimensionalPrintingDevice.__init__(
            self, manager=manager, branch=branch, id=id,
            name=name, description=description,
            manufacturer=manufacturer, model=model,
            printingTechnology='sls',
            buildVolumeX=buildVolumeX,
            buildVolumeY=buildVolumeY,
            buildVolumeZ=buildVolumeZ,
            minLayerHeight=minLayerHeight,
            maxLayerHeight=maxLayerHeight,
            hasEnclosure=True)

        # Laser
        self.laserType = laserType
        self.laserPower = laserPower
        self.laserSpotSize = laserSpotSize
        self.scanSpeed = scanSpeed

        # Powder bed
        self.bedTempMax = bedTempMax
        self.bedHeatingZones = bedHeatingZones
        self.powderLayerThicknessMin = powderLayerThicknessMin
        self.powderLayerThicknessMax = powderLayerThicknessMax

        # Powder handling
        self.powderCapacity = powderCapacity
        self.hasPowderRecycling = hasPowderRecycling
        self.hasInertAtmosphere = hasInertAtmosphere
        self.atmosphereType = atmosphereType

        # Thermal management
        self.hasChamberHeating = hasChamberHeating
        self.chamberTempMax = chamberTempMax
        self.cooldownTimeTypical = cooldownTimeTypical

        # Safety
        self.hasFireSuppression = hasFireSuppression
        self.hasPowderContainment = hasPowderContainment

    def __repr__(self):
        return f"SLSPrinter(id='{self.id}', name='{self.name}', laserPower={self.laserPower}W)"
