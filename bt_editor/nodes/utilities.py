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
Utility node definitions: Value, Vector, Math, VectorTransform, Blackboard.

These nodes have no BT parent/child sockets; they carry data (scalars,
vectors, images) across the canvas and expose it via data-output sockets.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
import dearpygui.dearpygui as dpg

from bt_editor.core.node_def import NodeDef

if TYPE_CHECKING:
    from bt_editor.core.state import GraphState

# ── Operation lists (mirrors Blender) ─────────────────────────────────────────
_MATH_OPS: list[str] = [
    "Add", "Subtract", "Multiply", "Divide",
    "Power", "Logarithm", "Absolute", "Round",
    "Floor", "Ceiling", "Minimum", "Maximum",
    "Snap", "Sine", "Cosine", "Tangent",
]

_VTRANSFORM_OPS: list[str] = [
    "Translate", "Scale",
    "Rotate X", "Rotate Y", "Rotate Z",
    "Normalize", "Negate",
    "Mirror X", "Mirror Y", "Mirror Z",
]


# ─────────────────────────────────────────────────────────────────────────────
# Value
# ─────────────────────────────────────────────────────────────────────────────

class ValueNodeDef(NodeDef):
    TYPE     = "Value"
    CATEGORY = "Utilities"
    COLOR    = (150, 110, 40)
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["data_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        vtag = dpg.generate_uuid()
        dpg.add_drag_float(label="Value", tag=vtag, width=160,
                           default_value=0.0, speed=0.01, format="%.4f")
        info["params"] = {"value": vtag}

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        out = dpg.generate_uuid()
        info["data_out_attr"] = out
        state.attr_to_node[out] = nid
        with dpg.node_attribute(tag=out, attribute_type=dpg.mvNode_Attr_Output):
            dpg.add_text("value", indent=2)

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        vtag = info.get("params", {}).get("value")
        val = dpg.get_value(vtag) if vtag and dpg.does_item_exist(vtag) else 0.0
        return {"params": {"value": round(float(val), 6)}}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, float(v))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        vtag = info.get("params", {}).get("value")
        val = round(float(dpg.get_value(vtag)), 4) if vtag and dpg.does_item_exist(vtag) else 0.0
        return {"type": self.TYPE, "name": info["label"], "value": val}


# ─────────────────────────────────────────────────────────────────────────────
# Vector
# ─────────────────────────────────────────────────────────────────────────────

class VectorNodeDef(NodeDef):
    TYPE     = "Vector"
    CATEGORY = "Utilities"
    COLOR    = (30, 110, 100)
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["data_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        ptags: dict[str, int] = {}
        for pname in ("x", "y", "z"):
            tag = dpg.generate_uuid()
            ptags[pname] = tag
            dpg.add_drag_float(label=pname.upper(), tag=tag, width=160,
                               default_value=0.0, speed=0.01, format="%.4f")
        info["params"] = ptags

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        out = dpg.generate_uuid()
        info["data_out_attr"] = out
        state.attr_to_node[out] = nid
        with dpg.node_attribute(tag=out, attribute_type=dpg.mvNode_Attr_Output):
            dpg.add_text("vector", indent=2)

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        params = {
            k: round(float(dpg.get_value(v)), 6)
            for k, v in info.get("params", {}).items()
            if dpg.does_item_exist(v)
        }
        return {"params": params} if params else {}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, float(v))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        vec = {
            k: round(float(dpg.get_value(v)), 4) if dpg.does_item_exist(v) else 0.0
            for k, v in info.get("params", {}).items()
        }
        return {"type": self.TYPE, "name": info["label"], "vector": vec}


# ─────────────────────────────────────────────────────────────────────────────
# Math
# ─────────────────────────────────────────────────────────────────────────────

