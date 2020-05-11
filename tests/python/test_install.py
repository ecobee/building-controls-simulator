#!/usr/bin/env python
# created by Tom Stesco tom.s@ecobee.com

from types import ModuleType
import importlib

import pytest


class TestInstall:
    def test_import_package_modules(self):
        """Test all package modules can be imported"""
        modules = [
            "BuildingControlSimulator",
        ]

        for m in modules:
            assert isinstance(importlib.import_module(m), ModuleType)

    def test_import_deps(self):
        """Test all dependencies can be imported"""
        deps = [
            "pyfmi",
            "pandas",
            "numpy",
            "scipy",
            "eppy",
            "plotly",
        ]
        for d in deps:
            assert isinstance(importlib.import_module(d), ModuleType)
