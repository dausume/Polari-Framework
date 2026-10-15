"""
@module cmod.custom.generator.env

The Jinja2 Environment for generated firmware C (reusing pol-build/render.py's idiom: StrictUndefined, so a context key a
template needs but the builder did not supply FAILS with its name, never renders as empty). keep_trailing_newline +
trim_blocks + lstrip_blocks make `{% %}` lines vanish, so a template reads like the C it produces and the bytes are exact.
"""
import hashlib
import os

import jinja2

from cmod.custom.generator.filters import FILTERS, GenError

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.normpath(os.path.join(HERE, '..', 'templates'))


def environment(templates_dir=None):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates_dir or TEMPLATES), undefined=jinja2.StrictUndefined,
                             keep_trailing_newline=True, trim_blocks=True, lstrip_blocks=True, autoescape=False)
    env.filters.update(FILTERS)
    return env


def render(name, ctx, templates_dir=None):
    """-> bytes of template `name` (e.g. 'avr/polari_graph.c.j2') over `ctx`. A missing key -> GenError naming it."""
    try:
        return environment(templates_dir).get_template(name).render(**ctx).encode()
    except jinja2.UndefinedError as e:
        raise GenError('template %s: context is missing a key — %s' % (name, e.message))


def template_sha(name, templates_dir=None):
    with open(os.path.join(templates_dir or TEMPLATES, name), 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def provenance(names, templates_dir=None):
    """{'templates': {name: sha256}, 'template_generator': 'jinja2 <version>'} for the record."""
    return {'templates': {n: template_sha(n, templates_dir) for n in sorted(names)}, 'template_generator': 'jinja2 %s' % jinja2.__version__}
