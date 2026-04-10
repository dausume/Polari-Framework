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
SLAPrinter Model

SLA (Stereolithography) / DLP (Digital Light Processing) printer.
Defines capabilities specific to resin-based 3D printing.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.devices.threeDimensionalPrintingDevices.threeDimensionalPrintingDevice import ThreeDimensionalPrintingDevice


class SLAPrinter(ThreeDimensionalPrintingDevice):
    """
    SLA/DLP 3D printer device.

    Defines capabilities specific to resin curing printers.
    These capabilities are referenced by ThreeDimensionalPrintable
    to determine material compatibility.

    Attributes:
        # Light source
        lightSourceType: Light source (laser, lcd, dlp)
        wavelength: UV wavelength (nm), typically 385 or 405
        lightPower: Light source power (mW)
        xyResolution: XY resolution / pixel size (um)

        # Vat/Tank
        vatMaterial: Vat material (fep, nfep, pdms)
        vatCapacity: Vat capacity (ml)
        hasHeatedVat: Whether vat can be heated
        vatTempMax: Maximum vat temperature (C)

        # Build plate
        buildPlateMaterial: Build plate material
        hasFlexibleBuildPlate: Whether plate is flexible/magnetic

        # Motion
        zAxisResolution: Z-axis resolution (um)
        liftSpeed: Maximum lift speed (mm/min)
        retractSpeed: Maximum retract speed (mm/min)

        # Environmental
        hasResinLevelSensor: Whether resin level sensing exists
        hasAirFiltration: Whether air filtration is built in
        hasResinHeating: Whether resin heating is available

        # Software
        antiAliasingSupport: Whether anti-aliasing is supported
        greyLevelCount: Number of grey levels for AA
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='SLA Printer',
                 description='',
                 manufacturer='',
                 model='',
                 buildVolumeX=0.0,
                 buildVolumeY=0.0,
                 buildVolumeZ=0.0,
                 minLayerHeight=0.01,
                 maxLayerHeight=0.1,
                 # Light source
                 lightSourceType='lcd',
                 wavelength=405,
                 lightPower=0.0,
                 xyResolution=0.0,
                 # Vat/Tank
                 vatMaterial='fep',
                 vatCapacity=0.0,
                 hasHeatedVat=False,
                 vatTempMax=0.0,
                 # Build plate
                 buildPlateMaterial='aluminum',
                 hasFlexibleBuildPlate=False,
                 # Motion
                 zAxisResolution=0.0,
                 liftSpeed=0.0,
                 retractSpeed=0.0,
                 # Environmental
                 hasResinLevelSensor=False,
                 hasAirFiltration=False,
                 hasResinHeating=False,
                 # Software
                 antiAliasingSupport=True,
                 greyLevelCount=0):
        ThreeDimensionalPrintingDevice.__init__(
            self, manager=manager, branch=branch, id=id,
            name=name, description=description,
            manufacturer=manufacturer, model=model,
            printingTechnology='sla',
            buildVolumeX=buildVolumeX,
            buildVolumeY=buildVolumeY,
            buildVolumeZ=buildVolumeZ,
            minLayerHeight=minLayerHeight,
            maxLayerHeight=maxLayerHeight)

        # Light source
        self.lightSourceType = lightSourceType
        self.wavelength = wavelength
        self.lightPower = lightPower
        self.xyResolution = xyResolution

        # Vat/Tank
        self.vatMaterial = vatMaterial
        self.vatCapacity = vatCapacity
        self.hasHeatedVat = hasHeatedVat
        self.vatTempMax = vatTempMax

        # Build plate
        self.buildPlateMaterial = buildPlateMaterial
        self.hasFlexibleBuildPlate = hasFlexibleBuildPlate

        # Motion
        self.zAxisResolution = zAxisResolution
        self.liftSpeed = liftSpeed
        self.retractSpeed = retractSpeed

        # Environmental
        self.hasResinLevelSensor = hasResinLevelSensor
        self.hasAirFiltration = hasAirFiltration
        self.hasResinHeating = hasResinHeating

        # Software
        self.antiAliasingSupport = antiAliasingSupport
        self.greyLevelCount = greyLevelCount

    def __repr__(self):
        return f"SLAPrinter(id='{self.id}', name='{self.name}', wavelength={self.wavelength}nm)"
