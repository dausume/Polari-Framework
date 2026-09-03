"""
@module mealoptions.export_hook

The PRIVACY STRIP for the export path (MEAL_OPTIONS_MODULE_PLAN mo-3,
Dustin 2026-09-03: "user and location oriented data should not be
[pushed up]"). moduleService.json_seeds.export_rows discovers this
module by name and calls, in order, `include_classes` /
`include_prior_classes` / `filter_row` / `strip_fields`.

What may leave the instance: meal data (templates, variations,
recipes, vocabularies, staples' shelf-life + cadence) a person
AUTHORED (is_prior False; seeds stay in code, D5) and the computed
PriceReference rows (food × month × source type × chain × coarse
region — exported regardless of is_prior, they are references not
seeds). What never leaves: any field naming a person, a household, a
place or a day. Two layers, deliberately redundant: `strip_fields`
removes the keys; `filter_row` runs first and REFUSES a row that still
carries a non-empty private value (a schema drift, an attribute stuck
on a row) so the file can never contain it.

PriceReference (mo-2, price_reference_basis) is imported lazily — this
hook works before and after that phase lands.
"""

#: Fields that name a person, a household, a place or a day. The
#: union with PriceReference.PRIVACY_STRIPPED_FIELDS (when present) is
#: what strip_fields() returns.
LOCAL_PRIVATE_FIELDS = (
    'household_name', 'person_name', 'location_name',
    'bulk_location_name', 'observed_date', 'latitude', 'longitude',
    'address', 'purchaser',
)

#: Rows exported whole (not just is_prior False): computed references.
PRIOR_EXEMPT_CLASSES = ('PriceReference',)


def _price_reference():
    """(class_name, stripped-fields tuple) when mo-2 has landed."""
    try:
        from mealoptions.price_reference_basis import (  # noqa: WPS433
            PRIVACY_STRIPPED_FIELDS, PriceReference)
    except Exception:  # noqa: BLE001 — absent before mo-2, or half-landed
        return None, ()
    return PriceReference.__name__, tuple(PRIVACY_STRIPPED_FIELDS)


def strip_fields():
    """Every field removed from every exported row."""
    _name, price_fields = _price_reference()
    return tuple(sorted(set(LOCAL_PRIVATE_FIELDS) | set(price_fields)))


def include_classes():
    """The mealoptions class names + PriceReference when present."""
    from mealoptions import MEALOPTIONS_CLASSES
    names = [c if isinstance(c, str) else c.__name__ for c in MEALOPTIONS_CLASSES]
    price_name, _fields = _price_reference()
    if price_name and price_name not in names:
        names.append(price_name)
    return names


def include_prior_classes():
    price_name, _fields = _price_reference()
    return (price_name,) if price_name else ()


def _blank(value):
    return value in ('', None, 0, 0.0, [], {}, ())


def filter_row(class_name, row):
    """Blank BulkStaple's instance-pointer trio (its offer location
    lives on the instance), then drop ANY row still carrying a
    non-empty private value. Returns the row or None."""
    row = dict(row)
    if class_name == 'BulkStaple':
        from mealoptions.staple_basis import INSTANCE_POINTER_FIELDS
        for field in INSTANCE_POINTER_FIELDS:
            if field in row:
                row[field] = ''
    for field in strip_fields():
        if not _blank(row.get(field)):
            return None
    return row
