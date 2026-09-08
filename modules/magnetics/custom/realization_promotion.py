"""
@module magnetics.custom.realization_promotion

mag-12: MEASURED EVIDENCE MEETS THE REALIZATION LADDER — as a
SUGGESTION, never a mutation.

The gap this closes: MagneticMaterialOption rows carry a
realization_level that gates costing and business use, and the whole
stack records measurement (MotorVerificationRun rows, bizops
QualityCheckRecord rows against qa-wound-core-inductance and
qa-magnet-remanence). Nothing joined them. Somebody could run fifty
measured batches and the catalog would still say recipe-seeded,
because promotion was a hand edit nobody was prompted to make.

This module reads the evidence and says what it WOULD support. It
never writes. Promotion stays a human act for the same reason
OrganMeshChoice and material readiness do: "we have measured this"
is a claim a person puts their name to, and a rule that promotes
silently would let a mis-tagged QA row quietly open the business
gate.

THE RULES, stated here and repeated in every payload:

  theoretical -> literature-demonstrated
      at least one property whose provenance cites literature
      (provenance tag containing "literature"). A row whose numbers
      are all 'theoretical' has nothing published behind it.

  literature-demonstrated -> recipe-seeded
      a seeded ProductFormula for the option's item_ref — the same
      test gates_for() already uses for costing. A recipe is what
      makes the material a thing you could make rather than read
      about.

  recipe-seeded -> made-and-measured
      at least one MEASURED record bearing on THIS option. Two
      strengths, and they are NOT treated as equal:
        DIRECT      a QualityCheckRecord against a magnetic QA check
                    (qa-wound-core-inductance measures mu_r_eff,
                    qa-magnet-remanence measures b_r_t) that names
                    this option. It measures a claimed PROPERTY.
        SYSTEM      a MotorVerificationRun with kind='measured' on a
                    design whose material slots name this option. It
                    demonstrates the material worked in a machine,
                    but measures the MACHINE, not the property.
      Direct evidence alone earns the suggestion. System evidence
      alone is reported as CORROBORATION and explicitly does not:
      a clock that keeps time tells you the rotor was magnetic
      enough, not that its B_r is what the row claims.

  BOUGHT COMMODITIES are the one genuine ambiguity in this ladder,
  and it is REPORTED rather than resolved. A cited, purchasable
  part with vendor-specified properties (copper magnet wire) was
  measured by somebody — just not by us — and demanding our own
  bench test of a spool of Essex wire would be theatre. But
  made-and-measured gates BUSINESS use of what WE make, so being
  purchasable must not unlock it either. Such rows are therefore
  flagged VENDOR-ATTESTED, which does NOT raise the supported
  level; the note explains the basis and a human decides. This is
  the one place the tool declines to have an opinion, on purpose.

  reference-only options are never promoted at all. NdFeB and
  electrical steel are priced-for-honesty comparators; measuring
  someone else's commercial part says nothing about our route.

Simulation rows never count anywhere: kind='sim-quasi-static' is
provenance, not proof — the same rule motor_verify already applies.

AND OUR OWN BLIND SPOT MAY NOT CONDEMN A ROW. When the table
holding direct evidence is absent (bizops gated off), a row
claiming made-and-measured is reported UNJUDGEABLE-HERE, never as
over-claiming: we cannot see the evidence, which is not the same as
there being none. This is the mag-9 winding rule applied again —
a stand-in for missing information must not be used as a verdict.

Evidence tables are read at DATA level (manager.objectTables), the
way bizops reads magnetics: this module must work when motors or
bizops are gated off, and say so rather than failing to import.

@consumers magnetics.magnet_api, magnetics.magnetics_selftest
"""

import json

from magnetics.custom.magnet_analysis import (
    buyable_cited, _named, _rows, recipe_seeded,
)
from magnetics.magnet_basis import REALIZATION_LEVELS

#: QA check -> the property that check actually measures. A record
#: against a check NOT in this map is not magnetic evidence, however
#: measured it is: a dimensional-fit pass says nothing about mu.
MAGNETIC_QA_CHECKS = {
    'qa-wound-core-inductance': 'mu_r_eff',
    'qa-magnet-remanence': 'b_r_t',
}

