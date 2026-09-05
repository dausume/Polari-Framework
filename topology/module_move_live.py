"""
@module topology.module_move_live

dyn-7 (DYNAMIC_MODULES_PLAN): move a module between live instances
WITHOUT recreating either backend.

What it replaces: today's `isle polari module move` rewrites
POLARI_MODULES on both compose services and force-recreates both
backends (~1-2 min each even with lazy boot), and the stateful half
— the module's ROWS — is left behind entirely
(MESH_APP_CONVERGENCE_HANDOFF §48/§49 name both gaps as the
documented-but-unbuilt work).

The sequence, deliberately in this order:

  1. PLAN        — pure; what would happen, and every refusal, first.
  2. ADMIT on the GAINER (dyn-2/dyn-4)  — the module serves in two
     places briefly. Overlap is the point: no request window is
     unserved, which is what makes it zero-downtime.
  3. DATA handoff — the rows follow the module (module_data_move's
     whole-class vs named-subset regimes, UNION merge, quiesced).
  4. PUT AWAY on the LOSER (dyn-3) — non-destructive; its tables stay
     until the handoff is verified, so a failed move is recoverable.
  5. ROWS + PUSH (dyn-2b) — ModuleAssignment reflects the new home,
     the observation refreshes, and STOMP /topic/PolariModule tells
     open clients to re-point (dyn-8's invalidateOn signal).

Boundaries kept: the backend is the LEDGER, not the executor — steps
that need docker/ssh or a second instance's cooperation are returned
as the caller's acts, each with its exact call. Nothing here reaches
into another instance uninvited; the gainer performs its own
admission through its own API, and a PeerAgreement must already
exist (bilateral consent before cross-instance anything).
"""

import time

from polariApiServer.module_gating import CORE_PACKAGES
from polariApiServer.lazy_boot import top_module


def _instance_name(manager):
    from topology.placement_truth import _instance_name as name
    return name()


def _peer_base_url(manager, instance):
    for node in (manager.objectTables.get('PeerNode', {})
                 or {}).values():
        name = getattr(node, 'name', '')
        base = (getattr(node, 'base_url', '') or '').rstrip('/')
        if base and (name == instance or name.endswith(instance)
                     or instance.endswith(name)):
            return base
    return ''


def _agreement_ok(manager, instance):
    """Bilateral consent: an approved PeerAgreement must exist before
    anything crosses instances. Absent the class entirely (a
    standalone node), say so rather than pretending to have checked."""
    table = manager.objectTables.get('PeerAgreement')
    if table is None:
        return None, 'PeerAgreement rows unavailable on this instance'
    for row in table.values():
        peer = (getattr(row, 'peer_name', '')
                or getattr(row, 'name', ''))
        state = (getattr(row, 'state', '')
                 or getattr(row, 'status', '')).lower()
        if instance and instance in str(peer) and state in (
                'approved', 'active', 'admitted'):
            return True, f'approved agreement with {peer}'
    return False, f'no approved PeerAgreement naming {instance!r}'


def plan_module_move(manager, module, to_instance,
                     from_instance=None):
    """Pure preview: the ordered steps, who performs each, and every
    refusal — computed BEFORE anything moves."""
    here = _instance_name(manager)
    from_instance = from_instance or here
    polServer = manager.polServer
    refusals = []

    if module in CORE_PACKAGES:
        refusals.append(f"'{module}' is a core package — it "
                        'registers everywhere; there is nothing to '
                        'move.')
    if to_instance == from_instance:
        refusals.append('source and target are the same instance')
    live_here = {top_module(c) for c in polServer.defClassList}
    if from_instance == here and module not in live_here:
        refusals.append(f"'{module}' is not live on '{from_instance}'"
                        ' — nothing to move from here')
    base_url = _peer_base_url(manager, to_instance)
    if not base_url:
        refusals.append(f"no PeerNode base_url for '{to_instance}' —"
                        ' the gainer must be addressable')
    consent, why = _agreement_ok(manager, to_instance)
    if consent is False:
        refusals.append(why)

    class_names = sorted(c.__name__ for c in polServer.defClassList
                         if top_module(c) == module)
    rows_here = sum(len(manager.objectTables.get(n, {}))
                    for n in class_names)
    steps = [
        {'step': 1, 'act': 'admit on the gainer',
         'performedBy': to_instance,
         'call': f'POST {base_url}/modules/{module}/admit'
                 f'?withDeps=true' if base_url else
                 f'POST <gainer>/modules/{module}/admit?withDeps=true',
         'why': 'overlap first — the module serves in two places so '
                'no request window is unserved'},
        {'step': 2, 'act': 'hand the data over',
         'performedBy': 'host (pol CLI)',
         'call': f'python3 -m polariDBmanagement.module_data_move '
                 f'--module {module} --from <{from_instance}.db> '
                 f'--to <{to_instance}.db> --apply',
         'why': f'{rows_here} rows across {len(class_names)} classes '
                'follow the module; UNION merge, quiesce first',
         'classes': class_names},
        {'step': 3, 'act': 'put away on the loser',
         'performedBy': from_instance,
         'call': f'POST /modules/{module}/put-away',
         'why': 'non-destructive — tables stay until the handoff is '
                'verified, so a failed move is recoverable'},
        {'step': 4, 'act': 'rows + push',
         'performedBy': from_instance,
         'call': 'automatic (dyn-2b): ModuleAssignment reflects the '
                 'new home, observation refreshes, STOMP '
                 '/topic/PolariModule tells open clients to '
                 're-point',
         'why': 'the placement authority must agree, and clients '
                'must SEE it'},
    ]
    return {
        'ok': not refusals, 'module': module,
        'from': from_instance, 'to': to_instance,
        'gainerBaseUrl': base_url,
        'consent': {'ok': consent, 'detail': why},
        'classes': class_names, 'rowsOnSource': rows_here,
        'steps': steps,
        'refusals': refusals,
        'note': 'plan only — executes nothing. The backend is the '
                'ledger; docker/ssh and the gainer\'s own admission '
                'are the caller\'s acts.',
    }


def execute_local_half(manager, module, to_instance,
                       data_moved=False):
    """Perform ONLY what this instance may legitimately do itself:
    put the module away here and land the new placement in the rows,
    with the client-visible push. Refuses unless the caller confirms
    the data handoff already happened — otherwise the rows would say
    'moved' while the data sat here, the exact incoherence dyn-2b
    exists to prevent."""
    if not data_moved:
        return {'ok': False, 'module': module,
                'refusal': 'data handoff not confirmed — put-away '
                           'would strand the rows here while the '
                           'placement says otherwise',
                'suggestion': {
                    'action': 'run module_data_move --apply, verify '
                              'the destination, then retry with '
                              'dataMoved=true'}}
    started = time.time()
    from polariApiServer.live_admission import put_away_module_live
    result = put_away_module_live(manager, module)
    if not result.get('ok'):
        return result
    try:
        from topology.placement_truth import sync_assignment_row
        row = sync_assignment_row(manager, module, 'transient',
                                  f'dyn-7 moved to {to_instance}')
    except Exception as exc:
        row = {'synced': False, 'reason': str(exc)}
    return {'ok': True, 'module': module, 'to': to_instance,
            'putAway': result,
            'assignmentRow': row,
            'tookSeconds': round(time.time() - started, 3),
            'note': 'the losing side is now transient (visible, '
                    'inert, one click back) — never deleted; open '
                    'clients re-point on the STOMP push + the 410 '
                    'their next call gets'}
