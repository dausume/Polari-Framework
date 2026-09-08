"""
@module cntfet.custom.cnt_validate

The standards judge for the S1 aligned device — REUSES
electrodevice.device_validator_basis's finding/verdict machinery and its
DeviceValidationReport rows (derivations never self-bless), with
cntfet-specific criteria:

  components-resolved   all six decomposed rows exist
  params-derived        derive ran; derived fields stamped
  roles-assigned        every CNTFETParameterRow carries role +
                        source (D8 is real, not decorative)
  rc-first-class        contact prior present, distinct from
                        mobility, above the quantum floor (D9)
  model-labeled         family/implementation/equivalence labels
                        ride the transport row (D3)
  calibration-recorded  a calibration result row with residuals
                        exists (warn until run)
  equivalence-proven    an OSDI equivalence run passed (warn until
                        run — tools may be absent on this instance)
  priors-honest         calibration-role rows carry low/medium
                        confidence, never 'high' (a prior claiming
                        certainty is a lie)

@consumers
  - cntfet.cnt_api ({action: validate})
  - cntfet.cntfet_selftest
"""

import json

from electrodevice.device_validator_basis import (
    DeviceValidationReport, _finding, _verdict,
)

from cntfet.custom.cnt_derive import resolve_components


def validate_cntfet_device(manager, device):
    findings = []
    rows, missing = resolve_components(manager, device)
    if missing:
        findings.append(_finding(
            'components-resolved', 'fail',
            f'missing: {missing}',
            {'knob': 'device component name fields',
             'how': 'point at existing rows or seed them'}))
        return findings, rows
    findings.append(_finding(
        'components-resolved', 'pass',
        'all six decomposed rows resolve (D2b)'))
    if not getattr(device, 'derived_at', ''):
        findings.append(_finding(
            'params-derived', 'fail', 'never derived',
            {'knob': f'/api/cntfet/devices/{device.name}',
             'how': 'POST {"action": "derive"}'}))
        return findings, rows
    transport = rows['transport']
    findings.append(_finding(
        'params-derived', 'pass',
        f'derived {device.derived_at}: vxo '
        f'{transport.vxo_m_per_s:.4g} m/s, n_ss '
        f'{transport.n_ss:.4g}, DIBL '
        f'{transport.dibl_v_per_v:.4g} V/V'))

    tables = getattr(manager, 'objectTables', None) or {}
    param_rows = [r for r in (tables.get('CNTFETParameterRow')
                              or {}).values()
                  if getattr(r, 'device', '') == device.name]
    unroled = [r.parameter for r in param_rows
               if not (getattr(r, 'role', '')
                       and getattr(r, 'source', ''))]
    if not param_rows:
        findings.append(_finding(
            'roles-assigned', 'fail',
            'no CNTFETParameterRow rows — derive should have '
            'stamped them'))
    elif unroled:
        findings.append(_finding(
            'roles-assigned', 'fail',
            f'{len(unroled)} parameter rows missing role/source: '
            f'{unroled[:6]}'))
    else:
        by_role = {}
        for r in param_rows:
            by_role[r.role] = by_role.get(r.role, 0) + 1
        findings.append(_finding(
            'roles-assigned', 'pass',
            f'{len(param_rows)} parameter rows, all role+source '
            f'tagged: {by_role}'))

    contact = rows['contact']
    rc = float(getattr(contact, 'rc_ohm', 0.0) or 0.0)
    floor = float(getattr(contact, 'rq_floor_ohm', 0.0) or 0.0)
    if rc <= 0.0:
        findings.append(_finding(
            'rc-first-class', 'fail',
            'no contact-resistance prior (D9: Rc is first-class)'))
    elif floor > 0.0 and rc < floor:
        findings.append(_finding(
            'rc-first-class', 'fail',
            f'Rc prior {rc:.4g} ohm BELOW the quantum floor '
            f'{floor:.4g} ohm — unphysical',
            {'knob': 'contact rc_ohm',
             'how': f'>= {floor:.4g} ohm'}))
    else:
        findings.append(_finding(
            'rc-first-class', 'pass',
            f'Rc {rc:.4g} ohm per terminal (floor {floor:.4g}), '
            'carried as its own object, never in mobility'))

    label_ok = (getattr(transport, 'model_family', '')
                == 'VS-CNFET-derived'
                and getattr(transport, 'implementation', '')
                == 'independent'
                and not getattr(transport,
                                'numerically_equivalent_to_stanford',
                                True))
    findings.append(_finding(
        'model-labeled', 'pass' if label_ok else 'fail',
        'D3 labels ride the transport row' if label_ok else
        'model labels missing/misleading — the model must never '
        'be presented as the Stanford VS-CNFET'))

    results = [r for r in (tables.get('CNTFETSimResult')
                           or {}).values()
               if getattr(r, 'device', '') == device.name]
    cal = [r for r in results if getattr(r, 'kind', '')
           == 'calibration']
    if cal:
        findings.append(_finding(
            'calibration-recorded', 'pass',
            f'{len(cal)} calibration run(s) with residuals '
            'recorded'))
    else:
        findings.append(_finding(
            'calibration-recorded', 'warn',
            'no calibration run yet',
            {'knob': f'/api/cntfet/devices/{device.name}',
             'how': 'POST {"action": "calibrate"}'}))
    equiv = [r for r in results if getattr(r, 'kind', '')
             == 'equivalence']
    passed = [r for r in equiv if getattr(r, 'verdict', '')
              == 'EQUIVALENT']
    if passed:
        findings.append(_finding(
            'equivalence-proven', 'pass',
            'Python reference == OSDI twin within recorded '
            'tolerances'))
    else:
        findings.append(_finding(
            'equivalence-proven', 'warn',
            'no passed OSDI equivalence run on this instance '
            '(tooling may be absent — capability endpoint says)',
            {'knob': f'/api/cntfet/devices/{device.name}',
             'how': 'POST {"action": "equivalence"}'}))

    dishonest = [r.parameter for r in param_rows
                 if getattr(r, 'role', '') == 'calibration'
                 and getattr(r, 'confidence', '') == 'high']
    if dishonest:
        findings.append(_finding(
            'priors-honest', 'fail',
            f'calibration-role parameters claiming HIGH '
            f'confidence: {dishonest}',
            {'knob': 'those parameter rows',
             'how': 'a prior is not a measurement — low/medium '
                    'only'}))
    else:
        findings.append(_finding(
            'priors-honest', 'pass',
            'all calibration-role parameters carry honest '
            'confidence'))
    return findings, rows


def validate(manager, device):
    """Judge + persist the DeviceValidationReport row (subject_kind
    'aligned-cntfet')."""
    from datetime import datetime, timezone
    findings, _ = validate_cntfet_device(manager, device)
    verdict = _verdict(findings)
    stamp = datetime.now(timezone.utc).isoformat()
    row = DeviceValidationReport(
        name=f'{device.name}-validation-'
             f'{stamp[11:19].replace(":", "")}',
        subject=device.name, subject_kind='aligned-cntfet',
        findings_json=json.dumps(findings), verdict=verdict,
        validated_at=stamp, notes='', manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    return {'ok': True, 'subject': device.name,
            'kind': 'aligned-cntfet', 'verdict': verdict,
            'findings': findings, 'reportRow': row.name}
