"""
@module firmwarefaults.objects.evidence.StaticFinding

StaticFinding — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StaticFinding(treeObject):
    """What it is: One finding of a StaticCheck (sc-2b): the checker's id, severity, message, CWE, file and line in the
    variant's generated project. A row to read and triage — never a build failure.
    Related concepts: `StaticCheck`, `FirmwareVariant`.
    """

    plain_words = ('A static finding is one thing a rule checker noticed in the firmware source, with the file and line.')

    @treeObjectInit
    def __init__(self, name: str = '', check_name: str = '', variant: str = '', tool: str = 'cppcheck', check_id: str = '', severity: str = '',
                 message: str = '', cwe: int = 0, file: str = '', line: int = 0, symbol: str = '', addon: str = '', manager=None):
        self.name = name
        # fw-2: named `check_name`, not `check` — `check` is a SQLite reserved word and broke
        # CREATE TABLE for this class ('near "check": syntax error'); rows never persisted.
        self.check_name = check_name  # the StaticCheck name
        self.variant = variant
        self.tool = tool
        self.check_id = check_id  # cppcheck's id (e.g. unusedFunction, threadsafety-unsafe-call)
        self.severity = severity  # error | warning | style | portability | performance
        self.message = message
        self.cwe = cwe
        self.file = file
        self.line = line
        self.symbol = symbol
        self.addon = addon
