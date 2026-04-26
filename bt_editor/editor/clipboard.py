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
Copy / Paste (Cmd+C / Cmd+V  or  Ctrl+C / Ctrl+V).

Clipboard entries store type, label, relative position offset, params, and op.
Pasting places nodes at the current canvas mouse position + a small offset.
"""
from __future__ import annotations
import dearpygui.dearpygui as dpg

from bt_editor.constants import EDITOR_TAG
from bt_editor.core.state import state
from bt_editor.editor.factory import add_node


def _ctrl_or_cmd() -> bool:
    """Return True when Ctrl or macOS Command (Super) is held."""
    keys = [dpg.mvKey_LControl, dpg.mvKey_RControl]
    for attr in ("mvKey_LSuper", "mvKey_RSuper"):
        k = getattr(dpg, attr, None)
        if k is not None:
            keys.append(k)
    return any(dpg.is_key_down(k) for k in keys)


def _canvas_mouse_pos() -> tuple[float, float]:
    """Return mouse position in node-editor canvas space.

    Uses a reference node's canvas vs. screen position to account for
    internal canvas panning by the DPG node editor.
    """
    mx, my = dpg.get_mouse_pos(local=False)
    for nid in state.nodes:
        if dpg.does_item_exist(nid):
            try:
                cp = dpg.get_item_pos(nid)        # canvas space
                sp = dpg.get_item_rect_min(nid)   # screen / viewport space
                return mx - (sp[0] - cp[0]), my - (sp[1] - cp[1])
            except Exception:
                break
    # Fallback: subtract the editor window's top-left corner.
    from bt_editor.constants import EDITOR_WIN
    try:
        rm = dpg.get_item_state(EDITOR_WIN)["rect_min"]
        return mx - float(rm[0]), my - float(rm[1])
    except Exception:
        return mx, my


def copy_callback() -> None:
    if not _ctrl_or_cmd():
        return
    selected = dpg.get_selected_nodes(EDITOR_TAG)
    if not selected:
        return
    state.clipboard.clear()
    positions: list[list[float]] = []
    valid_ids: list[int] = []
    for nid in selected:
        if nid not in state.nodes:
            continue
        try:
            pos = list(dpg.get_item_pos(nid))
        except Exception:
            pos = [0.0, 0.0]
        positions.append(pos)
        valid_ids.append(nid)
    if not valid_ids:
        return
    cx = sum(p[0] for p in positions) / len(positions)
    cy = sum(p[1] for p in positions) / len(positions)
    for nid, pos in zip(valid_ids, positions):
        info = state.nodes[nid]
        op_tag = info.get("op_tag")
        state.clipboard.append({
            "type":  info["type"],
            "label": info["label"],
            "dx":    pos[0] - cx,
            "dy":    pos[1] - cy,
            "params": {
                k: (dpg.get_value(v) if dpg.does_item_exist(v) else 0.0)
                for k, v in info.get("params", {}).items()
            },
            "op": dpg.get_value(op_tag) if op_tag and dpg.does_item_exist(op_tag) else None,
        })


def paste_callback() -> None:
    if not _ctrl_or_cmd():
        return
    if not state.clipboard:
        return
    mx, my = _canvas_mouse_pos()
    _DX, _DY = 20, 20
    for item in state.clipboard:
        nid = add_node(ntype=item["type"], label=item["label"])
        try:
            dpg.set_item_pos(nid, [mx + _DX + item["dx"], my + _DY + item["dy"]])
        except Exception:
            pass
        for pname, pval in item.get("params", {}).items():
            ptag = state.nodes[nid].get("params", {}).get(pname)
            if ptag and dpg.does_item_exist(ptag):
                dpg.set_value(ptag, pval)
        if item.get("op") is not None:
            op_tag = state.nodes[nid].get("op_tag")
            if op_tag and dpg.does_item_exist(op_tag):
                dpg.set_value(op_tag, item["op"])
