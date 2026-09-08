"""@module computers.objects.computers._shared — what the computers row classes share (constants, seeds, helpers); split from computers_basis.py (sap-2c)."""

def field_of(row, name, default=''):
    """Dict-or-object accessor (the computerparts _field pattern) —
    every pure function here runs against seed dicts in selftests
    and live rows in the API."""
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)
