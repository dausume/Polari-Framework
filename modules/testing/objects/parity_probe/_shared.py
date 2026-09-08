"""@module testing.objects.parity_probe._shared — what the parity_probe row classes share (constants, seeds, helpers); split from parity_probe_basis.py (sap-2c)."""

TABLE = 'Acct1ParityProbe'
COLUMN_DEFS = [
    'name TEXT PRIMARY KEY',
    'count INTEGER',
    'ratio REAL',
    'note NONE',   # sqlite's typeless affinity — the translation
                   # edge case (mariadb has no NONE; adapter maps it)
]
