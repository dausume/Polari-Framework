"""
@module grpcbridge.grpc_server

The gRPC serving sidecar (grpc-2) — mirrors
polariApiServer.stompWebSocketServer exactly: a daemon-thread server
next to the Falcon WSGI backend, module-level singleton accessors,
started by initLocalhostPolariServer, knobs `grpc.enabled` /
`grpc.port` (env GRPC_ENABLED / GRPC_PORT, default :3002).

Serving is GENERIC — no per-class codegen at runtime. One
GenericRpcHandler resolves every `/polari.sync.<Class>Sync/<Method>`
call against the live ContractRuntime (descriptors built from the
stored tag ledger); classes without an enabled+CURRENT GrpcExposure
refuse with evidence naming the knob (the gate IS the feature).

Auth parity note: the REST layer currently grants universal object
access when no user info is present (see polariCRUDE
.getUsersObjectAccessPermissions) — the bridge matches that behavior
exactly: an `authorization` bearer token in call metadata is accepted
and logged, absence is allowed. Hardware service-account enforcement
is the named grpc-4 seam (_authorize below).

@consumers
  - initLocalhostPolariServer (startup, next to the STOMP sidecar)
  - grpcbridge.transport_mux (Watch/Commands fan-out)
  - grpcbridge.contract_api (refresh on knob acts)
"""

import json
import queue
import threading

try:
    import grpc
    from grpc_reflection.v1alpha import reflection, reflection_pb2_grpc
    HAS_GRPC = True
except ImportError:
    HAS_GRPC = False

# Module-level singleton — same idiom as stompWebSocketServer: keeps
# the server out of treeObject __dict__ so tree serialization never
# encounters it.
_grpc_instance = None


def get_grpc_server():
    """Get the module-level PolariGrpcServer singleton (or None)."""
    return _grpc_instance


def set_grpc_server(server):
    """Set the module-level PolariGrpcServer singleton."""
    global _grpc_instance
    _grpc_instance = server


def refresh_grpc_runtime():
    """Rebuild the serving runtime from the current exposure rows.
    Safe to call from anywhere (no-op when the sidecar isn't up)."""
    server = get_grpc_server()
    if server is not None:
        server.refresh()


def _method_of(handler_call_details):
    # '/polari.sync.FooSync/Get' -> ('polari.sync.FooSync', 'Get')
    parts = handler_call_details.method.lstrip('/').rsplit('/', 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], '')