#: The material slots a motor design names. Read as data — the
#: motors module owns these keys, and duplicating the NAMES here is
#: cheaper and safer than importing a module that may be gated off.
DESIGN_MATERIAL_SLOTS = ('rotor_material', 'stator_material',
                         'winding_material')

RULES_NOTE = (
    'theoretical -> literature-demonstrated needs a literature '
    'provenance on some property; -> recipe-seeded needs a seeded '
    'ProductFormula for the item_ref; -> made-and-measured needs '
    'DIRECT measurement of a claimed property (a magnetic QA record '
    'naming this option). A measured MOTOR run is SYSTEM-level '
    'corroboration and does not earn the top rung on its own — a '
    'clock that keeps time proves the rotor was magnetic enough, '
    'not that its B_r is what the row claims. Simulation rows never '
    'count.')


def _loads(row, attr, default):
    try:
        return json.loads(getattr(row, attr, '') or '')
    except (TypeError, ValueError):
        return default


def _table_present(manager, class_name):
    return class_name in (getattr(manager, 'objectTables', None)
                          or {})


def _has_literature_property(option):
    """Any property whose provenance cites literature."""
    props = _loads(option, 'properties_json', {})
    if not isinstance(props, dict):
        return False, []
    hits = [name for name, entry in props.items()
            if isinstance(entry, dict)
            and 'literature' in str(entry.get('provenance', '')
                                    ).lower()]
    return bool(hits), sorted(hits)


def _designs_using(manager, option_name):
    """Motor designs whose material slots name this option, with
    the slot that named it — read at DATA level."""
    out = []
    for design in _rows(manager, 'MotorDesignDefinition'):
        params = _loads(design, 'params_json', {})
        if not isinstance(params, dict):
            continue
        slots = [s for s in DESIGN_MATERIAL_SLOTS
                 if params.get(s) == option_name]
        if slots:
            out.append((getattr(design, 'name', ''), slots))
    return out


def _system_evidence(manager, option_name):
    """MEASURED motor runs on designs using this option. Corroborates
    the material worked; does not measure a property."""
    designs = dict(_designs_using(manager, option_name))
    if not designs:
        return []
    out = []
    for run in _rows(manager, 'MotorVerificationRun'):
        if getattr(run, 'kind', '') != 'measured':
            continue          # sim rows are provenance, not proof
        design_ref = getattr(run, 'design_ref', '')
        if design_ref not in designs:
            continue
        out.append({
            'kind': 'system',
            'row': getattr(run, 'name', ''),
            'source': 'MotorVerificationRun',
            'design': design_ref,
            'slots': designs[design_ref],
            'stepsTaken': getattr(run, 'steps_taken', None),
            'stepsCommanded': getattr(run, 'steps_commanded', None),
            'clockErrorS': getattr(run, 'clock_error_s', None),
            'measures': 'the MACHINE (steps kept vs time), not this '
                        'material\'s claimed property',
        })
    return out


def _names_option(record, option_name):
    """Does this QA record actually name the option?

    THE HONEST LIMIT (and the one real ambiguity in this module):
    QualityCheckRecord ties to a product VARIANT, and the
    variant -> material mapping lives in bizops PRESTAGE_VARIANTS,
    which is code, not rows — unreadable from here without importing
    a module that may be gated off. So the link must be EXPLICIT
    text: the record's variant, batch note or notes must name the
    option. Anything looser would credit evidence to a material
    nobody claimed it for, which is worse than reporting a gap."""
    for attr in ('variant', 'batch_note', 'notes'):
        if option_name in (getattr(record, attr, '') or ''):
            return True, attr
    return False, ''


def _direct_evidence(manager, option_name):
    """QA records against a magnetic check that NAME this option."""
    out = []
    for rec in _rows(manager, 'QualityCheckRecord'):
        check_ref = getattr(rec, 'check_ref', '')
        prop = MAGNETIC_QA_CHECKS.get(check_ref)
        if prop is None:
            continue          # not a magnetic measurement
        named, via = _names_option(rec, option_name)
        if not named:
            continue
        checked = getattr(rec, 'units_checked', 0) or 0
        passed = getattr(rec, 'units_passed', 0) or 0
        out.append({
            'kind': 'direct',
            'row': getattr(rec, 'name', ''),
            'source': 'QualityCheckRecord',
            'check': check_ref,
            'measuresProperty': prop,
            'unitsChecked': checked,
            'unitsPassed': passed,
            'linkedVia': via,
            'measures': f'{prop} directly, by the method on '
                        f'"{check_ref}"',
        })
    return out


