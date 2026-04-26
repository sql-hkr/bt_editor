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
DPG theme builders.

node_theme()     — normal node appearance keyed by type string
node_dim_theme() — dimmed (semi-transparent) appearance
build_global_theme() — dark Blender-style application theme
setup_fonts()    — load system fonts covering all Unicode glyphs used in the app
"""
from __future__ import annotations
import os
import dearpygui.dearpygui as dpg
from bt_editor.core.registry import registry

# ─────────────────────────────────────────────────────────────────────────────
# Font setup
# ─────────────────────────────────────────────────────────────────────────────

# Candidate monospace fonts in priority order (TTF/TTC).
_FONT_CANDIDATES = [
    # macOS built-ins
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
    "/System/Library/Fonts/Courier.ttc",
    # Common Linux mono fonts
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    # Windows
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
]


def setup_fonts(size: float = 14.0) -> int:
    """
    Create a font registry, load the first available system monospace font, and
    register all Unicode glyph ranges needed by the application.

    Returns the font item tag.  Bind it globally with ``dpg.bind_font(tag)``.
    """
    font_path = next((p for p in _FONT_CANDIDATES if os.path.exists(p)), None)
    if font_path is None:
        return 0  # no suitable font found; DPG will use its built-in default

    with dpg.font_registry():
        with dpg.font(font_path, size) as fnt:
            # Basic Latin + Latin-1 Supplement (covers °, ², ×, ¬ …)
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Default)
            # Greek (Δ, λ)
            dpg.add_font_range(0x0370, 0x03FF)
            # General Punctuation (–, —, •, …  U+2013–U+2026)
            dpg.add_font_range(0x2000, 0x206F)
            # Superscripts & Subscripts (⁺, ⁻, ₁, ₇)
            dpg.add_font_range(0x2070, 0x209F)
            # Arrows (↑, →, ↔)
            dpg.add_font_range(0x2190, 0x21FF)
            # Mathematical Operators (−, ≤, ⊗)
            dpg.add_font_range(0x2200, 0x22FF)
            # Box Drawing (─) + Block Elements (█, ░)
            dpg.add_font_range(0x2500, 0x259F)
            # Geometric Shapes (▶)
            dpg.add_font_range(0x25A0, 0x25FF)
    return fnt


def node_theme(ntype: str) -> int:
    """Create and return a DPG theme for *ntype* (normal brightness)."""
    r, g, b = registry.colors.get(ntype, (80, 80, 80))
    bg = (42, 42, 42)
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvNode):
            dpg.add_theme_color(dpg.mvNodeCol_TitleBar,
                                (r, g, b, 255), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_TitleBarHovered,
                                (min(r+30, 255), min(g+30, 255), min(b+30, 255), 255),
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_TitleBarSelected,
                                (min(r+55, 255), min(g+55, 255), min(b+55, 255), 255),
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeBackground,
                                (*bg, 230), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeBackgroundHovered,
                                (bg[0]+8, bg[1]+8, bg[2]+8, 230),
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeBackgroundSelected,
                                (bg[0]+18, bg[1]+18, bg[2]+18, 230),
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeOutline,
                                (18, 18, 18, 255), category=dpg.mvThemeCat_Nodes)
            pr, pg, pb = min(r+20, 255), min(g+20, 255), min(b+20, 255)
            dpg.add_theme_color(dpg.mvNodeCol_Pin,
                                (pr, pg, pb, 255), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_PinHovered,
                                (255, 255, 255, 255), category=dpg.mvThemeCat_Nodes)
    return theme


def node_dim_theme(ntype: str) -> int:
    """Create and return a dimmed (semi-transparent) DPG theme for *ntype*."""
    r, g, b = registry.colors.get(ntype, (80, 80, 80))
    dr, dg, db = r // 4, g // 4, b // 4
    bg = (28, 28, 28)
    a_title, a_bg = 80, 60
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvNode):
            dpg.add_theme_color(dpg.mvNodeCol_TitleBar,
                                (dr, dg, db, a_title), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_TitleBarHovered,
                                (dr, dg, db, a_title), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_TitleBarSelected,
                                (dr, dg, db, a_title), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeBackground,
                                (*bg, a_bg), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeBackgroundHovered,
                                (*bg, a_bg), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeBackgroundSelected,
                                (*bg, a_bg), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeOutline,
                                (15, 15, 15, 80), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_Pin,
                                (dr, dg, db, a_title), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_PinHovered,
                                (dr, dg, db, a_title), category=dpg.mvThemeCat_Nodes)
    return theme


def build_global_theme() -> int:
    """Build and return the application-wide dark Blender-inspired theme."""
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg,       (30,  30,  30, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,        (30,  30,  30, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,        (50,  50,  50, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (62,  62,  62, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive,  (75,  75,  75, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text,           (220, 220, 220, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Button,         (55,  55,  55, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  (80,  80,  80, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   (100, 100, 100, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Header,         (60,  60,  60, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered,  (80,  80,  80, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive,   (100, 100, 100, 255))
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg,        (35,  35,  35, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border,         (20,  20,  20, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Separator,      (60,  60,  60, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg,        (20,  20,  20, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive,  (30,  30,  30, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg,    (20,  20,  20, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab,  (60,  60,  60, 255))
        with dpg.theme_component(dpg.mvNodeEditor):
            dpg.add_theme_color(dpg.mvNodeCol_GridBackground,  (28, 28, 28, 255),
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_GridLine,        (42, 42, 42, 255),
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_Link,            (150, 150, 150, 255),
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_LinkHovered,     (210, 210, 210, 255),
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_LinkSelected,    (255, 255, 255, 255),
                                category=dpg.mvThemeCat_Nodes)
    return theme
