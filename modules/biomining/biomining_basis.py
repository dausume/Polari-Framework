"""
@cross-cutting
@module biomining.biomining_basis
@tags @xc:bindings

Biomining / bioextraction as specialized aquaponic variants (biomine-1).
Own module + own data (framework-core only; a lazy tanks read resolves a
coupled system's surplus for the nutrient-recovery variant). Organisms
(bacteria / algae / biofilm) pull target elements out of the water, and
a refinement pathway carries the raw element to a useful product —
iron → ferrite for magnets, mixed metals → steel feedstock, concentrated
carbon → carbon-nanotube feedstock, or excess nutrients recovered to
SUPPLEMENT a system that lacks them. Each variant is a distinct
"specialized hydroponic" configuration.

Three treeObjects (auto-CRUDE + persisted — object-coherence):

  BioextractionAgent      one organism: what element it targets, by what
                          mechanism, how selectively + how fast.
  BiomineralProduct       the refined output + its pathway (element →
                          refined form → a real MaterialsScienceMaterial
                          where one exists, e.g. 'ferrite',
                          'carbon-nanotube').
  BiomineSystemDefinition a specialized aquaponic VARIANT binding
                          agents + a product + a source stream, with the
                          extraction cap that keeps it from stripping
                          the parent (the biochar/regulation idiom).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - biomining.custom.biomining_analysis
@see materialsScience/ (ferrite + CNT targets), tanks/, microalgae/
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/biomining/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from biomining.objects.biomining._shared import AGENT_TYPES, BIOMINE_VARIANTS, MECHANISMS, PRODUCT_KINDS, SOURCE_KINDS  # noqa: F401
from biomining.objects.biomining.BioextractionAgent import BioextractionAgent  # noqa: F401
from biomining.objects.biomining.BiomineralProduct import BiomineralProduct  # noqa: F401
from biomining.objects.biomining.BiomineSystemDefinition import BiomineSystemDefinition  # noqa: F401
