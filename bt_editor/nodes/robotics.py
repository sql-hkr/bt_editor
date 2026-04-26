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
Robotics computation node definitions.

Covers the essential mathematical building blocks for robot manipulator
control and visual servo:

  HTMatrix        — writable 4×4 homogeneous-transformation matrix display
  PoseCompose     — compose two poses: T_out = T_a ⊗ T_b  (right-multiply)
  PoseInverse     — compute the inverse of a homogeneous transform
  RPYtoHTM        — Roll-Pitch-Yaw (ZYX) + translation → 4×4 HTM
  HTMtoRPY        — HTM → [x,y,z,roll,pitch,yaw] 6-vector output
  JointState      — N-DOF joint angle vector (configurable 1–7 joints)
  ForwardKin      — stub: maps joint angles to EE pose (calls FK callback)
  PoseError       — 6-DOF pose error [Δx,Δy,Δz,Δrx,Δry,Δrz]
  ScalarToVector  — pack 3 separate scalar sockets into one vector socket
  VectorSplit     — unpack a vector socket into individual scalar outputs
  ClampVector     — element-wise clamp of a vector to [min, max]
  DotProduct      — dot product of two (same-size) vectors
  CrossProduct    — 3×1 cross product
  Normalize       — |v| → unit vector
"""
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
import dearpygui.dearpygui as dpg

from bt_editor.core.node_def import NodeDef

if TYPE_CHECKING:
    from bt_editor.core.state import GraphState

# ── Shared colour palette ─────────────────────────────────────────────────────
_C_HTM    = (20,  100, 170)   # blue
_C_POSE   = (30,  140,  80)   # green
_C_VEC    = (30,  110, 100)   # teal
_C_SCALAR = (150, 110,  40)   # amber
_C_JOINT  = (110,  60, 160)   # purple
_C_SERVO  = (160,  80,  20)   # orange


def _data_in(nid: int, info: dict, state: "GraphState",
             key: str, label: str) -> int:
    """Create a data input attribute and return its id."""
    ia = dpg.generate_uuid()
    info[key] = ia
    state.attr_to_node[ia] = nid
    with dpg.node_attribute(tag=ia, attribute_type=dpg.mvNode_Attr_Input):
        dpg.add_text(label, indent=2)
    return ia


def _data_out(nid: int, info: dict, state: "GraphState",
              key: str, label: str) -> int:
    """Create a data output attribute and return its id."""
    oa = dpg.generate_uuid()
    info[key] = oa
    state.attr_to_node[oa] = nid
    with dpg.node_attribute(tag=oa, attribute_type=dpg.mvNode_Attr_Output):
        dpg.add_text(label, indent=2)
    return oa


# ─────────────────────────────────────────────────────────────────────────────
# HTMatrix  —  4×4 homogeneous transformation (display + manual entry)
# ─────────────────────────────────────────────────────────────────────────────

class HTMatrixNodeDef(NodeDef):
    """Display & manual-entry for a 4×4 Homogeneous Transformation Matrix."""
    TYPE     = "HTMatrix"
    CATEGORY = "Robotics"
    COLOR    = _C_HTM
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["htm_in_attr", "htm_out_attr"]

    _ROWS = ("R0", "R1", "R2", "R3")

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        # 4×4 drag_float table (row-major order)
        rows: list[list[int]] = []
        default = [
            [1., 0., 0., 0.],
            [0., 1., 0., 0.],
            [0., 0., 1., 0.],
            [0., 0., 0., 1.],
        ]
        for r in range(4):
            row_tags: list[int] = []
            with dpg.group(horizontal=True):
                for c in range(4):
                    tag = dpg.generate_uuid()
                    dpg.add_drag_float(tag=tag, label=f"##{tag}",
                                       width=52, speed=0.001, format="%.3f",
                                       default_value=default[r][c])
                    row_tags.append(tag)
            rows.append(row_tags)
        info["matrix_tags"] = rows

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _data_in(nid, info, state, "htm_in_attr",  "T_in")
        _data_out(nid, info, state, "htm_out_attr", "T_out")

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        rows = info.get("matrix_tags", [])
        mat = [
            [round(float(dpg.get_value(cell)), 6) if dpg.does_item_exist(cell) else 0.0
             for cell in row]
            for row in rows
        ]
        return {"matrix": mat}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        mat = data.get("matrix", [])
        rows = info.get("matrix_tags", [])
        for r, row in enumerate(rows):
            for c, cell_tag in enumerate(row):
                try:
                    val = mat[r][c]
                except IndexError:
                    val = 0.0
                if dpg.does_item_exist(cell_tag):
                    dpg.set_value(cell_tag, float(val))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        rows = info.get("matrix_tags", [])
        mat = [
            [round(float(dpg.get_value(cell)), 6) if dpg.does_item_exist(cell) else 0.0
             for cell in row]
            for row in rows
        ]
        return {"type": self.TYPE, "name": info["label"], "matrix": mat}


# ─────────────────────────────────────────────────────────────────────────────
# RPYtoHTM  —  Roll-Pitch-Yaw (rad) + xyz translation → 4×4 HTM
# ─────────────────────────────────────────────────────────────────────────────

class RPYtoHTMNodeDef(NodeDef):
    """Convert roll-pitch-yaw (ZYX, radians) + translation to a 4×4 HTM."""
    TYPE     = "RPYtoHTM"
    CATEGORY = "Robotics"
    COLOR    = _C_HTM
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["htm_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        ptags: dict[str, int] = {}
        labels = [("x",   "X (m)"),  ("y",   "Y (m)"),  ("z",   "Z (m)"),
                  ("ro",  "Roll"),   ("pi",  "Pitch"),  ("ya",  "Yaw")]
        for name, lbl in labels:
            tag = dpg.generate_uuid()
            ptags[name] = tag
            dpg.add_drag_float(label=lbl, tag=tag, width=140,
                               default_value=0.0, speed=0.001, format="%.4f")
        info["params"] = ptags

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _data_out(nid, info, state, "htm_out_attr", "T_out")

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        return {"params": {
            k: round(float(dpg.get_value(v)), 6)
            for k, v in info.get("params", {}).items()
            if dpg.does_item_exist(v)
        }}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, float(v))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        params = {
            k: round(float(dpg.get_value(v)), 6) if dpg.does_item_exist(v) else 0.0
            for k, v in info.get("params", {}).items()
        }
        return {"type": self.TYPE, "name": info["label"], "params": params}


# ─────────────────────────────────────────────────────────────────────────────
# HTMtoRPY  —  4×4 HTM → [x,y,z,roll,pitch,yaw]
# ─────────────────────────────────────────────────────────────────────────────

class HTMtoRPYNodeDef(NodeDef):
    """Extract [x,y,z,roll,pitch,yaw] from a 4×4 Homogeneous Transform."""
    TYPE     = "HTMtoRPY"
    CATEGORY = "Robotics"
    COLOR    = _C_HTM
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["htm_in_attr", "pose_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        dpg.add_text("[x, y, z, R, P, Y]", color=(160, 200, 240, 200))

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _data_in(nid,  info, state, "htm_in_attr",   "T_in")
        _data_out(nid, info, state, "pose_out_attr",  "pose[6]")

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}


# ─────────────────────────────────────────────────────────────────────────────
# PoseCompose  —  T_out = T_a @ T_b
# ─────────────────────────────────────────────────────────────────────────────

class PoseComposeNodeDef(NodeDef):
    """Compose two homogeneous transforms: T_out = T_a ⊗ T_b."""
    TYPE     = "PoseCompose"
    CATEGORY = "Robotics"
    COLOR    = _C_POSE
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["ta_in_attr", "tb_in_attr", "tc_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        dpg.add_text("T_out = T_a ⊗ T_b", color=(130, 210, 150, 200))

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _data_in(nid,  info, state, "ta_in_attr",  "T_a")
        _data_in(nid,  info, state, "tb_in_attr",  "T_b")
        _data_out(nid, info, state, "tc_out_attr", "T_out")

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}


# ─────────────────────────────────────────────────────────────────────────────
# PoseInverse  —  T_inv = T⁻¹
# ─────────────────────────────────────────────────────────────────────────────

class PoseInverseNodeDef(NodeDef):
    """Compute the inverse of a homogeneous transform T⁻¹."""
    TYPE     = "PoseInverse"
    CATEGORY = "Robotics"
    COLOR    = _C_POSE
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["htm_in_attr", "inv_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        dpg.add_text("T_inv = T⁻¹", color=(130, 210, 150, 200))

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _data_in(nid,  info, state, "htm_in_attr",  "T_in")
        _data_out(nid, info, state, "inv_out_attr", "T_inv")

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}


# ─────────────────────────────────────────────────────────────────────────────
# PoseError  —  6-DOF pose error
# ─────────────────────────────────────────────────────────────────────────────

class PoseErrorNodeDef(NodeDef):
    """Compute 6-DOF pose error: e = [Δx,Δy,Δz,Δrx,Δry,Δrz].

    e = log(T_des⁻¹ ⊗ T_cur)  (spatial error)
    """
    TYPE     = "PoseError"
    CATEGORY = "Robotics"
    COLOR    = _C_SERVO
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = [
        "t_des_attr", "t_cur_attr", "error_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        dpg.add_text("e = [Δx Δy Δz Δrx Δry Δrz]",
                     color=(240, 170,  90, 200))

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _data_in(nid,  info, state, "t_des_attr",    "T_desired")
        _data_in(nid,  info, state, "t_cur_attr",    "T_current")
        _data_out(nid, info, state, "error_out_attr", "error[6]")

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}


# ─────────────────────────────────────────────────────────────────────────────
# JointState  —  N-DOF joint angle vector
# ─────────────────────────────────────────────────────────────────────────────

class JointStateNodeDef(NodeDef):
    """N-DOF joint angle vector (q₁…q₇, configurable 1–7 joints)."""
    TYPE     = "JointState"
    CATEGORY = "Robotics"
    COLOR    = _C_JOINT
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["q_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        ndof_tag = dpg.generate_uuid()
        dpg.add_combo(label="DOF", tag=ndof_tag, width=60,
                      items=["1","2","3","4","5","6","7"],
                      default_value="6",
                      callback=lambda s, a, u: _rebuild_joints(u["nid"],
                                                               u["info"],
                                                               int(a),
                                                               u["grp"]))
        grp = dpg.generate_uuid()
        dpg.add_group(tag=grp)
        ptags: dict[str, int] = {}
        with dpg.group(tag=grp):
            pass
        info["ndof_tag"] = ndof_tag
        info["joint_grp"] = grp
        info["params"]   = ptags
        # Draw initial 6-joint sliders
        _rebuild_joints(nid, info, 6, grp)
        # Store user_data for the combo callback AFTER info is populated
        dpg.configure_item(ndof_tag,
                           user_data={"nid": nid, "info": info, "grp": grp})

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _data_out(nid, info, state, "q_out_attr", "q[]")

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        ndof_tag = info.get("ndof_tag")
        ndof = int(dpg.get_value(ndof_tag)) if ndof_tag and dpg.does_item_exist(ndof_tag) else 6
        params = {
            k: round(float(dpg.get_value(v)), 6)
            for k, v in info.get("params", {}).items()
            if dpg.does_item_exist(v)
        }
        return {"ndof": ndof, "params": params}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        ndof_tag = info.get("ndof_tag")
        ndof = int(data.get("ndof", 6))
        if ndof_tag and dpg.does_item_exist(ndof_tag):
            dpg.set_value(ndof_tag, str(ndof))
        grp = info.get("joint_grp")
        if grp:
            _rebuild_joints(nid, info, ndof, grp)
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, float(v))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        params = {
            k: round(float(dpg.get_value(v)), 4) if dpg.does_item_exist(v) else 0.0
            for k, v in info.get("params", {}).items()
        }
        return {"type": self.TYPE, "name": info["label"], "params": params}


def _rebuild_joints(nid: int, info: dict, ndof: int, grp: int) -> None:
    """Recreate joint-angle sliders inside group ``grp`` for ``ndof`` joints."""
    if not dpg.does_item_exist(grp):
        return
    # Delete existing children
    for child in dpg.get_item_children(grp, slot=1):
        dpg.delete_item(child)
    ptags: dict[str, int] = {}
    with dpg.group(parent=grp):
        pass
    parent = grp
    for i in range(1, ndof + 1):
        key = f"q{i}"
        tag = dpg.generate_uuid()
        ptags[key] = tag
        dpg.add_drag_float(label=f"q{i}", tag=tag, width=140,
                           default_value=0.0, speed=0.01, format="%.3f",
                           parent=parent)
    info["params"] = ptags


# ─────────────────────────────────────────────────────────────────────────────
# ScalarToVector  —  pack 3 scalars → vector
# ─────────────────────────────────────────────────────────────────────────────

class ScalarToVectorNodeDef(NodeDef):
    """Pack three scalar inputs (X, Y, Z) into one vector data output."""
    TYPE     = "ScalarToVector"
    CATEGORY = "Robotics"
    COLOR    = _C_VEC
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = [
        "s_x_attr", "s_y_attr", "s_z_attr", "vec_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        # Tags are created here so they exist before build_extra_sockets runs.
        ptags: dict[str, int] = {name: dpg.generate_uuid()
                                  for name in ("x", "y", "z")}
        info["params"] = ptags
        dpg.add_spacer(width=130, height=1)   # fix minimum node width

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        for name, key in (("X", "s_x_attr"), ("Y", "s_y_attr"), ("Z", "s_z_attr")):
            ia = dpg.generate_uuid()
            info[key] = ia
            state.attr_to_node[ia] = nid
            ptag = info["params"][name.lower()]
            # wrap text+drag together so set_input_visibility can hide both
            grp = dpg.generate_uuid()
            info[f"s_{name.lower()}_grp"] = grp
            with dpg.node_attribute(tag=ia, attribute_type=dpg.mvNode_Attr_Input):
                with dpg.group(tag=grp):
                    dpg.add_text(name, indent=2)
                    dpg.add_drag_float(label=f"##{ptag}", tag=ptag, width=120,
                                       default_value=0.0, speed=0.01, format="%.4f")
        _data_out(nid, info, state, "vec_out_attr", "vector")

    def set_input_visibility(self, in_attr: int, show: bool,
                              nid: int, info: dict,
                              state: "GraphState") -> None:
        for key, pname in (("s_x_attr","x"), ("s_y_attr","y"), ("s_z_attr","z")):
            if info.get(key) == in_attr:
                # hide the whole group (text label + drag widget)
                grp = info.get(f"s_{pname}_grp")
                if grp and dpg.does_item_exist(grp):
                    dpg.configure_item(grp, show=show)
                return

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        return {"params": {
            k: round(float(dpg.get_value(v)), 6)
            for k, v in info.get("params", {}).items()
            if dpg.does_item_exist(v)
        }}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, float(v))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        vec = {k: round(float(dpg.get_value(v)), 4) if dpg.does_item_exist(v) else 0.0
               for k, v in info.get("params", {}).items()}
        return {"type": self.TYPE, "name": info["label"], "vector": vec}


# ─────────────────────────────────────────────────────────────────────────────
# VectorSplit  —  unpack vector → 3 scalar outputs
# ─────────────────────────────────────────────────────────────────────────────

class VectorSplitNodeDef(NodeDef):
    """Split a vector data input into X, Y, Z scalar output sockets."""
    TYPE     = "VectorSplit"
    CATEGORY = "Robotics"
    COLOR    = _C_VEC
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = [
        "vec_in_attr", "x_out_attr", "y_out_attr", "z_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        dpg.add_text("vec → x, y, z", color=(100, 200, 200, 200))

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _data_in(nid, info, state,  "vec_in_attr", "vector")
        _data_out(nid, info, state, "x_out_attr",  "X")
        _data_out(nid, info, state, "y_out_attr",  "Y")
        _data_out(nid, info, state, "z_out_attr",  "Z")

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}


# ─────────────────────────────────────────────────────────────────────────────
# Gain  —  scalar or vector gain (e.g. visual-servo λ)
# ─────────────────────────────────────────────────────────────────────────────

class GainNodeDef(NodeDef):
    """Multiply an input signal by a scalar gain λ.

    Commonly used as the control gain in image-based visual servo:
        u = λ · e
    """
    TYPE     = "Gain"
    CATEGORY = "Robotics"
    COLOR    = _C_SERVO
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["sig_in_attr", "sig_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        tag = dpg.generate_uuid()
        dpg.add_drag_float(label="λ (gain)", tag=tag, width=140,
                           default_value=0.5, min_value=0.0, max_value=100.0,
                           speed=0.001, format="%.4f")
        info["params"] = {"gain": tag}

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _data_in(nid,  info, state, "sig_in_attr",  "signal_in")
        _data_out(nid, info, state, "sig_out_attr", "signal_out")

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        tag = info.get("params", {}).get("gain")
        val = round(float(dpg.get_value(tag)), 6) if tag and dpg.does_item_exist(tag) else 0.5
        return {"params": {"gain": val}}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        tag = info.get("params", {}).get("gain")
        val = data.get("params", {}).get("gain", 0.5)
        if tag and dpg.does_item_exist(tag):
            dpg.set_value(tag, float(val))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        tag = info.get("params", {}).get("gain")
        val = round(float(dpg.get_value(tag)), 4) if tag and dpg.does_item_exist(tag) else 0.5
        return {"type": self.TYPE, "name": info["label"], "params": {"gain": val}}


# ─────────────────────────────────────────────────────────────────────────────
# DotProduct
# ─────────────────────────────────────────────────────────────────────────────

class DotProductNodeDef(NodeDef):
    """Compute the dot product of two equal-length vector inputs."""
    TYPE     = "DotProduct"
    CATEGORY = "Robotics"
    COLOR    = _C_VEC
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = [
        "va_in_attr", "vb_in_attr", "dot_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        dpg.add_text("a · b", color=(120, 210, 200, 200))

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _data_in(nid,  info, state, "va_in_attr",  "a")
        _data_in(nid,  info, state, "vb_in_attr",  "b")
        _data_out(nid, info, state, "dot_out_attr", "a·b")

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}


# ─────────────────────────────────────────────────────────────────────────────
# CrossProduct
# ─────────────────────────────────────────────────────────────────────────────

class CrossProductNodeDef(NodeDef):
    """Compute the 3D cross product a × b."""
    TYPE     = "CrossProduct"
    CATEGORY = "Robotics"
    COLOR    = _C_VEC
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = [
        "va_in_attr", "vb_in_attr", "cross_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        dpg.add_text("a × b", color=(120, 210, 200, 200))

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _data_in(nid,  info, state, "va_in_attr",     "a")
        _data_in(nid,  info, state, "vb_in_attr",     "b")
        _data_out(nid, info, state, "cross_out_attr", "a×b")

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}
