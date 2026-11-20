"""
@module hal

The generalized HAL (hal-0, AI-Notes/plans/HAL_CATOM_CATALOGUE_PLAN.md §4a): chip-independent HAL operations (HalOperation),
the access mechanisms that decide how register code is generated (HalAccessMechanism: port-mapped bit, set/clear aliases,
read-modify-write, routing matrices ...), and what the generator derives per SoC pin from board's cited register tables
(HalBinding, HalCodeUnit, HalGenerationStep, HalCrossCheck). /display/hal reviews every generated line step by step.
Requires the board module (its SoC, pin and register tables).
"""
from hal.hal_basis import (HAL_CLASSES, HalAccessMechanism, HalBinding, HalCodeUnit, HalCrossCheck,  # noqa: F401
                           HalGenerationStep, HalIsotopeNeed, HalOperation)
from hal.hal_seed import HAL_SEED_PAIRS  # noqa: F401
from hal.hal_page import SEED_HAL_PAGE_DISPLAYS  # noqa: F401
