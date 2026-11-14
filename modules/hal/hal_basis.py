"""
@module hal.hal_basis

The INDEX of hal rows (design §7): classes live one-per-file under objects/hal/.
"""
from hal.objects.hal.HalOperation import HalOperation  # noqa: F401
from hal.objects.hal.HalAccessMechanism import HalAccessMechanism  # noqa: F401
from hal.objects.hal.HalBinding import HalBinding  # noqa: F401
from hal.objects.hal.HalCodeUnit import HalCodeUnit  # noqa: F401
from hal.objects.hal.HalGenerationStep import HalGenerationStep  # noqa: F401
from hal.objects.hal.HalCrossCheck import HalCrossCheck  # noqa: F401
from hal.objects.hal.HalIsotopeNeed import HalIsotopeNeed  # noqa: F401

HAL_CLASSES = [HalOperation, HalAccessMechanism, HalBinding, HalCodeUnit, HalGenerationStep, HalCrossCheck, HalIsotopeNeed]
