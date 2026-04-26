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
P2P runtime behaviour — moves the robot to a 6-DOF target pose.

This is the *execution-side* counterpart of the GUI's P2PNodeDef.
Replace the stub ``update()`` body with real robot API calls.
"""
from __future__ import annotations
from bt_editor.runtime.behaviours.base import RuntimeBehaviour

#: Must match P2P_PARAMS in bt_editor/nodes/behaviours/p2p.py
P2P_PARAMS: tuple[str, ...] = ("x", "y", "z", "rx", "ry", "rz")


class P2PRuntimeBehaviour(RuntimeBehaviour):
    """Move-to-point behaviour carrying a 6-DOF target pose."""

    def __init__(self, **params: float) -> None:
        self.params: dict[str, float] = {
            k: float(params.get(k, 0.0)) for k in P2P_PARAMS
        }

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_json(cls, node_data: dict) -> "P2PRuntimeBehaviour":
        return cls(**node_data.get("params", {}))

    # ── py_trees Behaviour interface ──────────────────────────────────────────

    def setup(self) -> None:
        """Initialize hardware connection (override in your robot package)."""

    def update(self):
        """Send pose command and return execution status.

        Replace this with real robot API calls, e.g.:
            robot.move_to(**self.params)
            return py_trees.common.Status.SUCCESS
        """
        # Stub: always succeeds immediately.
        # return py_trees.common.Status.SUCCESS
        raise NotImplementedError("Implement update() with real robot API calls.")

    def __repr__(self) -> str:
        vals = ", ".join(f"{k}={v:.3f}" for k, v in self.params.items())
        return f"P2PRuntimeBehaviour({vals})"
