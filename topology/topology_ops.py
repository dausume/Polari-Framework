"""
@module topology.topology_ops

rel-87: the host operator's topology commands, run INSIDE a backend container (no `pol` needed on the device):

    sudo docker exec <backend> python3 -m topology.topology_ops peers
    sudo docker exec <backend> python3 -m topology.topology_ops peers-add <name> <https://url>
    sudo docker exec <backend> python3 -m topology.topology_ops peers-remove <name|url>
    sudo docker exec <backend> python3 -m topology.topology_ops pull
    sudo docker exec <backend> python3 -m topology.topology_ops example-rows
    sudo docker exec <backend> python3 -m topology.topology_ops retire --digest <planDigest>
    sudo docker exec <backend> python3 -m topology.topology_ops restore --backup <name from the receipt>

A thin client of the running backend's own doors over loopback (http://127.0.0.1:<port>), so every change goes through
the server process that owns the database (never a second writer) and the tpl-6 operator gate reads it as the host
operator. Knob POLARI_TOPOLOGY_OPS_PORT (default 3000, the backend's in-container port). Prints the door's words; exit 0
when the door said ok, 1 otherwise, 2 on a usage error or an unreachable backend.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

PORT_KNOB = 'POLARI_TOPOLOGY_OPS_PORT'


def _base():
    return 'http://127.0.0.1:%s' % ((os.environ.get(PORT_KNOB) or '3000').strip())


def call(method, path, body=None, opener=None):
    """-> (status, json). opener is injectable for the selftest."""
    data = None if body is None else json.dumps(body).encode('utf-8')
    req = urllib.request.Request(_base() + path, data=data, method=method, headers={'Content-Type': 'application/json'})
    open_ = opener or urllib.request.urlopen
    try:
        with open_(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8') or '{}')
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8') or '{}')
        except Exception:  # noqa: BLE001
            return e.code, {'ok': False, 'words': 'HTTP %d' % e.code}


def parser():
    p = argparse.ArgumentParser(prog='python3 -m topology.topology_ops', description='host-operator topology commands')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('peers', help='the peers this backend names, and their last pull')
    a = sub.add_parser('peers-add', help='name a peer backend (kept on the data volume)')
    a.add_argument('name')
    a.add_argument('url')
    r = sub.add_parser('peers-remove', help='stop naming an operator-added peer')
    r.add_argument('peer')
    sub.add_parser('pull', help='pull every named peer now')
    sub.add_parser('example-rows', help='the plan for retiring the July example rows (read only)')
    t = sub.add_parser('retire', help='retire the example rows, bound to the plan digest (backs up first)')
    t.add_argument('--digest', required=True)
    s = sub.add_parser('restore', help='restore a retire backup')
    s.add_argument('--backup', required=True)
    return p


ROUTES = {
    'peers': ('GET', '/api/topology/peers', lambda a: None),
    'peers-add': ('POST', '/api/topology/peers/add', lambda a: {'name': a.name, 'url': a.url}),
    'peers-remove': ('POST', '/api/topology/peers/remove', lambda a: {'peer': a.peer}),
    'pull': ('POST', '/api/topology/peers/pull', lambda a: {}),
    'example-rows': ('GET', '/api/topology/example-rows', lambda a: None),
    'retire': ('POST', '/api/topology/example-rows/retire', lambda a: {'planDigest': a.digest}),
    'restore': ('POST', '/api/topology/example-rows/restore', lambda a: {'backup': a.backup}),
}


def main(argv=None, opener=None, out=sys.stdout):
    args = parser().parse_args(argv)
    method, path, body = ROUTES[args.cmd]
    try:
        status, media = call(method, path, body(args), opener=opener)
    except Exception as exc:  # noqa: BLE001 - an unreachable backend is said, never a traceback
        print('backend not reachable at %s (%s: %s)' % (_base(), type(exc).__name__, exc), file=out)
        return 2
    print(json.dumps(media, indent=2, sort_keys=True, default=str), file=out)
    if media.get('words'):
        print('\n' + str(media['words']), file=out)
    return 0 if (200 <= status < 300 and media.get('ok', True)) else 1


if __name__ == '__main__':
    sys.exit(main())
