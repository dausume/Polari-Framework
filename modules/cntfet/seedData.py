"""
Seed Data — cntfet

Loads this module's initial data from JSON files in initialData/
(the module data convention: moduleService.json_seeds). What is in
those files, and why nothing else, is the RULE in cntfet.cnt_snapshot.
"""


def seed_initial_data(manager=None):
    """Load seed data into the object tree.

    Returns:
        dict: Mapping of class name to list of created instances.
    """
    from moduleService.json_seeds import apply
    return apply('cntfet', manager, tag='cntfet.initialData')['created']
