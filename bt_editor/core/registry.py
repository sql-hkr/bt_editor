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
NodeRegistry — central store for all NodeDef instances.

Built-in nodes are registered explicitly in ``bt_editor/nodes/__init__.py``.
Behaviour plugins are auto-discovered with ``registry.discover()``.

Import the module-level singleton ``registry`` everywhere:

    from bt_editor.core.registry import registry
"""
from __future__ import annotations
import importlib
import inspect
import pkgutil
from pathlib import Path

from bt_editor.core.node_def import NodeDef


class NodeRegistry:

    def __init__(self) -> None:
        # Insertion-ordered dicts → stable menu ordering
        self._defs:       dict[str, NodeDef]      = {}
        self._categories: dict[str, list[str]]    = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, defn: NodeDef) -> None:
        """Register a NodeDef instance, creating its category slot if needed."""
        self._defs[defn.TYPE] = defn
        lst = self._categories.setdefault(defn.CATEGORY, [])
        if defn.TYPE not in lst:
            lst.append(defn.TYPE)

    def pre_register_category(self, category: str) -> None:
        """Reserve a category slot to control Add-menu ordering.

        Call this *before* ``discover()`` to ensure the category appears at the
        correct position even when filled entirely by plugin discovery.
        """
        self._categories.setdefault(category, [])

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get(self, type_str: str) -> NodeDef | None:
        return self._defs.get(type_str)

    def has(self, type_str: str) -> bool:
        return type_str in self._defs

    @property
    def categories(self) -> dict[str, list[str]]:
        """Ordered mapping of {category: [type, ...]}."""
        return dict(self._categories)

    @property
    def all_types(self) -> list[str]:
        return list(self._defs.keys())

    @property
    def colors(self) -> dict[str, tuple[int, int, int]]:
        return {t: d.COLOR for t, d in self._defs.items()}

    @property
    def ctrl_types(self) -> set[str]:
        return {t for t, d in self._defs.items() if d.IS_CTRL}

    # ── Plugin discovery ──────────────────────────────────────────────────────

    def discover(self, package_name: str, base_class: type = NodeDef) -> None:
        """Import every non-private module in *package_name* and register any
        concrete subclass of *base_class* that declares a non-empty TYPE.

        Private modules (names starting with ``_``) are skipped so that base
        classes stored in ``_base.py`` are not auto-registered.
        """
        try:
            pkg = importlib.import_module(package_name)
        except ImportError:
            return
        pkg_path = Path(pkg.__file__).parent
        for _, mod_name, _ in pkgutil.iter_modules([str(pkg_path)]):
            if mod_name.startswith("_"):
                continue
            try:
                mod = importlib.import_module(f"{package_name}.{mod_name}")
            except Exception as exc:
                print(f"[NodeRegistry] Could not load {package_name}.{mod_name}: {exc}")
                continue
            for _, cls in inspect.getmembers(mod, inspect.isclass):
                if (issubclass(cls, base_class)
                        and cls is not base_class
                        and getattr(cls, "TYPE", None)):
                    self.register(cls())


# Module-level singleton
registry = NodeRegistry()
