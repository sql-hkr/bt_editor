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
Image texture helpers and OpenCV evaluation pipeline.

All functions receive ``state`` explicitly so they can be called from
any context without relying on a global import side-effect.
"""
from __future__ import annotations
import numpy as np
import cv2
import dearpygui.dearpygui as dpg

from bt_editor.constants import DISP_W, DISP_H
from bt_editor.core.state import GraphState, state as _state


# ─────────────────────────────────────────────────────────────────────────────
# Texture data helpers
# ─────────────────────────────────────────────────────────────────────────────

def blank_texture_data() -> np.ndarray:
    """Return a flat float32 RGBA array for a dark-gray placeholder texture."""
    arr = np.full((DISP_H * DISP_W * 4,), 0.15, dtype=np.float32)
    arr[3::4] = 1.0   # alpha = 1
    return arr


def img_to_texture_data(img: np.ndarray) -> np.ndarray:
    """Resize *img* (BGR uint8) to fit DISP_W×DISP_H with letterboxing,
    convert to RGBA float32, and return a flat array for DPG textures."""
    h, w = img.shape[:2]
    scale  = min(DISP_W / w, DISP_H / h)
    nw     = max(1, int(w * scale))
    nh     = max(1, int(h * scale))
    resized = cv2.resize(img, (nw, nh))
    if len(resized.shape) == 2:
        resized = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)
    canvas = np.zeros((DISP_H, DISP_W, 3), dtype=np.uint8)
    yo = (DISP_H - nh) // 2
    xo = (DISP_W - nw) // 2
    canvas[yo:yo+nh, xo:xo+nw] = resized
    rgba = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGBA).astype(np.float32) / 255.0
    return rgba.flatten()


def update_node_texture(nid: int, img: np.ndarray,
                         st: GraphState = None) -> None:
    """Push new image data into the DPG raw texture for *nid*."""
    if st is None:
        st = _state
    tex = st.node_textures.get(nid)
    if tex is None or not dpg.does_item_exist(tex):
        return
    dpg.set_value(tex, img_to_texture_data(img))


# ─────────────────────────────────────────────────────────────────────────────
# Link traversal
# ─────────────────────────────────────────────────────────────────────────────

def get_connected_image(in_attr: int | None, st: GraphState = None):
    """Follow the link feeding into *in_attr* and return the source node's
    cached numpy image, or ``None`` if not connected / no image loaded."""
    if st is None:
        st = _state
    if in_attr is None:
        return None
    for _lid, (out_a, in_a) in st.links.items():
        if in_a == in_attr:
            src = st.attr_to_node.get(out_a)
            if src:
                return st.node_images.get(src)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# OpenCV operations
# ─────────────────────────────────────────────────────────────────────────────

def apply_opencv_op(img: np.ndarray, op: str) -> np.ndarray:
    """Apply the named OpenCV operation to *img* (BGR uint8) and return result."""
    if op == "Grayscale":
        return cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    if op == "Gaussian Blur":
        return cv2.GaussianBlur(img, (15, 15), 0)
    if op == "Median Blur":
        return cv2.medianBlur(img, 15)
    if op == "Canny Edge":
        edges = cv2.Canny(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 100, 200)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    if op == "Threshold Binary":
        _, th = cv2.threshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY),
                              127, 255, cv2.THRESH_BINARY)
        return cv2.cvtColor(th, cv2.COLOR_GRAY2BGR)
    if op == "Adaptive Threshold":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
        return cv2.cvtColor(th, cv2.COLOR_GRAY2BGR)
    if op == "Dilate":
        return cv2.dilate(img, np.ones((5, 5), np.uint8), iterations=1)
    if op == "Erode":
        return cv2.erode(img, np.ones((5, 5), np.uint8), iterations=1)
    if op == "Flip Horizontal":
        return cv2.flip(img, 1)
    if op == "Flip Vertical":
        return cv2.flip(img, 0)
    if op == "Rotate 90 CW":
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    if op == "Rotate 90 CCW":
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img.copy()


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────────────────────

def eval_node(nid: int, st: GraphState = None) -> None:
    """Evaluate *nid* if it is an image-processing node and update its texture."""
    if st is None:
        st = _state
    if nid not in st.nodes:
        return
    info  = st.nodes[nid]
    ntype = info["type"]
    blank = blank_texture_data()

    if ntype == "OpenCV":
        img = get_connected_image(info.get("img_in_attr"), st)
        if img is not None:
            op_tag = info.get("op_tag")
            op = dpg.get_value(op_tag) if op_tag and dpg.does_item_exist(op_tag) else "Grayscale"
            result = apply_opencv_op(img, op)
            st.node_images[nid] = result
            update_node_texture(nid, result, st)
        else:
            st.node_images.pop(nid, None)
            tex = st.node_textures.get(nid)
            if tex and dpg.does_item_exist(tex):
                dpg.set_value(tex, blank)

    elif ntype == "Result Image":
        img = get_connected_image(info.get("img_in_attr"), st)
        if img is not None:
            update_node_texture(nid, img, st)
        else:
            tex = st.node_textures.get(nid)
            if tex and dpg.does_item_exist(tex):
                dpg.set_value(tex, blank)

    elif ntype == "BlobDetector":
        _eval_blob_detector(nid, info, st)

    elif ntype == "ContourAnalysis":
        _eval_contour_analysis(nid, info, st)

    elif ntype == "ColorMask":
        _eval_color_mask(nid, info, st)

    elif ntype == "CornerDetector":
        _eval_corner_detector(nid, info, st)

    elif ntype == "TemplateMatch":
        _eval_template_match(nid, info, st)

    elif ntype == "LineDetector":
        _eval_line_detector(nid, info, st)

    elif ntype == "Centroid":
        _eval_centroid(nid, info, st)


def propagate_image(nid: int, st: GraphState = None) -> None:
    """Evaluate all nodes downstream of *nid*'s image output socket."""
    if st is None:
        st = _state
    img_out = st.nodes.get(nid, {}).get("img_out_attr")
    if img_out is None:
        return
    for _lid, (out_a, in_a) in list(st.links.items()):
        if out_a == img_out:
            dst = st.attr_to_node.get(in_a)
            if dst and dst in st.nodes:
                eval_node(dst, st)
                propagate_image(dst, st)


