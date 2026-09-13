"""
@module security.objects.security.FirewallRuleSet

Row class FirewallRuleSet of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FirewallRuleSet(treeObject):
    """The rendered rules of one chain for one scenario (DOCKER-USER, ufw, the swarm ports) and whether an audit run found them applied."""

    @treeObjectInit
    def __init__(self, name: str = '', scenario: str = '', chain: str = '', rules: str = '', rule_count: int = 0, applied: str = 'unknown', sources_resolved: bool = False, artifact: str = ''):
        self.name = name
        self.scenario = scenario
        self.chain = chain
        self.rules = rules
        self.rule_count = rule_count
        self.applied = applied
        self.sources_resolved = sources_resolved
        self.artifact = artifact
