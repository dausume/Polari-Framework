"""
@cross-cutting
@module waxsupply.wax_basis
@tags @xc:bindings

Bio wax SOURCES for hydroponic + food-forest systems (wax-1). Wax is a
cornerstone of the manufacturing pipeline — lost-wax molds + electronic
masking for device fabrication — so we need wax that grows in the same
systems. This models the biological sources (plants, crop byproducts,
insects, macroalgae) with their wax properties, hydroponic feasibility,
and manufacturing use, each linked to a real materialsScience wax
material. Own module + own data (framework-core only).

  WaxSourceDefinition — one source: what organism/byproduct yields the
                        wax, its melt point + hardness, how feasibly it
                        grows hydroponically, its per-plant/feedstock
                        yield, its primary manufacturing use, and the
                        MaterialsScienceMaterial it refines to.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - waxsupply.custom.wax_analysis; supplychain (wax as a material output)
@see materialsScience/ wax materials (beeswax, carnauba-wax, ...)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/wax/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from waxsupply.objects.wax._shared import HYDROPONIC_FEASIBILITY, WAX_SOURCE_TYPES, WAX_USES  # noqa: F401
from waxsupply.objects.wax.WaxSourceDefinition import WaxSourceDefinition  # noqa: F401
