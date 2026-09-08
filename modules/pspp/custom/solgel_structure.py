"""
@module pspp.custom.solgel_structure

mtt-2 sg-5: point the gsp structure machinery at SOL-GEL Q
distributions — silica gel IS a corner-sharing tetrahedral network,
so the ensemble sampler and Debye halo apply verbatim (si_al_ratio
None -> pure Si, no charge-balancing cations).

- solgel_stepped_groups — the sol-gel analog of the geopolymer
  stepped mode: stoichiometric inventory (R ratio) + scientist-driven
  step_once sequence under {pH, R} conditions -> Q-motif fractions
  via the SHARED inventory_q_fractions mapper.
- solgel_route_demo — the catalysis fork made visible: canonical
  acid vs base step sequences -> fractions (acid: low/zero Q4, open;
  base: Q4-rich, dense) -> sampled cluster -> simulated halo, plus
  the kinetics-free framework reachability under the route's gates
  (acid reaches ONLY the polymeric gel, base ONLY the colloidal one).

Honesty: the demo step sequences are DEMONSTRATION bookkeeping a
scientist could equally drive by hand — never kinetics, never a
measured trajectory (those await the digitized NMR curves in
pspp.custom.solgel_process). Every payload says so.

@consumers
  - pspp.pspp_api (/api/pspp/solgel/routes)
  - pspp.solgel_structure_selftest
"""

from pspp.custom.network_stepping import reachable_frameworks, step_once
from pspp.reaction_network_basis import (
    SEED_CHEMICAL_SPECIES, SEED_REACTION_RULES,
)
from pspp.custom.solgel_network import (
    SOLGEL_CHEMICAL_SPECIES, SOLGEL_REACTION_RULES,
    SOLGEL_THRESHOLD_WINDOWS, solgel_inventory,
)
from pspp.custom.structure_groups import _ranked_groups, inventory_q_fractions
from pspp.threshold_windows_basis import SEED_THRESHOLD_WINDOWS

_DEMO_NOTE = ('demonstration step sequence — scientist-driven '
              'stoichiometric bookkeeping under the route gates, '
              'never kinetics or a measured trajectory (digitize the '
              '29Si NMR curves to replace it with data)')

#: Canonical route demos: (pH, R, [(rule, times), ...]).
#: Acid: hydrolysis-led, linear/end growth only (crosslink gates
#: closed) -> Q4-free open network. Base: full hydrolysis + gated
#: crosslinking -> Q4-rich dense particles.
ROUTE_DEMOS = {
    'acid': {
        'ph': 2.5, 'r': 2.0,
        'steps': (('alkoxide-hydrolysis', 60),
                  ('alcohol-condensation', 10),
                  ('silicic-dimerization', 20),
                  ('chain-extension-condensation', 10),
                  ('end-crosslinking-condensation', 15)),
        'target_density_g_cm3': None,  # open network — unconstrained
        'story': 'acid catalysis: weakly-branched/linear growth, '
                 'low Q4, spinnable regime',
    },
    'base': {
        'ph': 9.0, 'r': 10.0,
        'steps': (('alkoxide-hydrolysis', 100),
                  ('silicic-dimerization', 50),
                  ('end-crosslinking-condensation', 40),
                  ('crosslink-condensation', 30),
                  ('network-completion-condensation', 25)),
        'target_density_g_cm3': 2.2,  # amorphous-silica-like density
        'story': 'base catalysis: monomer-cluster growth, Q4-rich '
                 'dense colloidal particles',
    },
}


def _combined_rules():
    return list(SEED_REACTION_RULES) + list(SOLGEL_REACTION_RULES)


def _combined_windows():
    return list(SEED_THRESHOLD_WINDOWS) + list(SOLGEL_THRESHOLD_WINDOWS)


def _combined_species():
    return list(SEED_CHEMICAL_SPECIES) + list(SOLGEL_CHEMICAL_SPECIES)


