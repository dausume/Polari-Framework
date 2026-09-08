"""
Selftest — acct-2: golden shapes for the four specialized JSON
formats (the per-format pins the matrix carries as
selftest:testing.formats, category `format`).

Run from polari-framework/:
    python3 -m testing.formats_selftest

For one reference class saved through the real DB seam, each
format's exact shape is asserted so drift fails LOUDLY:
  polariTree  manager.getJSONdictForClass -> [{class, varsLimited,
              data}] (the CRUDE body wraps this as [{ClassName: …}]).
  flatJson    /flat/<Class> -> bare array of flat row dicts.
  d3Column    /d3/<Class> -> {columns, data(column-major), length}.
  geoJson     /geojson/<Class> -> RFC 7946 FeatureCollection with
              Point coordinates in [lng, lat] ORDER (the classic
              swap bug is pinned here), driven by a
              GeoJsonDefinition (source_class + geoJsonConfig).
Also pins the knobs: formats are DISABLED by default (a disabled
format 404s honestly), and getActiveWsTopics builds the
/topic/<Class>[/<fmt>] names the STOMP leg delivers on.
"""

import json
import os
import sys

import falcon
from falcon import testing as falcon_testing

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from objectTreeDecorators import treeObject, treeObjectInit

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


class Acct2FormatProbe(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', label: str = '',
                 lat: float = 0.0, lng: float = 0.0, manager=None):
        self.name = name
        self.label = label
        self.lat = lat
        self.lng = lng


def _booted_manager():
    from objectTreeManagerDecorators import managerObject
    manager = managerObject(hasDB=True)
    table = 'Acct2FormatProbe'
    if table in (manager.db.tables or []):
        manager.db.dropTable(table)
    manager.db.makeSQLiteTable(tableName=table, rowList=[
        'name TEXT PRIMARY KEY', 'label TEXT', 'lat REAL',
        'lng REAL'])
    manager.getObjectTyping(classObj=Acct2FormatProbe)
    rows = [
        Acct2FormatProbe(manager=manager, name='alpha',
                         label='first', lat=45.5, lng=-122.6),
        Acct2FormatProbe(manager=manager, name='beta',
                         label='second', lat=51.5, lng=-0.1),
    ]
    for row in rows:
        manager.db.saveInstanceInDB(row)
    return manager, rows


def _client_for(api, path):
    app = falcon.App()
    app.add_route(path, api)
    return falcon_testing.TestClient(app)


def _polaritree(manager, rows):
    print('polariTree (in-memory tree render)')
    payload = manager.getJSONdictForClass(passedInstances=[rows[0]])
    check('render is a one-element list', isinstance(payload, list)
          and len(payload) == 1)
    entry = payload[0] if payload else {}
    check('golden keys {class, varsLimited, data}',
          set(entry) >= {'class', 'varsLimited', 'data'},
          str(sorted(entry))[:80])
    check('class name + instance data carried',
          entry.get('class') == 'Acct2FormatProbe'
          and any(d.get('name') == 'alpha'
                  for d in entry.get('data', [])))


def _format_config(manager):
    typing = manager.objectTypingDict['Acct2FormatProbe']
    if getattr(typing, 'apiFormatConfig', None) is None:
        # Same lazy init runAnalysis() performs on the live path.
        from polariApiServer.apiFormatConfig import ApiFormatConfig
        typing.apiFormatConfig = ApiFormatConfig(
            polyTypedObj=typing, manager=manager)
    # The DB-backed format APIs check read access; with no polServer
    # (no CRUDE perms to delegate to) they fall back to the typing's
    # baseAccessDictionary — grant R the way a served class would.
    typing.baseAccessDictionary = {'R': ['anyone']}
    config = typing.apiFormatConfig
    check('typing carries an ApiFormatConfig', config is not None)
    return config


def _knob_defaults(config):
    print('format knobs (disabled by default)')
    check('polariTree always enabled',
          getattr(config, 'polariTreeEnabled', False))
    check('flatJson/d3Column/geoJson default DISABLED',
          not config.flatJsonEnabled and not config.d3ColumnEnabled
          and not config.geoJsonEnabled)


