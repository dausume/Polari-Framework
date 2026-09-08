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
Seed Data Loader

Loads initial data from JSON files in the initialData/ directory
and instantiates them as treeObject instances in the object tree.
"""

import json
import os


def seed_initial_data(manager=None):
    """
    Load initial data from JSON files into the object tree.

    Reads well-organized JSON files from the initialData/ directory
    and instantiates them as framework objects. Files are loaded in
    dependency order so that referenced IDs exist before use.

    Args:
        manager: The object tree manager to register instances with.

    Returns:
        dict: Mapping of class name to list of created instances.
    """
    from materials_science.dataProvenance_basis import DataProvenance, DataSource
    from materials_science.rawMaterials_basis import RawMaterial
    from materials_science.materialAdditives_basis import (
        MaterialAdditive, PropertyEffect, AdditiveCompatibility, Compatibilizer
    )
    from materials_science.targetProfiles_basis import TargetMaterialProfile, PropertyTarget
    from materials_science.formulation_basis import Formulation, FormulationComponent, FormulationIntent

    data_dir = os.path.join(os.path.dirname(__file__), 'initialData')

    # Load order respects dependencies:
    # 1. DataSource (no deps)
    # 2. DataProvenance (refs DataSource IDs)
    # 3. RawMaterial (standalone)
    # 4. Compatibilizer (refs RawMaterial, DataProvenance)
    # 5. MaterialAdditive (refs RawMaterial, DataProvenance)
    # 6. PropertyEffect (refs MaterialAdditive, DataProvenance)
    # 7. AdditiveCompatibility (refs MaterialAdditive, RawMaterial, Compatibilizer, DataProvenance)
    # 8. TargetMaterialProfile (refs PurposeCategory, ReferenceMaterial)
    # 9. PropertyTarget (refs TargetMaterialProfile)
    # 10. Formulation (refs TargetMaterialProfile, RawMaterial, DataProvenance)
    # 11. FormulationComponent (refs Formulation, RawMaterial)
    # 12. FormulationIntent (refs Formulation)
    # JSON filename -> Class mapping, in dependency load order.
    # Each JSON file contains an array of objects whose keys match
    # the __init__ kwargs of the mapped class.
    load_order = [
        ('dataSources.json',             DataSource),             # dataProvenance.dataSource
        ('dataProvenances.json',         DataProvenance),         # dataProvenance.dataProvenance
        ('rawMaterials.json',            RawMaterial),            # rawMaterials.rawMaterial
        ('compatibilizers.json',         Compatibilizer),         # materialAdditives.compatibilizer
        ('materialAdditives.json',       MaterialAdditive),       # materialAdditives.materialAdditive
        ('propertyEffects.json',         PropertyEffect),         # materialAdditives.propertyEffect
        ('additiveCompatibilities.json', AdditiveCompatibility),  # materialAdditives.additiveCompatibility
        ('targetMaterialProfiles.json',  TargetMaterialProfile),  # targetProfiles.targetMaterialProfile
        ('propertyTargets.json',         PropertyTarget),         # targetProfiles.propertyTarget
        ('formulations.json',            Formulation),            # formulation.formulation
        ('formulationComponents.json',   FormulationComponent),   # formulation.formulationComponent
        ('formulationIntents.json',      FormulationIntent),      # formulation.formulationIntent
    ]

    # print(f"[MS-Module-Load] [seedData] data_dir={data_dir} exists={os.path.isdir(data_dir)}")
    if os.path.isdir(data_dir):
        # print(f"[MS-Module-Load] [seedData] files in data_dir: {os.listdir(data_dir)}")
        pass

    created = {}
    for filename, cls in load_order:
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            # print(f"[MS-Module-Load] [seedData] {filename} — NOT FOUND, skipping")
            continue
        try:
            with open(filepath, 'r') as f:
                records = json.load(f)
            # print(f"[MS-Module-Load] [seedData] {filename} — {len(records)} records for {cls.__name__}")
            instances = []
            for idx, record in enumerate(records):
                try:
                    record['manager'] = manager
                    obj = cls(**record)
                    instances.append(obj)
                except Exception as inst_err:
                    # print(f"[MS-Module-Load] [seedData]   {cls.__name__} record {idx} FAILED: {inst_err}")
                    pass
            created[cls.__name__] = instances
            # print(f"[MS-Module-Load] [seedData]   -> created {len(instances)} instances")
        except Exception as file_err:
            # print(f"[MS-Module-Load] [seedData] {filename} — ERROR: {file_err}")
            import traceback
            traceback.print_exc()

    total = sum(len(v) for v in created.values())
    # print(f"[MS-Module-Load] [seedData] Complete: {total} total instances across {len(created)} classes")
    return created
