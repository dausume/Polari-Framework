#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
ExecutionTrace Module for Polari No-Code System

Components:
- InstanceContextSnapshot: Serializable snapshot of execution context
- VariableChange, ObjectChange: Change records between snapshots
- ContextDiff: Diff between before and after context snapshots
- ExecutionStepSnapshot: Full diagnostic state at a single execution step
- ExecutionTrace: Complete ordered record of one execution run
- Breakpoint: A breakpoint on a state
- DebugSession: Manages interactive stepping and breakpoints
"""

from polariNoCode.ExecutionTrace.ExecutionStepSnapshot import (
    InstanceContextSnapshot,
    VariableChange,
    ObjectChange,
    ContextDiff,
    ExecutionStepSnapshot,
)
from polariNoCode.ExecutionTrace.ExecutionTrace import ExecutionTrace
from polariNoCode.ExecutionTrace.DebugSession import (
    Breakpoint,
    DebugSession,
)

__all__ = [
    'InstanceContextSnapshot',
    'VariableChange',
    'ObjectChange',
    'ContextDiff',
    'ExecutionStepSnapshot',
    'ExecutionTrace',
    'Breakpoint',
    'DebugSession',
]
