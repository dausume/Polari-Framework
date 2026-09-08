"""
@module electrodevice.device_validator_basis

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
  - electrodevice.electrodevice_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/device_validator/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit

from electrodevice.objects.device_validator._shared import _finding, _verdict, validate_profile, validate_transistor  # noqa: F401
from electrodevice.objects.device_validator.DeviceValidationReport import DeviceValidationReport  # noqa: F401

from datetime import datetime, timezone
import json

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
