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
Callbacks registered directly on node body widgets (combo, button, etc.).

These must NOT import from bt_editor.nodes.*  to avoid circular imports —
the node definitions import from this module to pass their callbacks to DPG.
"""
from __future__ import annotations
import os
import numpy as np
import cv2
import dearpygui.dearpygui as dpg

from bt_editor.core.state import state
from bt_editor.editor.image_pipeline import (
    eval_node, propagate_image, update_node_texture)


# ─────────────────────────────────────────────────────────────────────────────
# Blackboard node — Mode toggle
# ─────────────────────────────────────────────────────────────────────────────

def bb_node_mode_changed(sender, app_data, user_data) -> None:
    """Show/hide Blackboard output/input sockets when Read ↔ Write mode changes.

    Can be called programmatically (sender=None) during YAML deserialization.
    """
    nid  = user_data
    info = state.nodes.get(nid)
    if info is None:
        return
    is_read = (app_data == "Read")
    out_a   = info.get("bb_out_attr")
    in_a    = info.get("bb_in_attr")
    if out_a and dpg.does_item_exist(out_a):
        dpg.configure_item(out_a, show=is_read)
    if in_a and dpg.does_item_exist(in_a):
        dpg.configure_item(in_a, show=not is_read)
    # Disconnect links from the socket that just became hidden.
    hidden_attr = in_a if is_read else out_a
    for lid in [ld for ld, (o, i) in list(state.links.items())
                if o == hidden_attr or i == hidden_attr]:
        state.links.pop(lid, None)
        if dpg.does_item_exist(lid):
            dpg.delete_item(lid)


# ─────────────────────────────────────────────────────────────────────────────
# OpenCV node — Operation changed
# ─────────────────────────────────────────────────────────────────────────────

def opencv_op_changed(sender, app_data, user_data) -> None:
    nid = user_data
    eval_node(nid)
    propagate_image(nid)


# ─────────────────────────────────────────────────────────────────────────────
# Vision nodes — parameter changed (any slider/drag/checkbox)
# ─────────────────────────────────────────────────────────────────────────────

def vision_param_changed(sender, app_data, user_data) -> None:
    """Re-evaluate a Vision node whenever any of its parameter widgets change."""
    nid = user_data
    eval_node(nid)
    propagate_image(nid)


# ─────────────────────────────────────────────────────────────────────────────
# Image node — File selected
# ─────────────────────────────────────────────────────────────────────────────

def file_selected_callback(sender, app_data, user_data) -> None:
    """Called when the user confirms a file selection in an Image node dialog."""
    nid = user_data
    if nid not in state.nodes:
        return
    selections = app_data.get("selections", {})
    path = list(selections.values())[0] if selections else app_data.get("file_path_name", "")
    if not path:
        return

    path_tag = state.nodes[nid].get("path_tag")
    if path_tag and dpg.does_item_exist(path_tag):
        dpg.set_value(path_tag, os.path.basename(path))

    # Use np.fromfile + imdecode for robust Unicode/macOS path support.
    buf = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None:
        return

    state.node_images[nid] = img
    update_node_texture(nid, img)
    propagate_image(nid)
    state.nodes[nid]["image_path"] = path


# ─────────────────────────────────────────────────────────────────────────────
# TemplateMatch node — template file selection
# ─────────────────────────────────────────────────────────────────────────────

def tmpl_browse_callback(sender, app_data, user_data) -> None:
    """Called when the user selects a template image in a TemplateMatch node."""
    nid = user_data
    if nid not in state.nodes:
        return
    selections = app_data.get("selections", {})
    path = list(selections.values())[0] if selections else app_data.get("file_path_name", "")
    if not path:
        return

    buf = np.fromfile(path, dtype=np.uint8)
    tmpl = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if tmpl is None:
        return

    state.nodes[nid]["tmpl_image"] = tmpl
    state.nodes[nid]["tmpl_path"]  = path
    path_tag = state.nodes[nid].get("tmpl_path_tag")
    if path_tag and dpg.does_item_exist(path_tag):
        dpg.set_value(path_tag, os.path.basename(path))

    # Re-evaluate the node now that we have a template.
    from bt_editor.editor.image_pipeline import eval_node
    eval_node(nid)
    propagate_image(nid)
