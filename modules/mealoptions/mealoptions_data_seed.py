"""
Seed Data — mealoptions

Loads this module's initialData/*.json (the module data convention,
moduleService.json_seeds): the USER-AUTHORED meal rows and computed
PriceReference rows a `pol modules export mealoptions` wrote there,
privacy-stripped by mealoptions.custom.export_hook. The module's own seeds
(SEED_* in the *_basis modules) stay in code and are registered
through MEALOPTIONS_SEED_PAIRS by polariServer, not here.
"""


def seed_initial_data(manager=None):
    """Upsert initialData/ into the live tables (customized rows —
    is_prior False — are never clobbered).

    Returns:
        dict: class name -> list of created row names.
    """
    from moduleService.json_seeds import apply
    return apply('mealoptions', manager, tag='mealoptions.initialData')['created']
