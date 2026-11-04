"""
@module mech.objects.material

The material rows of mech, one class per file: MechMaterialOption (mirrors magnetics' MagneticMaterialOption; registered in composition's MATERIAL_PROPERTY_CLASSES), MechMaterialPreference (the per-part-category default / alternative / legacy ids, checked through composition's role_viability).
"""
from mech.objects.material.MechMaterialOption import MechMaterialOption  # noqa: F401
from mech.objects.material.MechMaterialPreference import MechMaterialPreference  # noqa: F401
