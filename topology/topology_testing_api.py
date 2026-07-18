"""
@cross-cutting
@module topology.topology_testing_api

TopologyTestingAPI (tt-11): the /api/topology/testing surface.
Reads serve the Testing tab + the colored topology; the two POSTs
EXECUTE things a human explicitly asked for and store honest
receipts as rows:

  POST /run  {module?: 'aquaponics' | 'all'} — run selftest suites
             in-process (same subprocess the pol CLI uses), parse
             the X/Y tally, persist TopologyTestRun rows.
  POST /ping — the FOUNDATIONAL integration pass: connectivity
             only, never functionality. Machines ping via their
             system_info_url knob; dependency edges via the top-7
             provider routing (cross-node reachability — the real
             'does prf-a reach the engines worker' check);
             config-artifact connections are honestly marked
             static (nothing live to ping). Every row notates the
             protocol and how it is (not) secured.

@consumers
  - polariServer (instantiated next to TopologyAPI)
  - polari-platform-angular /testing page (tt-11)
"""

import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit

from topology.topology_analysis import active_topology_name
from topology.topology_testing import (
    IntegrationPing, TopologyTestRun, discover_suites,
    parse_suite_output, protocol_of, testing_report,
)

SUITE_TIMEOUT_S = 120


class TopologyTestingAPI(treeObject):
    """Testing-over-topology endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/topology/testing'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/topology/testing', self, suffix='report')
            add('/api/topology/testing/run', self, suffix='run')
            add('/api/topology/testing/ping', self, suffix='ping')

    # ---- helpers ----------------------------------------------------

    def _payload(self, request):
        try:
            return json.load(request.bounded_stream), None
        except Exception as e:
            return None, f'bad JSON payload: {e}'

    def _topology_name(self, request, payload=None):
        name = (payload or {}).get('topology', '') or (
            request.params.get('name', ''))
        return name or active_topology_name(self.manager)

    def _save(self, row):
        try:
            self.manager.db.saveInstanceInDB(row)
        except Exception:
            pass

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    # ---- reads ------------------------------------------------------

    def on_get_report(self, request, response):
        name = self._topology_name(request)
        if not name:
            return self._refuse(
                response, 'no active topology and no ?name= given',
                '404 Not Found')
        response.media = testing_report(self.manager, name)

    # ---- executions (explicitly human-invoked) -----------------------

    def on_post_run(self, request, response):
        """Run one module's selftest suites (or all modules')."""
        payload, err = self._payload(request)
        if err:
            payload = {}
        topology = self._topology_name(request, payload)
        module = (payload or {}).get('module', '') or 'all'
        suites = discover_suites()
        if module != 'all':
            if module not in suites:
                return self._refuse(
                    response,
                    f'no selftest suites found for "{module}" '
                    f'(modules with suites: {sorted(suites)})',
                    '404 Not Found')
            suites = {module: suites[module]}
        results = []
        for module_name, module_suites in sorted(suites.items()):
            for suite in module_suites:
                results.append(self._run_suite(
                    module_name, suite, topology))
        response.media = {
            'ok': True, 'topology': topology,
            'ran': len(results), 'results': results,
            'report': testing_report(self.manager, topology)}

    def _run_suite(self, module_name, suite, topology):
        """One suite as a subprocess — the same invocation the pol
        CLI documents; the row is the honest receipt either way."""
        ran_at = self._now()
        try:
            proc = subprocess.run(
                [sys.executable, '-m', suite],
                capture_output=True, text=True,
                timeout=SUITE_TIMEOUT_S)
            output = (proc.stdout or '') + (proc.stderr or '')
            tally = parse_suite_output(output)
            if tally is None:
                status, passed, total = 'error', 0, 0
            else:
                passed, total = tally
                status = ('pass' if proc.returncode == 0
                          and passed == total else 'fail')
            tail = output[-1500:]
        except subprocess.TimeoutExpired:
            status, passed, total = 'timeout', 0, 0
            tail = f'suite exceeded {SUITE_TIMEOUT_S}s'
        except Exception as e:
            status, passed, total = 'error', 0, 0
            tail = str(e)
        row = TopologyTestRun(
            name=f'{suite}@{ran_at}', module_name=module_name,
            suite=suite, status=status, checks_passed=passed,
            checks_total=total, output_tail=tail, ran_at=ran_at,
            topology_name=topology, manager=self.manager)
        self._save(row)
        return {'suite': suite, 'status': status,
                'checksPassed': passed, 'checksTotal': total}

    def on_post_ping(self, request, response):
        """The foundational integration pass — pinging only."""
        payload, err = self._payload(request)
        if err:
            payload = {}
        topology = self._topology_name(request, payload)
        if not topology:
            return self._refuse(
                response, 'no active topology and no name given',
                '404 Not Found')
        checked_at = self._now()
        pings = []
        pings.extend(self._ping_machines(topology, checked_at))
        pings.extend(self._ping_dep_edges(topology, checked_at))
        pings.extend(self._mark_connections(topology, checked_at))
        for ping in pings:
            self._save(ping)
        response.media = {
            'ok': True, 'topology': topology,
            'checked': len(pings),
            'report': testing_report(self.manager, topology)}

    def _rows(self, class_name, topology=None):
        rows = (self.manager.objectTables or {}).get(
            class_name, {}).values()
        if topology is None:
            return list(rows)
        return [r for r in rows
                if getattr(r, 'topology_name', '') == topology]

    def _ping(self, url, timeout=4):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as rsp:
                return True, f'HTTP {rsp.status}'
        except Exception as e:
            return False, str(e)[:200]

    def _ping_row(self, kind, subject, topology, checked_at,
                  **fields):
        return IntegrationPing(
            name=f'{subject}@{checked_at}', kind=kind,
            subject=subject, checked_at=checked_at,
            topology_name=topology, manager=self.manager, **fields)

    def _ping_machines(self, topology, checked_at):
        from topology.topology_analysis import is_real_machine
        out = []
        for machine in self._rows('PolariNodeMachine'):
            name = getattr(machine, 'name', '')
            url = getattr(machine, 'system_info_url', '')
            swarm_role = getattr(machine, 'swarm_role', 'none')
            if not is_real_machine(machine):
                out.append(self._ping_row(
                    'machine', name, topology, checked_at,
                    status='unpingable',
                    evidence='synthetic (sim) machine row — '
                             'nothing real to ping'))
                continue
            if not getattr(machine, 'ssh_alias', ''):
                out.append(self._ping_row(
                    'machine', name, topology, checked_at,
                    protocol='in-process', secured=True,
                    security_note='this backend runs here — no '
                                  'network channel involved',
                    status='ok',
                    evidence='local machine (the core backend '
                             'process itself)'))
                continue
            swarm_note = (f'; swarm {swarm_role} (node-level health '
                          'lives on the manager: docker node ls)'
                          if swarm_role in ('manager', 'worker')
                          else '')
            if not url:
                out.append(self._ping_row(
                    'machine', name, topology, checked_at,
                    status='unpingable',
                    evidence='no system_info_url knob set — no HTTP '
                             'endpoint to ping' + swarm_note))
                continue
            protocol, secured, note = protocol_of(url)
            alive, evidence = self._ping(url)
            out.append(self._ping_row(
                'machine', name, topology, checked_at,
                target=url, protocol=protocol, secured=secured,
                security_note=note,
                status='ok' if alive else 'failed',
                evidence=evidence + ('' if alive else swarm_note)))
        return out

    def _ping_dep_edges(self, topology, checked_at):
        """Cross-node reachability via the top-7 provider routing —
        the real 'does the consumer reach its provider' ping."""
        from topology.provider_registry import resolve_provider
        out = []
        for edge in self._rows('ModuleDependencyEdge', topology):
            subject = getattr(edge, 'name', '')
            result = resolve_provider(
                getattr(edge, 'depends_on_module', ''))
            if result.get('ok'):
                url = result.get('url', '')
                protocol, secured, note = protocol_of(url)
                out.append(self._ping_row(
                    'dep-edge', subject, topology, checked_at,
                    target=url, protocol=protocol, secured=secured,
                    security_note=note
                    + (' on the docker/swarm network'
                       if not secured and protocol else ''),
                    status='ok',
                    evidence=f'provider "{result.get("instance")}" '
                             f'answered at {url}'))
            else:
                out.append(self._ping_row(
                    'dep-edge', subject, topology, checked_at,
                    status='failed',
                    evidence=json.dumps(result)[:400]))
        return out

    def _mark_connections(self, topology, checked_at):
        """Config-artifact connections have no live channel — say
        so instead of painting them green."""
        out = []
        for conn in self._rows('ServiceConnection', topology):
            out.append(self._ping_row(
                'connection', getattr(conn, 'name', ''), topology,
                checked_at,
                protocol='file', secured=False,
                security_note='config artifact — no live channel '
                              'to secure or ping',
                status='static-artifact',
                evidence=f'artifact: '
                         f'{getattr(conn, "artifact", "")}'))
        return out
