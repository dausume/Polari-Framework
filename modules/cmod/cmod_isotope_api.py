"""
@module cmod.cmod_isotope_api

Isotope variant doors (iso-0): the model is pure (`cmod.custom.isotope_variants`, `cmod.custom.isotope_variants_eligibility`) and the work is in
`cmod.custom.isotope_variants_doors`; this API only registers the routes. Contracts are in isotope_variants_doors.py:

GET /api/atom-jobs · GET /api/atom-jobs/{job}/variants[?board=&tier=] · GET /api/atom-variants[?board=&tier=]
"""
from objectTreeDecorators import treeObject, treeObjectInit


class IsotopeVariantAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/atom-jobs', self, suffix='jobs')
            add('/api/atom-jobs/{job}/variants', self, suffix='job_variants')
            add('/api/atom-variants', self, suffix='all_variants')

    def on_get_jobs(self, request, response):
        from cmod.custom import isotope_variants_doors as D
        D.jobs_table(self, request, response)

    def on_get_job_variants(self, request, response, job):
        from cmod.custom import isotope_variants_doors as D
        D.job_variants(self, request, response, job)

    def on_get_all_variants(self, request, response):
        from cmod.custom import isotope_variants_doors as D
        D.all_variants(self, request, response)
