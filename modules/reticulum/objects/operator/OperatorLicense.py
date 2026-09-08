"""
@module reticulum.objects.operator.OperatorLicense

Row class OperatorLicense of the reticulum module — one class per file (design §7), split
from operator_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class OperatorLicense(treeObject):
    """A self-declaration with an author and a timestamp — precisely
    what it claims to be, and the software never pretends it is more.
    Identity stays Keycloak's: this row ANNOTATES a user."""

    @treeObjectInit
    def __init__(self, name='', kc_subject='', callsign='',
                 license_class='', issuing_authority='',
                 jurisdiction='', issued_date='', expiry_date='',
                 asserted_at='', notes='', manager=None):
        self.name = name
        self.kc_subject = kc_subject
        self.callsign = callsign
        self.license_class = license_class
        self.issuing_authority = issuing_authority
        self.jurisdiction = jurisdiction
        self.issued_date = issued_date
        self.expiry_date = expiry_date
        # When the operator made the assertion — part of the record.
        self.asserted_at = asserted_at
        self.notes = notes
