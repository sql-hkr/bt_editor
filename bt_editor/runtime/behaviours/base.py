# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  sql-hkr
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Abstract base class for runtime behaviour implementations.

Runtime behaviours are executed by the BT engine (not the GUI).
They are instantiated from the JSON exported by the editor.

Usage
-----
::

    from bt_editor.runtime.behaviours.base import RuntimeBehaviour

    class MyBehaviour(RuntimeBehaviour):
        @classmethod
        def from_json(cls, node_data):
            return cls(**node_data.get("params", {}))

        def setup(self):
            pass   # one-time hardware / resource init

        def update(self):
            # return py_trees.common.Status.SUCCESS
            ...
"""
from __future__ import annotations
import abc


class RuntimeBehaviour(abc.ABC):
    """Abstract base for py_trees Behaviour implementations.

    Subclass this (alongside ``py_trees.behaviour.Behaviour``) in your
    robot's runtime package to bind GUI-exported parameters to real actions.
    """

    @classmethod
    @abc.abstractmethod
    def from_json(cls, node_data: dict) -> "RuntimeBehaviour":
        """Instantiate from a JSON node dict as produced by the GUI export."""

    @abc.abstractmethod
    def setup(self) -> None:
        """One-time setup (hardware init, resource acquisition, etc.)."""

    @abc.abstractmethod
    def update(self):
        """Called every BT tick.  Return a py_trees.common.Status value."""
