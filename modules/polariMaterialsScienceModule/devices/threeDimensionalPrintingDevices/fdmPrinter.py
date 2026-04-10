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
FDMPrinter Model

FDM (Fused Deposition Modeling) / FFF (Fused Filament Fabrication) printer.
Defines capabilities specific to filament-based 3D printing.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.devices.threeDimensionalPrintingDevices.threeDimensionalPrintingDevice import ThreeDimensionalPrintingDevice


class FDMPrinter(ThreeDimensionalPrintingDevice):
    """
    FDM/FFF 3D printer device.

    Defines capabilities specific to filament extrusion printers.
    These capabilities are referenced by ThreeDimensionalPrintable
    to determine material compatibility.

    Attributes:
        # Hotend capabilities
        nozzleDiameter: Installed nozzle diameter (mm)
        nozzleDiametersAvailable: Available nozzle sizes
        hotendTempMax: Maximum hotend temperature (C)
        hotendType: Hotend type (all-metal, ptfe-lined)
        hasHardenedNozzle: Whether nozzle is hardened (for abrasives)
        nozzleMaterial: Nozzle material (brass, hardened steel, ruby)

        # Bed capabilities
        bedTempMax: Maximum bed temperature (C)
        bedSurface: Bed surface type (glass, pei, buildtak, magnetic)
        hasHeatedBed: Whether bed is heated
        bedLevelingType: Bed leveling (manual, auto, mesh)

        # Extruder capabilities
        extruderType: Extruder type (direct, bowden)
        filamentDiameter: Supported filament diameter (1.75 or 2.85)
        maxExtrusionSpeed: Maximum extrusion speed (mm/s)
        retractionCapable: Whether retraction is supported
        multiMaterialCapable: Whether multi-material is supported
        extruderCount: Number of extruders

        # Motion capabilities
        maxPrintSpeed: Maximum print speed (mm/s)
        maxTravelSpeed: Maximum travel speed (mm/s)
        accelerationMax: Maximum acceleration (mm/s^2)

        # Environmental
        enclosureTempMax: Maximum enclosure temperature if heated (C)
        hasFilamentRunoutSensor: Whether runout detection exists
        hasFilamentDryer: Whether integrated dryer exists
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='FDM Printer',
                 description='',
                 manufacturer='',
                 model='',
                 buildVolumeX=0.0,
                 buildVolumeY=0.0,
                 buildVolumeZ=0.0,
                 minLayerHeight=0.05,
                 maxLayerHeight=0.4,
                 # Hotend
                 nozzleDiameter=0.4,
                 nozzleDiametersAvailable='0.2,0.4,0.6,0.8',
                 hotendTempMax=260.0,
                 hotendType='all-metal',
                 hasHardenedNozzle=False,
                 nozzleMaterial='brass',
                 # Bed
                 bedTempMax=100.0,
                 bedSurface='pei',
                 hasHeatedBed=True,
                 bedLevelingType='auto',
                 # Extruder
                 extruderType='direct',
                 filamentDiameter=1.75,
                 maxExtrusionSpeed=0.0,
                 retractionCapable=True,
                 multiMaterialCapable=False,
                 extruderCount=1,
                 # Motion
                 maxPrintSpeed=0.0,
                 maxTravelSpeed=0.0,
                 accelerationMax=0.0,
                 # Environmental
                 hasEnclosure=False,
                 hasHeatedEnclosure=False,
                 enclosureTempMax=0.0,
                 hasFilamentRunoutSensor=False,
                 hasFilamentDryer=False):
        ThreeDimensionalPrintingDevice.__init__(
            self, manager=manager, branch=branch, id=id,
            name=name, description=description,
            manufacturer=manufacturer, model=model,
            printingTechnology='fdm',
            buildVolumeX=buildVolumeX,
            buildVolumeY=buildVolumeY,
            buildVolumeZ=buildVolumeZ,
            minLayerHeight=minLayerHeight,
            maxLayerHeight=maxLayerHeight,
            hasEnclosure=hasEnclosure,
            hasHeatedEnclosure=hasHeatedEnclosure)

        # Hotend
        self.nozzleDiameter = nozzleDiameter
        self.nozzleDiametersAvailable = nozzleDiametersAvailable
        self.hotendTempMax = hotendTempMax
        self.hotendType = hotendType
        self.hasHardenedNozzle = hasHardenedNozzle
        self.nozzleMaterial = nozzleMaterial

        # Bed
        self.bedTempMax = bedTempMax
        self.bedSurface = bedSurface
        self.hasHeatedBed = hasHeatedBed
        self.bedLevelingType = bedLevelingType

        # Extruder
        self.extruderType = extruderType
        self.filamentDiameter = filamentDiameter
        self.maxExtrusionSpeed = maxExtrusionSpeed
        self.retractionCapable = retractionCapable
        self.multiMaterialCapable = multiMaterialCapable
        self.extruderCount = extruderCount

        # Motion
        self.maxPrintSpeed = maxPrintSpeed
        self.maxTravelSpeed = maxTravelSpeed
        self.accelerationMax = accelerationMax

        # Environmental
        self.enclosureTempMax = enclosureTempMax
        self.hasFilamentRunoutSensor = hasFilamentRunoutSensor
        self.hasFilamentDryer = hasFilamentDryer

    def __repr__(self):
        return f"FDMPrinter(id='{self.id}', name='{self.name}', hotendMax={self.hotendTempMax}C)"
