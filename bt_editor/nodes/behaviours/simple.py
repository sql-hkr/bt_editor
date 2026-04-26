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
Built-in simple behaviour nodes: Action and Condition variants.

These require no parameters; the GUI shows only a spacer in the body.
They extend BehaviourNodeDef with an empty PARAMS list and are auto-discovered.
"""
from __future__ import annotations
from bt_editor.nodes.behaviours._base import BehaviourNodeDef


class ActionSuccessNodeDef(BehaviourNodeDef):
    TYPE  = "Action (Success)"
    COLOR = (16, 133, 68)


class ActionFailureNodeDef(BehaviourNodeDef):
    TYPE  = "Action (Failure)"
    COLOR = (155, 20, 20)


class ActionRunningNodeDef(BehaviourNodeDef):
    TYPE  = "Action (Running)"
    COLOR = (160, 120, 0)


class ConditionTrueNodeDef(BehaviourNodeDef):
    TYPE  = "Condition (True)"
    COLOR = (0, 140, 140)


class ConditionFalseNodeDef(BehaviourNodeDef):
    TYPE  = "Condition (False)"
    COLOR = (110, 45, 45)
