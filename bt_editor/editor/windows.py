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
Blackboard window UI: table, form, CRUD callbacks.

The blackboard is a shared parameter registry accessible to all Blackboard
nodes in the graph.  This module handles:
  - Rendering the BB table rows
  - Add / Edit / Delete BB entries
  - Syncing Blackboard node Key-combo dropdowns
"""
from __future__ import annotations
import dearpygui.dearpygui as dpg

from bt_editor.constants import (
    BB_WIN_TAG, BB_TABLE_TAG,
    BB_KEY_TAG, BB_TYPE_TAG, BB_VAL_TAG, BB_DESC_TAG, BB_TYPES)
from bt_editor.core.state import state


# ─────────────────────────────────────────────────────────────────────────────
# Value coercion
# ─────────────────────────────────────────────────────────────────────────────

def _bb_coerce_value(type_: str, raw: str):
    """Cast *raw* string to the target blackboard type."""
    try:
        if type_ == "float":
            return float(raw)
        if type_ == "int":
            return int(float(raw))
        if type_ == "bool":
            return raw.strip().lower() in ("true", "1", "yes")
        if type_ in ("vector2", "vector3", "vector6"):
            size    = {"vector2": 2, "vector3": 3, "vector6": 6}[type_]
            cleaned = str(raw).replace("[", "").replace("]", "")
            parts   = [p.strip() for p in cleaned.split(",") if p.strip()]
            vals: list[float] = []
            for p in parts:
                try:
                    vals.append(float(p))
                except (ValueError, TypeError):
                    vals.append(0.0)
            while len(vals) < size:
                vals.append(0.0)
            return vals[:size]
        return str(raw)
    except (ValueError, TypeError):
        return str(raw)


# ─────────────────────────────────────────────────────────────────────────────
# Node key-combo sync
# ─────────────────────────────────────────────────────────────────────────────

def bb_sync_node_key_combos(deleted_key: str = "") -> None:
    """Update all Blackboard node Key-combos to reflect the current blackboard.

    If *deleted_key* is provided, reset any node that had that key selected.
    """
    keys = list(state.blackboard.keys())
    for nid, info in state.nodes.items():
        if info.get("type") != "Blackboard":
            continue
        kt = info.get("bb_key_tag")
        if not (kt and dpg.does_item_exist(kt)):
            continue
        dpg.configure_item(kt, items=keys)
        if deleted_key and dpg.get_value(kt) == deleted_key:
            dpg.set_value(kt, "")


# ─────────────────────────────────────────────────────────────────────────────
# Table rendering
# ─────────────────────────────────────────────────────────────────────────────

def bb_refresh_table() -> None:
    if not dpg.does_item_exist(BB_TABLE_TAG):
        return
    for row_id in state.bb_row_ids:
        if dpg.does_item_exist(row_id):
            dpg.delete_item(row_id)
    state.bb_row_ids.clear()
    for key, entry in state.blackboard.items():
        row_id = dpg.generate_uuid()
        state.bb_row_ids.append(row_id)
        with dpg.table_row(parent=BB_TABLE_TAG, tag=row_id):
            dpg.add_text(key)
            dpg.add_text(entry.get("type", ""))
            dpg.add_text(str(entry.get("value", "")))
            dpg.add_text(entry.get("description", ""))
            with dpg.group(horizontal=True):
                dpg.add_button(label="Edit", width=46,
                               callback=_bb_edit_button, user_data=key)
                dpg.add_button(label="Del",  width=40,
                               callback=_bb_delete_button, user_data=key)


# ─────────────────────────────────────────────────────────────────────────────
# Entry CRUD callbacks
# ─────────────────────────────────────────────────────────────────────────────

def _bb_edit_button(sender, app_data, user_data) -> None:
    key   = user_data
    entry = state.blackboard.get(key, {})
    state.bb_editing_key = key
    if dpg.does_item_exist(BB_KEY_TAG):
        dpg.set_value(BB_KEY_TAG, key)
    if dpg.does_item_exist(BB_TYPE_TAG):
        dpg.set_value(BB_TYPE_TAG, entry.get("type", "float"))
    if dpg.does_item_exist(BB_VAL_TAG):
        dpg.set_value(BB_VAL_TAG, str(entry.get("value", "")))
    if dpg.does_item_exist(BB_DESC_TAG):
        dpg.set_value(BB_DESC_TAG, entry.get("description", ""))


def _bb_delete_button(sender, app_data, user_data) -> None:
    key = user_data
    state.blackboard.pop(key, None)
    bb_refresh_table()
    bb_sync_node_key_combos(deleted_key=key)


def bb_apply_entry(sender, app_data, user_data) -> None:
    key   = (dpg.get_value(BB_KEY_TAG) or "").strip()
    type_ = dpg.get_value(BB_TYPE_TAG) or "float"
    raw   = dpg.get_value(BB_VAL_TAG)  or ""
    desc  = dpg.get_value(BB_DESC_TAG) or ""
    if not key:
        return
    editing = state.bb_editing_key
    if editing and editing != key and editing in state.blackboard:
        del state.blackboard[editing]
    state.blackboard[key] = {
        "type":        type_,
        "value":       _bb_coerce_value(type_, raw),
        "description": desc,
    }
    state.bb_editing_key = ""
    dpg.set_value(BB_KEY_TAG,  "")
    dpg.set_value(BB_VAL_TAG,  "")
    dpg.set_value(BB_DESC_TAG, "")
    bb_refresh_table()
    bb_sync_node_key_combos()


# ─────────────────────────────────────────────────────────────────────────────
# Show callback
# ─────────────────────────────────────────────────────────────────────────────

def show_blackboard_callback() -> None:
    if dpg.does_item_exist(BB_WIN_TAG):
        dpg.configure_item(BB_WIN_TAG, show=True)
