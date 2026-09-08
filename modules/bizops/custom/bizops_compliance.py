"""
@module bizops.custom.bizops_compliance

Sellability + QA reporting (biz-4): which sale contexts a product
variant is allowed in RIGHT NOW, derived from ComplianceRecord
attainment vs each requirement's required_level — and QA pass rates
from QualityCheckRecord rows. Levels are earned by evidence; the
food-contact context stays blocked without certified third-party
testing, always. NOT LEGAL ADVICE — every report says so.
"""

from bizops.bizops_basis import COMPLIANCE_LEVELS
from bizops.custom.bizops_flows import _loads, _named, _rows

DISCLAIMER = ('requirement references are pointers, NOT legal '
              'advice — verify for your jurisdiction')


def _level_index(level):
    try:
        return COMPLIANCE_LEVELS.index(level)
    except ValueError:
        return 0


def _attained(manager, business_name, variant, requirement_name):
    """Best attained level for (business, variant, requirement) —
    variant-specific rows win; ''-variant rows apply business-wide
    (licenses, labeling templates)."""
    best = 'unassessed'
    best_row = None
    for rec in _rows(manager, 'ComplianceRecord'):
        if getattr(rec, 'business_ref', '') != business_name:
            continue
        if getattr(rec, 'requirement_ref', '') != requirement_name:
            continue
        rec_variant = getattr(rec, 'variant', '')
        if rec_variant not in ('', variant):
            continue
        if _level_index(getattr(rec, 'level', 'unassessed')) \
                > _level_index(best):
            best = getattr(rec, 'level', 'unassessed')
            best_row = rec
    return best, best_row


def sellability_report(manager, business_name, variant=''):
    """Per sale context: the requirements that gate it, what has
    been attained, and whether selling IN THAT CONTEXT is allowed
    now. 'general-goods' gates every sale; claim-contexts gate the
    CLAIM (blocked claim != blocked sale as plain goods)."""
    biz = _named(manager, 'BusinessProfile', business_name)
    if biz is None:
        return {'ok': False,
                'refusal': f'no BusinessProfile named '
                           f'"{business_name}"'}
    requirements = _rows(manager, 'ComplianceRequirement')
    if not requirements:
        return {'ok': False,
                'refusal': 'no ComplianceRequirement rows seeded'}
    contexts = {}
    for req in requirements:
        ctx = getattr(req, 'applies_context', 'general-goods')
        level, row = _attained(manager, business_name, variant,
                               getattr(req, 'name', ''))
        needed = getattr(req, 'required_level', 'self-test-pass')
        met = _level_index(level) >= _level_index(needed)
        entry = contexts.setdefault(ctx, {
            'context': ctx, 'requirements': [], 'allowed': True,
            'blockers': []})
        detail = {
            'requirement': getattr(req, 'name', ''),
            'displayName': getattr(req, 'display_name', ''),
            'kind': getattr(req, 'kind', ''),
            'requiredLevel': needed,
            'attainedLevel': level,
            'met': met,
            'evidence': getattr(row, 'evidence_note', '')
            if row else '',
            'reference': getattr(req, 'reference_note', '')}
        entry['requirements'].append(detail)
        if not met and getattr(req, 'kind', '') != \
                'voluntary-standard':
            entry['allowed'] = False
            entry['blockers'].append(
                f'{detail["displayName"]}: attained '
                f'"{level}", needs "{needed}"')
        elif not met:
            entry['blockers'].append(
                f'(claim only) {detail["displayName"]}: '
                f'"{level}" < "{needed}" — the CLAIM stays off '
                'the stall card')
    general = contexts.get('general-goods', {'allowed': False})
    return {'ok': True, 'business': business_name,
            'variant': variant or '(business-wide)',
            'levels': list(COMPLIANCE_LEVELS),
            'contexts': sorted(contexts.values(),
                               key=lambda c: c['context']),
            'canSellPlainGoods': general.get('allowed', False),
            'hardRule': 'NOTHING sells as food-safe without '
                        'certified-third-party-pass — the '
                        'food-contact context enforces it',
            'disclaimer': DISCLAIMER}


def qa_report(manager, business_name, variant=''):
    """QA per check: definition + measured pass rate from the
    records; checks with no records show honestly unmeasured."""
    checks = _rows(manager, 'QualityCheckDefinition')
    if not checks:
        return {'ok': False,
                'refusal': 'no QualityCheckDefinition rows seeded'}
    rows = []
    for check in checks:
        checked = 0
        passed = 0
        runs = 0
        defects = []
        for rec in _rows(manager, 'QualityCheckRecord'):
            if getattr(rec, 'business_ref', '') != business_name:
                continue
            if getattr(rec, 'check_ref', '') != getattr(
                    check, 'name', ''):
                continue
            if variant and getattr(rec, 'variant', '') != variant:
                continue
            checked += getattr(rec, 'units_checked', 0)
            passed += getattr(rec, 'units_passed', 0)
            runs += 1
            note = getattr(rec, 'defects_note', '')
            if note:
                defects.append(note)
        row = {'check': getattr(check, 'name', ''),
               'displayName': getattr(check, 'display_name', ''),
               'method': getattr(check, 'method', ''),
               'acceptance': getattr(check, 'acceptance', ''),
               'frequency': getattr(check, 'frequency', ''),
               'runs': runs, 'unitsChecked': checked}
        if checked:
            row['passRatePct'] = round(100.0 * passed / checked, 1)
            row['defectsSeen'] = defects
        else:
            row['passRatePct'] = None
            row['note'] = 'no runs logged — unmeasured, honestly'
        rows.append(row)
    return {'ok': True, 'business': business_name,
            'variant': variant or '(all variants)',
            'checks': rows,
            'note': 'pass rates derive from QualityCheckRecord '
                    'rows; the leachate-pH check doubles as the '
                    'plant-safe claim evidence'}
