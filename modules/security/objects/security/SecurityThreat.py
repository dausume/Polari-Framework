"""
@module security.objects.security.SecurityThreat

Row class SecurityThreat — one threat played on the topology for one scenario, with the policy that blocked it and the counterexample.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SecurityThreat(treeObject):
    """A named threat (an actor, a means, a target from one of the three views) resolved against a scenario
    and a mode: the verdict, the system that blocked it and the policy line it applied, and beside it the
    COUNTEREXAMPLE — which actor, group or permission legitimately reaches the same target, by what means,
    and whether that path is open on this route. Seeded from security_threats for every scenario at today's
    mode; the simulation panel (/display/security-threats) animates the same rows live from the API."""

    @treeObjectInit
    def __init__(self, name: str = '', threat: str = '', view: str = '', scenario: str = '', mode: str = 'today', title: str = '',
                 actor: str = '', means: str = '', target: str = '', verdict: str = '', blocked_by: str = '', policy: str = '',
                 counter_actor: str = '', counter_group: str = '', counter_means: str = '', counter_verdict: str = '', story: str = ''):
        self.name = name
        self.threat = threat
        self.view = view
        self.scenario = scenario
        self.mode = mode
        self.title = title
        self.actor = actor
        self.means = means
        self.target = target
        self.verdict = verdict
        self.blocked_by = blocked_by
        self.policy = policy
        self.counter_actor = counter_actor
        self.counter_group = counter_group
        self.counter_means = counter_means
        self.counter_verdict = counter_verdict
        self.story = story
