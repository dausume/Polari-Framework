import os
import sys
import ssl
import threading
from pathlib import Path

# Import configuration loader
from config_loader import config, is_in_docker, get_backend_port

# Check if running in Docker container and adjust Python path
if is_in_docker():
    # If running in a Docker container, add vendor path
    sys.path.insert(0, '/app/vendor')

# Add the modules subdirectory to sys.path so polari*Module packages are importable
_modules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')
if os.path.isdir(_modules_dir) and _modules_dir not in sys.path:
    sys.path.insert(0, _modules_dir)

from objectTreeManagerDecorators import managerObject
from wsgiref.simple_server import make_server, WSGIServer
from socketserver import ThreadingMixIn
from falcon import falcon


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """Multi-threaded WSGI server to handle concurrent requests.

    This is necessary for the API Profiler self-call feature, which makes
    HTTP requests to the same server. Without threading, the server would
    deadlock waiting for its own response.
    """
    daemon_threads = True

# SSL Configuration - Cloudflare-compatible HTTPS port
HTTPS_PORT = 2096
SSL_CERT_PATH = "/app/certs/prf-proxy.crt"
SSL_KEY_PATH = "/app/certs/prf-proxy.key"


def check_ssl_certs():
    """Check if SSL certificates exist and are readable."""
    cert_path = Path(SSL_CERT_PATH)
    key_path = Path(SSL_KEY_PATH)

    if not cert_path.exists():
        return False, f"SSL certificate not found: {SSL_CERT_PATH}"
    if not key_path.exists():
        return False, f"SSL key not found: {SSL_KEY_PATH}"

    # Check if files are readable
    try:
        with open(cert_path, 'r') as f:
            f.read(1)
        with open(key_path, 'r') as f:
            f.read(1)
    except PermissionError as e:
        return False, f"Cannot read SSL files: {e}"

    return True, "SSL certificates found"


