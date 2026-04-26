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
Debug overlay — passthrough HUD rendered via the viewport draw list.

Content is drawn directly in viewport space using draw commands, so:
  * mouse events pass through the overlay to the node editor
  * only text pixels are visible; everything else is fully transparent
  * no window chrome, no background rectangle

Press **F3** (or View -> Debug Overlay) to toggle.
"""
from __future__ import annotations
import platform
import sys
import time
import dearpygui.dearpygui as dpg

try:
    import psutil as _psutil       # type: ignore[import-untyped]
    _HAS_PSUTIL = True
except ImportError:
    _psutil = None                  # type: ignore[assignment]
    _HAS_PSUTIL = False

from bt_editor.constants import EDITOR_TAG
from bt_editor.core.state import state as _state

# ─────────────────────────────────────────────────────────────────────────────
# Module-level state
# ─────────────────────────────────────────────────────────────────────────────

_DRAWLIST_TAG = "dbg_overlay_dl"
_visible      = [False]

# Layout
_X_L      =   8    # left column left margin (px)
_R_MARGIN =  20    # gap between right column text and the viewport right edge (px)
_Y0       =  26    # first line top — just below the ~22 px menu bar
_TSIZE    =  22.0  # draw_text font size
_LH       =  int(_TSIZE)  # line height with zero gap (font size = line height)

# Per-line text background
_BG_COL   = (80, 80, 80, 100)  # grey semi-transparent
_CHAR_W   =  10.5              # estimated monospace glyph width at _TSIZE px
_PAD_X    =   4                # horizontal padding around the background rect
_PAD_Y    =   0                # vertical padding (0 = zero line gap)

# Plain white — no per-section colouring anywhere
_COL    = (255, 255, 255, 255)

# CPU sampling
_cpu_cache:  list[float] = []
_cpu_last_t: list[float] = [0.0]
_CPU_INTERVAL = 1.0               # seconds between samples


def _head(text: str) -> None:
    dpg.add_text(text, color=(152, 217, 84, 255))   # Minecraft green


def _dim(text: str) -> None:
    dpg.add_text(text, color=(170, 170, 170, 210))


def _bar(pct: float, w: int = 14) -> str:
    """ASCII usage bar."""
    filled = round(max(0.0, min(100.0, pct)) / 100.0 * w)
    return "[" + "X" * filled + "." * (w - filled) + f"]  {pct:5.1f}%"


def _draw_line(x: float, y: float, text: str) -> None:
    """Draw one text line with a semi-transparent black background rect."""
    w = len(text) * _CHAR_W
    dpg.draw_rectangle(
        [x - _PAD_X,         y - _PAD_Y],
        [x + w + _PAD_X, y + _TSIZE + _PAD_Y],
        color=(0, 0, 0, 0),
        fill=_BG_COL,
        parent=_DRAWLIST_TAG,
    )
    dpg.draw_text([x, y], text, color=_COL, size=_TSIZE, parent=_DRAWLIST_TAG)


# ─────────────────────────────────────────────────────────────────────────────
# Static system info  (gathered once at import time)
# ─────────────────────────────────────────────────────────────────────────────

def _gather_static() -> dict[str, str]:
    import subprocess
    d: dict[str, str] = {}
    d["os"]  = f"{platform.system()} {platform.release()}  [{platform.machine()}]"
    d["py"]  = f"Python {sys.version.split()[0]}"

    # CPU brand
    raw_cpu = platform.processor() or ""
    if not raw_cpu or raw_cpu in ("arm", "i386", "x86_64"):
        try:
            brand = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                stderr=subprocess.DEVNULL, timeout=1,
            ).decode().strip()
            raw_cpu = brand if brand else (platform.machine() or "Unknown CPU")
        except Exception:
            raw_cpu = platform.machine() or "Unknown CPU"
    d["cpu"] = raw_cpu

    if _HAS_PSUTIL:
        lc  = _psutil.cpu_count(logical=True)    # type: ignore[union-attr]
        pc  = _psutil.cpu_count(logical=False)   # type: ignore[union-attr]
        try:
            freq = _psutil.cpu_freq()            # type: ignore[union-attr]
            fs   = (f"  @{freq.max/1000:.2f} GHz"
                    if freq and freq.max >= 100 else "")
        except Exception:
            fs = ""
        d["cpu_ct"]  = f"{pc} cores / {lc} threads{fs}"
        vm           = _psutil.virtual_memory()  # type: ignore[union-attr]
        d["ram_tot"] = f"{vm.total / (1024**3):.1f} GB"
    else:
        d["cpu_ct"]  = "?"
        d["ram_tot"] = "?"

    # GPU — parse system_profiler on macOS; fallback on other platforms
    gpu_model  = "Unknown GPU"
    gpu_extra: list[str] = []
    try:
        sp = subprocess.check_output(
            ["system_profiler", "SPDisplaysDataType"],
            stderr=subprocess.DEVNULL, timeout=5,
        ).decode()
        for line in sp.splitlines():
            ls = line.strip()
            if ls.startswith("Chipset Model:"):
                gpu_model = ls.split(":", 1)[1].strip()
            elif ls.startswith("Total Number of Cores:"):
                gpu_extra.append(f"{ls.split(':', 1)[1].strip()} cores")
            elif ls.startswith("Metal Support:"):
                gpu_extra.append(ls.split(":", 1)[1].strip())
            elif ls.startswith("VRAM"):
                gpu_extra.append(ls.split(":", 1)[1].strip())
    except Exception:
        pass
    d["gpu"]       = gpu_model
    d["gpu_extra"] = "  /  ".join(gpu_extra) if gpu_extra else ""

    return d


_SYS = _gather_static()

# ─────────────────────────────────────────────────────────────────────────────
# CPU sampling (once per second)
# ─────────────────────────────────────────────────────────────────────────────

def _maybe_sample_cpu() -> None:
    if not _HAS_PSUTIL:
        return
    now = time.monotonic()
    if now - _cpu_last_t[0] >= _CPU_INTERVAL:
        _cpu_cache.clear()
        _cpu_cache.extend(
            _psutil.cpu_percent(percpu=True))  # type: ignore[union-attr]
        _cpu_last_t[0] = now

# ─────────────────────────────────────────────────────────────────────────────
# Two-column line builders
# ─────────────────────────────────────────────────────────────────────────────

def _build_left() -> list[str]:
    """Static / slow-changing info — left column."""
    lines: list[str] = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines.append("BT Node Editor v1.0")
    lines.append("Debug: True [Overlay Mode]")
    lines.append("")

    # ── Engine ────────────────────────────────────────────────────────────────
    lines.append("Engine: Custom BT Runtime")
    lines.append("API: BT Node Editor v1.0")
    lines.append("Threading: Single-threaded")
    lines.append("")

    # ── System ────────────────────────────────────────────────────────────────
    lines.append(f"OS: {_SYS['os']}")
    lines.append(f"CPU: {_SYS['cpu']}")
    lines.append(f"Cores: {_SYS['cpu_ct']}")
    lines.append(f"RAM: {_SYS['ram_tot']}")
    lines.append(f"GPU: {_SYS['gpu']}")
    if _SYS["gpu_extra"]:
        lines.append(f"     {_SYS['gpu_extra']}")
    lines.append("")

    # ── Display ───────────────────────────────────────────────────────────────
    try:
        vw = dpg.get_viewport_width()
        vh = dpg.get_viewport_height()
        lines.append(f"Display: {vw} x {vh}")
    except Exception:
        lines.append("Display: ?")
    lines.append(f"DearPyGui: {dpg.get_dearpygui_version()}")
    lines.append(f"Python: {_SYS['py']}")

    return lines


def _build_right() -> list[str]:
    """Dynamic / per-frame info — right column."""
    lines: list[str] = []

    # ── Performance ───────────────────────────────────────────────────────────
    fps = dpg.get_frame_rate()
    ft  = 1000.0 / fps if fps > 0 else 0.0
    fc  = dpg.get_frame_count()
    lines.append(f"FPS: {fps:.2f}")
    lines.append(f"Frame Time: {ft:.2f} ms")
    lines.append(f"Frame: #{fc}")
    lines.append("")

    # ── Node editor cursor ────────────────────────────────────────────────────
    # dpg.node_editor does NOT report its rect via get_item_rect_min/max
    # (always returns 0,0).  Use viewport client size for Canvas and derive
    # canvas coords directly from a reference node's screen vs canvas pos:
    #   canvas_x = mouse_screen_x - node_screen_x + node_canvas_x
    # This formula is correct regardless of pan/zoom and needs no container rect.
    if dpg.does_item_exist(EDITOR_TAG):
        try:
            mx, my = dpg.get_mouse_pos(local=False)

            # Canvas size — viewport client area minus the ~22 px menu bar
            _MENU_H = 22
            cw = dpg.get_viewport_client_width()
            ch = max(0, dpg.get_viewport_client_height() - _MENU_H)
            lines.append(f"Canvas: {cw} x {ch}")

            # Canvas coordinates — derived from any reference node
            cx = cy = None
            for ref_nid in _state.nodes:
                if dpg.does_item_exist(ref_nid):
                    cvs = dpg.get_item_pos(ref_nid)       # canvas space
                    scr = dpg.get_item_rect_min(ref_nid)  # screen space
                    cx  = mx - scr[0] + cvs[0]
                    cy  = my - scr[1] + cvs[1]
                    break
            if cx is None:
                lines.append("Editor XY: ? / ?")
            else:
                lines.append(f"Editor XY: {cx:.1f} / {cy:.1f}")
        except Exception:
            lines.append("Canvas: ?")
            lines.append("Editor XY: ? / ?")
    else:
        lines.append("Canvas: ?")
        lines.append("Editor XY: ? / ?")
    lines.append("")

    # ── Graph stats ───────────────────────────────────────────────────────────
    lines.append("Graph Stats:")
    lines.append(f"Total Nodes: {len(_state.nodes)}")
    lines.append(f"Connections: {len(_state.links)}")
    lines.append("")

    # ── Memory / CPU average (psutil) ────────────────────────────────────────
    if _HAS_PSUTIL:
        _maybe_sample_cpu()
        vm        = _psutil.virtual_memory()   # type: ignore[union-attr]
        # On macOS vm.used excludes compressed/cached memory, so percent and
        # used_mb would be inconsistent.  Use (total - available) which is
        # exactly what vm.percent is calculated from.
        used_mb   = int((vm.total - vm.available) / (1024 ** 2))
        total_mb  = int(vm.total / (1024 ** 2))
        lines.append(f"Mem: {vm.percent:.0f}%  {used_mb}/{total_mb} MB")
        if _cpu_cache:
            avg = sum(_cpu_cache) / len(_cpu_cache)
            lines.append(f"CPU: {avg:.1f}%")
        lines.append("")

    # ── Selected node info ────────────────────────────────────────────────────
    lines.append("Selected Node:")
    try:
        sel = dpg.get_selected_nodes(EDITOR_TAG) if dpg.does_item_exist(EDITOR_TAG) else []
    except Exception:
        sel = []

    if sel:
        nid  = sel[0]   # show first selected node
        info = _state.nodes.get(nid, {})
        ntype = info.get("type",  "?")
        label = info.get("label", "?")
        try:
            pos = dpg.get_item_pos(nid)
            px, py = pos[0], pos[1]
        except Exception:
            px, py = 0.0, 0.0
        lines.append(f"  Name:  {label}")
        lines.append(f"  Type:  {ntype}")
        lines.append(f"  ID:    #{nid}")
        lines.append(f"  Pos:   {px:.0f} / {py:.0f}")
        if len(sel) > 1:
            lines.append(f"  (+{len(sel)-1} more selected)")
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("Warnings: None")
    lines.append("Errors: 0")

    return lines

# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def build_debug_overlay() -> None:
    """Register the viewport draw list (call once after dpg.create_context)."""
    dpg.add_viewport_drawlist(tag=_DRAWLIST_TAG, front=True)


def toggle_debug_overlay(sender=None, app_data=None) -> None:
    _visible[0] = not _visible[0]
    if not _visible[0] and dpg.does_item_exist(_DRAWLIST_TAG):
        dpg.delete_item(_DRAWLIST_TAG, children_only=True)


def update_debug_overlay() -> None:
    """Redraw all overlay text each frame.  Returns immediately when hidden."""
    if not _visible[0]:
        return
    if not dpg.does_item_exist(_DRAWLIST_TAG):
        return

    # Clear the previous frame's draw commands
    dpg.delete_item(_DRAWLIST_TAG, children_only=True)

    # Right column: each line is individually right-aligned to the viewport edge.
    # Using viewport width (not editor rect) for a stable reference across frames.
    try:
        vw = dpg.get_viewport_width()
    except Exception:
        vw = 1320

    # Left column
    y = _Y0
    for line in _build_left():
        if line:
            _draw_line(_X_L, y, line)
        y += _LH

    # Right column — each line is right-aligned to the viewport right edge
    y = _Y0
    for line in _build_right():
        if line:
            x_r = vw - len(line) * _CHAR_W - _R_MARGIN
            _draw_line(x_r, y, line)
        y += _LH
