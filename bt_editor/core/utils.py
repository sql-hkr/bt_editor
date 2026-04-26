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
Graph-level utility helpers that need access to both state and registry.
"""
from __future__ import annotations
from bt_editor.core.state import GraphState
from bt_editor.core.registry import NodeRegistry


def attr_to_socket_key(nid: int, attr_id: int,
                        state: GraphState, reg: NodeRegistry) -> str | None:
    """Map a DPG attribute tag back to its logical socket-key string.

    Returns strings like ``"in_attr"``, ``"out_attr"``, ``"img_in_attr"``,
    ``"math_in_attrs.A"``, etc., or ``None`` if not found.
    """
    info = state.nodes.get(nid)
    if not info:
        return None
    defn = reg.get(info["type"])
    std_keys = ("in_attr", "out_attr")
    extra_keys: tuple = tuple(defn.EXTRA_SOCKET_KEYS) if defn else ()
    for key in (*std_keys, *extra_keys):
        if info.get(key) == attr_id:
            return key
    for k, v in info.get("math_in_attrs", {}).items():
        if v == attr_id:
            return f"math_in_attrs.{k}"
    return None


def socket_key_to_attr(nid: int, socket_key: str,
                        state: GraphState) -> int | None:
    """Resolve a socket-key string back to a DPG attribute tag."""
    info = state.nodes.get(nid)
    if not info:
        return None
    if socket_key.startswith("math_in_attrs."):
        k = socket_key.split(".", 1)[1]
        return info.get("math_in_attrs", {}).get(k)
    return info.get(socket_key)


def all_attr_ids(nid: int, info: dict, reg: NodeRegistry) -> set[int]:
    """Return every DPG attr ID associated with *nid* (for bulk cleanup)."""
    defn = reg.get(info["type"])
    keys = ["in_attr", "out_attr"]
    if defn:
        keys.extend(defn.EXTRA_SOCKET_KEYS)
    result: set[int] = {info.get(k) for k in keys} - {None}  # type: ignore[arg-type]
    result.update(info.get("math_in_attrs", {}).values())
    return result