class PolariGrpcServer:
    """Generic gRPC object-sync server over enabled exposures.

    Watch subscribers receive ChangeNotification messages (the exact
    STOMP payload fields — parity by construction); Commands
    subscribers receive full serialized objects when rows of their
    class change (the hardware command-down leg).
    """

    def __init__(self, manager, port=3002, max_workers=20):
        self.manager = manager
        self.port = port
        self.max_workers = max_workers
        self.runtime = None
        self._server = None
        self._running = False
        self._lock = threading.Lock()
        # class -> set of (queue, format_type) for Watch streams
        self._watchers = {}
        # class -> set of queue for Commands streams
        self._command_watchers = {}

    # ---- lifecycle ---------------------------------------------------

    def refresh(self):
        """Swap in a fresh ContractRuntime (atomic attr assignment;
        in-flight streams keep serving off the runtime they started
        with)."""
        try:
            from grpcbridge.descriptor_build import runtime_from_manager
            self.runtime = runtime_from_manager(self.manager)
            print(f"[gRPC] Runtime refreshed: serving "
                  f"{self.runtime.service_names() or 'no services'}",
                  flush=True)
        except Exception as exc:
            print(f"[gRPC] Runtime refresh failed: {exc}", flush=True)

    def start(self):
        if not HAS_GRPC:
            print("[gRPC] WARNING: 'grpcio' not installed. "
                  "gRPC server disabled.", flush=True)
            return
        self.refresh()
        from concurrent import futures
        self._server = grpc.server(
            futures.ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix='grpc-sync'))
        self._server.add_generic_rpc_handlers(
            (_DynamicSyncHandler(self),))
        reflection_pb2_grpc.add_ServerReflectionServicer_to_server(
            _DynamicReflection(self), self._server)
        bound = self._server.add_insecure_port(f'0.0.0.0:{self.port}')
        if not self.port:  # ephemeral (selftests): keep the real port
            self.port = bound
        self._server.start()
        self._running = True
        print(f"[gRPC] Server started on port {self.port}", flush=True)

    def stop(self):
        self._running = False
        if self._server is not None:
            self._server.stop(grace=1.0)

    def get_status(self):
        with self._lock:
            watch = sum(len(s) for s in self._watchers.values())
            cmds = sum(len(s) for s in self._command_watchers.values())
        return {
            'running': self._running,
            'port': self.port,
            'services': (self.runtime.service_names()
                         if self.runtime else []),
            'watchSubscribers': watch,
            'commandSubscribers': cmds,
        }

    # ---- fan-out (called from CRUDE threads via the transport MUX) ----

    def notify_watchers(self, class_name, notification):
        """Deliver one change-notification dict (the STOMP payload) to
        this class's Watch streams. Thread-safe; queue puts only."""
        runtime = self.runtime
        if runtime is None or class_name not in runtime.field_maps:
            return 0
        with self._lock:
            targets = list(self._watchers.get(class_name, ()))
        if not targets:
            return 0
        cn_cls = runtime.message_class('ChangeNotification')
        msg = cn_cls(
            class_name=notification.get('className', class_name),
            operation=notification.get('operation', ''),
            timestamp=notification.get('timestamp', ''),
            instance_ids=[str(i) for i in
                          notification.get('instanceIds') or []],
            format_type=notification.get('formatType', ''))
        sent = 0
        fmt = notification.get('formatType', '')
        for q, wanted_fmt in targets:
            # No filter = the default 'crude' topic (parity with a
            # STOMP /topic/{Class} subscription — per-format streams
            # opt in explicitly, so nobody gets duplicate deliveries).
            if (wanted_fmt or 'crude') != fmt:
                continue
            q.put(msg)
            sent += 1
        return sent

    def notify_commands(self, class_name, instance_ids):
        """Deliver the FULL current state of the named rows to this
        class's Commands streams (the hardware command-down leg)."""
        runtime = self.runtime
        if runtime is None or class_name not in runtime.field_maps:
            return 0
        with self._lock:
            targets = list(self._command_watchers.get(class_name, ()))
        if not targets:
            return 0
        tables = getattr(self.manager, 'objectTables', None) or {}
        rows = tables.get(class_name) or {}
        sent = 0
        for pid in instance_ids or []:
            inst = rows.get(pid)
            if inst is None:
                continue
            msg = runtime.instance_to_message(class_name, inst)
            for q in targets:
                q.put(msg)
                sent += 1
        return sent

    # ---- subscription registry ----------------------------------------

    def _subscribe(self, registry, class_name, entry):
        with self._lock:
            registry.setdefault(class_name, set()).add(entry)

    def _unsubscribe(self, registry, class_name, entry):
        with self._lock:
            entries = registry.get(class_name)
            if entries:
                entries.discard(entry)
                if not entries:
                    registry.pop(class_name, None)

    # ---- the gate ------------------------------------------------------

    def refusal_for(self, class_name):
        """Why this class is not served right now — evidence naming
        the knob, mirroring the contract layer's refusal shape."""
        from grpcbridge.proto_gen import get_exposure
        exposure = get_exposure(self.manager, class_name)
        knob = f'/api/grpc/exposures/{class_name}'
        if exposure is None:
            return (f'class "{class_name}" has no gRPC exposure — '
                    f'enable the knob: POST {knob} '
                    '{"action": "enable"}')
        status = getattr(exposure, 'contract_status', 'never-generated')
        if not getattr(exposure, 'enabled', False):
            return (f'gRPC exposure for "{class_name}" is disabled — '
                    f'POST {knob} {{"action": "enable"}}')
        if status != 'current':
            notes = getattr(exposure, 'notes', '')
            return (f'contract for "{class_name}" is {status} — '
                    f'regenerate the knob: POST {knob} '
                    f'{{"action": "regenerate"}}; evidence: {notes}')
        return (f'class "{class_name}" is not in the serving runtime '
                'yet — refresh pending')

    def _authorize(self, context):
        """grpc-4 seam: hardware service-account enforcement lands
        here. Today: parity with REST (anonymous allowed), bearer
        tokens logged for observability."""
        for key, value in (context.invocation_metadata() or ()):
            if key == 'authorization':
                print(f"[gRPC] call carries authorization metadata "
                      f"({value[:16]}...)", flush=True)
        return True


