"""
@module electrodevice.custom.layout_words

lay-1: the refusal type of the layout engine and the few plain-words helpers its text shares. A refusal is never a stack trace: it carries the words (and a status
the door answers with).
"""


class LayoutRefused(ValueError):
    """A layout request refused in plain words. `status` is the HTTP status the door answers with (404 unknown, 409 conflicting, 422 cannot be built)."""

    def __init__(self, words, status=422, findings=None):
        super().__init__(words)
        self.status = status
        self.findings = findings or []


def hole_words(tie):
    """'r14e' -> 'row 14, hole e'; 'rail:top:-:3' -> 'the top - rail, hole 3'; a header label -> 'pin D6'."""
    from electrodevice.custom import board_family as BF
    p = BF.parse_tie(tie)
    if p is None:
        return 'pin %s' % tie
    if p[0] == 'hole':
        return 'row %d, hole %s' % (p[1], p[2])
    if p[0] == 'rail':
        return 'the %s %s rail, hole %d' % (p[1], 'ground (-)' if p[2] == '-' else 'supply (+)', p[3])
    if p[0] == 'strip':
        return 'row %d, %s side' % (p[1], 'left' if p[2] == 'L' else 'right')
    return tie


def a_an(word):
    """'a black', 'an orange'."""
    return ('an ' if word[:1] in 'aeiou' else 'a ') + word


def join_words(items):
    items = list(items)
    if len(items) <= 1:
        return ''.join(items)
    return ', '.join(items[:-1]) + ' and ' + items[-1]