class MathNodeDef(NodeDef):
    TYPE     = "Math"
    CATEGORY = "Utilities"
    COLOR    = (100, 70, 140)
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["data_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        op_tag = dpg.generate_uuid()
        dpg.add_combo(label="Op", tag=op_tag, width=140,
                      items=_MATH_OPS, default_value="Add")
        info["op_tag"] = op_tag
        info["params"] = {}      # filled in build_extra_sockets below

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        math_in_attrs: dict[str, int] = {}
        ptags: dict[str, int]         = {}
        for pname in ("A", "B"):
            ia   = dpg.generate_uuid()
            ptag = dpg.generate_uuid()
            math_in_attrs[pname] = ia
            ptags[pname]         = ptag
            state.attr_to_node[ia] = nid
            with dpg.node_attribute(tag=ia, attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text(pname, indent=2)
                dpg.add_drag_float(label=f"##{ptag}", tag=ptag, width=120,
                                   default_value=0.0, speed=0.01, format="%.4f")
        info["math_in_attrs"] = math_in_attrs
        info["params"]        = ptags

        out = dpg.generate_uuid()
        info["data_out_attr"] = out
        state.attr_to_node[out] = nid
        with dpg.node_attribute(tag=out, attribute_type=dpg.mvNode_Attr_Output):
            dpg.add_text("result", indent=2)

    def set_input_visibility(self, in_attr: int, show: bool,
                              nid: int, info: dict,
                              state: "GraphState") -> None:
        for pname, ia in info.get("math_in_attrs", {}).items():
            if ia == in_attr:
                ptag = info.get("params", {}).get(pname)
                if ptag and dpg.does_item_exist(ptag):
                    dpg.configure_item(ptag, show=show)
                return

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        op_tag = info.get("op_tag")
        op = dpg.get_value(op_tag) if op_tag and dpg.does_item_exist(op_tag) else "Add"
        params = {
            k: round(float(dpg.get_value(v)), 6)
            for k, v in info.get("params", {}).items()
            if dpg.does_item_exist(v)
        }
        return {"op": op, "params": params}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        op_tag = info.get("op_tag")
        if op_tag and dpg.does_item_exist(op_tag) and data.get("op"):
            dpg.set_value(op_tag, data["op"])
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, float(v))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        op_tag = info.get("op_tag")
        op = dpg.get_value(op_tag) if op_tag and dpg.does_item_exist(op_tag) else "Add"
        math_ins = info.get("math_in_attrs", {})
        params   = info.get("params", {})
        inputs_obj: dict = {}
        for pname, ia in math_ins.items():
            src_ref = None
            for _lid, (out_a, in_a) in state.links.items():
                if in_a == ia:
                    src = state.attr_to_node.get(out_a)
                    if src and src in state.nodes:
                        src_ref = {"node": state.nodes[src]["label"],
                                   "type": state.nodes[src]["type"]}
                    break
            ptag = params.get(pname)
            inputs_obj[pname] = src_ref if src_ref else (
                round(float(dpg.get_value(ptag)), 4)
                if ptag and dpg.does_item_exist(ptag) else 0.0
            )
        obj: dict = {"type": self.TYPE, "name": info["label"],
                     "operation": op, "inputs": inputs_obj}
        if children:
            obj["children"] = children
        return obj


# ─────────────────────────────────────────────────────────────────────────────
# VectorTransform
# ─────────────────────────────────────────────────────────────────────────────

class VectorTransformNodeDef(NodeDef):
    TYPE     = "Vector Transform"
    CATEGORY = "Utilities"
    COLOR    = (50, 100, 140)
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["vt_in_attr", "data_out_attr"]

    def build_extra_inputs(self, nid: int, info: dict,
                            state: "GraphState") -> None:
        vt_in = dpg.generate_uuid()
        info["vt_in_attr"] = vt_in
        state.attr_to_node[vt_in] = nid
        with dpg.node_attribute(tag=vt_in, attribute_type=dpg.mvNode_Attr_Input):
            dpg.add_text("vector in", indent=2)

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        op_tag = dpg.generate_uuid()
        dpg.add_combo(label="Op", tag=op_tag, width=160,
                      items=_VTRANSFORM_OPS, default_value="Translate")
        info["op_tag"] = op_tag
        ptags: dict[str, int] = {}
        for pname in ("x", "y", "z"):
            tag = dpg.generate_uuid()
            ptags[pname] = tag
            dpg.add_drag_float(label=pname.upper(), tag=tag, width=140,
                               default_value=0.0, speed=0.01, format="%.4f")
        info["params"] = ptags

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        out = dpg.generate_uuid()
        info["data_out_attr"] = out
        state.attr_to_node[out] = nid
        with dpg.node_attribute(tag=out, attribute_type=dpg.mvNode_Attr_Output):
            dpg.add_text("vector out", indent=2)

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        op_tag = info.get("op_tag")
        op = dpg.get_value(op_tag) if op_tag and dpg.does_item_exist(op_tag) else "Translate"
        params = {
            k: round(float(dpg.get_value(v)), 6)
            for k, v in info.get("params", {}).items()
            if dpg.does_item_exist(v)
        }
        return {"op": op, "params": params}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        op_tag = info.get("op_tag")
        if op_tag and dpg.does_item_exist(op_tag) and data.get("op"):
            dpg.set_value(op_tag, data["op"])
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, float(v))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        op_tag = info.get("op_tag")
        op = dpg.get_value(op_tag) if op_tag and dpg.does_item_exist(op_tag) else "Translate"
        params = {
            k: round(float(dpg.get_value(v)), 4) if dpg.does_item_exist(v) else 0.0
            for k, v in info.get("params", {}).items()
        }
        obj: dict = {"type": self.TYPE, "name": info["label"],
                     "operation": op, "params": params}
        vt_in = info.get("vt_in_attr")
        if vt_in is not None:
            for _lid, (out_a, in_a) in state.links.items():
                if in_a == vt_in:
                    src = state.attr_to_node.get(out_a)
                    if src and src in state.nodes:
                        obj["input"] = {"node": state.nodes[src]["label"],
                                        "type": state.nodes[src]["type"]}
                    break
        if children:
            obj["children"] = children
        return obj


