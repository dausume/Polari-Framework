"""@module electrodevice.objects.device_validator._shared — what the device_validator row classes share (constants, seeds, helpers); split from device_validator_basis.py (sap-2c)."""
import json

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
    from electrodevice.semiconductor_basis import get_profile
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
