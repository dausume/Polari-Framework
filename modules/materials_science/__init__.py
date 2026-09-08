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
Polari Materials Science Module

This module provides data models for multi-scale materials science modeling.

Core Concepts:
- Material: Base class representing an actual material (e.g., "Epoxy Resin")
- MaterialProperty: Properties attached to a Material (viscosity, hardness, etc.)
- MaterialResolution: Resolution-level definitions attached to a Material (FEM, MD, DFT)
- MaterialPurpose: Intended uses attached to a Material (3D printing, CNC machining)
- MaterialRelatedDevice: Devices used for testing/fabrication (printers, mills, testers)

Structure:
materials_science/
├── material.py              # Material base class
├── materialProperty.py      # MaterialProperty base class
├── materialResolution.py    # MaterialResolution base class
├── materialPurpose.py       # MaterialPurpose base class
├── properties/              # Material properties by category
│   ├── rheological/         # Flow/deformation (viscosity, elasticity, MFI)
│   ├── mechanical/          # Strength/resistance (hardness, tensile)
│   ├── surface/             # Interfacial (surface energy, surface tension)
│   ├── thermal/             # Temperature-dependent (melting, Tg, CTE)
│   └── physical/            # Basic physical (specific gravity)
├── resolutions/             # Material resolutions by scale
│   ├── experimental/        # Level 0: Real-world measurements
│   ├── continuum/           # Level 1: FEM (Finite Element Methods)
│   ├── mesoscale/           # Level 2: CGMD (Coarse-Grained MD)
│   ├── atomistic/           # Level 3: MD (Molecular Dynamics)
│   └── quantum/             # Level 4: DFT (Density Functional Theory)
├── purposes/                # Material purposes/applications
│   ├── cncMachinable/       # Base CNC machinability with a device
│   ├── threeDimensionalPrintable/  # Base 3D printability with a device
│   └── moldFabrication/     # Fine-resolution mold creation (3D printed, CNC)
├── devices/                 # Devices for testing and fabrication
│   ├── threeDimensionalPrintingDevices/  # 3D printers (FDM, SLA, SLS)
│   ├── cncMills/            # CNC milling machines
│   ├── cncLathes/           # CNC turning machines
│   └── materialTestingDevices/  # Testing equipment
├── referenceMaterials/      # Well-characterized reference materials
│   └── threeDimensionalPrintable/  # FDM printable reference materials
├── rawMaterials/            # Raw/base materials before processing
└── materialSourcing/        # Material sourcing options
    ├── naturalSourcing      # Natural sources (plants, minerals, waste)
    ├── openSourceLocalSourcing  # Open-source, locally producible
    └── commercialSourcing   # Commercial vendors

Usage:
    # Create a material
    material = Material(name="Epoxy Composite", category="composite")

    # Attach properties
    viscosity = KrebsViscosity(materialId=material.id, viscosityKU=85.0)
    hardness = ShoreMeasurement(materialId=material.id, hardnessReading=75)

    # Attach resolution definitions
    experimental = RawExperimentalMaterial(materialId=material.id, ...)
    fem = ConsistentFiniteElementMaterial(materialId=material.id, youngsModulus=3.5e9)

    # Attach purpose definitions (mold fabrication)
    fdm_mold = FDMPrintedMoldMaterial(materialId=material.id, nozzleTempForMold=210)