# ─────────────────────────────────────────────────────────────────────────────
# Feature-extraction evaluation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_params(info: dict) -> dict:
    """Return {name: value} for all params whose DPG tags exist."""
    return {k: dpg.get_value(v) for k, v in info.get("params", {}).items()
            if dpg.does_item_exist(v)}


def _set_text_safe(info: dict, key: str, text: str) -> None:
    tag = info.get(key)
    if tag and dpg.does_item_exist(tag):
        dpg.set_value(tag, text)


def _push_or_blank(nid: int, info: dict, st: GraphState,
                   result: np.ndarray | None) -> None:
    """Update texture; clear if result is None."""
    if result is not None:
        st.node_images[nid] = result
        update_node_texture(nid, result, st)
    else:
        st.node_images.pop(nid, None)
        tex = st.node_textures.get(nid)
        if tex and dpg.does_item_exist(tex):
            dpg.set_value(tex, blank_texture_data())


# ── BlobDetector ─────────────────────────────────────────────────────────────

def _eval_blob_detector(nid: int, info: dict, st: GraphState) -> None:
    img = get_connected_image(info.get("img_in_attr"), st)
    if img is None:
        _push_or_blank(nid, info, st, None)
        return

    p = _safe_params(info)
    min_t = int(p.get("min_thresh", 10))
    max_t = int(max(p.get("max_thresh", 200), min_t + 1))
    min_a = float(p.get("min_area", 100))

    params = cv2.SimpleBlobDetector_Params()
    params.minThreshold = min_t
    params.maxThreshold = max_t
    params.filterByArea = True
    params.minArea      = min_a
    params.filterByCircularity = False
    params.filterByConvexity   = False
    params.filterByInertia     = False

    detector = cv2.SimpleBlobDetector_create(params)
    gray     = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    keypoints = detector.detect(gray)

    result = img.copy()
    cv2.drawKeypoints(img, keypoints, result,
                      (0, 0, 255),
                      cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

    count = len(keypoints)
    if count > 0:
        best = max(keypoints, key=lambda k: k.size)
        cx, cy = best.pt
        area   = np.pi * (best.size / 2) ** 2
        _set_text_safe(info, "txt_centroid", f"centroid: ({cx:.1f}, {cy:.1f})")
        _set_text_safe(info, "txt_area",     f"area: {area:.1f} px²")
    else:
        cx = cy = area = 0.0
        _set_text_safe(info, "txt_centroid", "centroid: (-, -)")
        _set_text_safe(info, "txt_area",     "area: -")
    _set_text_safe(info, "txt_count", f"count: {count}")

    st.node_data[nid] = {"centroid": [cx, cy], "area": area, "count": count}
    _push_or_blank(nid, info, st, result)


# ── ContourAnalysis ───────────────────────────────────────────────────────────

def _eval_contour_analysis(nid: int, info: dict, st: GraphState) -> None:
    img = get_connected_image(info.get("img_in_attr"), st)
    if img is None:
        _push_or_blank(nid, info, st, None)
        return

    p = _safe_params(info)
    thresh = int(p.get("threshold", 127))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)

    result = img.copy()
    cx = cy = area = peri = 0.0
    if contours:
        biggest = max(contours, key=cv2.contourArea)
        cv2.drawContours(result, [biggest], -1, (0, 255, 0), 2)
        area = float(cv2.contourArea(biggest))
        peri = float(cv2.arcLength(biggest, True))
        M = cv2.moments(biggest)
        if M["m00"] != 0:
            cx = M["m10"] / M["m00"]
            cy = M["m01"] / M["m00"]
        cv2.circle(result, (int(cx), int(cy)), 5, (0, 0, 255), -1)
        _set_text_safe(info, "txt_centroid",  f"centroid: ({cx:.1f}, {cy:.1f})")
        _set_text_safe(info, "txt_area",      f"area: {area:.1f} px²")
        _set_text_safe(info, "txt_perimeter", f"perimeter: {peri:.1f} px")
    else:
        _set_text_safe(info, "txt_centroid",  "centroid: (-, -)")
        _set_text_safe(info, "txt_area",      "area: -")
        _set_text_safe(info, "txt_perimeter", "perimeter: -")

    st.node_data[nid] = {"centroid": [cx, cy], "area": area, "perimeter": peri}
    _push_or_blank(nid, info, st, result)


