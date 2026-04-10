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
ThreeDimensionalPrintingDevice Model

Base class for 3D printing devices. Defines common capabilities
that all 3D printers share.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.devices.deviceCategory import DeviceCategory


class ThreeDimensionalPrintingDevice(DeviceCategory):
    """
    Base class for 3D printing devices.

    Defines common capabilities shared by all 3D printer types.
    Specific technologies (FDM, SLA, SLS) inherit from this.

    Attributes:
        printingTechnology: Technology type (fdm, sla, sls, dlp, mjf)
        buildVolumeX: Build volume X dimension (mm)
        buildVolumeY: Build volume Y dimension (mm)
        buildVolumeZ: Build volume Z dimension (mm)
        minLayerHeight: Minimum layer height (mm)
        maxLayerHeight: Maximum layer height (mm)
        positioningAccuracyXY: XY positioning accuracy (mm)
        positioningAccuracyZ: Z positioning accuracy (mm)
        hasEnclosure: Whether printer has enclosure
        hasHeatedEnclosure: Whether enclosure is heated
        connectivity: Connectivity options (usb, wifi, ethernet, sd)
        slicerSoftware: Compatible slicer software
        fileFormats: Supported file formats
    """

    DEVICE_CATEGORY = '3d_printing'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='3D Printer',
                 description='',
                 manufacturer='',
                 model='',
                 printingTechnology='',
                 buildVolumeX=0.0,
                 buildVolumeY=0.0,
                 buildVolumeZ=0.0,
                 minLayerHeight=0.0,
                 maxLayerHeight=0.0,
                 positioningAccuracyXY=0.0,
                 positioningAccuracyZ=0.0,
                 hasEnclosure=False,
                 hasHeatedEnclosure=False,
                 connectivity='',
                 slicerSoftware='',
                 fileFormats=''):
        DeviceCategory.__init__(self, manager=manager, branch=branch, id=id,
                                name=name, description=description,
                                categoryDescription='3D printing device')
        self.manufacturer = manufacturer
        self.model = model
        self.printingTechnology = printingTechnology
        self.buildVolumeX = buildVolumeX
        self.buildVolumeY = buildVolumeY
        self.buildVolumeZ = buildVolumeZ
        self.minLayerHeight = minLayerHeight
        self.maxLayerHeight = maxLayerHeight
        self.positioningAccuracyXY = positioningAccuracyXY
        self.positioningAccuracyZ = positioningAccuracyZ
        self.hasEnclosure = hasEnclosure
        self.hasHeatedEnclosure = hasHeatedEnclosure
        self.connectivity = connectivity
        self.slicerSoftware = slicerSoftware
        self.fileFormats = fileFormats

    def __repr__(self):
        return f"ThreeDimensionalPrintingDevice(id='{self.id}', name='{self.name}', tech='{self.printingTechnology}')"
