"""
@module polariApiProfiler.endpoint_fetch

THE GENERIC FETCH PATH for APIEndpoint rows (Dustin 2026-08-02:
"ensure we use api profile capabilities and expand on them if
possible to retrieve the data so we can re-use that approach").

`APIProfiler.query_external_api` only speaks JSON — it calls
`.json()` and falls back to `.text`. That makes an entire class of
official data unreachable: SAS-XPORT lab files (binary), NOAA's
fixed-column text records, tab-delimited ice-core archives. This
module adds the missing path so ONE executor serves every row:

    resolve_endpoint_url(endpoint, params) -> (live, redacted)
    fetch_endpoint(endpoint, params, fetcher) -> retrieval dict

and it enforces the acceptance criteria the row carries
(`contentSignature` / `rejectSignature` / `minBytes`).

⚠ WHY CONTENT VALIDATION IS NOT OPTIONAL — a 200 that is not the
data, observed live against two different federal agencies:
- census.gov answers a keyless request with HTTP 200 and a
  'Missing Key' HTML page (census_pull.py, 2026-07-16);
- wwwn.cdc.gov answers RETIRED NHANES paths with HTTP 200 and a
  'Page Not Found' HTML page — two different retired URLs returned
  byte-identical 20905-byte bodies (2026-08-02).
Checking the status code alone would have ingested a webpage as a
lab result. `pandas.read_sas` would then have raised a traceback
from inside an API handler, blaming the parser for a routing
problem three layers up.

Bytes, never str: decoding a payload to find out what it is
corrupts the binary formats this exists to fetch.

@consumers climate.custom.series_ingest, climate.custom.xpt_reader,
polariApiProfiler.apiProfilerAPI
"""

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request

#: How to decode the body. The row says which; nothing sniffs.
RESPONSE_FORMATS = ('json', 'text', 'tsv', 'csv', 'xport', 'binary')

_REDACTED = '<redacted:env:{var}>'


def _get(endpoint, attr, default=''):
    """Rows and plain dicts both work — selftests build fixtures as
    SimpleNamespace, live tables carry treeObjects."""
    if isinstance(endpoint, dict):
        return endpoint.get(attr, default)
    return getattr(endpoint, attr, default)


def _secret_and_var(endpoint):
    raw = (_get(endpoint, 'authConfig', '') or '').strip()
    if raw.startswith('env:'):
        var = raw[4:].strip()
        return (os.environ.get(var) or '').strip(), var
    return raw, ''


def redact(url, endpoint):
    """A key must never reach provenance, a log, or a payload."""
    secret, var = _secret_and_var(endpoint)
    if not secret or not var:
        return url
    return url.replace(secret, _REDACTED.format(var=var))


def resolve_endpoint_url(endpoint, params=None):
    """(live_url, redacted_url) from a row + call params.

    `endpointPath` placeholders are filled from `paramsTemplate`
    defaults overlaid with `params`. A placeholder with no value
    RAISES by name rather than fetching a URL with a literal
    '{cycle}' in it — a 404 three seconds later is a much worse
    error message than the one we can give right here.
    """
    merged = {}
    raw_defaults = _get(endpoint, 'paramsTemplate', '') or '{}'
    try:
        merged.update(json.loads(raw_defaults) or {})
    except ValueError:
        raise ValueError(
            f'endpoint {_get(endpoint, "name", "?")!r} has invalid '
            f'paramsTemplate JSON: {raw_defaults[:120]!r}')
    merged.update(dict(params or {}))

    path = _get(endpoint, 'endpointPath', '') or ''
    try:
        path = path.format(**merged)
    except KeyError as exc:
        raise ValueError(
            f'endpoint {_get(endpoint, "name", "?")!r} path '
            f'{path!r} needs param {exc} — pass it, or put a '
            f'default in paramsTemplate')

    base = (_get(endpoint, 'url', '') or '').strip()
    if not base:
        base = _endpoint_base_from_domain(endpoint)
    url = f'{base.rstrip("/")}/{path.lstrip("/")}' if path else base

    secret, _var = _secret_and_var(endpoint)
    if _get(endpoint, 'authType', 'none') == 'apikey-query' and secret:
        sep = '&' if '?' in url else '?'
        url = f'{url}{sep}key={urllib.parse.quote(secret)}'
    return url, redact(url, endpoint)


def _endpoint_base_from_domain(endpoint):
    """Compose from the APIDomain row when no absolute url is set."""
    get_domain = getattr(endpoint, 'get_domain', None)
    domain = get_domain() if callable(get_domain) else None
    if domain is None:
        return ''
    getter = getattr(domain, 'get_base_url', None)
    if callable(getter):
        return getter() or ''
    proto = getattr(domain, 'protocol', 'https')
    host = getattr(domain, 'host', '')
    port = getattr(domain, 'port', 0)
    if not host:
        return ''
    return f'{proto}://{host}' + (f':{port}' if port else '')


def default_fetcher(url, timeout=120, headers=None):
    """(status, body_bytes_or_none, error). Never raises."""
    req = urllib.request.Request(url, headers=dict(headers or {}))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return getattr(resp, 'status', 200), resp.read(), ''
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read()
        except Exception:
            body = None
        return exc.code, body, f'HTTP {exc.code}'
    except Exception as exc:  # URLError, timeout, DNS…
        return 0, None, f'unreachable: {exc}'


def _as_bytes(value):
    if value is None:
        return b''
    if isinstance(value, bytes):
        return value
    return str(value).encode('utf-8', errors='replace')


