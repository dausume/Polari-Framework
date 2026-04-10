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
Seed Data Registration

This module provides functions to register default material types and
property definitions in the Polari framework.
"""


def register_materials_science_defaults(manager=None):
    """
    Register default materials science classes with the given manager.

    This function should be called during application initialization to
    register all material science models with the object tree manager.

    Args:
        manager: The object tree manager to register defaults with.
                 If None, defaults are registered globally.

    Returns:
        dict: A dictionary of registered class names to class objects
    """
    # Import core classes
    from polariMaterialsScienceModule.material import Material
    from polariMaterialsScienceModule.materialProperty import MaterialProperty
    from polariMaterialsScienceModule.materialResolution import MaterialResolution
    from polariMaterialsScienceModule.materialPurpose import MaterialPurpose
    from polariMaterialsScienceModule.materialRelatedDevice import MaterialRelatedDevice

    # Import properties
    from polariMaterialsScienceModule.properties import (
        PropertyCategory,
        RheologicalProperty, MechanicalProperty, SurfaceProperty, ThermalProperty,
        Viscosity, KrebsViscosity, StormerViscosity,
        Elasticity, StorageModulus, DMAMeasurement, RheometerMeasurement,
        MeltFlowIndex, MFIValue, MFIMeasurement,
        Hardness, HardnessScale, ShoreMeasurement,
        TensileStrength, UltimateTensileStrength, TensileMeasurement,
        SolidSurfaceEnergy, CriticalSurfaceTension, ContactAngleMeasurement,
        LiquidSurfaceTension, SurfaceTensionValue, WilhelmyMeasurement,
        MeltingPoint, MeltingPointValue, DSCMeltingMeasurement,
        GlassTransition, GlassTransitionTemp, DMAGlassTransitionMeasurement,
        SmokingPoint, SmokingPointValue, SmokingPointMeasurement,
        ThermalExpansion, CoefficientOfThermalExpansion, TMAMeasurement,
        SpecificGravity, ReferentialSpecificGravity,
        PycnometerMeasurement, HydrometerMeasurement, DensityMeterMeasurement
    )

    # Import resolutions
    from polariMaterialsScienceModule.resolutions import (
        ResolutionCategory,
        ExperimentalResolution, ContinuumResolution,
        MesoscaleResolution, AtomisticResolution, QuantumResolution,
        RawExperimentalMaterial, RulesOfMixturesExperimentalMaterial,
        ConsistentFiniteElementMaterial, StochasticFiniteElementMaterial,
        ChosenMaterial, RangeMaterial,
        CoarsegrainedMolecularDynamicsMaterial,
        MolecularDynamicsMaterial,
        DensityFunctionalMaterial
    )

    # Import purposes
    from polariMaterialsScienceModule.purposes import (
        PurposeCategory,
        CNCMachinable, ThreeDimensionalPrintable,
        MoldFabricationPurpose,
        ThreeDimensionalPrintedMoldMaterial, FDMPrintedMoldMaterial,
        SLAPrintedMoldMaterial, SLSPrintedMoldMaterial,
        CNCMachinedMoldMaterial, MilledMoldMaterial, TurnedMoldMaterial,
        GeopolymerConcreteMoldMaterial, GeopolymerThermalResistantConcreteMoldMaterial
    )

    # Import devices
    from polariMaterialsScienceModule.devices import (
        DeviceCategory,
        ThreeDimensionalPrintingDevice, FDMPrinter, SLAPrinter, SLSPrinter,
        CNCMill, ThreeAxisMill, FiveAxisMill,
        CNCLathe,
        MaterialTestingDevice, Viscometer, HardnessTester,
        TensileTestingMachine, ThermalAnalyzer
    )

    # Import reference materials
    from polariMaterialsScienceModule.referenceMaterials import (
        ReferenceMaterial, PropertyValueSource,
        PrintableReferenceMaterial,
        PLA, ABS, PETG, Nylon, TPU, PHA
    )

    # Import raw materials
    from polariMaterialsScienceModule.rawMaterials import (
        RawMaterial
    )

    # Import material sourcing
    from polariMaterialsScienceModule.materialSourcing import (
        MaterialSourcing,
        NaturalSourcing,
        OpenSourceLocalSourcing,
        CommercialSourcing
    )

    # Import data provenance
    from polariMaterialsScienceModule.dataProvenance import (
        DataProvenance,
        DataSource
    )

    # Import material additives
    from polariMaterialsScienceModule.materialAdditives import (
        MaterialAdditive,
        PropertyEffect,
        AdditiveCompatibility,
        Compatibilizer
    )

    # Import target profiles
    from polariMaterialsScienceModule.targetProfiles import (
        TargetMaterialProfile,
        PropertyTarget
    )

    # Import formulation
    from polariMaterialsScienceModule.formulation import (
        Formulation,
        FormulationComponent,
        FormulationIntent
    )

    registered_classes = {
        # Core classes
        'Material': Material,
        'MaterialProperty': MaterialProperty,
        'MaterialResolution': MaterialResolution,
        'MaterialPurpose': MaterialPurpose,
        'MaterialRelatedDevice': MaterialRelatedDevice,

        # Property categories
        'PropertyCategory': PropertyCategory,
        'RheologicalProperty': RheologicalProperty,
        'MechanicalProperty': MechanicalProperty,
        'SurfaceProperty': SurfaceProperty,
        'ThermalProperty': ThermalProperty,

        # Rheological properties
        'Viscosity': Viscosity,
        'KrebsViscosity': KrebsViscosity,
        'StormerViscosity': StormerViscosity,
        'Elasticity': Elasticity,
        'StorageModulus': StorageModulus,
        'DMAMeasurement': DMAMeasurement,
        'RheometerMeasurement': RheometerMeasurement,
        'MeltFlowIndex': MeltFlowIndex,
        'MFIValue': MFIValue,
        'MFIMeasurement': MFIMeasurement,

        # Mechanical properties
        'Hardness': Hardness,
        'HardnessScale': HardnessScale,
        'ShoreMeasurement': ShoreMeasurement,
        'TensileStrength': TensileStrength,
        'UltimateTensileStrength': UltimateTensileStrength,
        'TensileMeasurement': TensileMeasurement,

        # Surface properties
        'SolidSurfaceEnergy': SolidSurfaceEnergy,
        'CriticalSurfaceTension': CriticalSurfaceTension,
        'ContactAngleMeasurement': ContactAngleMeasurement,
        'LiquidSurfaceTension': LiquidSurfaceTension,
        'SurfaceTensionValue': SurfaceTensionValue,
        'WilhelmyMeasurement': WilhelmyMeasurement,

        # Thermal properties
        'MeltingPoint': MeltingPoint,
        'MeltingPointValue': MeltingPointValue,
        'DSCMeltingMeasurement': DSCMeltingMeasurement,
        'GlassTransition': GlassTransition,
        'GlassTransitionTemp': GlassTransitionTemp,
        'DMAGlassTransitionMeasurement': DMAGlassTransitionMeasurement,
        'SmokingPoint': SmokingPoint,
        'SmokingPointValue': SmokingPointValue,
        'SmokingPointMeasurement': SmokingPointMeasurement,
        'ThermalExpansion': ThermalExpansion,
        'CoefficientOfThermalExpansion': CoefficientOfThermalExpansion,
        'TMAMeasurement': TMAMeasurement,

        # Physical properties
        'SpecificGravity': SpecificGravity,
        'ReferentialSpecificGravity': ReferentialSpecificGravity,
        'PycnometerMeasurement': PycnometerMeasurement,
        'HydrometerMeasurement': HydrometerMeasurement,
        'DensityMeterMeasurement': DensityMeterMeasurement,

        # Resolution categories
        'ResolutionCategory': ResolutionCategory,
        'ExperimentalResolution': ExperimentalResolution,
        'ContinuumResolution': ContinuumResolution,
        'MesoscaleResolution': MesoscaleResolution,
        'AtomisticResolution': AtomisticResolution,
        'QuantumResolution': QuantumResolution,

        # Experimental resolutions
        'RawExperimentalMaterial': RawExperimentalMaterial,
        'RulesOfMixturesExperimentalMaterial': RulesOfMixturesExperimentalMaterial,

        # Continuum resolutions
        'ConsistentFiniteElementMaterial': ConsistentFiniteElementMaterial,
        'StochasticFiniteElementMaterial': StochasticFiniteElementMaterial,
        'ChosenMaterial': ChosenMaterial,
        'RangeMaterial': RangeMaterial,

        # Mesoscale resolutions
        'CoarsegrainedMolecularDynamicsMaterial': CoarsegrainedMolecularDynamicsMaterial,

        # Atomistic resolutions
        'MolecularDynamicsMaterial': MolecularDynamicsMaterial,

        # Quantum resolutions
        'DensityFunctionalMaterial': DensityFunctionalMaterial,

        # Purpose categories
        'PurposeCategory': PurposeCategory,

        # Base conditions
        'CNCMachinable': CNCMachinable,
        'ThreeDimensionalPrintable': ThreeDimensionalPrintable,

        # Mold Fabrication
        'MoldFabricationPurpose': MoldFabricationPurpose,

        # 3D Printed Mold purposes
        'ThreeDimensionalPrintedMoldMaterial': ThreeDimensionalPrintedMoldMaterial,
        'FDMPrintedMoldMaterial': FDMPrintedMoldMaterial,
        'SLAPrintedMoldMaterial': SLAPrintedMoldMaterial,
        'SLSPrintedMoldMaterial': SLSPrintedMoldMaterial,

        # CNC Machined Mold purposes
        'CNCMachinedMoldMaterial': CNCMachinedMoldMaterial,
        'MilledMoldMaterial': MilledMoldMaterial,
        'TurnedMoldMaterial': TurnedMoldMaterial,

        # Geopolymer Concrete Mold purposes
        'GeopolymerConcreteMoldMaterial': GeopolymerConcreteMoldMaterial,
        'GeopolymerThermalResistantConcreteMoldMaterial': GeopolymerThermalResistantConcreteMoldMaterial,

        # Device categories
        'DeviceCategory': DeviceCategory,

        # 3D Printing Devices
        'ThreeDimensionalPrintingDevice': ThreeDimensionalPrintingDevice,
        'FDMPrinter': FDMPrinter,
        'SLAPrinter': SLAPrinter,
        'SLSPrinter': SLSPrinter,

        # CNC Mills
        'CNCMill': CNCMill,
        'ThreeAxisMill': ThreeAxisMill,
        'FiveAxisMill': FiveAxisMill,

        # CNC Lathes
        'CNCLathe': CNCLathe,

        # Material Testing Devices
        'MaterialTestingDevice': MaterialTestingDevice,
        'Viscometer': Viscometer,
        'HardnessTester': HardnessTester,
        'TensileTestingMachine': TensileTestingMachine,
        'ThermalAnalyzer': ThermalAnalyzer,

        # Reference Materials
        'ReferenceMaterial': ReferenceMaterial,
        'PropertyValueSource': PropertyValueSource,
        'PrintableReferenceMaterial': PrintableReferenceMaterial,
        'PLA': PLA,
        'ABS': ABS,
        'PETG': PETG,
        'Nylon': Nylon,
        'TPU': TPU,
        'PHA': PHA,

        # Raw Materials
        'RawMaterial': RawMaterial,

        # Material Sourcing
        'MaterialSourcing': MaterialSourcing,
        'NaturalSourcing': NaturalSourcing,
        'OpenSourceLocalSourcing': OpenSourceLocalSourcing,
        'CommercialSourcing': CommercialSourcing,

        # Data Provenance
        'DataProvenance': DataProvenance,
        'DataSource': DataSource,

        # Material Additives
        'MaterialAdditive': MaterialAdditive,
        'PropertyEffect': PropertyEffect,
        'AdditiveCompatibility': AdditiveCompatibility,
        'Compatibilizer': Compatibilizer,

        # Target Profiles
        'TargetMaterialProfile': TargetMaterialProfile,
        'PropertyTarget': PropertyTarget,

        # Formulation
        'Formulation': Formulation,
        'FormulationComponent': FormulationComponent,
        'FormulationIntent': FormulationIntent
    }

    # If a manager is provided, register each class in the object tree
    if manager is not None:
        # print(f"[MS-Module-Load] Registering {len(registered_classes)} classes with manager")
        registered_count = 0
        failed_count = 0
        analyzed_count = 0
        for class_name, class_obj in registered_classes.items():
            try:
                # Check if already registered
                existing = manager.getObjectTyping(className=class_name)
                if existing is not None:
                    # Class already registered — ensure moduleBinding is set
                    existing.moduleBinding = 'materials_science'
                    registered_count += 1
                    continue
                # Register via makeDefaultObjectTyping which creates a polyTypedObject
                # and adds it to manager.objectTypingDict + manager.objectTyping
                typing_obj = manager.makeDefaultObjectTyping(classObj=class_obj)
                if typing_obj is not None:
                    # Allow CRUDE endpoint registration for module classes
                    typing_obj.excludeFromCRUDE = False
                    typing_obj.moduleBinding = 'materials_science'
                    registered_count += 1

                    # Derive polyTypedVars from the constructor signature so the
                    # frontend knows which columns to display — no mock instances needed.
                    try:
                        var_count = typing_obj.initializeVarsFromSignature()
                        analyzed_count += 1
                    except Exception as ae:
                        var_count = 0
                        # print(f"[MS-Module-Load]   {class_name} — registered but var init failed: {ae}")

                    # print(f"[MS-Module-Load]   {class_name} — registered OK, {var_count} vars from signature")
                else:
                    failed_count += 1
                    # print(f"[MS-Module-Load]   {class_name} — makeDefaultObjectTyping returned None")
            except Exception as e:
                failed_count += 1
                # print(f"[MS-Module-Load]   {class_name} — FAILED: {e}")
        # print(f"[MS-Module-Load] Registration complete: {registered_count} succeeded, {failed_count} failed, {analyzed_count} analyzed")
        # print(f"[MS-Module-Load] objectTypingDict now has {len(manager.objectTypingDict)} entries")
        # print(f"[MS-Module-Load] objectTyping list now has {len(manager.objectTyping)} entries")
    else:
        # print("[MS-Module-Load] No manager provided — returning class dict only (no tree registration)")
        pass

    return registered_classes
