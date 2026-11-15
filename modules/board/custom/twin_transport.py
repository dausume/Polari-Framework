"""
@module board.custom.twin_transport

td-1 (AI-Notes/plans/TWIN_DOOR_PLAN.md §3, §5): HOW this backend reaches a twin session's two streams, read from what the worker ADVERTISES, never guessed from
its URL.

    pick(cap, worker_url, session_id, ports) -> {'ctl_url', 'uart_url', 'why'}

A worker whose /capability carries
    "transports": {"ctl": "wss://twin.board-engines.isle/sessions/{id}/ctl", "uart": "wss://twin.board-engines.isle/sessions/{id}/uart"}
is reached through that door (WebSocket over HTTPS, by name, through the isle agent). A worker that advertises none is reached on its per-session TCP ports
(`tcp://<worker host>:<port>`): the dev compose, which publishes the range. The choice and its reason go on the TwinSession row, so a person can read which
way a session went and why.

An advertised door is a DECLARED door: a malformed one is a refusal in words (TransportRefused), and one that is down refuses the session (twin_sessions) -
never a silent fall back to TCP (the user's D4, the same rule as BOARD_ENGINES_URL).
"""
from urllib.parse import quote, urlparse

STREAMS = ('ctl', 'uart')
LOOPBACK = ('127.0.0.1', 'localhost', '::1')
PLACEHOLDER = '{id}'


class TransportRefused(RuntimeError):
    pass


def split(url):
    """-> (scheme, host, port, the url). Refuses anything that is not tcp://host:port, wss://host[:port]/path or (loopback only) ws://."""
    u = urlparse(url or '')
    try:
        port = u.port
    except ValueError:
        raise TransportRefused('the twin channel %r has a port that is not a number' % url)
    if u.scheme == 'tcp':
        if not u.hostname or not port:
            raise TransportRefused('the twin channel %r needs a host and a port (tcp://host:port)' % url)
        return 'tcp', u.hostname, port, url
    if u.scheme in ('wss', 'ws'):
        if not u.hostname:
            raise TransportRefused('the twin channel %r names no host' % url)
        if u.scheme == 'ws' and u.hostname not in LOOPBACK:
            raise TransportRefused('the twin channel %r is a WebSocket without TLS: only wss:// is accepted off this device (ws:// is for a loopback test)' % url)
        return u.scheme, u.hostname, port or (443 if u.scheme == 'wss' else 80), url
    raise TransportRefused('the twin channel %r is neither tcp://host:port nor wss://host/path' % url)


def _door(template, stream, session_id):
    if not isinstance(template, str) or PLACEHOLDER not in template:
        raise TransportRefused('the worker advertises transports.%s = %r, which has no %s to put the session id in' % (stream, template, PLACEHOLDER))
    url = template.replace(PLACEHOLDER, quote(str(session_id), safe=''))
    scheme = split(url)[0]
    if scheme == 'tcp':
        raise TransportRefused('the worker advertises transports.%s = %r: a door is wss://, the TCP ports are what a worker WITHOUT a door uses' % (stream, template))
    return url


def pick(cap, worker_url, session_id, ports):
    """The two channel URLs of ONE session and the reason, from the worker's capability (`cap`, the /capability JSON) and the session's `ports` ({'tcp', 'ctl'})."""
    host = urlparse(worker_url or '').hostname or ''
    tcp = {'ctl': 'tcp://%s:%s' % (host, (ports or {}).get('ctl') or 0), 'uart': 'tcp://%s:%s' % (host, (ports or {}).get('tcp') or 0)}
    if not isinstance(cap, dict):
        raise TransportRefused('the worker\'s /capability could not be read just now, so whether it has a twin door is unknown')
    adv = cap.get('transports')
    if adv is None:
        return {'ctl_url': tcp['ctl'], 'uart_url': tcp['uart'],
                'why': 'the worker advertises no twin door (no "transports" in its /capability): plain TCP on the session\'s own ports, which works only where '
                       'the worker publishes them (the dev compose)'}
    if not isinstance(adv, dict) or not any(adv.get(s) for s in STREAMS):
        raise TransportRefused('the worker\'s /capability has "transports": %r - expected {"ctl": "wss://.../sessions/{id}/ctl", "uart": "wss://.../sessions/{id}/uart"}' % (adv,))
    out, said = {}, []
    for s in STREAMS:
        if adv.get(s):
            out[s] = _door(adv[s], s, session_id)
            said.append('%s through the worker\'s twin door' % s)
        else:
            out[s] = tcp[s]
            said.append('%s on plain TCP (the worker advertises no door for it)' % s)
    return {'ctl_url': out['ctl'], 'uart_url': out['uart'], 'why': 'read from the worker\'s /capability: ' + ', '.join(said)}


def kind(url):
    """'door' | 'tcp' | '' - the one word the status view shows."""
    try:
        return 'tcp' if split(url)[0] == 'tcp' else 'door'
    except TransportRefused:
        return ''
