"""@module printing_suite.printing_suite_api — /api/printing-suite/summary: the pipeline as counts + the suite's placement."""
import falcon  # noqa: F401
from objectTreeDecorators import treeObject, treeObjectInit


class PrintingSuiteAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/printing-suite/summary', self, suffix='summary')

    def _rows(self, class_name):
        return list(((self.manager.objectTables or {}).get(class_name, {}) or {}).values())

    def on_get_summary(self, request, response):
        counts = {c: len(self._rows(c)) for c in ('ImportedCadObject', 'MathShapeDefinition', 'MoldDefinition', 'Material', 'MaterialLot',
                                                  'PrintProfile', 'SliceJob', 'GcodeArtifact', 'PrintJob', 'PrintOutcome', 'PrinterDefinition')}
        jobs = self._rows('PrintJob')
        response.media = {'ok': True, 'pipeline': counts,
                          'printing': [{'job': j.name, 'printer': j.printer, 'state': j.state, 'progressPct': j.progress_pct} for j in jobs if j.state in ('printing', 'paused')],
                          'placement': '/api/suiteapps/printing-production',
                          'note': 'shape → mold → profile → slice job → gcode artifact → print job → outcome; every arrow is a row'}
