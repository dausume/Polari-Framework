"""
Seed Data — sifet

Loads this module's initial data from JSON files in initialData/
(moduleService.json_seeds). Carries the DERIVED SiliconMOSFET rows;
the basis rows are seeds in si_basis (cntfet.custom.cnt_snapshot RULE).
"""


def seed_initial_data(manager=None):
    from moduleService.json_seeds import apply
    return apply('sifet', manager, tag='sifet.initialData')['created']
