"""
@module appstore.preview_server

Dev harness: serve the FOUR real download surfaces (/downloads,
/downloads/apps, /downloads/offline, /downloads/plan) without
booting the full polari backend — for browser review passes and
download testing. It mounts the SAME resource classes polariServer
registers (no twin routes, no re-implementation): what you see
here is what the instance serves, minus auth/SPA/everything else.

  cd polari-framework
  POLARI_DOWNLOADS_DIR=... POLARI_APP_DEBS_DIR=... \\
  POLARI_OFFLINE_DIR=... \\
  PYTHONPATH=.:modules python3 -m appstore.preview_server [port]

Binds 0.0.0.0 (LAN review from another device is the point);
default port 8090. Serves real files: Option A/B debs download for
real, app debs GENERATE for real (TTL pool + ledger active), and
offline chunks stream for real. NOT a production server — wsgiref,
no TLS, no auth; kill it when the review pass is done.
"""

import sys
from wsgiref.simple_server import make_server

import falcon

from appstore.app_debs_page import AppDebsPage
from appstore.downloads_page import DownloadsPage
from appstore.offline_page import OfflinePage
from appstore.planner_page import PlannerPage


def build_app():
    app = falcon.App()
    downloads = DownloadsPage(polServer=None)
    apps = AppDebsPage(polServer=None)
    offline = OfflinePage(polServer=None)
    plan = PlannerPage(polServer=None)
    # the same routes polariServer adds (appstore gate section)
    app.add_route('/downloads', downloads, suffix='page')
    app.add_route('/downloads/{filename}', downloads,
                  suffix='file')
    app.add_route('/downloads/apps', apps, suffix='page')
    app.add_route('/downloads/apps/get/{module}', apps,
                  suffix='get')
    app.add_route('/downloads/apps/get-offline/{module}', apps,
                  suffix='get_offline')
    app.add_route('/downloads/apps/status/{module}', apps,
                  suffix='status')
    app.add_route('/downloads/apps/file/{filename}', apps,
                  suffix='file')
    app.add_route('/downloads/apps/shared/{debname}', apps,
                  suffix='shared')
    app.add_route('/downloads/offline', offline, suffix='page')
    app.add_route('/downloads/offline/{filename:path}', offline,
                  suffix='file')
    app.add_route('/downloads/plan', plan, suffix='page')
    return app


def main(argv):
    port = int(argv[0]) if argv else 8090
    server = make_server('0.0.0.0', port, build_app())
    print(f'downloads preview on http://0.0.0.0:{port}/downloads '
          '(ctrl-c stops it)')
    server.serve_forever()


if __name__ == '__main__':
    main(sys.argv[1:])
