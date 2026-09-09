"""
@module kirimoto.custom.build_image

Build the Kiri:Moto image from the pinned commit: refuses while the pin is
'<PIN ME>'. Returns (command, refusals) — the caller (pol / Jenkins) runs it.
"""
import os

from kirimoto.kirimoto_basis import KIRIMOTO_UPSTREAM, KIRIMOTO_IMAGE


def build_command():
    if KIRIMOTO_UPSTREAM['commit'] == '<PIN ME>':
        return [], ['kirimoto upstream commit is <PIN ME> — pin it in kirimoto_basis.KIRIMOTO_UPSTREAM after the licence gate']
    here = os.path.dirname(os.path.abspath(__file__))
    return ['docker', 'build', '--build-arg', 'KIRIMOTO_COMMIT=%s' % KIRIMOTO_UPSTREAM['commit'], '-t', KIRIMOTO_IMAGE, here], []