def _flatjson(manager):
    print('flatJson golden shape')
    from polariApiServer.configuredFormattedAPIs.flatJsonAPI import (
        FlatJsonAPI,
    )
    api = FlatJsonAPI(apiObject='Acct2FormatProbe', polServer=None,
                      manager=manager)
    client = _client_for(api, '/flat/Acct2FormatProbe')
    config = manager.objectTypingDict[
        'Acct2FormatProbe'].apiFormatConfig
    disabled = client.simulate_get('/flat/Acct2FormatProbe')
    check('disabled format 404s honestly',
          disabled.status_code == 404)
    config.flatJsonEnabled = True
    result = client.simulate_get('/flat/Acct2FormatProbe')
    body = result.json
    check('enabled: bare array of flat dicts',
          result.status_code == 200 and isinstance(body, list)
          and len(body) == 2 and all(isinstance(r, dict)
                                     for r in body))
    by_name = {r.get('name'): r for r in body}
    check('flat rows carry the columns',
          by_name.get('alpha', {}).get('label') == 'first'
          and abs(by_name.get('beta', {}).get('lat', 0)
                  - 51.5) < 1e-9)
    return by_name


def _d3column(manager):
    print('d3Column golden shape')
    from polariApiServer.configuredFormattedAPIs.d3ColumnAPI import (
        D3ColumnAPI,
    )
    api = D3ColumnAPI(apiObject='Acct2FormatProbe', polServer=None,
                      manager=manager)
    client = _client_for(api, '/d3/Acct2FormatProbe')
    manager.objectTypingDict[
        'Acct2FormatProbe'].apiFormatConfig.d3ColumnEnabled = True
    body = client.simulate_get('/d3/Acct2FormatProbe').json
    check('golden keys {columns, data, length}',
          set(body) >= {'columns', 'data', 'length'},
          str(sorted(body))[:60])
    check('column-major data with matching length',
          body.get('length') == 2
          and body.get('data', {}).get('name')
          in (['alpha', 'beta'], ['beta', 'alpha']))


def _geojson(manager):
    print('geoJson golden shape (RFC 7946)')
    from polariApiServer.configuredFormattedAPIs.geoJsonAPI import (
        GeoJsonAPI,
    )
    from polariApiServer.geoJsonDefinition import GeoJsonDefinition
    manager.getObjectTyping(classObj=GeoJsonDefinition)
    GeoJsonDefinition(
        manager=manager, name='acct2-probe-geo',
        source_class='Acct2FormatProbe',
        definition=json.dumps({'geoJsonConfig': {
            'coordinateMode': 'separate',
            'latitudeVariable': 'lat',
            'longitudeVariable': 'lng'}}))
    api = GeoJsonAPI(apiObject='Acct2FormatProbe', polServer=None,
                     manager=manager)
    client = _client_for(api, '/geojson/Acct2FormatProbe')
    manager.objectTypingDict[
        'Acct2FormatProbe'].apiFormatConfig.geoJsonEnabled = True
    body = client.simulate_get('/geojson/Acct2FormatProbe').json
    check('FeatureCollection with two features',
          body.get('type') == 'FeatureCollection'
          and len(body.get('features', [])) == 2)
    feature = next((f for f in body.get('features', [])
                    if f.get('properties', {}).get('name')
                    == 'alpha'), {})
    geometry = feature.get('geometry', {})
    check('Point geometry in [lng, lat] order (the swap pin)',
          geometry.get('type') == 'Point'
          and geometry.get('coordinates') == [-122.6, 45.5],
          str(geometry.get('coordinates')))
    check('properties carry the full row',
          feature.get('properties', {}).get('label') == 'first')


def _ws_topics(config):
    print('websocket topic construction')
    config.polariTreeWsEnabled = True
    config.flatJsonWsEnabled = True
    topics = set(config.getActiveWsTopics())
    check('topics follow /topic/<Class>[/<fmt>]',
          {'/topic/Acct2FormatProbe',
           '/topic/Acct2FormatProbe/flatJson'} <= topics,
          str(sorted(topics)))


if __name__ == '__main__':
    manager, rows = _booted_manager()
    _polaritree(manager, rows)
    config = _format_config(manager)
    if config is not None:
        _knob_defaults(config)
        _flatjson(manager)
        _d3column(manager)
        _geojson(manager)
        _ws_topics(config)
    manager.db.dropTable('Acct2FormatProbe')
    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
