"""
Solution Version API

Provides an endpoint for atomically creating solution version snapshots:
- POST /createSolutionVersion  - Snapshot current solution state + generated code
"""

from objectTreeDecorators import treeObject, treeObjectInit
from polariApiServer.solutionCodeGeneratorAPI import generate_code_from_solution
import falcon
import json
import time


class SolutionVersionAPI(treeObject):
    """
    POST /createSolutionVersion - Atomically create a version snapshot.
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/createSolutionVersion'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

    def on_post(self, request, response):
        """
        Create a new version snapshot of a solution.

        Expects JSON body:
        {
            "solutionId": "<polariId of SolutionDefinition>",
            "label": "optional label",
            "description": "optional description",
            "createdBy": "optional user id"
        }
        """
        try:
            content_type = request.content_type or ''
            if 'multipart/form-data' in content_type:
                solution_id = request.get_param('solutionId') or ''
                label = request.get_param('label') or ''
                description = request.get_param('description') or ''
                created_by = request.get_param('createdBy') or ''
            else:
                raw = request.bounded_stream.read()
                body = json.loads(raw) if raw else {}
                solution_id = body.get('solutionId', '')
                label = body.get('label', '')
                description = body.get('description', '')
                created_by = body.get('createdBy', '')

            if not solution_id:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'solutionId is required'}
                return

            # 1. Load the SolutionDefinition
            instances = self.manager.objectTables.get('SolutionDefinition', {})
            solution_inst = instances.get(solution_id)
            if solution_inst is None:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'SolutionDefinition "{solution_id}" not found'}
                return

            definition_str = getattr(solution_inst, 'definition', '{}')
            try:
                solution_data = json.loads(definition_str) if isinstance(definition_str, str) else definition_str
            except Exception:
                solution_data = {}

            # 2. Generate code for both runtimes
            generated_code = {}
            for runtime in ['python_backend', 'typescript_frontend']:
                try:
                    generated_code[runtime] = generate_code_from_solution(solution_data, runtime)
                except Exception as e:
                    generated_code[runtime] = f'# Code generation error: {e}'

            # 3. Find the highest version_number for this solution
            version_instances = self.manager.objectTables.get('SolutionVersion', {})
            max_version = 0
            previous_current_id = None
            for vid, vinst in version_instances.items():
                if getattr(vinst, 'solution_id', '') == solution_id:
                    vnum = getattr(vinst, 'version_number', 0)
                    if vnum > max_version:
                        max_version = vnum
                    if getattr(vinst, 'is_current', False):
                        previous_current_id = vid

            new_version_number = max_version + 1

            # 4. Set is_current=False on previous current version
            if previous_current_id and previous_current_id in version_instances:
                prev = version_instances[previous_current_id]
                prev.is_current = False

            # 5. Create the new SolutionVersion
            from polariApiServer.solutionVersion import SolutionVersion
            new_version = SolutionVersion(
                solution_id=solution_id,
                version_number=new_version_number,
                label=label or f'v{new_version_number}',
                description=description,
                definition=definition_str,
                generated_code=json.dumps(generated_code),
                created_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                created_by=created_by,
                parent_version_id=previous_current_id or '',
                is_current=True,
                manager=self.manager,
            )

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'versionId': getattr(new_version, 'polariId', ''),
                'versionNumber': new_version_number,
                'label': new_version.label,
                'solutionId': solution_id,
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')
