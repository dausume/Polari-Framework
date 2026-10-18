"""
@module board.profile_overlap_page

pp-1: /display/profile-overlap - "Profile overlap": which kinds of pin need may share ONE pin, ONE net (two pins wired together) or ONE peripheral on the
ATmega328P, every verdict cited to a datasheet section and page or to an existing rule, plus the co-location of the light Mission. CONFIGURED
tables over the doors (no raw JSON, no new component): GET /api/board/socs/atmega328p/profile-overlap and GET /api/missions/uno-light-mission/colocation.
"""
from polariApiServer.module_pages_seed import _page, _row, _table

_API = '/api/board/socs/atmega328p/profile-overlap'
_MIS = '/api/missions/uno-light-mission/colocation'
_COLS = 'pair,verdict,mode,condition,reason,rule,cite,common_pins'

PROFILE_OVERLAP_PAGES = [
    _page('profile-overlap', 'profile-overlap',
          'Profile overlap - which pin needs may share. Two needs (a digital output, an interrupt input, a PWM output, the USB transport ...) may be put on ONE pin, on two pins '
          'WIRED TOGETHER (one net) or on ONE peripheral block (two channels of a timer). Each pair has a verdict: compatible, exclusive, conditional (it works only if the '
          'condition holds) or undetermined (the datasheet does not settle it - the reason says why). Every row cites the datasheet section and page, or the existing rule it '
          'reuses (one output per net, the claims rules, the board\'s reserved transport pins). The `mode` says how they share: exclusive, shared-read (both read the pin), '
          'shared-config (they share settings) or time-multiplexed-later (take turns - a later claim mode). The last tables apply it to the light Mission. '
          'From the command line: pol board overlap uno, pol capability colocation <mission>.',
          'BoardDefinition', [
              _row(0, [_table('po-pin', 0, 12, 'On ONE pin - two needs on the same physical pin', '',
                              description='What this is for: can two roles use one pin? One row = one pair of kinds. Columns: verdict, mode, condition (what must hold when conditional), reason, '
                                          'rule (the rule that decided), cite (datasheet section and page, or the code rule), common_pins (the pins that offer both kinds). GET %s?scope=pin.' % _API,
                              columns=_COLS, data_path='%s?scope=pin' % _API)]),
              _row(1, [_table('po-net', 0, 12, 'On ONE net - two pins wired together', '',
                              description='What this is for: can two pins be wired to each other? One output plus any number of inputs is fine; two outputs are refused (rule single_output). '
                                          'One row = one pair of kinds. GET %s?scope=net.' % _API,
                              columns='pair,verdict,mode,condition,reason,rule,cite', data_path='%s?scope=net' % _API)]),
              _row(2, [_table('po-peripheral', 0, 12, 'On ONE peripheral - the same block serving two needs', '',
                              description='What this is for: two needs served by one block (the timer\'s two compare channels, the USART\'s receive and transmit sides). `applies` says whether the two '
                                          'kinds share a block at all; pairs on different blocks are compatible with nothing to share. GET %s?scope=peripheral.' % _API,
                              columns='pair,applies,verdict,mode,condition,reason,rule,cite', data_path='%s?scope=peripheral' % _API)]),
              _row(3, [_table('po-mission-groups', 0, 12, 'The light Mission - which needs can share a pin, and the fewest pins', '',
                              description='What this is for: the light Mission\'s pin needs (Pin profiles page) grouped by the table. One row = one pin group; `shared` yes means several needs on one pin, '
                                          'with the pins that offer them and the conditions. GET %s?view=groups.' % _MIS,
                              columns='group,shared,pin_options,as,conditions,reserved', data_path='%s?view=groups' % _MIS)]),
              _row(4, [_table('po-mission-apart', 0, 12, 'The light Mission - pairs that cannot share, and why', '',
                              description='What this is for: the needs forced apart (the button and the LED cannot share a pin, the transport pins are reserved). GET %s?view=apart.' % _MIS,
                              columns='pair,scope,verdict,why,cite', data_path='%s?view=apart' % _MIS)]),
              _row(5, [_table('po-kinds', 0, 12, 'The kinds - what each one is and which pins offer it', '',
                              description='What this is for: the vocabulary of the table. One row = one kind: which side of a wire it is on, the peripheral it uses, the pins that offer it. '
                                          'GET %s?list=kinds.' % _API,
                              columns='kind,title,side,peripherals,pins', data_path='%s?list=kinds' % _API)]),
              _row(6, [_table('po-rules', 0, 12, 'The rules - how many verdicts each rule decides, and what it cites', '',
                              description='What this is for: audit. One row = one rule; `rows` is how many table rows it decides, `cite` every source it stands on. GET %s?list=rules.' % _API,
                              columns='rule,rows,reason,cite,example', data_path='%s?list=rules' % _API)]),
          ], title='Profile overlap'),
]
