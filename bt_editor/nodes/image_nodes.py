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
Image I/O and processing node definitions: Image, OpenCV, ResultImage.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
import dearpygui.dearpygui as dpg

from bt_editor.core.node_def import NodeDef
from bt_editor.constants import DISP_W, DISP_H

if TYPE_CHECKING:
    from bt_editor.core.state import GraphState

_OPENCV_OPS: list[str] = [
    "Grayscale", "Gaussian Blur", "Median Blur",
    "Canny Edge", "Threshold Binary", "Adaptive Threshold",
    "Dilate", "Erode", "Flip Horizontal", "Flip Vertical",
    "Rotate 90 CW", "Rotate 90 CCW",
]


class ImageNodeDef(NodeDef):
    """Loads an image from disk; displays a preview; outputs to an image wire."""

    TYPE     = "Image"
    CATEGORY = "Input"
    COLOR    = (80, 60, 120)
    HAS_BT_IN     = False
    HAS_BT_OUT    = False
    NEEDS_PREVIEW = True
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["img_out_attr"]

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        from bt_editor.editor.node_callbacks import file_selected_callback

        path_tag   = dpg.generate_uuid()
        dialog_tag = dpg.generate_uuid()
        info["path_tag"]   = path_tag
        info["dialog_tag"] = dialog_tag

        dpg.add_input_text(label="##path", tag=path_tag, width=DISP_W,
                           hint="no file selected", readonly=True)
        dpg.add_button(label="Browse...",
                       callback=lambda s, a, u: dpg.show_item(u),
                       user_data=dialog_tag, width=DISP_W)
        dpg.add_file_dialog(
            label="Open Image", tag=dialog_tag,
            callback=file_selected_callback, user_data=nid,
            width=700, height=400, show=False)
        dpg.add_file_extension(".jpg",  parent=dialog_tag, color=(255, 200, 100, 255))
        dpg.add_file_extension(".jpeg", parent=dialog_tag, color=(255, 200, 100, 255))
        dpg.add_file_extension(".png",  parent=dialog_tag, color=(100, 200, 255, 255))
        dpg.add_file_extension(".bmp",  parent=dialog_tag)
        dpg.add_file_extension(".*",    parent=dialog_tag)

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        # Image preview
        pre_tex = state.node_textures.get(nid)
        if pre_tex:
            prev_attr = dpg.generate_uuid()
            info["prev_attr"] = prev_attr
            with dpg.node_attribute(tag=prev_attr,
                                    attribute_type=dpg.mvNode_Attr_Static):
                img_widget = dpg.generate_uuid()
                dpg.add_image(pre_tex, tag=img_widget,
                              width=DISP_W, height=DISP_H)
                state.node_image_widgets[nid] = img_widget

        # Image output socket
        img_out = dpg.generate_uuid()
        info["img_out_attr"] = img_out
        state.attr_to_node[img_out] = nid
        with dpg.node_attribute(tag=img_out, attribute_type=dpg.mvNode_Attr_Output):
            dpg.add_text("image", indent=2)

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        data: dict = {}
        if info.get("image_path"):
            data["image_path"] = info["image_path"]
        return data

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        import os
        import cv2
        import numpy as np
        from bt_editor.editor.image_pipeline import update_node_texture, propagate_image

        img_path = data.get("image_path")
        if not img_path or not os.path.exists(img_path):
            return
        buf = np.fromfile(img_path, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            return
        info["image_path"] = img_path
        state.node_images[nid] = img
        update_node_texture(nid, img, state)
        path_tag = info.get("path_tag")
        if path_tag and dpg.does_item_exist(path_tag):
            dpg.set_value(path_tag, os.path.basename(img_path))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}


class OpenCVNodeDef(NodeDef):
    """Applies an OpenCV operation to an incoming image and outputs the result."""

    TYPE     = "OpenCV"
    CATEGORY = "Utilities"
    COLOR    = (40, 130, 80)
    HAS_BT_IN     = False
    HAS_BT_OUT    = False
    NEEDS_PREVIEW = True
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["img_in_attr", "img_out_attr"]

    def build_extra_inputs(self, nid: int, info: dict,
                            state: "GraphState") -> None:
        img_in = dpg.generate_uuid()
        info["img_in_attr"] = img_in
        state.attr_to_node[img_in] = nid
        with dpg.node_attribute(tag=img_in, attribute_type=dpg.mvNode_Attr_Input):
            dpg.add_text("image in", indent=2)

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        from bt_editor.editor.node_callbacks import opencv_op_changed
        op_tag = dpg.generate_uuid()
        dpg.add_combo(label="Op", tag=op_tag, width=160,
                      items=_OPENCV_OPS, default_value="Grayscale",
                      callback=opencv_op_changed, user_data=nid)
        info["op_tag"] = op_tag

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        # Image preview
        pre_tex = state.node_textures.get(nid)
        if pre_tex:
            prev_attr = dpg.generate_uuid()
            info["prev_attr"] = prev_attr
            with dpg.node_attribute(tag=prev_attr,
                                    attribute_type=dpg.mvNode_Attr_Static):
                img_widget = dpg.generate_uuid()
                dpg.add_image(pre_tex, tag=img_widget,
                              width=DISP_W, height=DISP_H)
                state.node_image_widgets[nid] = img_widget

        # Image output socket
        img_out = dpg.generate_uuid()
        info["img_out_attr"] = img_out
        state.attr_to_node[img_out] = nid
        with dpg.node_attribute(tag=img_out, attribute_type=dpg.mvNode_Attr_Output):
            dpg.add_text("image out", indent=2)

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        op_tag = info.get("op_tag")
        op = dpg.get_value(op_tag) if op_tag and dpg.does_item_exist(op_tag) else "Grayscale"
        return {"op": op}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        op_tag = info.get("op_tag")
        if op_tag and dpg.does_item_exist(op_tag) and data.get("op"):
            dpg.set_value(op_tag, data["op"])

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        op_tag = info.get("op_tag")
        op = dpg.get_value(op_tag) if op_tag and dpg.does_item_exist(op_tag) else "Grayscale"
        return {"type": self.TYPE, "name": info["label"], "operation": op}


class ResultImageNodeDef(NodeDef):
    """Displays the final output image from a processing pipeline."""

    TYPE     = "Result Image"
    CATEGORY = "Output"
    COLOR    = (50, 90, 60)
    HAS_BT_IN     = False
    HAS_BT_OUT    = False
    NEEDS_PREVIEW = True
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = ["img_in_attr"]

    def build_extra_inputs(self, nid: int, info: dict,
                            state: "GraphState") -> None:
        img_in = dpg.generate_uuid()
        info["img_in_attr"] = img_in
        state.attr_to_node[img_in] = nid
        with dpg.node_attribute(tag=img_in, attribute_type=dpg.mvNode_Attr_Input):
            dpg.add_text("image in", indent=2)

    def build_body(self, nid: int, info: dict, state: "GraphState") -> None:
        dpg.add_text("(connect image input)", color=(140, 140, 140, 255))

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        pre_tex = state.node_textures.get(nid)
        if pre_tex:
            prev_attr = dpg.generate_uuid()
            info["prev_attr"] = prev_attr
            with dpg.node_attribute(tag=prev_attr,
                                    attribute_type=dpg.mvNode_Attr_Static):
                img_widget = dpg.generate_uuid()
                dpg.add_image(pre_tex, tag=img_widget,
                              width=DISP_W, height=DISP_H)
                state.node_image_widgets[nid] = img_widget

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}
