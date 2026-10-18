"""
@module cmod.cmod_template_api

ed-0 doors (contract in cmod.custom.editor.doors): GET /api/cmod/templates and GET /api/cmod/templates/{tid:path}. The id is a nested path, so the
route uses Falcon's `path` converter; the literal `templates` segment is its own, so no CModAPI route ({atom}/{tail}, graphs/{graph}) can shadow it.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TemplateAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/cmod/templates', self, suffix='templates')
            add('/api/cmod/templates/{tid:path}', self, suffix='template_one')

    def on_get_templates(self, request, response):
        from cmod.custom.editor import doors as D
        D.get_list(self, request, response)

    def on_get_template_one(self, request, response, tid):
        from cmod.custom.editor import doors as D
        D.get_one(self, request, response, tid)
