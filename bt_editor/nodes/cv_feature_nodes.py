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
OpenCV feature-extraction node definitions.

Each node receives a BGR image on its ``image in`` socket, runs a
feature-extraction algorithm, and outputs:
  • a BGR image with the extracted features rendered as an overlay, and
  • one or more numeric data sockets carrying the measured values.

Available nodes
---------------
BlobDetector      — detects blobs; outputs centroid (x, y), area, count
ContourAnalysis   — largest contour; outputs centroid (x, y), area, perimeter
ColorMask         — HSV colour range filter; outputs binary mask image + pixel count
HarrisCorner      — Harris / GFTT corner detection; outputs corner-count
TemplateMatch     — normalized template matching; outputs best-match score & location
LineDetector      — HoughLinesP; outputs dominant-line angle & line count
"""
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
import dearpygui.dearpygui as dpg

from bt_editor.core.node_def import NodeDef
from bt_editor.constants import DISP_W, DISP_H

if TYPE_CHECKING:
    from bt_editor.core.state import GraphState


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _img_in_socket(nid: int, info: dict, state: "GraphState") -> int:
    ia = dpg.generate_uuid()
    info["img_in_attr"] = ia
    state.attr_to_node[ia] = nid
    with dpg.node_attribute(tag=ia, attribute_type=dpg.mvNode_Attr_Input):
        dpg.add_text("image in", indent=2)
    return ia


def _img_out_socket(nid: int, info: dict, state: "GraphState") -> int:
    oa = dpg.generate_uuid()
    info["img_out_attr"] = oa
    state.attr_to_node[oa] = nid
    with dpg.node_attribute(tag=oa, attribute_type=dpg.mvNode_Attr_Output):
        dpg.add_text("image out", indent=2)
    return oa


def _data_out(nid: int, info: dict, state: "GraphState",
              key: str, label: str) -> int:
    oa = dpg.generate_uuid()
    info[key] = oa
    state.attr_to_node[oa] = nid
    with dpg.node_attribute(tag=oa, attribute_type=dpg.mvNode_Attr_Output):
        dpg.add_text(label, indent=2)
    return oa


def _preview_attr(nid: int, info: dict, state: "GraphState") -> None:
    """Insert a static image-preview attribute using the pre-created texture."""
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


def _result_text(info: dict, key: str, label: str) -> None:
    """Add a small read-only text widget for displaying a numeric result."""
    tag = dpg.generate_uuid()
    info[key] = tag
    dpg.add_text(f"{label}: —", tag=tag, color=(180, 220, 255, 255))


# ─────────────────────────────────────────────────────────────────────────────
# BlobDetector
# ─────────────────────────────────────────────────────────────────────────────

class BlobDetectorNodeDef(NodeDef):
    """SimpleBlobDetector — detect blobs and output their centroid, area, count.

    The result image shows the detected blobs drawn as coloured circles.

    Output sockets
    --------------
    centroid   — (x, y) pixel position of the largest blob
    area       — area of the largest blob (px²)
    count      — total number of blobs detected
    """

    TYPE     = "BlobDetector"
    CATEGORY = "Vision"
    COLOR    = (60, 130, 180)
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    NEEDS_PREVIEW = True
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = [
        "img_in_attr", "img_out_attr",
        "centroid_out_attr", "area_out_attr", "count_out_attr",
    ]

    # ── Thresh knobs
    _MIN_THRESH = 10
    _MAX_THRESH = 200
    _MIN_AREA   = 100

    def build_extra_inputs(self, nid: int, info: dict,
                            state: "GraphState") -> None:
        _img_in_socket(nid, info, state)

    def build_body(self, nid: int, info: dict,
                   state: "GraphState") -> None:
        from bt_editor.editor.node_callbacks import vision_param_changed
        min_t = dpg.generate_uuid()
        max_t = dpg.generate_uuid()
        min_a = dpg.generate_uuid()
        dpg.add_text("Min threshold")
        dpg.add_slider_int(label="##blob_min_t", tag=min_t, width=160,
                           default_value=self._MIN_THRESH,
                           min_value=0, max_value=255,
                           callback=vision_param_changed, user_data=nid)
        dpg.add_text("Max threshold")
        dpg.add_slider_int(label="##blob_max_t", tag=max_t, width=160,
                           default_value=self._MAX_THRESH,
                           min_value=1, max_value=255,
                           callback=vision_param_changed, user_data=nid)
        dpg.add_text("Min area (px²)")
        dpg.add_drag_float(label="##blob_min_a", tag=min_a, width=160,
                           default_value=self._MIN_AREA,
                           speed=10, min_value=1, max_value=50000,
                           callback=vision_param_changed, user_data=nid)
        info["params"] = {"min_thresh": min_t, "max_thresh": max_t,
                          "min_area": min_a}
        dpg.add_spacer(width=170, height=4)
        _result_text(info, "txt_centroid", "centroid")
        _result_text(info, "txt_area",     "area")
        _result_text(info, "txt_count",    "count")

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _preview_attr(nid, info, state)
        _img_out_socket(nid, info, state)
        _data_out(nid, info, state, "centroid_out_attr", "centroid (vec)")
        _data_out(nid, info, state, "area_out_attr",     "area (scalar)")
        _data_out(nid, info, state, "count_out_attr",    "count (scalar)")

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        p = info.get("params", {})
        return {"params": {k: (int if "thresh" in k else float)(
            dpg.get_value(v)) for k, v in p.items()
            if dpg.does_item_exist(v)}}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, v)

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}


# ─────────────────────────────────────────────────────────────────────────────
# ContourAnalysis
# ─────────────────────────────────────────────────────────────────────────────

class ContourAnalysisNodeDef(NodeDef):
    """Find contours in a thresholded image; analyse the largest one.

    Output sockets
    --------------
    centroid  — (cx, cy) pixel centre of mass of the largest contour
    area      — contour area (px²)
    perimeter — arc length of the contour (px)
    """

    TYPE     = "ContourAnalysis"
    CATEGORY = "Vision"
    COLOR    = (60, 180, 110)
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    NEEDS_PREVIEW = True
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = [
        "img_in_attr", "img_out_attr",
        "centroid_out_attr", "area_out_attr", "perimeter_out_attr",
    ]

    def build_extra_inputs(self, nid: int, info: dict,
                            state: "GraphState") -> None:
        _img_in_socket(nid, info, state)

    def build_body(self, nid: int, info: dict,
                   state: "GraphState") -> None:
        from bt_editor.editor.node_callbacks import vision_param_changed
        thresh_t = dpg.generate_uuid()
        dpg.add_text("Threshold")
        dpg.add_slider_int(label="##ca_thresh", tag=thresh_t, width=160,
                           default_value=127, min_value=0, max_value=254,
                           callback=vision_param_changed, user_data=nid)
        info["params"] = {"threshold": thresh_t}
        dpg.add_spacer(width=170, height=4)
        _result_text(info, "txt_centroid",  "centroid")
        _result_text(info, "txt_area",      "area")
        _result_text(info, "txt_perimeter", "perimeter")

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _preview_attr(nid, info, state)
        _img_out_socket(nid, info, state)
        _data_out(nid, info, state, "centroid_out_attr",  "centroid (vec)")
        _data_out(nid, info, state, "area_out_attr",      "area (scalar)")
        _data_out(nid, info, state, "perimeter_out_attr", "perimeter (scalar)")

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        p = info.get("params", {})
        return {"params": {k: int(dpg.get_value(v)) for k, v in p.items()
                           if dpg.does_item_exist(v)}}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, int(v))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}


# ─────────────────────────────────────────────────────────────────────────────
# ColorMask
# ─────────────────────────────────────────────────────────────────────────────

class ColorMaskNodeDef(NodeDef):
    """HSV colour-range mask.

    Converts input to HSV, applies cv2.inRange, and outputs the binary mask as
    a 3-channel image plus the pixel count of the masked region.

    Output sockets
    --------------
    mask image   — binary mask rendered as BGR (white on black)
    pixel count  — number of non-zero pixels in the mask
    centroid     — (cx, cy) centroid of the masked region (0,0 if empty)
    """

    TYPE     = "ColorMask"
    CATEGORY = "Vision"
    COLOR    = (180, 130, 40)
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    NEEDS_PREVIEW = True
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = [
        "img_in_attr", "img_out_attr",
        "count_out_attr", "centroid_out_attr",
    ]

    def build_extra_inputs(self, nid: int, info: dict,
                            state: "GraphState") -> None:
        _img_in_socket(nid, info, state)

    def build_body(self, nid: int, info: dict,
                   state: "GraphState") -> None:
        h_lo = dpg.generate_uuid()
        h_hi = dpg.generate_uuid()
        s_lo = dpg.generate_uuid()
        s_hi = dpg.generate_uuid()
        v_lo = dpg.generate_uuid()
        v_hi = dpg.generate_uuid()

        from bt_editor.editor.node_callbacks import vision_param_changed
        for label, tag, lo, hi in (
            ("H low/high", h_lo, 0,   10),
            ("",           h_hi, 170, 180),
            ("S low/high", s_lo, 100, 100),
            ("",           s_hi, 255, 255),
            ("V low/high", v_lo, 100, 100),
            ("",           v_hi, 255, 255),
        ):
            if label:
                dpg.add_text(label)
            dpg.add_slider_int(label=f"##cm_{tag}", tag=tag, width=160,
                               default_value=lo, min_value=0, max_value=255,
                               callback=vision_param_changed, user_data=nid)
        info["params"] = {
            "h_lo": h_lo, "h_hi": h_hi,
            "s_lo": s_lo, "s_hi": s_hi,
            "v_lo": v_lo, "v_hi": v_hi,
        }
        dpg.add_spacer(width=170, height=4)
        _result_text(info, "txt_count",    "count")
        _result_text(info, "txt_centroid", "centroid")

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _preview_attr(nid, info, state)
        _img_out_socket(nid, info, state)
        _data_out(nid, info, state, "count_out_attr",    "count (scalar)")
        _data_out(nid, info, state, "centroid_out_attr", "centroid (vec)")

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        p = info.get("params", {})
        return {"params": {k: int(dpg.get_value(v)) for k, v in p.items()
                           if dpg.does_item_exist(v)}}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, int(v))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}


# ─────────────────────────────────────────────────────────────────────────────
# HarrisCorner / Shi-Tomasi (GFTT) corner detector
# ─────────────────────────────────────────────────────────────────────────────

class CornerDetectorNodeDef(NodeDef):
    """Corner detector (Shi-Tomasi / Good Features to Track).

    Uses cv2.goodFeaturesToTrack internally.  Detected corners are drawn as
    circles on the result image.

    Output sockets
    --------------
    corner count   — number of corners detected
    corners (vec)  — [cx0, cy0, cx1, cy1, …] flattened pixel coordinates
                     of up to ``max_corners`` corners
    """

    TYPE     = "CornerDetector"
    CATEGORY = "Vision"
    COLOR    = (160, 60, 160)
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    NEEDS_PREVIEW = True
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = [
        "img_in_attr", "img_out_attr",
        "count_out_attr", "corners_out_attr",
    ]

    def build_extra_inputs(self, nid: int, info: dict,
                            state: "GraphState") -> None:
        _img_in_socket(nid, info, state)

    def build_body(self, nid: int, info: dict,
                   state: "GraphState") -> None:
        max_c = dpg.generate_uuid()
        qual  = dpg.generate_uuid()
        dist  = dpg.generate_uuid()
        from bt_editor.editor.node_callbacks import vision_param_changed
        dpg.add_text("Max corners")
        dpg.add_slider_int(label="##cd_max", tag=max_c, width=160,
                           default_value=50, min_value=1, max_value=500,
                           callback=vision_param_changed, user_data=nid)
        dpg.add_text("Quality level")
        dpg.add_slider_float(label="##cd_qual", tag=qual, width=160,
                             default_value=0.01, min_value=0.001, max_value=1.0,
                             format="%.3f",
                             callback=vision_param_changed, user_data=nid)
        dpg.add_text("Min distance (px)")
        dpg.add_drag_float(label="##cd_dist", tag=dist, width=160,
                           default_value=10.0, speed=1.0,
                           min_value=1.0, max_value=200.0,
                           callback=vision_param_changed, user_data=nid)
        info["params"] = {"max_corners": max_c, "quality": qual,
                          "min_dist": dist}
        dpg.add_spacer(width=170, height=4)
        _result_text(info, "txt_count", "corners")

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _preview_attr(nid, info, state)
        _img_out_socket(nid, info, state)
        _data_out(nid, info, state, "count_out_attr",   "count (scalar)")
        _data_out(nid, info, state, "corners_out_attr", "corners (vec)")

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        p = info.get("params", {})
        out: dict = {}
        for k, v in p.items():
            if dpg.does_item_exist(v):
                val = dpg.get_value(v)
                out[k] = int(val) if k == "max_corners" else float(val)
        return {"params": out}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, v)

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}


# ─────────────────────────────────────────────────────────────────────────────
# TemplateMatch
# ─────────────────────────────────────────────────────────────────────────────

class TemplateMatchNodeDef(NodeDef):
    """Normalised cross-correlation template matching (cv2.TM_CCOEFF_NORMED).

    The template image is loaded from disk on the node itself.  The result
    image shows the best-match bounding box drawn on the input image.

    Output sockets
    --------------
    score      — best normalised match score in [−1, 1]
    location   — (cx, cy) centre of the best-match region in pixels
    """

    TYPE     = "TemplateMatch"
    CATEGORY = "Vision"
    COLOR    = (130, 160, 60)
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    NEEDS_PREVIEW = True
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = [
        "img_in_attr", "img_out_attr",
        "score_out_attr", "loc_out_attr",
    ]

    def build_extra_inputs(self, nid: int, info: dict,
                            state: "GraphState") -> None:
        _img_in_socket(nid, info, state)

    def build_body(self, nid: int, info: dict,
                   state: "GraphState") -> None:
        from bt_editor.editor.node_callbacks import (
            tmpl_browse_callback, vision_param_changed)

        path_tag   = dpg.generate_uuid()
        dialog_tag = dpg.generate_uuid()
        info["tmpl_path_tag"]   = path_tag
        info["tmpl_dialog_tag"] = dialog_tag

        dpg.add_input_text(label="##tmpl_path", tag=path_tag, width=DISP_W,
                           hint="no template", readonly=True)
        dpg.add_button(label="Browse template…",
                       callback=lambda s, a, u: dpg.show_item(u),
                       user_data=dialog_tag, width=DISP_W)
        dpg.add_file_dialog(
            label="Open Template", tag=dialog_tag,
            callback=tmpl_browse_callback, user_data=nid,
            width=700, height=400, show=False)
        dpg.add_file_extension(".jpg",  parent=dialog_tag,
                               color=(255, 200, 100, 255))
        dpg.add_file_extension(".png",  parent=dialog_tag,
                               color=(100, 200, 255, 255))
        dpg.add_file_extension(".*",    parent=dialog_tag)

        thresh_t = dpg.generate_uuid()
        dpg.add_text("Match threshold")
        dpg.add_slider_float(label="##tm_thresh", tag=thresh_t, width=160,
                             default_value=0.7, min_value=0.0, max_value=1.0,
                             format="%.2f",
                             callback=vision_param_changed, user_data=nid)
        info["params"] = {"threshold": thresh_t}
        dpg.add_spacer(width=170, height=4)
        _result_text(info, "txt_score", "score")
        _result_text(info, "txt_loc",   "location")

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _preview_attr(nid, info, state)
        _img_out_socket(nid, info, state)
        _data_out(nid, info, state, "score_out_attr", "score (scalar)")
        _data_out(nid, info, state, "loc_out_attr",   "location (vec)")

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        p = info.get("params", {})
        data: dict = {}
        thresh_tag = p.get("threshold")
        if thresh_tag and dpg.does_item_exist(thresh_tag):
            data["params"] = {"threshold": float(dpg.get_value(thresh_tag))}
        if info.get("tmpl_path"):
            data["tmpl_path"] = info["tmpl_path"]
        return data

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        import os, numpy as np, cv2
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, float(v))
        tmpl_path = data.get("tmpl_path")
        if tmpl_path and os.path.exists(tmpl_path):
            buf = np.fromfile(tmpl_path, dtype=np.uint8)
            tmpl = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if tmpl is not None:
                info["tmpl_image"] = tmpl
                info["tmpl_path"]  = tmpl_path
                path_tag = info.get("tmpl_path_tag")
                if path_tag and dpg.does_item_exist(path_tag):
                    dpg.set_value(path_tag, os.path.basename(tmpl_path))

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}


# ─────────────────────────────────────────────────────────────────────────────
# LineDetector
# ─────────────────────────────────────────────────────────────────────────────

class LineDetectorNodeDef(NodeDef):
    """Probabilistic Hough Line Transform (cv2.HoughLinesP).

    Detects line segments in an edge image (runs Canny internally if the
    input is colour).  Detected lines are drawn on the result image.

    Output sockets
    --------------
    line count   — number of line segments detected
    angle (deg)  — average angle of detected lines in degrees [−90, 90]
    """

    TYPE     = "LineDetector"
    CATEGORY = "Vision"
    COLOR    = (80, 140, 170)
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    NEEDS_PREVIEW = True
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = [
        "img_in_attr", "img_out_attr",
        "count_out_attr", "angle_out_attr",
    ]

    def build_extra_inputs(self, nid: int, info: dict,
                            state: "GraphState") -> None:
        _img_in_socket(nid, info, state)

    def build_body(self, nid: int, info: dict,
                   state: "GraphState") -> None:
        rho_t     = dpg.generate_uuid()  # LineDetector
        thresh_t  = dpg.generate_uuid()
        min_len_t = dpg.generate_uuid()
        max_gap_t = dpg.generate_uuid()
        from bt_editor.editor.node_callbacks import vision_param_changed
        dpg.add_text("Rho (px)")
        dpg.add_drag_float(label="##ld_rho", tag=rho_t, width=160,
                           default_value=1.0, speed=0.5,
                           min_value=0.5, max_value=10.0, format="%.1f",
                           callback=vision_param_changed, user_data=nid)
        dpg.add_text("Threshold (votes)")
        dpg.add_slider_int(label="##ld_thresh", tag=thresh_t, width=160,
                           default_value=50, min_value=1, max_value=200,
                           callback=vision_param_changed, user_data=nid)
        dpg.add_text("Min line length (px)")
        dpg.add_drag_float(label="##ld_minlen", tag=min_len_t, width=160,
                           default_value=30.0, speed=1.0,
                           min_value=1.0, max_value=500.0,
                           callback=vision_param_changed, user_data=nid)
        dpg.add_text("Max line gap (px)")
        dpg.add_drag_float(label="##ld_maxgap", tag=max_gap_t, width=160,
                           default_value=10.0, speed=1.0,
                           min_value=0.0, max_value=200.0,
                           callback=vision_param_changed, user_data=nid)
        info["params"] = {
            "rho": rho_t, "threshold": thresh_t,
            "min_length": min_len_t, "max_gap": max_gap_t,
        }
        dpg.add_spacer(width=170, height=4)
        _result_text(info, "txt_count", "lines")
        _result_text(info, "txt_angle", "avg angle")

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _preview_attr(nid, info, state)
        _img_out_socket(nid, info, state)
        _data_out(nid, info, state, "count_out_attr", "count (scalar)")
        _data_out(nid, info, state, "angle_out_attr", "angle (scalar)")

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        p = info.get("params", {})
        out: dict = {}
        for k, v in p.items():
            if dpg.does_item_exist(v):
                val = dpg.get_value(v)
                out[k] = int(val) if k == "threshold" else float(val)
        return {"params": out}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, v)

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}


# ─────────────────────────────────────────────────────────────────────────────
# Centroid  —  image centre of mass via spatial moments
# ─────────────────────────────────────────────────────────────────────────────

class CentroidNodeDef(NodeDef):
    """Compute image centroid (centre of mass) using spatial moments.

    Converts the input image to greyscale, applies binary thresholding,
    and calculates the centroid of the non-zero pixel region via
    cv2.moments().  The result image shows a crosshair drawn at the
    centroid position.

    Output sockets
    --------------
    centroid   — [cx, cy] pixel position (vec)
    cx         — centroid x coordinate (scalar)
    cy         — centroid y coordinate (scalar)
    """

    TYPE     = "Centroid"
    CATEGORY = "Vision"
    COLOR    = (40, 190, 160)
    HAS_BT_IN  = False
    HAS_BT_OUT = False
    NEEDS_PREVIEW = True
    EXTRA_SOCKET_KEYS: ClassVar[list[str]] = [
        "img_in_attr", "img_out_attr",
        "centroid_out_attr", "cx_out_attr", "cy_out_attr",
    ]

    def build_extra_inputs(self, nid: int, info: dict,
                            state: "GraphState") -> None:
        _img_in_socket(nid, info, state)

    def build_body(self, nid: int, info: dict,
                   state: "GraphState") -> None:
        from bt_editor.editor.node_callbacks import vision_param_changed
        thresh_t = dpg.generate_uuid()
        invert_t = dpg.generate_uuid()
        dpg.add_text("Threshold")
        dpg.add_slider_int(label="##cen_thresh", tag=thresh_t, width=160,
                           default_value=127, min_value=0, max_value=254,
                           callback=vision_param_changed, user_data=nid)
        dpg.add_checkbox(label="Invert mask", tag=invert_t,
                         default_value=False,
                         callback=vision_param_changed, user_data=nid)
        info["params"] = {"threshold": thresh_t, "invert": invert_t}
        dpg.add_spacer(width=170, height=4)
        _result_text(info, "txt_centroid", "centroid")
        _result_text(info, "txt_cx",       "cx")
        _result_text(info, "txt_cy",       "cy")

    def build_extra_sockets(self, nid: int, info: dict,
                             state: "GraphState") -> None:
        _preview_attr(nid, info, state)
        _img_out_socket(nid, info, state)
        _data_out(nid, info, state, "centroid_out_attr", "centroid (vec)")
        _data_out(nid, info, state, "cx_out_attr",       "cx (scalar)")
        _data_out(nid, info, state, "cy_out_attr",       "cy (scalar)")

    def serialize(self, nid: int, info: dict, state: "GraphState") -> dict:
        p = info.get("params", {})
        out: dict = {}
        thresh_tag = p.get("threshold")
        if thresh_tag and dpg.does_item_exist(thresh_tag):
            out["threshold"] = int(dpg.get_value(thresh_tag))
        invert_tag = p.get("invert")
        if invert_tag and dpg.does_item_exist(invert_tag):
            out["invert"] = bool(dpg.get_value(invert_tag))
        return {"params": out} if out else {}

    def deserialize(self, nid: int, info: dict,
                    state: "GraphState", data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = info.get("params", {}).get(k)
            if tag and dpg.does_item_exist(tag):
                dpg.set_value(tag, v)

    def to_json(self, nid: int, info: dict,
                state: "GraphState", children: list[dict]) -> dict:
        return {"type": self.TYPE, "name": info["label"]}
