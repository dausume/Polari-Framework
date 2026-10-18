"""
@module cmod.cmod_task_plan_api

fgm-3 doors (contract in cmod.custom.task_plan_doors): GET/POST /api/missions/{name}/task-plan and POST /api/task-plans/{plan}/also-runs-on. Own class, own file - they sit beside mis-0's
/solution|/resolution, pp-0's /pin-profiles, rt-0's /approach and sol-0's /solve (same depth, literal last segment, same {name} field).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TaskPlanAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/missions/{name}/task-plan', self, suffix='task_plan')
            add('/api/task-plans/{plan}/also-runs-on', self, suffix='also_runs_on')

    def on_get_task_plan(self, request, response, name):
        from cmod.custom import task_plan_doors as D
        D.get_plan(self, request, response, name)

    def on_post_task_plan(self, request, response, name):
        from cmod.custom import task_plan_doors as D
        D.post_plan(self, request, response, name)

    def on_post_also_runs_on(self, request, response, plan):
        from cmod.custom import task_plan_doors as D
        D.post_also_runs_on(self, request, response, plan)
