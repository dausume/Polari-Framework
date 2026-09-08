"""@module composition.objects.functional._shared — what the functional row classes share (constants, seeds, helpers); split from functional_basis.py (sap-2c)."""
from composition.node_basis import derive_level
from composition.custom.fill_models import FILL_CLASSES, fill_for_class
import json
from composition.custom.data_refs import resolve_named, rows

def variants_of(manager, functional_name):
    return [v for v in rows(manager, 'ConstructionVariantDefinition')
            if getattr(v, 'functional_ref', '') == functional_name]
def variant_report(manager, functional_name,
                   wound_diameter_mm=None, wall_mm=None):
    """One functional part, all its constructions: derived level,
    fill (computed from the class when geometry is stated, refused
    honestly when not), repairability implied by the level."""
    fp, refusal = resolve_named(manager, 'FunctionalPartDefinition',
                                functional_name)
    if refusal:
        return {'ok': False, **refusal}
    variants = variants_of(manager, functional_name)
    if not variants:
        return {'ok': False, 'functional': functional_name,
                'refusal': 'no construction variants — a functional '
                           'part with no way to build it is a '
                           'requirement, not a design',
                'suggestion': {'knob': 'ConstructionVariantDefinition',
                               'action': 'add at least one variant '
                                         'with its node'}}
    out = []
    for v in variants:
        node_ref = getattr(v, 'node_ref', '')
        level = derive_level(manager, node_ref)
        fill = fill_for_class(getattr(v, 'fill_factor_class', 'n/a'),
                              wound_diameter_mm, wall_mm)
        derived = level.get('derived', '')
        out.append({
            'variant': getattr(v, 'name', ''),
            'displayName': getattr(v, 'display_name', ''),
            'node': node_ref,
            'level': level if not level.get('ok') else derived,
            'separableSet': level.get('separableSet', []),
            'boundSet': level.get('boundSet', []),
            # Repairability FOLLOWS from separability — a promoted
            # interface set is exactly what cannot be repaired.
            'repairable': (level.get('ok', False)
                           and derived == 'assembly'),
            'fillClass': getattr(v, 'fill_factor_class', 'n/a'),
            'fill': fill.get('fill') if fill.get('ok') else None,
            'fillNote': fill.get('refusal', fill.get('note', '')),
            'routing': getattr(v, 'routing_ref', '') or
            'routing-unstated (arch-4)',
            'rationale': getattr(v, 'selection_rationale', ''),
        })
    return {
        'ok': True, 'functional': functional_name,
        'purpose': getattr(fp, 'purpose', ''),
        'tunableToward': getattr(fp, 'tunable_toward', ''),
        'allocatedRoles': json.loads(
            getattr(fp, 'allocated_role_refs_json', '') or '[]'),
        'variants': out, 'count': len(out),
        'note': 'these are ALTERNATIVES of one functional part, not '
                'different parts — fill, steps and repairability '
                'are properties of the construction, and choosing '
                'between them is an MBOM decision the EBOM row '
                'survives.',
    }