# ── ColorMask ─────────────────────────────────────────────────────────────────

def _eval_color_mask(nid: int, info: dict, st: GraphState) -> None:
    img = get_connected_image(info.get("img_in_attr"), st)
    if img is None:
        _push_or_blank(nid, info, st, None)
        return

    p = _safe_params(info)
    lo = np.array([int(p.get("h_lo", 0)),  int(p.get("s_lo", 100)),
                   int(p.get("v_lo", 100))], dtype=np.uint8)
    hi = np.array([int(p.get("h_hi", 180)), int(p.get("s_hi", 255)),
                   int(p.get("v_hi", 255))], dtype=np.uint8)

    hsv  = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lo, hi)
    result = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

    count = int(np.count_nonzero(mask))
    cx = cy = 0.0
    if count > 0:
        M = cv2.moments(mask)
        if M["m00"] != 0:
            cx = M["m10"] / M["m00"]
            cy = M["m01"] / M["m00"]
    _set_text_safe(info, "txt_count",    f"count: {count} px")
    _set_text_safe(info, "txt_centroid", f"centroid: ({cx:.1f}, {cy:.1f})")

    st.node_data[nid] = {"centroid": [cx, cy], "count": count}
    _push_or_blank(nid, info, st, result)


# ── CornerDetector ────────────────────────────────────────────────────────────

def _eval_corner_detector(nid: int, info: dict, st: GraphState) -> None:
    img = get_connected_image(info.get("img_in_attr"), st)
    if img is None:
        _push_or_blank(nid, info, st, None)
        return

    p = _safe_params(info)
    max_corners = max(1, int(p.get("max_corners", 50)))
    quality     = float(p.get("quality",     0.01))
    min_dist    = float(p.get("min_dist",    10.0))

    gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corners = cv2.goodFeaturesToTrack(gray, maxCorners=max_corners,
                                      qualityLevel=quality,
                                      minDistance=min_dist)

    result = img.copy()
    pts: list[float] = []
    if corners is not None:
        for c in corners:
            x, y = c.ravel().astype(int)
            cv2.circle(result, (x, y), 4, (0, 255, 255), -1)
            pts.extend([float(x), float(y)])
    count = len(corners) if corners is not None else 0
    _set_text_safe(info, "txt_count", f"corners: {count}")

    st.node_data[nid] = {"count": count, "corners": pts}
    _push_or_blank(nid, info, st, result)


# ── TemplateMatch ─────────────────────────────────────────────────────────────

