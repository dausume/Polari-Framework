"""
@module testing.custom.twin_fixtures

acct-3: throwaway twin fixtures — fresh core+m+n containers per run,
torn down after (plan §4: clean over fast; the suite must leave NO
demo containers running).

Each fixture runs the prf-backend image with the CURRENT framework
source (host repo mounted read-only at /src, copied to /appcopy at
boot so nothing writes into the working tree) and its own sqlite at
/tmp — the module split comes from POLARI_MODULES, identity from
POLARI_INSTANCE_ID/NAME, and epoch validation from POLARI_CORE_URL
pointing at the throwaway core (docker DNS by container name on the
run's own network).
"""

import json
import os
import subprocess
import time
import urllib.request

from testing.check_catalog import FRAMEWORK_ROOT

BOOT_CMD = ('cp -r /src /appcopy && cd /appcopy && '
            'mkdir -p /tmp/polari-data && '
            'exec python3 initLocalhostPolariServer.py')


def image_name():
    """The fixture image — a knob, read at call time."""
    return os.environ.get('POLARI_TWIN_IMAGE', 'prf-backend:staging')


def _docker(*args, timeout=60):
    return subprocess.run(['docker', *args], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True,
                          timeout=timeout)


class TwinRun:
    """One rehearsal's containers + network, teardown-guaranteed."""

    def __init__(self, run_tag):
        self.run_tag = run_tag
        self.network = f'acct3-net-{run_tag}'
        self.containers = {}   # role -> container name
        self.ips = {}          # role -> ip

    def container_name(self, role):
        return f'acct3-{role}-{self.run_tag}'

    def up(self, role, instance_id, modules=None, core_role=None):
        name = self.container_name(role)
        env = ['-e', 'DEPLOY_ENV=staging',
               '-e', 'IN_DOCKER_CONTAINER=true',
               '-e', 'DATABASE_TYPE=sqlite',
               '-e', 'DATABASE_PATH=/tmp/polari-data/polari.db',
               '-e', f'POLARI_INSTANCE_ID={instance_id}',
               '-e', f'POLARI_INSTANCE_NAME=polari-{instance_id}',
               '-e', 'WEBSOCKET_ENABLED=false',
               '-e', 'GRPC_ENABLED=false',
               # The fixtures ARE test builds: the rehearsal drives
               # the lease over /api/testing/lease (production has
               # no HTTP lease surface by design).
               '-e', 'POLARI_TEST_BUILD=true']
        if modules:
            env += ['-e', f'POLARI_MODULES={modules}']
        if core_role:
            env += ['-e', f'POLARI_CORE_URL=http://'
                          f'{self.container_name(core_role)}:3000']
        result = _docker(
            'run', '-d', '--name', name, '--network', self.network,
            '-v', f'{FRAMEWORK_ROOT}:/src:ro', '-w', '/app',
            *env, image_name(), 'sh', '-c', BOOT_CMD, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f'docker run {name}: {result.stdout}')
        self.containers[role] = name

    def create_network(self):
        result = _docker('network', 'create', self.network)
        if result.returncode != 0:
            raise RuntimeError(f'network create: {result.stdout}')

    def ip_of(self, role):
        if role not in self.ips:
            result = _docker(
                'inspect', '-f',
                '{{range .NetworkSettings.Networks}}'
                '{{.IPAddress}}{{end}}', self.containers[role])
            self.ips[role] = result.stdout.strip()
        return self.ips[role]

    def base_url(self, role):
        return f'http://{self.ip_of(role)}:3000'

    def internal_url(self, role):
        return f'http://{self.container_name(role)}:3000'

    def wait_ready(self, roles, timeout_s=300):
        """Poll /api/peers/ping on every role until identity answers
        (or raise with the slowest role's last error)."""
        deadline = time.monotonic() + timeout_s
        pending, last_error = set(roles), {}
        while pending and time.monotonic() < deadline:
            for role in sorted(pending):
                try:
                    with urllib.request.urlopen(
                            self.base_url(role) + '/api/peers/ping',
                            timeout=5) as response:
                        payload = json.load(response)
                    if payload.get('success'):
                        pending.discard(role)
                except Exception as exc:
                    last_error[role] = f'{type(exc).__name__}: {exc}'
            if pending:
                time.sleep(4)
        if pending:
            raise RuntimeError(
                f'not ready after {timeout_s}s: '
                + ', '.join(f'{r} ({last_error.get(r, "?")})'
                            for r in sorted(pending)))

    def logs_tail(self, role, lines=15):
        result = _docker('logs', '--tail', str(lines),
                         self.containers.get(role, ''))
        return result.stdout

    def teardown(self):
        """Remove every container + the network. Never raises."""
        for name in self.containers.values():
            _docker('rm', '-f', name, timeout=90)
        _docker('network', 'rm', self.network)

    def leftovers(self):
        """Any acct3-* containers still running (must be none)."""
        result = _docker('ps', '--format', '{{.Names}}')
        return [n for n in result.stdout.split()
                if n.startswith(f'acct3-') and
                n.endswith(self.run_tag)]
