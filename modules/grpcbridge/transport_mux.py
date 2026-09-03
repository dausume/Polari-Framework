"""
@module grpcbridge.transport_mux

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
  - grpcbridge.grpc_server._fan_out_push (pushed frames fan out here)
"""

from datetime import datetime, timezone


def _preference(manager, class_name):
    """The routing knob: only an ENABLED exposure's preference counts
    — a disabled/absent exposure routes 'stomp', exactly today's
    behavior (knob discipline: nothing changes until a human acts)."""
    try:
        from grpcbridge.proto_gen import get_exposure
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
        from grpcbridge.grpc_server import get_grpc_server
        return get_grpc_server()
    except Exception:
        return None


def publish_change(manager, class_name, topic, notification):
    """Route ONE topic's notification per the class knob. The STOMP
    leg publishes the same topic + dict it always has; the gRPC leg
    delivers a ChangeNotification carrying the same fields (parity by
    construction — the proto mirrors this payload)."""
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
