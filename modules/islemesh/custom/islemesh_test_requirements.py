"""Reviewed requirements for the bounded weekend test set, not generic kind guesses."""
from copy import deepcopy


def need(dep, check='present', **kwargs):
    return dict(dep=dep, scope='device', check=check, **kwargs)


_REQUIREMENTS = {
    ('whoami','use'): dict(schema_version=1,kind='mesh-app',action='use',complete=True,
        needs=[need('access.whoami.https')]),
    ('polari','use'): dict(schema_version=1,kind='polari-instance',action='use',complete=True,
        needs=[need('access.polari.https'),need('access.polari-frontend.https')]),
    # Preliminary deployment checks; the Electronics owner must close the full descriptor.
    ('board-engines','host'): dict(schema_version=1,kind='mesh-app',action='host',complete=False,
        needs=[need('runtime.docker.usable'),need('runtime.compose.usable'),need('agent.running'),
               need('host.architecture','equals',value='x86_64',failure='unsupported'),
               need('resources.memory_available_mib','min',value=768,failure='resource-limited'),
               need('resources.root_disk_free_mib','min',value=2048,failure='resource-limited'),
               need('image.board-engines.present'),
               need('service.board-engines.tls'),
               need('service.board-engines.name_available'),
               need('deployment.board-engines.preflight'),
               need('policy.mesh-app.allowed',failure='policy-restricted')]),
}


def test_requirement(entry, action):
    descriptor = _REQUIREMENTS.get((entry.get('name'),action))
    if descriptor is None or descriptor['kind'] != entry.get('kind'):
        return None
    return deepcopy(descriptor)
