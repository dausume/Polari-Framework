"""
@module security.security_endpoints

construct_security_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.

It is also where the PII scrub is scheduled (his rule D18-1, 2026-09-18): the four observation ledgers were written
before Polari keyed people by their Keycloak `sub` alone, so any `actor` value on this instance that is not a subject
id is a name left over from an earlier test and is cleared, once per process, with the count in the log. The scrub
waits for the module's rows to be restored first — routes are built well before Phase B admits the data.
"""
from security.security_api import SecurityAPI


def construct_security_endpoints(polServer):
    api = SecurityAPI(polServer=polServer, manager=polServer.manager)
    try:
        from security.custom.security_observe import start_pii_scrub
        start_pii_scrub(polServer.manager, polServer)
    except Exception as exc:       # a migration must never stop the module from coming up
        print('[security] PII scrub could not be scheduled: %s' % exc, flush=True)
    try:
        # §54: the core display seed only INSERTS a missing page, so a change to one of these pages' definitions
        # never reaches an instance that already has them. Converge them once the rows are restored.
        from security.security_page import start_page_converge
        start_page_converge(polServer.manager, polServer)
    except Exception as exc:
        print('[security] page converge could not be scheduled: %s' % exc, flush=True)
    try:
        # op-4: the modules' `app.owned` stanzas become OwnedClassPolicy rows, re-derived on every read of the
        # owner doors and once here at boot so the FIRST CRUDE act already sees them. A policy an
        # administrator set is never overwritten.
        from security.custom.security_owned_manifest import start_owned_converge
        start_owned_converge(polServer.manager, polServer)
    except Exception as exc:
        print('[security] owned-policy converge could not be scheduled: %s' % exc, flush=True)
    return api
