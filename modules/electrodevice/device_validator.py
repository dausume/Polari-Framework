"""
@module electrodevice.device_validator

THE STANDARDS JUDGE (Dustin 2026-07-10): establishes whether the
simulations behind a component meet the standards to be considered a
VALID SEMICONDUCTOR DEVICE. Derivations never self-bless — this
module is the separate, evidence-bearing gate.

Criteria (each finding: criterion, pass|warn|fail, evidence,
suggestion when actionable):

  semiconductor profiles —
    gap-positive        gap > 0.1 eV (else metallic/degenerate)
    gap-window          0.1..8 eV plausible semiconductor window
                        (fragment/KS caveats make edges a warn)
    carrier-consistent  DERIVED carrier type matches the CLAIMED
                        variant (p/n/intrinsic)
    provenance-complete every number traces to an executed sim
    honesty-recorded    the sims' validity/caveat notes are stored

  transistor devices —
    profile-valid       its SemiconductorProfile passes above
    params-derived      VTO/KP/Ron/Roff derived, never hand-set
    onoff-ratio         Ron/Roff separation >= 1e3 (digital switch
                        standard)
    drive-capability    on-state supports the LED-class load at VDD
    dielectric-sourced  gate epsilon_r from a material row (warn on
                        literature fallback — the data gap is named)

Verdict: not-valid on any fail; conditionally-valid when passes carry
warns; valid-semiconductor-device when all pass clean. Reports are
rows (DeviceValidationReport) — object coherence.

@consumers
  - electrodevice.device_api ({action: validate})
  - electrodevice.selftest_electrodevice
"""

import json
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit


class DeviceValidationReport(treeObject):
    """One validation run — findings + verdict as a row."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        subject: str = '',
        subject_kind: str = '',
        findings_json: str = '[]',
        verdict: str = '',
        validated_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.subject = subject
        self.subject_kind = subject_kind
        self.findings_json = findings_json
        self.verdict = verdict
        self.validated_at = validated_at
        self.notes = notes


def _finding(criterion, status, evidence, suggestion=None):
    out = {'criterion': criterion, 'status': status,
           'evidence': evidence}
    if suggestion:
        out['suggestion'] = suggestion
    return out


def _verdict(findings):
    statuses = [f['status'] for f in findings]
    if 'fail' in statuses:
        return 'not-valid'
    if 'warn' in statuses:
        return 'conditionally-valid'
    return 'valid-semiconductor-device'


def validate_profile(profile):
    """Judge one SemiconductorProfile's findings."""
    findings = []
    prov = json.loads(getattr(profile, 'provenance_json', '{}')
                      or '{}')
    if not getattr(profile, 'derived_at', ''):
        findings.append(_finding(
            'provenance-complete', 'fail',
            'never derived — no executed sim behind the numbers',
            {'knob': f'/api/electrodevice/semiconductors/'
                     f'{profile.name}',
             'how': 'POST {"action": "derive"}'}))
        return findings
    gap = float(getattr(profile, 'gap_ev', 0.0))
    if gap <= 0.1:
        findings.append(_finding(
            'gap-positive', 'fail',
            f'gap {gap:.3f} eV — metallic/degenerate, not a '
            'semiconductor',
            {'knob': 'sim_model', 'how': 'use a semiconducting '
             'fragment/chirality variant'}))
    else:
        findings.append(_finding('gap-positive', 'pass',
                                 f'gap {gap:.3f} eV > 0.1 eV'))
        if gap > 8.0:
            findings.append(_finding(
                'gap-window', 'warn',
                f'gap {gap:.3f} eV above the 8 eV window — '
                'insulator-like; small fragments overestimate',
                {'knob': 'sim_model',
                 'how': 'larger fragment / periodic model to '
                        'approach the bulk gap'}))
        else:
            findings.append(_finding(
                'gap-window', 'pass',
                f'gap {gap:.3f} eV within 0.1-8 eV'))
    claimed = getattr(profile, 'variant', 'intrinsic')
    derived = getattr(profile, 'carrier_type', '')
    if claimed == derived:
        findings.append(_finding(
            'carrier-consistent', 'pass',
            f'claimed "{claimed}" matches the derived frontier-shift '
            f'classification (shift {profile.level_shift_ev:+.3f} '
            'eV)'))
    else:
        findings.append(_finding(
            'carrier-consistent', 'fail',
            f'claimed "{claimed}" but the frontier shifts classify '
            f'"{derived}"',
            {'knob': 'variant OR sim_model',
             'how': 'fix the claim, or use the dopant fragment that '
                    'actually produces those states'}))
    if prov.get('simModel') and prov.get('engine'):
        findings.append(_finding(
            'provenance-complete', 'pass',
            f'{prov["simModel"]} via {prov["engine"]}'))
    else:
        findings.append(_finding(
            'provenance-complete', 'fail',
            'provenance missing the executed model/engine'))
    if prov.get('honesty') and prov.get('fragmentCaveat'):
        findings.append(_finding(
            'honesty-recorded', 'pass',
            'KS-orbital + fragment caveats stored with the data'))
    else:
        findings.append(_finding(
            'honesty-recorded', 'warn',
            'validity caveats not recorded alongside the numbers'))
    return findings


