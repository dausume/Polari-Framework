"""
@module instruments.instruments_page

osc-0: /display/instruments — the instrument models as CARDS (the generic wb-1 `cards` kind, grouped by vendor: channels, bandwidth,
sample rate and memory depth per channel count, resolution, capture rate, transports, emulator, price) over GET /api/instruments, and the
same rows as a configured table underneath with the citation column — so every number on the screen can be traced to its page.
osc-3: three more tabs — ENDPOINTS (a door-form that adds a reachable instrument by a typed address, a door-form that starts the DHO804
emulator in the backend, the endpoints table with "Ask *IDN?" and row-select -> scope `endpoint`), CAPTURE (a door-form that captures the
four channels of the selected endpoint, the captures table with row-select -> scope `acquisition`) and CHART (ONE named-graph-panel over
the GraphDefinition `instruments-capture`, data from /api/instruments/captures/{scope:acquisition}/chart — four series, volts over seconds;
sci-xy-chart underneath, no new chart engine). No raw JSON on screens.
"""
import json

from polariApiServer.module_pages_seed import _page, _row, _table, _tab, _component

_MODELS = '/api/instruments'
_EP = '/api/instruments/endpoints'
_EMU = '/api/instruments/emulators'
_CAPS = '/api/instruments/captures'
_REV = 'rev=r{scope:rev}'
GRAPH = 'instruments-capture'


def model_cards():
    return {'dataPath': _MODELS, 'title_field': 'title', 'subtitle_field': 'family', 'group_by': 'vendor', 'badge_fields': ['kind', 'lineage', 'resolution'],
            'fields': {'Channels': 'channels_text', 'Bandwidth': 'bandwidth', 'Sample rate': 'sample_rate', 'Memory depth': 'memory_depth',
                       'Capture rate': 'capture_rate', 'Sensitivity': 'sensitivity', 'Transports': 'transports', 'Emulator': 'emulator', 'Price': 'price'},
            'empty_text': 'No instrument models on this instance.'}


def _models_tab():
    return _tab('models', 'Models', [
        _row(0, [_component('instrument-cards', 0, 12, 'Instrument models', 'cards', model_cards(),
                            description='One card per model, grouped by vendor. "unverified" means the document was not read, never a guess; '
                                        'the sample rate and memory depth fall as more channels are switched on, so both are given per channel count.')],
             min_height=420),
        _row(1, [_table('instrument-table', 0, 12, 'The same models with their sources', 'Instrument',
                        description='Every number\'s document and page, the command lineage the waveform preamble follows, the *IDN? form, and the LXI statement (unverified until read).',
                        columns='name,vendor,model,kind,channels,bandwidth_hz,resolution_bits,lineage,idn_format,lxi,citation', data_path=_MODELS)],
             min_height=320)],
        description='The oscilloscope models this instance knows, with cited numbers.')


def _endpoint_form():
    return {'fields': [{'name': 'name', 'label': 'Endpoint name (a short key, e.g. bench-scope)', 'required': True},
                       {'name': 'instrument', 'label': 'Model (an Instrument name, e.g. rigol-dho804)', 'required': True},
                       {'name': 'address', 'label': 'Address (host or IP on your LAN - typed here, never stored in a seed)', 'required': True},
                       {'name': 'port', 'label': 'Port (blank = 5555, the raw SCPI socket)'},
                       {'name': 'transport', 'label': 'Transport (scpi-raw | vxi-11 | hislip | usbtmc; blank = scpi-raw)'}],
            'action': {'label': 'Add', 'method': 'POST', 'path': _EP,
                       'body_template': {'name': '{name}', 'instrument': '{instrument}', 'address': '{address}', 'port': '{port}', 'transport': '{transport}'},
                       'then_scope': {'key': 'endpoint', 'from': 'endpoint'}},
            'submit_label': 'Add the instrument', 'success_text': 'Added - it is now the selected endpoint; ask it *IDN? in the table.'}


def _emulator_form():
    return {'fields': [{'name': 'profile', 'label': 'Emulator profile (dho804)', 'required': True},
                       {'name': 'name', 'label': 'Endpoint name (blank = emu-<profile>-<n>)'}],
            'action': {'label': 'Start', 'method': 'POST', 'path': _EMU, 'body_template': {'profile': '{profile}', 'name': '{name}'},
                       'then_scope': {'key': 'endpoint', 'from': 'endpoint'}},
            'submit_label': 'Start an emulated scope', 'success_text': 'Started in the backend on a loopback port - it is now the selected endpoint.'}


