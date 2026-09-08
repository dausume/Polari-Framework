"""
@module odooconnect.odoo_bindings_basis

OdooModelBinding — bindings are DATA (ODOO_INTEGRATION_PLAN.md od-4):
one row maps an Odoo model to a Polari class with a field map; new
mappings are new rows, never code. The external-id strategy is a
custom `x_polari_ref` field on the Odoo side (created on demand by the
sync engine on push-enabled instances) holding the Polari row name —
the idempotency key that makes pushes safe to re-run.

@consumers polariServer defClassList + seed_pairs, odooconnect.custom.odoo_sync
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/odoo_bindings/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from odooconnect.objects.odoo_bindings._shared import BINDING_DIRECTIONS, SEED_ODOO_BINDINGS  # noqa: F401
from odooconnect.objects.odoo_bindings.OdooModelBinding import OdooModelBinding  # noqa: F401
from odooconnect.objects.odoo_bindings.OdooSyncReceipt import OdooSyncReceipt  # noqa: F401
