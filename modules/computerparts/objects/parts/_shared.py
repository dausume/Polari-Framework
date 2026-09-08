"""@module computerparts.objects.parts._shared — what the parts row classes share (constants, seeds, helpers); split from parts_basis.py (sap-2c)."""
import json

PART_KINDS = ('gpu', 'cpu', 'motherboard', 'ram', 'storage',
              'psu', 'case', 'cooler', 'nic', 'fpga-accelerator',
              'prebuilt',
              # cmp-c-6: comms (embedded m2-key-e or attached
              # usb-a/usb-c) + the parts that ENABLE usb seats.
              'comms', 'usb-expansion')
CONDITIONS = ('new', 'used', 'refurbished')
def _field(row, name, default=''):
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)
def build_report(build, parts_by_name):
    """Derived cost + parts breakdown for one build. Pure. Missing
    or unpriced parts are STATED, and the oldest price date in the
    build is surfaced — a build is only as fresh as its stalest
    price."""
    try:
        part_names = json.loads(_field(build, 'parts_json', '[]')
                                or '[]')
    except ValueError:
        part_names = []
    parts, missing = [], []
    total = 0.0
    oldest = ''
    for pname in part_names:
        part = parts_by_name.get(pname)
        if part is None:
            missing.append(pname)
            continue
        price = float(_field(part, 'price_amount', 0.0) or 0.0)
        as_of = _field(part, 'price_as_of', '')
        total += price
        if as_of and (not oldest or as_of < oldest):
            oldest = as_of
        parts.append({
            'name': pname,
            'title': _field(part, 'title'),
            'kind': _field(part, 'kind'),
            'condition': _field(part, 'condition'),
            'price_amount': price,
            'price_unit': _field(part, 'price_unit', 'USD'),
            'price_as_of': as_of,
            'price_source': _field(part, 'price_source'),
            'price_note': _field(part, 'price_note'),
        })
    try:
        specs = json.loads(_field(build, 'specs_json', '{}') or '{}')
    except ValueError:
        specs = {}
    return {
        'name': _field(build, 'name'),
        'title': _field(build, 'title'),
        'purpose': _field(build, 'purpose'),
        'specs': specs,
        'parts': parts,
        'missing_parts': missing,
        'total_usd': round(total, 2),
        'price_as_of_oldest': oldest,
        'notes': _field(build, 'notes'),
    }
def break_even_months(build_total_usd, monthly_rental_usd):
    """How many months of rental equal buying outright. Honest
    None when either side is unknown — never a guessed number."""
    if not build_total_usd or not monthly_rental_usd:
        return None
    return round(build_total_usd / monthly_rental_usd, 1)
