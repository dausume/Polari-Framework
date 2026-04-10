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
ThreeDimensionalPrintable Model

Defines base conditions for whether a material can be 3D printed
at all with a particular device. This is about fundamental printability,
not application-specific optimization (like mold-making).

Current Focus: FDM (Fused Deposition Modeling)
- This is the easiest and most cost-effective entry point
- SLA/SLS support can be added later by extending this model

Key questions this answers:
- Can this material be printed with this device?
- What are the hard constraints?
- What basic parameters are required?

Relevant Material Properties (for FDM):
The following material properties can affect FDM printability and should be
considered when evaluating whether a material can be 3D printed:
- Elasticity: Affects filament flexibility and feed behavior
- Hardness: Affects filament rigidity and grinding in extruder
- Viscosity: Critical for melt flow through nozzle
- SolidSurfaceEnergy: Affects bed adhesion and layer bonding
- LiquidSurfaceTension: Affects droplet formation and wetting
- TensileStrength: Affects filament strength during feeding
- MeltingPoint: Defines minimum processing temperature
- ThermalExpansion: Affects warping and dimensional accuracy
- GlassTransition: Defines softening point and bed temp requirements
- SmokingPoint: Defines maximum safe processing temperature
- MeltFlowIndex: Quantifies extrusion behavior at temperature
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.purposes.purposeCategory import PurposeCategory


