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
NodeFactory: creates DPG node widgets from NodeDef registry entries
and registers the node in the shared GraphState.

Public API
----------
    from bt_editor.editor.factory import add_node
    nid = add_node("Sequence")
    nid = add_node("P2P", label="Go Home")
"""
from __future__ import annotations
import dearpygui.dearpygui as dpg

from bt_editor.constants import EDITOR_TAG, DISP_W, DISP_H
from bt_editor.core.state import state
from bt_editor.core.registry import registry


def add_node(ntype: str, label: str = "") -> int:
    """Create a node widget in the editor and register it in *state*.

    Returns the nid (DPG item ID of the node widget).
    Raises ``ValueError`` for unknown *ntype*.
    """
    defn = registry.get(ntype)
    if defn is None:
        raise ValueError(f"Unknown node type: {ntype!r}")

    label     = label.strip() if label else ntype
    nid       = dpg.generate_uuid()
    body_attr = dpg.generate_uuid()
    in_attr   = dpg.generate_uuid() if defn.HAS_BT_IN  else None
    out_attr  = dpg.generate_uuid() if defn.HAS_BT_OUT else None

    info: dict = {
        "type":      ntype,
        "label":     label,
        "in_attr":   in_attr,
        "body_attr": body_attr,
        "out_attr":  out_attr,
        "collapsed": False,
    }
    state.nodes[nid] = info
    if in_attr is not None:
        state.attr_to_node[in_attr]  = nid
    if out_attr is not None:
        state.attr_to_node[out_attr] = nid

    # Pre-create image texture BEFORE opening any DPG node context so that
    # parent=state.tex_registry is unambiguous (mvStage approach).
    if defn.NEEDS_PREVIEW:
        from bt_editor.editor.image_pipeline import blank_texture_data
        pre_tex = dpg.add_raw_texture(
            DISP_W, DISP_H, blank_texture_data(),
            parent=state.tex_registry,
            format=dpg.mvFormat_Float_rgba)
        state.node_textures[nid] = pre_tex

    from bt_editor.editor.themes import node_theme

    with dpg.node(label=label, parent=EDITOR_TAG, tag=nid):
        dpg.bind_item_theme(nid, node_theme(ntype))

        # ── BT parent input (left socket) ─────────────────────────────────
        if defn.HAS_BT_IN:
            order_tag = dpg.generate_uuid()
            info["order_tag"] = order_tag
            with dpg.node_attribute(tag=in_attr,
                                    attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text("parent", indent=2, tag=order_tag)

        # ── Extra inputs (image-in, vector-in, …) ─────────────────────────
        defn.build_extra_inputs(nid, info, state)

        # ── Static body ───────────────────────────────────────────────────
        with dpg.node_attribute(tag=body_attr,
                                attribute_type=dpg.mvNode_Attr_Static):
            defn.build_body(nid, info, state)

        # ── Extra sockets (preview, data-out, A/B, P2P vec, …) ───────────
        defn.build_extra_sockets(nid, info, state)

        # ── BT children output (right socket) ─────────────────────────────
        if defn.HAS_BT_OUT:
            with dpg.node_attribute(tag=out_attr,
                                    attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text(defn.BT_OUT_LABEL, indent=2)

    return nid