def check_payload(endpoint, body):
    """The acceptance gate -> {'ok', 'refusal', 'saw'}.

    reject_signature is tested FIRST so the refusal can name the
    decoy specifically. Signatures are compared on BYTES, and a
    UTF-8 BOM is skipped before comparing: NOAA's paleo archives
    are BOM-prefixed, and a BOM is an encoding artifact, not a
    statement about whether the file is the right file.
    """
    raw = _as_bytes(body)
    if raw.startswith(b'\xef\xbb\xbf'):
        raw_cmp = raw[3:]
    else:
        raw_cmp = raw
    saw = raw_cmp[:80].decode('utf-8', errors='replace')

    # ORDER MATTERS, and it was wrong once: minBytes used to run
    # first, which MASKED this branch on the very endpoints the
    # trap was found on. The real CDC decoy is 20905 bytes and the
    # NHANES rows require 100000, so the decoy refused with a size
    # complaint and never with "that is an error page" - a true
    # refusal carrying the least useful of the two diagnoses. A
    # decoy is identified by WHAT IT IS, not by how big it is.
    reject = _get(endpoint, 'rejectSignature', '') or ''
    if reject and _as_bytes(reject).lower() in raw_cmp[:400].lower():
        return {'ok': False, 'saw': saw,
                'refusal': (f'the response starts with {reject!r} — '
                            f'an error/landing page served with a '
                            f'success status, not data. The URL has '
                            f'moved; re-verify it before seeding.')}

    min_bytes = int(_get(endpoint, 'minBytes', 0) or 0)
    if min_bytes and len(raw) < min_bytes:
        return {'ok': False, 'saw': saw,
                'refusal': (f'payload is {len(raw)} bytes, under the '
                            f'{min_bytes} this endpoint requires — '
                            f'that is not the series')}

    signature = _get(endpoint, 'contentSignature', '') or ''
    if signature and not raw_cmp.startswith(_as_bytes(signature)):
        return {'ok': False, 'saw': saw,
                'refusal': (f'payload does not begin with '
                            f'{signature!r}, which this source\'s '
                            f'real files carry; saw {saw!r}')}
    return {'ok': True, 'saw': saw, 'refusal': ''}


def _accepts_headers(fetcher):
    try:
        import inspect
        return 'headers' in inspect.signature(fetcher).parameters
    except (TypeError, ValueError):
        return False


def fetch_endpoint(endpoint, params=None, fetcher=None, timeout=120):
    """Fetch one endpoint -> a retrieval dict. Never raises.

    {'ok', 'status', 'bytes', 'sha256', 'url_redacted', 'body',
     'refusal', 'saw', 'endpoint', 'format'}

    `body` is bytes on success and None on every refusal, so a
    caller physically cannot parse a decoy.
    """
    fetcher = fetcher or default_fetcher
    name = _get(endpoint, 'name', '?')
    fmt = _get(endpoint, 'responseFormat', 'json') or 'json'
    out = {'endpoint': name, 'format': fmt, 'status': 0, 'bytes': 0,
           'sha256': '', 'url_redacted': '', 'body': None,
           'saw': '', 'ok': False, 'refusal': ''}

    try:
        live_url, safe_url = resolve_endpoint_url(endpoint, params)
    except ValueError as exc:
        out['refusal'] = str(exc)
        return out
    out['url_redacted'] = safe_url
    if not live_url:
        out['refusal'] = (f'endpoint {name!r} resolves to an empty '
                          f'URL — set url, or domainName + a domain '
                          f'row')
        return out

    headers = {}
    getter = getattr(endpoint, 'get_headers_with_auth', None)
    if callable(getter):
        try:
            headers = dict(getter() or {})
        except Exception:
            headers = {}
    resolver = getattr(endpoint, 'resolve_secret', None)
    if callable(resolver):
        _secret, refusal = resolver()
        if refusal:
            out['refusal'] = refusal
            return out

    if _accepts_headers(fetcher):
        status, body, err = fetcher(live_url, timeout=timeout,
                                    headers=headers)
    else:
        status, body, err = _normalize(fetcher(live_url))

    raw = _as_bytes(body)
    out['status'] = status
    out['bytes'] = len(raw)
    out['sha256'] = hashlib.sha256(raw).hexdigest() if raw else ''
    if status != 200:
        out['refusal'] = err or f'HTTP {status} from {safe_url}'
        return out

    gate = check_payload(endpoint, raw)
    out['saw'] = gate['saw']
    if not gate['ok']:
        out['refusal'] = gate['refusal']
        return out
    out['ok'] = True
    out['body'] = raw
    return out


def _normalize(result):
    """Tolerate the older 2-tuple fetchers (census_pull's shape)."""
    if isinstance(result, tuple) and len(result) == 3:
        return result
    if isinstance(result, tuple) and len(result) == 2:
        status, body = result
        return status, body, ''
    return 0, None, f'fetcher returned {type(result).__name__}'


def decode_body(fetch_result):
    """Bytes -> the shape the row's responseFormat promises.

    Returns (value, error). JSON that will not parse is an ERROR,
    not a silent fallback to text — a caller asking for json and
    receiving a string is how a decoy gets ingested.
    """
    if not fetch_result.get('ok'):
        return None, fetch_result.get('refusal', 'fetch refused')
    raw = fetch_result.get('body') or b''
    fmt = fetch_result.get('format', 'json')
    if fmt in ('xport', 'binary'):
        return raw, ''
    text = raw.decode('utf-8-sig', errors='replace')
    if fmt in ('text', 'tsv', 'csv'):
        return text, ''
    if fmt == 'json':
        try:
            return json.loads(text), ''
        except ValueError as exc:
            return None, (f'endpoint declares responseFormat=json '
                          f'but the body will not parse: {exc}; '
                          f'starts {text[:80]!r}')
    return text, ''
