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
Base class for user-defined Behaviour node plugins.

To create a new behaviour:
    1. Create a .py file inside ``bt_editor/nodes/behaviours/``.
    2. Subclass ``BehaviourNodeDef``.
    3. Set TYPE, COLOR, and PARAMS.
    4. The GUI widgets are generated automatically from PARAMS.

The file is auto-discovered at startup — no manual registration needed.

Example
-------
::

    # bt_editor/nodes/behaviours/my_action.py
    from bt_editor.nodes.behaviours._base import BehaviourNodeDef, ParamSpec

    class MyActionNodeDef(BehaviourNodeDef):
        TYPE   = "My Action"
        COLOR  = (0, 130, 100)
        PARAMS = [
            ParamSpec("speed",   "Speed",  default=1.0, min_val=0.0, max_val=10.0),
            ParamSpec("timeout", "Timeout", default=5.0, min_val=0.0, max_val=60.0),
        ]
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar
import dearpygui.dearpygui as dpg

from bt_editor.core.node_def import NodeDef

if TYPE_CHECKING:
    from bt_editor.core.state import GraphState


@dataclass
class ParamSpec:
    """Specification for one numeric parameter of a BehaviourNodeDef."""
    name:    str
    label:   str
    default: float = 0.0
    min_val: float = -180.0
    max_val: float =  180.0
    speed:   float = 0.01
    fmt:     str   = "%.2f"
    widget:  str   = "slider_float"   # "slider_float" | "drag_float"


class BehaviourNodeDef(NodeDef):
    """Base for user-defined behaviour node plugins.

    Subclasses declare PARAMS as a list of ParamSpec; the GUI is built
    automatically.  Serialization and JSON export are also handled here.
    """

    CATEGORY: ClassVar[str]             = "Behaviours"
    PARAMS:   ClassVar[list[ParamSpec]] = []
    HAS_BT_OUT: ClassVar[bool]          = False   # behaviours are leaf nodes — no children

    # ── Widget construction ───────────────────────────────────────────────────

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        ptags: dict[str, int] = {}
        for ps in self.PARAMS:
            tag = dpg.generate_uuid()
            ptags[ps.name] = tag
            if ps.widget == "drag_float":
                dpg.add_drag_float(
                    label=ps.label, tag=tag, width=160,
                    default_value=ps.default, speed=ps.speed, format=ps.fmt)
            else:
                dpg.add_slider_float(
                    label=ps.label, tag=tag, width=160,
                    default_value=ps.default,
                    min_value=ps.min_val, max_value=ps.max_val,
                    format=ps.fmt)
        info["params"] = ptags
        if not ptags:
            dpg.add_spacer(width=60, height=1)

    # ── Serialization ─────────────────────────────────────────────────────────

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        params: dict = {}
        for k, v in info.get("params", {}).items():
            if dpg.does_item_exist(v):
                params[k] = round(float(dpg.get_value(v)), 6)
        return {"params": params} if params else {}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, float(v))

    # ── JSON export ───────────────────────────────────────────────────────────

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        params_widgets = info.get("params", {})
        params = {
            k: round(float(dpg.get_value(v)), 4) if dpg.does_item_exist(v) else 0.0
            for k, v in params_widgets.items()
        }
        obj: dict = {"type": self.TYPE, "name": info["label"]}
        if params:
            obj["params"] = params
        if children:
            obj["children"] = children
        return obj
