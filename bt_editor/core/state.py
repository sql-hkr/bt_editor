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
Shared runtime state for the Behaviour Tree editor graph.

Import the module-level singleton ``state`` everywhere:

    from bt_editor.core.state import state
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GraphState:
    # ── Graph data ────────────────────────────────────────────────────────────
    nodes:        dict[int, dict]  = field(default_factory=dict)   # nid → info
    links:        dict[int, tuple] = field(default_factory=dict)   # lid → (out_attr, in_attr)
    attr_to_node: dict[int, int]   = field(default_factory=dict)   # attr_id → nid
    blackboard:   dict[str, dict]  = field(default_factory=dict)   # key → {type,value,desc}
    clipboard:    list[dict]       = field(default_factory=list)

    # ── BT root tracking ──────────────────────────────────────────────────────
    root_nid: int = 0

    # ── DPG texture handles (populated during Application.__init__) ───────────
    tex_registry:       int        = 0
    tex_stage:          int        = 0
    node_textures:      dict[int, int]  = field(default_factory=dict)
    node_image_widgets: dict[int, int]  = field(default_factory=dict)
    node_images:        dict[int, Any]  = field(default_factory=dict)

    # ── Computed feature data (Vision nodes) ─────────────────────────────────
    node_data:          dict[int, Any]  = field(default_factory=dict)

    # ── Blackboard UI transient state ─────────────────────────────────────────
    bb_row_ids:     list[int] = field(default_factory=list)
    bb_editing_key: str       = ""

    def clear_graph(self) -> None:
        """Clear all graph data (nodes, links, images) while preserving handles."""
        self.nodes.clear()
        self.links.clear()
        self.attr_to_node.clear()
        for tex in self.node_textures.values():
            try:
                import dearpygui.dearpygui as dpg
                if dpg.does_item_exist(tex):
                    dpg.delete_item(tex)
            except Exception:
                pass
        self.node_textures.clear()
        self.node_image_widgets.clear()
        self.node_images.clear()
        self.node_data.clear()


# Module-level singleton — import this everywhere.
state = GraphState()
