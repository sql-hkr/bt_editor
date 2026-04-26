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
Decorator node definitions for the BT editor.

Decorators wrap exactly ONE child node and modify how its result is
interpreted or how many times it is ticked.

Included Decorators
-------------------
Inverter           — flips SUCCESS ↔ FAILURE
ForceSuccess       — always returns SUCCESS regardless of child
ForceFailure       — always returns FAILURE regardless of child
Repeat             — tick child N times (or until failure with option)
RetryUntilSuccess  — tick child until it returns SUCCESS (up to N attempts)
Timeout            — FAILURE if child takes longer than the time limit
SuccessIsRunning   — converts SUCCESS → RUNNING (for rate-limiting)
"""
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
import dearpygui.dearpygui as dpg

from bt_editor.core.node_def import NodeDef
from bt_editor.nodes.behaviours._base import ParamSpec

if TYPE_CHECKING:
    from bt_editor.core.state import GraphState


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _serialize_params(info: dict) -> dict:
    return {
        k: round(float(dpg.get_value(v)), 6)
        for k, v in info.get("params", {}).items()
        if dpg.does_item_exist(v)
    }


def _deserialize_params(info: dict, data: dict) -> None:
    for k, v in data.get("params", {}).items():
        tag = info.get("params", {}).get(k)
        if tag and dpg.does_item_exist(tag):
            dpg.set_value(tag, float(v))


# ─────────────────────────────────────────────────────────────────────────────
# Base: DecoratorNodeDef
# ─────────────────────────────────────────────────────────────────────────────

class DecoratorNodeDef(NodeDef):
    """Base for all Decorator nodes.

    Decorators accept ONE BT child (IS_CTRL=False keeps it as a pass-through
    socket — the JSON exporter's ``children`` list is expected to have len ≤ 1,
    and ``to_json`` uses ``child`` instead of ``children``).
    """
    CATEGORY:     ClassVar[str]             = "Decorators"
    COLOR:        ClassVar[tuple]           = (140, 60, 60)
    IS_CTRL:      ClassVar[bool]            = True   # allow one child wiring
    BT_OUT_LABEL: ClassVar[str]             = "child"   # decorators wrap exactly one child
    PARAMS:    ClassVar[list[ParamSpec]] = []

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        info["params"] = {}
        dpg.add_spacer(width=80, height=1)

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        p = _serialize_params(info)
        return {"params": p} if p else {}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        _deserialize_params(info, data)

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        p = {
            k: round(float(dpg.get_value(v)), 4) if dpg.does_item_exist(v) else 0.0
            for k, v in info.get("params", {}).items()
        }
        obj: dict = {"type": self.TYPE, "name": info["label"]}
        if p:
            obj["params"] = p
        # Decorators expose a single "child" key (not "children")
        if children:
            obj["child"] = children[0]
        return obj


# ─────────────────────────────────────────────────────────────────────────────
# Inverter
# ─────────────────────────────────────────────────────────────────────────────

class InverterNodeDef(DecoratorNodeDef):
    """flip SUCCESS ↔ FAILURE; RUNNING passes through unchanged."""
    TYPE  = "Inverter"
    COLOR = (175, 55, 55)

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        info["params"] = {}
        dpg.add_text("¬ child result", color=(210, 130, 130, 200))


# ─────────────────────────────────────────────────────────────────────────────
# ForceSuccess / ForceFailure
# ─────────────────────────────────────────────────────────────────────────────

class ForceSuccessNodeDef(DecoratorNodeDef):
    """Always return SUCCESS regardless of child result."""
    TYPE  = "ForceSuccess"
    COLOR = (40, 155, 80)

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        info["params"] = {}
        dpg.add_text("→ SUCCESS", color=(100, 220, 130, 200))


class ForceFailureNodeDef(DecoratorNodeDef):
    """Always return FAILURE regardless of child result."""
    TYPE  = "ForceFailure"
    COLOR = (180, 60, 40)

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        info["params"] = {}
        dpg.add_text("→ FAILURE", color=(240, 110, 90, 200))


# ─────────────────────────────────────────────────────────────────────────────
# Repeat
# ─────────────────────────────────────────────────────────────────────────────

class RepeatNodeDef(DecoratorNodeDef):
    """Tick child N times.

    Params:
        num_cycles: how many times to tick (0 = infinite)
    """
    TYPE  = "Repeat"
    COLOR = (130, 100, 30)

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        tag = dpg.generate_uuid()
        dpg.add_drag_int(label="Cycles", tag=tag, width=140,
                         default_value=1, min_value=0, max_value=9999,
                         speed=1)
        dpg.add_text("(0 = infinite)", color=(160, 160, 160, 180))
        info["params"] = {"num_cycles": tag}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, int(v))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        tag = info.get("params", {}).get("num_cycles")
        n = int(dpg.get_value(tag)) if tag and dpg.does_item_exist(tag) else 1
        obj: dict = {"type": self.TYPE, "name": info["label"],
                     "params": {"num_cycles": n}}
        if children:
            obj["child"] = children[0]
        return obj


# ─────────────────────────────────────────────────────────────────────────────
# RetryUntilSuccess
# ─────────────────────────────────────────────────────────────────────────────

class RetryUntilSuccessNodeDef(DecoratorNodeDef):
    """Tick child until it returns SUCCESS, up to 'num_attempts' times.

    Params:
        num_attempts: max retries (0 = infinite)
    """
    TYPE  = "RetryUntilSuccess"
    COLOR = (130, 80, 160)

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        tag = dpg.generate_uuid()
        dpg.add_drag_int(label="Attempts", tag=tag, width=140,
                         default_value=3, min_value=0, max_value=9999,
                         speed=1)
        dpg.add_text("(0 = infinite)", color=(160, 160, 160, 180))
        info["params"] = {"num_attempts": tag}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, int(v))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        tag = info.get("params", {}).get("num_attempts")
        n = int(dpg.get_value(tag)) if tag and dpg.does_item_exist(tag) else 3
        obj: dict = {"type": self.TYPE, "name": info["label"],
                     "params": {"num_attempts": n}}
        if children:
            obj["child"] = children[0]
        return obj


# ─────────────────────────────────────────────────────────────────────────────
# Timeout
# ─────────────────────────────────────────────────────────────────────────────

class TimeoutNodeDef(DecoratorNodeDef):
    """Return FAILURE if child does not complete within 'duration' seconds.

    Params:
        duration: time limit in seconds
    """
    TYPE  = "Timeout"
    COLOR = (160, 130, 30)

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        tag = dpg.generate_uuid()
        dpg.add_drag_float(label="Duration (s)", tag=tag, width=140,
                           default_value=5.0, min_value=0.0, max_value=600.0,
                           speed=0.1, format="%.1f")
        info["params"] = {"duration": tag}

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        tag = info.get("params", {}).get("duration")
        d = round(float(dpg.get_value(tag)), 2) if tag and dpg.does_item_exist(tag) else 5.0
        obj: dict = {"type": self.TYPE, "name": info["label"],
                     "params": {"duration": d}}
        if children:
            obj["child"] = children[0]
        return obj


# ─────────────────────────────────────────────────────────────────────────────
# SuccessIsRunning
# ─────────────────────────────────────────────────────────────────────────────

class SuccessIsRunningNodeDef(DecoratorNodeDef):
    """Map SUCCESS → RUNNING; useful as a rate-limiting or looping wrapper."""
    TYPE  = "SuccessIsRunning"
    COLOR = (60, 140, 160)

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        info["params"] = {}
        dpg.add_text("SUCCESS→RUNNING", color=(100, 200, 230, 200))
