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
Registers all built-in node types with the global NodeRegistry.

Import order determines Add-menu category ordering.
Behaviour plugins are auto-discovered from ``bt_editor/nodes/behaviours/``.
"""
from bt_editor.core.node_def import NodeDef
from bt_editor.core.registry import registry

# ── Composites ────────────────────────────────────────────────────────────────
from bt_editor.nodes.composites import (
    SequenceNodeDef, SelectorNodeDef, ParallelNodeDef)

for _defn in (SequenceNodeDef(), SelectorNodeDef(), ParallelNodeDef()):
    registry.register(_defn)

# ── Behaviours (reserve slot; discovery fills content) ────────────────────────
registry.pre_register_category("Behaviours")
registry.discover("bt_editor.nodes.behaviours", NodeDef)

# ── Decorators ────────────────────────────────────────────────────────────────
from bt_editor.nodes.decorators import (
    InverterNodeDef, ForceSuccessNodeDef, ForceFailureNodeDef,
    RepeatNodeDef, RetryUntilSuccessNodeDef, TimeoutNodeDef,
    SuccessIsRunningNodeDef)

for _defn in (InverterNodeDef(), ForceSuccessNodeDef(), ForceFailureNodeDef(),
              RepeatNodeDef(), RetryUntilSuccessNodeDef(),
              TimeoutNodeDef(), SuccessIsRunningNodeDef()):
    registry.register(_defn)

# ── Utilities ─────────────────────────────────────────────────────────────────
from bt_editor.nodes.utilities import (
    ValueNodeDef, VectorNodeDef, MathNodeDef,
    VectorTransformNodeDef, BlackboardNodeDef)

for _defn in (ValueNodeDef(), VectorNodeDef(), MathNodeDef(),
              VectorTransformNodeDef(), BlackboardNodeDef()):
    registry.register(_defn)

# ── Robotics ──────────────────────────────────────────────────────────────────
from bt_editor.nodes.robotics import (
    HTMatrixNodeDef, RPYtoHTMNodeDef, HTMtoRPYNodeDef,
    PoseComposeNodeDef, PoseInverseNodeDef, PoseErrorNodeDef,
    JointStateNodeDef,
    ScalarToVectorNodeDef, VectorSplitNodeDef,
    GainNodeDef, DotProductNodeDef, CrossProductNodeDef)

for _defn in (HTMatrixNodeDef(), RPYtoHTMNodeDef(), HTMtoRPYNodeDef(),
              PoseComposeNodeDef(), PoseInverseNodeDef(), PoseErrorNodeDef(),
              JointStateNodeDef(),
              ScalarToVectorNodeDef(), VectorSplitNodeDef(),
              GainNodeDef(), DotProductNodeDef(), CrossProductNodeDef()):
    registry.register(_defn)

# ── Input ─────────────────────────────────────────────────────────────────────
from bt_editor.nodes.image_nodes import ImageNodeDef
registry.register(ImageNodeDef())

# ── Vision (feature extraction) ───────────────────────────────────────────────
from bt_editor.nodes.cv_feature_nodes import (
    BlobDetectorNodeDef, ContourAnalysisNodeDef, ColorMaskNodeDef,
    CornerDetectorNodeDef, TemplateMatchNodeDef, LineDetectorNodeDef,
    CentroidNodeDef)

for _defn in (BlobDetectorNodeDef(), ContourAnalysisNodeDef(),
              ColorMaskNodeDef(), CornerDetectorNodeDef(),
              TemplateMatchNodeDef(), LineDetectorNodeDef(),
              CentroidNodeDef()):
    registry.register(_defn)

# ── Output ────────────────────────────────────────────────────────────────────
from bt_editor.nodes.image_nodes import OpenCVNodeDef, ResultImageNodeDef
registry.register(OpenCVNodeDef())
registry.register(ResultImageNodeDef())

# ── BT Root (internal — not shown in Add menu) ────────────────────────────────
from bt_editor.nodes.root import BTRootNodeDef
registry.register(BTRootNodeDef())