def _endpoints_tab():
    return _tab('endpoints', 'Endpoints', [
        _row(0, [_component('instrument-add-endpoint', 0, 6, 'A real instrument on the LAN', 'door-form', _endpoint_form(),
                            description='A reachable unit of a model at an address you type. Nothing is probed until you ask *IDN?.'),
                 _component('instrument-start-emulator', 1, 6, 'An emulated instrument', 'door-form', _emulator_form(),
                            description='Starts the DHO804 emulator inside the backend (osc-2): four channels fed by synthesised signals, answering the Rigol command subset. '
                                        'It identifies itself honestly as POLARI,DHO804-EMU unless the strict knob is set.')], min_height=300),
        _row(1, [_table('instrument-endpoints', 0, 12, 'Endpoints - click one to capture from it', '',
                        description='One row per reachable instrument: transport, address, the last *IDN? answer (or the refusal words) and when it was checked. "Ask *IDN?" talks to it now.',
                        columns='name,instrument,transport,address,port,status,last_idn,checked_at,note', data_path=_EP + '?' + _REV,
                        select_field='name', select_scope='endpoint', selected_value='{scope:endpoint}', empty_text='No endpoints yet - add one or start the emulator.',
                        row_action={'label': 'Ask *IDN?', 'method': 'POST', 'path': _EP + '/{name}/idn', 'body_template': {}})], min_height=260)],
        description='Where the instruments are: typed addresses and started emulators.')


def _capture_form():
    return {'fields': [{'name': 'channels', 'label': 'Channels (comma list, blank = 1,2,3,4)'},
                       {'name': 'max_points', 'label': 'Points per channel (blank = the whole memory depth)'}],
            'action': {'label': 'Capture', 'method': 'POST', 'path': _EP + '/{scope:endpoint}/capture', 'body_template': {'channels_text': '{channels}', 'max_points': '{max_points}'},
                       'then_scope': {'key': 'acquisition', 'from': 'acquisition'}},
            'submit_label': 'Capture one acquisition', 'success_text': 'Captured - the chart tab shows it.'}


def _capture_tab():
    return _tab('capture', 'Capture', [
        _row(0, [_component('instrument-capture', 0, 4, 'Capture from the selected endpoint', 'door-form', _capture_form(),
                            description='One acquisition: the instrument is stopped so every channel is the same shot, then each channel is read in pages (WORD, 12 bits kept) '
                                        'and stored verbatim with its preamble and sha256.'),
                 _table('instrument-captures', 1, 8, 'Captures - click one to chart it', '',
                        description='One row per channel per acquisition: points, sample rate, span, the block\'s sha256, where the bytes are kept, and the source that produced an emulated one.',
                        columns='acquisition,channel,endpoint,points,sample_rate,span_s,v_min,v_max,v_mean,stored,source,source_ref,raw_sha256', data_path=_CAPS + '?' + _REV,
                        select_field='acquisition', select_scope='acquisition', selected_value='{scope:acquisition}', empty_text='No captures yet.')], min_height=320)],
        description='Read the channels of the selected endpoint into capture rows.')


def _chart_tab():
    return _tab('chart', 'Chart', [
        _row(0, [{'id': 'instrument-chart', 'index': 0, 'type': 'component', 'rowSegmentsUsed': 12, 'gridColumnStart': None, 'title': 'The selected acquisition - four channels',
                  'description': 'Volts over seconds for every channel of the selected acquisition, recomputed from the stored block and preamble (never from stored floats); '
                                 'decimated by a plain stride to at most 4000 points per channel for the screen - every drawn point is a real sample.',
                  'visible': True, 'collapsed': False, 'cssClass': '',
                  'componentProps': {'componentName': 'named-graph-panel', 'inputs': {'graphName': GRAPH, 'dataPath': _CAPS + '/{scope:acquisition}/chart?max=4000&' + _REV}},
                  'item': None, 'nestedRows': []}], min_height=420)],
        description='The waveform view.')


def _graph_config():
    return {'renderStyle': 'lineY', 'xDimension': 't_s', 'yDimensions': ['ch1', 'ch2', 'ch3', 'ch4'],
            'seriesColors': ['#e6b800', '#1fa8c9', '#d63fa0', '#3b5bdb'],       # the DHO's channel colours by eye (yellow, cyan, magenta, blue) - a convention, not data
            'options': {'width': 900, 'height': 360, 'marginTop': 20, 'marginRight': 30, 'marginBottom': 40, 'marginLeft': 60,
                        'showLegend': True, 'showGrid': True, 'xLabel': 'time from trigger (s)', 'yLabel': 'volts'},
            'aggregation': {'enabled': False, 'strategy': 'average'}}


SEED_INSTRUMENTS_GRAPHS = [{
    'name': GRAPH, 'source_class': 'WaveformCapture',
    'description': 'One acquisition of an oscilloscope endpoint: ch1..ch4 in volts over seconds from the trigger, recomputed from each channel\'s stored block + preamble '
                   'by its lineage\'s formula (instruments.custom.lineage). Data: GET /api/instruments/captures/{acquisition}/chart.',
    'definition': json.dumps({'graphConfig': _graph_config()})}]


SEED_INSTRUMENTS_PAGE_DISPLAYS = [
    _page('instruments', 'instruments',
          'Bench instruments: oscilloscope models with cited specifications (the RIGOL DHO800 family first), the two biggest makers as lineage rows until one of their '
          'models has its datasheet read, reachable endpoints (typed addresses or the emulator started here), captures kept verbatim, and the four-channel chart. '
          'Doors: /api/instruments, /api/instruments/endpoints|emulators|captures. The workbench (/display/workbench, step 4) picks from the model cards.',
          'Instrument', [], title='Instruments', tabs=[_models_tab(), _endpoints_tab(), _capture_tab(), _chart_tab()]),
]
