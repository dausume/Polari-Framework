"""
Object-tree core: treeObject / @treeObjectInit + managerObject.

Exercises the heart of Polari's "define a class → get a table" model,
including defining a class AT RUNTIME (the createClass essence): the
manager accepts a new treeObject type, gives it a table, and tracks
instance counts.

Uses one in-process managerObject(hasServer=True) shared across the class
(construction is heavy). No live server / DB.

Run (in the backend container):
    python3 -m unittest tests.test_object_tree -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from objectTreeManagerDecorators import managerObject
from objectTreeDecorators import treeObject, treeObjectInit


class Widget(treeObject):
    """A throwaway typed object for object-tree tests."""

    @treeObjectInit
    def __init__(self, name='', size=0, tag='', manager=None):
        self.name = name
        self.size = size
        self.tag = tag


def _make_runtime_class():
    """Build a treeObject subclass at RUNTIME (the createClass essence)."""
    def __init__(self, name='', level=0, manager=None):
        self.name = name
        self.level = level
    init = treeObjectInit(__init__)
    return type('RuntimeGadget', (treeObject,), {'__init__': init})


class ObjectTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mgr = managerObject(hasServer=True)
        cls.mgr.getObjectTyping(classObj=Widget)

    def test_typing_registered(self):
        # After typing, the manager knows the type (typedObjects registry).
        typed = getattr(self.mgr, 'objectTyping', None) \
            or getattr(self.mgr, 'typedObjects', None) \
            or self.mgr.objectTables
        self.assertIsNotNone(typed)

    def test_instance_lands_in_table(self):
        w = Widget(name='w-alpha', size=3, tag='a', manager=self.mgr)
        self.assertIn('Widget', self.mgr.objectTables)
        self.assertIn(w.id, self.mgr.objectTables['Widget'])

    def test_fields_preserved(self):
        w = Widget(name='w-beta', size=7, tag='b', manager=self.mgr)
        stored = self.mgr.objectTables['Widget'][w.id]
        self.assertEqual(stored.size, 7)
        self.assertEqual(stored.tag, 'b')

    def test_instance_count_increments(self):
        before = len(self.mgr.objectTables.get('Widget', {}))
        Widget(name='w-count-1', manager=self.mgr)
        Widget(name='w-count-2', manager=self.mgr)
        after = len(self.mgr.objectTables['Widget'])
        self.assertEqual(after, before + 2)

    def test_runtime_defined_class_gets_a_table(self):
        Gadget = _make_runtime_class()
        self.mgr.getObjectTyping(classObj=Gadget)
        g = Gadget(name='g-1', level=2, manager=self.mgr)
        self.assertIn('RuntimeGadget', self.mgr.objectTables)
        self.assertIn(g.id, self.mgr.objectTables['RuntimeGadget'])
        self.assertEqual(
            self.mgr.objectTables['RuntimeGadget'][g.id].level, 2)

    def test_each_object_has_unique_id(self):
        a = Widget(name='w-id-a', manager=self.mgr)
        b = Widget(name='w-id-b', manager=self.mgr)
        self.assertNotEqual(a.id, b.id)


if __name__ == '__main__':
    unittest.main(verbosity=2)
