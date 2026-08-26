"""
@module computerparts.parts_basis

ai-8 (Dustin): a DEDICATED module for computer parts — GPU cards,
CPUs, everything needed to put a computer together — so the cost
and feasibility of building devices from scratch is TRACKED DATA,
not folklore. Prices follow the ai-7 discipline: every price
carries its as-of date and source; a price without a date is a lie
waiting to happen.

A ComputerBuildDefinition is a parts LIST (by part name) plus the
build's effective specs; its total cost is DERIVED from the part
rows at read time (edit a part's price, every build using it
updates). The appstore's /ai-hosting surface reads these ROWS for
the buy-vs-rent advisory — row reads, never a Python import, so
the modules stay uncoupled.

@consumers
  - computerparts.parts_api (/api/computerparts)
  - appstore.appstore_ai_api (row reads for buy-vs-rent)
  - polariServer defClassList (tables + CRUDE)
  - computerparts.selftest_computerparts
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

#: What a part IS. 'prebuilt' = a whole machine sold as one unit.
#: nic / fpga-accelerator added by cmp-c-1 (the computers module's
#: taxonomy rows document each kind's declared-spec vocabulary).
PART_KINDS = ('gpu', 'cpu', 'motherboard', 'ram', 'storage',
              'psu', 'case', 'cooler', 'nic', 'fpga-accelerator',
              'prebuilt',
              # cmp-c-6: comms (embedded m2-key-e or attached
              # usb-a/usb-c) + the parts that ENABLE usb seats.
              'comms', 'usb-expansion')

#: Part condition — used-market VRAM is the researched value play.
CONDITIONS = ('new', 'used', 'refurbished')


class ComputerPartDefinition(treeObject):
    """One buyable part with a DATED price."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('gpu-rtx3090-used').
        name: str = '',
        title: str = '',
        # PART_KINDS entry.
        kind: str = 'gpu',
        model: str = '',
        # CONDITIONS entry.
        condition: str = 'new',
        # Kind-specific specs: gpu {vram_mb}, cpu {cores, threads},
        # ram {capacity_mb}, storage {capacity_mb}, psu {watts}.
        specs_json: str = '{}',
        price_amount: float = 0.0,
        price_unit: str = 'USD',
        price_as_of: str = '',
        price_source: str = '',
        price_note: str = '',
        notes: str = '',
        published: bool = True,
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.title = title
        self.kind = kind
        self.model = model
        self.condition = condition
        self.specs_json = specs_json
        self.price_amount = price_amount
        self.price_unit = price_unit
        self.price_as_of = price_as_of
        self.price_source = price_source
        self.price_note = price_note
        self.notes = notes
        self.published = published
        self.is_prior = is_prior


class ComputerBuildDefinition(treeObject):
    """One assemblable machine: a parts list + effective specs.
    Total cost is DERIVED from the part rows — never stored."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('build-used-3090').
        name: str = '',
        title: str = '',
        # What this build is FOR ('local AI — 30B-class models').
        purpose: str = '',
        # JSON list of ComputerPartDefinition names.
        parts_json: str = '[]',
        # The build's effective machine specs (the ai-6 gauge
        # vocabulary): cores, ram_mb, disk_mb, gpu_model, vram_mb.
        specs_json: str = '{}',
        notes: str = '',
        published: bool = True,
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.title = title
        self.purpose = purpose
        self.parts_json = parts_json
        self.specs_json = specs_json
        self.notes = notes
        self.published = published
        self.is_prior = is_prior


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
