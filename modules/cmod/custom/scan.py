"""
@module cmod.custom.scan

ONE FUNCTION BODY → WHAT IT TOUCHES (C_MODULARIZATION_PLAN.md §2). A CONSERVATIVE scan over pycparser's AST — it may
say "touches" for something a path never reaches, never the reverse:

  globals      every file-scope variable the body names, read and/or written (`g++`, `g = …`, `g[i] = …`, `g.f = …`,
               `&g` passed on = may-write), and whether each access sits inside an ATOMIC_BLOCK
  registers    every identifier that avr-libc's <avr/io.h> defines as a register (registers.py), read / written
  calls        every function it calls by name (a call through a pointer is listed as `(*indirect)`)
  pointers     per pointer parameter: written through (`*p = …`, `p[i] = …`, `p->f = …`), read through, passed on
  atomic       whether it opens an ATOMIC_BLOCK; `sei()` / `cli()` are calls (a manual interrupt region is NOT tracked —
               the ISR-safety verdict then says undetermined instead of guessing)
"""
from pycparser import c_ast

from cmod.custom.preprocess import ATOMIC_MARK

_RMW_UNARY = ('++', '--', 'p++', 'p--')


class BodyScan(object):
    def __init__(self, fdef, globals_, registers, types):
        self.globals_, self.registers, self.types = globals_, registers, types
        self.params = {}
        decl = fdef.decl.type
        for p in (getattr(decl, 'args', None) and decl.args.params or []):
            if isinstance(p, c_ast.Decl) and p.name:
                self.params[p.name] = types.describe(p.type)
        self.locals = set(self.params)
        self.g = {}       # name → {'r': bool, 'w': bool, 'rmw': bool, 'outside_atomic': bool, 'inside_atomic': bool}
        self.reg = {}     # name → {'r', 'w'}
        self.calls = []
        self.ptr = {n: {'w': False, 'r': False, 'passed': []} for n, d in self.params.items() if d['kind'] in ('pointer', 'array')}
        self.atomic = False
        self._collect_locals(fdef.body)
        self._v(fdef.body, atomic=False, lhs=False)

    # ---- scope
    def _collect_locals(self, node):
        if isinstance(node, c_ast.Decl) and node.name:
            self.locals.add(node.name)
        for _, ch in node.children():
            self._collect_locals(ch)

    # ---- access recording
    def _id(self, name, atomic, lhs, rmw=False, read=True):
        if name in self.ptr:
            return
        if name in self.locals:
            return
        if name in self.globals_:
            a = self.g.setdefault(name, {'r': False, 'w': False, 'rmw': False, 'inside_atomic': False, 'outside_atomic': False})
            if lhs:
                a['w'] = True
            if read or rmw:
                a['r'] = True
            a['rmw'] = a['rmw'] or rmw
            a['inside_atomic' if atomic else 'outside_atomic'] = True
        elif name in self.registers:
            a = self.reg.setdefault(name, {'r': False, 'w': False})
            if lhs:
                a['w'] = True
            if read or rmw:
                a['r'] = True

    def _base(self, node):
        """The identifier an lvalue chain bottoms out at: g, g[i], g.f, g->f, *g → g (or None)."""
        while True:
            if isinstance(node, c_ast.ID):
                return node.name
            if isinstance(node, c_ast.ArrayRef):
                node = node.name
            elif isinstance(node, c_ast.StructRef):
                node = node.name
            elif isinstance(node, c_ast.UnaryOp) and node.op == '*':
                node = node.expr
            elif isinstance(node, c_ast.Cast):
                node = node.expr
            else:
                return None

    def _through_pointer(self, node):
        return isinstance(node, (c_ast.ArrayRef,)) or (isinstance(node, c_ast.UnaryOp) and node.op == '*') or \
            (isinstance(node, c_ast.StructRef) and node.type == '->')

    def _write(self, target, atomic, rmw):
        base = self._base(target)
        if base in self.ptr:
            if self._through_pointer(target) or isinstance(target, c_ast.StructRef):
                self.ptr[base]['w'] = True
                if rmw:
                    self.ptr[base]['r'] = True
        elif base:
            self._id(base, atomic, lhs=True, rmw=rmw, read=rmw)
        # subscripts / inner expressions are reads
        for sub in self._inner_reads(target):
            self._v(sub, atomic, lhs=False)

    def _inner_reads(self, node):
        out = []
        while True:
            if isinstance(node, c_ast.ArrayRef):
                out.append(node.subscript)
                node = node.name
            elif isinstance(node, (c_ast.StructRef,)):
                node = node.name
            elif isinstance(node, c_ast.UnaryOp) and node.op == '*':
                node = node.expr
            elif isinstance(node, c_ast.Cast):
                node = node.expr
            else:
                return out

    # ---- the walk
    def _v(self, node, atomic, lhs):
        if node is None:
            return
        if isinstance(node, c_ast.If) and isinstance(node.cond, c_ast.FuncCall) and getattr(node.cond.name, 'name', '') == ATOMIC_MARK:
            self.atomic = True
            self._v(node.iftrue, True, False)
            self._v(node.iffalse, atomic, False)
            return
        if isinstance(node, c_ast.Assignment):
            self._write(node.lvalue, atomic, rmw=node.op != '=')
            self._v(node.rvalue, atomic, False)
            return
        if isinstance(node, c_ast.UnaryOp) and node.op in _RMW_UNARY:
            self._write(node.expr, atomic, rmw=True)
            return
        if isinstance(node, c_ast.UnaryOp) and node.op == '&':
            base = self._base(node.expr)
            if base and base not in self.locals:
                self._id(base, atomic, lhs=True, rmw=False, read=True)   # its address escapes: may be written
            for sub in self._inner_reads(node.expr):
                self._v(sub, atomic, False)
            return
        if isinstance(node, c_ast.FuncCall):
            name = node.name.name if isinstance(node.name, c_ast.ID) else '(*indirect)'
            if name not in self.calls:
                self.calls.append(name)
            for arg in (node.args.exprs if node.args else []):
                base = self._base(arg)
                if base in self.ptr:
                    self.ptr[base]['passed'].append(name)
                elif isinstance(arg, c_ast.ID) and arg.name in self.globals_ and self.globals_[arg.name]['kind'] in ('array', 'pointer'):
                    self._id(arg.name, atomic, lhs=True, read=True)   # an array handed to a callee may be written
                self._v(arg, atomic, False)
            if not isinstance(node.name, c_ast.ID):
                self._v(node.name, atomic, False)
            return
        if isinstance(node, c_ast.ID):
            if node.name in self.ptr:
                return
            self._id(node.name, atomic, lhs=False)
            return
        if isinstance(node, (c_ast.ArrayRef, c_ast.StructRef)) or (isinstance(node, c_ast.UnaryOp) and node.op == '*'):
            base = self._base(node)
            if base in self.ptr:
                self.ptr[base]['r'] = True
                for sub in self._inner_reads(node):
                    self._v(sub, atomic, False)
                return
        if isinstance(node, c_ast.StructRef):
            self._v(node.name, atomic, lhs)   # the field name is not an identifier
            return
        if isinstance(node, c_ast.Decl):
            self._v(node.init, atomic, False)
            return
        if isinstance(node, (c_ast.Typename, c_ast.TypeDecl, c_ast.PtrDecl, c_ast.ArrayDecl, c_ast.IdentifierType)):
            return
        for _, ch in node.children():
            self._v(ch, atomic, False)
