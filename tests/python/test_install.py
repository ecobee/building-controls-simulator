import pytest

from types import ModuleType


class TestImports:
    def test_import_package(self):
        import BuildingControlSimulator as bcs

        assert isinstance(bcs, ModuleType)

    def test_import_pyfmi(self):
        import pyfmi

        assert isinstance(pyfmi, ModuleType)
