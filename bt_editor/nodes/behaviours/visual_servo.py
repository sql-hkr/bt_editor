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
Visual Servo behaviour nodes.

Covers the common visual-servo control loops for a robot manipulator:

  ImageBasedVS   — Image-Based Visual Servo (IBVS) using feature errors
  PositionBasedVS — Position-Based Visual Servo (PBVS)
  HybridVS       — Hybrid (2.5D) visual servo
  AlignFeature   — Align a single image feature (point/line/blob) to target
  MoveToTarget   — Move EE to a Cartesian target pose derived from vision
  CheckConverged — Check whether the servo error is below a threshold
"""
from __future__ import annotations
from bt_editor.nodes.behaviours._base import BehaviourNodeDef, ParamSpec


# ─────────────────────────────────────────────────────────────────────────────
# Image-Based Visual Servo  (IBVS)
# ─────────────────────────────────────────────────────────────────────────────

class ImageBasedVSNodeDef(BehaviourNodeDef):
    """Image-Based Visual Servo (IBVS).

    Controls velocity in image space: v = −λ · L⁺ · e
    where e = s − s* is the image-feature error.

    Parameters
    ----------
    gain        λ control gain
    max_vel     maximum joint velocity (rad/s)
    thresh_err  convergence threshold on feature error (pixels)
    """
    TYPE  = "ImageBasedVS"
    COLOR = (160, 80, 20)
    PARAMS = [
        ParamSpec("gain",       "Gain λ",          default=0.5,  min_val=0.0, max_val=5.0,   speed=0.01),
        ParamSpec("max_vel",    "Max vel (rad/s)",  default=0.5,  min_val=0.0, max_val=5.0,   speed=0.01),
        ParamSpec("thresh_err", "Threshold (px)",   default=2.0,  min_val=0.0, max_val=100.0, speed=0.1),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Position-Based Visual Servo  (PBVS)
# ─────────────────────────────────────────────────────────────────────────────

class PositionBasedVSNodeDef(BehaviourNodeDef):
    """Position-Based Visual Servo (PBVS).

    Reconstructs the 3D target pose from vision and controls in Cartesian space.

    Parameters
    ----------
    gain          λ control gain
    max_vel       maximum Cartesian velocity (m/s)
    thresh_pos    convergence threshold on position error (m)
    thresh_rot    convergence threshold on rotation error (rad)
    """
    TYPE  = "PositionBasedVS"
    COLOR = (20, 120, 160)
    PARAMS = [
        ParamSpec("gain",      "Gain λ",           default=0.5,  min_val=0.0, max_val=5.0,  speed=0.01),
        ParamSpec("max_vel",   "Max vel (m/s)",     default=0.1,  min_val=0.0, max_val=2.0,  speed=0.005),
        ParamSpec("thresh_pos","Thresh pos (m)",    default=0.005,min_val=0.0, max_val=0.5,  speed=0.001),
        ParamSpec("thresh_rot","Thresh rot (rad)",  default=0.01, min_val=0.0, max_val=0.5,  speed=0.001),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Hybrid (2.5D) Visual Servo
# ─────────────────────────────────────────────────────────────────────────────

class HybridVSNodeDef(BehaviourNodeDef):
    """Hybrid (2.5D) Visual Servo.

    Translational control in image space, rotational in 3D space.

    Parameters
    ----------
    gain_t    translational gain λ_t
    gain_r    rotational gain λ_r
    max_vel   maximum velocity magnitude
    thresh    convergence threshold
    """
    TYPE  = "HybridVS"
    COLOR = (100, 50, 160)
    PARAMS = [
        ParamSpec("gain_t",  "Gain λ_t",     default=0.5,  min_val=0.0, max_val=5.0, speed=0.01),
        ParamSpec("gain_r",  "Gain λ_r",     default=0.5,  min_val=0.0, max_val=5.0, speed=0.01),
        ParamSpec("max_vel", "Max vel",       default=0.5,  min_val=0.0, max_val=5.0, speed=0.01),
        ParamSpec("thresh",  "Threshold",     default=0.01, min_val=0.0, max_val=1.0, speed=0.001),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# AlignFeature
# ─────────────────────────────────────────────────────────────────────────────

class AlignFeatureNodeDef(BehaviourNodeDef):
    """Align a single image feature (point/centroid) to a target position.

    Parameters
    ----------
    target_u    desired image column (px)
    target_v    desired image row (px)
    gain        control gain
    thresh      convergence threshold (px)
    """
    TYPE  = "AlignFeature"
    COLOR = (160, 100, 20)
    PARAMS = [
        ParamSpec("target_u", "Target U (px)",  default=320.0, min_val=0.0, max_val=1920.0, speed=1.0, fmt="%.0f"),
        ParamSpec("target_v", "Target V (px)",  default=240.0, min_val=0.0, max_val=1080.0, speed=1.0, fmt="%.0f"),
        ParamSpec("gain",     "Gain λ",          default=0.5,   min_val=0.0, max_val=5.0,    speed=0.01),
        ParamSpec("thresh",   "Threshold (px)",  default=3.0,   min_val=0.0, max_val=50.0,   speed=0.1),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# MoveToTarget  (vision-guided Cartesian move)
# ─────────────────────────────────────────────────────────────────────────────

class MoveToTargetNodeDef(BehaviourNodeDef):
    """Move EE to a Cartesian target pose reconstructed from vision.

    Parameters
    ----------
    gain         control gain
    max_vel      maximum EE velocity (m/s)
    thresh_pos   position convergence threshold (m)
    thresh_rot   rotation convergence threshold (rad)
    approach_d   safe approach standoff distance (m)
    """
    TYPE  = "MoveToTarget"
    COLOR = (20, 140, 100)
    PARAMS = [
        ParamSpec("gain",       "Gain λ",           default=0.5,  min_val=0.0, max_val=5.0,  speed=0.01),
        ParamSpec("max_vel",    "Max vel (m/s)",     default=0.1,  min_val=0.0, max_val=2.0,  speed=0.005),
        ParamSpec("thresh_pos", "Thresh pos (m)",    default=0.005,min_val=0.0, max_val=0.5,  speed=0.001),
        ParamSpec("thresh_rot", "Thresh rot (rad)",  default=0.01, min_val=0.0, max_val=1.0,  speed=0.001),
        ParamSpec("approach_d", "Approach dist (m)", default=0.05, min_val=0.0, max_val=0.5,  speed=0.005),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# CheckConverged
# ─────────────────────────────────────────────────────────────────────────────

class CheckConvergedNodeDef(BehaviourNodeDef):
    """Condition: returns SUCCESS when servo error drops below threshold.

    Useful as a Condition node inside a Sequence before executing the next step.

    Parameters
    ----------
    thresh  convergence threshold (same unit as the upstream error signal)
    """
    TYPE  = "CheckConverged"
    COLOR = (40, 160, 60)
    PARAMS = [
        ParamSpec("thresh", "Threshold", default=0.01, min_val=0.0, max_val=10.0, speed=0.001),
    ]
