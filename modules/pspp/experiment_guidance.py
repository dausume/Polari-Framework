"""
@module pspp.experiment_guidance

ONE payload that walks a bench scientist through a geopolymer (or any
loaded-library) experiment — the synthesis layer over everything the
engines already refuse and grade honestly:

1. composition — derived oxide ratios graded through the MERGED
   windows (banded p.193 crack thresholds beat the binary patent
   claims), each verdict carrying its physical behavior note.
2. pathways — which reaction routes the mix OPENS (kinetics-free
   reachability: frameworks, rule chains, hypothesis floors,
   competing branches) and which stay blocked and why.
3. cure — the measured cure schedule (progress_engine v1) or the
   refusal that names the dataset a measurement would fill.
4. gaps — every refusal collected as a NEXT-DATA ask: guidance is
   'here is exactly what to measure/enter', never a guess. Absence
   is honest data; the gap list IS the experiment plan.

Every section is independent: a scientist with only a composition
still gets grading; one with only MR still gets pathways + cure.

@consumers
  - pspp.pspp_api (POST /api/pspp/guide)
"""

from pspp.composition_math import oxide_ratios, ratios_from_moles
from pspp.network_stepping import (
    reachable_frameworks, solution_inventory,
)
from pspp.progress_engine import cure_progress
from pspp.threshold_windows import grade_composition_merged


def _gap(section, refusal):
    return {'section': section,
            'refusal': refusal.get('refusal', ''),
            'nextData': refusal.get('suggestion', '')}


def experiment_guide(manager, composition=None, basis='mass',
                     family='', cation='', mr=None,
                     cure_temperature_c=80.0, site=None,
                     windows=None, banded_windows=None, rules=None):
    """The guidance payload. Provide what you know; every absent
    input produces a section-level gap, never a silent skip."""
    sections = {}
    gaps = []

    # 1. composition grading through the merged windows.
    if composition:
        derive = oxide_ratios if basis == 'mass' else ratios_from_moles
        try:
            ratios = derive({k: float(v)
                             for k, v in composition.items()})
        except (TypeError, ValueError):
            ratios = {'ok': False,
                      'refusal': 'composition must be '
                                 '{oxide: number}',
                      'suggestion': "e.g. {'SiO2': 55, 'Al2O3': 25}"}
        if ratios.get('ok'):
            from pspp.pspp_views import _seed_or_rows
            from pspp.reaction_windows import SEED_REACTION_WINDOWS
            from pspp.threshold_windows import SEED_THRESHOLD_WINDOWS
            symmetric = windows if windows is not None else \
                _seed_or_rows(manager, 'ReactionWindow',
                              SEED_REACTION_WINDOWS)
            banded = banded_windows if banded_windows is not None \
                else _seed_or_rows(manager, 'ThresholdReactionWindow',
                                   SEED_THRESHOLD_WINDOWS)
            if family:
                grading = grade_composition_merged(
                    symmetric, banded, ratios['ratios'], family)
            else:
                grading = {'ok': False,
                           'refusal': 'no material_family selected',
                           'suggestion': 'windows never transfer '
                                         'between families — name '
                                         'the family the mix targets'}
            sections['composition'] = {
                'ratios': ratios['ratios'],
                'grading': grading,
            }
            if not grading.get('ok'):
                gaps.append(_gap('composition', grading))
        else:
            sections['composition'] = ratios
            gaps.append(_gap('composition', ratios))
    else:
        gaps.append(_gap('composition', {
            'refusal': 'no composition provided',
            'suggestion': 'enter the mix as {oxide: amount} (mass or '
                          'moles) to grade it against the cited '
                          'windows'}))

    # 2. open pathways from the measured Q inventory.
    if cation and mr is not None:
        from pspp.pspp_views import _datasets
        inventory = solution_inventory(cation, mr,
                                       datasets=_datasets(manager))
        if inventory.get('ok'):
            from pspp.pspp_views import _seed_or_rows
            from pspp.reaction_network import SEED_REACTION_RULES
            from pspp.threshold_windows import SEED_THRESHOLD_WINDOWS
            reach = reachable_frameworks(
                inventory['inventory'],
                rules=rules if rules is not None else _seed_or_rows(
                    manager, 'ReactionRule', SEED_REACTION_RULES),
                site=site, conditions={'MR': mr},
                windows=banded_windows if banded_windows is not None
                else _seed_or_rows(manager, 'ThresholdReactionWindow',
                                   SEED_THRESHOLD_WINDOWS),
                cation=cation)
            sections['pathways'] = {
                'inventory': inventory['inventory'],
                'inventoryAssumptions': inventory['assumptions'],
                'reachableFrameworks': reach['reachableFrameworks'],
                'blockedRules': reach['blockedRules'],
                'assumptions': reach['assumptions'],
            }
        else:
            sections['pathways'] = inventory
            gaps.append(_gap('pathways', inventory))
    else:
        gaps.append(_gap('pathways', {
            'refusal': 'cation and/or MR not provided',
            'suggestion': 'pass cation (Na|K) + the silicate MR to '
                          'see which reaction routes the mix opens '
                          '(Table 5.6 listed MRs)'}))

    # 3. the measured cure schedule.
    if mr is not None:
        cure = cure_progress(manager, mr,
                             cure_temperature_c=cure_temperature_c)
        sections['cure'] = cure
        if not cure.get('ok'):
            gaps.append(_gap('cure', cure))
    else:
        gaps.append(_gap('cure', {
            'refusal': 'MR not provided',
            'suggestion': 'the measured setting classes key on MR '
                          '(§8.2.8) — pass it for a cure schedule'}))

    return {
        'ok': True,
        'sections': sections,
        'gaps': gaps,
        'note': 'each gap names exactly the measurement or dataset '
                'that would close it — the gap list is the '
                'experiment plan, never a guess',
    }
