"""
@cross-cutting
@module casting.interventions
@tags @xc:bindings

cast-6 (Dustin's original ask): ALTER the fill when it needs help —
positive or negative pressure through a sprue, heat or cold — with
every intervention GATED so it damages neither the mold nor the
cast material, and NOTHING auto-applied (knobs-and-suggestions:
the report says what the knob would do and what the gates say;
turning it is the human's move).

  pressure-positive  compresses trapped air (Boyle, ideal-gas,
                     named) and helps thin channels — gated by the
                     pour-loading wall-bending model at the raised
                     pressure, plus the clamping force it demands.
  pressure-vacuum    pre-fill evacuation eliminates TOPOLOGICAL
                     pockets (unfed chambers stay unfed — vacuum
                     moves air, not slurry) — gated by the same
                     plate model (atmosphere now pushes INWARD) and
                     slurry outgassing (a named absence).
  heat-soak          for geopolymer this is COUNTERPRODUCTIVE and
                     the measured data says so: pot life falls
                     210→45 min from cure 40→85°C — reported as a
                     refutation with the evidence, not a silent
                     apply. Mold softening margin re-gated at the
                     raised temperature.
  chill              extends the geopolymer pot life toward the
                     measured 210 min ceiling; below the 40°C
                     validity floor it refuses to extrapolate.
                     Ceramic molds re-gate on thermal_shock.

FillInterventionDefinition rows seed the four knobs so the
capability is discoverable as data (object-coherence).

@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-6)
"""

from casting.fill_sim import simulate_fill
from casting.pour_loading import (
    EXOTHERM_MEASURED, cure_duration_min, pour_loading_report,
)
from objectTreeDecorators import treeObject, treeObjectInit

INTERVENTION_KINDS = ('pressure-positive', 'pressure-vacuum',
                      'heat-soak', 'chill')
_ATM_KPA = 101.325


