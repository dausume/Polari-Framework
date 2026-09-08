"""
@module odooconnect.odoo_basis

OdooInstanceConfig — one row per Odoo endpoint the framework may talk
to (ODOO_INTEGRATION_PLAN.md od-3). THE HARD INVARIANT lives here as
data: every row carries mode 'simulation' | 'operations', and the
client layer (odoo_client) refuses writes on any handle whose row does
not explicitly allow them. Secrets NEVER sit in a row — auth_password_env
names the environment variable that holds the RPC password/api-key.

@consumers
  - polariServer defClassList + seed_pairs (SEED_ODOO_INSTANCES)
  - odooconnect.custom.odoo_client (handles), odooconnect.custom.odoo_analysis
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/odoo/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from odooconnect.objects.odoo._shared import ODOO_MODES  # noqa: F401
from odooconnect.objects.odoo.OdooInstanceConfig import OdooInstanceConfig  # noqa: F401
