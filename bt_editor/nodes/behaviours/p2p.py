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
P2P (Point-to-Point) move behaviour node.

Carries a 6-DOF pose vector (x, y, z, rx, ry, rz) as slider parameters.
Accepts an optional data wire from a Vector node to override the pose.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
import dearpygui.dearpygui as dpg

from bt_editor.nodes.behaviours._base import BehaviourNodeDef, ParamSpec
from bt_editor.core.state import state as _state

if TYPE_CHECKING:
    from bt_editor.core.state import GraphState

#: Ordered parameter names — also used by the runtime.
P2P_PARAMS: tuple[str, ...] = ("x", "y", "z", "rx", "ry", "rz")


class P2PNodeDef(BehaviourNodeDef):
    TYPE  = "P2P"
    COLOR = (10, 90, 155)

    # PARAMS list is intentionally empty: sliders live in a special input
    # socket (vec_attr) rather than in the body, matching the original layout.
    PARAMS: ClassVar[list[ParamSpec]] = []

    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["vec_attr"]

    # ── Widget construction ───────────────────────────────────────────────────

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        # Body is empty; params live inside the vec_attr input socket below.
        info["params"] = {}
        dpg.add_spacer(width=60, height=1)

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        vec_attr = dpg.generate_uuid()
        info["vec_attr"]   = vec_attr
        state.attr_to_node[vec_attr] = nid

        slider_group = dpg.generate_uuid()
        info["slider_group"] = slider_group
        ptags: dict[str, int] = {}

        with dpg.node_attribute(tag=vec_attr,
                                attribute_type=dpg.mvNode_Attr_Input):
            dpg.add_text("vector", indent=2)
            with dpg.group(tag=slider_group):
                for pname in P2P_PARAMS:
                    ptag = dpg.generate_uuid()
                    ptags[pname] = ptag
                    dpg.add_slider_float(
                        label=pname, tag=ptag, width=160,
                        default_value=0.0,
                        min_value=-180.0, max_value=180.0,
                        format="%.2f")

        info["params"] = ptags

    # ── Input visibility (hide sliders when a Vector node is wired in) ────────

    def set_input_visibility(self, in_attr: int, show: bool,
                              nid: int, info: dict,
                              state: "GraphState") -> None:
        if info.get("vec_attr") == in_attr:
            sg = info.get("slider_group")
            if sg and dpg.does_item_exist(sg):
                dpg.configure_item(sg, show=show)

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
        params = info.get("params", {})
        obj: dict = {
            "type":   self.TYPE,
            "name":   info["label"],
            "params": {
                k: round(float(dpg.get_value(v)), 4) if dpg.does_item_exist(v) else 0.0
                for k, v in params.items()
            },
        }
        # Check if a Vector node is wired into the vec_attr socket.
        vec_attr = info.get("vec_attr")
        if vec_attr is not None:
            for _lid, (out_a, in_a) in state.links.items():
                if in_a == vec_attr:
                    src = state.attr_to_node.get(out_a)
                    if src and src in state.nodes:
                        obj["vector_input"] = {
                            "node": state.nodes[src]["label"],
                            "type": state.nodes[src]["type"],
                        }
                    break
        if children:
            obj["children"] = children
        return obj
