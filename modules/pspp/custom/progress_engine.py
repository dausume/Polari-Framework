"""
@module pspp.custom.progress_engine

ReactionProgressModel v1 — MEASURED CURVES ONLY (plan pspp-8 floor;
invariant I5: no invented kinetics). Supported exactly where the book
measured:

- 80 °C, K-silicate + MK-750 across MR 1.23-2.85: §8.2.8 setting
  classes give completion times (ultra-rapid <1 h; complete at 4 h;
  incomplete/never per class).
- Other cure temperatures ONLY for MR≈1.83: the Fig 8.20 exotherm
  ladder scales time by measured peak-time ratios (marked
  'interpolated', bands honest).

Everything else refuses, naming the dataset that would support it —
a scientist extends the model by ENTERING DATA, not by editing code.
"""

from pspp.custom.dataset_interpolation import read_dataset
from pspp.custom.pspp_views import _datasets

_SETTING = 'mk750-k-silicate-setting-class-vs-mr'
_EXOTHERM = 'k-pss-exotherm-vs-cure-temperature'
_REFERENCE_TEMP_C = 80.0

#: Setting class → (completion hours at 80 °C, honest note).
_CLASS_COMPLETION = {
    1: (1.0, 'ultra rapid — complete before 1 h (§8.2.8)'),
    2: (4.0, 'complete at 4 h (§8.2.8)'),
    3: (None, 'incomplete at 4 h — completion time NOT measured'),
    4: (None, 'does not harden within the experiment timeframe'),
}


def cure_progress(manager, mr, cure_temperature_c=80.0, hours=6.0,
                  steps=24):
    """Reaction-extent-vs-time estimate for a K-silicate + MK-750 mix.
    Returns a claim-shaped payload or an evidence-bearing refusal."""
    datasets = _datasets(manager)
    setting = datasets.get(_SETTING)
    if setting is None:
        return {'ok': False, 'refusal': f'dataset {_SETTING!r} absent',
                'suggestion': 'restore the seed row'}
    match = read_dataset(setting, {'MR': mr})
    if not match.get('ok'):
        return match
    cls = int(match['values'].get('setting_class_code', 0))
    completion, note = _CLASS_COMPLETION.get(cls, (None, 'unknown'))
    assumptions = [f'setting class {cls}: {note}',
                   'progress ramp is a LINEAR placeholder between '
                   'mix and measured completion — the measured '
                   'quantity is the completion time, not the shape']

    if completion is None:
        return {'ok': False,
                'refusal': f'MR={mr} is setting class {cls} — {note}',
                'suggestion': 'the book gives no completion time '
                              'here; enter a measured extent-vs-time '
                              'series as a DigitizedDataset row to '
                              'support this mix',
                'evidence': match['evidence']}

    scale = 1.0
    if abs(cure_temperature_c - _REFERENCE_TEMP_C) > 1e-9:
        if abs(mr - 1.83) > 0.13:
            return {'ok': False,
                    'refusal': f'temperature scaling is measured only '
                               f'near MR=1.83 (Fig 8.20); got '
                               f'MR={mr}, T={cure_temperature_c}',
                    'suggestion': 'cure at 80C (the §8.2.8 reference) '
                                  'or add an exotherm ladder dataset '
                                  'for this MR'}
        exotherm = datasets.get(_EXOTHERM)
        ladder = read_dataset(exotherm,
                              {'cure_temperature_c': cure_temperature_c})
        if not ladder.get('ok'):
            return ladder
        reference = read_dataset(exotherm,
                                 {'cure_temperature_c':
                                  _REFERENCE_TEMP_C})
        if not reference.get('ok'):
            # 80C itself is interpolated between 60 and 85 — honest.
            return reference
        scale = (ladder['values']['peak_time_min']
                 / reference['values']['peak_time_min'])
        assumptions.append(
            f'time scaled x{scale:.2f} by the Fig 8.20 peak-time '
            f'ratio ({cure_temperature_c}C vs {_REFERENCE_TEMP_C}C '
            'reference) — kinetics shape still unmeasured')

    completion_h = completion * scale
    curve = []
    for i in range(steps + 1):
        t = hours * i / steps
        curve.append({'hours': t,
                      'reactionExtent':
                          min(1.0, t / completion_h)
                          if completion_h > 0 else 0.0})
    return {
        'ok': True,
        'MR': mr,
        'cureTemperatureC': cure_temperature_c,
        'completionHours': completion_h,
        'settingClass': cls,
        'curve': curve,
        'assumptions': assumptions,
        'evidence': {'method': 'interpolated' if scale != 1.0
                     else 'literature',
                     'datasets': [_SETTING] +
                     ([_EXOTHERM] if scale != 1.0 else [])},
    }