"""

# Core classes
from materials_science.material_basis import Material
from materials_science.materialProperty_basis import MaterialProperty
from materials_science.materialResolution_basis import MaterialResolution
from materials_science.materialPurpose_basis import MaterialPurpose
from materials_science.materialRelatedDevice_basis import MaterialRelatedDevice

# Import from properties module
from materials_science.custom.properties import (
    # Base category
    PropertyCategory,

    # Category classes
    RheologicalProperty,
    MechanicalProperty,
    SurfaceProperty,
    ThermalProperty,

    # Rheological properties
    Viscosity, KrebsViscosity, StormerViscosity,
    Elasticity, StorageModulus, DMAMeasurement, RheometerMeasurement,
    MeltFlowIndex, MFIValue, MFIMeasurement,

    # Mechanical properties
    Hardness, HardnessScale, ShoreMeasurement,
    TensileStrength, UltimateTensileStrength, TensileMeasurement,

    # Surface properties
    SolidSurfaceEnergy, CriticalSurfaceTension, ContactAngleMeasurement,
    LiquidSurfaceTension, SurfaceTensionValue, WilhelmyMeasurement,

    # Thermal properties
    MeltingPoint, MeltingPointValue, DSCMeltingMeasurement,
    GlassTransition, GlassTransitionTemp, DMAGlassTransitionMeasurement,
    SmokingPoint, SmokingPointValue, SmokingPointMeasurement,
    ThermalExpansion, CoefficientOfThermalExpansion, TMAMeasurement,

    # Physical properties
    SpecificGravity, ReferentialSpecificGravity,
    PycnometerMeasurement, HydrometerMeasurement, DensityMeterMeasurement
)

# Import from resolutions module
from materials_science.custom.resolutions import (
    # Base category
    ResolutionCategory,

    # Category classes
    ExperimentalResolution,
    ContinuumResolution,
    MesoscaleResolution,
    AtomisticResolution,
    QuantumResolution,

    # Experimental (Level 0)
    RawExperimentalMaterial,
    RulesOfMixturesExperimentalMaterial,

    # Continuum (Level 1)
    ConsistentFiniteElementMaterial,
    StochasticFiniteElementMaterial,
    ChosenMaterial,
    RangeMaterial,

    # Mesoscale (Level 2)
    CoarsegrainedMolecularDynamicsMaterial,

    # Atomistic (Level 3)
    MolecularDynamicsMaterial,

    # Quantum (Level 4)
    DensityFunctionalMaterial
)

# Import from purposes module
from materials_science.custom.purposes import (
    # Base category
    PurposeCategory,

    # Base conditions
    CNCMachinable,
    ThreeDimensionalPrintable,

    # Mold Fabrication category
    MoldFabricationPurpose,

    # 3D Printed Molds
    ThreeDimensionalPrintedMoldMaterial,
    FDMPrintedMoldMaterial,
    SLAPrintedMoldMaterial,
    SLSPrintedMoldMaterial,

    # CNC Machined Molds
    CNCMachinedMoldMaterial,
    MilledMoldMaterial,
    TurnedMoldMaterial,

    # Geopolymer Concrete Molds
    GeopolymerConcreteMoldMaterial,
    GeopolymerThermalResistantConcreteMoldMaterial
)

# Import from devices module
from materials_science.custom.devices import (
    # Base category
    DeviceCategory,

    # 3D Printing Devices
    ThreeDimensionalPrintingDevice,
    FDMPrinter,
    SLAPrinter,
    SLSPrinter,

    # CNC Mills
    CNCMill,
    ThreeAxisMill,
    FiveAxisMill,

    # CNC Lathes
    CNCLathe,

    # Material Testing Devices
    MaterialTestingDevice,
    Viscometer,
    HardnessTester,
    TensileTestingMachine,
    ThermalAnalyzer
)

# Import from referenceMaterials module
from materials_science.custom.referenceMaterials import (
    ReferenceMaterial,
    PropertyValueSource,

    # 3D Printable reference materials
    PrintableReferenceMaterial,
    PLA, ABS, PETG, Nylon, TPU, PHA
)

# Import from rawMaterials module
from materials_science.rawMaterials_basis import (
    RawMaterial
)

# Import from materialSourcing module
from materials_science.custom.materialSourcing import (
    MaterialSourcing,
    NaturalSourcing,
    OpenSourceLocalSourcing,
    CommercialSourcing
)

# Import from dataProvenance module
from materials_science.dataProvenance_basis import (
    DataProvenance,
    DataSource
)

# Import from materialAdditives module
from materials_science.materialAdditives_basis import (
    MaterialAdditive,
    PropertyEffect,
    AdditiveCompatibility,
    Compatibilizer
)

# Import from targetProfiles module
from materials_science.targetProfiles_basis import (
    TargetMaterialProfile,
    PropertyTarget
)

# Import from formulation module
from materials_science.formulation_basis import (
    Formulation,
    FormulationComponent,
    FormulationIntent
)

from materials_science.custom.registerMaterialsScienceModule import register_materials_science_defaults
from materials_science.materials_science_data_seed import seed_initial_data


def initialize(manager=None, include_seed_data=False):
    """
    Initialize the Materials Science module.

    Registers all module classes with the manager and optionally
    loads seed data from JSON files. This is the standard entry
    point for loading a polari module.

    Args:
        manager: The object tree manager to register with.
        include_seed_data: If True, also load initial data from
            the initialData/ JSON files into the object tree.

    Returns:
        dict: {
            'registered_classes': dict of class name -> class,
            'seed_data': dict of class name -> [instances] (if include_seed_data)
        }
    """
    # print(f"[MS-Module-Load] initialize() called — manager={'present' if manager else 'None'}, include_seed_data={include_seed_data}")

    registered_classes = register_materials_science_defaults(manager)
    # print(f"[MS-Module-Load] register_materials_science_defaults returned {len(registered_classes)} class entries")

    result = {
        'registered_classes': registered_classes,
        'seed_data': {}
    }

    if manager is not None:
        # Verify classes landed in the object tree
        in_dict = sum(1 for cn in registered_classes if cn in manager.objectTypingDict)
        # print(f"[MS-Module-Load] Verification: {in_dict}/{len(registered_classes)} classes found in manager.objectTypingDict")

    if include_seed_data:
        # print("[MS-Module-Load] Loading seed data...")
        result['seed_data'] = seed_initial_data(manager)
        seed_count = sum(len(v) for v in result['seed_data'].values())
        # print(f"[MS-Module-Load] Seed data loaded: {seed_count} total records")

    return result

__all__ = [
    # Core classes
    'Material',
    'MaterialProperty',
    'MaterialResolution',
    'MaterialPurpose',
    'MaterialRelatedDevice',

    # Property categories
    'PropertyCategory',
    'RheologicalProperty',
    'MechanicalProperty',
    'SurfaceProperty',
    'ThermalProperty',

    # Rheological properties
    'Viscosity', 'KrebsViscosity', 'StormerViscosity',
    'Elasticity', 'StorageModulus', 'DMAMeasurement', 'RheometerMeasurement',
    'MeltFlowIndex', 'MFIValue', 'MFIMeasurement',

    # Mechanical properties
    'Hardness', 'HardnessScale', 'ShoreMeasurement',
    'TensileStrength', 'UltimateTensileStrength', 'TensileMeasurement',

    # Surface properties
    'SolidSurfaceEnergy', 'CriticalSurfaceTension', 'ContactAngleMeasurement',
    'LiquidSurfaceTension', 'SurfaceTensionValue', 'WilhelmyMeasurement',

    # Thermal properties
    'MeltingPoint', 'MeltingPointValue', 'DSCMeltingMeasurement',
    'GlassTransition', 'GlassTransitionTemp', 'DMAGlassTransitionMeasurement',
    'SmokingPoint', 'SmokingPointValue', 'SmokingPointMeasurement',
    'ThermalExpansion', 'CoefficientOfThermalExpansion', 'TMAMeasurement',

    # Physical properties
    'SpecificGravity', 'ReferentialSpecificGravity',
    'PycnometerMeasurement', 'HydrometerMeasurement', 'DensityMeterMeasurement',

    # Resolution categories
    'ResolutionCategory',
    'ExperimentalResolution',
    'ContinuumResolution',
    'MesoscaleResolution',
    'AtomisticResolution',
    'QuantumResolution',

    # Experimental resolutions (Level 0)
    'RawExperimentalMaterial',
    'RulesOfMixturesExperimentalMaterial',

    # Continuum resolutions (Level 1)
    'ConsistentFiniteElementMaterial',
    'StochasticFiniteElementMaterial',
    'ChosenMaterial',
    'RangeMaterial',

    # Mesoscale resolutions (Level 2)
    'CoarsegrainedMolecularDynamicsMaterial',

    # Atomistic resolutions (Level 3)
    'MolecularDynamicsMaterial',

    # Quantum resolutions (Level 4)
    'DensityFunctionalMaterial',

    # Purpose categories
    'PurposeCategory',

    # Base conditions
    'CNCMachinable',
    'ThreeDimensionalPrintable',

    # Mold Fabrication
    'MoldFabricationPurpose',

    # 3D Printed Mold purposes
    'ThreeDimensionalPrintedMoldMaterial',
    'FDMPrintedMoldMaterial',
    'SLAPrintedMoldMaterial',
    'SLSPrintedMoldMaterial',

    # CNC Machined Mold purposes
    'CNCMachinedMoldMaterial',
    'MilledMoldMaterial',
    'TurnedMoldMaterial',

    # Geopolymer Concrete Mold purposes
    'GeopolymerConcreteMoldMaterial',
    'GeopolymerThermalResistantConcreteMoldMaterial',

    # Device categories
    'DeviceCategory',

    # 3D Printing Devices
    'ThreeDimensionalPrintingDevice',
    'FDMPrinter',
    'SLAPrinter',
    'SLSPrinter',

    # CNC Mills
    'CNCMill',
    'ThreeAxisMill',
    'FiveAxisMill',

    # CNC Lathes
    'CNCLathe',

    # Material Testing Devices
    'MaterialTestingDevice',
    'Viscometer',
    'HardnessTester',
    'TensileTestingMachine',
    'ThermalAnalyzer',

    # Reference Materials
    'ReferenceMaterial',
    'PropertyValueSource',
    'PrintableReferenceMaterial',
    'PLA',
    'ABS',
    'PETG',
    'Nylon',
    'TPU',
    'PHA',

    # Raw Materials
    'RawMaterial',

    # Material Sourcing
    'MaterialSourcing',
    'NaturalSourcing',
    'OpenSourceLocalSourcing',
    'CommercialSourcing',

    # Data Provenance
    'DataProvenance',
    'DataSource',

    # Material Additives
    'MaterialAdditive',
    'PropertyEffect',
    'AdditiveCompatibility',
    'Compatibilizer',

    # Target Profiles
    'TargetMaterialProfile',
    'PropertyTarget',

    # Formulation
    'Formulation',
    'FormulationComponent',
    'FormulationIntent',

    # Module initialization
    'initialize',
    'register_materials_science_defaults',
    'seed_initial_data'
]
