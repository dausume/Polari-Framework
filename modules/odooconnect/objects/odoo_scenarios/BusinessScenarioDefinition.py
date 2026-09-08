"""
@module odooconnect.objects.odoo_scenarios.BusinessScenarioDefinition

Row class BusinessScenarioDefinition of the odooconnect module — one class per file (design §7), split
from odoo_scenarios_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BusinessScenarioDefinition(treeObject):
    """One runnable business simulation: seed spec, driver, outcome
    spec — all data. Lifecycle receipts land as OdooSyncReceipt rows
    (kind scenario-<phase>)."""

    @treeObjectInit
    def __init__(self, name='', display_name='', instance_ref='',
                 scenario_db='', required_modules='',
                 assumptions_json='[]', seed_spec_json='{}',
                 driver_spec_json='{}', outcome_spec_json='{}',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        #: Base config (MUST be mode=simulation) whose server/auth the
        #: scenario database is reached through.
        self.instance_ref = instance_ref
        #: Throwaway database, 'odoo_scn_*' by convention — the CLI
        #: refuses to init/drop anything outside that prefix.
        self.scenario_db = scenario_db
        self.required_modules = required_modules
        self.assumptions_json = assumptions_json
        self.seed_spec_json = seed_spec_json
        self.driver_spec_json = driver_spec_json
        self.outcome_spec_json = outcome_spec_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