def validate_transistor(manager, device):
    """Judge one transistor device (its profile included)."""
    from electrodevice.semiconductor import get_profile
    findings = []
    profile = get_profile(manager,
                          getattr(device, 'semiconductor_profile',
                                  ''))
    if profile is None:
        findings.append(_finding(
            'profile-valid', 'fail',
            f'no SemiconductorProfile '
            f'"{device.semiconductor_profile}"'))
    else:
        sub = validate_profile(profile)
        worst = ('fail' if any(f['status'] == 'fail' for f in sub)
                 else 'warn' if any(f['status'] == 'warn'
                                    for f in sub) else 'pass')
        findings.append(_finding(
            'profile-valid', worst,
            f'profile "{profile.name}" -> {_verdict(sub)}',
            None if worst == 'pass' else
            {'knob': f'/api/electrodevice/semiconductors/'
                     f'{profile.name}',
             'how': 'POST {"action": "validate"} for the detailed '
                    'findings'}))
    if not getattr(device, 'derived_at', ''):
        findings.append(_finding(
            'params-derived', 'fail', 'never derived',
            {'knob': f'/api/electrodevice/devices/{device.name}',
             'how': 'POST {"action": "derive"}'}))
        return findings
    findings.append(_finding(
        'params-derived', 'pass',
        f'VTO {device.threshold_v:+.3f} V, Ron '
        f'{device.r_on_ohm:.4g} ohm, Roff {device.r_off_ohm:.4g} '
        'ohm from executed sims'))
    ron = float(getattr(device, 'r_on_ohm', 0.0) or 0.0)
    roff = float(getattr(device, 'r_off_ohm', 0.0) or 0.0)
    ratio = (roff / ron) if ron > 0 else 0.0
    if ratio >= 1e3:
        findings.append(_finding(
            'onoff-ratio', 'pass',
            f'Ron/Roff separation {ratio:.3g} >= 1e3'))
    else:
        findings.append(_finding(
            'onoff-ratio', 'fail',
            f'on/off separation {ratio:.3g} < 1e3 — not a usable '
            'digital switch',
            {'knob': 'channel sim volumeFraction (on) / matrix '
                     'conductivity (off)',
             'how': 'raise the on-state network or lower matrix '
                    'leakage; re-derive'}))
    if 0 < ron <= 2000:
        findings.append(_finding(
            'drive-capability', 'pass',
            f'Ron {ron:.4g} ohm can source mA-class LED load at '
            '3.3 V'))
    else:
        findings.append(_finding(
            'drive-capability', 'fail' if ron > 0 else 'fail',
            f'Ron {ron:.4g} ohm too high for the LED-class load',
            {'knob': 'geometry (length_m / cross_section_m2)',
             'how': 'shorter/wider channel; re-derive'}))
    prov = json.loads(getattr(device, 'provenance_json', '{}')
                      or '{}')
    dielectric = prov.get('dielectric', {})
    eps_src = dielectric.get('source', '')
    context = dielectric.get('measurementContext') or {}
    if eps_src == 'material-row':
        detail = (f"eps_r {dielectric.get('epsilonR')} @ "
                  f"{context.get('frequency_hz', '?')} Hz, "
                  f"{context.get('temperature_c', '?')} C, method "
                  f"{context.get('measurement_method', '?')}, "
                  f"confidence {context.get('confidence', '?')}")
        if context.get('confidence') == 'low':
            findings.append(_finding(
                'dielectric-sourced', 'warn',
                f'material row present but LOW confidence — {detail}',
                {'knob': 'the material property row',
                 'how': 'a direct measurement or a higher-confidence '
                        'source'}))
        else:
            findings.append(_finding(
                'dielectric-sourced', 'pass',
                f'gate epsilon_r from a material property row — '
                f'{detail}'))
    else:
        findings.append(_finding(
            'dielectric-sourced', 'warn',
            f'gate epsilon_r source: {eps_src or "unknown"} — not '
            'yet a simulated/measured material row',
            {'knob': 'msci material property rows for the sol-gel '
                     'dielectric',
             'how': 'add relativePermittivity to the material; '
                    're-derive'}))
    return findings


def validate(manager, subject, kind, report_factory=None):
    """Run the judge and save the report row."""
    findings = (validate_profile(subject) if kind == 'semiconductor'
                else validate_transistor(manager, subject))
    verdict = _verdict(findings)
    if report_factory is None:
        report_factory = DeviceValidationReport
    stamp = datetime.now(timezone.utc).isoformat()
    row = report_factory(
        name=f'{subject.name}-validation-'
             f'{stamp[11:19].replace(":", "")}',
        subject=subject.name, subject_kind=kind,
        findings_json=json.dumps(findings), verdict=verdict,
        validated_at=stamp, notes='', manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    return {'ok': True, 'subject': subject.name, 'kind': kind,
            'verdict': verdict, 'findings': findings,
            'reportRow': row.name}
