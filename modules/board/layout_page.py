"""
@module board.layout_page

lay-2 (PROTOTYPING_VIEWS_PLAN.md section 3): `/display/layout?config=&board=` - the build laid out on a breadboard, drawn by the ONE sanctioned layout component
(`hardware-layout-view`, D-ptv-1) in BUILD mode, with the tables beside it as configured tables (no raw JSON):

    Layout tab   the picture (step mode: previous / next, the step's text, "whole build") | the build steps as a table | the gate's verdict as a table |
                 the wire-colour schemes (copy before editing: the row action of the scores page) | the boards on the bench (pick one to lay the build on it)
    Boards tab   the board models (breadboard half / full, the UNO, the reserved protoboard and pcb), with their derived tie counts

The page SCOPE: the component announces `config` and `board` (from `?config=` / `?board=` or its defaults); the tables read `{scope:config}` / `{scope:board}`. Picking a wire-colour
scheme sets scope `scheme` (the picture is drawn in it), picking a bench board sets scope `board`. A click on a hole or a part sets scope `net` / `component`
(sibling views follow). Every scope change is applied IN PLACE on a tabbed page (the picture keeps its zoom and step), which is why the page is tabbed.
"""
from polariApiServer.module_pages_seed import _layout_view, _page, _row, _tab, _table

ROUTE = 'layout'
DEFAULT_CONFIG = 'uno-light'

_TEXT = ('Layout - where each part and wire goes on the breadboard, drawn from the real geometry of the boards: the Arduino UNO\'s headers on top, the breadboard below with its numbered '
         'strips (rows 1, 2, 3 ...), the holes a to e on the left of the centre trench and f to j on the right, and the power rails along both long edges. Parts are drawn as small '
         'pictures built from their values (a resistor\'s colour bands come from its ohms; an LED shows its flat side and its longer leg; the pushbutton sits across the trench). '
         'Wires are curves in the colour of the chosen wire-colour scheme (a wire\'s own colour wins). Click a hole to see its net and what else sits on that strip; click a part '
         'or a wire to see its row; click again, or press Escape, to clear. Step mode walks the build one step at a time: step k shows steps 1 to k, the new part or wire is '
         'highlighted and the rest dimmed; the step stays in the address (?step=). "Whole build" shows everything. Drag to pan, scroll to zoom, Fit to see it all. The tables beside the picture '
         'are the same build as words: the steps, the verdict of the netlist gate (the layout\'s nets must EQUAL the design\'s nets), the wire colours and the boards.')

_STEPS_COLS = 'step,kind,title,text'
_VERDICT_COLS = 'status,check,subject,words'


def _build_rows():
    return [
        _row(0, [_layout_view('lay-view', 0, 12, 'Layout - the build on the bench', _TEXT, mode='build', config=DEFAULT_CONFIG)], min_height=620),
        _row(1, [
            _table('lay-steps', 0, 6, 'Build steps', '', data_path='/api/layout/steps?config={scope:config}&board={scope:board}&scheme={scope:scheme}',
                   empty_text='Opening the layout... (the steps appear when the picture has said which config it shows)',
                   description='What this is for: the build as words, in the order to do it. One row = one step. step is its number (the picture\'s Step control shows the same steps), kind says what '
                               'the step does (unplug, rails, part, wire, check), title names it and text says exactly which holes and which colour. The steps are worked out from the design '
                               'every time and never typed in.',
                   columns=_STEPS_COLS, max_height=520),
            _table('lay-verdict', 1, 6, 'Does the layout make the design? - the netlist gate', '', data_path='/api/layout/verdict?config={scope:config}&board={scope:board}&scheme={scope:scheme}',
                   empty_text='Opening the layout... (the verdict appears when the picture has said which config it shows)',
                   description='What this is for: the proof that the wiring on the board makes exactly the circuit that was designed. One row = one check. The first row is the whole verdict; then one row per '
                               'design net (equal = the layout joins exactly the same terminals, wrong = it does not, and the words say which); then one row per electrical rule (LED polarity, a series '
                               'resistor, ...). status ok / equal means it holds; refused / wrong means the build must not be powered.',
                   columns=_VERDICT_COLS, max_height=520)], css_class='side-by-side', min_height=300),
        _row(2, [
            _table('lay-colours', 0, 7, 'Wire colours - pick a scheme to draw the wires in it', '', data_path='/api/layout/wire-colors?rev=r{scope:rev}',
                   select_field='name', select_scope='scheme', selected_value='{scope:scheme}',
                   description='What this is for: the colour convention the wires are drawn in. One row = one wire-colour scheme; click a row to draw the picture in it (click again to go back to the default). '
                               'The seeded scheme is read-only: press "Copy to edit" to make your own copy (named my- followed by its name), then change its colours with `pol board wire-colors set` '
                               '- the copy can be edited, the seeded one never is. colors_text lists which colour each kind of wire takes; a single wire can also carry its own colour, which wins.',
                   columns='name,display_name,description,seeded,colors_text',
                   row_action={'label': 'Copy to edit', 'method': 'POST', 'path': '/api/layout/wire-colors', 'show_when_field': 'seeded',
                               'body_template': {'name': 'my-{name}', 'copy_of': '{name}'}, 'then_scope': {'key': 'scheme', 'from': 'name'}}, max_height=360),
            _table('lay-boards', 1, 5, 'Boards on the bench - pick one to lay the build on it', '', data_path='/api/layout/boards',
                   select_field='name', select_scope='board', selected_value='{scope:board}',
                   description='What this is for: the boards the build can be laid on. One row = one physical board on the bench: its model (a half breadboard has 400 tie points, a full one 830), what kind it is, '
                               'its label and how many tie points it has. Click a breadboard to lay the build on it; the UNO is the board the wires start from. A layout is placed on breadboards so far '
                               '(protoboard and pcb are reserved).',
                   columns='name,model,kind,label,ties,default', max_height=360)], css_class='side-by-side', min_height=300),
    ]


def _boards_rows():
    return [_row(0, [_table('lay-models', 0, 12, 'Board models - the geometry each kind of board is drawn from', '', data_path='/api/layout/models',
                            description='What this is for: the board family the picture draws from. One row = one kind of board. rows is the number of numbered strips, rail_holes the holes in each power rail, '
                                        'pitch_mm the hole spacing (2.54 mm), nominal_ties the sold tie-point count and derived_ties the count worked out from the geometry (ties_agree says they match). '
                                        'status reserved means no geometry is built yet: a layout on it is refused in words.',
                            columns='name,kind,size,status,rows,rail_holes,pitch_mm,nominal_ties,derived_ties,ties_agree,description')], min_height=320)]


LAYOUT_PAGES = [
    _page(ROUTE, ROUTE, _TEXT, 'BoardPin', [], title='Layout',
          tabs=[_tab('layout', 'Layout', _build_rows(), 'The build on the bench: the picture, its steps, its verdict, its wire colours and its boards.'),
                _tab('boards', 'Board models', _boards_rows(), 'The geometry of every board kind the picture can draw.')]),
]
