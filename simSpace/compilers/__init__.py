"""
@cross-cutting
@module simSpace.compilers
@tags @xc:render-shared

Snapshot compilers — one per dimensionality. Pulled out of sim_space_api
so the API class stays focused on HTTP routing + dispatch.

The compilers share helpers via `common.py` (ref resolution, instance-id
extraction) and remain otherwise independent. New dimensionalities (e.g.
hypothetical 4D, or a curved-space variant) would add a sibling module.
"""

from .compile_2d import compile_2d
from .compile_3d import compile_3d

__all__ = ['compile_2d', 'compile_3d']
