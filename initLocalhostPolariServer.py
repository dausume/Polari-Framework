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
    db_enabled = config.get_bool('database.enabled', True)
    localHostedManagerServer = managerObject(hasServer=True, hasDB=db_enabled)

    # Persist all initialized instances to database
    if db_enabled and localHostedManagerServer.db is not None:
        localHostedManagerServer.persistTree()

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