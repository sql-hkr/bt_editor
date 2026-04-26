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
Right-click context menu for nodes in the BT editor.

Menu items
----------
- Copy            : copy this node to clipboard (paste with Cmd/Ctrl+V)
- Duplicate       : clone the node in-place (+40 px offset)
- Rename…         : edit the node label via a modal dialog
- Toggle Collapse : expand / collapse the node body
- Delete          : remove the node (BT Root is protected)

Implementation notes
--------------------
We use a plain DPG window (NOT popup=True) so that macOS right-click events
do not inadvertently close the menu on the same frame they open it.  The
window is shown/hidden manually and closed on:
  • left-click outside the window   (close_ctx_if_outside)
  • Escape key                       (close_ctx_on_escape)
  • any menu-item action             (_hide_ctx inside each callback)

Hit detection uses each node's screen-space bounding box rather than
DPG's get_hovered_item(), which is unreliable inside a node_editor.
"""
from __future__ import annotations
import dearpygui.dearpygui as dpg

from bt_editor.core.state import state

# ── Widget tags ───────────────────────────────────────────────────────────────
_CTX_WIN      = "ctx_node_menu_win"
_RENAME_DLG   = "ctx_rename_dlg_win"
_RENAME_INPUT = "ctx_rename_input_wgt"

# Mutable cells so inner callbacks share state without module-level globals.
_target_nid: list[int | None] = [None]
_ctx_open:   list[bool]       = [False]   # track visibility ourselves


# ── Internal helpers ──────────────────────────────────────────────────────────

def _find_hovered_node() -> int | None:
    """
    Find which node (if any) the mouse cursor is over.

    Uses each node's screen-space bounding rectangle instead of
    get_hovered_item(), which can return child widgets or nothing at all
    when hovering a DPG node_editor node.
    """
    mx, my = dpg.get_mouse_pos(local=False)
    for nid in state.nodes:
        if not dpg.does_item_exist(nid):
            continue
        try:
            rmin = dpg.get_item_rect_min(nid)
            rmax = dpg.get_item_rect_max(nid)
            if rmin[0] <= mx <= rmax[0] and rmin[1] <= my <= rmax[1]:
                return nid
        except Exception:
            continue
    return None


def _hide_ctx() -> None:
    _ctx_open[0] = False
    if dpg.does_item_exist(_CTX_WIN):
        dpg.configure_item(_CTX_WIN, show=False)


# ── Action callbacks (all hide the popup first) ───────────────────────────────

def _copy_target() -> None:
    _hide_ctx()
    nid = _target_nid[0]
    if nid is None or nid not in state.nodes:
        return
    info   = state.nodes[nid]
    op_tag = info.get("op_tag")
    state.clipboard.clear()
    state.clipboard.append({
        "type":  info["type"],
        "label": info["label"],
        "dx":    30.0,
        "dy":    30.0,
        "params": {
            k: (dpg.get_value(v) if dpg.does_item_exist(v) else 0.0)
            for k, v in info.get("params", {}).items()
        },
        "op": (dpg.get_value(op_tag)
               if op_tag and dpg.does_item_exist(op_tag) else None),
    })


def _show_rename() -> None:
    _hide_ctx()
    nid = _target_nid[0]
    if nid is None or nid not in state.nodes:
        return
    dpg.set_value(_RENAME_INPUT, state.nodes[nid]["label"])
    mx, my = dpg.get_mouse_pos(local=False)
    dpg.configure_item(_RENAME_DLG, pos=[int(mx), int(my)], show=True)
    dpg.focus_item(_RENAME_INPUT)


def _rename_ok() -> None:
    new_label = dpg.get_value(_RENAME_INPUT).strip()
    dpg.configure_item(_RENAME_DLG, show=False)
    nid = _target_nid[0]
    if not new_label or nid is None or nid not in state.nodes:
        return
    info          = state.nodes[nid]
    info["label"] = new_label
    prefix        = "▶ " if info.get("collapsed", False) else ""
    if dpg.does_item_exist(nid):
        dpg.configure_item(nid, label=f"{prefix}{new_label}")


def _duplicate_target() -> None:
    _hide_ctx()
    nid = _target_nid[0]
    if nid is None or nid not in state.nodes:
        return
    from bt_editor.editor.factory import add_node  # lazy to avoid circular import
    info    = state.nodes[nid]
    op_tag  = info.get("op_tag")
    new_nid = add_node(info["type"], info["label"] + " (copy)")
    try:
        pos = dpg.get_item_pos(nid)
        dpg.set_item_pos(new_nid, [pos[0] + 40, pos[1] + 40])
    except Exception:
        pass
    for pname, ptag in info.get("params", {}).items():
        new_ptag = state.nodes[new_nid].get("params", {}).get(pname)
        if (ptag and new_ptag
                and dpg.does_item_exist(ptag)
                and dpg.does_item_exist(new_ptag)):
            dpg.set_value(new_ptag, dpg.get_value(ptag))
    if op_tag and dpg.does_item_exist(op_tag):
        new_op_tag = state.nodes[new_nid].get("op_tag")
        if new_op_tag and dpg.does_item_exist(new_op_tag):
            dpg.set_value(new_op_tag, dpg.get_value(op_tag))


def _toggle_collapse_target() -> None:
    _hide_ctx()
    nid = _target_nid[0]
    if nid is None:
        return
    from bt_editor.editor.callbacks import toggle_collapse
    toggle_collapse(nid)


def _delete_target() -> None:
    _hide_ctx()
    nid = _target_nid[0]
    if nid is None or nid not in state.nodes:
        return
    if nid == state.root_nid:
        return   # BT Root is protected
    from bt_editor.editor.callbacks import _delete_node, refresh_execution_order
    _delete_node(nid)
    refresh_execution_order()


# ── Public API ────────────────────────────────────────────────────────────────

def build_context_menu() -> None:
    """
    Create the context menu window and rename dialog.
    Must be called inside a live DPG context, at top-level (not inside a window).
    """
    # ── Context menu — plain window (no popup=True to avoid macOS timing issues)
    with dpg.window(tag=_CTX_WIN, show=False,
                    no_title_bar=True, no_move=True, no_resize=True,
                    no_scrollbar=True, no_collapse=True,
                    no_bring_to_front_on_focus=False,
                    min_size=[150, 10], autosize=True):
        dpg.add_menu_item(label="Copy",            callback=_copy_target)
        dpg.add_menu_item(label="Duplicate",       callback=_duplicate_target)
        dpg.add_separator()
        dpg.add_menu_item(label="Rename…",         callback=_show_rename)
        dpg.add_menu_item(label="Toggle Collapse", callback=_toggle_collapse_target)
        dpg.add_separator()
        dpg.add_menu_item(label="Delete",          callback=_delete_target,
                          shortcut="X")

    # ── Rename modal dialog ─────────────────────────────────────────────────
    with dpg.window(tag=_RENAME_DLG, label="Rename Node",
                    show=False, modal=True, no_resize=True,
                    width=340, height=92, no_collapse=True):
        dpg.add_input_text(tag=_RENAME_INPUT, label="##rename_input",
                           width=-1, hint="New label",
                           on_enter=True, callback=_rename_ok)
        dpg.add_spacer(height=4)
        with dpg.group(horizontal=True):
            dpg.add_button(label="OK",     callback=_rename_ok, width=90)
            dpg.add_button(
                label="Cancel", width=90,
                callback=lambda: dpg.configure_item(_RENAME_DLG, show=False))


def node_right_click_callback(sender, app_data) -> None:
    """Show the context menu when right-clicking on a node."""
    nid = _find_hovered_node()
    if nid is None:
        # Right-click on empty canvas: close any open menu and do nothing.
        _hide_ctx()
        return
    _target_nid[0] = nid
    mx, my = dpg.get_mouse_pos(local=False)
    dpg.set_item_pos(_CTX_WIN, [int(mx), int(my)])
    dpg.configure_item(_CTX_WIN, show=True)
    dpg.focus_item(_CTX_WIN)
    _ctx_open[0] = True


def close_ctx_if_outside(sender, app_data) -> None:
    """Left-click handler: close the context menu if clicking outside it."""
    if not _ctx_open[0]:
        return
    if dpg.does_item_exist(_CTX_WIN) and dpg.is_item_hovered(_CTX_WIN):
        return   # click was inside the menu — let the item handle it
    _hide_ctx()


def close_ctx_on_escape(sender, app_data) -> None:
    """Escape key handler: close the context menu."""
    _hide_ctx()