def create_ssl_context():
    """Create SSL context for HTTPS server."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(SSL_CERT_PATH, SSL_KEY_PATH)
    return context


def run_http_server(app, port):
    """Run HTTP server on specified port (multi-threaded)."""
    with make_server('', port, app, server_class=ThreadingWSGIServer) as httpd:
        print(f"[HTTP] Multi-threaded server starting on port {port}")
        httpd.serve_forever()


def run_https_server(app, port):
    """Run HTTPS server on specified port with SSL (multi-threaded)."""
    try:
        context = create_ssl_context()
        with make_server('', port, app, server_class=ThreadingWSGIServer) as httpd:
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
            print(f"[HTTPS] Multi-threaded server starting on port {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"[HTTPS] Server error: {e}")
        print(f"[HTTPS] HTTPS server on port {port} has stopped")


if(__name__=='__main__'):
    print("="*70)
    print("POLARI BACKEND SERVER STARTING")
    print("="*70)

    #Create a basic manager with a polariServer
    from polariApiServer.lazy_boot import (
        lazy_boot_enabled, start_admission_worker,
    )
    lazy = lazy_boot_enabled()
    if lazy:
        print("[LazyBoot] POLARI_LAZY_BOOT=on — two-phase boot: "
              "typing + routes now, DB/seeds after listen.")
    db_enabled = config.get_bool('database.enabled', True)
    localHostedManagerServer = managerObject(hasServer=True, hasDB=db_enabled)

    # Persist all initialized instances to database (lazy boots defer
    # this to the admission worker's close-out — the DB doesn't exist
    # yet in Phase 0).
    if not lazy and db_enabled and localHostedManagerServer.db is not None:
        localHostedManagerServer.persistTree()
        # dyn-2b: report what this boot ACTUALLY brought online (the
        # lazy path does the same in the admission worker close-out).
        try:
            from topology.placement_truth import (
                record_placement_observation,
            )
            record_placement_observation(localHostedManagerServer,
                                         'monolithic boot')
        except Exception as exc:
            print(f'[PlacementTruth] boot observation failed '
                  f'(non-fatal): {exc}', flush=True)

    # First-boot mesh role auto-config (mesh convergence Phase 1).
    # Runs in a delayed daemon thread so the API is already serving when
    # probes/join requests fire. Idempotent + graceful: unmeshed with no
    # discovery evidence is a logged no-op. Knob: POLARI_MESH_AUTOCONFIG
    # (default on; set 'false' to skip entirely).
    if (os.environ.get('POLARI_MESH_AUTOCONFIG') or 'true').lower() \
            in ('1', 'true', 'yes'):
        def _mesh_autoconfig():
            import time
            time.sleep(8)  # let the HTTP server come up first
            try:
                from polariPeers.role_autoconfig import auto_configure
                auto_configure(localHostedManagerServer)
            except Exception as exc:
                print(f'[RoleAutoConfig] first-boot run failed (non-fatal): '
                      f'{exc}', flush=True)
        threading.Thread(target=_mesh_autoconfig, daemon=True).start()

    # Start STOMP WebSocket server if enabled
    ws_enabled = config.get_bool('websocket.enabled', True)
    ws_port = config.get_int('websocket.port', 3001)
    if ws_enabled:
        from polariApiServer.stompWebSocketServer import StompWebSocketServer, set_stomp_server
        cors_origins = config.get('api.cors_origins', [])
        stomp_server = StompWebSocketServer(port=ws_port, cors_origins=cors_origins)
        stomp_server.start()
        # Store as module-level singleton (not on polariServer instance)
        # to avoid tree serialization encountering a non-tree object
        set_stomp_server(stomp_server)
    else:
        print("[WS] STOMP WebSocket server disabled by configuration")

    # Start the gRPC serving sidecar if enabled (grpc-2) — same idiom
    # as the STOMP sidecar: module-level singleton, next to falcon.
    # Serves ONLY classes with an enabled+current GrpcExposure row.
    grpc_enabled = config.get_bool('grpc.enabled', True)
    grpc_port = config.get_int('grpc.port', 3002)
    try:
        from grpcbridge.custom.grpc_server import (PolariGrpcServer,
                                            set_grpc_server)
    except ImportError:
        PolariGrpcServer = None   # the core image carries no grpcbridge (optional module) — the sidecar is simply off
    if grpc_enabled and PolariGrpcServer is not None:
        grpc_server = PolariGrpcServer(localHostedManagerServer,
                                       port=grpc_port)
        grpc_server.start()
        set_grpc_server(grpc_server)
    elif grpc_enabled:
        print("[gRPC] grpcbridge module not present (core image) — gRPC sidecar off; admit grpcbridge to enable it")
    else:
        print("[gRPC] Server disabled by configuration")

    # Get backend port from configuration
    http_port = get_backend_port()

    # Check for SSL certificates
    ssl_available, ssl_message = check_ssl_certs()

    print("\n" + "="*70)
    print("SERVER READY - All APIs available")
    print("="*70)

    # Display HTTP access
    print(f"\n[HTTP]  Server running on port {http_port}")
    print(f"        URL: http://localhost:{http_port}/")

    # Display WebSocket status
    if ws_enabled:
        print(f"\n[WS]    STOMP WebSocket server on port {ws_port}")
        print(f"        URL: ws://localhost:{ws_port}/")
    else:
        print(f"\n[WS]    STOMP WebSocket server NOT started (disabled)")

    # Display gRPC status
    if grpc_enabled:
        print(f"\n[gRPC]  Object-sync server on port {grpc_port}")
        print(f"        Serves enabled GrpcExposure classes "
              f"(reflection on)")
    else:
        print(f"\n[gRPC]  Server NOT started (disabled)")

    # Display HTTPS status
    if ssl_available:
        print(f"\n[HTTPS] Server running on port {HTTPS_PORT} (Cloudflare-compatible)")
        print(f"        URL: https://localhost:{HTTPS_PORT}/")
    else:
        print(f"\n[HTTPS] WARNING: HTTPS server NOT started")
        print(f"        Reason: {ssl_message}")
        print(f"        To enable HTTPS, run: ./generate-prf-certs.sh dev")

    print("\n" + "="*70 + "\n")

    falcon_app = localHostedManagerServer.polServer.falconServer

    # mlb-1: start the module-admission worker just before listening —
    # core data first (health flips 200), then each module in
    # dependency order, timing recorded per module.
    if lazy and db_enabled:
        start_admission_worker(localHostedManagerServer)
        print("[LazyBoot] admission worker started — "
              "GET /api/health + /api/modules/status track the "
              "bring-up.")
    else:
        # reg-1: a monolithic boot is complete here (tables, seeds, pages
        # all in) — verify every declared module against the live server
        # and mirror the records; the lazy path does this at BOOT COMPLETE.
        reg = getattr(localHostedManagerServer.polServer, 'moduleRegistrar', None)
        if reg is not None:
            try:
                reg.verify_all()
                reg.mirror_all()
                snap = reg.snapshot()
                print(f"[Registrar] {snap['counts']} — unhealthy: {snap['unhealthy'] or 'none'}",
                      flush=True)
            except Exception as exc:
                print(f'[Registrar] monolithic settle failed: {exc}', flush=True)

    if ssl_available:
        # Start HTTPS server in a separate thread
        https_thread = threading.Thread(
            target=run_https_server,
            args=(falcon_app, HTTPS_PORT),
            daemon=True
        )
        https_thread.start()
        print(f"[HTTPS] Background server started on port {HTTPS_PORT}")

    # Run HTTP server in main thread (blocks)
    print(f"[HTTP]  Server listening on port {http_port}...")
    run_http_server(falcon_app, http_port)