def solgel_stepped_groups(r_ratio, ph, steps=None, alkoxide='teos',
                          amount=100.0, rules=None, windows=None):
    """Q-motif fractions of a sol-gel mix after scientist-driven
    steps ({rule, times?}) under {pH, R} gate conditions."""
    start = solgel_inventory(r_ratio, alkoxide=alkoxide, amount=amount)
    if not start.get('ok'):
        return start
    try:
        ph = float(ph)
    except (TypeError, ValueError):
        return {'ok': False, 'refusal': f'pH {ph!r} is not a number',
                'suggestion': 'the pH condition drives the catalysis '
                              'fork gates — pass it explicitly'}
    inventory = dict(start['inventory'])
    conditions = {'pH': ph, 'R': start['R']}
    assumptions = list(start['assumptions'])
    applied = []
    for index, step in enumerate(steps or []):
        verdict = step_once(
            inventory, step.get('rule', ''),
            rules=rules if rules is not None else _combined_rules(),
            conditions=step.get('conditions', conditions),
            windows=(windows if windows is not None
                     else _combined_windows()),
            cation=None, times=int(step.get('times', 1)))
        if not verdict.get('ok'):
            verdict['stepIndex'] = index
            verdict['applied'] = applied
            return verdict
        inventory = verdict['inventory']
        applied.append({'rule': verdict['rule'],
                        'times': verdict['times']})
        for note in verdict.get('assumptions') or []:
            if note not in assumptions:
                assumptions.append(note)
    mapping = inventory_q_fractions(inventory,
                                    species=_combined_species())
    if not mapping['ok']:
        mapping['mode'] = 'solgel-stepped'
        return mapping
    if mapping['unmappedQuantified']:
        assumptions.append(
            'fractions cover ONLY qn-carrying species — quantified '
            f"but unmapped: {sorted(mapping['unmappedQuantified'])}")
    return {
        'ok': True, 'mode': 'solgel-stepped',
        'alkoxide': start['alkoxide'], 'R': start['R'],
        'pH': conditions['pH'],
        'stepsApplied': applied,
        'groups': _ranked_groups(mapping['fractions']),
        'fractions': {m: round(v, 4)
                      for m, v in mapping['fractions'].items()},
        'unmappedQuantified': mapping['unmappedQuantified'],
        'presentUnquantified': mapping['presentUnquantified'],
        'assumptions': assumptions,
        'evidence': start['evidence'],
    }


def solgel_route_demo(route, n_tetrahedra=80, seed=1,
                      sample=True, halo=True):
    """The catalysis fork end-to-end for one canonical route:
    fractions + framework reachability (+ sampled cluster + Debye
    halo). route: 'acid' | 'base'."""
    demo = ROUTE_DEMOS.get(route)
    if demo is None:
        return {'ok': False,
                'refusal': f'unknown sol-gel route {route!r}',
                'suggestion': f'available: {sorted(ROUTE_DEMOS)} — or '
                              'drive solgel_stepped_groups with your '
                              'own pH/R/steps'}
    groups = solgel_stepped_groups(
        demo['r'], demo['ph'],
        steps=[{'rule': r, 'times': t} for r, t in demo['steps']])
    if not groups.get('ok'):
        return groups
    start = solgel_inventory(demo['r'])
    reachable = reachable_frameworks(
        start['inventory'], rules=_combined_rules(),
        conditions={'pH': demo['ph'], 'R': demo['r']},
        windows=_combined_windows(), species=_combined_species(),
        cation=None)
    payload = {
        'ok': True, 'route': route, 'story': demo['story'],
        'pH': demo['ph'], 'R': demo['r'],
        'groups': groups,
        'reachableFrameworks': reachable.get('reachableFrameworks'),
        'blockedRules': reachable.get('blockedRules'),
        'assumptions': [_DEMO_NOTE] + list(
            groups.get('assumptions') or []),
    }
    if not sample:
        return payload
    from pspp.custom.structure_sampling import build_geopolymer_sample
    cluster = build_geopolymer_sample(
        groups['fractions'], n_tetrahedra=n_tetrahedra, seed=seed,
        si_al_ratio=None,
        target_density_g_cm3=demo['target_density_g_cm3'])
    payload['sample'] = cluster
    if cluster.get('ok'):
        payload['assumptions'].append(
            'pure-silica sampling: si_al_ratio None -> all Si, no '
            'charge-balancing cations')
        if halo:
            from pspp.custom.structure_validation import simulated_halo
            payload['halo'] = simulated_halo(cluster)
    return payload
