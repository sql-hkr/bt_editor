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
JSON export: recursively builds a JSON representation of the BT graph
starting from the BT Root, then displays it in the JSON export window.
"""
from __future__ import annotations
import json
import dearpygui.dearpygui as dpg

from bt_editor.constants import JSON_WIN_TAG, JSON_TEXT_TAG
from bt_editor.core.state import state
from bt_editor.core.registry import registry


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_children_map_sorted() -> tuple[dict, set]:
    """Build a {parent_nid: [child_nid, …]} map from all current links.

    Children are sorted by ascending Y position (top → bottom).
    """
    children_map: dict[int, list[int]] = {}
    child_set:    set[int]             = set()
    for _, (out_a, in_a) in state.links.items():
        p = state.attr_to_node.get(out_a)
        c = state.attr_to_node.get(in_a)
        if p and c:
            children_map.setdefault(p, []).append(c)
            child_set.add(c)
    for p in children_map:
        children_map[p].sort(key=lambda c: (
            dpg.get_item_pos(c)[1] if dpg.does_item_exist(c) else 0))
    return children_map, child_set


def _build_json_tree(nid: int, children_map: dict) -> dict:
    """Recursively build a JSON-serialisable dict for the subtree rooted at *nid*."""
    if nid not in state.nodes:
        return {}
    info = state.nodes[nid]
    defn = registry.get(info["type"])
    if defn is None:
        return {"type": info["type"], "name": info["label"]}
    child_nids = children_map.get(nid, [])
    children   = [_build_json_tree(c, children_map) for c in child_nids]
    return defn.to_json(nid, info, state, children)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def build_json_export() -> dict:
    """Return the full export dict ``{blackboard, tree}`` without touching DPG UI."""
    from bt_editor.editor.callbacks import ensure_root_node
    ensure_root_node()
    if state.root_nid not in state.nodes:
        return {}
    children_map, _ = _build_children_map_sorted()
    tree_obj = _build_json_tree(state.root_nid, children_map)
    return {"blackboard": dict(state.blackboard), "tree": tree_obj}


def show_json_callback() -> None:
    """Build the BT JSON tree from the root node and display it."""
    from bt_editor.editor.callbacks import ensure_root_node
    ensure_root_node()
    if state.root_nid not in state.nodes:
        return
    children_map, _ = _build_children_map_sorted()
    tree_obj = _build_json_tree(state.root_nid, children_map)
    export   = {"blackboard": dict(state.blackboard), "tree": tree_obj}
    json_str = json.dumps(export, ensure_ascii=False, indent=2)
    if dpg.does_item_exist(JSON_WIN_TAG):
        dpg.set_value(JSON_TEXT_TAG, json_str)
        dpg.configure_item(JSON_WIN_TAG, show=True)