def _next_level(level):
    try:
        idx = REALIZATION_LEVELS.index(level)
    except ValueError:
        return REALIZATION_LEVELS[0]
    if idx + 1 >= len(REALIZATION_LEVELS):
        return None
    return REALIZATION_LEVELS[idx + 1]


def _supported_level(manager, option, direct, system):
    """The HIGHEST level the evidence supports, and why each rung
    was or was not reached. Independent of what the row claims —
    that comparison is the caller's."""
    reasons = {}
    lit, lit_props = _has_literature_property(option)
    reasons['literature-demonstrated'] = (
        f'literature provenance on {lit_props}' if lit else
        'no property carries a literature provenance')
    item = getattr(option, 'item_ref', '')
    recipe = recipe_seeded(manager, item)
    reasons['recipe-seeded'] = (
        f'ProductFormula seeded for "{item}"' if recipe else
        (f'no ProductFormula for "{item}"' if item else
         'no item_ref, so no recipe can be found'))
    # A bought, cited part with vendor-specified numbers is
    # made-and-measured on the MANUFACTURER's bench. Recorded as a
    # distinct basis so it is never mistaken for our own evidence.
    props = _loads(option, 'properties_json', {})
    vendor_props = sorted(
        name for name, entry in (props or {}).items()
        if isinstance(entry, dict)
        and 'vendor' in str(entry.get('provenance', '')).lower())
    vendor_attested = bool(vendor_props) and buyable_cited(
        manager, getattr(option, 'item_ref', ''))
    reasons['made-and-measured'] = (
        f'{len(direct)} direct property measurement(s)' if direct
        else (f'VENDOR-ATTESTED: bought part, cited price, vendor '
              f'provenance on {vendor_props} — measured by its '
              f'manufacturer, not by us' if vendor_attested
              else ('measured motor run(s) exist but are '
                    'SYSTEM-level only — they corroborate, they do '
                    'not measure a claimed property' if system else
                    'no measured record names this option')))

    supported = 'theoretical'
    if lit:
        supported = 'literature-demonstrated'
    # A recipe is only meaningful once something is published behind
    # the numbers; without literature the row is still theoretical
    # with a recipe attached, and the report says which is missing.
    if lit and recipe:
        supported = 'recipe-seeded'
    # NOTE vendor_attested does NOT raise the supported level.
    # made-and-measured gates BUSINESS use of what WE make, and
    # being able to buy a thing is not evidence that we made and
    # measured it. Copper wire's made-and-measured tag rests on
    # that different basis; the report says so and leaves the call
    # to a human rather than quietly ratifying OR condemning it.
    if lit and recipe and direct:
        supported = 'made-and-measured'
    return supported, reasons, vendor_attested


