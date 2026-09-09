"""
@module suiteapps.suiteapps_basis

The INDEX of suiteapps rows (design §7). No seeds here: each suite module
seeds its own SuiteAppDefinition / SuitePart / SuiteContract rows.
"""
from suiteapps.objects.suiteapps.SuiteAppDefinition import SuiteAppDefinition  # noqa: F401
from suiteapps.objects.suiteapps.SuitePart import SuitePart, PART_KINDS, PLACEMENTS, ROLES  # noqa: F401
from suiteapps.objects.suiteapps.SuiteContract import SuiteContract  # noqa: F401
from suiteapps.objects.suiteapps.SuitePlacement import SuitePlacement, PLACEMENT_VERDICTS  # noqa: F401

SUITEAPPS_SEED_PAIRS = [('SuiteAppDefinition', SuiteAppDefinition, []), ('SuitePart', SuitePart, []),
                        ('SuiteContract', SuiteContract, []), ('SuitePlacement', SuitePlacement, [])]
SUITEAPPS_CLASSES = [cls for _, cls, _ in SUITEAPPS_SEED_PAIRS]