# ─────────────────────────────────────────────────────────────────────────────
# Blackboard
# ─────────────────────────────────────────────────────────────────────────────

class BlackboardNodeDef(NodeDef):
    """Read/Write gateway to the shared Blackboard parameter store."""

    TYPE     = "Blackboard"
    CATEGORY = "Utilities"
    COLOR    = (90, 50, 160)
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["bb_out_attr", "bb_in_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        # Import callback lazily to avoid circular imports at module load time.
        from bt_editor.editor.node_callbacks import bb_node_mode_changed

        op_tag = dpg.generate_uuid()
        dpg.add_combo(label="Mode", tag=op_tag, width=140,
                      items=["Read", "Write"], default_value="Read",
                      callback=bb_node_mode_changed, user_data=nid)
        info["op_tag"] = op_tag

        key_tag = dpg.generate_uuid()
        dpg.add_combo(label="Key", tag=key_tag, width=140,
                      items=list(state.blackboard.keys()), default_value="")
        info["bb_key_tag"] = key_tag

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        bb_out = dpg.generate_uuid()
        info["bb_out_attr"] = bb_out
        state.attr_to_node[bb_out] = nid
        with dpg.node_attribute(tag=bb_out, attribute_type=dpg.mvNode_Attr_Output):
            dpg.add_text("value", indent=2)

        bb_in = dpg.generate_uuid()
        info["bb_in_attr"] = bb_in
        state.attr_to_node[bb_in] = nid
        with dpg.node_attribute(tag=bb_in, attribute_type=dpg.mvNode_Attr_Input):
            dpg.add_text("value", indent=2)
        dpg.configure_item(bb_in, show=False)   # default = Read mode

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        op_tag  = info.get("op_tag")
        key_tag = info.get("bb_key_tag")
        return {
            "op":     dpg.get_value(op_tag)  if op_tag  and dpg.does_item_exist(op_tag)  else "Read",
            "bb_key": dpg.get_value(key_tag) if key_tag and dpg.does_item_exist(key_tag) else "",
        }

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        from bt_editor.editor.node_callbacks import bb_node_mode_changed
        op_tag  = info.get("op_tag")
        key_tag = info.get("bb_key_tag")
        op = data.get("op", "Read")
        if op_tag and dpg.does_item_exist(op_tag):
            dpg.set_value(op_tag, op)
        if key_tag and dpg.does_item_exist(key_tag):
            dpg.set_value(key_tag, data.get("bb_key", ""))
        # Re-apply socket visibility for the restored mode.
        bb_node_mode_changed(None, op, nid)

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        op_tag  = info.get("op_tag")
        key_tag = info.get("bb_key_tag")
        mode = dpg.get_value(op_tag)  if op_tag  and dpg.does_item_exist(op_tag)  else "Read"
        key  = dpg.get_value(key_tag) if key_tag and dpg.does_item_exist(key_tag) else ""
        obj: dict = {"type": self.TYPE, "name": info["label"],
                     "mode": mode, "key": key}
        if mode == "Read":
            obj["value"] = state.blackboard.get(key, {}).get("value") if key else None
        else:
            bb_in = info.get("bb_in_attr")
            if bb_in is not None:
                for _lid, (out_a, in_a) in state.links.items():
                    if in_a == bb_in:
                        src = state.attr_to_node.get(out_a)
                        if src and src in state.nodes:
                            obj["write_from"] = {
                                "node": state.nodes[src]["label"],
                                "type": state.nodes[src]["type"],
                            }
                        break
        if children:
            obj["children"] = children
        return obj