if HAS_GRPC:

    class _DynamicSyncHandler(grpc.GenericRpcHandler):
        """Resolves every polari.sync.* call against the live runtime
        — one handler, zero per-class registration."""

        def __init__(self, server):
            self._srv = server

        def service(self, handler_call_details):
            service_name, method = _method_of(handler_call_details)
            if not service_name.startswith('polari.sync.'):
                return None
            runtime = self._srv.runtime
            cls = (runtime.class_for_service(service_name)
                   if runtime else None)
            if cls is None:
                if service_name.endswith('Sync'):
                    gate_cls = service_name[len('polari.sync.'):-4]
                    detail = self._srv.refusal_for(gate_cls)
                    return _refusal_handler(method, detail)
                return None
            serializer = lambda msg: msg.SerializeToString()
            req_cls = {
                'Get': runtime.message_class('ObjectKey'),
                'List': runtime.message_class('ListRequest'),
                'Watch': runtime.message_class('WatchRequest'),
                'Push': runtime.message_class(cls),
                'Commands': runtime.message_class('WatchRequest'),
            }.get(method)
            if req_cls is None:
                return None
            deserializer = req_cls.FromString
            srv, rt = self._srv, runtime
            if method == 'Get':
                return grpc.unary_unary_rpc_method_handler(
                    lambda req, ctx: _do_get(srv, rt, cls, req, ctx),
                    deserializer, serializer)
            if method == 'List':
                return grpc.unary_stream_rpc_method_handler(
                    lambda req, ctx: _do_list(srv, rt, cls, req, ctx),
                    deserializer, serializer)
            if method == 'Watch':
                return grpc.unary_stream_rpc_method_handler(
                    lambda req, ctx: _do_watch(srv, cls, req, ctx),
                    deserializer, serializer)
            if method == 'Push':
                return grpc.stream_unary_rpc_method_handler(
                    lambda it, ctx: _do_push(srv, rt, cls, it, ctx),
                    deserializer, serializer)
            if method == 'Commands':
                return grpc.unary_stream_rpc_method_handler(
                    lambda req, ctx: _do_commands(srv, cls, req, ctx),
                    deserializer, serializer)
            return None

    def _refusal_handler(method, detail):
        def _abort_unary(request, context):
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, detail)

        def _abort_stream(request, context):
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, detail)
            yield  # pragma: no cover — abort raises

        if method == 'Push':
            return grpc.stream_unary_rpc_method_handler(
                _abort_unary,
                request_deserializer=lambda b: b,
                response_serializer=lambda m: m)
        if method in ('List', 'Watch', 'Commands'):
            return grpc.unary_stream_rpc_method_handler(
                _abort_stream,
                request_deserializer=lambda b: b,
                response_serializer=lambda m: m)
        return grpc.unary_unary_rpc_method_handler(
            _abort_unary,
            request_deserializer=lambda b: b,
            response_serializer=lambda m: m)

    class _DynamicReflection(reflection_pb2_grpc.ServerReflectionServicer):
        """Reflection over the LIVE runtime: each stream snapshots the
        current pool + enabled services (a fresh inner servicer per
        call keeps grpcio-reflection's internals untouched)."""

        def __init__(self, server):
            self._srv = server

        def ServerReflectionInfo(self, request_iterator, context):
            runtime = self._srv.runtime
            names = list(runtime.service_names()) if runtime else []
            names.append(reflection.SERVICE_NAME)
            inner = reflection.ReflectionServicer(
                names, pool=runtime.pool if runtime else None)
            return inner.ServerReflectionInfo(request_iterator, context)

    # ---- method bodies ------------------------------------------------

    def _do_get(srv, runtime, cls, request, context):
        srv._authorize(context)
        scope = _instance_scope(srv.manager)
        if request.instance_id and scope and request.instance_id != scope:
            context.abort(
                grpc.StatusCode.NOT_FOUND,
                f'instance_id "{request.instance_id}" is not this '
                f'instance ("{scope}") — each Polari instance serves '
                'only its own rows (shared-DB composite identity)')
        tables = getattr(srv.manager, 'objectTables', None) or {}
        inst = (tables.get(cls) or {}).get(request.id)
        if inst is None:
            context.abort(grpc.StatusCode.NOT_FOUND,
                          f'no {cls} row with id "{request.id}"')
        return runtime.instance_to_message(cls, inst)

    def _do_list(srv, runtime, cls, request, context):
        srv._authorize(context)
        tables = getattr(srv.manager, 'objectTables', None) or {}
        rows = tables.get(cls) or {}
        ordered = sorted(rows.values(),
                         key=lambda r: str(getattr(r, 'id', '')))
        offset = max(0, request.offset)
        limit = request.limit if request.limit > 0 else len(ordered)
        for inst in ordered[offset:offset + limit]:
            yield runtime.instance_to_message(cls, inst)

    def _do_watch(srv, cls, request, context):
        srv._authorize(context)
        entry = (queue.Queue(), request.format_type or '')
        srv._subscribe(srv._watchers, cls, entry)
        try:
            while context.is_active():
                try:
                    yield entry[0].get(timeout=0.5)
                except queue.Empty:
                    continue
        finally:
            srv._unsubscribe(srv._watchers, cls, entry)

    def _do_commands(srv, cls, request, context):
        srv._authorize(context)
        q = queue.Queue()
        srv._subscribe(srv._command_watchers, cls, q)
        try:
            while context.is_active():
                try:
                    yield q.get(timeout=0.5)
                except queue.Empty:
                    continue
        finally:
            srv._unsubscribe(srv._command_watchers, cls, q)

    def _do_push(srv, runtime, cls, request_iterator, context):
        """Hardware-in: each streamed message lands as a scoped
        object-tree update (matched by id) or a new row, then fans out
        through the SAME transport MUX as REST mutations."""
        srv._authorize(context)
        received = applied = refused = 0
        notes = []
        for msg in request_iterator:
            received += 1
            try:
                pid, operation = _apply_push(srv.manager, runtime,
                                             cls, msg)
                applied += 1
                _fan_out_push(srv.manager, cls, operation, pid)
            except Exception as exc:
                refused += 1
                if len(notes) < 3:
                    notes.append(str(exc))
        summary = runtime.message_class('PushSummary')(
            received=received, applied=applied, refused=refused,
            note='; '.join(notes))
        return summary

    def _instance_scope(manager):
        db = getattr(manager, 'db', None)
        return getattr(db, 'instanceScope', '') if db is not None else ''

    def _apply_push(manager, runtime, cls, msg):
        values = runtime.message_to_values(cls, msg)
        pid = str(values.get('id', '') or '')
        tables = getattr(manager, 'objectTables', None) or {}
        rows = tables.get(cls)
        if rows is None:
            raise ValueError(f'class "{cls}" has no object table')
        inst = rows.get(pid) if pid else None

        def _narrowed(target, name, value):
            # Python bools stabilize as TEXT, so contracts carry them
            # as 'True'/'False' strings; narrow back to the trusted
            # bool on the way in — otherwise every hardware push
            # OOPSes the schema it is honestly conforming to.
            if (isinstance(value, str)
                    and isinstance(getattr(target, name, None), bool)
                    and value in ('True', 'False')):
                return value == 'True'
            return value

        if inst is None and not pid and values.get('name'):
            # Many stabilization snapshots don't carry the polari id
            # (it isn't a typed field) — fall back to the framework's
            # `name` unique-key convention so repeated telemetry
            # frames UPDATE their row instead of multiplying rows.
            wanted = str(values['name'])
            for row in rows.values():
                if str(getattr(row, 'name', '')) == wanted:
                    inst = row
                    pid = str(getattr(row, 'id', '') or '')
                    break
        if inst is not None:
            for name, value in values.items():
                if name == 'id':
                    continue
                setattr(inst, name, _narrowed(inst, name, value))
            operation = 'update'
        else:
            typing = (getattr(manager, 'objectTypingDict', None)
                      or {}).get(cls)
            class_def = getattr(typing, 'classDefinition', None)
            if class_def is None:
                raise ValueError(
                    f'no registered class definition for "{cls}" — '
                    'cannot create from a pushed frame')
            inst = class_def(manager=manager)
            generated_id = getattr(inst, 'id', None)
            for name, value in values.items():
                if name == 'id':
                    continue
                setattr(inst, name, _narrowed(inst, name, value))
            if pid and pid != generated_id:
                # Re-key to the pushed identity (the device names its
                # row) BEFORE first save, so table key == id.
                rows.pop(generated_id, None)
                inst.id = pid
                rows[pid] = inst
            else:
                pid = generated_id
            operation = 'create'
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(inst)
        return pid, operation

    def _fan_out_push(manager, cls, operation, pid):
        """Pushed frames fan out exactly like REST mutations — via the
        transport MUX (STOMP and/or gRPC per the class knob). Never
        raises into the push loop."""
        try:
            from grpcbridge.transport_mux import publish_crude_change
            publish_crude_change(manager, cls, operation, [pid],
                                 from_push=True)
        except Exception as exc:
            print(f"[gRPC] push fan-out error for {cls}: {exc}",
                  flush=True)
