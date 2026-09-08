"""
@module testing.custom.twin_http

acct-3: tiny stdlib HTTP client for the rehearsal — JSON calls plus
the CRUDE multipart write protocol (the wire format polariCRUDE
accepts: multipart/form-data only, initParamSets to create,
polariId+updateData to update).
"""

import json
import urllib.error
import urllib.request

BOUNDARY = 'acct3-boundary'


def json_call(url, method='GET', body=None, headers=None,
              timeout=30):
    """(status, parsed-json-or-text). Never raises on HTTP errors."""
    data = None
    all_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        all_headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(url, data=data, method=method,
                                     headers=all_headers)
    try:
        with urllib.request.urlopen(request,
                                    timeout=timeout) as response:
            raw = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        status = exc.code
    except Exception as exc:
        return 0, f'{type(exc).__name__}: {exc}'
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw


def _multipart(fields):
    parts = []
    for name, value in fields.items():
        parts.append(f'--{BOUNDARY}\r\nContent-Disposition: '
                     f'form-data; name="{name}"\r\n\r\n{value}\r\n')
    body = (''.join(parts) + f'--{BOUNDARY}--\r\n').encode()
    return body, f'multipart/form-data; boundary={BOUNDARY}'


def _crude(url, method, fields, timeout=30):
    body, content_type = _multipart(fields)
    request = urllib.request.Request(
        url, data=body, method=method,
        headers={'Content-Type': content_type})
    try:
        with urllib.request.urlopen(request,
                                    timeout=timeout) as response:
            raw = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        status = exc.code
    except Exception as exc:
        return 0, f'{type(exc).__name__}: {exc}'
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw


def crude_create(base_url, class_name, init_params, timeout=30):
    """POST /<Class> with one initParamSets entry -> (status, body)."""
    return _crude(f'{base_url}/{class_name}', 'POST',
                  {'initParamSets': json.dumps([init_params])},
                  timeout=timeout)


def crude_update(base_url, class_name, polari_id, update_data,
                 timeout=30):
    return _crude(f'{base_url}/{class_name}', 'PUT',
                  {'polariId': polari_id,
                   'updateData': json.dumps(update_data)},
                  timeout=timeout)


def created_id(body, class_name):
    """Pull the new instance's id out of a CRUDE 201 body
    ([{Class: [{class, varsLimited, data:[{...}]}]}])."""
    try:
        entry = body[0][class_name][0]
        return entry['data'][0].get('id')
    except (KeyError, IndexError, TypeError):
        return None
