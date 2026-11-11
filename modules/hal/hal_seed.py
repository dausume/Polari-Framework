"""
@module hal.hal_seed

Seed rows (upserted by name — never insert-by-name). The two SEEDED parts of the HAL: the generalized vocabulary (HalOperation)
and the access mechanisms (HalAccessMechanism). Everything per chip (HalBinding, HalCodeUnit, HalGenerationStep, HalCrossCheck) is
derived on every read by hal.custom.generate from board's cited tables, never seeded.
"""
from hal.hal_basis import HalAccessMechanism, HalOperation
from hal.custom import mechanisms as MX
from hal.custom import operations as OPS

SEED_HAL_OPERATIONS = OPS.seed_rows()
SEED_HAL_MECHANISMS = MX.seed_rows()

HAL_SEED_PAIRS = [
    ('HalOperation', HalOperation, SEED_HAL_OPERATIONS),
    ('HalAccessMechanism', HalAccessMechanism, SEED_HAL_MECHANISMS),
]
