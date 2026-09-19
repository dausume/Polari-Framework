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
    outcome; `why` says it in one sentence.

    ct-5 (design §7) adds ONE column, `payload`: *what* crosses. The os /
    network / app views leave it empty — they answer who can reach what — and
    the `objects` view fills it with the CLASSES an edge carries and how often
    (`MealEntry×12`). Class names and counts only: an instance id never appears
    on a topology, and the effect journal is where one is looked up."""

    @treeObjectInit
    def __init__(self, name: str = '', view: str = '', scenario: str = '', mode: str = 'complain',
                 source: str = '', target: str = '', means: str = '', chain: str = '', decided_by: str = '',
                 provenance: str = '', verdict: str = 'allowed', why: str = '', payload: str = ''):
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
        self.payload = payload      # ct-5: the CLASSES this edge carries, with counts ('' on the other views)
