"""
@module cmod.objects.cmod.ConfigVerdict

ConfigVerdict - one class per file (design section 7); cfg-0 (AI-Notes/plans/CATOM_CONFIG_PLAN.md "Three verdicts and the default").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ConfigVerdict(treeObject):
    """What it is: WHETHER ONE OPTION WORKS IN ONE BENCH SOLUTION - invalid (cannot work; never chosen automatically, refused at build), compromise
    (works but gives something up) or ideal (every check with the full recommended margin) - and its competitive score among the valid options of
    its group (best = 100, worst = 0). Written by the checks (cmod.custom.catom_config.evaluate), never typed. The evidence is one level down: one
    `ConfigCheckResult` per check. The catom and the configuration are not copied here: the option names the catom, the Bench Solution names
    the firmware solution.
    Related concepts: `BenchSolution`, `ConfigOption`, `ConfigCheckResult`, `ConfigChoice`.
    """

    plain_words = ('A configuration verdict says whether one candidate setting works on one bench - no, yes with a cost, or yes fully - '
                   'and how it scored against the others.')

    @treeObjectInit
    def __init__(self, name: str = '', bench_solution: str = '', option: str = '', verdict: str = '', score: float = 0.0, why: str = '',
                 manager=None):
        self.name = name                      # '<bench_solution>|<option>'
        self.bench_solution = bench_solution  # a BenchSolution name
        self.option = option                  # a ConfigOption name
        self.verdict = verdict                # invalid | compromise | ideal
        self.score = score                    # 0..100 among the valid options of the group; 0 when invalid
        self.why = why
