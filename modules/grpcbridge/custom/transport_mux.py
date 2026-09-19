"""
@module grpcbridge.custom.transport_mux

The transport MUX (grpc-2/3): ONE publish seam for CRUDE change
notifications, routed per the class's `transport_preference` knob on
its GrpcExposure row — 'stomp' (the default, and the behavior when no
exposure exists: byte-identical to the historical direct-STOMP path),
'grpc', or 'both' (the dual-publish migration mode).

Also carries the hardware command-down leg: create/update changes
that did NOT originate from a gRPC Push are streamed as full objects
to Commands subscribers (a Push echoing back down would loop the
simulated MCU forever — telemetry in must never come back out as a
command).

@consumers
  - polariApiServer.polariCRUDE._notify_ws_subscribers (the seam)
  - grpcbridge.custom.grpc_server._fan_out_push (pushed frames fan out here)
"""

from datetime import datetime, timezone


def _preference(manager, class_name):
    """The routing knob: only an ENABLED exposure's preference counts
    — a disabled/absent exposure routes 'stomp', exactly today's
    behavior (knob discipline: nothing changes until a human acts)."""
    try:
        from grpcbridge.custom.proto_gen import get_exposure
        exposure = get_exposure(manager, class_name)
    except Exception:
        exposure = None
    if exposure is not None and getattr(exposure, 'enabled', False):
        pref = getattr(exposure, 'transport_preference', 'stomp')
        if pref in ('stomp', 'grpc', 'both'):
            return pref
    return 'stomp'


def _stomp_server():
    try:
        from polariApiServer.stompWebSocketServer import get_stomp_server
        return get_stomp_server()
    except Exception:
        return None


def _grpc_server():
    try:
        from grpcbridge.custom.grpc_server import get_grpc_server
        return get_grpc_server()
    except Exception:
        return None


def _anonymised(manager, class_name):
    """op-0's `OwnedClassPolicy.anonymised` (design §5). Never raises: a class whose policy cannot be read is
    treated as ordinary, exactly as it was before op-0 existed."""
    try:
        from security.custom.security_owned import policy_for
        policy = policy_for(manager, class_name)
        return bool(policy and policy.get('anonymised'))
    except Exception:
        return False


def _trace_publish(manager, class_name, topic, notification):
    """ct-2 (design §3): `object:<Class>:<verb> → event:topic:<Class>` (means `ws-publish`).

    COUNT ONLY — the map is class-level, so no instance id ever rides this edge (the effect journal is where
    an instance is looked up). `touch` runs first because a broadcast can be the first seam a chain crosses on
    the armed class. WHO subscribes is not knowable here and is not guessed: the subscribe half is ct-6.
    Lazy import, never raises, a complete no-op unless a `TraceTarget` is armed and this chain is traced."""
    try:
        from security.custom.security_trace import record_edge, touch
    except Exception:
        return
    try:
        verb = str((notification or {}).get('operation') or 'update')
        touch(manager, class_name, verb)
        record_edge(manager, 'object:%s:%s' % (class_name, verb),
                    'event:topic:%s' % class_name, 'ws-publish', detail=str(topic or ''))
    except Exception:
        pass


def publish_change(manager, class_name, topic, notification):
    """Route ONE topic's notification per the class knob. The STOMP
    leg publishes the same topic + dict it always has; the gRPC leg
    delivers a ChangeNotification carrying the same fields (parity by
    construction — the proto mirrors this payload)."""
    _trace_publish(manager, class_name, topic, notification)
    pref = _preference(manager, class_name)
    if pref in ('stomp', 'both'):
        stomp = _stomp_server()
        if stomp is not None:
            stomp.publish(topic, notification)
    if pref in ('grpc', 'both'):
        grpc_srv = _grpc_server()
        if grpc_srv is not None:
            grpc_srv.notify_watchers(class_name, notification)


def publish_crude_change(manager, class_name, operation, instance_ids,
                         from_push=False):
    """The full CRUDE fan-out for one mutation — topic construction
    identical to the historical polariCRUDE._notify_ws_subscribers,
    now routed through the MUX. Never raises (failure-isolated at the
    caller too, belt and braces)."""
    # cal-2: OBJECT triggers ride this one lifecycle hook — every
    # CRUDE create/update/delete reaches EventTrigger rows here.
    # Never raises (the dispatcher is failure-isolated itself).
    try:
        from polariNoCode.event_dispatcher import dispatch_object_change
        dispatch_object_change(manager, class_name, operation, instance_ids)
    except Exception as e:
        print(f'[transport_mux] event dispatch failed for {class_name}: {e}',
              flush=True)
    typing = (getattr(manager, 'objectTypingDict', None)
              or {}).get(class_name)
    format_config = getattr(typing, 'apiFormatConfig', None)
    if format_config is None:
        return

    notification = {
        "className": class_name,
        "operation": operation,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "instanceIds": instance_ids or []
    }

    # ct-2 / design §5: a class whose OwnedClassPolicy is ANONYMISED is
    # deliberately unlinkable, and STOMP subscription to /topic/{Class} is
    # unauthenticated until ct-6 — so the BROADCAST drops the instance ids.
    # The class and the operation stay, which is all a subscriber needs to
    # know it should re-read; what it may then read is the CRUDE gate's
    # business, not the broadcast's.
    if _anonymised(manager, class_name):
        notification["instanceIds"] = []

    if getattr(format_config, 'polariTreeWsEnabled', False):
        crude = dict(notification)
        crude["formatType"] = "crude"
        publish_change(manager, class_name,
                       f'/topic/{class_name}', crude)

    for fmt, enabled in [
            ('flatJson', getattr(format_config, 'flatJsonWsEnabled',
                                 False)),
            ('d3Column', getattr(format_config, 'd3ColumnWsEnabled',
                                 False)),
            ('geoJson', getattr(format_config, 'geoJsonWsEnabled',
                                False))]:
        if enabled:
            fmt_notification = dict(notification)
            fmt_notification["formatType"] = fmt
            publish_change(manager, class_name,
                           f'/topic/{class_name}/{fmt}',
                           fmt_notification)

    # Command-down leg: human/API-initiated create/update reaches
    # hardware as full objects. Pushed telemetry never echoes back.
    if (not from_push and operation in ('create', 'update')
            and _preference(manager, class_name) in ('grpc', 'both')):
        grpc_srv = _grpc_server()
        if grpc_srv is not None:
            grpc_srv.notify_commands(class_name, instance_ids or [])
