"""@module bizops.objects.bizops._shared — what the bizops row classes share (constants, seeds, helpers); split from bizops_basis.py (sap-2c)."""

UPGRADE_KINDS = ('hire-role', 'process-change', 'add-capability')
ORDER_STATUSES = ('requested', 'accepted', 'deferred', 'refused',
                  'done')
COMPLIANCE_LEVELS = ('unassessed', 'theoretical-pass',
                     'self-test-pass',
                     'certified-third-party-pass')
