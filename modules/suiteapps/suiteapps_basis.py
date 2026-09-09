"""
@module suiteapps.suiteapps_basis

The INDEX of suiteapps rows (design §7). No seeds here: each suite module
seeds its own SuiteAppDefinition / SuitePart / SuiteContract rows.
"""
from suiteapps.objects.suiteapps.SuiteAppDefinition import SuiteAppDefinition  # noqa: F401
from suiteapps.objects.suiteapps.SuitePart import SuitePart, PART_KINDS, PLACEMENTS, ROLES  # noqa: F401
from suiteapps.objects.suiteapps.SuiteContract import SuiteContract  # noqa: F401
from suiteapps.objects.suiteapps.SuitePlacement import SuitePlacement, PLACEMENT_VERDICTS  # noqa: F401

from suiteapps.suiteapps_seed import SEED_SUITES, SEED_SUITE_PARTS, SEED_SUITE_CONTRACTS  # noqa: F401

SUITEAPPS_SEED_PAIRS = [('SuiteAppDefinition', SuiteAppDefinition, SEED_SUITES), ('SuitePart', SuitePart, SEED_SUITE_PARTS),
                        ('SuiteContract', SuiteContract, SEED_SUITE_CONTRACTS), ('SuitePlacement', SuitePlacement, [])]
SUITEAPPS_CLASSES = [cls for _, cls, _ in SUITEAPPS_SEED_PAIRS]
