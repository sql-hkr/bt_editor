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
Application entry point.

Builds and runs the Behaviour Tree Editor GUI.

    from bt_editor.app import Application
    Application().run()
"""
from __future__ import annotations
import os
import dearpygui.dearpygui as dpg

# Register all built-in node types (side-effect import).
import bt_editor.nodes  # noqa: F401

from bt_editor.constants import (
    EDITOR_TAG, EDITOR_WIN,
    JSON_WIN_TAG, JSON_TEXT_TAG,
    YAML_SAVE_WIN_TAG, YAML_SAVE_PATH_TAG, YAML_LOAD_DLG_TAG,
    BB_WIN_TAG, BB_TABLE_TAG,
    BB_KEY_TAG, BB_TYPE_TAG, BB_VAL_TAG, BB_DESC_TAG, BB_TYPES,
)
from bt_editor.core.state import state
from bt_editor.core.registry import registry

from bt_editor.editor.themes import build_global_theme, setup_fonts
from bt_editor.editor.dimmer import update_sibling_dim
from bt_editor.editor.callbacks import (
    link_callback, delink_callback,
    delete_selected_callback, clear_all_callback,
    load_demo_callback, ensure_root_node,
    mouse_release_callback,
)
from bt_editor.editor.clipboard import copy_callback, paste_callback
from bt_editor.editor.windows import show_blackboard_callback, bb_apply_entry
from bt_editor.editor.context_menu import (
    build_context_menu, node_right_click_callback,
    close_ctx_if_outside, close_ctx_on_escape,
)
from bt_editor.editor.debug_overlay import (
    build_debug_overlay, update_debug_overlay, toggle_debug_overlay,
)
from bt_editor.editor.factory import add_node

from bt_editor.io.yaml_io import (
    save_yaml_callback, do_save_yaml,
    load_yaml_callback, yaml_load_file_callback,
)
from bt_editor.io.json_export import show_json_callback


def _menu_add_node(sender, app_data, user_data) -> None:
    add_node(ntype=user_data)


class Application:
    """Encapsulates the full DPG application lifecycle."""

    def run(self) -> None:
        dpg.create_context()

        # Texture registry + stage (must exist before any node is created).
        state.tex_registry = dpg.add_texture_registry()
        state.tex_stage    = dpg.add_stage()

        # Fonts – load a system monospace font covering all Unicode glyphs used
        # in the app (box-drawing, block elements, Greek, arrows, math, …).
        _font = setup_fonts(14.0)
        if _font:
            dpg.bind_font(_font)

        dpg.bind_theme(build_global_theme())

        # ── Main window ───────────────────────────────────────────────────────
        with dpg.window(label="Behaviour Tree Editor", tag="main_window",
                        width=1300, height=840, no_close=True):

            # ── Menu bar ──────────────────────────────────────────────────────
            with dpg.menu_bar():
                with dpg.menu(label="File"):
                    dpg.add_menu_item(label="Save YAML…",
                                      callback=save_yaml_callback)
                    dpg.add_menu_item(label="Load YAML…",
                                      callback=load_yaml_callback)

                with dpg.menu(label="Add"):
                    for cat, types in registry.categories.items():
                        if not types or cat.startswith("_"):
                            continue
                        with dpg.menu(label=cat):
                            for ntype in types:
                                dpg.add_menu_item(label=ntype,
                                                  callback=_menu_add_node,
                                                  user_data=ntype)

                with dpg.menu(label="Edit"):
                    dpg.add_menu_item(label="Delete Selected",
                                      callback=delete_selected_callback)
                    dpg.add_menu_item(label="Clear All",
                                      callback=clear_all_callback)
                    dpg.add_separator()
                    dpg.add_menu_item(label="Load Demo",
                                      callback=load_demo_callback)

                with dpg.menu(label="Run"):
                    dpg.add_menu_item(label="Export JSON",
                                      callback=show_json_callback)

                with dpg.menu(label="View"):
                    dpg.add_menu_item(label="Blackboard…",
                                      callback=show_blackboard_callback)
                    dpg.add_menu_item(label="Debug Overlay  (F3)",
                                      callback=toggle_debug_overlay)

            # ── Node editor ───────────────────────────────────────────────────
            with dpg.child_window(width=-1, height=-1,
                                  no_scrollbar=True, border=False,
                                  tag=EDITOR_WIN):
                with dpg.node_editor(tag=EDITOR_TAG,
                                     callback=link_callback,
                                     delink_callback=delink_callback,
                                     minimap=True,
                                     minimap_location=dpg.mvNodeMiniMap_Location_BottomRight):
                    pass

        # ── JSON export window ────────────────────────────────────────────────
        with dpg.window(label="BT JSON Export", tag=JSON_WIN_TAG,
                        width=600, height=500, show=False, no_scrollbar=False):
            dpg.add_input_text(tag=JSON_TEXT_TAG, multiline=True,
                               width=-1, height=-1,
                               default_value="", readonly=True)

        # ── YAML save window ──────────────────────────────────────────────────
        with dpg.window(label="Save YAML", tag=YAML_SAVE_WIN_TAG,
                        width=520, height=114, show=False, no_collapse=True):
            dpg.add_text("Output path:")
            dpg.add_input_text(label="##yaml_save_path",
                               tag=YAML_SAVE_PATH_TAG, width=490,
                               default_value=os.path.join(os.getcwd(), "graph.yaml"))
            with dpg.group(horizontal=True):
                dpg.add_button(label="Save",   callback=do_save_yaml, width=80)
                dpg.add_button(
                    label="Cancel", width=80,
                    callback=lambda: dpg.configure_item(YAML_SAVE_WIN_TAG, show=False))

        # ── YAML load dialog ──────────────────────────────────────────────────
        dpg.add_file_dialog(label="Load YAML", tag=YAML_LOAD_DLG_TAG,
                            callback=yaml_load_file_callback,
                            width=700, height=420, show=False)
        dpg.add_file_extension(".yaml", parent=YAML_LOAD_DLG_TAG,
                               color=(100, 220, 180, 255))
        dpg.add_file_extension(".yml",  parent=YAML_LOAD_DLG_TAG,
                               color=(100, 220, 180, 255))
        dpg.add_file_extension(".*",    parent=YAML_LOAD_DLG_TAG)

        # ── Blackboard window ─────────────────────────────────────────────────
        with dpg.window(label="Blackboard", tag=BB_WIN_TAG,
                        width=760, height=400, show=False, no_collapse=True):
            with dpg.table(tag=BB_TABLE_TAG, header_row=True,
                           borders_innerV=True, borders_outerH=True,
                           borders_outerV=True, row_background=True,
                           scrollY=True, height=260):
                dpg.add_table_column(label="Key",         width_fixed=True,
                                     init_width_or_weight=160)
                dpg.add_table_column(label="Type",        width_fixed=True,
                                     init_width_or_weight=62)
                dpg.add_table_column(label="Value",       width_fixed=True,
                                     init_width_or_weight=130)
                dpg.add_table_column(label="Description", width_stretch=True)
                dpg.add_table_column(label="Actions",     width_fixed=True,
                                     init_width_or_weight=92)
            dpg.add_separator()
            dpg.add_text("Add / Edit entry:", color=(160, 160, 160, 255))
            with dpg.group(horizontal=True):
                dpg.add_input_text(label="##bb_key",  tag=BB_KEY_TAG,
                                   width=150, hint="param_name")
                dpg.add_combo(label="##bb_type", tag=BB_TYPE_TAG,
                              items=list(BB_TYPES), default_value="float", width=80)
                dpg.add_input_text(label="##bb_val",  tag=BB_VAL_TAG,
                                   width=120, hint="value  (x,y,z for vectors)")
                dpg.add_input_text(label="##bb_desc", tag=BB_DESC_TAG,
                                   width=175, hint="description")
                dpg.add_button(label="Apply", callback=bb_apply_entry, width=70)

        # ── Context menu (popup + rename dialog) ────────────────────────────────
        build_context_menu()

        # ── Debug overlay ─────────────────────────────────────────────────────
        build_debug_overlay()

        # ── Global event handlers ─────────────────────────────────────────────
        with dpg.handler_registry():
            dpg.add_mouse_release_handler(callback=mouse_release_callback)
            dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Right,
                                        callback=node_right_click_callback)
            dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Left,
                                        callback=close_ctx_if_outside)
            dpg.add_key_press_handler(dpg.mvKey_Escape, callback=close_ctx_on_escape)
            dpg.add_key_press_handler(dpg.mvKey_C, callback=copy_callback)
            dpg.add_key_press_handler(dpg.mvKey_V, callback=paste_callback)
            dpg.add_key_press_handler(dpg.mvKey_X, callback=delete_selected_callback)
            dpg.add_key_press_handler(dpg.mvKey_F3, callback=toggle_debug_overlay)

        # ── Viewport ──────────────────────────────────────────────────────────
        dpg.create_viewport(title="Behaviour Tree Editor  —  Dear PyGui",
                            width=1320, height=860)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

        # Create the initial BT Root node.
        ensure_root_node()

        # ── Render loop ───────────────────────────────────────────────────────
        while dpg.is_dearpygui_running():
            update_sibling_dim()
            update_debug_overlay()
            dpg.render_dearpygui_frame()

        dpg.destroy_context()
