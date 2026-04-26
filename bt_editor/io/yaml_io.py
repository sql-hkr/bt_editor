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
YAML serialization: save and load the full graph (nodes, links, blackboard).
"""
from __future__ import annotations
import os
import numpy as np
import cv2
import yaml
import dearpygui.dearpygui as dpg

from bt_editor.constants import (
    YAML_SAVE_WIN_TAG, YAML_SAVE_PATH_TAG, YAML_LOAD_DLG_TAG,
    EDITOR_TAG, ROOT_TYPE)
from bt_editor.core.state import state
from bt_editor.core.registry import registry
from bt_editor.core.utils import attr_to_socket_key, socket_key_to_attr
from bt_editor.editor.factory import add_node
from bt_editor.editor.callbacks import (
    clear_all_callback, ensure_root_node,
    toggle_collapse, set_input_visibility, refresh_execution_order)
from bt_editor.editor.image_pipeline import update_node_texture, propagate_image, eval_node
from bt_editor.editor.windows import bb_refresh_table, bb_sync_node_key_combos
from bt_editor.editor.node_callbacks import bb_node_mode_changed


# ─────────────────────────────────────────────────────────────────────────────
# Build serialization dict
# ─────────────────────────────────────────────────────────────────────────────

def build_yaml_data() -> dict:
    node_list:  list[dict] = []
    nid_to_idx: dict[int, int] = {}

    for idx, (nid, info) in enumerate(state.nodes.items()):
        nid_to_idx[nid] = idx
        defn = registry.get(info["type"])
        entry: dict = {
            "type":      info["type"],
            "label":     info["label"],
            "pos":       [round(v, 1) for v in dpg.get_item_pos(nid)]
                         if dpg.does_item_exist(nid) else [0.0, 0.0],
            "collapsed": info.get("collapsed", False),
        }
        # Ask the NodeDef for type-specific extras (params, op, bb_key, …)
        if defn:
            entry.update(defn.serialize(nid, info, state))
        node_list.append(entry)

    link_list: list[dict] = []
    for _lid, (out_a, in_a) in state.links.items():
        src = state.attr_to_node.get(out_a)
        dst = state.attr_to_node.get(in_a)
        if src is None or dst is None:
            continue
        fs = attr_to_socket_key(src, out_a, state, registry)
        ts = attr_to_socket_key(dst, in_a,  state, registry)
        if fs is None or ts is None:
            continue
        link_list.append({
            "from_node":   nid_to_idx[src],
            "from_socket": fs,
            "to_node":     nid_to_idx[dst],
            "to_socket":   ts,
        })

    return {"nodes": node_list, "links": link_list,
            "blackboard": dict(state.blackboard)}


# ─────────────────────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────────────────────

def save_yaml_callback() -> None:
    if dpg.does_item_exist(YAML_SAVE_WIN_TAG):
        dpg.configure_item(YAML_SAVE_WIN_TAG, show=True)


def do_save_yaml(sender, app_data, user_data) -> None:
    path = (dpg.get_value(YAML_SAVE_PATH_TAG) or "").strip()
    if not path:
        return
    if not (path.endswith(".yaml") or path.endswith(".yml")):
        path += ".yaml"
    try:
        data = build_yaml_data()
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True,
                      sort_keys=False, default_flow_style=False)
        dpg.configure_item(YAML_SAVE_WIN_TAG, show=False)
    except Exception as exc:
        print(f"[YAML] Save error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Load
# ─────────────────────────────────────────────────────────────────────────────

def load_yaml_callback() -> None:
    if dpg.does_item_exist(YAML_LOAD_DLG_TAG):
        dpg.show_item(YAML_LOAD_DLG_TAG)


def yaml_load_file_callback(sender, app_data, user_data) -> None:
    selections = app_data.get("selections", {})
    path = list(selections.values())[0] if selections else app_data.get("file_path_name", "")
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        load_yaml_data(data)
    except Exception as exc:
        print(f"[YAML] Load error: {exc}")


def load_yaml_data(data: dict) -> None:
    """Reconstruct the graph from a YAML data dict."""
    clear_all_callback()    # also recreates root
    node_entries  = data.get("nodes", [])
    created_nids: list[int] = []

    # If the first YAML node is BT Root, reuse the auto-created root slot.
    yaml_has_root = (bool(node_entries)
                     and node_entries[0].get("type") == ROOT_TYPE)
    if yaml_has_root and state.root_nid in state.nodes:
        root_info = state.nodes.pop(state.root_nid)
        for ak in ("in_attr", "out_attr"):
            state.attr_to_node.pop(root_info.get(ak), None)
        if dpg.does_item_exist(state.root_nid):
            dpg.delete_item(state.root_nid)
        state.root_nid = 0

    for entry in node_entries:
        nid = add_node(ntype=entry.get("type", "Sequence"),
                       label=entry.get("label", ""))
        created_nids.append(nid)
        if len(created_nids) == 1 and yaml_has_root:
            state.root_nid = nid

        pos = entry.get("pos", [0.0, 0.0])
        if dpg.does_item_exist(nid):
            dpg.set_item_pos(nid, [float(pos[0]), float(pos[1])])

        info = state.nodes[nid]
        defn = registry.get(info["type"])
        if defn:
            defn.deserialize(nid, info, state, entry)

        if entry.get("collapsed", False):
            toggle_collapse(nid)

    for lentry in data.get("links", []):
        fi = lentry.get("from_node")
        ti = lentry.get("to_node")
        fs = lentry.get("from_socket")
        ts = lentry.get("to_socket")
        if fi is None or ti is None:
            continue
        if fi >= len(created_nids) or ti >= len(created_nids):
            continue
        src_nid = created_nids[fi]
        dst_nid = created_nids[ti]
        out_attr = socket_key_to_attr(src_nid, fs, state)
        in_attr  = socket_key_to_attr(dst_nid, ts, state)
        if out_attr is None or in_attr is None:
            continue
        lid = dpg.generate_uuid()
        dpg.add_node_link(out_attr, in_attr, parent=EDITOR_TAG, tag=lid)
        state.links[lid] = (out_attr, in_attr)
        set_input_visibility(in_attr, show=False)
        # Propagate image data if source already has a loaded image.
        if src_nid in state.node_images and dst_nid in state.nodes:
            eval_node(dst_nid)
            propagate_image(dst_nid)

    refresh_execution_order()

    # Restore blackboard entries.
    state.blackboard.clear()
    state.blackboard.update(data.get("blackboard", {}))
    bb_refresh_table()
    bb_sync_node_key_combos()