class FillInterventionDefinition(treeObject):
    """One available intervention knob — kind, default magnitude,
    where it applies. Evaluation is evaluate_intervention; a row is
    a capability, never an auto-applied action."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 kind: str = 'pressure-positive',
                 # kPa for pressures; Δ°C for heat/chill.
                 default_magnitude: float = 0.0,
                 applied_at: str = 'sprue',
                 is_prior: bool = True, notes: str = '',
                 provenance_id: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.kind = (kind if kind in INTERVENTION_KINDS
                     else 'pressure-positive')
        self.default_magnitude = default_magnitude
        self.applied_at = applied_at
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id


SEED_FILL_INTERVENTIONS = [
    {'name': 'inject-50kpa', 'display_name': 'Inject at 50 kPa',
     'kind': 'pressure-positive', 'default_magnitude': 50.0,
     'applied_at': 'sprue', 'is_prior': True,
     'provenance_id': 'cast-6',
     'notes': 'compresses trapped air ~33% and pushes thin '
              'channels; needs clamping.'},
    {'name': 'vacuum-80kpa', 'display_name': 'Evacuate to −80 kPa',
     'kind': 'pressure-vacuum', 'default_magnitude': 80.0,
     'applied_at': 'vent', 'is_prior': True,
     'provenance_id': 'cast-6',
     'notes': 'pre-fill evacuation — the trapped-pocket killer; '
              'outgassing unmeasured (named).'},
    {'name': 'warm-cure-60', 'display_name': 'Warm cure (+20°C)',
     'kind': 'heat-soak', 'default_magnitude': 20.0,
     'applied_at': 'mold-wall', 'is_prior': True,
     'provenance_id': 'cast-6',
     'notes': 'faster cure — but the measured exotherm says it '
              'costs pot life AND peaks hotter; the gates decide.'},
    {'name': 'chill-cure-40', 'display_name': 'Chill toward 40°C',
     'kind': 'chill', 'default_magnitude': 20.0,
     'applied_at': 'mold-wall', 'is_prior': True,
     'provenance_id': 'cast-6',
     'notes': 'longest measured pot life (210 min) and the lowest '
              'exotherm peak (70°C) — the wax-mold-friendly cure.'},
]


def evaluate_intervention(manager, mold_name, kind, magnitude,
                          feedstock_name=None,
                          cast_material='geopolymer-slurry',
                          cure_temp_c=40.0):
    """What would this intervention DO, and do the gates allow it?
    Returns effect + gates + verdict; applies nothing."""
    if kind not in INTERVENTION_KINDS:
        return {'ok': False,
                'error': f"unknown intervention '{kind}' — know: "
                         f'{INTERVENTION_KINDS}'}
    base = simulate_fill(manager, mold_name,
                         cast_material=cast_material)
    if not base.get('ok'):
        return base
    gates, findings, effect = [], [], {}

    if kind == 'pressure-positive':
        m = float(magnitude)
        pockets = base.get('trappedPockets', [])
        cell = base['grids']['domain'].cell_volume
        compressed = [round(p * cell * _ATM_KPA / (_ATM_KPA + m), 3)
                      for p in pockets]
        effect = {'trappedPocketsCm3':
                  [round(p * cell, 3) for p in pockets],
                  'compressedToCm3': compressed,
                  'model': 'ideal-gas isothermal compression '
                           '(Boyle) — NAMED; pockets shrink, they '
                           'do not vanish'}
        loading = pour_loading_report(
            manager, mold_name, feedstock_name=feedstock_name,
            cast_material=cast_material, inject_pressure_kpa=m,
            cure_temp_c=cure_temp_c)
        gates.append({'gate': 'mold wall bending at the raised '
                              'pressure',
                      'ok': loading.get('verdict') == 'feasible',
                      'evidence': (loading.get('wallBending') or {})})
        up = loading.get('uplift') or {}
        if up:
            findings.append(f"clamping ≥ {up.get('forceN')} N "
                            f'required (cope lift)')
    elif kind == 'pressure-vacuum':
        m = float(magnitude)
        effect = {'trappedPocketsEliminated':
                  len(base.get('trappedPockets', [])),
                  'unfedRegionsRemaining':
                  len(base.get('unfedRegions', [])),
                  'model': 'pre-fill evacuation removes the AIR — '
                           'topological pockets fill; UNFED '
                           'chambers stay unfed (vacuum moves air, '
                           'not slurry)'}
        loading = pour_loading_report(
            manager, mold_name, feedstock_name=feedstock_name,
            cast_material=cast_material, inject_pressure_kpa=m)
        gates.append({'gate': 'wall bending under the pressure '
                              'differential (atmosphere pushes '
                              'INWARD on an evacuated mold — same '
                              'plate model, conservative)',
                      'ok': loading.get('verdict') == 'feasible',
                      'evidence': (loading.get('wallBending') or {})})
        gates.append({'gate': 'slurry outgassing under vacuum',
                      'ok': None,
                      'evidence': 'NAMED ABSENCE — unmeasured; a '
                                  'frothing mix ruins the surface. '
                                  'Bench-test the mix at this '
                                  'vacuum first.'})
    elif kind in ('heat-soak', 'chill'):
        delta = float(magnitude) * (1.0 if kind == 'heat-soak'
                                    else -1.0)
        new_cure = cure_temp_c + delta
        lo, hi = EXOTHERM_MEASURED[0][0], EXOTHERM_MEASURED[-1][0]
        if not lo <= new_cure <= hi:
            return {'ok': False,
                    'refusal': f'adjusted cure {new_cure:.0f}°C is '
                               f'outside the measured {lo:.0f}–'
                               f'{hi:.0f}°C validity — refusing to '
                               f'extrapolate the exotherm'}
        old_life = cure_duration_min(cure_temp_c)
        new_life = cure_duration_min(new_cure)
        effect = {'cureTempC': new_cure,
                  'potLifeMinBefore': old_life,
                  'potLifeMinAfter': new_life,
                  'basis': 'measured pspp exotherm times '
                           '(210/90/45 min at 40/60/85°C)'}
        if kind == 'heat-soak' and new_life < old_life:
            findings.append(
                f'COUNTERPRODUCTIVE for the fill window: heating to '
                f'{new_cure:.0f}°C cuts pot life '
                f'{old_life:.0f}→{new_life:.0f} min AND raises the '
                f'exotherm peak — the measured data refutes the '
                f'intent')
        loading = pour_loading_report(
            manager, mold_name, feedstock_name=feedstock_name,
            cast_material=cast_material, cure_temp_c=new_cure)
        exo = loading.get('exotherm') or {}
        gates.append({'gate': 'mold softening vs the exotherm peak '
                              'at the adjusted cure',
                      'ok': exo.get('ok'),
                      'evidence': exo})
        if kind == 'chill':
            gates.append({'gate': 'thermal shock on ceramic molds',
                          'ok': None,
                          'evidence': 'applies when the mold is a '
                                      'fired ceramic (chain stage '
                                      '2+) — CeramicSample.'
                                      'thermal_shock rates it; a '
                                      'wax mold just hardens'})

    blocked = any(g['ok'] is False for g in gates)
    return {'ok': True, 'mold': mold_name, 'kind': kind,
            'magnitude': magnitude, 'effect': effect,
            'gates': gates, 'findings': findings,
            'verdict': 'blocked' if blocked else 'allowed',
            'note': 'evaluated, NEVER auto-applied — a gate with '
                    'ok=None is a named absence to measure, not a '
                    'pass'}
