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
Sibling-dim effect: dims all nodes that are NOT in the selected node's
sibling group (nodes that share the same BT parent).

update_sibling_dim() is called once per render frame.
"""
from __future__ import annotations
import dearpygui.dearpygui as dpg

from bt_editor.constants import EDITOR_TAG
from bt_editor.core.state import state
from bt_editor.editor.themes import node_theme, node_dim_theme

# Module-level change-detection state
_dimmed_nids:           set[int]        = set()
_prev_selected_for_dim: frozenset[int]  = frozenset()


def update_sibling_dim() -> None:
    """Called every frame; re-applies dim themes only when selection changes."""
    global _dimmed_nids, _prev_selected_for_dim

    selected = frozenset(dpg.get_selected_nodes(EDITOR_TAG))
    if selected == _prev_selected_for_dim:
        return
    _prev_selected_for_dim = selected

    # Restore all currently-dimmed nodes first.
    for nid in list(_dimmed_nids):
        if nid in state.nodes and dpg.does_item_exist(nid):
            dpg.bind_item_theme(nid, node_theme(state.nodes[nid]["type"]))
    _dimmed_nids.clear()

    if not selected:
        return   # nothing selected → everything normal

    # Collect the sibling group: for each selected node, find its parent and
    # add all of that parent's children to the highlight set.
    highlight: set[int] = set(selected)
    for nid in selected:
        in_a = state.nodes[nid].get("in_attr")
        if in_a is None:
            continue
        parent_out = None
        for _, (o, i) in state.links.items():
            if i == in_a:
                parent_out = o
                break
        if parent_out is None:
            continue
        for _, (o, i) in state.links.items():
            if o == parent_out:
                sibling = state.attr_to_node.get(i)
                if sibling:
                    highlight.add(sibling)

    # Dim every node not in the highlight set.
    for nid, info in state.nodes.items():
        if nid not in highlight and dpg.does_item_exist(nid):
            dpg.bind_item_theme(nid, node_dim_theme(info["type"]))
            _dimmed_nids.add(nid)
