"""
@module security.objects.security.SecurityTopologyEdge

Row class SecurityTopologyEdge — one reach attempt in a view: source → target by a means, the chain of systems that decide, the verdict.
"""
from objectTreeDecorators import treeObject, treeObjectInit

VERDICTS = ('allowed', 'logged', 'blocked')


class SecurityTopologyEdge(treeObject):
    """The unit of the simulation. `means` is what the source tries (write its
    image, mount, connect the docker socket, reach sshd, log in, sudo …);
    `chain` lists in order the systems consulted and each one's decision under
    the row's `mode` (stock = only what docker/qemu give; complain = Polari's
    rings loaded warn-only, today; enforce = every Polari ring on); `decided_by`
    is the first system that blocks, or the one that logs; `verdict` is the
    outcome; `why` says it in one sentence."""

    @treeObjectInit
    def __init__(self, name: str = '', view: str = '', scenario: str = '', mode: str = 'complain',
                 source: str = '', target: str = '', means: str = '', chain: str = '', decided_by: str = '',
                 provenance: str = '', verdict: str = 'allowed', why: str = ''):
        self.name = name
        self.view = view
        self.scenario = scenario
        self.mode = mode
        self.source = source
        self.target = target
        self.means = means
        self.chain = chain
        self.decided_by = decided_by
        self.provenance = provenance
        self.verdict = verdict
        self.why = why
