"""
@module electrodevice.objects.device_validator.DeviceValidationReport

Row class DeviceValidationReport of the electrodevice module — one class per file (design §7), split
from device_validator_basis.py (sap-2c). The class docstring below is the explanation.
"""
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
