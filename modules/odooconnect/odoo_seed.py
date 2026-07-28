"""
@module odooconnect.odoo_seed

The two OdooInstanceConfig rows the suite runs on (od-1's pair):
odoo-sim is free to write (business simulations), odoo-ops is REAL
business data — read_only AND push_enabled=False until the od-6
guardrails land, and even then every write needs the typed phrase.

Idempotent-by-name (polariServer seed_pairs). Secrets are env-var
NAMES only.

@consumers polariServer seed_pairs
"""

SEED_ODOO_INSTANCES = [
    {
        'name': 'odoo-sim',
        'display_name': 'Odoo — simulations (odoo_sim)',
        'base_url': 'http://odoo:8069',
        'db': 'odoo_sim',
        'mode': 'simulation',
        'url_env': 'ODOO_SIM_URL',
        'auth_login': 'admin',
        'auth_password_env': 'ODOO_SIM_RPC_PASSWORD',
        'push_enabled': True,
        'read_only': False,
        'is_prior': True,
        'provenance_id': 'od-3',
        'notes': 'Business-simulation database — scenario seeds/pushes '
                 'are free (od-5 drives transactions here). v1 auth = '
                 'the init-db admin; a least-privilege RPC user is an '
                 'od-6 refinement.',
    },
    {
        'name': 'odoo-ops',
        'display_name': 'Odoo — REAL operations (odoo_ops)',
        'base_url': 'http://odoo:8069',
        'db': 'odoo_ops',
        'mode': 'operations',
        'url_env': 'ODOO_OPS_URL',
        'auth_login': 'admin',
        'auth_password_env': 'ODOO_OPS_RPC_PASSWORD',
        'push_enabled': False,
        'read_only': True,
        'is_prior': True,
        'provenance_id': 'od-3',
        'notes': 'REAL business data. read_only + push_enabled=False '
                 'until od-6 guardrails (backups + restore drill) are '
                 'proven; writes additionally require the typed '
                 'confirmation phrase per call. Transactions stay '
                 'human-in-Odoo in v1 — pushes are master-data only.',
    },
]