def _eval_template_match(nid: int, info: dict, st: GraphState) -> None:
    import math
    img  = get_connected_image(info.get("img_in_attr"), st)
    tmpl = info.get("tmpl_image")
    if img is None or tmpl is None:
        _push_or_blank(nid, info, st, img.copy() if img is not None else None)
        return

    # Resize template if larger than image
    ih, iw = img.shape[:2]
    th, tw = tmpl.shape[:2]
    if th > ih or tw > iw:
        scale = min(ih / th, iw / tw) * 0.9
        tmpl  = cv2.resize(tmpl, (max(1, int(tw * scale)),
                                   max(1, int(th * scale))))
        th, tw = tmpl.shape[:2]

    res = cv2.matchTemplate(img, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    cx = float(max_loc[0] + tw / 2)
    cy = float(max_loc[1] + th / 2)
    result = img.copy()

    p = _safe_params(info)
    threshold = float(p.get("threshold", 0.7))
    if max_val >= threshold:
        cv2.rectangle(result, max_loc,
                      (max_loc[0] + tw, max_loc[1] + th),
                      (0, 255, 0), 2)
        cv2.circle(result, (int(cx), int(cy)), 4, (0, 0, 255), -1)

    score = float(max_val)
    _set_text_safe(info, "txt_score", f"score: {score:.3f}")
    _set_text_safe(info, "txt_loc",   f"location: ({cx:.1f}, {cy:.1f})")

    st.node_data[nid] = {"score": score, "location": [cx, cy]}
    _push_or_blank(nid, info, st, result)


# ── LineDetector ──────────────────────────────────────────────────────────────

def _eval_line_detector(nid: int, info: dict, st: GraphState) -> None:
    import math
    img = get_connected_image(info.get("img_in_attr"), st)
    if img is None:
        _push_or_blank(nid, info, st, None)
        return

    p = _safe_params(info)
    rho      = float(p.get("rho",        1.0))
    thresh   = int(p.get("threshold",   50))
    min_len  = float(p.get("min_length", 30.0))
    max_gap  = float(p.get("max_gap",    10.0))

    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, rho, np.pi / 180, thresh,
                             minLineLength=min_len, maxLineGap=max_gap)

    result = img.copy()
    angles: list[float] = []
    if lines is not None:
        for ln in lines:
            x1, y1, x2, y2 = ln[0]
            cv2.line(result, (x1, y1), (x2, y2), (0, 255, 0), 2)
            ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
            angles.append(ang)

    count  = len(lines) if lines is not None else 0
    avg_ang = float(np.mean(angles)) if angles else 0.0
    _set_text_safe(info, "txt_count", f"lines: {count}")
    _set_text_safe(info, "txt_angle", f"avg angle: {avg_ang:.1f}°")

    st.node_data[nid] = {"count": count, "angle": avg_ang}
    _push_or_blank(nid, info, st, result)


# ── Centroid ──────────────────────────────────────────────────────────────────

def _eval_centroid(nid: int, info: dict, st: GraphState) -> None:
    """Compute spatial-moment centroid of the thresholded greyscale image."""
    img = get_connected_image(info.get("img_in_attr"), st)
    if img is None:
        _push_or_blank(nid, info, st, None)
        return

    p = _safe_params(info)
    thresh = int(p.get("threshold", 127))
    invert = bool(p.get("invert",   False))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    flag = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    _, binary = cv2.threshold(gray, thresh, 255, flag)

    M  = cv2.moments(binary)
    cx = cy = 0.0
    found = M["m00"] != 0
    if found:
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]

    result = img.copy()
    if found:
        ix, iy = int(cx), int(cy)
        cv2.line(result, (ix - 20, iy), (ix + 20, iy), (0, 0, 255), 2)
        cv2.line(result, (ix, iy - 20), (ix, iy + 20), (0, 0, 255), 2)
        cv2.circle(result, (ix, iy), 5, (0, 255, 255), -1)

    _set_text_safe(info, "txt_centroid", f"centroid: ({cx:.1f}, {cy:.1f})")
    _set_text_safe(info, "txt_cx",       f"cx: {cx:.1f}")
    _set_text_safe(info, "txt_cy",       f"cy: {cy:.1f}")

    st.node_data[nid] = {"centroid": [cx, cy], "cx": cx, "cy": cy}
    _push_or_blank(nid, info, st, result)
