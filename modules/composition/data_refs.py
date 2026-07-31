"""
@module composition.data_refs

Cross-module DATA references (PART_ARCHETYPES_PLAN §3.2 — the bizops
rule). Composition imports no domain module; material and equation
references resolve by manager lookup at runtime, and when the module
owning a table is not booted the resolver REFUSES honestly, naming
the module, in the lazy-boot style — never a silent empty.

@consumers composition.part_roles, composition.node_basis,
composition.composition_seed
"""

import json

#: Where property-bearing material rows live today. Extendable as
#: data — a new property-bearing class is one entry, not an import.
MATERIAL_PROPERTY_CLASSES = ('MagneticMaterialOption',)


def rows(manager, class_name):
    return list(getattr(manager, 'objectTables', {}).get(
        class_name, {}).values())


def named(manager, class_name, name):
    for row in rows(manager, class_name):
        if getattr(row, 'name', None) == name:
            return row
    return None


def table_available(manager, class_name):
    """Is the class booted at all? Distinguishes 'no such row' from
    'the module that owns this table is not running'."""
    tables = getattr(manager, 'objectTables', {}) or {}
    if class_name in tables:
        return True
    typing = getattr(manager, 'objectTypingDict', None)
    return bool(typing) and class_name in typing


def resolve_named(manager, class_name, name):
    """(row, refusal) — exactly one is non-None. The refusal names
    what would fix it, per the I-do-not-know discipline."""
    if not table_available(manager, class_name):
        return None, {
            'refusal': f'{class_name} table is not booted — the '
                       f'module that owns it is gated off or not '
                       f'yet admitted',
            'kind': 'module-not-booted', 'class': class_name}
    row = named(manager, class_name, name)
    if row is None:
        return None, {
            'refusal': f'no {class_name} named "{name}"',
            'kind': 'no-such-row', 'class': class_name, 'name': name}
    return row, None


def material_prop(manager, material_ref, key):
    """(value, provenance) for one property of a material row,
    searched across MATERIAL_PROPERTY_CLASSES. Missing anywhere =
    (None, '') — callers treat that as UNASSESSED, never a pass."""
    for class_name in MATERIAL_PROPERTY_CLASSES:
        opt = named(manager, class_name, material_ref)
        if opt is None:
            continue
        try:
            props = json.loads(
                getattr(opt, 'properties_json', '') or '{}')
        except (TypeError, ValueError):
            return None, ''
        entry = props.get(key)
        if not isinstance(entry, dict):
            return None, ''
        return entry.get('value'), entry.get('provenance', '')
    return None, ''