def promotion_report(manager, option_name=None):
    """What the measured evidence would support for one option, or
    for the whole catalog. Reads only; suggests only."""
    if option_name:
        option = _named(manager, 'MagneticMaterialOption',
                        option_name)
        if option is None:
            return {'ok': False,
                    'refusal': f'no MagneticMaterialOption named '
                               f'"{option_name}"'}
        options = [option]
    else:
        options = _rows(manager, 'MagneticMaterialOption')

    # Honest absence: the evidence lives in other modules' tables.
    missing = []
    if not _table_present(manager, 'MotorVerificationRun'):
        missing.append(
            'MotorVerificationRun absent — the motors module is not '
            'enabled, so system-level corroboration cannot be seen '
            'from here (this is a blind spot, not an absence of '
            'evidence)')
    if not _table_present(manager, 'QualityCheckRecord'):
        missing.append(
            'QualityCheckRecord absent — the bizops module is not '
            'enabled, so DIRECT property measurements cannot be '
            'seen from here; no option can be shown as earning '
            'made-and-measured while this is true')

    entries, suggestions = [], []
    for option in sorted(options, key=lambda o: getattr(o, 'name',
                                                        '')):
        name = getattr(option, 'name', '')
        current = getattr(option, 'realization_level', 'theoretical')
        ref_only = bool(getattr(option, 'is_reference_only', False))
        direct = _direct_evidence(manager, name)
        system = _system_evidence(manager, name)
        supported, reasons, vendor_attested = _supported_level(
            manager, option, direct, system)
        nxt = _next_level(current)

        try:
            gap = (REALIZATION_LEVELS.index(supported)
                   - REALIZATION_LEVELS.index(current))
        except ValueError:
            gap = 0

        entry = {
            'option': name,
            'displayName': getattr(option, 'display_name', ''),
            'currentLevel': current,
            'supportedLevel': supported,
            'referenceOnly': ref_only,
            'directEvidence': direct,
            'systemEvidence': system,
            'evidenceCount': {'direct': len(direct),
                              'system': len(system)},
            'vendorAttested': vendor_attested,
            'rungReasons': reasons,
            'nextLevel': nxt,
            'missingForNextLevel': (reasons.get(nxt)
                                    if nxt else
                                    'already at the top of the '
                                    'ladder'),
        }

        if vendor_attested:
            entry['vendorNote'] = (
                f'"{name}" is a BOUGHT part with a cited price and '
                f'vendor-specified properties: measured by its '
                f'manufacturer, not by us. That is a different '
                f'basis from our bench evidence, and it does NOT '
                f'raise the supported level here — made-and-'
                f'measured gates business use of what WE make. A '
                f'human decides whether the vendor\'s word is the '
                f'right basis for this row.')
        if ref_only:
            entry['verdict'] = 'never-promoted'
            entry['note'] = (
                'reference-only: a priced-for-honesty comparator. '
                'Measuring someone else\'s commercial part says '
                'nothing about OUR route, so no evidence promotes '
                'it.')
        elif gap > 0:
            entry['verdict'] = 'promotion-suggested'
            suggestion = {
                'evidence': (
                    f'{len(direct)} direct + {len(system)} system '
                    f'record(s); {reasons.get(supported, "")}'),
                'knob': 'MagneticMaterialOption.realization_level',
                'action': (f'a human may raise "{name}" from '
                           f'{current} to {supported} — check the '
                           f'evidence rows below first; this tool '
                           f'never writes it'),
            }
            entry['suggestion'] = suggestion
            suggestions.append({'option': name,
                                'from': current, 'to': supported,
                                **suggestion})
        elif gap < 0 and not _table_present(manager,
                                            'QualityCheckRecord'):
            # OUR blind spot, not their over-claim (the mag-9 rule).
            entry['verdict'] = 'unjudgeable-here'
            entry['note'] = (
                f'"{name}" claims {current}; the table holding '
                f'DIRECT measurements (QualityCheckRecord) is not '
                f'loaded, so this report cannot see the evidence. '
                f'Not seeing evidence is not the same as there '
                f'being none — enable bizops and ask again.')
        elif gap < 0:
            entry['verdict'] = 'claims-more-than-evidence'
            entry['suggestion'] = {
                'evidence': f'row claims {current}; evidence '
                            f'supports only {supported} '
                            f'({reasons.get(current, "")})',
                'knob': 'MagneticMaterialOption.realization_level',
                'action': (f'either add the missing evidence for '
                           f'"{name}" or lower the claim — a level '
                           f'nothing backs is the one failure this '
                           f'ladder exists to prevent'),
            }
            suggestions.append({'option': name, 'from': current,
                                'to': supported,
                                **entry['suggestion']})
        else:
            entry['verdict'] = 'level-matches-evidence'
        entries.append(entry)

    out = {
        'ok': True,
        'options': entries,
        'count': len(entries),
        'suggestions': suggestions,
        'suggestionCount': len(suggestions),
        'rules': RULES_NOTE,
        'blindSpots': missing,
        'honesty': 'this report NEVER mutates a row. Promotion is a '
                   'human act for the same reason material '
                   'readiness is: "we have measured this" is a '
                   'claim somebody puts their name to, and a rule '
                   'that promoted silently would let one '
                   'mis-tagged QA row open the business gate.',
    }
    if option_name:
        out['option'] = option_name
    return out
