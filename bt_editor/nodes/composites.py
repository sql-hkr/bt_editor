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
Composite node definitions: Sequence, Selector, Parallel.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import dearpygui.dearpygui as dpg

from bt_editor.core.node_def import NodeDef

if TYPE_CHECKING:
    from bt_editor.core.state import GraphState


class SequenceNodeDef(NodeDef):
    TYPE = "Sequence"
    CATEGORY = "Composites"
    COLOR = (26, 111, 176)
    IS_CTRL = True

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        dpg.add_spacer(width=60, height=1)


class SelectorNodeDef(NodeDef):
    TYPE = "Selector"
    CATEGORY = "Composites"
    COLOR = (163, 68, 0)
    IS_CTRL = True

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        dpg.add_spacer(width=60, height=1)


class ParallelNodeDef(NodeDef):
    TYPE = "Parallel"
    CATEGORY = "Composites"
    COLOR = (90, 20, 160)
    IS_CTRL = True

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        dpg.add_spacer(width=60, height=1)
