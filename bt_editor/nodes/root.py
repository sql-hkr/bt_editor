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
BT Root node definition.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import dearpygui.dearpygui as dpg

from bt_editor.core.node_def import NodeDef

if TYPE_CHECKING:
    from bt_editor.core.state import GraphState


class BTRootNodeDef(NodeDef):
    """The single root of the Behaviour Tree. Protected from deletion."""

    TYPE          = "BT Root"
    CATEGORY      = "_internal"   # not shown in Add menu
    COLOR         = (20, 80, 140)
    HAS_BT_IN     = False
    HAS_BT_OUT    = True
    BT_OUT_LABEL  = "child"

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        # Spacer prevents the empty static attribute from widening every frame.
        dpg.add_spacer(width=60, height=1)

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        obj: dict = {"type": self.TYPE, "name": info["label"]}
        if children:
            obj["child"] = children[0]
        return obj
