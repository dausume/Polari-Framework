"""
@module testing.testing_seed

acct-0: seed rows — every catalog entry becomes a CapabilityCheck
row at boot (idempotent-by-name, like every other seed), status
'never-run' until a CheckRun observes it. Generated FROM the
discovery catalog so the seed can never drift from the surfaces
that actually exist. Skipped automatically on normal builds (the
class is absent from objectTypingDict).

CheckRun rows are NEVER seeded — runs are observed state.
"""

from testing.check_catalog import catalog_checks

SEED_CAPABILITY_CHECKS = [
    {'name': entry['name'], 'category': entry['category'],
     'kind': entry['kind'], 'criticality': entry['criticality'],
     'runner_ref': entry['runner_ref'],
     'description': entry['description']}
    for entry in catalog_checks()
]
