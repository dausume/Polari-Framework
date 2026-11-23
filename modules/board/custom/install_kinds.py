"""
@module board.custom.install_kinds

ins-c3-1 (AI-Notes/plans/C3_INSTALL_PLAN.md): what differs between the boards the firmware installer can put a program on. installer.py asks here which board a
variant, a build or a target belongs to and names no board itself beyond the UNO's own steps, which stay in installer.py ('steps' = '').

    of_board(board) / of_alias(word)   the kind of a board definition name / of the word a person types (uno, c3, esp32c3 ...), or None
    of_twin(instance)                  the kind of a twin target ('twin:<board>'; 'twin' alone is the UNO: the old spelling), or None
    of_variant(config)                 a C3 firmware variant -> C3, anything else -> UNO (the same rule as twin_kinds.of)
    of_build(b)                        by the build's board_definition; the UNO when it is unknown
    steps(kind)                        the module with that board's own installer steps (board.custom.install_c3), or None for the UNO
"""
import importlib

from board.custom import gen_c3, twin_kinds, variants_c3 as V3

_UNO_BOARD = twin_kinds.AVR['board']

UNO = {'name': 'uno', 'board': _UNO_BOARD, 'twin': 'twin:%s' % _UNO_BOARD, 'aliases': ('uno', _UNO_BOARD), 'label': 'UNO', 'artifact': '.hex',
       'programmer': 'avrdude', 'default_variant': 'uno-sim-rig', 'steps': ''}   # '' = the installer's own UNO functions
C3 = {'name': 'c3', 'board': V3.BOARD, 'twin': 'twin:%s' % V3.BOARD, 'aliases': tuple(gen_c3.ALIASES), 'label': 'ESP32-C3', 'artifact': 'flash image',
      'programmer': 'esptool', 'default_variant': V3.LIGHT_NAME, 'steps': 'board.custom.install_c3'}
KINDS = (UNO, C3)


def of_board(board):
    return next((k for k in KINDS if k['board'] == board), None)


def of_alias(word):
    w = str(word or '').strip().lower()
    return next((k for k in KINDS if w in k['aliases'] or w == k['board']), None)


def of_twin(instance):
    s = str(instance or '')
    if s == 'twin':
        return UNO
    return of_board(s[len('twin:'):]) if s.startswith('twin:') else None


def of_variant(config):
    return C3 if config in V3.VARIANT_NAMES else UNO


def of_build(b):
    board = b.get('board_definition') if isinstance(b, dict) else getattr(b, 'board_definition', '')
    return of_board(board) or UNO


def steps(kind):
    return importlib.import_module(kind['steps']) if kind['steps'] else None
