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
Core editor callbacks: link/delink, delete, clear, execution-order refresh,
collapse/expand, mouse helpers, and node management utilities.
"""
from __future__ import annotations
import dearpygui.dearpygui as dpg

from bt_editor.constants import EDITOR_TAG, EDITOR_WIN, ROOT_TYPE, ROOT_NODE_LABEL
from bt_editor.core.state import state
from bt_editor.core.registry import registry
from bt_editor.core.utils import all_attr_ids
from bt_editor.editor.factory import add_node
from bt_editor.editor.image_pipeline import eval_node, propagate_image
from bt_editor.editor.themes import node_theme


# ─────────────────────────────────────────────────────────────────────────────
# Input visibility helper
# ─────────────────────────────────────────────────────────────────────────────

def set_input_visibility(in_attr: int, show: bool) -> None:
    """Show/hide the inline value widget for an input socket (Blender-style)."""
    nid = state.attr_to_node.get(in_attr)
    if nid is None:
        return
    info = state.nodes.get(nid)
    if info is None:
        return
    defn = registry.get(info["type"])
    if defn:
        defn.set_input_visibility(in_attr, show, nid, info, state)


# ─────────────────────────────────────────────────────────────────────────────
# Link / delink callbacks
# ─────────────────────────────────────────────────────────────────────────────

def link_callback(sender, app_data) -> None:
    out_attr, in_attr = app_data[0], app_data[1]

    # Skip duplicate links.
    if any(o == out_attr and i == in_attr for o, i in state.links.values()):
        return

    # BT Root allows only one child.
    src_nid = state.attr_to_node.get(out_attr)
    if src_nid and state.nodes.get(src_nid, {}).get("type") == ROOT_TYPE:
        existing = [l for l, (o, _) in state.links.items() if o == out_attr]
        if existing:
            return   # reject: Root already has a child

    # Remove any existing link into this input socket.
    for old_lid in [l for l, (o, i) in list(state.links.items()) if i == in_attr]:
        state.links.pop(old_lid)
        if dpg.does_item_exist(old_lid):
            dpg.delete_item(old_lid)

    lid = dpg.generate_uuid()
    dpg.add_node_link(out_attr, in_attr, parent=EDITOR_TAG, tag=lid)
    state.links[lid] = (out_attr, in_attr)
    set_input_visibility(in_attr, show=False)

    # Propagate image data immediately if source has a loaded image.
    dst_nid = state.attr_to_node.get(in_attr)
    if src_nid in state.node_images and dst_nid in state.nodes:
        eval_node(dst_nid)
        propagate_image(dst_nid)

    refresh_execution_order()


def delink_callback(sender, app_data) -> None:
    lid = app_data
    if lid in state.links:
        out_attr, in_attr = state.links.pop(lid)
        set_input_visibility(in_attr, show=True)
        dst_nid = state.attr_to_node.get(in_attr)
        if dst_nid and dst_nid in state.nodes:
            eval_node(dst_nid)
            propagate_image(dst_nid)
    if dpg.does_item_exist(lid):
        dpg.delete_item(lid)
    refresh_execution_order()


# ─────────────────────────────────────────────────────────────────────────────
# Delete / Clear
# ─────────────────────────────────────────────────────────────────────────────

def delete_selected_callback() -> None:
    selected = dpg.get_selected_nodes(EDITOR_TAG)
    if not selected:
        return
    for nid in selected:
        if nid not in state.nodes:
            continue
        if nid == state.root_nid:
            continue    # Root is protected
        _delete_node(nid)


def _delete_node(nid: int) -> None:
    info = state.nodes.pop(nid)
    defn = registry.get(info["type"])

    # Remove attr → node mappings.
    for attr in all_attr_ids(nid, info, registry):
        state.attr_to_node.pop(attr, None)

    # Remove texture.
    tex = state.node_textures.pop(nid, None)
    if tex and dpg.does_item_exist(tex):
        dpg.delete_item(tex)
    state.node_image_widgets.pop(nid, None)
    state.node_images.pop(nid, None)
    state.node_data.pop(nid, None)

    # Remove all links touching this node.
    all_attrs = all_attr_ids(nid, info, registry)
    for lid in [l for l, (o, i) in list(state.links.items())
                if o in all_attrs or i in all_attrs]:
        state.links.pop(lid, None)
        if dpg.does_item_exist(lid):
            dpg.delete_item(lid)

    if dpg.does_item_exist(nid):
        dpg.delete_item(nid)


def _tex_registry_clear() -> None:
    """Delete all per-node textures without touching the registry itself."""
    for nid in list(state.node_textures):
        tex = state.node_textures.pop(nid, None)
        if tex and dpg.does_item_exist(tex):
            dpg.delete_item(tex)
    state.node_image_widgets.clear()
    state.node_images.clear()


def clear_all_callback() -> None:
    """Delete every node and link, then recreate the BT Root."""
    for lid in list(state.links):
        if dpg.does_item_exist(lid):
            dpg.delete_item(lid)
    state.links.clear()
    for nid in list(state.nodes):
        if dpg.does_item_exist(nid):
            dpg.delete_item(nid)
    state.nodes.clear()
    state.attr_to_node.clear()
    _tex_registry_clear()
    ensure_root_node()


# ─────────────────────────────────────────────────────────────────────────────
# BT Root management
# ─────────────────────────────────────────────────────────────────────────────

def ensure_root_node() -> None:
    """Guarantee that exactly one BT Root node exists; update state.root_nid."""
    if state.root_nid in state.nodes:
        return
    nid = add_node(ntype=ROOT_TYPE, label=ROOT_NODE_LABEL)
    state.root_nid = nid
    if dpg.does_item_exist(nid):
        dpg.set_item_pos(nid, [60.0, 60.0])


# ─────────────────────────────────────────────────────────────────────────────
# Execution order
# ─────────────────────────────────────────────────────────────────────────────

def refresh_execution_order() -> None:
    """Number child-node 'parent' labels by top-to-bottom (Y-position) order."""
    # Reset all labels first.
    for nid, info in state.nodes.items():
        otag = info.get("order_tag")
        if otag and dpg.does_item_exist(otag):
            dpg.set_value(otag, "parent")

    # For each control node (Sequence / Selector / Parallel), sort children
    # by Y position and number them.
    ctrl_types = registry.ctrl_types
    for nid, info in state.nodes.items():
        if info["type"] not in ctrl_types:
            continue
        out_a = info.get("out_attr")
        if out_a is None:
            continue
        children = [state.attr_to_node.get(in_a)
                    for _, (o, in_a) in state.links.items()
                    if o == out_a]
        children = [c for c in children if c in state.nodes]
        children.sort(key=lambda c: (
            dpg.get_item_pos(c)[1] if dpg.does_item_exist(c) else 0))
        for idx, child_nid in enumerate(children, 1):
            otag = state.nodes[child_nid].get("order_tag")
            if otag and dpg.does_item_exist(otag):
                dpg.set_value(otag, f"↑ {idx}")


# ─────────────────────────────────────────────────────────────────────────────
# Collapse / expand
# ─────────────────────────────────────────────────────────────────────────────

def toggle_collapse(nid: int) -> None:
    if nid not in state.nodes:
        return
    info      = state.nodes[nid]
    collapsed = not info.get("collapsed", False)
    info["collapsed"] = collapsed
    body = info.get("body_attr")
    if body and dpg.does_item_exist(body):
        dpg.configure_item(body, show=not collapsed)
    prefix = "▶ " if collapsed else ""
    if dpg.does_item_exist(nid):
        dpg.configure_item(nid, label=f"{prefix}{info['label']}")


# ─────────────────────────────────────────────────────────────────────────────
# Mouse callbacks
# ─────────────────────────────────────────────────────────────────────────────

def mouse_release_callback(sender, app_data) -> None:
    if app_data == dpg.mvMouseButton_Left:
        refresh_execution_order()


# ─────────────────────────────────────────────────────────────────────────────
# Demo preset
# ─────────────────────────────────────────────────────────────────────────────

def load_demo_callback() -> None:
    """Build a small demo graph: Root -> Sequence -> [Condition, Action]."""
    clear_all_callback()    # also recreates root
    root_nid = state.root_nid
    seq_id  = add_node("Sequence",         "Main Seq")
    cond_id = add_node("Condition (True)", "Is Ready?")
    act_id  = add_node("Action (Success)", "Do Task")
    dpg.set_item_pos(root_nid, [60,  80])
    dpg.set_item_pos(seq_id,   [260, 80])
    dpg.set_item_pos(cond_id,  [460, 30])
    dpg.set_item_pos(act_id,   [460, 140])

    def _link(src_nid, dst_nid):
        lid = dpg.generate_uuid()
        dpg.add_node_link(
            state.nodes[src_nid]["out_attr"],
            state.nodes[dst_nid]["in_attr"],
            parent=EDITOR_TAG, tag=lid)
        state.links[lid] = (
            state.nodes[src_nid]["out_attr"],
            state.nodes[dst_nid]["in_attr"])

    _link(root_nid, seq_id)
    _link(seq_id,   cond_id)
    _link(seq_id,   act_id)
    refresh_execution_order()


# ─────────────────────────────────────────────────────────────────────────────
# Coordinate helpers
# ─────────────────────────────────────────────────────────────────────────────

def editor_origin() -> tuple[float, float]:
    try:
        rm = dpg.get_item_state(EDITOR_WIN)["rect_min"]
        return float(rm[0]), float(rm[1])
    except Exception:
        return 0.0, 0.0


def canvas_mouse_pos() -> tuple[float, float]:
    """Mouse position in node-editor canvas space (handles panning)."""
    mx, my = dpg.get_mouse_pos(local=False)
    for nid in state.nodes:
        if dpg.does_item_exist(nid):
            try:
                cp = dpg.get_item_pos(nid)
                sp = dpg.get_item_rect_min(nid)
                return mx - (sp[0] - cp[0]), my - (sp[1] - cp[1])
            except Exception:
                break
    ox, oy = editor_origin()
    return mx - ox, my - oy


def pan_nodes(dx: float, dy: float) -> None:
    for nid in list(state.nodes):
        if dpg.does_item_exist(nid):
            p = dpg.get_item_pos(nid)
            dpg.set_item_pos(nid, [p[0] + dx, p[1] + dy])


def over_editor() -> bool:
    if dpg.does_item_exist(EDITOR_TAG) and dpg.is_item_hovered(EDITOR_TAG):
        return True
    if dpg.does_item_exist(EDITOR_WIN) and dpg.is_item_hovered(EDITOR_WIN):
        return True
    return False
