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
Abstract base class for all node-type definitions.

Every node type (built-in or plugin) subclasses NodeDef, sets the required
ClassVars, and overrides the hook methods that differ from the defaults.
"""
from __future__ import annotations
from abc import ABC
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from bt_editor.core.state import GraphState


class NodeDef(ABC):
    """Defines the GUI appearance, widget construction, serialization, and
    JSON-export behaviour of a single node type.

    Subclassing recipe:
        1. Set TYPE (unique string) and CATEGORY.
        2. Set COLOR to an (r, g, b) tuple.
        3. Override BT socket ClassVars as needed.
        4. Override build_* hooks to add widgets/sockets.
        5. Override serialize / deserialize / to_json for I/O.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    TYPE:     ClassVar[str]                      # unique type string (= serialized name)
    CATEGORY: ClassVar[str]                      # Add-menu category label
    COLOR:    ClassVar[tuple[int, int, int]] = (80, 80, 80)

    # ── BT socket presence ────────────────────────────────────────────────────
    HAS_BT_IN:    ClassVar[bool] = True          # left "parent" input socket
    HAS_BT_OUT:   ClassVar[bool] = True          # right output socket
    BT_OUT_LABEL: ClassVar[str]  = "children"    # label on the BT output socket
    IS_CTRL:      ClassVar[bool] = False          # True for Sequence/Selector/Parallel

    # ── Image / texture ───────────────────────────────────────────────────────
    NEEDS_PREVIEW: ClassVar[bool] = False         # True for Image/OpenCV/ResultImage

    # ── Socket key registry (used for cleanup + YAML serialization) ───────────
    # List the node-info dict keys that hold DPG attr IDs beyond in_attr/out_attr.
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = []

    # ── Widget construction ───────────────────────────────────────────────────

    def build_extra_inputs(self, nid: int, info: dict,
                           state: "GraphState") -> None:
        """Build optional extra input socket attributes *before* the body.

        E.g. image-in for OpenCV, vector-in for VectorTransform.
        Update *info* with any new attr tag keys.
        """

    def build_body(self, nid: int, info: dict,
                   state: "GraphState") -> None:
        """Build DPG widgets inside the static body attribute.

        The factory opens/closes the body_attr context; just call dpg.add_*
        directly here. Update *info* with any widget tag keys.
        """

    def build_extra_sockets(self, nid: int, info: dict,
                            state: "GraphState") -> None:
        """Build special sockets/attributes *after* the body.

        E.g. image preview, P2P vector socket, Math A/B sockets,
        Blackboard Read/Write sockets, data output sockets.
        """

    # ── Serialization ─────────────────────────────────────────────────────────

    def serialize(self, nid: int, info: dict,
                  state: "GraphState") -> dict:
        """Return extra key–value pairs to embed in the YAML node entry.

        The factory always saves type/label/pos/collapsed/op/bb_key
        automatically; only return node-specific extras here.
        """
        return {}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        """Restore widget values from a YAML node-entry dict."""

    # ── JSON export ───────────────────────────────────────────────────────────

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        """Build the JSON representation of this node for BT export.

        *children* is the already-recursed list of child node JSON objects.
        """
        obj: dict = {"type": self.TYPE, "name": info["label"]}
        if children:
            obj["children"] = children
        return obj

    # ── Inline widget visibility (Blender-style hide-on-connect) ──────────────

    def set_input_visibility(self, in_attr: int, show: bool,
                              nid: int, info: dict,
                              state: "GraphState") -> None:
        """Show/hide any inline input widget when a wire is connected or removed.

        Only needed for nodes that have inline editable values on input sockets
        (Math A/B drag_float, P2P slider group).
        """