class ThreeDimensionalPrintable(PurposeCategory):
    """
    Base printability definition for a material with a specific device.

    Defines whether a material can realistically be 3D printed
    with a particular printer/setup. This is the prerequisite check
    before considering application-specific purposes like mold fabrication.

    Current Focus: FDM (Fused Deposition Modeling)
    SLA/SLS attributes are included as placeholders for future expansion.

    Attributes:
        materialId: ID reference to the parent Material
        deviceId: ID reference to the 3D printer device
        deviceName: Name of the 3D printer for reference
        isPrintable: Whether the material can be printed at all
        printingTechnology: Technology type (fdm, sla, sls, dlp, mjf)

        # Hard constraints - FDM (Primary Focus)
        nozzleTempMin: Minimum nozzle temp material requires (C)
        nozzleTempMax: Maximum nozzle temp material tolerates (C)
        deviceNozzleTempMax: Maximum temp device can reach (C)
        bedTempRequired: Required bed temperature (C)
        deviceBedTempMax: Maximum bed temp device can reach (C)
        filamentDiameter: Required filament diameter (mm)
        deviceFilamentDiameter: Device filament diameter (mm)

        # Hard constraints - Resin (SLA/DLP) - Future expansion
        wavelengthRequired: Required curing wavelength (nm)
        deviceWavelength: Device wavelength (nm)
        vatCompatibility: Whether material is compatible with vat material

        # Hard constraints - Powder (SLS) - Future expansion
        laserPowerRequired: Required laser power (W)
        deviceLaserPower: Device laser power (W)
        bedTempRequiredSLS: Required powder bed temperature (C)
        deviceBedTempMaxSLS: Device max bed temperature (C)

        # Basic operating parameters
        minLayerHeight: Minimum layer height material supports (mm)
        maxLayerHeight: Maximum layer height material supports (mm)
        deviceLayerHeightRange: Device layer height range
        printSpeedRange: Viable print speed range (mm/s)

        # Material form requirements
        materialForm: Form required (filament, resin, powder)
        materialFormAvailable: Whether material is available in required form

        # Environment requirements
        enclosureRequired: Whether heated enclosure is mandatory
        deviceHasEnclosure: Whether device has enclosure
        ventilationRequired: Whether ventilation is mandatory
        dryingRequired: Whether material must be dried before printing
        dryingTemp: Drying temperature if required (C)
        dryingTime: Drying time if required (hours)

        # Device compatibility (FDM specific)
        hotendType: Required hotend type (all-metal, ptfe-lined)
        deviceHotendType: Device hotend type
        abrasiveResistanceRequired: Whether hardened nozzle needed
        deviceHasHardenedNozzle: Whether device has hardened nozzle

        # Limitations
        limitingFactors: List of factors limiting printability
        notes: Additional notes about printing this material

    Class Constants:
        RELEVANT_PROPERTIES: List of material property names that affect FDM printability
    """

    PURPOSE_CATEGORY = 'three_dimensional_printable'

    # Material properties that affect 3D printability
    # These are the property class names from polariMaterialsScienceModule.properties
    RELEVANT_PROPERTIES = [
        'Elasticity',           # Affects filament flexibility and feed behavior
        'Hardness',             # Affects filament rigidity and grinding in extruder
        'Viscosity',            # Critical for melt flow through nozzle
        'SolidSurfaceEnergy',   # Affects bed adhesion and layer bonding
        'LiquidSurfaceTension', # Affects droplet formation and wetting
        'TensileStrength',      # Affects filament strength during feeding
        'MeltingPoint',         # Defines minimum processing temperature
        'ThermalExpansion',     # Affects warping and dimensional accuracy
        'GlassTransition',      # Defines softening point and bed temp requirements
        'SmokingPoint',         # Defines maximum safe processing temperature
        'MeltFlowIndex'         # Quantifies extrusion behavior at temperature
    ]

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='3D Printable',
                 description='Base printability conditions for 3D printing',
                 deviceId='',
                 deviceName='',
                 isPrintable=True,
                 printingTechnology='fdm',
                 # Hard constraints - FDM (Primary Focus)
                 nozzleTempMin=0.0,
                 nozzleTempMax=0.0,
                 deviceNozzleTempMax=0.0,
                 bedTempRequired=0.0,
                 deviceBedTempMax=0.0,
                 filamentDiameter=1.75,
                 deviceFilamentDiameter=1.75,
                 # Hard constraints - Resin (Future expansion)
                 wavelengthRequired=0,
                 deviceWavelength=0,
                 vatCompatibility=True,
                 # Hard constraints - Powder (Future expansion)
                 laserPowerRequired=0.0,
                 deviceLaserPower=0.0,
                 bedTempRequiredSLS=0.0,
                 deviceBedTempMaxSLS=0.0,
                 # Basic operating parameters
                 minLayerHeight=0.0,
                 maxLayerHeight=0.0,
                 deviceLayerHeightRange='',
                 printSpeedRange='',
                 # Material form
                 materialForm='filament',
                 materialFormAvailable=True,
                 # Environment requirements
                 enclosureRequired=False,
                 deviceHasEnclosure=False,
                 ventilationRequired=False,
                 dryingRequired=False,
                 dryingTemp=0.0,
                 dryingTime=0.0,
                 # Device compatibility
                 hotendType='all-metal',
                 deviceHotendType='',
                 abrasiveResistanceRequired=False,
                 deviceHasHardenedNozzle=False,
                 # Limitations
                 limitingFactors='',
                 notes=''):
        PurposeCategory.__init__(self, manager=manager, branch=branch, id=id,
                                 materialId=materialId,
                                 name=name, description=description,
                                 categoryDescription='3D printability conditions')
        self.deviceId = deviceId
        self.deviceName = deviceName
        self.isPrintable = isPrintable
        self.printingTechnology = printingTechnology

        # Hard constraints - FDM (Primary Focus)
        self.nozzleTempMin = nozzleTempMin
        self.nozzleTempMax = nozzleTempMax
        self.deviceNozzleTempMax = deviceNozzleTempMax
        self.bedTempRequired = bedTempRequired
        self.deviceBedTempMax = deviceBedTempMax
        self.filamentDiameter = filamentDiameter
        self.deviceFilamentDiameter = deviceFilamentDiameter

        # Hard constraints - Resin (Future expansion)
        self.wavelengthRequired = wavelengthRequired
        self.deviceWavelength = deviceWavelength
        self.vatCompatibility = vatCompatibility

        # Hard constraints - Powder (Future expansion)
        self.laserPowerRequired = laserPowerRequired
        self.deviceLaserPower = deviceLaserPower
        self.bedTempRequiredSLS = bedTempRequiredSLS
        self.deviceBedTempMaxSLS = deviceBedTempMaxSLS

        # Basic operating parameters
        self.minLayerHeight = minLayerHeight
        self.maxLayerHeight = maxLayerHeight
        self.deviceLayerHeightRange = deviceLayerHeightRange
        self.printSpeedRange = printSpeedRange

        # Material form
        self.materialForm = materialForm
        self.materialFormAvailable = materialFormAvailable

        # Environment requirements
        self.enclosureRequired = enclosureRequired
        self.deviceHasEnclosure = deviceHasEnclosure
        self.ventilationRequired = ventilationRequired
        self.dryingRequired = dryingRequired
        self.dryingTemp = dryingTemp
        self.dryingTime = dryingTime

        # Device compatibility
        self.hotendType = hotendType
        self.deviceHotendType = deviceHotendType
        self.abrasiveResistanceRequired = abrasiveResistanceRequired
        self.deviceHasHardenedNozzle = deviceHasHardenedNozzle

        # Limitations
        self.limitingFactors = limitingFactors
        self.notes = notes

    def __repr__(self):
        return f"ThreeDimensionalPrintable(id='{self.id}', materialId='{self.materialId}', device='{self.deviceName}', printable={self.isPrintable})"
